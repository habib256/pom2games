#!/usr/bin/env python3
"""LOOK UP / LOOK DOWN of the original (docs/LOOK_UPDOWN.md, Réalisation).

Drives the original (build/SIERRA.woz + build/JOURNEY.dsk, tools/re_surv_run)
from the crash site: START, LOOK U, LOOK F, LOOK D, PAN and the commands that
keep or level the tilt, and reads $E7 after each. Then compares the first
view at the three tilts with tools/view_ref on the Sierra comparison map
(tests/test_adventure.original_map: the original TOPO, 112 x 84 cells):
per column, the first non-sky row of the original's HGR page against the
oracle's sky bottom, and the Sun and wreck rows. The port's terrain is a
coarser grid, so the profiles differ at level by a few rows; the tilt must
move both by the same amount. Results in build/re_tilt/ (ignored).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'tests'))
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
from re_surv_run import play  # noqa: E402
from hgr_tables import hgr_offset  # noqa: E402
import view_ref  # noqa: E402

OUT = HERE / 'build/re_tilt'


def pairs(mem):
    """HGR page 1 as 192 rows x 140 pixel pairs (even, odd)."""
    rows = []
    for r in range(192):
        bits = []
        for b in mem[0x2000 + hgr_offset(r):0x2000 + hgr_offset(r) + 40]:
            bits += [(b >> k) & 1 for k in range(7)]
        rows.append([(bits[2 * c], bits[2 * c + 1]) for c in range(140)])
    return rows


def sky_bottom(p, col, sky=(1, 0)):
    for r in range(160):
        if p[r][col] != sky:
            return r
    return 160


def white_rows(p, cols, rows=range(160)):
    found = [r for r in rows for c in cols if p[r][c] == (1, 1)]
    return (min(found), max(found)) if found else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    commands = ['LOOK U', 'LOOK F', 'LOOK D', 'LOOK U', 'LOOK R', 'VIEW', 'LOOK D', 'LOOK F',
                'PAN U', 'PAN U', 'PAN D', 'PAN D', 'PAN D', 'PAN F', 'LOOK B', 'LOOK U',
                'USE COMPASS', 'LOOK N', 'LOOK AZ|72', 'LOOK D', 'REST|1']
    dumps = play(OUT / 'o', commands)
    tilts = [m[0xE7] for m in dumps]
    log = [dict(command=c, e7=t, hour=m[0x4C57:0x4C5C].hex())
           for c, t, m in zip(['START'] + commands, tilts, dumps)]
    for row in log:
        print(f"  {row['command']:12} $E7 = {row['e7']:02X}  clock {row['hour']}")
    import test_adventure
    m = test_adventure.original_map()
    px, py = int.from_bytes(m[2:4], 'little'), int.from_bytes(m[4:6], 'little')
    heading = int.from_bytes(m[6:8], 'little')
    level, up, down = (pairs(dumps[i]) for i in (0, 1, 3))
    report = {'commands': log}
    for name, p, tilt in (('level', level, 0), ('up', up, 1), ('down', down, -1)):
        tops = [sky_bottom(p, c) for c in range(140)]
        ref = [next(r1 for k, r0, r1, n in col if k == 'sky')
               for col in view_ref.columns(m, px, py, heading, tilt)]
        both = [(a, b) for a, b in zip(tops, ref) if 0 < a < 160 and 0 < b < 160]
        mean = sum(a - b for a, b in both) / len(both) if both else None
        report[name] = dict(original=tops, oracle=ref, columns=len(both), mean_difference=mean)
        print(f'  {name:5}: {len(both)} columns with terrain in both views, '
              f'original - oracle = {mean:+.1f} rows' if both else f'  {name}: no common ridge')
    # The Sun (columns 3..8 at level) and the wreck (white, columns 80..139).
    sun_level, sun_up = white_rows(level, range(3, 9), range(0, 95)), white_rows(up, range(3, 9))
    wreck_level = white_rows(level, range(100, 113), range(100, 160))
    wreck_down = white_rows(down, range(100, 113), range(40, 160))
    summit_level = min(r for c in range(60, 80) for r in [sky_bottom(level, c)])
    summit_up = min(r for c in range(60, 80) for r in [sky_bottom(up, c)])
    report.update(sun=(sun_level, sun_up), wreck=(wreck_level, wreck_down),
                  summit=(summit_level, summit_up))
    print(f'  Sun rows level {sun_level}, up {sun_up}; summit {summit_level} -> {summit_up}; '
          f'wreck rows (columns 100-112) level {wreck_level}, down {wreck_down}')
    (OUT / 'report.json').write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
