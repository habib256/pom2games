#!/usr/bin/env python3
"""WARGALAGA II long tests (make test-long, a few minutes more).

Autopilot (tools/autopilot.py, on the model): levels 1, 25 and 100 can be
finished from a new game (3 lives, no armour), the boss of level 100 too.
Worst levels (a2shot, //e): the hardest levels played by a cheating player
(invulnerable, triple shot, 10 shots, autofire) for FRAMES frames; the late
frames (shown a refresh after their deadline) stay under LATE_MAX of them,
LATE_MAX_MB with the Mockingboard (PT3 music in the timer interrupt, ~1 600
cycles 25 times a second): the frame rate drops there, the game's speed
does not (the logic steps by refresh pairs).

    tests/test_long.py [--frames N]
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'wargalagaii'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test
from boot import boot
import autopilot
import test_game

# The scene is chaotic: shifting its start by 2-10 refreshes gives 46 to
# 76 late frames out of ~570 on level 97 (bug hunt 6). Bounds with room:
LATE_MAX = 0.15            # without a card (measured up to 13 %)
LATE_MAX_MB = 0.28         # with the card, PT3 music (measured up to 22 %)
WORST = ((96, 'level 97: 7 divers, fastest bombs'), (24, 'boss of level 25'),
         (99, 'boss of level 100'))


def word(data):
    return int.from_bytes(data, 'little')


def autopilots():
    for level in (1, 25, 100):
        ok, steps, lives = autopilot.play(level - 1)
        assert ok, f'level {level}: the autopilot did not finish it ({steps} steps)'
        print(f'PASS autopilot: level {level} finished in {steps} steps, {lives} lives left')


def worst(disk, L, start, why, frames, mockingboard=False):
    steps = [L.until('main', 3000), L.poke('front_skip', 1), L.poke('start_level', start), L.until('game_tick', 3000),
             L.poke('weapon', 2), L.poke('shot_limit', 10), L.poke('noshop', 1), 'wait:300']
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2)]
    for k in range(frames // 20):
        steps += [L.poke('invul_t', 60), L.poke('fire_held', 0x80), L.poke('autofire_t', 255),
                  'press:' + ' <> '[k % 4].replace('<', '\\<').replace('>', '\\>'), 'wait:40']
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2)]
    r = a2test.run(disk, steps, iie=True, mockingboard=mockingboard, timeout=1200)
    late = word(r.mem(L['late_count'], 2, 1)) - word(r.mem(L['late_count'], 2, 0))
    count = word(r.mem(L['frame_count'], 2, 1)) - word(r.mem(L['frame_count'], 2, 0))
    why += ', Mockingboard' if mockingboard else ''
    assert late <= (LATE_MAX_MB if mockingboard else LATE_MAX) * count, f'{why}: {late} late frames out of {count}'
    print(f'PASS worst level, {why}: {late} late frames out of {count}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    ap.add_argument('--frames', type=int, default=600)
    a = ap.parse_args()
    autopilots()
    if not a2test.have_a2shot('worst levels'):
        return
    L = a2test.labels(a.labels, strip=True)
    # the last loop: level 100 of loop 255 shot through, loop 255 again
    # (bug hunt 6: 255 + 1 was loop 0, the game easy again)
    game, seen = test_game.level_oracle(a.disk, L, 99, 6000, every=30, seed=12, cheats=[('loop', 255)])
    assert seen[0] == (99, 255) and seen[1:] and all(p == 255 for l, p in seen), seen
    print(f'PASS level oracle, loop 255: levels {[l + 1 for l, p in seen]} of loop 255 == model')
    for mockingboard in (False, True):
        for start, why in WORST:
            worst(a.disk, L, start, why, a.frames, mockingboard)


if __name__ == '__main__':
    main()
