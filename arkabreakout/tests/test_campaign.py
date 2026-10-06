#!/usr/bin/env python3
"""Play all twelve boards with a deterministic paddle pilot, without altering progress."""
from pathlib import Path
import argparse
import re
import subprocess

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('pilot',type=Path)
parser.add_argument('--disk',type=Path,default=root/'dist/ARKABREAKOUT.dsk')
parser.add_argument('--labels',type=Path,default=root/'arkabreakout/build/game.lbl')
args = parser.parse_args()
labels = {name: addr for addr,name in re.findall(
    r'^al ([0-9A-Fa-f]+) \.(\w+)$',
    args.labels.read_text(),re.M)}
pilot = args.pilot.resolve()
subprocess.run([str(pilot),str(args.disk.resolve()),
                str(root/'dev/tools/a2shot/roms')] +
               [labels[name] for name in ('loop','state','ball_x','ball_y','pad_x',
                                         'pad_width','ball_live','level','ball_diry')],
               check=True,timeout=180)
print('ARKABREAKOUT campaign: all 12 sectors cleared by paddle steering alone.')
