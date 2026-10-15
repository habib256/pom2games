#!/usr/bin/env python3
"""ALTCHARSET on NeoWildernessXL (docs/MENUS.md 9.2), user report of 15
October 2026: "au démarrage, utiliser la flèche haute mène au STATUS sans
les caractères MouseText".

The loader raised ALTCHARSET ($C00F) before the Monitor's SETVID, INIT and
HOME; the IIc's SETVID ($FE93 falls into a `STA $C00E`) turns it off again,
so the first STATUS (UP right after the start) and the grid showed inverse
letters until CRAFT raised it. `start` (src/boot.s) raises it again on XL,
after every ROM call of the loader. The emulator here is an enhanced IIe:
the IIc's SETVID is played by a write to $C00E at the start menu.

- XL, first thing after the start (UP, the STATUS page): ALTCHARSET on
  ($C01E bit 7), MouseText codes ($40-$5F) on the page, the footer line;
- after SAVE and RESTORE; after QUIT, the start menu and a new journey;
  after the hall of fame (H at the start menu) and a new journey;
- 140 KB: ALTCHARSET stays off, no MouseText code on its pages.
"""
import sys

from common import L, DISK, DISK140, a2test, text_screen

LIMIT = 40000
fails = []


def check(name, ok, detail=''):
    print(f'  {name}: {"OK" if ok else "FAIL"}' + (f' {detail}' if not ok and detail != '' else ''))
    if not ok:
        fails.append(name)


def alt(s):
    return s.step('peek:C01E').data[0] >= 0x80


def mousetext(codes):
    return sum(0x40 <= c < 0x60 for c in codes)


def status(s, label, xl):
    """UP at the prompt: the STATUS page, then ESC back to the view."""
    s.step('press:\\^')
    s.step(L.until('status_key', LIMIT))
    s.step('wait:2')
    codes = s.step('peek:0400:1024').data       # the main half: odd columns
    rows = text_screen(codes)
    on = alt(s)
    if xl:
        check(f'{label}: STATUS with ALTCHARSET on and MouseText',
              on and mousetext(codes) > 50 and '─' * 20 in rows[22], (on, mousetext(codes), rows[22]))
    else:
        check(f'{label}: STATUS, primary set, no MouseText code', not on and mousetext(codes) == 0,
              (on, mousetext(codes)))
    s.step('press:\\e')
    s.step(L.until('idle', LIMIT))


def start(s, choice='1', iic=True):
    s.step(L.until('menu_key', LIMIT))
    if iic:
        s.step('poke:C00E:00')                  # the IIc's SETVID, in the loader
    s.step(f'key:{choice}\r')
    s.step(L.until('idle', LIMIT))


def typed(s, text, answer=None):
    s.step(f'key:{text}')
    s.step('press:\\r')
    s.step('wait:2')
    for _ in range(20):
        r = s.step(f'until:{L["idle"]:04X},{L["keyboard_wait"]:04X}:{LIMIT}')
        if r.out.rstrip().endswith(f'PC={L["idle"]:04X}'):
            return
        s.step(f'key:{answer}' if answer else 'press: ')
        answer = None
        s.step('wait:2')
    raise AssertionError(f'{text}: no prompt')


def to_menu(s):
    """QUIT, the score screen (ESC: not recorded, a key), the start menu."""
    s.step('key:QUIT\\r')
    s.step('wait:30')
    s.step('key:Y')
    keys = iter(['key:\x1b', 'key: '] + ['key: '] * 10)
    for _ in range(40):
        s.step(f'until:{L["hof_key_wait"]:04X},{L["menu_key"]:04X}:{LIMIT}')
        rows = text_screen(s.step('peek:0400:1024').data)
        if any('CHOOSE A JOURNEY' in row for row in rows):
            return
        if any('JOURNEY SCORE' in row or 'HALL OF FAME' in row for row in rows):
            s.step(next(keys))
        s.step('wait:2')
    raise AssertionError('QUIT: no start menu')


def xl():
    print(' NeoWildernessXL:')
    with a2test.Session(DISK, menu=False) as s:
        start(s)
        check('the start (the IIc\'s SETVID played): ALTCHARSET on at the prompt', alt(s))
        status(s, 'UP first thing', True)
        typed(s, 'SAVE', answer='1\\r')
        typed(s, 'RESTORE 1')
        check('after RESTORE: ALTCHARSET on', alt(s))
        status(s, 'after RESTORE', True)
        to_menu(s)
        s.step('poke:C00E:00')
        s.step('key:1\r')
        s.step(L.until('idle', LIMIT))
        check('after QUIT and a new journey: ALTCHARSET on', alt(s))
        status(s, 'after QUIT', True)
        to_menu(s)
        s.step('key:H')                          # the hall of fame, then back
        s.step('wait:60')
        for _ in range(10):
            rows = text_screen(s.step('peek:0400:1024').data)
            if any('CHOOSE A JOURNEY' in row for row in rows):
                break
            s.step('key: ')
            s.step('wait:30')
        check('the hall of fame, then the start menu', any('CHOOSE A JOURNEY' in r for r in rows))
        s.step('poke:C00E:00')
        s.step('key:1\r')
        s.step(L.until('idle', LIMIT))
        check('after the hall of fame and a new journey: ALTCHARSET on', alt(s))
        status(s, 'after the hall of fame', True)


def neo140():
    print(' Neowilderness (140 KB):')
    with a2test.Session(DISK140, menu=False) as s:
        start(s, '\r', iic=False)
        check('the start: ALTCHARSET off', not alt(s))
        status(s, 'UP first thing', False)


def main():
    xl()
    neo140()
    print('ALTCHARSET: ' + ('OK' if not fails else 'FAILED: ' + '; '.join(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
