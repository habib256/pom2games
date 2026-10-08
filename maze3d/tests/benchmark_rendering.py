#!/usr/bin/env python3
"""Optional cycle benchmark. Fixtures alter RAM only, never the disk image.

Pass a directory containing MAZE3D.dsk and maze3d.lbl to measure an older
build with the same fixtures; otherwise use the current build.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test

base = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'maze3d/build'
disk = base / 'MAZE3D.dsk' if len(sys.argv) > 1 else ROOT / 'dist/MAZE3D.dsk'
labels = a2test.labels(base / 'maze3d.lbl')
measurements = {}
for scene in ('game', 'corridor', 'cluster'):
    steps = ['wait:2200', 'key:X', 'wait:130', 'press:L', labels.until('render_3d')]
    if scene != 'game':
        steps += [f'poke:{0x1000+i:04x}:{2 if i % 11 < 10 else 0:02x}' for i in range(77)]
        steps += [labels.poke('p_col', 0), labels.poke('p_row', 3), labels.poke('p_face', 1)]
        steps += [f'poke:{0x10b0+i:04x}:ff' for i in range(8)]
    if scene == 'cluster':
        for i, (col, kind) in enumerate(((1, 0), (1, 1), (1, 2), (3, 0), (5, 3))):
            steps += [f'poke:{0x10a0+i:04x}:{col:02x}', f'poke:{0x10a8+i:04x}:03',
                      f'poke:{0x10b0+i:04x}:{kind:02x}']
    result = a2test.run(disk, steps + [labels.until('play_input')], emulator=a2test.A2SHOT)
    measurements[scene] = result.cycles[-1] - result.cycles[-2]
boot = a2test.run(disk, [labels.until('wait_key_real')], emulator=a2test.A2SHOT)
measurements['boot_to_title'] = boot.cycles[-1]
print(json.dumps(measurements, indent=2))
