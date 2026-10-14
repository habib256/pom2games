#!/usr/bin/env python3
"""Differential commands through both real Apple II games, with RAM evidence.

Requires the local original build/SIERRA.woz, build/JOURNEY.dsk and
build/files/TOPO.B. Never substitutes a Python survival model for the
original. Reports every observed difference and exits nonzero on differences
or incomplete commands. Artifacts (RAM, screenshots, JSON, emulator logs)
remain in ignored build/adventure/. The opening is a checkpoint sequence,
not evidence of a completed crash-to-outpost adventure.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from common import HERE, L, a2test, disk_with, fp, text_screen
from re_surv_run import boot
import topo
import mkmap
from gendata import VOCAB

OPENING = [('USE COMPASS', ()), ('WEAR PARKA', ()),
           ('DRINK WATER', ('C', '10')),
           ('EAT CHEESE', ('8', 'P')), ('REST', ('1',))]
SCENARIOS = {
    'opening': OPENING,
    'camp': OPENING + [('DRINK WATER', ('C', '10')), ('EAT CHEESE', ('8', 'P')),
                      ('REST', ('3',)), ('DRINK WATER', ('C', '10')),
                      ('EAT CHEESE', ('8', 'P')), ('REST', ('6',))],
    'overnight': OPENING + [('REST', ('6',)), ('DRINK WATER', ('C', '10')),
                           ('EAT CHEESE', ('8', 'P')), ('REST', ('8',))],
    'travel': OPENING + [('LOOK E', ()), ('WALK', ('1',)),
                        ('DRINK WATER', ('C', '10')), ('EAT CHEESE', ('8', 'P'))],
    'discovery': OPENING + [('LOOK AZ', ('73',)), ('WALK', ('1',)),
                           ('DRINK WATER', ('C', '10')), ('EAT CHEESE', ('8', 'P'))],
}
# LOOK UP / LOOK DOWN (docs/LOOK_UPDOWN.md): the port's tilt against the
# original's $E7 at every step, no game time (compared only here: the
# original also tilts the view by itself at some encounters, the port not).
SCENARIOS['look_tilt'] = [(c, ()) for c in ('LOOK U', 'LOOK R', 'VIEW', 'LOOK D', 'LOOK F',
                                             'PAN U', 'PAN U', 'PAN D', 'PAN D', 'PAN D')]
TILT_SCENARIOS = {'look_tilt'}
for scenario in ('march', 'encounter'):
    SCENARIOS[scenario] = [(r['command'], r['answers']) for r in
        json.loads((HERE/f'tests/fixtures/sierra_{scenario}.json').read_text())['commands']]
FLOATS = {'hour': ('s_hour', 0x4C57), 'elapsed': ('s_elap', 0x4C61),
          'date': ('s_date', 0x4C89), 'health': ('s_health', 0x4C34),
          'body': ('s_body', 0x4C70), 'since_drink': ('s_drink', 0x49CD+75),
          'since_meal': ('s_eat', 0x49CD+80), 'since_rest': ('s_rest', 0x49CD+85),
          'water_deficit': ('s_defw', 0x4950+105),
          'food_deficit': ('s_deff', 0x4950+110),
          'rest_deficit': ('s_defr', 0x4950+115)}


def original_map():
    raw = (HERE / 'build/files/TOPO.B').read_bytes()
    samples = (HERE/'build/re_geography/heights.bin').read_bytes()
    types = (HERE/'build/re_geography/types.bin').read_bytes()
    assert len(samples) == len(types) == 224*168
    h = [list(samples[y*224:(y+1)*224]) for y in range(168)]
    water = [[False]*mkmap.W for _ in range(mkmap.H)]
    for y, items in enumerate(topo.rows(raw)):
        for x, value, flag in items:
            if isinstance(flag, tuple):
                for xx in range(x, min(flag[1], mkmap.W-1)+1):
                    water[y][xx] = True
                    h[y][xx] = value
            elif flag == 0x80:
                water[y][x] = True
                h[y][x] = value
    woods = [[False]*224 for _ in range(168)]
    full_woods = bytearray(28*168)
    for y, spans in enumerate(topo.woods(raw)):
        for x0, x1 in spans:
            for x in range(x0, min(x1,223)+1):
                woods[y][x] = True
                full_woods[y*28+x//8] |= 1 << (x%8)
    result = bytearray(mkmap.map_bin(h, water, (raw[0x84], raw[0x83]),
                         (raw[0x81], raw[0x80]), round(128*560/360),
                         declination=int.from_bytes(raw[0xA9:0xAA], 'little', signed=True),
                         woods=woods))
    saved = (HERE / 'build/game.bin').read_bytes()
    result[28:32] = bytes((1, saved[0x4B9B], saved[0x4B9D], saved[0x4B9F]))
    result[16:21] = bytes(5)  # no artificial cabin on the Sierra comparison map
    result[37] = 1
    # Water heights fit six bits in Sierra; bit 6 distinguishes lakes from
    # rivers in the bank. The query strips it before returning the height.
    result += bytes(v | (192 if t == 1 else 128 if t == 128 else 0)
                    for v,t in zip(samples,types))
    result += full_woods
    return bytes(result)


def screen(mem):
    return '\n'.join(text_screen(mem[0x400:0x800])[20:24])


def normalized(mem, original):
    if original:
        value = {name: fp(mem[addr:addr+5]) for name, (_, addr) in FLOATS.items()}
        value.update(x=mem[0xD0], y=mem[0xD1],
                     heading=int.from_bytes(mem[0xD2:0xD4], 'little'),
                     calories_spent=int.from_bytes(mem[0x4BDA:0x4BDC], 'little'),
                     calories_eaten=int.from_bytes(mem[0x4BDC:0x4BDE], 'little'))
        value['shivering'] = bool(mem[0x4B87])
        value['sweating'] = bool(mem[0x4B7B])
        value['air_temperature'] = int.from_bytes(mem[0x4B9B:0x4B9C], 'little', signed=True)
        value['wind'] = mem[0x4B9F]
        value['felt_temperature'] = int.from_bytes(mem[0x4B9D:0x4B9E], 'little', signed=True)
        value['inside_shelter'] = bool(mem[0x0D5E])
        value['health_interval'] = int.from_bytes(mem[0x4BCC:0x4BCE], 'little')
        value['health_pending'] = int.from_bytes(mem[0x4C08:0x4C0A], 'little')
        value['animal'] = mem[0xD80]&127 if mem[0x4B72] else 0
        value['random_state'] = int.from_bytes(mem[0x03B9:0x03BD], 'little')
        value['load_free'] = [int.from_bytes(mem[a:a+2], 'little')
                              for a in (0x4BF8, 0x4BEE, 0x4BF0, 0x4BF2)]
        value['items'] = list(mem[0x404C+1:0x404C+76])
        for title, addr in [('ground', 0x42AC), ('pack', 0x4344), ('ounces', 0x417C)]:
            value[title] = [int.from_bytes(mem[addr+2*i:addr+2*i+2], 'little')
                            for i in range(22, 38)]
    else:
        value = {name: fp(mem[L[label]:L[label]+5]) for name, (label, _) in FLOATS.items()}
        value.update(x=int.from_bytes(mem[L['px']:L['px']+2], 'little')/128,
                     y=int.from_bytes(mem[L['py']:L['py']+2], 'little')/128,
                     heading=int.from_bytes(mem[L['heading']:L['heading']+2], 'little')*360/560,
                     calories_spent=fp(mem[L['s_spent']:L['s_spent']+5]),
                     calories_eaten=fp(mem[L['s_eaten']:L['s_eaten']+5]))
        value['shivering'] = mem[L['thermal_mode']] == 2
        value['sweating'] = mem[L['thermal_mode']] == 1
        value['air_temperature'] = int.from_bytes(mem[L['airtemp']:L['airtemp']+1], 'little', signed=True)
        value['wind'] = mem[L['wind']]
        value['felt_temperature'] = int.from_bytes(mem[L['felt_temp']:L['felt_temp']+2], 'little', signed=True)
        value['inside_shelter'] = bool(mem[L['shelter_inside']])
        value['health_interval'] = mem[L['health_period']]
        value['health_pending'] = int.from_bytes(mem[L['health_minutes']:L['health_minutes']+2], 'little')
        value['animal'] = max(0, mem[L['animal_kind']]-5)
        value['random_state'] = int.from_bytes(mem[L['weather_seed']:L['weather_seed']+4], 'little')
        value['load_free'] = [int.from_bytes(mem[L['load_limits']+i:L['load_limits']+i+2], 'little')
                             - int.from_bytes(mem[L['load_used']+i:L['load_used']+i+2], 'little')
                             for i in (0, 2, 4, 6)]
        value['items'] = list(mem[L['it_place']+1:L['it_place']+76])
        for title, prefix in [('ground', 'it_gnd'), ('pack', 'it_pack'), ('ounces', 'it_oz')]:
            value[title] = [mem[L[prefix+'_lo']+i] + 256*mem[L[prefix+'_hi']+i]
                            for i in range(22, 38)]
    # Compare what can actually be used at this position. Keep the raw tables
    # separately in each checkpoint: the native game pages remote ground
    # stores out, whereas the port retains their coordinates.
    places = value['items']
    ground = value.pop('ground')
    pack = value.pop('pack')
    value.pop('ounces')
    accessible_ground = []
    for i, quantity in enumerate(ground, 22):
        here = original or (mem[L['it_x']+i] == mem[L['px']+1]
                            and mem[L['it_y']+i] == mem[L['py']+1])
        accessible_ground.append(quantity if here and places[i-1] != 255 else 0)
    value['ground_accessible'] = accessible_ground
    value['pack_accessible'] = [q if places[i-1] not in (0, 255, 5) else 0
                                for i, q in enumerate(pack, 22)]
    for i in range(1, 76):
        if 22 <= i < 38:
            value['items'][i-1] = (bool(value['ground_accessible'][i-22]),
                                    bool(value['pack_accessible'][i-22]))
        elif not original and places[i-1] == 0 and (
                mem[L['it_x']+i] != mem[L['px']+1]
                or mem[L['it_y']+i] != mem[L['py']+1]):
            value['items'][i-1] = 255
    return value


def raw_inventory(mem, original):
    if original:
        return dict(items=list(mem[0x404D:0x4098]),
                    ground=[int.from_bytes(mem[0x42AC+2*i:0x42AE+2*i], 'little')
                            for i in range(22, 38)],
                    ounces=[int.from_bytes(mem[0x417C+2*i:0x417E+2*i], 'little')
                            for i in range(22, 38)])
    return dict(items=list(mem[L['it_place']+1:L['it_place']+76]),
                ground=[mem[L['it_gnd_lo']+i]+256*mem[L['it_gnd_hi']+i]
                        for i in range(22, 38)],
                ounces=[mem[L['it_oz_lo']+i]+256*mem[L['it_oz_hi']+i]
                        for i in range(22, 38)])


def differences(original, port):
    out = []
    for name, expected in original.items():
        actual = port[name]
        if name == 'heading':  # explicit resolution: 560 azimuths versus 360
            ok = abs((actual-expected+180) % 360-180) <= 360/560/2
        elif isinstance(expected, float):
            ok = abs(actual-expected) <= 2e-6
        else:
            ok = actual == expected
        if not ok:
            if isinstance(expected, list):
                base = {'items': 1, 'load_free': 0}.get(name, 22)
                for i, (a, b) in enumerate(zip(expected, actual), base):
                    if a != b:
                        out.append(dict(field=f'{name}[{i}]', original=a, port=b))
            else:
                out.append(dict(field=name, original=expected, port=actual))
    return out


class Driver:
    def __init__(self, disk, original, directory):
        self.original = original
        self.directory = directory
        self.session = a2test.Session(disk, cwd=HERE)
        self.events = []
        self.state_sources = []
        self.raw_inventories = []

    def __enter__(self):
        self.session.__enter__()
        try:
            if self.original:
                for step in boot():
                    self.session.step(step)
                # SURV3D $103E saves $4000-$4FFF to Journey T04 before
                # borrowing that RAM for HGR page 2. Observe the unmodified
                # game's state before it pages out; do not send extra commands.
                self.session.step('watch:103E:4000:4096')
                self.session.step('watch:03DB:4BC6:16')
                self.session.step('watch:0321:0100:256')
            else:
                self.session.step(L.until('idle', 20000))
                self.session.step(f'watch:{L["spend"]:04X}:{L["health_period"]:04X}:1')
        except Exception:
            self.__exit__(*sys.exc_info())
            raise
        return self

    def __exit__(self, *args):
        (self.directory / ('original.log' if self.original else 'port.log')).write_text(self.session.out)
        self.session.__exit__(*args)

    def memory(self):
        return self.session.step('peek:0000:49152').mem(0, 49152)

    def observed_state(self, memory):
        if not self.original or memory[0x4D00:0x4D03] == bytes.fromhex('4c3c4d'):
            return memory
        state = None
        for hexdata in re.findall(r'^watch 103E .* mem=([0-9A-F]+)$', self.session.out, re.M):
            candidate = bytes.fromhex(hexdata)
            if candidate[0xD00:0xD03] == bytes.fromhex('4c3c4d'):
                state = candidate
        if state is None:
            raise AssertionError('Original state is paged out and no valid pre-save observation exists')
        merged = bytearray(memory)
        merged[0x4000:0x5000] = state
        return bytes(merged)

    def checkpoint(self, index, screenshot=True):
        kind = 'original' if self.original else 'port'
        memory = self.memory()
        source = 'RAM'
        if self.original and memory[0x4D00:0x4D03] != bytes.fromhex('4c3c4d'):
            (self.directory / f'{kind}-{index:03}.raw.bin').write_bytes(memory)
            memory = self.observed_state(memory)
            source = 'observed before original pages state to disk'
        self.state_sources.append(source)
        self.raw_inventories.append(raw_inventory(memory, self.original))
        (self.directory / f'{kind}-{index:03}.bin').write_bytes(memory)
        self.last_memory = memory
        if screenshot:
            self.session.step(f'shot:{self.directory / f"{kind}-{index:03}.png"}')
        return normalized(memory, self.original)

    def command(self, command, answers):
        if self.original:
            # The native night animation can take longer than a2shot's fixed
            # three-frame key delay. Observe each accepted character rather
            # than overwriting the guest's single keyboard latch mid-animation.
            for char in command:
                self.session.step('press:'+char)
                self.session.step('until:B126:20000')  # character added to $0200
                self.session.step('until:B0E2:20000')
            self.session.step('press:\r')
            self.session.step('until:B143:20000')      # RETURN accepted
        else:
            self.session.step('key:'+command+'\r')
        decisions = {}
        water_decisions = answers if isinstance(answers, dict) and command in ('GET WATER', 'DRINK WATER') else {}
        if water_decisions:
            pending = [water_decisions['ounces']]
            if not self.original and command == 'DRINK WATER' and (water_decisions['source'] != 'C' or water_decisions['river'] != 'N'):
                raise AssertionError('Only canteen drinking has an equivalent port source selector yet')
        elif isinstance(answers, dict):
            if any(answers.get(k, v) != v for k, v in (("river", "N"), ("shore", "N"), ("straight", "Y"))):
                raise AssertionError("Only explicit straight travel can be compared by this driver")
            decisions = {k: v for k, v in answers.items() if k != "hours"}
            pending = [answers["hours"]]
        else:
            pending = list(answers)
        if not self.original and command in ('WALK', 'SWIM', 'REST', 'WAIT', 'CAMP'):
            pending = [f'{round(float(a)*60)} MIN' if '.' in a else a for a in pending if a not in ('N', 'Y')]
        if not self.original and command == 'DRINK WATER' and not water_decisions:
            if pending and pending[0] != 'C':
                raise AssertionError('Ground drinking has no equivalent port source selector yet')
            pending = pending[1:]  # port currently selects the canteen implicitly
        if not self.original and command == 'GET WATER':
            if water_decisions:
                if water_decisions['source'] != 'G' or water_decisions['river'] != 'Y':
                    raise AssertionError('Only explicit river collection is supported by the port adapter')
            else:
                if not pending or pending[0] != 'Y':
                    raise AssertionError('River collection requires an explicit original source decision')
                pending.pop(0)
        if not self.original and command.startswith('EAT '):
            pending = pending[:1]  # port currently selects the pack implicitly
        for _ in range(16):
            self.session.step('wait:1')
            targets = (0xB0E2, 0xFD1B) if self.original else (L['idle'], L['number_idle'], L['wait_key'])
            result = self.session.step('until:'+','.join(f'{a:04X}' for a in targets)+':20000')
            pc = int(re.search(r'PC=([0-9A-F]{4})', result.out)[1], 16)
            mem = self.observed_state(self.memory())
            text = screen(mem)
            self.events.append(dict(command=command, pc=pc, text=text))
            if pc == targets[0]:
                if 'FIRST PUT DIRECTION AID IN USE' in text or 'NOT IN THIS VERSION YET' in text:
                    raise AssertionError(f'{command} was refused: {text}')
                # Once ground food disappears, the original chooses the pack
                # implicitly. Check the actual source before omitting its key.
                if self.original and pending == ['P'] and command.startswith('EAT '):
                    item = next((number for word, category, number in VOCAB
                                 if category == 2 and word == command[4:]), None)
                    if item is not None and int.from_bytes(
                            mem[0x42AC+2*item:0x42AE+2*item], 'little') == 0:
                        pending.clear()
                if pending:
                    raise AssertionError(f'{command} ended with unused answers {pending}; {text}')
                return
            if self.original:
                # Only known prompts receive answers; unknown screens fail.
                if ('AMOUNT IN OUNCES' in text or 'TIME IN HOURS' in text
                        or 'STATE DESIRED AZIMUTH' in text):
                    if command == 'DRINK WATER' and pending and pending[0] == 'C' \
                            and int.from_bytes(mem[0x42AC+44:0x42AC+46], 'little') == 0:
                        pending.pop(0)  # no ground water: implicit canteen
                    if not pending or not re.fullmatch(r'\d+(?:\.\d+)?', pending[0]):
                        raise AssertionError(f'{command}: unexpected numeric prompt: {text}')
                    key = pending.pop(0)+'\r'
                elif command in ('GET WATER', 'DRINK WATER') and '[Y/N]' in text:
                    if water_decisions:
                        key = water_decisions['river']
                    elif not pending or pending[0] not in ('Y', 'N'):
                        raise AssertionError(f'{command}: missing water source decision: {text}')
                    else:
                        key = pending.pop(0)
                elif '[Y/N]' in text and ('FOLLOW THE RIVER' in text or 'FOLLOW THE SHORE' in text or 'A STRAIGHT LINE' in text):
                    topic = 'river' if 'FOLLOW THE RIVER' in text else 'shore' if 'FOLLOW THE SHORE' in text else 'straight'
                    if decisions:
                        key = decisions.pop(topic, None)
                        if key not in ('Y', 'N'):
                            raise AssertionError(f'{command}: missing explicit {topic} decision: {text}')
                    else:
                        if not pending or pending[0] not in ('Y', 'N'):
                            raise AssertionError(f'{command}: missing explicit shore/river decision: {text}')
                        key = pending.pop(0)
                elif ('GROUND [G]' in text and ('CANTEEN' in text or 'PACK [P]' in text)):
                    if water_decisions:
                        key = water_decisions['source']
                    elif not pending or pending[0] not in ('C', 'P', 'G'):
                        raise AssertionError(f'{command}: unexpected container prompt: {text}')
                    else:
                        key = pending.pop(0)
                elif re.search(r'\bYOUR TRAVEL TIME WAS\s+\d+\s+MINUTES\b', text):
                    key = '\r'  # native travel report, no gameplay decision
                elif 'YOU HAVE BEEN INJURED BY' in text:
                    key = '\r'  # notification; the injury is already applied
                elif 'YOUR HEALTH HAS DETERIORATED SOMEWHAT' in text:
                    key = '\r'
                elif 'I ASSUME YOU MEAN WITH LOTS OF NOISE' in text:
                    key = '\r'
                elif 'YOU ARE SWEATING!' in text or 'YOU ARE SHIVERING!' in text:
                    key = '\r'
                elif re.search(r'THE (BEAR|COUGAR|RATTLESNAKE) HAS DEPARTED', text):
                    key = '\r'
                elif 'THERE IS A BAD SMELL IN THE AIR' in text:
                    key = '\r'
                elif 'YOU HEAR THE DISTANT SOUNDS OF RUNNING' in text:
                    key = '\r'
                elif 'YOU ARE HUNGRY ENOUGH TO EAT A HORSE' in text or 'YOU ARE VERY THIRSTY' in text or 'YOU ARE THIRSTY ENOUGH TO DRINK LAKE' in text:
                    key = '\r'
                elif 'THE SMALL GAME DECIDED TO VAMOOSE' in text:
                    key = '\r'
                elif 'THERE ARE SMALL GAME IN THE AREA' in text:
                    key = '\r'
                elif 'YOU HAVE REACHED A RIVER.' in text or 'YOU HAVE REACHED THE SHORE.' in text:
                    key = '\r'  # arrival notification; decisions are answered separately
                elif re.search(r'THE (BEAR|COUGAR) HAS STOLEN YOUR FOOD', text):
                    key = '\r'  # notification after the original stock mutation
                elif "LET'S HANG YOUR BACKPACK AND THE FOOD" in text:
                    key = '\r'  # acknowledges the requested HANG FOOD action
                elif 'THAT INCLUDES EVERY ITEM IN OR ON YOUR' in text:
                    key = '\r'
                elif "I'M GLAD YOU REMEMBERED." in text:
                    key = '\r'  # native acknowledgement of recovering the suspended pack
                elif "I ASSUME YOU DON'T SPECIFICALLY WANT" in text:
                    key = '\r'
                else:
                    raise AssertionError(f'{command}: unhandled original prompt: {text}')
            elif pc == L['number_idle'] or pending:
                if not pending:
                    raise AssertionError(f'{command}: unexpected port numeric prompt: {text}')
                key = pending.pop(0)+'\r'
            else:
                key = ' '  # port message acknowledgement, never a decision
            self.session.step('key:'+key)
        raise AssertionError(f'{command}: too many prompts')


def run_scenario(scenario, directory, disk=None, stop_on_difference=False):
    directory.mkdir(parents=True, exist_ok=True)
    if disk is None:
        disk = disk_with(directory, original_map())
    # Keep the label addresses with the observations: later builds move them.
    (directory/'labels.json').write_text(json.dumps(dict(L), indent=2))
    provenance = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (HERE/'build/SIERRA.woz', HERE/'build/JOURNEY.dsk', disk)}
    (directory/'manifest.json').write_text(json.dumps(provenance, indent=2))
    checkpoints = []
    try:
        with Driver(HERE/'build/SIERRA.woz', True, directory) as original, Driver(disk, False, directory) as port:
            for index, (command, answers) in enumerate([('START', ())]+SCENARIOS[scenario]):
                if index:
                    original.command(command, answers)
                    port.command(command, answers)
                a, b = original.checkpoint(index), port.checkpoint(index)
                if scenario in TILT_SCENARIOS:
                    # LOOK R turns 90 degrees in the original, 45 in the port
                    # (its scrolled view): a known difference, not the tilt.
                    a.pop('heading')
                    b.pop('heading')
                    signed = lambda v: v - 256 if v & 0x80 else v
                    a['tilt'] = signed(original.last_memory[0xE7])
                    b['tilt'] = signed(port.last_memory[L['tilt']])
                delta = differences(a, b)
                checkpoints.append(dict(command=command, answers=answers, original=a, port=b, differences=delta,
                    raw_inventory=dict(original=original.raw_inventories[-1],
                                       port=port.raw_inventories[-1])))
                print(f'{index:02} {command}: {len(delta)} differences', flush=True)
                for item in delta:
                    print(f'   {item["field"]}: original={item["original"]}, port={item["port"]}', flush=True)
                if delta and stop_on_difference:
                    break
            events = dict(original=original.events, port=port.events)
            state_sources = dict(original=original.state_sources, port=port.state_sources)
    except Exception as error:
        (directory/'report.json').write_text(json.dumps(dict(status='incomplete', error=str(error), checkpoints=checkpoints), indent=2))
        raise
    total = sum(len(c['differences']) for c in checkpoints)
    (directory/'report.json').write_text(json.dumps(dict(status='different' if total else 'equal',
        scope=f'{scenario}; no completed adventure',
        completed_commands=len(checkpoints)-1, planned_commands=len(SCENARIOS[scenario]), sha256=provenance, checkpoints=checkpoints,
        state_sources=state_sources, events=events), indent=2))
    print(f'{len(checkpoints)} checkpoints, {total} differences. Evidence: {directory}')
    return bool(total)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stop-on-difference', action='store_true')
    ap.add_argument('--out', type=Path, default=HERE / 'build/adventure')
    ap.add_argument('--scenario', choices=[*SCENARIOS, 'all'], default='opening')
    args = ap.parse_args()
    directory = args.out.resolve()
    if args.scenario != 'all':
        raise SystemExit(run_scenario(args.scenario, directory, stop_on_difference=args.stop_on_difference))
    results = {}
    directory.mkdir(parents=True, exist_ok=True)
    # Freeze one port disk for the entire suite, including the common map.
    disk = disk_with(directory, original_map())
    for scenario in SCENARIOS:
        print(f'Comparing {scenario}', flush=True)
        try:
            failed = run_scenario(scenario, directory/scenario, disk, args.stop_on_difference)
            results[scenario] = 'different' if failed else 'equal'
        except Exception as error:
            print(f'{scenario}: incomplete: {error}', flush=True)
            results[scenario] = 'incomplete'
    (directory/'index.json').write_text(json.dumps(results, indent=2))
    raise SystemExit(any(status != 'equal' for status in results.values()))


if __name__ == '__main__':
    main()
