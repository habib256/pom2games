#!/usr/bin/env python3
"""Local sprite pans: exact pixels across clipping/wrap and measured savings."""
import re
import tempfile
from common import terrain_boot, HERE, L, DISK, a2test, disk_with, view_rows
import scene_ref
from test_projection import mapbin
from test_sprites import SX, SY, HEAD, MAP, expected


def exercise(name, x, y, bearing, kind=0, full=False):
    steps = [*terrain_boot(20000)]
    for label, value in [('px', x), ('py', y), ('heading', bearing),
                         ('animal_bearing', bearing)]:
        steps += [L.poke(label, value), L.poke(label, value >> 8, 1)]
    steps += [L.poke('animal_kind', kind), L.poke('animal_x', x >> 8),
              L.poke('animal_y', y >> 8), 'key:V\\r', 'wait:1', L.until('idle', 20000)]
    turns = [('\\>', 35)] * 17 + [('\\<', -35)] * 17
    turns += [('LOOK L\\r', -70)] * 9 + [('LOOK R\\r', 70)] * 9
    for key, delta in turns:
        if full:
            # Force nearest-visible reprojection instead of scrolling.
            steps += [L.poke('scene_drawn', 3)]
        if key.endswith('\\r'):
            steps += [f'key:{key[:-2]}', 'press:\\r']
        else:
            steps += [f'press:{key}']
        steps += [L.until('turn_view', 20000),
                  f'pcprof:{L["idle"]:04X}:20000', 'peek:2000:8192', 'peek:0400:1024', L.peek('px',6), L.peek('sprite_left',2)]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    cycles = [int(c) for c in re.findall(r'pcprof [0-9A-F]+ cycles=(\d+)', result.out)]
    assert len(cycles) == len(turns)
    heading = bearing
    for i, (_, delta) in enumerate(turns):
        heading = (heading + delta) % 560
        assert view_rows(result.dumps[4*i]) == expected(x, y, heading, name, bearing), (name, i, heading, result.dumps[4*i+2].hex(), result.dumps[4*i+3].hex())
    return cycles, result.dumps


def reveal_order():
    completed = 20
    steps = [*terrain_boot(20000)]
    turns = [('\\<', -35), ('\\>', 35), ('LOOK L\\r', -70), ('LOOK R\\r', 70)]
    heading = HEAD
    for key, delta in turns:
        if key.endswith('\\r'):
            steps += [f'key:{key[:-2]}', 'press:\\r']
        else:
            steps += [f'press:{key}']
        steps += [f'tracepc:{L["render_column_done"]:04X}:{completed}:20000',
                  L.peek('col'), 'peek:2000:8192', L.until('idle', 20000)]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    for i, (_, delta) in enumerate(turns):
        heading = (heading + delta) % 560
        count = abs(delta)
        last = count-completed if delta < 0 else 140-count+completed-1
        assert result.dumps[2*i] == bytes([last])
        ref = bytearray(expected(SX, SY, heading, 'wreck', HEAD))
        pending = range(count-completed) if delta < 0 else range(140-count+completed, 140)
        for y in range(160):
            for col in pending:
                for pixel in (2*col, 2*col+1):
                    ref[y*40+pixel//7] &= ~(1 << (pixel % 7))
        assert view_rows(result.dumps[2*i+1]) == ref, 'local pan must reveal complete columns from the retained view'
    print('  local sprite pans: progressive reveal from retained view in both directions: OK')


def distant_pans(m, label, x, y, full=False, multiple=False):
    """Whole turns past offscreen sites, with pixel and I/O regression guards."""
    heading = 0
    turns = [('\\>', 35)] * 16 + [('\\<', -35)] * 16
    turns += [('LOOK R\\r', 70)] * 8 + [('LOOK L\\r', -70)] * 8
    steps = [*terrain_boot(20000)]
    for name, value in [('px', x), ('py', y), ('heading', heading)]:
        steps += [L.poke(name, value), L.poke(name, value >> 8, 1)]
    steps += ['key:V\\r', 'wait:1', L.until('idle', 20000), L.peek('overlay_reads', 2)]
    for key, _ in turns:
        if full:
            steps += [L.poke('scene_drawn', 3)]
        if key.endswith('\\r'):
            steps += [f'key:{key[:-2]}', 'press:\\r']
        else:
            steps += [f'press:{key}']
        steps += [L.until('turn_view', 20000),
                  f'pcprof:{L["idle"]:04X}:20000', 'peek:2000:8192',
                  L.peek('overlay_reads', 2)]
    # A direct bearing matching the old cached heading must not reuse stale
    # sprite geometry after a pan (LOOK F uses the same prepare path).
    steps += ['press:\\>', L.until('idle', 20000),
              'key:LOOK N\\r', 'wait:1', L.until('idle', 20000),
              'peek:2000:8192', L.peek('heading', 2)]
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, m)
        result = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    cycles = [int(c) for c in re.findall(r'pcprof [0-9A-F]+ cycles=(\d+)', result.out)]
    assert len(cycles) == len(turns)
    reads = int.from_bytes(result.dumps[0], 'little')
    for i, (key, delta) in enumerate(turns):
        heading = (heading + delta) % 560
        page, counter = result.dumps[1 + 2*i:3 + 2*i]
        assert view_rows(page) == scene_ref.render(m, x, y, heading), (label, full, i, heading)
        current = int.from_bytes(counter, 'little')
        if not full and not multiple:
            # LOOK loads vocabulary, TREE and the retained sprite; arrows reuse it.
            assert current - reads == (3 if key.endswith('\\r') else 0), (label, i, current-reads)
        reads = current
    head = int.from_bytes(result.dumps[-1], 'little')
    assert view_rows(result.dumps[-2]) == scene_ref.render(m, x, y, head), (label, 'cached heading')
    return sum(cycles)


def distant_regression():
    m = mapbin()
    x, y = 18*256+128, 20*256+128
    fast = distant_pans(m, 'cabin', x, y)
    slow = distant_pans(m, 'cabin', x, y, full=True)
    assert fast < slow * .6, 'distant pans should save at least 40% including projection I/O'
    print(f'  distant cabin: {slow:,} -> {fast:,} cycles ({100*(1-fast/slow):.1f}% saved); arrow turns: no disk reads')
    (HERE/'build/pan-profile.txt').write_text(
        f'Distant cabin, 48 turns: full {slow} cycles; pan {fast} cycles; '
        f'{100*(1-fast/slow):.1f}% saved\n')
    distant_pans(m, 'distant wreck', 10*256, 8*256)
    ridge = bytearray(m)
    for row in range(18, 23):
        ridge[64+row*112+19] = 11
    ridge[21] = 12
    distant_pans(bytes(ridge), 'foreground ridge', x, y)
    both = bytearray(m)
    both[2:8] = bytes((128, 22, 128, 22, 164, 1))
    distant_pans(bytes(both), 'competing sites', x, y, multiple=True)
    print('  distant pans: both directions, clipping, wraps, occlusion, competing sites and cached-heading return: OK')


def main():
    reveal_order()
    fast, pages = exercise('wreck', SX, SY, HEAD)
    slow, old_pages = exercise('wreck', SX, SY, HEAD, full=True)
    assert pages[1::4] == old_pages[1::4], 'pan must preserve command-line text'
    assert pages[2::4] == old_pages[2::4], 'pan must preserve position and heading'
    assert sum(fast) < sum(slow) * .6, 'local pans should save at least 40% of total cycles'
    print(f'  wreck: {sum(slow):,} -> {sum(fast):,} cycles ({100*(1-sum(fast)/sum(slow)):.1f}% saved)')
    for kind, name in [(6, 'bear'), (7, 'cougar'), (8, 'rattlesnake')]:
        exercise(name, SX+512, SY, 10, kind)
    exercise('cabin', MAP[17] << 8, MAP[18] << 8, int.from_bytes(MAP[19:21], 'little'))
    print('  five sprites: both directions, 22.5/45 degrees, offscreen return and full heading wraps: OK')
    distant_regression()


if __name__ == '__main__':
    main()
