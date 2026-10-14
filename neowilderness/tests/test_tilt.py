#!/usr/bin/env python3
"""LOOK UP / LOOK DOWN (docs/LOOK_UPDOWN.md): the tilted views against the
Python oracle, the commands, and the hidden rows of the menu.

- six maps x three tilts (LOOK U, LOOK D, LOOK F through the parser), the
  view of the 6502 = tools/dhgr_ref.view(tilt) bit for bit (logical rows
  0..159, cache rows included): the generated map, flat, cliffs, noise, a
  legacy map, and a summit-and-cliff map (a near summit clamped to the top
  row at level, a deep valley below the view at level);
- trees and a distant billboard (the wreck seen from three cells) at the
  three tilts, then the scrolled columns of LOOK L / LOOK R while tilted;
- a Sun 68 degrees high: hidden at level (row -24), drawn looking up
  (row 72), never looking down;
- commands: LOOK/PAN U, D, F as the original ($E7 of SURV3D $0FA9), no game
  time, refusal "NOT NOW!" with a standing animal at contact (not with a
  snake), inside the cabin nothing changes, LOOK B and WALK level the view;
- the six regions: HGR rows 176..191 of both banks (the sleeping grid of
  the menu, MENUSWAP) are identical before and after LOOK U and LOOK D;
- render cycles of a full view at the three tilts (printed).
"""
import re
import tempfile

from common import (HERE, L, DISK, a2test, disk_with, terrain_boot, dhgr_view, dhgr_scene,
                    view_diff, mood_name, menu_keys, text_screen, result_text, dhgr)

MAP = (HERE / 'build/map.bin').read_bytes()
SX = int.from_bytes(MAP[2:4], 'little')
SY = int.from_bytes(MAP[4:6], 'little')
HEAD = int.from_bytes(MAP[6:8], 'little')
IDLE = L.until('idle', 20000)
COMMANDS = [('LOOK U', 1), ('LOOK D', -1), ('LOOK F', 0)]


def command(c):
    return [f'key:{c}\r', 'wait:1', IDLE]


def maps():
    flat = bytearray(MAP)
    flat[64:] = bytes([10]) * 9408
    flat[21] = 11
    cliffs = bytearray(MAP)
    cliffs[64:] = bytes(125 if (x // 7 + y // 5) % 3 == 0 else 0
                        for y in range(84) for x in range(112))
    cliffs[21] = 126
    import random
    rng = random.Random(917)
    noise = bytearray(MAP)
    noise[64:] = bytes(rng.randrange(126) | (0x80 if rng.random() < .05 else 0)
                       for _ in range(9408))
    noise[21] = 126
    legacy = bytearray(flat)
    legacy[21] = 0
    # Summit and cliff: the player on a pillar at level 60 (the plateau west),
    # facing east; ten cells ahead a summit of level 87 (dz 25 at n 10:
    # q = 640, row -25: the top row at level, row 71 looking up); around it
    # a valley at level 0 (dz -62: |q| >= 512 below the view at level up to
    # n = 30, rows 147..96 looking down from n = 12).
    sx, sy = SX >> 8, SY >> 8
    summit = bytearray(MAP)
    summit[64:] = bytes((87 if sx + 10 <= x <= sx + 11 and abs(y - sy) <= 2 else
                         0 if x >= sx and (x, y) != (sx, sy) else 60)
                        for y in range(84) for x in range(112))
    summit[6:8] = (140).to_bytes(2, 'little')
    summit[21] = 126
    return [('generated', MAP), ('flat', flat), ('cliffs', cliffs), ('noise', noise),
            ('legacy flat', legacy), ('summit and cliff', summit)]


def head_of(mapbin):
    return int.from_bytes(mapbin[6:8], 'little')


def check_maps():
    for name, mapbin in maps():
        steps = list(terrain_boot(20000))
        for c, _ in COMMANDS:
            steps += command(c) + ['peek:2000:8192', L.peek('sky_mood'), L.peek('tilt')]
        with tempfile.TemporaryDirectory() as tmp:
            r = a2test.run(disk_with(tmp, bytes(mapbin)), steps, emulator=a2test.A2SHOT, timeout=900)
        shown = []
        for i, (c, tilt) in enumerate(COMMANDS):
            page, mood, got = r.dumps[3 * i:3 * i + 3]
            assert got[0] == tilt & 255, (name, c, got[0])
            want = dhgr_scene(mapbin, SX, SY, head_of(mapbin), mood_name(mood), tilt=tilt)
            n, first = view_diff(dhgr_view(page), want)
            assert not n, f'{name} {c}: {n} pixels differ, first {first}'
            shown.append(page)
        assert shown[0] != shown[2] and shown[1] != shown[2], name
        print(f'  {name}: LOOK U, LOOK D, LOOK F = dhgr_ref(tilt 1, -1, 0): OK')
    # The summit map exercises the slopes the level view clamps or hides.
    _, summit = maps()[-1]
    R = dhgr()
    import view_ref
    level, up, down = (view_ref.columns(summit, SX, SY, 140, t) for t in (0, 1, -1))
    ridges = lambda ev, col: [(r0, n) for k, r0, r1, n in ev[col] if k == 'ridge']
    assert (0, 10) in ridges(level, 70) and (71, 10) in ridges(up, 70), 'summit: clamped at level only'
    valley = lambda ev: [n for n in (n for r, n in ridges(ev, 10)) if 12 <= n <= 30]
    assert not valley(level) and valley(down), 'cliff: the valley appears looking down'


def check_scene():
    """Trees and a distant billboard (the wreck from three cells west)."""
    x, y = SX - 3 * 256, SY
    steps = [L.until('game_start', 20000), L.poke('sky_enabled', 0), L.poke('ui_enabled', 0), IDLE]
    for n, v in [('px', x), ('py', y), ('heading', 140)]:
        steps += [L.poke(n, v), L.poke(n, v >> 8, 1)]
    cases = [('VIEW', 0)] + COMMANDS[:2] + [('LOOK R', -1), ('LOOK L', -1), ('PAN U', 0),
                                            ('PAN U', 1), ('LOOK L', 1), ('PAN D', 0)]
    for c, _ in cases:
        steps += command(c) + ['peek:2000:8192', L.peek('sky_mood'), L.peek('heading', 2),
                               L.peek('scene_drawn')]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    for i, (c, tilt) in enumerate(cases):
        page, mood, head, drawn = r.dumps[4 * i:4 * i + 4]
        h = int.from_bytes(head, 'little')
        want = dhgr_scene(MAP, x, y, h, mood_name(mood), forest=True, tilt=tilt)
        n, first = view_diff(dhgr_view(page), want)
        assert not n, f'scene {c}: {n} pixels differ, first {first}'
    assert r.dumps[3][0] & 1, 'the wreck is a billboard of this view'
    print(f'  trees and a distant billboard, {len(cases)} views (turns while tilted): OK')


def check_sun():
    """A Sun 68 degrees high (sky_y = 95 - 48 tan 68 = -24): row 72 looking up."""
    sun_y, bearing = (-24) & 255, HEAD
    steps = [L.until('game_start', 20000), L.poke('forest_enabled', 0), L.poke('ui_enabled', 0), IDLE,
             L.poke('sky_y', sun_y), L.poke('sky_bearing', bearing), L.poke('sky_bearing', bearing >> 8, 1)]
    for c in ('LOOK F', 'LOOK U', 'LOOK D'):
        steps += command(c) + ['peek:2000:8192', L.peek('sky_mood'), L.peek('sky_y')]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    R = dhgr()
    for i, tilt in enumerate((0, 1, -1)):
        page, mood, y = r.dumps[3 * i:3 * i + 3]
        assert y[0] == sun_y, 'no hour passed: the poked Sun stays'
        sky = R.Sky(mood_name=mood_name(mood), body=(bearing, sun_y))
        lit = R.lighting(sky)
        want = R.view(MAP, SX, SY, HEAD, sky, forest=False, tilt=tilt)
        n, first = view_diff(dhgr_view(page), want)
        assert not n, f'Sun, tilt {tilt}: {n} pixels differ, first {first}'
        nosun = R.view(MAP, SX, SY, HEAD, R.Sky(mood_name=mood_name(mood)), forest=False, tilt=tilt)
        drawn = {r for r in range(16, 160) for c in range(140) if want[r][c] != nosun[r][c]}
        if tilt == 1:
            assert drawn and min(drawn) >= 72 - 8 and max(drawn) <= 72 + 8, sorted(drawn)
        else:
            assert not drawn, (tilt, sorted(drawn))
    print('  Sun at 68 degrees: hidden at level and looking down, row 72 looking up: OK')


def check_commands():
    """$E7 of the original (build/probes, docs/LOOK_UPDOWN.md 'Réalisation')."""
    seq = [('LOOK U', 1), ('LOOK U', 1), ('LOOK R', 1), ('VIEW', 1), ('LOOK D', -1), ('LOOK F', 0),
           ('PAN U', 1), ('PAN U', 1), ('PAN D', 0), ('PAN D', -1), ('PAN D', -1), ('PAN F', -1),
           ('STATUS', -1), ('LOOK B', 0), ('SCAN D', -1), ('SCAN U', 0), ('LOOK UP', 1),
           ('LOOK DOWN', -1), ('LOOK AHEAD', 0), ('LOOK D', -1), ('LOOK FORWARD', 0)]
    steps = [IDLE, L.peek('s_hour', 5), L.peek('s_elap', 5)]
    for c, _ in seq:
        if c == 'STATUS':           # the screen, a key, back to the view
            steps += ['key:STATUS\r', L.until('status_key', 20000), 'key: ', 'wait:1', IDLE]
        else:
            steps += command(c)
        steps += [L.peek('tilt')]
    steps += [L.peek('s_hour', 5), L.peek('s_elap', 5)]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    # s_hour and s_elap are adjacent: one dump of 10 bytes before and after.
    got = [d[0] for d in r.dumps[1:1 + len(seq)]]
    assert got == [t & 255 for _, t in seq], list(zip([c for c, _ in seq], got))
    assert r.dumps[0] == r.dumps[-1] and len(r.dumps[0]) == 10, 'tilting costs no game time'
    print(f'  {len(seq)} LOOK / PAN / SCAN commands: tilt as the original $E7, no time: OK')
    # Refusal with a standing animal at contact; a snake lets the view down.
    def contact(kind, region=None):
        s = [IDLE, L.poke('animal_kind', kind), L.peek('px', 4)]
        return s
    steps = [IDLE, L.peek('px', 4)]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=300)
    cx, cy = r.dumps[0][1], r.dumps[0][3]
    for kind, region, refused in ((6, 2, True), (8, 2, False), (7, 2, False), (6, 5, False),
                                  (7, 3, True), (8, 1, True)):
        steps = [IDLE, L.poke('animal_kind', kind), L.poke('animal_x', cx), L.poke('animal_y', cy),
                 L.poke('region_number', region), L.poke('nature_frequency', 0)]
        steps += command('LOOK D') + [L.peek('tilt'), 'peek:0400:1024']
        steps += command('PAN D') + [L.peek('tilt'), 'peek:0400:1024']
        r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=300)
        text = result_text(text_screen(r.mem(0x400, 1024)))
        if refused:
            assert r.dumps[0][0] == 0 and r.dumps[2][0] == 0 and 'NOT NOW.' in text, (kind, region, text)
        else:
            assert r.dumps[0][0] == 255 and 'NOT NOW' not in text, (kind, region, text)
    print('  NOT NOW: a standing animal at contact refuses LOOK D / PAN D (by region and slot): OK')
    # Inside the cabin the tilt does not change; WALK and LOOK B level it.
    steps = [IDLE, L.poke('shelter_inside', 1)] + command('LOOK U') + [L.peek('tilt'), L.poke('shelter_inside', 0)]
    steps += command('LOOK D') + [L.peek('tilt'), 'key:WALK\r', L.until('number_idle', 6000), 'key:10 MIN\r',
                                  'wait:200', IDLE, L.peek('tilt'), L.peek('px', 4)]
    r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=600)
    assert r.dumps[0][0] == 0 and r.dumps[1][0] == 255 and r.dumps[2][0] == 0, [d[0] for d in r.dumps[:3]]
    print('  inside the cabin nothing tilts; WALK levels the view: OK')


def hidden_rows(page):
    from hgr_tables import hgr_offset
    main, aux = page[:8192], page[8192:]
    return b''.join(bank[hgr_offset(y):hgr_offset(y) + 40] for bank in (main, aux) for y in range(176, 192))


def check_regions():
    for region in range(1, 7):
        steps = menu_keys(str(region)) + [IDLE, 'peek:2000:8192']
        for c in ('LOOK U', 'LOOK D', 'PAN U', 'LOOK R', 'LOOK D'):
            steps += command(c) + ['peek:2000:8192']
        r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
        rows = [hidden_rows(d) for d in r.dumps]
        assert all(x == rows[0] for x in rows), f'region {region}: rows 176..191 changed'
        assert any(rows[0]), 'the grid sleeps there'
    print('  six regions: rows 176..191 of both banks unchanged by LOOK U / D: OK')


def cycles():
    out = []
    for c, tilt in [('VIEW', 0)] + COMMANDS:
        steps = [*terrain_boot(20000), L.poke('scenes_enabled', 0)]
        if c != 'VIEW':
            steps += command(c)
        steps += ['key:V', 'press:\r', L.until('view_full', 20000),
                  f'pcprof:{L["idle"]:04X}:20000']
        r = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=600)
        out.append((tilt, int(re.search(r'pcprof [0-9A-F]+ cycles=(\d+)', r.out)[1])))
    print('  full view cycles (Sierra start, no sprite): ' +
          ', '.join(f'tilt {t:+d}: {n}' for t, n in out))
    return out


def main():
    check_commands()
    check_maps()
    check_scene()
    check_sun()
    check_regions()
    cycles()
    print('LOOK UP / LOOK DOWN: OK')


if __name__ == '__main__':
    main()
