#!/usr/bin/env python3
"""Boot the shipping disk on both VBL implementations, NTSC and PAL."""
from pathlib import Path
import sys
import subprocess

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2test


def test_embedded_contacts():
    # Overlapping balls moving together toward a wall. Pair separation
    # pushes ball 0's center into the wall before the wall solver runs.
    cases = [
        ('left', (10, 16), (100, 100), -4, 0, (10, 100)),
        ('right', (245, 239), (100, 100), 4, 0, (245, 100)),
        ('ceiling', (100, 100), (9, 15), 0, -4, (100, 9)),
        ('floor', (100, 100), (182, 176), 0, 4, (100, 182)),
    ]
    # Box 4 spans x=40..64, y=56..80. Each pair drives the first
    # ball through one face. A soft box permits four pixels of dent.
    box_cases = [
        ('box left', (34, 28), (68, 68), 4, 0, (34, 68), (38, 68)),
        ('box right', (70, 76), (68, 68), -4, 0, (70, 68), (66, 68)),
        ('box top', (52, 52), (50, 44), 0, 4, (52, 50), (52, 54)),
        ('box bottom', (52, 52), (86, 92), 0, -4, (52, 86), (52, 82)),
    ]
    cases = [(name, xs, ys, vx, vy, 3, expected)
             for name, xs, ys, vx, vy, expected in cases]
    cases += [(name, xs, ys, vx, vy, soft, soft_pos if soft else rigid_pos)
              for name, xs, ys, vx, vy, rigid_pos, soft_pos in box_cases
              for soft in (0, 3)]
    steps = ['wait:1800', 'key:P', 'wait:8', 'poke:00A6:02']
    for _, xs, ys, vx, vy, soft, _ in cases:
        state = bytearray(0x33)  # object fields from ob_xlo through ob_agehi
        for i in range(2):
            state[3 + i] = xs[i]
            state[9 + i] = ys[i]
            state[15 + i] = vx & 255
            state[21 + i] = vy & 255
        steps += [f'poke:005D:{soft:02X}', f'ramset:main:0200:{state.hex()}', 'ramset:main:0260:0000',
                  'poke:00A7:00', 'call:0824:2', 'peek:0200:12']  # physics_step
    result = subprocess.run([str(a2test.A2SHOT), '--iie', '--disk',
                             str(HERE / 'build/physics.dsk'), *steps],
                            capture_output=True, text=True, check=True, timeout=30)
    dumps = a2test.Result(result.stdout).dumps
    assert len(dumps) == len(cases)
    for (wall, _, _, _, _, soft, expected), data in zip(cases, dumps):
        actual = data[3], data[9]
        assert actual == expected, (wall, soft, actual, expected)
    print('Ball pair pressed against walls and all four faces of rigid and soft boxes: OK')


def test_sleep_transitions():
    # Let a ball settle at the right edge of rigid box 4.
    state = bytearray(0x33)
    state[3], state[9] = 64, 50
    tick = 'call:0824:2'
    steps = ['wait:1800', 'key:P', 'wait:8']
    for wake in (['rawkey:0A', 'wait:6'],  # soften the support
                 ['poke:00A6:02', 'poke:0204:3A', 'poke:020A:32']):  # push off edge
        steps += ['poke:00A6:01', 'poke:00A7:00', 'poke:005D:00',
                  f'ramset:main:0200:{state.hex()}', 'ramset:main:0260:0000']
        steps += [tick] * 35 + ['peek:0260:1'] + wake
        steps += [tick, 'peek:0260:1', 'peek:022A:1', 'peek:0206:1',
                  tick, 'peek:0206:1']
    result = subprocess.run([str(a2test.A2SHOT), '--iie', '--disk',
                             str(HERE / 'build/physics.dsk'), *steps],
                            capture_output=True, text=True, check=True, timeout=30)
    dumps = a2test.Result(result.stdout).dumps
    assert len(dumps) == 10
    for i, cause in ((0, 'softness'), (5, 'ball contact')):
        asleep, after_wake, still, y1, y2 = dumps[i:i+5]
        assert asleep == b'\x01' and after_wake == b'\x00', cause
        assert still == b'\x01' and y1 != y2, (cause, still, y1, y2)
    print('Sleeping ball resumes motion after softness change or pair separation: OK')


def main():
    if not a2test.A2SHOT.is_file():
        raise SystemExit('physics: build emulator first: make -C ../dev/tools/a2shot')
    test_embedded_contacts()
    test_sleep_transitions()
    for model in ('--iie', '--iic', '--iic16'):
        for pal in (False, True):
            # Three balls stress collision/dent rendering while checking the
            # real field clock. P must stop simulation without stopping video.
            steps = ['wait:1800', 'peek:0067:2', 'peek:0200:112',
                     'wait:600', 'peek:0067:2', 'peek:0200:112',
                     'key:P', 'wait:5', 'peek:0066:1', 'peek:0200:112',
                     'wait:120', 'peek:0200:112',
                     'rawkey:70', 'wait:120', 'peek:0066:1', 'peek:0200:112',
                     'poke:00A6:02', 'poke:00A7:00', 'rawkey:00', 'wait:8',
                     'peek:00A6:1', 'key: ', 'wait:1',
                     'peek:00A6:1', 'wait:120', 'peek:00AE:1',
                     'reset', 'wait:120', 'peek:C041:1', 'peek:C07E:1', 'pc']
            result = subprocess.run([str(a2test.A2SHOT), model] +
                                    (['--pal'] if pal else []) +
                                    ['--disk', str(HERE / 'build/physics.dsk')] + steps,
                                    capture_output=True, text=True, check=True, timeout=30)
            r = a2test.Result(result.stdout)
            d = r.dumps
            frames = (int.from_bytes(d[2], 'little') - int.from_bytes(d[0], 'little')) & 65535
            # 600 video fields, 2 fields per displayed frame, plus occasional
            # 3-field rendering under load. Frozen/overcounted clocks fail.
            assert 240 <= frames <= 301, (model, pal, frames)
            assert d[1] != d[3], (model, pal, 'simulation frozen')
            assert d[4] == b'\1' and d[5] == d[6], (model, pal, 'pause')
            assert d[7] == b'\0' and d[6] != d[8], (model, pal, 'resume')
            assert d[9] == b'\2', (model, pal, 'NUL spawned a ball')
            assert d[10] == b'\3', (model, pal, 'SPACE spawn')
            assert 2 <= d[11][0] <= 4, (model, pal, 'catch-up steps')
            if model != '--iie':
                assert not d[12][0] & 0x80 and d[13][0] & 0x80, (model, pal, 'reset IOU/VBL')
            print(f'{model[2:]} {"PAL" if pal else "NTSC"}: {frames} frames/600 fields, movement, pause/resume, spawn, reset: OK')


if __name__ == '__main__':
    main()
