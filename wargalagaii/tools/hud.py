#!/usr/bin/env python3
"""WARGALAGA II HUD layout (lot 10) -> src/hud.inc.

The HUD is HUD_N characters, each at its own place (byte column, top row):
the 40 of row 0, then rows of 4 inside the walls (model.FIELD_COL), like
Warblade's panels. render.s fills hud_buf from the state (hud_fill), then
rewrites on a page only the characters that differ from what it shows.

    row 0     score, HI and the best score, $ and the credits
              (Meteor Storm: score, SPEED %, credits: storm.s storm_template)
    left      lives (ships), armour (shields), the gauges S and B (bars of
              half segments), T (seconds), the letters E X T R A
    right     the score multiplier and the timed bonuses as draining bars
              (x2/x5, AF autofire, SH shield, FZ freeze), the rank (RK)
              and the six rank marks

`text(st)` is the same fill in Python, for tests/test_screen.py.

    tools/hud.py            write src/hud.inc (if changed)
    tools/hud.py --check    fail if src/hud.inc is stale
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'src/hud.inc'

GLYPH_SHIP, GLYPH_SHIELD, GLYPH_FULL, GLYPH_EMPTY = 0x60, 0x61, 0x62, 0x63
GLYPH_BAR2, GLYPH_BAR1, GLYPH_BAR0 = 0x64, 0x65, 0x66     # two, one, no half segment
LEFT, RIGHT = 0, 40 - model.FIELD_COL
TOP = '000000' + ' ' * 8 + 'HI 000000' + ' ' * 12 + '$0000'
# Wall rows: (column, character row, 4 characters); '@name' marks the
# field's first character (';' ends a name), the rest of a field are '~'.
WALL = [
    (LEFT, 2, '@lives~~~'), (LEFT, 3, '@armour~  '),
    (LEFT, 5, 'S@sbar~~'), (LEFT, 6, 'B@bbar~~'), (LEFT, 7, 'T@time;0 '),
    *[(LEFT, 9 + k, f' @extra{k}  ') for k in range(5)],
    (RIGHT, 2, 'X@mult  '), (RIGHT, 3, '@mbar~~~'),
    (RIGHT, 5, 'AF  '), (RIGHT, 6, '@abar~~~'),
    (RIGHT, 8, 'SH  '), (RIGHT, 9, '@shbar~~~'),
    (RIGHT, 11, 'FZ  '), (RIGHT, 12, '@fbar~~~'),
    (RIGHT, 15, 'RK  '), (RIGHT, 16, ' @rank~ '),
    (RIGHT, 18, ' @mark0@mark1@mark2'), (RIGHT, 19, ' @mark3@mark4@mark5'),
]


def parse(cells):
    """'S@sbar~~' -> ['S', 'sbar', '~', '~']."""
    out, k = [], 0
    while k < len(cells):
        if cells[k] == '@':
            j = k + 1
            while j < len(cells) and (cells[j].isalnum() and cells[j] != '~'):
                j += 1
            out.append(cells[k + 1:j])
            k = j + (j < len(cells) and cells[j] == ';')
        else:
            out.append(cells[k])
            k += 1
    assert len(out) == 4, cells
    return out


def layout():
    """-> places [(col, row)], template [codes], fields {name: index}."""
    places = [(c, 0) for c in range(40)]
    template = [ord(c) for c in TOP]
    fields = {'score': 0, 'hi': TOP.index('HI') + 3, 'credits': TOP.index('$') + 1}
    for col, r, cells in WALL:
        for k, cell in enumerate(parse(cells)):
            if len(cell) > 1:
                fields[cell] = len(places)
            places.append((col + k, 8 * r))
            template.append(ord(' ') if len(cell) > 1 or cell == '~' else ord(cell))
    assert len(places) <= 128, len(places)
    return places, template, fields


def bar(halves, n):
    """halves (half segments lit) -> n characters."""
    return [GLYPH_BAR2 if halves >= 2 * i + 2 else GLYPH_BAR1 if halves == 2 * i + 1 else GLYPH_BAR0
            for i in range(n)]


def timer_halves(t):
    """A timed bonus (steps left) -> half segments: one per 256 steps
    started (~8.5 s), 8 at most (the 4 characters)."""
    return min(8, (t >> 8) + (t & 0xFF != 0))


def digits(v, n):
    return [ord(c) for c in f'{v:0{n}X}']


def text(st):
    """The HUD's characters for a state (dict of ints, as the 6502 holds
    them: score and credits BCD, hi_score BCD 3 bytes, low first)."""
    places, out, f = layout()
    out = list(out)
    bcd = lambda b: [ord(c) for c in ''.join(f'{v:02X}' for v in reversed(b))]
    score = st['score']
    if st['storm']:
        out[:40] = storm_top(st)
    else:
        out[f['score']:f['score'] + 6] = bcd(score)
        out[f['hi']:f['hi'] + 6] = bcd(st['hi_score'])
        out[f['credits']:f['credits'] + 4] = bcd(st['credits'])
    side(out, f, st)
    return out


def side(out, f, st):
    lives = min(st['lives'], 4)
    out[f['lives']:f['lives'] + 4] = [GLYPH_SHIP] * lives + [ord(' ')] * (4 - lives)
    out[f['armour']:f['armour'] + 2] = [GLYPH_SHIELD] * st['armour'] + [ord(' ')] * (2 - st['armour'])
    out[f['sbar']:f['sbar'] + 3] = bar(st['s_level'], 3)
    out[f['bbar']:f['bbar'] + 3] = bar(st['shot_limit'] - model.B_MIN, 3)
    out[f['time']] = ord('0') + st['t_level']
    for k, c in enumerate('EXTRA'):
        out[f[f'extra{k}']] = ord(c) if st['extra_bits'] >> k & 1 else ord('-')
    out[f['mult']] = ord('0') + st['mult']
    for name, t in (('mbar', 'mult_t'), ('abar', 'autofire_t'), ('shbar', 'shield_t'), ('fbar', 'freeze_t')):
        out[f[name]:f[name] + 4] = bar(timer_halves(st[t]), 4)
    out[f['rank']:f['rank'] + 2] = [ord(c) for c in f'{st["rank"]:02d}']
    for k in range(6):
        out[f[f'mark{k}']] = ord('1') + k if st['marks'] >> k & 1 else ord('-')


def storm_pct(st):
    """model.Game.storm_pct from the state."""
    time = st['m_time'][0] | st['m_time'][1] << 8
    held = st['m_held'][0] | st['m_held'][1] << 8
    if not time:
        return 0
    if not st['m_rel']:
        return 101
    return (100 * held + (time >> 1)) // time


def storm_top(st):
    """Meteor Storm's row 0 (storm.s storm_template, lot 11): score, SPEED
    and the percentage (no leading zero), credits."""
    score = st['score']
    digits_ = f'{score[2]:02X}{score[1]:02X}{score[0]:02X}'
    credits = f'{st["credits"][1]:02X}{st["credits"][0]:02X}'
    row = f'{digits_}      SPEED {storm_pct(st):3d}%          ${credits}   '
    assert len(row) == 40
    return list(row.encode())


def emit():
    places, template, fields = layout()
    out = ['; Generated by tools/hud.py -- do not edit.',
           f'.assert HUD_N = {len(places)}, error, "HUD_N (game.s): tools/hud.py"']
    for name in ('score', 'hi', 'credits', 'lives', 'armour', 'sbar', 'bbar', 'time', 'mult', 'mbar',
                 'abar', 'shbar', 'fbar', 'rank'):
        out.append(f'HUD_{name.upper()} = {fields[name]}')
    # the wall rows a HUD row covers (bit 0 left, bit 1 right): wall_page
    # leaves them alone, so the HUD on them needn't be drawn again
    cover = [0] * 24
    for col, r, _ in WALL:
        cover[r] |= 1 if col == LEFT else 2
    out.append('hud_cover: .byte ' + ','.join(map(str, cover)))
    out.append('hud_extra_i: .byte ' + ','.join(str(fields[f'extra{k}']) for k in range(5)))
    out.append('hud_mark_i:  .byte ' + ','.join(str(fields[f'mark{k}']) for k in range(6)))
    for name, values in (('hud_col', [c for c, _ in places]), ('hud_row', [r for _, r in places]),
                         ('hud_template', template)):
        out.append(f'{name}:')
        for i in range(0, len(values), 16):
            out.append('        .byte ' + ','.join(f'${v:02X}' for v in values[i:i + 16]))
    return '\n'.join(out) + '\n'


def main():
    text_ = emit()
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text() != text_:
            sys.exit(f'{OUT} is stale: run tools/hud.py')
        return
    if not OUT.exists() or OUT.read_text() != text_:
        OUT.write_text(text_)


if __name__ == '__main__':
    main()
