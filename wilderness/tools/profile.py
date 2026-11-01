#!/usr/bin/env python3
"""profile.py: cycles per routine for one frame of build/WILDERNESS.dsk.

Boots the disk, types the command KEY (default V, the full view) and profiles
what it draws with a2shot's pcprof step, from view_full (or the command) to
the next command line; cycles are summed per label of build/wild.lbl.
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2profile  # noqa: E402
key = sys.argv[1] if len(sys.argv) > 1 else 'V'
import a2test  # noqa: E402
labs = sorted((a, n) for n, a in a2test.label_pairs(HERE / 'build/wild.lbl', any_name=True)
              if not n.startswith('__'))
L = {n: a for a, n in labs}
out = subprocess.run([str(HERE.parent / 'dev/tools/a2shot/a2shot'), '--disk', str(HERE.parent / 'wilderness/build/WILDERNESS.dsk'),
                      f'until:{L["idle"]:04X}:4000', f'key:{key}', 'press:\r', f'until:{L["view_full"]:04X}:400',
                      f'pcprof:{L["idle"]:04X}:8000'], capture_output=True, text=True, check=True).stdout
per = a2profile.by_label(a2profile.pcs(out), L, rom=0xD000, rom_name='ROM')
tot = sum(per.values())
print(f'frame: {tot} cycles')
for n, c in sorted(per.items(), key=lambda x: -x[1])[:20]:
    print(f'  {n:20} {c:9d} {100 * c / tot:5.1f}%')
