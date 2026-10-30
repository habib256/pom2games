#!/usr/bin/env python3
"""WARGALAGA II sub-games (lot 8) on a2shot, checked against tools/model.py.

Meteor Storm: the 6502's steps against storm_step, step by step (inputs
poked at logic_step, state read at logic_done): a cheating player clears
level 4 with the storm's icon caught, then flies the storm, speeding up and
slowing down, until a rock hits it (no life lost) or it gets through (the
prize); then the teleport and level 5. Memory Station: driven by keys and
stick, the final state == the model's (mem_deal, mem_turn) replaying the
same cards from the deal read at the opening.

    tests/test_subgames.py
"""
import argparse
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'wargalagaii'
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
sys.path.insert(0, str(GAME / 'tests'))
import a2test
from boot import boot
import model
import test_game

M = model


def storm_oracle(disk, L, seed, crash, count=1300, every=3):
    """From level 4 (a kamikaze level), invulnerable until the storm starts;
    crash: no invulnerability in the storm (a rock ends it), else the
    invulnerability holds and the ship gets through."""
    rng = random.Random(seed)
    names = [n for n in M.Game(3).state() if n != 'prng']
    first = min(L[n] for n in names)
    span = max(L[n] + len(v) for n, v in M.Game(3).state().items() if n != 'prng') - first
    cheats = [('weapon', 2), ('shot_limit', 10), ('s_level', 5), ('noshop', 1), ('subgame', 1)]
    steps = [L.until('main', 3000), L.poke('front_skip', 1), L.poke('start_level', 3), L.until('game_tick', 3000)]
    sim = M.Game(3)
    plan = []
    move, held = 0, 1
    stormed = through = crashed = 0
    top = 0
    for k in range(count):
        if rng.random() < 0.2:
            move = rng.choice((-1, 0, 1))
        if sim.storm and rng.random() < (0.03 if held else 0.1):
            held ^= 1                    # speeding up, slowing down
        pokes = list(cheats) if k == 0 else []
        if (not sim.storm or not crash) and sim.invul_t < 5:
            pokes.append(('invul_t', 60))
        for n, v in pokes:
            setattr(sim, n, v)
        was = sim.storm
        sim.step(move, True, bool(held) or not sim.storm)
        top = max(top, sim.m_speed)
        stormed |= sim.storm
        if was and not sim.storm:
            crashed += sim.m_crash
            through += not sim.m_crash
        plan.append((move, held or not was, pokes))
        if sim.station:
            sim.station_exit()
        if sim.shop:
            sim.shop_exit()
        steps += [L.until('logic_step', 10), L.poke('move_dir', move & 0xFF), L.poke('fire_req', 0x80),
                  L.poke('fire_held', 0x80 if plan[-1][1] else 0)]
        steps += [L.poke(n, v >> 8 * b, b) for n, v in pokes for b in range(1 + (v > 255))]
        steps.append(L.until('logic_done', 10))
        if k % every == every - 1 or k == count - 1:
            steps += [f'peek:{first:04X}:{span}', L.peek('prng_lo', 2)]
    assert stormed and (crashed if crash else through), (stormed, crashed, through)
    r = a2test.run(disk, steps, iie=True, timeout=1500)
    game = M.Game(3)
    seen = 0
    for k, (move, held, pokes) in enumerate(plan):
        for n, v in pokes:
            setattr(game, n, v)
        game.step(move, True, bool(held))
        if game.station:
            game.station_exit()
        if game.shop:
            game.shop_exit()
        if k % every == every - 1 or k == count - 1:
            got = r.mem(first, span, seen)
            for name, want in game.state().items():
                if name == 'prng':
                    assert r.mem(L['prng_lo'], 2, seen) == want, f'storm: step {k + 1} prng'
                    continue
                have = got[L[name] - first:L[name] - first + len(want)]
                assert have == want, f'storm: step {k + 1} {name}: 6502 {have.hex()} model {want.hex()}'
            seen += 1
    how = 'a rock hit it (no life lost)' if crash else f'through at top speed {top}'
    print(f'PASS Meteor Storm oracle: {count} steps == model (level 4 cleared, the storm, {how}, '
          f'teleport, level {game.level + 1}; score {game.score}, credits {game.credits})')


# --- Memory Station ---------------------------------------------------------
FIELDS = {'credits': 2, 'score': 3, 's_level': 1, 'shot_limit': 1, 'weapon': 1, 't_level': 1,
          'armour': 1, 'lives': 1, 'extra_bits': 1, 'mult': 1, 'mult_t': 2, 'level': 1,
          'station': 1, 'shop': 1, 'm_round': 1, 'm_pairs': 1, 'm_first': 1, 'm_card': M.MEM_CELLS,
          'm_up': M.MEM_CELLS, 'prng': 2}


def read(r, L, k):
    st = {}
    for name, n in FIELDS.items():
        label = 'prng_lo' if name == 'prng' else name
        st[name] = r.mem(L[label], n, k)
    return st


def model_of(st, start):
    """A model in the state read at the opening."""
    g = M.Game(start)
    for n, v in st.items():
        if n in ('m_card', 'm_up'):
            setattr(g, n, list(v))
        elif n == 'prng':
            g.prng = v[0] | v[1] << 8
        elif n == 'score':
            g.score = int(f'{v[2]:02x}{v[1]:02x}{v[0]:02x}')
        elif n == 'credits':
            g.credits = int(f'{v[1]:02x}{v[0]:02x}')
        else:
            setattr(g, n, int.from_bytes(v, 'little'))
    return g


def station_open(L, credits, pokes=(), joystick=False):
    """Steps: level 4 with the station's icon caught, until its screen."""
    c = int(str(credits), 16)
    steps = [L.until('main', 3000), L.poke('front_skip', 1), L.poke('start_level', 3), L.until('game_tick', 3000),
             L.poke('subgame', 2), L.poke('credits', c & 255), L.poke('credits', c >> 8, 1)]
    steps += [L.poke(n, v) for n, v in pokes]
    if joystick:
        steps += ['key:\t', 'wait:4']
    for _ in range(40):
        steps += [L.poke('invul_t', 60), 'wait:40']
    # (the station opened during the waits: a full clock for the scene)
    return steps + [L.until('mem_loop', 3000), L.poke('mem_sec', 90), 'wait:4']


def walk(g, cx, cy, cell):
    """Keys from the cursor to a card: down (K) then right (L), wrapping."""
    w, h = g.mem_grid()
    tx, ty = cell % w, cell // w
    keys = ['K'] * ((ty - cy) % h) + ['L'] * ((tx - cx) % w)
    return keys, tx, ty


def station_scene(disk, L, name, credits, plan, pokes=(), joystick=False, waits=(), shop=False):
    """plan(g) -> the cards to turn, from the model at the opening (it may
    play them on g to know the next grid). Keys: K / L to walk, RETURN to
    turn; a pause after a miss or a cleared grid."""
    steps = station_open(L, credits, pokes, joystick) + [L.peek(n if n != 'prng' else 'prng_lo', k)
                                                          for n, k in FIELDS.items()]
    r = a2test.run(disk, steps, iie=True, timeout=900)
    st0 = read(r, L, 0)
    assert st0['station'][0] == 1, st0
    g = model_of(st0, 3)
    cards, end = plan(model_of(st0, 3))
    keys, results, cx, cy = [], [], 0, 0
    for cell in cards:
        walk_keys, cx, cy = walk(g, cx, cy, cell)
        keys += [('key', k) for k in walk_keys]
        res = g.mem_turn(cell)
        results.append(res)
        keys.append(('turn', res))
        if res == 'cleared':
            cx = cy = 0
        if res == 'flag':
            break
    if end == 'esc':
        keys.append(('key', '\\e'))
    steps = station_open(L, credits, pokes, joystick)
    if not shop:                         # (no shop after it: the game goes on)
        steps.append(L.poke('noshop', 1))
    for kind, v in keys:
        if kind == 'key' and joystick and v in 'KL':
            x, y = (1, 0) if v == 'L' else (0, 1)
            steps += [f'joy:{x},{y}', 'wait:3', 'joy:0,0', 'wait:10']
        elif kind == 'key':
            steps += [f'key:{v}', 'wait:4']
        elif joystick:
            steps += ['btn:0,1', 'wait:3', 'btn:0,0', 'wait:4']
        else:
            steps += ['key:\\r', 'wait:4']
        if kind == 'turn' and v in ('miss', 'cleared', 'flag'):
            steps.append('wait:90')
    if steps[-1] == 'wait:90':
        steps.pop()
    steps += [f'wait:{w}' for w in waits]
    # the shop's screen, or the first frame drawn after the station (the
    # game has not stepped yet)
    steps += [L.until('sh_loop' if shop else 'render', 3000)]
    steps += [L.peek(n if n != 'prng' else 'prng_lo', k) for n, k in FIELDS.items()]
    r = a2test.run(disk, steps, iie=True, timeout=900)
    after = read(r, L, 0)
    assert results[-1:] == ['flag'] or end == 'esc', f'{name}: the plan does not end the station'
    g.station_exit()
    if g.shop and not shop:
        g.shop_exit()
    want = model_snapshot(g)
    got = model_snapshot(model_of(after, 3))
    diff = {n: (got[n], want[n]) for n in want if got[n] != want[n]}
    assert not diff, (name, diff)
    return g, results


def model_snapshot(g):
    return {'credits': g.credits, 'score': g.score, 's_level': g.s_level, 'shot_limit': g.shot_limit,
            'weapon': g.weapon, 't_level': g.t_level, 'armour': g.armour, 'lives': g.lives,
            'extra_bits': g.extra_bits, 'mult': g.mult, 'mult_t': g.mult_t, 'level': g.level,
            'station': g.station, 'shop': g.shop, 'm_round': g.m_round, 'm_pairs': g.m_pairs,
            'm_first': g.m_first, 'm_card': list(g.m_card), 'm_up': list(g.m_up), 'prng': g.prng}


def pairs_of(g):
    """{kind: [cells]} of the cards face down, the skull's cell."""
    by = {}
    w, h = g.mem_grid()
    for c in range(w * h):
        if not g.m_up[c]:
            by.setdefault(g.m_card[c], []).append(c)
    skull = by.pop(M.K['skull'])[0]
    return by, skull


def clear_then_skull(g):
    """A miss, every pair of the first grid (cleared: the prize, the next
    grid), then the skull of the second."""
    by, skull = pairs_of(g)
    groups = [c for c in by.values()]
    a, b = groups[0][0], groups[1][0]
    cards = [a, b]
    g.mem_turn(a)
    g.mem_turn(b)
    for cells in groups:
        for i in range(0, len(cells), 2):
            cards += cells[i:i + 2]
            g.mem_turn(cells[i])
            g.mem_turn(cells[i + 1])
    assert g.m_round == 1, 'the first grid cleared'
    _, skull2 = pairs_of(g)
    return cards + [skull2], 'flag'


def one_pair_then_esc(g):
    by, _ = pairs_of(g)
    cells = next(iter(by.values()))
    return cells[:2], 'esc'


def storm_prizes(disk, L):
    """Lot 11: storm_prize (6502) on each tier == the model: points with
    the multiplier, credits, the name, M_END steps."""
    cases = [(500, 0, 1), (499, 1, 1), (480, 1, 3), (100, 1, 1), (2, 1, 5)]
    steps = [*boot(L)]
    for held, rel, mult in cases:
        steps += [L.until('game_tick', 10)]
        steps += [L.poke('m_time', 500 & 255), L.poke('m_time', 500 >> 8, 1), L.poke('m_held', held & 255),
                  L.poke('m_held', held >> 8, 1), L.poke('m_rel', rel), L.poke('mult', mult),
                  L.poke('score', 0), L.poke('score', 0, 1), L.poke('score', 0, 2), L.poke('credits', 0),
                  L.poke('credits', 0, 1), f'call:{L["storm_prize"]:04X}:5',
                  L.peek('score', 3), L.peek('credits', 2), L.peek('pick_msg'), L.peek('m_end')]
    r = a2test.run(disk, steps, iie=True)
    names = []
    for k, (held, rel, mult) in enumerate(cases):
        g = M.Game(0)
        g.m_time, g.m_held, g.m_rel, g.mult = 500, held, rel, mult
        g.storm_prize()
        want = (M.bcd(g.score, 3), M.bcd(g.credits, 2), g.pick_msg, g.m_end)
        got = (r.mem(L['score'], 3, k), r.mem(L['credits'], 2, k), r.mem(L['pick_msg'], 1, k)[0],
               r.mem(L['m_end'], 1, k)[0])
        assert got == want, (held, rel, mult, got, want)
        names.append(M.PICK_TEXT[g.pick_msg])
    print(f'PASS Meteor Storm prizes == model: {", ".join(names)}')


def stations(disk, L):
    g, res = station_scene(disk, L, 'keys', 0, clear_then_skull)
    print(f'PASS Memory Station, keys: {res.count("pair") + res.count("cleared")} pairs, a miss, grid 3x3 '
          f'cleared (+25 000), the skull on grid 5x3 ends it; score {g.score}, credits {g.credits} == model')
    g, res = station_scene(disk, L, 'stick, then the shop', 500, one_pair_then_esc, joystick=True, shop=True)
    assert g.shop == 1, 'the shop after the station'
    print(f'PASS Memory Station, stick: a pair, ESC; then the shop (credits 500) == model')
    # the clock: 2 seconds left, nothing turned
    steps = station_open(L, 0) + [L.poke('mem_sec', 2), 'wait:200', L.peek('station'), L.peek('level')]
    r = a2test.run(disk, steps, iie=True, timeout=900)
    assert r.mem(L['station'], 1)[0] == 0 and r.mem(L['level'], 1)[0] == 4, \
        (r.mem(L['station'], 1), r.mem(L['level'], 1))
    print('PASS Memory Station, time out: closed, level 5 next')


def model_checks():
    """The model's own storms and decks: everything drawable, the prize."""
    for seed in range(20):
        g = M.Game(0)
        for _ in range(seed * 7):
            g.rand8()
        g.subgame = 1
        g.storm_start()
        rng = random.Random(seed)
        for k in range(3000):
            g.step(rng.choice((-1, 0, 1)), False, rng.random() < 0.8)
            # lot 11: everything left of byte 35 (the distance bar), small
            # rocks in their slots, big ones not
            assert all(not s or (s in (M.ROCK, M.BOOM) and i < M.M_ROCKS and 2 <= g.a_x[i] <= 95
                                 and not (g.a_big[i] and i >= M.M_SMALL0))
                       for i, s in enumerate(g.a_state)), k
            for y, kk in zip(g.obj_y, g.obj_k):
                assert not y or (M.FIELD_TOP <= y <= 192 - M.OBJ_H and kk <= 14), (k, y, kk)
            assert g.ship_c <= M.M_SHIP_MAX
            assert g.lives == M.LIVES and not g.game_over
            if not g.storm:
                break
        assert not g.storm and g.phase == 1
    # lot 11: the prize by the speed percentage, the multiplier on its points
    for held, rel, mult, name, points, credits in (
            (500, 0, 1, 'MEGA BONUS', 500000, 5000), (499, 1, 1, 'XTREME BONUS', 250000, 5000),
            (480, 1, 1, 'SUPER BONUS', 100000, 1000), (472, 1, 2, 'EXTRA BONUS', 100000, 0)):
        g = M.Game(0)
        g.storm_start()
        g.m_time, g.m_held, g.m_rel, g.mult = 500, held, rel, mult
        g.storm_prize()
        assert (M.PICK_TEXT[g.pick_msg], g.score, g.credits, g.m_end) == (name, points, credits, M.M_END), \
            (name, g.storm_pct(), g.score, g.credits)
    g = M.Game(0)                       # the icon ends a level at once, not the boss's
    g.take('meteor')
    assert g.subgame == 1 and g.phase == 1 and not any(g.a_state) and g.entry_w == M.ROWS
    g = M.Game(24)
    g.take('meteor')
    assert g.subgame == 1 and not g.phase
    for rnd in range(6):
        g = M.Game(0)
        g.m_round = rnd
        g.mem_deal()
        w, h = g.mem_grid()
        n = w * h
        cards = g.m_card[:n]
        assert cards.count(M.K['skull']) == 1 and all(cards.count(k) % 2 == 0 for k in set(cards)
                                                       if k != M.K['skull'])
        assert not any(g.m_card[n:]) and g.m_pairs == n // 2
    print('PASS model: 20 storms (rocks of 3 sizes and objects left of the bar, no life lost, each ends), '
          'the prizes by percentage, the icon ends the level (not the boss\'s), decks of 3x3 .. 7x5')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    a = ap.parse_args()
    model_checks()
    if not a2test.have_a2shot('sub-games'):
        return
    L = a2test.labels(a.labels, strip=True)
    storm_oracle(a.disk, L, 1, crash=False, count=1500)
    storm_oracle(a.disk, L, 2, crash=True, count=800)
    storm_prizes(a.disk, L)
    stations(a.disk, L)


if __name__ == '__main__':
    main()
