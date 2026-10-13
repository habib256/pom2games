#!/usr/bin/env python3
"""The 6502 DHGR view must match tools/dhgr_ref.py pixel for pixel after each turn.

Both banks are read (main, then aux through PAGE2). The reference colours the
band events of tools/view_ref.columns with the mood the game chose (sky_mood),
so geometry and palette are both checked; logical rows 0..159 are compared,
the cached rows 0..15 (physical 160..175) included.

Turns: LEFT / RIGHT on the empty command line (22.5 degrees, 5 groups = 10
bytes per bank scrolled), LOOK L / LOOK R (45 degrees, 20 bytes), LOOK B (180
degrees, full view), V (full view). On the generated map and, when it exists
locally, the original Sierra Nevada map (build/orig_map.bin). Also reports
the cycles of each frame.
"""
import sys, tempfile
from common import (terrain_boot, HERE, L, DISK, a2test, disk_with, state, DHGR_BANKS,
                    dhgr, dhgr_view, mood_name, view_diff)


def reference(mapbin, px, py, h, mood):
    R = dhgr()
    return R.view(mapbin, px, py, h, R.Sky(mood_name=mood_name(mood)), forest=False, sprites=False)

STEPS = [('', 0), ('\\>', 35), ('LOOK R\\r', 70), ('LOOK R\\r', 70), ('\\<', -35),
         ('LOOK L\\r', -70), ('LOOK B\\r', 280), ('\\>', 35), ('V\\r', 0)]


def run(disk, mapbin):
    probe = [L.peek('px', 6), L.peek('sky_mood'), *DHGR_BANKS]
    steps = [L.until('game_start', 4000), L.poke('forest_enabled', 0), L.poke('sky_enabled', 0), L.poke('scenes_enabled', 0), L.until('idle', 4000), *probe]
    for k, _ in STEPS[1:]:
        steps += [f'key:{k}', 'wait:1', L.until('idle', 4000), *probe]
    r = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    fails = 0
    head = mapbin[6] | mapbin[7] << 8
    for i, (k, turn) in enumerate(STEPS):
        head = (head + turn) % 560
        pos, mood, main, aux = r.dumps[4 * i:4 * i + 4]
        px, py, h = state(pos)
        bad, first = view_diff(dhgr_view(main, aux), reference(mapbin, px, py, h, mood))
        bad_head = h != head
        cyc = r.cycles[i] - (r.cycles[i - 1] if i else 0)
        print(f'  {k or "start":9} head {h:3} {mood_name(mood):8} '
              f'{"ok" if not (bad or bad_head) else f"{bad} pixels differ (first {first}), head {h} != {head}"}'
              f'  ({cyc / 1e6:.2f} Mcycles)')
        fails += bool(bad or bad_head)
    return fails


def reveal_order():
    """Pause a pan mid-frame: reveal from the retained view toward the edge."""
    completed = 20
    turns = [('\\<', -35), ('\\>', 35), ('LOOK L\\r', -70), ('LOOK R\\r', 70)]
    steps = [*terrain_boot(4000), L.poke('scenes_enabled', 0),
             L.poke('heading', 0), L.poke('heading', 0, 1),
             'key:V\\r', 'wait:1', L.until('idle', 4000)]
    for key, _ in turns:
        steps += [f'key:{key}', 'wait:1',
                  f'tracepc:{L["render_column_done"]:04X}:{completed}:4000',
                  L.peek('col'), L.peek('px', 6), L.peek('sky_mood'), *DHGR_BANKS,
                  L.until('idle', 4000), *DHGR_BANKS]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    mapbin = (HERE / 'build/map.bin').read_bytes()
    heading = 0
    for i, (key, turn) in enumerate(turns):
        heading = (heading + turn) % 560
        col, pos, mood, pmain, paux, fmain, faux = result.dumps[i * 7:i * 7 + 7]
        px, py, h = state(pos)
        assert h == heading
        count = abs(turn)
        last = count - completed if turn < 0 else 140 - count + completed - 1
        assert col == bytes([last]), f'{key}: wrong column reveal order'
        ref = reference(mapbin, px, py, h, mood)
        assert view_diff(dhgr_view(fmain, faux), ref)[0] == 0, f'{key}: final image differs'
        pending = range(count - completed) if turn < 0 else range(140 - count + completed, 140)
        expected = [list(row) for row in ref]
        for y in range(160):
            for c in pending:
                expected[y][c] = 0          # not painted yet: black in both banks
        assert view_diff(dhgr_view(pmain, paux), expected)[0] == 0, f'{key}: intermediate image differs'
    print('  pan reveal order (22.5 / 45 degrees, both directions, heading wrap, both banks): OK')


def main():
    fails = 0
    reveal_order()
    print('generated map')
    fails += run(DISK, (HERE / 'build/map.bin').read_bytes())
    orig = HERE / 'build/orig_map.bin'
    if orig.exists():
        print('original Sierra Nevada map (local only)')
        mapbin = bytearray(orig.read_bytes())
        mapbin[12:16] = bytes((38, 41, 77, 30))   # region climate: daytime
        with tempfile.TemporaryDirectory() as tmp:
            fails += run(disk_with(tmp, bytes(mapbin)), bytes(mapbin))
    print('FAIL' if fails else 'OK')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
