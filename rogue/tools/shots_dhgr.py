#!/usr/bin/env python3
"""The README's ROGUE.DHGR pictures, from the game itself (a2shot //e).

    python3 tools/shots_dhgr.py [DIR]          (default: screenshots/)

Writes dhgr_x2_<scene>.png (the page shown, 560 x 384) after checking each
against tools/x2_dhgr.py's model (tests/test_dhgr.py's oracle):

  title     the title page and its banner
  game      the first dungeon (test_dhgr.py's pinned PRNG): hero, monster,
            ration, rubble, walls, door
  hit       the hero next to a monster, bumping it: both flash (a hit)
  stairs    the hero beside the stairs down
  boss      the demon's room (the title's hidden B), the hero facing it
  bag       the bag (a full one: the icons)
"""
import sys
import tempfile
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GAME / 'tests'))
sys.path.insert(0, str(GAME.parent / 'dev/tools'))
import a2test  # noqa: E402
import test_dhgr as T  # noqa: E402

MON_HP = 1


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else GAME / 'screenshots'
    out.mkdir(parents=True, exist_ok=True)
    L = a2test.labels(T.LBL)
    wk = L['wait_key'] + 3
    with tempfile.TemporaryDirectory(prefix='rogue-shots-') as work:
        disk = a2test.build_disk(work, 'ROGUE.DHGR', T.BIN, load=L['entry'])
        for boss in (False, True):
            with a2test.Session(disk, iie=True, timeout=300) as s:
                def shot(tag):
                    o = ''.join(s.step(st).out for st in T.screen_steps(L))
                    ok = T.oracle(o, L, f'x2_{tag}', out, record=False)[0]
                    print(f'{tag}: {"ok" if ok else "DIFFERS FROM THE MODEL"}')

                def turn(key):
                    s.step(L.poke('hp', 14))
                    s.step(f'press:{key}')
                    s.step('wait:2')
                    s.step(f'until:{wk:04X}:900')

                def mons():
                    m = s.step(L.peek('monsters', T.MON_COUNT * T.MON_SIZE)).dumps[0]
                    return [(m[i], m[i + T.MON_COL], m[i + T.MON_ROW], i)
                            for i in range(0, len(m), T.MON_SIZE) if m[i]]

                def cell(c, r):
                    mp = s.step(L.peek('map_buffer', 80)).dumps[0]
                    b = mp[8 * r + c // 2]
                    return (b >> 4 if c & 1 else b) & 7

                def put(c, r):
                    s.step(L.poke('player_col', c))
                    s.step(L.poke('player_row', r))

                s.step(f'until:{L["wait_kb_choice"]:04X}:3000')
                s.step(f'until:{L["vid_idle"] + 7:04X}:600')
                if not boss:
                    shot('title')
                s.step('key:' + ('B' if boss else ' '))
                s.step('wait:200')
                s.step('press: ')
                s.step(f'until:{L["key_xlate"]:04X}:300')
                s.step(L.poke('prng_lo', T.SEED & 255))
                s.step(L.poke('prng_hi', T.SEED >> 8))
                s.step(f'until:{wk:04X}:900')
                def approach(c, r, gap):
                    """The hero `gap` cells left (or right, above, below)
                    of (c, r) after one real step (the field of view is
                    computed by a move): its key."""
                    for dc, dr, key in ((-1, 0, 'L'), (1, 0, 'J'), (0, -1, 'K'), (0, 1, 'I')):
                        p1 = (c + dc * gap, r + dr * gap)
                        p0 = (c + dc * (gap + 1), r + dr * (gap + 1))
                        if all(0 < x < 15 and 0 < y < 9 and cell(x, y) == T.TILE_EMPTY
                               for x, y in (p0, p1)):
                            put(*p0)
                            turn(key)
                            return key
                    return None

                if boss:
                    t, c, r, _ = next(x for x in mons() if x[0] == 6)
                    approach(c, r, 2) or approach(c + 1, r + 1, 2)
                    shot('boss')
                    continue
                shot('game')
                # stairs: the hero beside them
                stairs = next((c, r) for r in range(10) for c in range(16)
                              if cell(c, r) == T.TILE_STAIRS_DOWN)
                approach(*stairs, 1)
                shot('stairs')
                # a hit: the hero beside a monster, bumping it (it survives)
                _, c, r, i = mons()[0]
                s.step(f'poke:{L["monsters"] + i + MON_HP:04X}:30')
                approach(c, r, 1)
                for _ in range(12):             # bump a neighbour until a hit shows
                    pc, pr = s.step(L.peek('player_col', 2)).dumps[0]
                    near = [{(1, 0): 'L', (-1, 0): 'J', (0, 1): 'K', (0, -1): 'I'}.get((c2 - pc, r2 - pr))
                            for _, c2, r2, _ in mons()]
                    near = [k for k in near if k]
                    turn(near[0] if near else '.')
                    sat = s.step('peek:1B00:128').dumps[0]
                    if any(sat[k + 3] == 8 and sat[k] < 160 for k in range(0, 128, 4)
                           if sat[k] != 0xD0):
                        break
                shot('hit')
                # the bag, full
                inv = L['inventory']
                for slot, typ in enumerate((1, 2, 3, 4, 6, 8)):
                    for off, val in ((0, typ), (1, 0), (2, 1), (3, 2)):
                        s.step(f'poke:{inv + 8 * slot + off:04X}:{val:02X}')
                turn('B')
                shot('bag')
    if T.FAIL:
        sys.exit(f'{len(T.FAIL)} failure(s)')


if __name__ == '__main__':
    main()
