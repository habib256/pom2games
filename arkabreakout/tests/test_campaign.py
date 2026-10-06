#!/usr/bin/env python3
"""Play all twelve boards with a deterministic paddle pilot, without altering progress."""
from pathlib import Path
import argparse
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'dev/tools'))
import a2test
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('pilot',type=Path)
parser.add_argument('--disk',type=Path,default=root/'dist/ARKABREAKOUT.dsk')
parser.add_argument('--labels',type=Path,default=root/'arkabreakout/build/game.lbl')
args = parser.parse_args()
labels = a2test.labels(args.labels)
pilot = args.pilot.resolve()
subprocess.run([str(pilot),str(args.disk.resolve()),
                str(root/'dev/tools/a2shot/roms')] +
               [f'{labels[name]:06X}' for name in ('loop','state','ball_x','ball_y','pad_x',
                                         'pad_width','ball_live','level','ball_diry')],
               check=True,timeout=180)
print('ARKABREAKOUT campaign: all 12 sectors cleared by paddle steering alone.')
