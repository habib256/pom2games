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

OPENING = [('WEAR PARKA', ()),
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
}
FLOATS = {'hour': ('s_hour', 0x4C57), 'elapsed': ('s_elap', 0x4C61),
          'date': ('s_date', 0x4C89), 'health': ('s_health', 0x4C34),
          'body': ('s_body', 0x4C70), 'since_drink': ('s_drink', 0x49CD+75),
          'since_meal': ('s_eat', 0x49CD+80), 'since_rest': ('s_rest', 0x49CD+85),
          'water_deficit': ('s_defw', 0x4950+105),
          'food_deficit': ('s_deff', 0x4950+110),
          'rest_deficit': ('s_defr', 0x4950+115)}


def original_map():
    raw = (HERE / 'build/files/TOPO.B').read_bytes()
    h = [[round(v) for v in row] for row in topo.heightmap(raw)]
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
    return mkmap.map_bin(h, water, (raw[0x84], raw[0x83]),
                         (raw[0x81], raw[0x80]), round(128*560/360),
                         declination=int.from_bytes(raw[0xA9:0xAA], 'little', signed=True))


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
        value['items'] = list(mem[L['it_place']+1:L['it_place']+76])
        for title, prefix in [('ground', 'it_gnd'), ('pack', 'it_pack'), ('ounces', 'it_oz')]:
            value[title] = [mem[L[prefix+'_lo']+i] + 256*mem[L[prefix+'_hi']+i]
                            for i in range(22, 38)]
    return value


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
                base = 1 if name == 'items' else 22
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

    def checkpoint(self, index):
        kind = 'original' if self.original else 'port'
        memory = self.memory()
        source = 'RAM'
        if self.original and memory[0x4D00:0x4D03] != bytes.fromhex('4c3c4d'):
            (self.directory / f'{kind}-{index:03}.raw.bin').write_bytes(memory)
            state = None
            for hexdata in re.findall(r'^watch 103E .* mem=([0-9A-F]+)$', self.session.out, re.M):
                candidate = bytes.fromhex(hexdata)
                if candidate[0xD00:0xD03] == bytes.fromhex('4c3c4d'):
                    state = candidate
            if state is None:
                raise AssertionError('Original state is paged out and no valid pre-save observation exists')
            merged = bytearray(memory)
            merged[0x4000:0x5000] = state
            memory = bytes(merged)
            source = 'observed before original pages state to disk'
        self.state_sources.append(source)
        (self.directory / f'{kind}-{index:03}.bin').write_bytes(memory)
        self.session.step(f'shot:{self.directory / f"{kind}-{index:03}.png"}')
        return normalized(memory, self.original)

    def command(self, command, answers):
        self.session.step('key:'+command+'\r')
        pending = list(answers)
        if not self.original and command == 'DRINK WATER':
            pending = pending[1:]  # port currently selects the canteen implicitly
        if not self.original and command.startswith('EAT '):
            pending = pending[:1]  # port currently selects the pack implicitly
        for _ in range(16):
            self.session.step('wait:1')
            targets = (0xB0E2, 0xFD1B) if self.original else (L['idle'], L['number_idle'], L['wait_key'])
            result = self.session.step('until:'+','.join(f'{a:04X}' for a in targets)+':20000')
            pc = int(re.search(r'PC=([0-9A-F]{4})', result.out)[1], 16)
            mem = self.memory()
            text = screen(mem)
            self.events.append(dict(command=command, pc=pc, text=text))
            if pc == targets[0]:
                # Once ground food disappears, the original chooses the pack
                # implicitly. Check the actual source before omitting its key.
                if self.original and pending == ['P'] and command == 'EAT CHEESE' \
                        and int.from_bytes(mem[0x42AC+56:0x42AC+58], 'little') == 0:
                    pending.clear()
                if pending:
                    raise AssertionError(f'{command} ended with unused answers {pending}; {text}')
                return
            if self.original:
                # Only known prompts receive answers; unknown screens fail.
                if 'AMOUNT IN OUNCES' in text or 'TIME IN HOURS' in text:
                    if command == 'DRINK WATER' and pending and pending[0] == 'C' \
                            and int.from_bytes(mem[0x42AC+44:0x42AC+46], 'little') == 0:
                        pending.pop(0)  # no ground water: implicit canteen
                    if not pending or not pending[0].isdigit():
                        raise AssertionError(f'{command}: unexpected numeric prompt: {text}')
                    key = pending.pop(0)+'\r'
                elif ('GROUND [G]' in text and ('CANTEEN' in text or 'PACK [P]' in text)):
                    if not pending or pending[0] not in ('C', 'P', 'G'):
                        raise AssertionError(f'{command}: unexpected container prompt: {text}')
                    key = pending.pop(0)
                elif re.search(r'\bYOUR TRAVEL TIME WAS\s+\d+\s+MINUTES\b', text):
                    key = '\r'  # native travel report, no gameplay decision
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


def run_scenario(scenario, directory, disk=None):
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
                delta = differences(a, b)
                checkpoints.append(dict(command=command, original=a, port=b, differences=delta))
                print(f'{index:02} {command}: {len(delta)} differences', flush=True)
                for item in delta:
                    print(f'   {item["field"]}: original={item["original"]}, port={item["port"]}', flush=True)
            events = dict(original=original.events, port=port.events)
            state_sources = dict(original=original.state_sources, port=port.state_sources)
    except Exception as error:
        (directory/'report.json').write_text(json.dumps(dict(status='incomplete', error=str(error), checkpoints=checkpoints), indent=2))
        raise
    total = sum(len(c['differences']) for c in checkpoints)
    (directory/'report.json').write_text(json.dumps(dict(status='different' if total else 'equal',
        scope=f'{scenario}; no completed adventure', sha256=provenance, checkpoints=checkpoints,
        state_sources=state_sources, events=events), indent=2))
    print(f'{len(checkpoints)} checkpoints, {total} differences. Evidence: {directory}')
    return bool(total)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=HERE / 'build/adventure')
    ap.add_argument('--scenario', choices=[*SCENARIOS, 'all'], default='opening')
    args = ap.parse_args()
    directory = args.out.resolve()
    if args.scenario != 'all':
        raise SystemExit(run_scenario(args.scenario, directory))
    results = {}
    directory.mkdir(parents=True, exist_ok=True)
    # Freeze one port disk for the entire suite, including the common map.
    disk = disk_with(directory, original_map())
    for scenario in SCENARIOS:
        print(f'Comparing {scenario}', flush=True)
        try:
            failed = run_scenario(scenario, directory/scenario, disk)
            results[scenario] = 'different' if failed else 'equal'
        except Exception as error:
            print(f'{scenario}: incomplete: {error}', flush=True)
            results[scenario] = 'incomplete'
    (directory/'index.json').write_text(json.dumps(results, indent=2))
    raise SystemExit(any(status != 'equal' for status in results.values()))


if __name__ == '__main__':
    main()
