#!/usr/bin/env python3
"""Boot the shipping disk on both VBL implementations, NTSC and PAL."""
from pathlib import Path
import sys
import subprocess

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2test


def main():
    if not a2test.A2SHOT.is_file():
        raise SystemExit('physics: build emulator first: make -C ../dev/tools/a2shot')
    for model in ('--iie', '--iic', '--iic16'):
        for pal in (False, True):
            # Three balls stress collision/dent rendering while checking the
            # real field clock. P must stop simulation without stopping video.
            steps = ['wait:1800', 'peek:0067:2', 'peek:0200:112',
                     'wait:600', 'peek:0067:2', 'peek:0200:112',
                     'key:P', 'wait:5', 'peek:0066:1', 'peek:0200:112',
                     'wait:120', 'peek:0200:112',
                     'key:P', 'wait:120', 'peek:0066:1', 'peek:0200:112',
                     'poke:00A6:02', 'peek:00A6:1', 'key: ', 'wait:1',
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
            assert d[9] == b'\2' and d[10] == b'\3', (model, pal, 'SPACE spawn')
            assert 2 <= d[11][0] <= 4, (model, pal, 'catch-up steps')
            if model != '--iie':
                assert not d[12][0] & 0x80 and d[13][0] & 0x80, (model, pal, 'reset IOU/VBL')
            print(f'{model[2:]} {"PAL" if pal else "NTSC"}: {frames} frames/600 fields, movement, pause/resume, spawn, reset: OK')


if __name__ == '__main__':
    main()
