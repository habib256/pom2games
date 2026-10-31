#!/usr/bin/env python3
"""The hall of fame (src/hof.inc): initials entry, DIRTHOF's sectors, the table.

  * a record (finish line moved near the start, 1200 points), initials with
    the keys: DOWN wraps A to '-', RIGHT, UP UP (C), a typed 9 on the last
    letter (the cursor stays there), UP from 9 through space and '-' back
    to A, LEFT, DELETE, a lowercase z typed: "ZCA", cursor on the second
    letter; the letters and the '^' marker drawn under them;
  * RETURN saves: DIRTHOF's two data sectors (hof_t / hof_s, patched by
    dos33patch --sectors) hold DOS's 4-byte header untouched, then the
    table: the empty table of tools/hof.py except track 1's time, its
    initials, its points (BCD 001200) and their initials, and the last
    initials;
  * the stick: UP, the button (next letter), DOWN (A wraps to '-'), the
    button twice (next letter, then done): "B-A" saved;
  * the saved disk boots, ESC -> main menu -> 4: the hall of fame page shows
    track 1's time, ZCA, 001200, ZCA and track 2 empty (-:--.- --- 000000
    ---), glyph for glyph (dev/tools/fonts.py, white text).
"""
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
sys.path.insert(0, str(GAME / 'tools'))
import a2test  # noqa: E402
import dos33  # noqa: E402
import fonts  # noqa: E402
import hof  # noqa: E402

DISK = GAME.parent / 'dist/DIRTBIKE.dsk'
NT = hof.NTRACKS
REC_MIN, REC_SEC, REC_HUN = 4, 4 + NT, 4 + 2 * NT          # offsets in the payload
REC_INI, REC_PTS, REC_PINI, LAST_INI = 4 + 3 * NT, 4 + 6 * NT, 4 + 9 * NT, 4 + 12 * NT
UP, DOWN, LEFT, RIGHT, DELETE = '\x0b', '\x0a', '\x08', '\x15', '\x7f'


def race_to_record(L):
    """Title -> track 1; last lap, the finish line behind the bike, 1200
    points, the clock at 1:23.45: the record's initials are asked."""
    return ['joy:0,0', 'wait:1300', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900),
            L.until('main_loop', 60), L.poke('finish_x', 40), L.poke('finish_x', 0, 1), L.poke('laps', 2),
            L.poke('score', 0x00), L.poke('score', 0x12, 1), L.poke('score', 0x00, 2),
            L.poke('t_min', 1), L.poke('t_sec', 0x23), L.poke('t_hun', 0x45), 'wait:220', 'key: ', L.until('hof_entry', 300), 'wait:30']


def cells(page, col, sl, text):
    """Does HGR page `page` show `text` from byte column col, scanline sl?"""
    for k, ch in enumerate(text):
        g = fonts.glyph(ord(ch))
        for i in range(8):
            if page[a2test.hgr_offset(sl + i) + col + k] != g[i]:
                return False
    return True


def sectors(image, t, s):
    """DIRTHOF's two data sectors, joined (DOS order .dsk)."""
    return b''.join(image[(t[i] * 16 + s[i]) * 256:(t[i] * 16 + s[i] + 1) * 256] for i in (0, 1))


def main():
    L = a2test.labels(GAME / 'build/dirtbike.lbl')
    bad = 0
    empty = hof.empty()
    fresh = DISK.read_bytes()

    with tempfile.TemporaryDirectory(prefix='dirtbike-hof-') as tmp:
        # initials with the keys, drawn, then saved
        saved = Path(tmp) / 'saved.dsk'
        keys = [DOWN, RIGHT, UP, UP, RIGHT, '9', UP, UP, UP, LEFT, DELETE, 'z']
        steps = race_to_record(L) + [s for k in keys for s in (f'key:{k}', 'wait:5')]
        steps += [L.peek('last_ini', 3), L.peek('hpos', 1), 'peek:2000:8192', 'key:\r',
                  L.until('new_race', 900), L.peek('hof_t', 2), L.peek('hof_s', 2), f'dsk:{saved}']
        r = a2test.run(DISK, steps)
        ini, pos, page = r.mem(L['last_ini'], 3), r.mem(L['hpos'], 1)[0], r.mem(0x2000, 8192)
        drawn = cells(page, 24, 88, 'ZCA') and cells(page, 24, 98, ' ^ ')
        ok = ini == b'ZCA' and pos == 1 and drawn
        print(f'initials with the keys: {ini.decode()!r}, cursor {pos}, drawn {drawn}: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

        t, s = list(r.mem(L['hof_t'], 2)), list(r.mem(L['hof_s'], 2))   # (adjacent peeks merge)
        image = saved.read_bytes()
        raw = sectors(image, t, s)
        got = raw[4:4 + len(empty)]
        want = bytearray(empty)
        for off in (REC_MIN, REC_SEC, REC_HUN):
            want[off] = got[off]                    # the race's time, whatever it is
        want[REC_INI:REC_INI + 3] = want[REC_PINI:REC_PINI + 3] = want[LAST_INI:LAST_INI + 3] = b'ZCA'
        want[REC_PTS:REC_PTS + 3] = bytes([0x00, 0x12, 0x00])
        ok = (raw[:4] == sectors(fresh, t, s)[:4] and got[REC_MIN] == 1 and got[REC_SEC] >= 0x23 and got == bytes(want)
              and dos33.read_file(image, 'DIRTHOF') == got)
        time = f'{got[REC_MIN]}:{got[REC_SEC]:02x}.{got[REC_HUN] >> 4}'
        print(f'saved in DIRTHOF (T/S {t[0]}/{s[0]}, {t[1]}/{s[1]}): DOS header kept, time {time}, ZCA, 001200, '
              'the rest untouched: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

        # the stick: a push turns the letter, the button moves on, then ends
        stick = Path(tmp) / 'stick.dsk'
        push = ['joy:0,-1', 'wait:8', 'joy:0,0', 'wait:8']
        pull = ['joy:0,1', 'wait:8', 'joy:0,0', 'wait:8']
        btn = ['btn:0,1', 'wait:4', 'btn:0,0', 'wait:8']
        r = a2test.run(DISK, race_to_record(L) + push + btn + pull + btn + btn +
                       [L.until('new_race', 900), f'dsk:{stick}'])
        got = dos33.read_file(stick.read_bytes(), 'DIRTHOF')
        ok = got[REC_INI:REC_INI + 3] == b'B-A' and got[LAST_INI:LAST_INI + 3] == b'B-A'
        print(f'initials with the stick: {got[REC_INI:REC_INI + 3].decode()!r}: ' + ('ok' if ok else 'DIFF'))
        bad += not ok

        # the next boot: the table, from the main menu
        r = a2test.run(saved, ['wait:1000', 'key: ', 'wait:60', 'key:\r', L.until('new_race', 900), 'wait:60',
                               'key:\x1b', L.until('main_menu', 300), 'wait:20', 'key:4',
                               L.until('mm_wait', 300), 'peek:2000:8192'])
        page = r.mem(0x2000, 8192)
        row1, row2 = 34, 43
        ok = (cells(page, 14, 6, 'HALL OF FAME') and cells(page, 0, row1, '01') and
              cells(page, 18, row1, time) and cells(page, 25, row1, 'ZCA') and
              cells(page, 29, row1, '001200') and cells(page, 36, row1, 'ZCA') and
              cells(page, 0, row2, '02') and cells(page, 18, row2, '-:--.-') and cells(page, 25, row2, '---') and
              cells(page, 29, row2, '000000') and cells(page, 36, row2, '---'))
        print(f'next boot, main menu 4: the hall of fame shows 01 {time} ZCA 001200 ZCA / 02 empty: '
              + ('ok' if ok else 'DIFF'))
        bad += not ok
    if bad:
        sys.exit('hall of fame: failures')


if __name__ == '__main__':
    main()
