#!/usr/bin/env python3
"""Video modes of the DHGR game (lot 3) and its four mixed text rows.

The view is DHGR page 1 + 4 mixed text rows (80STORE, HIRES, 80COL on, AN3
low, PAGE2 off); menus are 40-column text (80COL off); TOPO is single HGR.
Under DHGR the text rows are 80-column cells: the game keeps its 40-column
text page in main RAM (odd cells) and spaces in the aux page (even cells),
printed by its own primitives, never by the Monitor's 80-column paths.
"""
from common import L, DISK, a2test, text_screen

# Status bits read in bit 7 ($C07F, RDDHIRES, is not emulated by a2shot: AN3
# is left to the captures, tools/game_shots.py).
STATUS = {'80STORE': 'C018', 'TEXT': 'C01A', 'MIXED': 'C01B', 'PAGE2': 'C01C',
          'HIRES': 'C01D', '80COL': 'C01F'}
VIEW = dict(zip(STATUS, (1, 0, 1, 0, 1, 1)))
MENU = {'80STORE': 1, 'TEXT': 1, 'PAGE2': 0, '80COL': 0}
TOPO = {'80STORE': 1, 'TEXT': 0, 'MIXED': 1, 'PAGE2': 0, 'HIRES': 1, '80COL': 0}
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
        assert all(row == b'\xa0' * 40 for row in aux_rows(s)), 'even 80-column cells must be spaces'
        text = text_screen(s.step('peek:0400:1024').data)
        assert text[21].startswith('> CRASH. REACH THE RANGERS.'), text[20:]
        # Messages scroll inside the four rows, in 40-column layout.
        for word in ('XYZZY', 'PLUGH', 'FOO'):
            s.step(f'key:{word}\\r')
            s.step('wait:1')
            s.step(idle)
        text = text_screen(s.step('peek:0400:1024').data)
        assert text[20].startswith('? '), text[20:]
        assert all(row == b'\xa0' * 40 for row in aux_rows(s)), 'aux cells changed by printing'
        check(s, VIEW, 'view after messages')
        s.step('key:STATUS\\r')
        s.step('wait:1')
        s.step(L.until('wait_key', 20000))
        check(s, MENU, 'STATUS page')
        s.step('key:\\e')
        s.step('wait:1')
        s.step(idle)
        check(s, VIEW, 'view after STATUS')
        s.step('key:TOPO\\r')
        s.step('wait:1')
        s.step(L.until('graphical_topo_key', 20000))
        check(s, TOPO, 'TOPO')
        s.step('key:\\r')
        s.step('wait:1')
        s.step(idle)
        check(s, VIEW, 'view after TOPO')
        s.step('key:MAP\\r')
        s.step('wait:1')
        s.step(L.until('topo_key', 20000))
        check(s, MENU, 'MAP')
        s.step('key:\\e')
        s.step('wait:1')
        s.step(idle)
        check(s, VIEW, 'view after MAP')
        assert all(row == b'\xa0' * 40 for row in aux_rows(s))
    print('  view DHGR + 80-column mixed rows (aux cells blank, 40-column page kept), '
          'STATUS/MAP 40-column text, TOPO single HGR, returns: OK')


if __name__ == '__main__':
    main()
