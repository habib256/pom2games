#!/usr/bin/env python3
"""The hall of fame inside the game (after the integration of docs/HOF.md).

On ../dist/NEOWILDERNESSXL.po (a2shot --iie, the six scenarios), with build/wild.lbl:
  1. menu: the BEST cells and the H screen of an empty NEOWILD.HOF;
  2. Sierra Nevada, level 4: the player is moved three cells west of the
     outpost, QUIT, Y: NEOWILD.END runs, its screen equals
     tools/score_ref.py for the values it gathered (outcome, level, region,
     DONE%, health, hours), a name is typed and saved;
  3. back at the menu (module_restart, fresh loader): BEST of the Sierra and
     the H screen show the entry, read from NEOWILD.HOF;
  4. free journey: QUIT, Y: "NOT RANKED", no NEOWILD.HOF access.
SKIP while the game has no hall of fame (no hof_key_wait in build/wild.lbl or
no NEOWILD.END on the volume).

  test_hof_game.py [DISK.po [wild.lbl]]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'dev/tools'))
sys.path.insert(0, str(HERE / 'tests'))
import a2test  # noqa: E402
import score as R  # noqa: E402

DISK = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'dist/NEOWILDERNESSXL.po'   # six scenarios in the hall
LABELS = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'build/wild.lbl'
MAP, STAGE = 0x7000, 0x2000


def screen(mem):
    return b''.join(mem[0x80 * (r & 7) + 40 * (r >> 3):][:40] for r in range(24))


def show(codes):
    return '\n'.join(''.join(chr(b & 0x7F if b >= 0x80 else (b | 0x40 if b < 0x20 else b))
                             for b in codes[r * 40:r * 40 + 40]) for r in range(24))


def xl_end(codes):
    """NEOWILD.END's screen on NeoWildernessXL (docs/MENUS.md 9) from the
    oracle's plain one: the title band a double line ($5C) around the
    inverse title, the total's dashes a MouseText line ($53), and the table
    of the scenario in a box: its title in inverse with a space each side,
    then '_'; rows 15-19 between the bars $5F (column 0) and $5A (column
    39), their text from column 1; row 20 the bottom line ($4C); the
    breakdown a post-it too (rows 2-13)."""
    b = bytearray(codes)
    hi = bytes(x | 0x80 for x in range(256))
    # The breakdown's post-it (15 October 2026): row 2 its title (the
    # region, the level) in inverse after a space, then '_'; rows 3-12 between
    # the bars, their text from column 1 up to column 27, the values (column
    # 28 on) in place; row 13 the line $4C.
    title = bytes(b[2 * 40:3 * 40]).rstrip(b'\xa0')
    inverse = bytes(ch & 0x3F for ch in b' '.translate(hi) + title + b'\xa0')
    b[2 * 40:3 * 40] = inverse + bytes([0xDF] * (40 - len(inverse)))
    for r in range(3, 13):
        line = b[r * 40:r * 40 + 40]
        assert line[27] == line[39] == 0xA0, (r, line)
        b[r * 40:r * 40 + 40] = bytes([0x5F]) + line[:27] + line[28:39] + bytes([0x5A])
    assert b[13 * 40:14 * 40] == b'\xa0' * 40
    b[13 * 40:14 * 40] = bytes([0x4C] * 40)
    for c in list(range(13)) + list(range(26, 40)):
        assert b[c] == 0x20, ('title band', c, b[c])
        b[c] = 0x5C
    assert b[9 * 40 + 28:9 * 40 + 33] == b'-----'.translate(bytes(x | 0x80 for x in range(256)))
    b[9 * 40 + 28:9 * 40 + 33] = bytes([0x53] * 5)
    title = bytes(b[14 * 40:15 * 40]).rstrip(b'\xa0')
    if title.endswith(b' - TOP 5'.translate(bytes(x | 0x80 for x in range(256)))):
        inverse = bytes(ch & 0x3F for ch in b' ' .translate(bytes(x | 0x80 for x in range(256))) + title + b'\xa0')
        b[14 * 40:15 * 40] = inverse + bytes([0xDF] * (40 - len(inverse)))
        for r in range(15, 20):
            line = b[r * 40:r * 40 + 40]
            assert line[38:] == b'\xa0\xa0', (r, line)
            b[r * 40:r * 40 + 40] = bytes([0x5F]) + line[:38] + bytes([0x5A])
        assert b[20 * 40:21 * 40] == b'\xa0' * 40
        b[20 * 40:21 * 40] = bytes([0x4C] * 40)
    return bytes(b)


def check(label, got, want):
    assert got == want, f'{label}\n--- got\n{show(got)}\n--- want\n{show(want)}'


def main():
    if sys.platform != 'darwin' or not a2test.A2SHOT.exists():
        print('SKIP: a2shot (IIe POM2 core) is required')
        return
    L = a2test.labels(LABELS)
    names = set(a2test.prodos_files(DISK))
    if 'hof_key_wait' not in L or not {'NEOWILD.END', 'NEOWILD.HOF'} <= names:
        print('SKIP: the game has no hall of fame yet (docs/HOF.md, integration)')
        return
    with a2test.Session(DISK, iie=True, timeout=1200) as s:
        text = lambda: screen(s.step('peek:0400:1024').dumps[0])  # noqa: E731
        s.step(L.until('menu_key', 40000))
        hof = s.step(f'peek:{STAGE:04X}:512').dumps[0]
        assert R.Hof(hof).valid() and R.menu_best_cells(hof) == {}
        s.step('key:H')
        s.step(L.until('menu_key', 4000))
        check('H screen, empty', text(), R.hall_screen(hof).bytes())
        s.step('key: ')
        s.step(L.until('menu_key', 4000))
        s.step('key:1\r')            # menu key 1: the Sierra Nevada (region 2)
        s.step(L.until('idle', 40000))
        goal = s.step(f'peek:{MAP + 8:04X}:2').dumps[0]
        s.step(f"poke:{L['px'] + 1:04X}:{goal[0] - 3:02X}")
        s.step(f"poke:{L['py'] + 1:04X}:{goal[1]:02X}")
        s.step('key:QUIT\r')
        s.step('wait:30')
        s.step('key:Y')
        s.step(L.until('hof_key_wait', 20000))
        v = s.step(L.peek('hof_outcome', 8)).dumps[0]
        outcome, level, region, kind, progress, health = v[:6]
        hours = v[6] | v[7] << 8
        assert (outcome, level, region, kind) == (R.ABANDONED, 4, 2, 0), v
        assert 90 <= progress < 100 and health == 100, (progress, health)
        c = R.score(progress, health, hours, outcome, level)
        want, _ = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), '', phase='entry')
        check('name entry', text(), xl_end(want.bytes()))       # (XL: docs/MENUS.md 9)
        for k in 'GIST\r':
            s.step('key:' + k)
            s.step(L.until('hof_key_wait', 4000))
        want, new = R.end_screen(c, 2, 'SIERRA NEVADA', False, R.empty_file(), 'GIST')
        check('saved', text(), xl_end(want.bytes()))
        s.step('key: ')
        s.step(L.until('menu_key', 40000))
        hof = s.step(f'peek:{STAGE:04X}:512').dumps[0]
        assert hof == new, 'NEOWILD.HOF read back by the restarted loader'
        menu = text()
        assert menu[2 * 40 + 35:2 * 40 + 40] == bytes(ord(ch) | 0x80 for ch in f"{c['score']:>5}")   # the Sierra's row
        s.step('key:H')
        s.step(L.until('menu_key', 4000))
        check('H screen, one entry', text(), R.hall_screen(new).bytes())
        s.step('key: ')
        s.step(L.until('menu_key', 4000))
        s.step('key:72\r')
        s.step(L.until('idle', 40000))
        before = s.step(L.peek('mli_calls', 2)).dumps[0]
        s.step('key:QUIT\r')
        s.step('wait:30')
        s.step('key:Y')
        s.step(L.until('hof_key_wait', 20000))
        after = s.step(L.peek('mli_calls', 2)).dumps[0]
        calls = (after[0] | after[1] << 8) - (before[0] | before[1] << 8)
        assert calls == 3, f'free journey: only OPEN/READ/CLOSE of NEOWILD.END ({calls})'
        assert show(text()).split('\n')[21].startswith(R.MSG_FREE)
    print(f"  Sierra QUIT near the outpost: score {c['score']}, saved, BEST and H screen after "
          f"the restart; free journey not ranked: OK")
    print('Hall of fame in the game: OK')


if __name__ == '__main__':
    main()
