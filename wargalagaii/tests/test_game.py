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


def model_invariants(games=30, steps=3000):
    """What logic hands the drawing stays drawable (render.s has rows 0..191,
    columns 0..39), and gauges stay in range, over random games of the model
    (the 6502 equals it). Bug hunt 2026-10-23: an object poked at row 188
    is drawn into the zero page; the rules can't produce one (drop guards
    it anyway), this keeps it so."""
    import random as rnd
    M = model
    dropped = set()
    for seed in range(games):
        g, rng = M.Game(), rnd.Random(seed)
        drop = g.drop

        def spy(i, g=g, drop=drop):
            before = list(g.obj_y)
            drop(i)
            dropped.update(g.obj_kind[k] for k in range(M.N_OBJ) if g.obj_y[k] and not before[k])
        g.drop = spy
        for k in range(steps):
            g.step(rng.choice((-1, 0, 1)), rng.random() < 0.5, rng.random() < 0.5)
            where = f'game {seed} step {k + 1}'
            assert 0 <= g.ship_c <= M.SHIP_MAX, where
            for y, c in zip(g.shot_y, g.shot_c):
                assert not y or (M.FIELD_TOP <= y <= 192 - M.SHOT_H and c <= 139), (where, y, c)
            assert all(not y or M.FIELD_TOP <= y <= 192 - M.BOMB_H for y in g.e_y), (where, g.e_y)
            assert all(c <= 139 for y, c in zip(g.e_y, g.e_c) if y), (where, g.e_c)
            for y, kk, kind in zip(g.obj_y, g.obj_k, g.obj_kind):
                assert not y or (M.FIELD_TOP <= y <= 192 - M.OBJ_H and kk <= 19
                                 and kind < len(M.KINDS)), (where, y, kk, kind)
            assert all(x <= M.ALIEN_MAX for x in g.a_x), where
            assert 0 <= g.lives <= 4 and 0 <= g.armour <= 2, where
            assert 1 <= g.s_level <= M.S_MAX and M.B_MIN <= g.shot_limit <= M.B_MAX, where
            assert M.T_MIN <= g.t_level <= M.T_MAX and g.mult in (1, 2, 5), where
            assert g.credits <= 9999 and g.weapon in (0, 1, 2), where
            assert max(g.autofire_t, g.mult_t, g.shield_t, g.freeze_t) <= M.duration(M.T_MAX), where
    # Bug hunt 2026-10-23: the kind came from the low byte of a second draw,
    # the first one shifted: only coins and S ever dropped. drop() itself,
    # called on and on: every kind but the rarest few comes out.
    g = M.Game()
    g.a_y[0], g.a_x[0] = 100, 60
    kinds = set()
    for _ in range(20000):
        g.obj_y = [0] * M.N_OBJ
        g.drop(0)
        kinds.update(g.obj_kind[k] for k in range(M.N_OBJ) if g.obj_y[k])
    assert len(kinds) >= 28, sorted(M.KINDS[k] for k in kinds)   # the bug: 5
    # Bug hunt 6: the boss's life and 200 coin fell half-way, then the level
    # ended (40 steps after the boss) and wiped them. A ship under them
    # takes both now.
    g = M.Game(24)
    for k in range(2000):
        if k == 300:                     # shot down
            g.boss_hp = 0
            g.boss_down()
        under = [7 * g.obj_k[i] for i in range(M.N_OBJ) if g.obj_y[i]]
        if under:
            g.ship_c = min(under[0], M.SHIP_MAX)
        g.invul_t = 50
        g.step(0, False, False)
        if g.phase:
            break
    assert g.lives == M.LIVES + 1, ('the boss life', g.lives)
    print(f'PASS model invariants: {games} random games x {steps} steps, everything drawable, '
          f'gauges in range; drop() gives {len(kinds)} of {len(M.KINDS)} kinds; the boss life caught')


def volume(disk, build):
    import importlib.util
    spec = importlib.util.spec_from_file_location('prodos_read', ROOT / 'dev/tools/prodos/read_volume.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(disk.read_bytes())
    assert image.header()['name'] == 'WARGALAGAII'
    assert image.header()['blocks'] == 280 and len(image.d) == 143360
    entries = {e[1:1 + (e[0] & 15)].decode(): e for e in image.entries(2)}
    assert set(entries) == {'PRODOS', *SYS_NAMES, 'WG2.AUX'}, sorted(entries)
    assert all(entries[n][0x10] == 0xFF for n in entries if n != 'WG2.AUX')
    assert image.read(entries['WG2.AUX']) == (build / 'WG2.AUX').read_bytes()
    assert image.read(entries['PRODOS']) == (ROOT / 'dev/tools/prodos/PRODOS').read_bytes()
    for name in SYS_NAMES:
        assert image.read(entries[name]) == (build / name).read_bytes(), name
    assert image.d[:1024] == (ROOT / 'dev/tools/prodos/boot.bin').read_bytes()
    print('PASS bootable ProDOS volume /WARGALAGAII, WG2.SYSTEM + WG2.SYS + WG2.AUX round trip')


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
    continuously (passing through: nohit), bombs falling: no late frame."""
    fire = [L.until('logic_step', 10), L.poke('fire_req', 0x80), L.until('logic_done', 10)]
    steps = [L.until('game_tick', 3000), L.poke('shot_limit', 10), L.poke('nohit', 1),
             L.poke('armour', 99), L.poke('invul_t', 250), 'wait:500', L.poke('invul_t', 250),
             'wait:500', L.poke('invul_t', 250), 'wait:200']
    steps += [L.peek('late_count', 2), L.peek('frame_count', 2)]
    for k in range(frames):              # (kept invulnerable: a diver kills anyway)
        steps += fire + ([L.poke('invul_t', 250)] if k % 100 == 0 else [])
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


def vbl_edges(disk, L):
    """The //e clock counts each refresh: timing_scan must run at least once
    in every vertical blank (~4 550 cycles), drawing included. A missed
    edge slows the game and shows a frame late unnoticed (bug hunt
    2026-10-23: aliens_pass and the column clears ran ~6 000 cycles
    without a scan). Every vbl_count increment comes <= 1.5 refresh after
    the previous one, during the entry waves and the 10-shot bench, and
    through level changes with the card (bug hunt 5: the new pack's tables
    came from aux in one AUXMOVE under SEI, ~50 000 cycles without a scan
    or the music; now 64 bytes at a time)."""
    vc = L['vbl_count']
    fire = [L.until('logic_step', 10), L.poke('fire_req', 0x80), L.until('logic_done', 10)]
    scenes = (('entry waves', ['wait:1', f'storewatch:{vc:04X}:{vc:04X}', 'wait:1500']),
              ('bench', [L.poke('shot_limit', 10), L.poke('nohit', 1), L.poke('armour', 99),
                         'wait:1100', f'storewatch:{vc:04X}:{vc:04X}'] + fire * 600),
              ('level changes, Mockingboard', 'levels'))
    cheat = [L.poke('invul_t', 60), L.poke('fire_held', 0x80), L.poke('autofire_t', 255), 'wait:40']
    for name, steps in scenes:
        start = [L.until('game_tick', 3000)]
        if steps == 'levels':            # level 4 -> 5: a new pack
            start = [L.until('main', 3000), L.poke('start_level', 3), L.until('game_tick', 3000),
                     L.poke('weapon', 2), L.poke('shot_limit', 10), L.poke('noshop', 1)]
            steps = [f'storewatch:{vc:04X}:{vc:04X}'] + cheat * 120 + [L.peek('level')]
        r = a2test.run(disk, start + steps, iie=True, timeout=900, mockingboard=name.endswith('board'))
        if name.endswith('board'):
            assert r.mem(L['level'], 1)[0] >= 4, ('a new pack', r.mem(L['level'], 1))
        stamps = [int(c) for c in re.findall(r'^store \w+ \w+ .* cycles=(\d+)', r.out, re.M)]
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        assert len(stamps) > 500 and max(gaps) < 17030 * 3 // 2, (name, len(stamps), max(gaps))
        print(f'PASS VBL edges, {name}: {len(stamps)} counted, none missed '
              f'(longest interval {max(gaps)} cycles)')


def oracle(disk, L, count=2000, every=1, seed=1983, armour=0):
    """Poke random inputs at each logic step; compare the state with the
    model at logic_done (every `every` steps, always the last). armour is
    poked into both at the first step."""
    rng = random.Random(seed)
    game = model.Game()
    game.armour = armour
    names = [n for n in game.state() if n != 'prng']
    first = min(L[n] for n in names)
    span = max(L[n] + len(v) for n, v in game.state().items() if n != 'prng') - first
    steps, inputs, checked = [L.until('game_tick', 3000), L.until('logic_step', 10),
                              L.poke('armour', armour)], [], []
    move = 0
    for k in range(count):
        if rng.random() < 0.15:
            move = rng.choice((-1, 0, 1))
        fire = rng.random() < 0.3
        held = rng.random() < 0.5
        inputs.append((move, fire, held))
        steps += [L.until('logic_step', 10), L.poke('move_dir', move & 0xFF),
                  L.poke('fire_req', 0x80 if fire else 0), L.poke('fire_held', 0x80 if held else 0),
                  L.until('logic_done', 10)]
        if k % every == every - 1 or k == count - 1:
            steps += [f'peek:{first:04X}:{span}', L.peek('prng_lo', 2)]
            checked.append(k)
    r = a2test.run(disk, steps, iie=True, timeout=900)
    seen = 0
    deaths = []
    for k, (move, fire, held) in enumerate(inputs):
        lives = game.lives
        game.step(move, fire, held)
        if game.lives != lives:
            deaths.append(k + 1)
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
    assert game.score and (game.level or game.a_state.count(model.DEAD) > 10)
    print(f'PASS logic oracle, seed {seed}, armour {armour}: {count} steps == tools/model.py '
          f'(score {game.score}, ship lost at steps {deaths}'
          f'{", GAME OVER" if game.game_over else ""})')
    return game, deaths


def game_over(disk, L):
    """Nobody plays: the model's game ends at a known step; the 6502 shows
    GAME OVER and 0 lives in the HUD of both pages, then SPACE starts anew."""
    g = model.Game()
    while not g.game_over:
        g.step()
    r = a2test.run(disk, [L.until('game_tick', 3000), 'wait:2400',
                          L.peek('game_over'), L.peek('lives'), L.peek('msg_drawn', 2),
                          L.peek('hud_seen', 80), 'key: ', 'wait:30',
                          L.peek('game_over'), L.peek('lives'), L.peek('score', 3),
                          L.peek('msg_drawn', 2)], iie=True)
    assert r.mem(L['game_over'], 1, 0) == b'\x01' and r.mem(L['lives'], 1, 0) == b'\x00'
    assert r.mem(L['msg_drawn'], 2, 0) == b'\x01\x01', 'GAME OVER on both pages'
    hud = r.mem(L['hud_seen'], 80)
    for page in (hud[:40], hud[40:]):
        assert page[:6] == b'000000' and page[8:9] == b'0', page
    assert r.mem(L['game_over'], 1, 1) == b'\x00' and r.mem(L['lives'], 1, 1) == b'\x03'
    assert r.mem(L['score'], 3, 0) == b'\0\0\0' and r.mem(L['msg_drawn'], 2, 1) == b'\0\0'
    # render_init/game_init once cleared whole pages past their variables:
    # the clock (//e fell back to delays after a restart), /RAM's unit and
    # crt0's saved zero page (bug hunt 2026-10-23).
    r = a2test.run(disk, [L.until('game_tick', 3000), L.peek('ram_unit'), L.peek('zp_save', 256),
                          'peek:0:256', 'wait:2400', 'key: ', 'wait:60', L.peek('timing_mode'),
                          L.peek('ram_unit'), L.peek('zp_save', 256)], iie=True)
    saved, live = r.mem(L['zp_save'], 256, 0), r.mem(0, 256)
    keep = range(0x20, 0x3A)        # text window, hooks ($3A-$4F: MLI and AUXMOVE scratch)
    assert [saved[a] for a in keep] == [live[a] for a in keep] and sum(map(bool, saved)) > 20, \
        'crt0 zero page kept'
    assert r.mem(L['ram_unit'], 1, 0)[0] & 0xF0 == 0xB0, '/RAM unit kept for the release'
    assert r.mem(L['timing_mode'], 1)[0] == 1 and r.mem(L['ram_unit'], 1, 1) == r.mem(L['ram_unit'], 1, 0)
    assert r.mem(L['zp_save'], 256, 1) == saved, 'restart keeps crt0 state'
    print('PASS no player: 3 lives lost, GAME OVER and 0 lives on both pages, SPACE: new game '
          '(clock, /RAM unit and saved zero page intact)')


def level_oracle(disk, L, start, count=3000, every=5, seed=5, cheats=(), later=None):
    """Lot 6: from level `start` (poked before game_init), a strong cheating
    player (kept invulnerable, triple shot, 10 shots, autofire) goes through
    level ends, teleports and the next levels; state == model at every
    `every` steps. Returns the model and the levels it saw."""
    rng = random.Random(seed)
    game = model.Game(start)
    names = [n for n in game.state() if n != 'prng']
    first = min(L[n] for n in names)
    span = max(L[n] + len(v) for n, v in game.state().items() if n != 'prng') - first
    cheats0 = [('weapon', 2), ('shot_limit', 10), ('s_level', 5), ('noshop', 1), *cheats]
    steps = [L.until('main', 3000), L.poke('start_level', start), L.until('game_tick', 3000)]
    plan, seen = [], []
    move = 0
    for k in range(count):
        if rng.random() < 0.2:
            move = rng.choice((-1, 0, 1))
        pokes = list(cheats0) if k == 0 else []
        pokes += (later or {}).get(k, [])
        plan.append((move, pokes))
        steps += [L.until('logic_step', 10), L.poke('move_dir', move & 0xFF), L.poke('fire_req', 0x80),
                  L.poke('fire_held', 0x80)] + [L.poke(n, v >> 8 * b, b) for n, v in pokes
                                                for b in range(1 + (v > 255))]
        steps.append(f'invul:{k}')       # placeholder, filled below
        steps += [L.until('logic_done', 10)]
        if k % every == every - 1 or k == count - 1:
            steps += [f'peek:{first:04X}:{span}', L.peek('prng_lo', 2)]
    # invulnerability: decided by the model's state before each step
    sim = model.Game(start)
    out, k = [], 0
    for st in steps:
        if st.startswith('invul:'):
            move, pokes = plan[k]
            for n, v in pokes:
                setattr(sim, n, v)
            if sim.invul_t < 5:
                out.append(L.poke('invul_t', 60))
                plan[k] = (move, pokes + [('invul_t', 60)])
            sim.step(move, True, True)
            if sim.shop:                 # noshop: closed at once
                sim.shop_exit()
            k += 1
        else:
            out.append(st)
    r = a2test.run(disk, out, iie=True, timeout=1200)
    seen_k = hurried = 0
    states = set()
    for k, (move, pokes) in enumerate(plan):
        for n, v in pokes:
            setattr(game, n, v)
        game.step(move, True, True)
        if game.shop:
            game.shop_exit()
        states.update(game.a_state)
        hurried += game.hurry
        if not seen or seen[-1] != (game.level, game.loop):
            seen.append((game.level, game.loop))
        if k % every == every - 1 or k == count - 1:
            got = r.mem(first, span, seen_k)
            for name, want in game.state().items():
                if name == 'prng':
                    assert r.mem(L['prng_lo'], 2, seen_k) == want, f'level {start}: step {k + 1} prng'
                    continue
                have = got[L[name] - first:L[name] - first + len(want)]
                assert have == want, f'level {start}: step {k + 1} {name}: 6502 {have.hex()} model {want.hex()}'
            seen_k += 1
    game.states_seen = states
    game.hurried = hurried
    return game, seen


def bonus_effects(disk, L):
    """Lot 5: every object kind falls onto the ship (poked into slot 0 of the
    6502 and of the model at the same step), gauges pushed to their maximum,
    EXTRA completed twice; fire pressed and held (weapons, autofire). The
    state is compared at every step; every kind must have been taken."""
    names = list(model.KINDS)
    seq = names + ['s'] * 5 + ['b'] * 6 + ['t'] * 7 + ['armour'] * 3 + ['life'] * 2 \
        + ['e', 'x', 'lt', 'r', 'a'] * 2 + ['skull'] * 6 + ['w3', 'auto', 'w2', 'x5', 'freeze', 'w1']
    game = model.Game()
    taken = {}
    take = game.take
    game.take = lambda kind: (taken.__setitem__(kind, taken.get(kind, 0) + 1), take(kind))
    state = game.state()
    names_cmp = [n for n in state if n != 'prng']
    first = min(L[n] for n in names_cmp)
    span = max(L[n] + len(v) for n, v in state.items() if n != 'prng') - first
    steps, plan, gap = [L.until('game_tick', 3000)], [], 12
    for k in range(len(seq) * gap + 40):
        pokes = []
        if k % gap == 0 and k // gap < len(seq):
            kind = model.K[seq[k // gap]]
            pokes = [('obj_y', model.SHIP_Y - 10), ('obj_k', (model.SHIP_MAX // 2 + 3) // 7),
                     ('obj_kind', kind), ('invul_t', 200)]
        fire, held = k % 5 == 0, k % 3 != 0
        plan.append((pokes, fire, held))
        steps += [L.until('logic_step', 10), L.poke('move_dir', 0), L.poke('fire_req', 0x80 if fire else 0),
                  L.poke('fire_held', 0x80 if held else 0)]
        steps += [L.poke(name, value) for name, value in pokes]
        steps += [L.until('logic_done', 10), f'peek:{first:04X}:{span}', L.peek('prng_lo', 2)]
    r = a2test.run(disk, steps, iie=True, timeout=900)
    peak = [0, 0, 0, 0]
    for k, (pokes, fire, held) in enumerate(plan):
        for name, value in pokes:
            if name in ('obj_y', 'obj_k', 'obj_kind'):
                getattr(game, name)[0] = value
            else:
                setattr(game, name, value)
        game.step(0, fire, held)
        peak = [max(a, b) for a, b in zip(peak, (game.s_level, game.shot_limit, game.t_level,
                                                 game.score > 0 and game.mult))]
        got = r.mem(first, span, k)
        for name, want in game.state().items():
            if name == 'prng':
                assert r.mem(L['prng_lo'], 2, k) == want, f'step {k + 1} prng'
                continue
            have = got[L[name] - first:L[name] - first + len(want)]
            assert have == want, f'step {k + 1} {name}: 6502 {have.hex()} model {want.hex()}'
    missing = [n for n in names if n not in taken]
    assert not missing, ('kinds never taken', missing)
    assert peak[:3] == [model.S_MAX, model.B_MAX, model.T_MAX] and peak[3] == 5, peak
    print(f'PASS bonus effects: all {len(names)} kinds taken ({sum(taken.values())} pickups), gauges '
          f'to their maximum, EXTRA twice, skulls, weapons and autofire; {len(plan)} steps == model '
          f'(score {game.score}, credits {game.credits}, marks {game.marks:06b})')


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


def score_cap(disk, L):
    """The score stops at 999 999 (bug hunt 6: it wrapped to 0)."""
    steps = [L.until('game_tick', 3000), L.poke('score', 0x90), L.poke('score', 0x99, 1),
             L.poke('score', 0x99, 2), L.poke('shot_limit', 10), L.poke('weapon', 2)]
    for _ in range(60):
        steps += [L.poke('invul_t', 60), 'press: ', 'wait:20']
    steps += [L.peek('score', 3)]
    for _ in range(60):
        steps += [L.poke('invul_t', 60), 'press: ', 'wait:20']
    r = a2test.run(disk, steps + [L.peek('score', 3)], iie=True)
    assert r.mem(L['score'], 3, 0) == r.mem(L['score'], 3, 1) == b'\x99\x99\x99', \
        (r.mem(L['score'], 3, 0).hex(), r.mem(L['score'], 3, 1).hex())
    print('PASS score stops at 999999 (from 999990, still there 60 shots later)')


def joystick_delay(disk, L):
    """Without a video clock (delays: a //c whose interrupt stopped, no
    mouse firmware) the stick is read too (bug hunt 5: it stayed centred)."""
    r = a2test.run(disk, [L.until('game_tick', 3000), L.poke('timing_mode', 0), 'key:\t',
                          'joy:1,0', 'wait:60', L.peek('joy_x'), 'joy:-1,0', 'wait:60', L.peek('joy_x')],
                   iie=True)
    right, left = r.mem(L['joy_x'], 1, 0)[0], r.mem(L['joy_x'], 1, 1)[0]
    assert 150 < right < 180 and left < 10, (right, left)   # (17 cycles a count, as the others)
    print(f'PASS joystick with the delay clock: right {right}, left {left}')


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


def small_machine(disk, L):
    """MACHID says 64 KB (poked at _main): message, a key, ProDOS launcher;
    /RAM ($BF) untouched."""
    r = a2test.run(disk, [L.until('main', 3000), 'poke:BF98:A2', 'wait:30', 'peek:400:1024',
                          'key: ', 'wait:300', 'peek:400:1024', 'peek:BF31:4'], iie=True)
    assert 'NEEDS 128K' in text(r, 0), text(r, 0)
    assert 'BITSY' in text(r, 1), 'a key returns to ProDOS'
    assert 0xBF in r.mem(0xBF31, 4)[1:], '/RAM still in the device list'
    print('PASS 64 KB machine: message, a key back to ProDOS, /RAM untouched')


def missing_sys(build, keep=('WG2.SYSTEM',), message='WG2.SYS ERROR'):
    """A volume with WG2.SYSTEM but no WG2.SYS: the loader's message, then a
    key back to ProDOS (it used to hang, bug hunt 2026-10-23). With
    keep=(WG2.SYSTEM, WG2.SYS): no WG2.AUX, the game's message."""
    import shutil
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(prefix='wargalagaii-') as tmp:
        stage = Path(tmp) / 'stage'
        stage.mkdir()
        shutil.copy(ROOT / 'dev/tools/prodos/PRODOS', stage / 'PRODOS#FF0000')
        for name in keep:
            shutil.copy(build / name, stage / f'{name}#FF2000')
        disk = Path(tmp) / 'NOSYS.po'
        subprocess.run([sys.executable, str(ROOT / 'dev/tools/prodos/build_volume.py'), str(stage),
                        str(disk), '--volume', 'WARGALAGAII', '--boot',
                        str(ROOT / 'dev/tools/prodos/boot.bin'), '--blocks', '280'],
                       check=True, capture_output=True)
        r = a2test.run(disk, ['wait:1500', 'peek:400:1024', 'key: ', 'wait:300', 'peek:400:1024'],
                       iie=True)
    assert message in text(r, 0) and 'BITSY' in text(r, 1), text(r, 0)
    print(f'PASS no {"WG2.SYS" if len(keep) == 1 else "WG2.AUX"} on the volume: '
          f'"{message}", a key back to ProDOS')


def nmos(disk):
    r = a2test.run(disk, ['wait:1500', 'peek:400:1024'], emulator=a2test.A2SHOT)
    assert 'NEEDS A 65C02' in text(r), text(r)
    print('PASS NMOS 6502 (Apple II+): refusal message, no crash')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    a = ap.parse_args()
    model_invariants()
    volume(a.disk, a.labels.parent)
    if not a2test.have_a2shot('//e execution'):
        return
    L = a2test.labels(a.labels, strip=True)
    cadence(a.disk, L, pal=False)
    cadence(a.disk, L, pal=True)
    game, deaths = oracle(a.disk, L)
    assert len(deaths) == 3 and game.game_over, 'the scripted game loses its 3 lives'
    game, _ = oracle(a.disk, L, count=1500, seed=7, armour=2)
    assert game.armour < 2, 'armour took a bomb'
    for start, why, count in ((0, 'normal', 3000), (2, 'big aliens', 3000), (3, 'bonus', 3000),
                              (7, 'kamikaze', 3000), (24, 'boss', 3000), (99, 'boss of level 100, loop', 4500)):
        game, seen = level_oracle(a.disk, L, start, count, every=10)
        assert len(seen) >= 2, (why, seen)
        # (bug hunt 2026-10-23: kamikaze aliens died on their first step)
        need = {3: model.PASS, 7: model.KAMI}.get(start)
        assert need is None or need in game.states_seen, (why, sorted(game.states_seen))
        assert start != 2 or game.marks & 1, 'a big alien shot: its rank mark taken'
        assert start not in (24, 99) or len(seen) >= 2, 'the boss shot down'
        print(f'PASS level oracle from level {start + 1} ({why}): levels {[l + 1 + 100 * p for l, p in seen]} '
              f'== model (score {game.score})')
    # bug hunt 6: frozen on a big level, the seated big aliens stay targets
    # (the 6502 let shots through them, the model hit them)
    game, seen = level_oracle(a.disk, L, 2, 1500, every=10, later={140: [('freeze_t', 300)]})
    print(f'PASS level oracle, frozen big aliens: levels {[l + 1 for l, p in seen]} == model')
    # a level that drags: the hurry-up saucer, its aimed bombs, gone at the level's end
    game, seen = level_oracle(a.disk, L, 1, 1500, every=10, cheats=[('level_t', model.HURRY_T - 60)])
    assert game.hurried > 100 and len(seen) >= 2 and not game.hurry, (game.hurried, seen)
    print(f'PASS level oracle, hurry-up: the saucer out {game.hurried} steps, levels '
          f'{[l + 1 for l, p in seen]} == model')
    bonus_effects(a.disk, L)
    bench(a.disk, L)
    vbl_edges(a.disk, L)
    game_over(a.disk, L)
    play(a.disk, L)
    joystick_delay(a.disk, L)
    score_cap(a.disk, L)
    exits(a.disk, L)
    small_machine(a.disk, L)
    missing_sys(a.labels.parent)
    missing_sys(a.labels.parent, ('WG2.SYSTEM', 'WG2.SYS'), 'WG2.AUX: LOAD ERROR')
    nmos(a.disk)


if __name__ == '__main__':
    main()
