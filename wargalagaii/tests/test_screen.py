#!/usr/bin/env python3
"""WARGALAGA II screen invariant: the page just drawn == the page drawn from
scratch out of the current state.

render.s only rewrites what changed on a page since that page was last drawn
(EOR for flying things, STA for the formation, partial column clears, HUD
character cache...). Whatever the history, the result must be what a full
redraw of the state gives:

    HUD (rows 0-7)        glyphs, STA
    seated aliens         STA, table entry shift*2 + row frame
    GAME OVER             glyphs, STA
    ship / its explosion  STA
    flying aliens, explosions, shots, bombs   EOR, clipped at row 191
    stars                 star i (23 down to 0) only on a black byte

The test plays a random game (arrows, SPACE, a GAME OVER and a restart),
stops at render_done on sampled frames and compares the 8 KB page.

    tests/test_screen.py [--frames N] [--seed S]
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
from hgr_tables import hgr_offset
import fonts
import model
import sprites

M = model


def tables():
    """name -> list of entries (rows of bytes), as sprites.inc has them."""
    out = {}
    for name in ('ship', 'shot', 'bomb', 'ufo'):
        pal, drawing = sprites.SPRITES[name]
        nb, shapes = sprites.shifted(drawing, pal, 1 if name in sprites.ONE_BYTE else None)
        out[name] = shapes
    boom = [sprites.shifted(f, sprites.BOOM[0])[1] for f in sprites.BOOM[1:]]
    sboom = [sprites.shifted(f, sprites.SHIPBOOM[0])[1] for f in sprites.SHIPBOOM[1:]]
    # per WG2.AUX combo (design x tint): the alien entries, then the explosion
    out['fly'] = {c: sprites.alien_shapes(c // 4, c % 4) + [boom[f][s] for s in range(7) for f in range(2)]
                  for c in range(len(sprites.SMALL) * len(sprites.TINTS))}
    out['shipboom'] = [sboom[f][s] for s in range(7) for f in range(2)]
    out['big'] = {c: sprites.big_shapes(c // 4, c % 4) for c in range(len(sprites.BIG) * len(sprites.TINTS))}
    nb = (2 * len(sprites.BOSS[1][0]) + 6) // 7
    out['boss'] = sprites.shifted(sprites.tinted(sprites.BOSS[1], 3), sprites.BOSS[0], nb)[1][0]
    return out


def font():
    """Glyph rows for codes $20-$63: bbfont, then the game's four."""
    glyphs = {c: list(fonts.glyph(c)) for c in range(0x20, 0x60)}
    text = (GAME / 'src/game.s').read_text()
    block = text[text.index('GLYPH_EMPTY = $63'):text.index('.assert * = bbfont')]
    for k, line in enumerate(re.findall(r'\.byte ([$0-9A-F,]+)', block)):
        glyphs[0x60 + k] = [int(v[1:], 16) for v in line.split(',')]
    return glyphs


def cell_byte(c):
    return 2 * (c // 7) + (2 * (c % 7) >= 7)


def hud_text(st):
    score = st['score']
    digits = f'{score[2]:02X}{score[1]:02X}{score[0]:02X}'
    full, empty = 0x62, 0x63
    bar = lambda n: [full] * n + [empty] * (5 - n)
    credits = f'{st["credits"][1]:02X}{st["credits"][0]:02X}'
    extra = [ord(c) if st['extra_bits'] >> k & 1 else ord('-') for k, c in enumerate('EXTRA')]
    text = (list(digits.encode()) + [0x20, 0x60, ord('0') + st['lives'], 0x20, 0x61,
            ord('0') + st['armour'], 0x20, ord('S')] + bar(st['s_level']) + [0x20, ord('B')]
            + bar(st['shot_limit'] - M.B_MIN) + [0x20, ord('T'), ord('0') + st['t_level'], ord('0'),
            ord('$')] + list(credits.encode()) + extra)
    assert len(text) == 40
    return text


def level_text(st):
    """LEVEL n: the level teleported to, (level + 2) + 100 * loop."""
    return f'LEVEL {st["level"] + 2 + 100 * st["loop"]}'.ljust(9).encode()


def expected(st, T, glyphs):
    page = bytearray(8192)
    fly = T['fly'][M.alien_combo(st['level'])]
    big = T['big'][M.big_combo(st['level'])]

    def drawn_big(i):
        return st['a_big'][i] and st['a_state'][i] != M.BOOM

    def shown(i):
        return (16 if drawn_big(i) else M.FIELD_TOP) <= st['a_y'][i] < 192

    def put(rows, col, y, mode):
        for r, row in enumerate(rows):
            if y + r >= 192:
                break
            base = hgr_offset(y + r)
            for b, v in enumerate(row):
                a = base + col + b
                page[a] = v if mode == 'sta' else page[a] ^ v

    for c, ch in enumerate(hud_text(st)):
        put([[v] for v in glyphs[ch]], c, 0, 'sta')
    for i in range(M.NALIENS):
        if st['a_state'][i] == M.FORM and shown(i):
            x, anim = st['a_x'][i], st['row_anim'][i // M.COLS]
            if drawn_big(i):
                put(big[(x - 2) % 7 * 2 + anim], cell_byte(x - 2), st['a_y'][i] - 8, 'sta')
            else:
                put(fly[x % 7 * 2 + anim], cell_byte(x), st['a_y'][i], 'sta')
    msg = b'GAME OVER' if st['game_over'] else level_text(st) if st['phase'] else b''
    for k, ch in enumerate(msg):
        put([[v] for v in glyphs[ch]], (40 - 9) // 2 + k, 96, 'sta')
    want = None
    if not st['game_over']:
        if st['ship_state']:
            if st['ship_state'] > M.DEATH_T - 24:
                want = (st['ship_state'] >> 2 & 1) + 1
        elif not (st['invul_t'] | st['shield_t'][0]) & 4:
            want = 0
    if want is not None:
        x = st['ship_c']
        rows = T['ship'][x % 7] if want == 0 else T['shipboom'][x % 7 * 2 + want - 1]
        put(rows, cell_byte(x), M.SHIP_Y, 'sta')
    for i in range(M.NALIENS):
        s, y = st['a_state'][i], st['a_y'][i]
        if (M.flying(s) or s == M.BOOM) and shown(i):
            x = st['a_x'][i]
            f = (st['a_timer'][i] >> 2 & 1) + 14 if s == M.BOOM else st['step_count'] >> 2 & 1
            if drawn_big(i):
                put(big[(x - 2) % 7 * 2 + f], cell_byte(x - 2), y - 8, 'eor')
            else:
                put(fly[x % 7 * 2 + f], cell_byte(x), y, 'eor')
    if st['boss_hp'] or st['boss_boom'] & 4:
        x = st['boss_x']
        assert x % 7 == 0
        put(T['boss'], cell_byte(x), M.BOSS_Y, 'eor')
    if st['hurry']:
        x = st['h_x']
        put(T['ufo'][x % 7], cell_byte(x), M.HURRY_Y, 'eor')
    for k in range(M.MAX_SHOTS):
        if st['shot_y'][k]:
            c = st['shot_c'][k]
            put(T['shot'][c % 7], cell_byte(c), st['shot_y'][k], 'eor')
    for k in range(M.E_SHOTS):
        if st['e_y'][k]:
            c = st['e_c'][k]
            put(T['bomb'][c % 7], cell_byte(c), st['e_y'][k], 'eor')
    icons = [sprites.icon(c, colour) for c, colour in sprites.ICONS]
    for k in range(M.N_OBJ):
        if st['obj_y'][k]:
            put(icons[st['obj_kind'][k]], 2 * st['obj_k'][k], st['obj_y'][k], 'eor')
    for i in reversed(range(M.NSTARS)):
        a = hgr_offset(st['star_y'][i]) + st['star_col'][i]
        if not page[a]:
            page[a] = 1 << (i * 3 % 7) | (i % 2) << 7
    return page


FIELDS = {'ship_c': 1, 'shot_limit': 1, 'shot_y': M.MAX_SHOTS, 'shot_c': M.MAX_SHOTS,
          'star_y': M.NSTARS, 'star_col': M.NSTARS, 'a_state': M.NALIENS, 'a_x': M.NALIENS,
          'a_y': M.NALIENS, 'a_timer': M.NALIENS, 'row_anim': M.ROWS, 'e_y': M.E_SHOTS,
          'e_c': M.E_SHOTS, 'lives': 1, 'armour': 1, 'ship_state': 1, 'invul_t': 1,
          'game_over': 1, 'score': 3, 'credits': 2, 'obj_y': M.N_OBJ, 'obj_k': M.N_OBJ,
          'obj_kind': M.N_OBJ, 's_level': 1, 't_level': 1, 'extra_bits': 1, 'shield_t': 2,
          'level': 1, 'loop': 1, 'phase': 1, 'a_big': M.NALIENS, 'boss_hp': 1, 'boss_x': 1,
          'boss_boom': 1, 'hurry': 1, 'h_x': 1}


def check(disk, labels, frames=120, seed=1, every=7, start=None, hurry=False):
    """start: begin at that level with a cheating player (invulnerable,
    triple shot, 10 shots) who clears levels: teleports, LEVEL n, flypast
    and kamikaze aliens. hurry: the level has dragged (level_t near
    HURRY_T): the saucer comes out."""
    L = a2test.labels(labels, strip=True)
    T, glyphs = tables(), font()
    rng = random.Random(seed)
    first = min(L[n] for n in FIELDS)
    span = max(L[n] + k for n, k in FIELDS.items()) - first
    steps = [L.until('game_tick', 3000)]
    if start is not None:
        steps = [L.until('main', 3000), L.poke('start_level', start), L.until('game_tick', 3000),
                 L.poke('weapon', 2), L.poke('shot_limit', 10)]
        if hurry:
            steps += [L.poke('level_t', M.HURRY_T - 40), L.poke('level_t', M.HURRY_T - 40 >> 8, 1)]
    samples = 0
    for k in range(frames * every):
        if start is not None and k % 20 == 0:
            steps += [L.poke('invul_t', 60), L.poke('fire_held', 0x80), L.poke('autofire_t', 255)]
        if k % 5 == 0:
            steps.append('press:' + rng.choice(['\\<', '\\>', ' ', ' ', ' ', 'J', 'L']))
        if k % every == every - 1:
            steps += [L.until('render_done', 60), L.peek('page'), L.peek('step_count', 2),
                      f'peek:{first:04X}:{span}', 'peek:2000:8192', 'peek:4000:8192']
            samples += 1
        else:
            steps.append(L.until('render', 60))
        steps.append(L.until('game_tick', 60))   # (until X twice: no progress)
        if k == frames * every // 2 and start is None:   # let the game end, then restart
            steps += ['wait:3000']
            for _ in range(10):
                steps += [L.until('render_done', 60), L.peek('page'), L.peek('step_count', 2),
                          f'peek:{first:04X}:{span}', 'peek:2000:8192', 'peek:4000:8192',
                          L.until('game_tick', 60)]
                samples += 1
            steps += ['key: ', 'wait:40', L.until('game_tick', 60)]
    r = a2test.run(disk, steps, iie=True, timeout=1800)
    bad = saucer = 0
    states = set()
    for n in range(samples):
        page = r.mem(L['page'], 1, n)[0]
        block = r.mem(first, span, n)
        st = {name: block[L[name] - first:L[name] - first + size] for name, size in FIELDS.items()}
        for name in ('ship_c', 'shot_limit', 'lives', 'armour', 'ship_state', 'invul_t', 'game_over',
                     's_level', 't_level', 'extra_bits', 'level', 'loop', 'phase', 'boss_hp',
                     'boss_x', 'boss_boom', 'hurry', 'h_x'):
            st[name] = st[name][0]
        st['step_count'] = r.mem(L['step_count'], 2, n)[0]
        states.update(st['a_state'])
        saucer += st['hurry']
        got = r.mem(0x2000 + page * 0x2000, 8192, n if page == 0 else n)
        want = expected(st, T, glyphs)
        diff = [a for a in range(8192) if got[a] != want[a] and a % 128 < 120]
        if diff:
            bad += 1
            rows = sorted({next(y for y in range(192) if 0 <= a - hgr_offset(y) < 40) for a in diff})
            print(f'FRAME {n}: page {page + 1}, {len(diff)} bytes differ, rows {rows[:12]}'
                  f'{"..." if len(rows) > 12 else ""}; game_over {st["game_over"]}')
            if bad >= 5:
                break
    assert not bad, f'{bad} frames differ from a redraw from scratch'
    assert saucer or not hurry, 'the hurry-up saucer never came out'
    what = (f'from level {start + 1}, cheating: teleports, flypast, kamikaze' if start is not None
            else 'play, GAME OVER, restart')
    if hurry:
        what = f'level dragging: the saucer in {saucer} of them'
    print(f'PASS screen invariant: {samples} frames ({what}) == redraw from scratch')
    return states


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--disk', type=Path, default=ROOT / 'dist/WARGALAGAII.po')
    ap.add_argument('--labels', type=Path, default=GAME / 'build/game.lbl')
    ap.add_argument('--frames', type=int, default=120)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    if not a2test.have_a2shot('screen invariant'):
        return
    check(a.disk, a.labels, a.frames, a.seed)
    assert M.PASS in check(a.disk, a.labels, 120, a.seed, every=9, start=3), 'flypast drawn'
    assert M.KAMI in check(a.disk, a.labels, 80, a.seed, every=9, start=7), 'kamikaze drawn'
    check(a.disk, a.labels, 80, a.seed, every=9, start=2)      # big aliens (sway, dives, shots)
    check(a.disk, a.labels, 240, a.seed, every=11, start=24)   # the boss, its fall
    check(a.disk, a.labels, 60, a.seed, every=5, start=0, hurry=True)   # the saucer


if __name__ == '__main__':
    main()
