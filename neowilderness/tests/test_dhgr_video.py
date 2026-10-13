#!/usr/bin/env python3
"""Video modes of the DHGR game and its four mixed text rows (lots 3-4).

The view is DHGR page 1 + 4 mixed text rows (80STORE, HIRES, 80COL on, AN3
low, PAGE2 off). Lot 4: those rows are real 80-column text (even columns in
the aux page, odd ones in main), printed by the game's own primitives, never
by the Monitor's 80-column paths; MAP and the simulation curtain are
80-column text too; STATUS, INVENTORY and HELP stay 40-column text (80COL
off); TOPO is DHGR with its legend in the 80-column rows.
"""
from common import L, DISK, a2test, text_screen, result_rows

# Status bits read in bit 7 ($C07F, RDDHIRES, is not emulated by a2shot: AN3
# is left to the captures, tools/game_shots.py).
STATUS = {'80STORE': 'C018', 'TEXT': 'C01A', 'MIXED': 'C01B', 'PAGE2': 'C01C',
          'HIRES': 'C01D', '80COL': 'C01F'}
VIEW = dict(zip(STATUS, (1, 0, 1, 0, 1, 1)))
MENU = {'80STORE': 1, 'TEXT': 1, 'PAGE2': 0, '80COL': 0}
MAP = {'80STORE': 1, 'TEXT': 1, 'PAGE2': 0, '80COL': 1}
TOPO = VIEW
ROWS = (0x650, 0x6D0, 0x750, 0x7D0)          # text rows 20..23


def modes(s):
    return {name: s.step(f'peek:{addr}:1').data[0] >> 7 for name, addr in STATUS.items()}


def check(s, want, label):
    got = modes(s)
    bad = {k: (got[k], v) for k, v in want.items() if got[k] != v}
    assert not bad, (label, bad)


def aux_rows(s):
    s.step('poke:C055:00')
    rows = [s.step(f'peek:{a:04X}:40').data for a in ROWS]
    s.step('poke:C054:00')
    return rows


def main():
    idle = L.until('idle', 30000)
    with a2test.Session(DISK) as s:
        s.step(idle)
        check(s, VIEW, 'view after boot')
        text = text_screen(s.step('peek:0400:1024').data)
        assert len(text[20]) == 80 and result_rows(text)[0].startswith('CRASH IN SIERRA NEVADA USA.'), text[20:]
        aux = aux_rows(s)
        assert aux[0][20] == ord('C') | 0x80, 'even columns live in the aux page'
        # Results fill the result column (rows 20..22, columns 40..78), in
        # 80-column layout; the command line is row 23 (src/menu.s).
        for word in ('XYZZY', 'PLUGH', 'FOO'):
            s.step(f'key:{word}\\r')
            s.step('wait:1')
            s.step(idle)
        text = text_screen(s.step('peek:0400:1024').data)
        assert 'UNKNOWN VERB: FOO' in result_rows(text)[0], text[20:]
        check(s, VIEW, 'view after messages')
        s.step('key:STATUS\\r')
        s.step('wait:1')
        s.step(L.until('wait_key', 20000))
        check(s, MENU, 'STATUS page')
        assert text_screen(s.step('peek:0400:1024').data)[0].startswith('STATUS:')
        s.step('key:\\e')
        s.step('wait:1')
        s.step(idle)
        check(s, VIEW, 'view after STATUS')
        rows = text_screen(s.step('peek:0400:1024').data)[20:]
        assert not any(r.strip() for r in result_rows(rows)[:3]) and result_rows(rows)[3].startswith('FOOD'), ('result column cleared', rows)
        s.step('key:TOPO\\r')
        s.step('wait:1')
        s.step(L.until('graphical_topo_key', 20000))
        check(s, TOPO, 'TOPO')
        assert text_screen(s.step('peek:0400:1024').data)[20].startswith('TOPO  N UP')
        s.step('key:\\r')
        s.step('wait:1')
        s.step(idle)
        check(s, VIEW, 'view after TOPO')
        s.step('key:MAP\\r')
        s.step('wait:1')
        s.step(L.until('topo_key', 20000))
        check(s, MAP, 'MAP')
        assert text_screen(s.step('peek:0400:1024').data)[0].startswith('MAP P YOU')
        s.step('key:\\e')
        s.step('wait:1')
        s.step(idle)
        check(s, VIEW, 'view after MAP')
    print('  view DHGR + 80-column mixed rows (both text pages), STATUS 40-column text, '
          'MAP 80-column text, TOPO DHGR with its legend, returns: OK')


if __name__ == '__main__':
    main()
