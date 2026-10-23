#!/usr/bin/env python3
"""WARGALAGA II fast tier: volume, boot, cadence, oracle, input, exits.

The //e parts run on a2shot (enhanced //e, 128 KB, NTSC and PAL); an
NMOS Apple II+ must get the refusal message. The logic is compared with
tools/model.py at every step: inputs are poked at logic_step's entry and
the state is read at logic_done.
"""
import argparse
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'wargalagaii'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test
import model

SYS_NAMES = ('WG2.SYSTEM', 'WG2.SYS')


def volume(disk, build):
    import importlib.util
    spec = importlib.util.spec_from_file_location('prodos_read', ROOT / 'dev/tools/prodos/read_volume.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(disk.read_bytes())
    assert image.header()['name'] == 'WARGALAGAII'
    assert image.header()['blocks'] == 280 and len(image.d) == 143360
    entries = {e[1:1 + (e[0] & 15)].decode(): e for e in image.entries(2)}
    assert set(entries) == {'PRODOS', *SYS_NAMES}, sorted(entries)
    assert all(entries[n][0x10] == 0xFF for n in entries)
    assert image.read(entries['PRODOS']) == (ROOT / 'dev/tools/prodos/PRODOS').read_bytes()
    for name in SYS_NAMES:
        assert image.read(entries[name]) == (build / name).read_bytes(), name
    assert image.d[:1024] == (ROOT / 'dev/tools/prodos/boot.bin').read_bytes()
    print('PASS bootable ProDOS volume /WARGALAGAII, WG2.SYSTEM + WG2.SYS round trip')


def text(result, occurrence=0):
    """Text page 1 as ASCII (rows in memory order, bit 7 stripped)."""
    return bytes(b & 0x7F for b in result.mem(0x400, 0x400, occurrence)).decode('latin-1')


def word(data):
    return data[0] | data[1] << 8


def cadence(disk, L, pal):
    """Game speed = refreshes / 2 from the start (entry waves included:
    a late frame there must not slow the game), and no late frame once the
    formation is seated (from refresh 1200)."""
    names = ('frame_count', 'step_count', 'late_count')
    peeks = [L.peek(n, 2) for n in names]
    r = a2test.run(disk, [L.until('game_tick', 3000), *peeks, 'wait:1200', *peeks,
                          'wait:2000', *peeks], iie=True, pal=pal)
    at = [[word(r.mem(L[n], 2, k)) for n in names] for k in range(3)]
    frames, steps, late = (at[2][i] - at[0][i] for i in range(3))
    assert abs(steps - 3200 // 2) <= 1, (steps, 'game speed')
    steady = [at[2][i] - at[1][i] for i in range(3)]
    assert steady[2] == 0, f'{steady[2]} late frames with the formation seated'
    assert abs(steady[0] - 1000) <= 1, steady
    print(f'PASS {"PAL" if pal else "NTSC"} cadence: {steps} logic steps in 3200 refreshes '
          f'({late} late frames during the entry waves); seated: {steady[0]} frames in 2000, none late')


def bench(disk, L, frames=300):
    """TODO.md lot 2 scene: 40 seated aliens, divers, 10 shots fired
    continuously: no late frame."""
    fire = [L.until('logic_step', 10), L.poke('fire_req', 0x80), L.until('logic_done', 10)]
    steps = [L.until('game_tick', 3000), L.poke('shot_limit', 10), 'wait:1200']
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2)] + fire * frames
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2), L.peek('shot_y', 10),
              L.peek('a_state', model.NALIENS)]
    r = a2test.run(disk, steps, iie=True, timeout=600)
    late = word(r.mem(L['late_count'], 2, 1)) - word(r.mem(L['late_count'], 2, 0))
    count = word(r.mem(L['frame_count'], 2, 1)) - word(r.mem(L['frame_count'], 2, 0))
    shots = sum(map(bool, r.mem(L['shot_y'], 10)))
    states = r.mem(L['a_state'], model.NALIENS)
    assert shots >= 9 and states.count(model.FORM) >= 34, (shots, states.hex())
    assert late == 0, f'{late} late frames out of {count}'
    print(f'PASS bench: {count} frames with {shots} shots, {model.NALIENS - states.count(model.FORM)} '
          'aliens off their seats, none late')
    # One small alien: draw (STA, seated), EOR (flying, both ways), erase.
    costs = []
    for name in ('alien_sta', 'alien_eor', 'alien_clr'):
        r = a2test.run(disk, [L.until('game_tick', 3000), 'wait:1200',
                              L.until(name, 60), L.until(name + '_done', 1)], iie=True)
        costs.append(r.cycles[-1] - r.cycles[-2])
    print(f'PASS 14x8 alien: STA {costs[0]}, EOR {costs[1]}, zeros {costs[2]} cycles')
    assert costs[0] <= 650 and costs[2] <= 400, costs


def oracle(disk, L, count=2000, every=1):
    """Poke random inputs at each logic step; compare the state with the
    model at logic_done (every `every` steps, always the last)."""
    rng = random.Random(1983)
    game = model.Game()
    names = [n for n in game.state() if n != 'prng']
    first = min(L[n] for n in names)
    span = max(L[n] + len(v) for n, v in game.state().items() if n != 'prng') - first
    steps, inputs, checked = [L.until('game_tick', 3000)], [], []
    move = 0
    for k in range(count):
        if rng.random() < 0.15:
            move = rng.choice((-1, 0, 1))
        fire = rng.random() < 0.3
        inputs.append((move, fire))
        steps += [L.until('logic_step', 10), L.poke('move_dir', move & 0xFF),
                  L.poke('fire_req', 0x80 if fire else 0), L.until('logic_done', 10)]
        if k % every == every - 1 or k == count - 1:
            steps += [f'peek:{first:04X}:{span}', L.peek('prng_lo', 2)]
            checked.append(k)
    r = a2test.run(disk, steps, iie=True, timeout=900)
    seen = 0
    for k, (move, fire) in enumerate(inputs):
        game.step(move, fire)
        if k not in checked:
            continue
        got = r.mem(first, span, seen)
        state = game.state()
        for name in names:
            want = state[name]
            have = got[L[name] - first:L[name] - first + len(want)]
            assert have == want, f'step {k + 1} {name}: 6502 {have.hex()} model {want.hex()}'
        assert r.mem(L['prng_lo'], 2, seen) == state['prng'], f'step {k + 1} prng'
        seen += 1
    assert game.entry_w == model.ROWS and model.FORM in game.a_state and model.DIVE in game.a_state
    print(f'PASS logic oracle: {count} steps (waves, formation, dives, ship, shots, stars) '
          '== tools/model.py')


def play(disk, L):
    tick = L.until('game_tick', 3000)
    r = a2test.run(disk, [tick, L.peek('ship_c'), 'key:\\>', 'key:\\>', 'wait:4', L.peek('ship_c'),
                          'key:\\<', 'wait:4', L.peek('ship_c'),
                          'key: ', 'wait:2', L.peek('shot_y', model.MAX_SHOTS),
                          'btn:0,1', 'wait:4', 'btn:0,0', 'wait:2', L.peek('shot_y', model.MAX_SHOTS),
                          'key:\t', 'joy:1,0', 'wait:20', L.peek('ship_c'),
                          'joy:-1,0', 'wait:120', L.peek('ship_c'), 'joy:0,0', 'wait:10', L.peek('ship_c'),
                          'wait:10', L.peek('ship_c')], iie=True)
    ship = [r.mem(L['ship_c'], 1, k)[0] for k in range(6)]
    assert ship[1] > ship[0] and ship[2] < ship[1], ('arrow keys', ship[:3])
    shots = [r.mem(L['shot_y'], model.MAX_SHOTS, k) for k in range(2)]
    assert sum(map(bool, shots[0])) == 1, ('space fires', shots[0].hex())
    assert sum(map(bool, shots[1])) == 2, ('open apple fires', shots[1].hex())
    assert ship[3] > ship[2] + 10, ('joystick right', ship)
    assert ship[4] == 0, ('joystick left to the wall', ship)
    assert ship[5] == ship[4], ('centred stick holds', ship)
    print('PASS arrows move, SPACE and open apple fire, TAB -> joystick moves and stops')


def exits(disk, L):
    for how in ('key:\\e', 'reset'):
        r = a2test.run(disk, [L.until('game_tick', 3000), 'wait:30', how, 'wait:300',
                              'peek:C01A', 'peek:BF31:16', 'peek:400:1024'], iie=True)
        assert r.mem(0xC01A, 1)[0] & 0x80, 'text mode'
        devices = r.mem(0xBF31, 16)
        units = devices[1:2 + devices[0]]
        assert any(u & 0xF0 == 0xB0 for u in units), ('/RAM back in the device list', units.hex())
        assert 'BITSY' in text(r), 'ProDOS launcher'
        print(f'PASS {"ESC" if how.startswith("key") else "Ctrl-RESET"} -> text, /RAM rebuilt, ProDOS QUIT launcher')


def nmos(disk):
    r = a2test.run(disk, ['wait:1500', 'peek:400:1024'], emulator=a2test.A2SHOT)
    assert 'NEEDS A 65C02' in text(r), text(r)
    print('PASS NMOS 6502 (Apple II+): refusal message, no crash')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    a = ap.parse_args()
    volume(a.disk, a.labels.parent)
    if not a2test.have_a2shot('//e execution'):
        return
    L = a2test.labels(a.labels, strip=True)
    cadence(a.disk, L, pal=False)
    cadence(a.disk, L, pal=True)
    oracle(a.disk, L)
    bench(a.disk, L)
    play(a.disk, L)
    exits(a.disk, L)
    nmos(a.disk)


if __name__ == '__main__':
    main()
