#!/usr/bin/env python3
"""Check column composition during rendering, exact pixels, and ray pruning."""
import random, re, tempfile
from common import terrain_boot, HERE, L, DISK, a2test, disk_with, dhgr_view, mood_name
from test_sprites import expected_dhgr, MAP, SX, SY, HEAD


def profile(disk, enabled, mapbin):
    steps = [*terrain_boot(20000), L.poke('scenes_enabled', enabled),
             'key:V', 'press:\r', L.until('view_full', 20000),
             f'pcprof:{L["idle"]:04X}:20000', 'peek:2000:8192', L.peek('sky_mood')]
    result = a2test.run(disk, steps, emulator=a2test.A2SHOT, timeout=900)
    pcs = {int(a, 16): int(c) for a, c in
           re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', result.out, re.M)}
    cycles = int(re.search(r'pcprof [0-9A-F]+ cycles=(\d+)', result.out)[1])
    ref = expected_dhgr(SX, SY, HEAD, 'wreck' if enabled else None, HEAD, mapbin, mood_name(result.dumps[1]))
    assert dhgr_view(result.dumps[0]) == ref, 'clipped ray must preserve the final image'
    # INC n is a five-cycle zero-page instruction, once per attempted step.
    return pcs[L['ray_step']] // 5, cycles


def partial_frame():
    completed = 20
    steps = [*terrain_boot(20000), 'key:V', 'press:\r', L.until('view_full', 20000),
             f'tracepc:{L["render_column_done"]:04X}:{completed}:20000',
             L.peek('col'), 'peek:2000:8192', L.until('idle', 20000), 'peek:2000:8192',
             L.peek('sky_mood')]
    result = a2test.run(DISK, steps, emulator=a2test.A2SHOT, timeout=900)
    assert result.dumps[0] == bytes([completed - 1])
    mood = mood_name(result.dumps[3])
    ref = expected_dhgr(SX, SY, HEAD, 'wreck', HEAD, mood=mood)
    prefix = [row[:completed] + [0] * (140 - completed) for row in ref]
    assert dhgr_view(result.dumps[1]) == prefix, 'each completed column must already include its sprite'
    terrain = expected_dhgr(SX, SY, HEAD, mood=mood)
    assert any(ref[y][x] != terrain[y][x] for y in range(160) for x in range(completed)), \
        'checkpoint must include opaque sprite pixels'
    assert dhgr_view(result.dumps[2]) == ref
    print('  intermediate frame: completed columns contain terrain and sprite, later columns are clear: OK')


def main():
    partial_frame()
    flat = bytearray(MAP)
    flat[64:] = bytes([10]) * 9408
    flat[21] = 11
    cliffs = bytearray(MAP)
    cliffs[64:] = bytes(125 if (x // 7 + y // 5) % 3 == 0 else 0
                        for y in range(84) for x in range(112))
    cliffs[21] = 126
    rng = random.Random(917)
    noise = bytearray(MAP)
    noise[64:] = bytes(rng.randrange(126) | (0x80 if rng.random() < .05 else 0)
                       for _ in range(9408))
    noise[21] = 126
    legacy = bytearray(flat)
    legacy[21] = 0
    rows = []
    for name, mapbin in [('generated', MAP), ('flat', flat), ('cliffs', cliffs),
                         ('noise', noise), ('legacy flat', legacy)]:
        with tempfile.TemporaryDirectory() as tmp:
            disk = disk_with(tmp, bytes(mapbin))
            plain_steps, plain_cycles = profile(disk, 0, mapbin)
            sprite_steps, sprite_cycles = profile(disk, 1, mapbin)
        assert sprite_steps <= plain_steps, name
        if name == 'flat':
            assert sprite_steps < plain_steps * .7, 'covered terrain should save at least 30% of steps'
        print(f'  {name}: {plain_steps} -> {sprite_steps} ray steps, '
              f'{plain_cycles} -> {sprite_cycles} rendering cycles; exact pixels: OK')
        rows.append(f'{name}: {plain_steps} -> {sprite_steps} steps; '
                    f'{plain_cycles} -> {sprite_cycles} cycles')
    (HERE / 'build/scene-render-profile.txt').write_text('\n'.join(rows) + '\n')
    print('Column composition and conservative ray pruning: OK')


if __name__ == '__main__':
    main()
