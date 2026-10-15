#!/usr/bin/env python3
"""Local sprite pans: exact DHGR pixels across clipping/wrap and measured savings."""
import re
import tempfile
from common import terrain_boot, HERE, L, DISK, a2test, disk_with, dhgr, dhgr_view, mood_name
from test_projection import mapbin
from test_sprites import SX, SY, HEAD, MAP, expected_dhgr


def scene(m, x, y, heading, mood):
    """Terrain and nearest billboard (tests/scene_ref geometry) in the mood."""
    R = dhgr()
    return R.view(m, x, y, heading, R.Sky(mood_name=mood), forest=False)


def exercise(name, x, y, bearing, kind=0, full=False):
    steps = [*terrain_boot(20000)]
    for label, value in [('px', x), ('py', y), ('heading', bearing)]:
        steps += [L.poke(label, value), L.poke(label, value >> 8, 1)]
    steps += [L.poke('animal_kind', kind), L.poke('animal_x', x >> 8),
              L.poke('animal_y', y >> 8), 'key:V\\r', 'wait:1', L.until('idle', 20000)]
    turns = [('\\>', 35)] * 17 + [('\\<', -35)] * 17
    turns += [('LOOK L\\r', -70)] * 9 + [('LOOK R\\r', 70)] * 9
    for key, delta in turns:
        if full:
            # Force nearest-visible reprojection instead of scrolling.
            steps += [L.poke('scene_drawn', 3)]
        elif kind:
            steps += [L.peek('scene_drawn')]
        if key.endswith('\\r'):
            steps += [f'key:{key[:-2]}', 'press:\\r']
        else:
            steps += [f'press:{key}']
        steps += [L.until('turn_view', 20000),
                  f'pcprof:{L["idle"]:04X}:20000', 'peek:2000:8192', 'peek:0400:1024', L.peek('px',6), L.peek('sprite_left',2)]
    steps += [L.peek('sky_mood')]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    mood = mood_name(result.dumps[-1])
    cycles = [int(c) for c in re.findall(r'pcprof [0-9A-F]+ cycles=(\d+)', result.out)]
    assert len(cycles) == len(turns)
    heading = bearing
    k = 5 if kind and not full else 4           # + scene_drawn before the turn
    base = 1 if k == 5 else 0
    for i, (_, delta) in enumerate(turns):
        heading = (heading + delta) % 560
        # An animal faces the player whatever the heading (PROJECT
        # module_animal): centred after every turn. Its background is kept
        # (OUTDOOR ab_copy): the view scrolls, the animal is drawn again;
        # the pixels of the whole redraw. The site billboards stay behind it.
        if kind or name is None:
            R = dhgr()
            want = R.view(MAP, x, y, heading, R.Sky(mood_name=mood), (kind, x, y, 0) if kind else None,
                          forest=False)
        else:
            want = expected_dhgr(x, y, heading, name, bearing, mood=mood)
        if k == 5:
            assert result.dumps[k*i] == b'\x83', (name, i, 'the background kept', result.dumps[k*i].hex())
        assert dhgr_view(result.dumps[k*i+base]) == want, (name, i, heading, result.dumps[k*i+base+2].hex(),
                                                            result.dumps[k*i+base+3].hex())
    return cycles, result.dumps[:-1]


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
    steps += [L.peek('sky_mood')]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    mood = mood_name(result.dumps[-1])
    for i, (_, delta) in enumerate(turns):
        heading = (heading + delta) % 560
        count = abs(delta)
        last = count-completed if delta < 0 else 140-count+completed-1
        assert result.dumps[2*i] == bytes([last])
        ref = expected_dhgr(SX, SY, heading, 'wreck', HEAD, mood=mood)
        pending = range(count-completed) if delta < 0 else range(140-count+completed, 140)
        for y in range(160):
            for col in pending:
                ref[y][col] = 0                 # not painted yet: black, both banks
        assert dhgr_view(result.dumps[2*i+1]) == ref, 'local pan must reveal complete columns from the retained view'
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
              'key:USE COMPASS\\r', 'wait:1', L.until('idle', 20000),   # lot 7: aid in use
              'key:LOOK N\\r', 'wait:1', L.until('idle', 20000),
              'peek:2000:8192', L.peek('heading', 2), L.peek('sky_mood')]
    with tempfile.TemporaryDirectory() as tmp:
        disk = disk_with(tmp, m)
        result = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    cycles = [int(c) for c in re.findall(r'pcprof [0-9A-F]+ cycles=(\d+)', result.out)]
    assert len(cycles) == len(turns)
    reads = int.from_bytes(result.dumps[0], 'little')
    mood = mood_name(result.dumps[-1])
    for i, (key, delta) in enumerate(turns):
        heading = (heading + delta) % 560
        page, counter = result.dumps[1 + 2*i:3 + 2*i]
        assert dhgr_view(page) == scene(m, x, y, heading, mood), (label, full, i, heading)
        current = int.from_bytes(counter, 'little')
        if not full and not multiple:
            # LOOK loads vocabulary and the retained sprite; arrows reuse it.
            assert current - reads == (2 if key.endswith('\\r') else 0), (label, i, current-reads)
        reads = current
    head = int.from_bytes(result.dumps[-2], 'little')
    assert dhgr_view(result.dumps[-3]) == scene(m, x, y, head, mood), (label, 'cached heading')
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
    report = []
    for kind, name in [(6, 'bear'), (7, 'cougar'), (8, 'rattlesnake')]:
        fast, _ = exercise(name, SX+512, SY, 10, kind)
        report.append((name, sum(fast)))
    # docs/MEMORY.md 28: with the bear, the turns scroll (scene_drawn $83)
    # instead of redrawing the view (the full path forced: scene_drawn 3).
    bare, _ = exercise(None, SX+512, SY, 10)
    slow, _ = exercise('bear', SX+512, SY, 10, 6, full=True)
    bear = report[0][1]
    assert bear < sum(slow) * .6, ('animal turns must scroll', bear, sum(slow))
    print(f'  bear: {sum(slow):,} -> {bear:,} cycles ({100*(1-bear/sum(slow)):.1f}% saved; '
          f'{sum(bare):,} without the animal, +{100*(bear/sum(bare)-1):.0f}%)')
    # The fixed cabin: the log or the rock of MAP+16 (src/project.s cabin_asset).
    exercise(('log', 'rock')[MAP[16] - 1], MAP[17] << 8, MAP[18] << 8, int.from_bytes(MAP[19:21], 'little'))
    print('  wreck and shelter pans, animals centred after every turn (redrawn whole): OK')
    distant_regression()


if __name__ == '__main__':
    main()
