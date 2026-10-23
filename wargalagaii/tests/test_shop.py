#!/usr/bin/env python3
"""WARGALAGA II shop (lot 7): driven by keys and stick on a2shot, checked
against tools/model.py (buy, shop_exit).

Each scene starts at level 4 (the last of the first pack) with credits and
marks poked, waits for the shop screen (sh_loop: the overlay copied from aux
memory to $4000), plays its inputs, leaves, and compares the game state with
the model's from the same state at the opening.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'wargalagaii'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test
import model

M = model
FIELDS = {'credits': 2, 's_level': 1, 'shot_limit': 1, 'weapon': 1, 'autofire_t': 2, 'armour': 1,
          'lives': 1, 'marks': 1, 'mark_dark': 1, 'rank': 1, 't_level': 1, 'level': 1, 'loop': 1,
          'shop': 1}
LEAVE = len(M.ITEMS)


def bcd(v):
    return int(f'{v:x}')


def read(r, L, k):
    st = {}
    for name, n in FIELDS.items():
        b = r.mem(L[name], n, k)
        st[name] = int.from_bytes(b, 'little')
    st['credits'] = bcd(st['credits'])
    return st


def to_bcd(v):
    return int(str(v), 16)


def scene(disk, L, name, credits, inputs, pokes=(), mockingboard=False, joystick=False):
    """inputs: a2shot keys ('\\r', '\\>', '\\<', '\\e') or ('joy', y) /
    ('btn',): played one by one. The model replays them on the cursor."""
    steps = [L.until('main', 3000), L.poke('start_level', 3), L.until('game_tick', 3000)]
    c = to_bcd(credits)
    steps += [L.poke('credits', c & 255), L.poke('credits', c >> 8, 1)]
    steps += [L.poke(n, v) for n, v in pokes]
    if joystick:
        steps += ['key:\t', 'wait:4']
    for _ in range(40):
        steps += [L.poke('invul_t', 60), 'wait:40']
    steps += [L.until('sh_loop', 3000), 'wait:4'] + [L.peek(n, k) for n, k in FIELDS.items()]
    for inp in inputs:
        if isinstance(inp, tuple) and inp[0] == 'joy':
            steps += [f'joy:0,{inp[1]}', 'wait:3', 'joy:0,0', 'wait:12']
        elif inp == ('btn',):
            steps += ['btn:0,1', 'wait:3', 'btn:0,0', 'wait:4']
        else:
            steps += [f'key:{inp}', 'wait:4']
    steps += ['wait:30'] + [L.peek(n, k) for n, k in FIELDS.items()]
    r = a2test.run(disk, steps, iie=True, mockingboard=mockingboard, timeout=900)
    opened, after = read(r, L, 0), read(r, L, 1)
    assert opened['shop'] == 1 and opened['level'] == 3, opened
    g = M.Game(0)
    for n, v in opened.items():
        setattr(g, n, v)
    cur, bought, refused = 0, [], 0
    for inp in inputs:
        key = inp[1] if isinstance(inp, tuple) and inp[0] == 'joy' else inp
        if key in ('\\<', -1):
            cur = (cur - 1) % (LEAVE + 1)
        elif key in ('\\>', 1):
            cur = (cur + 1) % (LEAVE + 1)
        elif inp in ('\\r', ('btn',)):
            if cur == LEAVE:
                break
            if g.buy(cur):
                bought.append(M.ITEMS[cur][0])
            else:
                refused += 1
        elif inp == '\\e':
            break
    g.shop_exit()
    want = {n: getattr(g, n) for n in FIELDS}
    assert after == want, (name, {n: (after[n], want[n]) for n in FIELDS if after[n] != want[n]})
    print(f'PASS shop, {name}: bought {", ".join(bought) or "nothing"}'
          f'{f", {refused} refused" if refused else ""}; credits {opened["credits"]} -> {after["credits"]}, '
          f'rank {opened["rank"]} -> {after["rank"]}, level {after["level"] + 1} next == model')


def speaker_music(disk, L):
    """Without a card the shop plays the tune on the speaker (duet.asm),
    DUET_TICK slices at a time: the flips run, an event lasts its slices
    (2 sixteenths, ~0.24 s), and the keys still answer."""
    import re
    sl = L['sh_sl']
    steps = [L.until('main', 3000), L.poke('start_level', 3), L.until('game_tick', 3000),
             L.poke('credits', 0), L.poke('credits', 0x10, 1)]
    for _ in range(40):
        steps += [L.poke('invul_t', 60), 'wait:40']
    steps += [L.until('sh_loop', 3000), f'tracepc:{L["duet_flip_mel"]:04X}:500:30',
              f'storewatch:{sl:04X}:{sl:04X}', 'wait:120', 'unstorewatch', 'key:\\>', 'wait:6',
              L.peek('sh_cur')]
    r = a2test.run(disk, steps, iie=True, timeout=900)
    flips = len(re.findall(r'^tracepc ', r.out, re.M))   # the melody's speaker flips
    stamps = [int(c) for v, c in re.findall(r'^store \w+ \w+ (\S+) .*cycles=(\d+)', r.out, re.M)
              if v.endswith('>1C')]                  # a new event: sh_sl reloaded
    event = (stamps[-1] - stamps[0]) / (len(stamps) - 1) / 1020484
    assert flips == 500 and abs(event - 0.24) < 0.01 and r.mem(L['sh_cur'], 1)[0] == 1, (flips, event)
    print(f'PASS shop music on the speaker: the voices flip, an event every {event:.3f} s '
          '(two sixteenths), the cursor still moves')


def no_shop(disk, L):
    """Under 50 credits: no shop, the next level at once."""
    steps = [L.until('main', 3000), L.poke('start_level', 3), L.until('game_tick', 3000),
             L.poke('credits', 0x49), L.poke('credits', 0, 1)]
    for _ in range(40):
        steps += [L.poke('invul_t', 60), 'wait:40']
    steps += [L.peek('level'), L.peek('shop'), L.peek('sh_cur')]
    r = a2test.run(disk, steps, iie=True, timeout=900)
    assert r.mem(L['level'], 1)[0] == 4 and r.mem(L['shop'], 1)[0] == 0, (r.mem(L['level'], 1), r.mem(L['shop'], 1))
    print('PASS no shop under 50 credits: level 5 next')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    a = ap.parse_args()
    if not a2test.have_a2shot('shop'):
        return
    L = a2test.labels(a.labels, strip=True)
    R, N, P = '\\r', '\\>', '\\<'
    # speed, bullet, double, triple (over double), less speed, life (max 4),
    # life refused, then too poor for the time; with the card (music on)
    scene(a.disk, L, 'buying, the card on', 3000,
          [R, N, R, N, R, N, N, R, P, R, N, N, N, N, R, R, N, N, R, '\\e'], mockingboard=True)
    # the last mark bought: rank up on leaving through LEAVE
    scene(a.disk, L, 'rank marker', 1300, [N] * 8 + [R] + [N, N, R], pokes=[('marks', 62)])
    # the dark mark: rank down
    scene(a.disk, L, 'dark mark', 100, ['\\e'], pokes=[('mark_dark', 1), ('rank', 2)])
    # the stick: down twice, button (double shot), up, button (bullet), ESC
    scene(a.disk, L, 'stick', 500, [('joy', 1), ('joy', 1), ('btn',), ('joy', -1), ('btn',), '\\e'],
          joystick=True)
    speaker_music(a.disk, L)
    no_shop(a.disk, L)


if __name__ == '__main__':
    main()
