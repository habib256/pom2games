#!/usr/bin/env python3
"""Measure identical native GAME recovery, COOK 8 OZ and EAT 8 OZ.

Pass a frozen directory containing NEOWILDERNESSXL.po and its wild.lbl.
The isolated emulator receives a deterministic bow/prey/fire fixture before
counting. Every counted action uses joystick axes/buttons. No disk is patched.
Guest cycles include fixed input pulses and settling, excluding operator time.
"""
import argparse
import hashlib
import json
from pathlib import Path
import common
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('snapshot', type=Path)
parser.add_argument('--output', type=Path, help='write measurements and native state snapshots as JSON')
args = parser.parse_args()
root = args.snapshot.resolve()
common.L.clear()
common.L.update(common.a2test.labels(root / 'wild.lbl'))
common.DISK = root / 'NEOWILDERNESSXL.po'
from common import L
from test_joystick_journey import GamePortSession, byte, rows, grid, saved_state, IDLE, READY
from test_survival_flows import choose_source, stock
from test_forage import seed_for
import test_joystick_journey as journey
# Read SAVE ranges from this snapshot, rather than the current build.
save_module = common.a2test.prodos_files(common.DISK)['NEOWILD.SAV'][2]
at = L['sv_ranges'] - 38400
journey.RANGES = []
while (address := int.from_bytes(save_module[at:at + 2], 'little')):
    journey.RANGES.append((address, int.from_bytes(save_module[at + 2:at + 4], 'little')))
    at += 4

def event(s, control, ready=READY):
    axes = {'up': '0,-1', 'down': '0,1', 'left': '-1,0', 'right': '1,0'}
    start, stop = ('joy:' + axes[control], 'joy:0,0') if control in axes else (f"btn:{(0 if control == 'ok' else 1)},1", f"btn:{(0 if control == 'ok' else 1)},0")
    s.step(start)
    s.step('wait:8')
    s.step(stop)
    wait = ready if ready == L.until('menu_key', 60000) else f"until:{L['idle']:04X},{L['keyboard_wait']:04X}:60000"
    s.step(wait)
    s.step('wait:6')
    s.step(wait)
journey.event = event

class Counted(GamePortSession):
    count = 0
    counting = False
    latest = 0
    timeline = {}

    def step(self, step):
        if self.counting and (step.startswith('joy:') and step != 'joy:0,0' or (step.startswith('btn:') and step.endswith(',1'))):
            self.count += 1
        r = super().step(step)
        if r.cycles:
            self.latest = r.cycles[-1]
        return r

def snap(s):
    names = [('px', 6), ('s_hour', L['s_t0'] + 5 - L['s_hour']), ('fg_b1', 6), ('fg_b2', 6), ('fg_gl', 6), ('fg_gh', 6), ('fg_pl', 6), ('fg_ph', 6), ('fg_skin', 1), ('weather_seed', 4), ('it_pack_lo', 76), ('it_pack_hi', 76), ('injury_active', 15)]
    result = {n: s.step(L.peek(n, k)).data.hex() for n, k in names}
    result['saved_state'] = saved_state(s).hex()
    return result

def dump(s, title):
    s.timeline[title] = {'gestures': s.count, 'cycles': s.latest}
    print(title, s.count, '\n' + '\n'.join(rows(s)[20:]), flush=True)
with Counted(root / 'NEOWILDERNESSXL.po', menu=False) as s:
    menu = L.until('menu_key', 60000)
    s.step(menu)
    event(s, 'ok', menu)
    event(s, 'ok', IDLE)
    for n, v in [('nature_frequency', 0), ('resource_seen', 1), ('cr_b1', 3), ('fg_use', 4), ('camp_use', 0), ('care_tools', 0), ('light', 1), ('fire_on', 1), ('fire_near', 1)]:
        s.step(L.poke(n, v))
    for axis in ('x', 'y'):
        s.step(L.poke('fg_' + axis, byte(s, 'p' + axis, 1)))
    s.step(L.poke('fg_b2', 0, 4))
    s.step(L.poke('fg_b2', 255, 5))
    for n in ('fg_b1', 'fg_gl', 'fg_gh', 'fg_pl', 'fg_ph'):
        s.step(L.poke(n, 0, 4))
    event(s, 'right', IDLE)
    event(s, 'left', IDLE)
    seed = seed_for(0.001, position=1)
    for i in range(4):
        s.step(L.poke('weather_seed', seed >> 8 * i & 255, i))
    grid(s, 'KILL', ready=READY)
    for _ in range(4):
        if byte(s, 'fg_b2', 4) == 1:
            break
        event(s, 'ok', READY)
    assert byte(s, 'fg_b2', 4) == 1, rows(s)
    start = snap(s)
    s.counting = True
    dump(s, 'POST KILL')
    if 'SKIN THIS CARCASS' in ' '.join(rows(s)):
        event(s, 'ok', READY)
    else:
        grid(s, 'SKIN', ready=IDLE)
        choose_source(s, 80, READY)
    dump(s, 'POST SKIN')
    if 'GET THIS MEAT' in ' '.join(rows(s)):
        event(s, 'ok', READY)
    else:
        grid(s, 'GET', ready=IDLE)
        choose_source(s, 80, READY)
    dump(s, 'POST GET')
    event(s, 'ok', READY)
    dump(s, 'COOK FORM')
    for _ in range(2):
        event(s, 'down')
    event(s, 'ok')
    dump(s, 'COOK DURATION')
    for _ in range(3):
        event(s, 'right')
    event(s, 'ok')
    dump(s, 'POST COOK')
    cooked = snap(s)
    cookcount = s.count
    assert stock(s, 'fg_g', 4) == 8, (stock(s, 'fg_g', 4), rows(s))
    event(s, 'ok')
    dump(s, 'EAT FORM')
    event(s, 'ok', IDLE)
    dump(s, 'POST EAT')
    assert stock(s, 'fg_g', 4) == 0 and stock(s, 'fg_p', 4) == 2, rows(s)
    result = {'start': start, 'cooked': cooked, 'end': snap(s), 'cook_gestures': cookcount, 'gestures': s.count, 'timeline': s.timeline}
    result['image_sha256'] = hashlib.sha256(common.DISK.read_bytes()).hexdigest()
    result['scope'] = 'Native successful bow kill result through SKIN, PACK, COOK 8 OZ for 30 MIN and EAT 8 OZ; fire available before counting'
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Hunt result -> SKIN -> PACK -> COOK 8 OZ -> EAT 8 OZ: {s.count} joystick gestures')
