#!/usr/bin/env python3
"""profile.py: cycles per routine for one frame of dist/NEOWILDERNESSXL.po.

Boots the disk, types the command KEY (default V, the full view) and profiles
what it draws with a2shot's pcprof step, from view_full (or the command) to
the next command line; cycles are summed per label of build/wild.lbl.
"""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / 'dev/tools'))
import a2profile  # noqa: E402
import a2test  # noqa: E402
key = sys.argv[1] if len(sys.argv) > 1 else 'V'
# a2test.labels, as the tests: the last of two homonyms (menu_key: the
# loader's start menu, not menu.s's) wins
L = a2test.labels(HERE / 'build/wild.lbl')
out = subprocess.run([str(HERE.parent / 'dev/tools/a2shot/a2shot'), '--iie', '--disk', str(HERE.parent / 'dist/NEOWILDERNESSXL.po'),
                      f'until:{L["menu_key"]:04X}:40000', 'key:1\\r',   # start menu: Sierra (key 1), level 4
                      f'until:{L["idle"]:04X}:4000', f'key:{key}', 'press:\\r', f'until:{L["view_full"]:04X}:400',
                      f'pcprof:{L["idle"]:04X}:8000'], capture_output=True, text=True, check=True).stdout
per = a2profile.by_label(a2profile.pcs(out), L, rom=0xD000, rom_name='ROM')
tot = sum(per.values())
print(f'frame: {tot} cycles')
for n, c in sorted(per.items(), key=lambda x: -x[1])[:20]:
    print(f'  {n:20} {c:9d} {100 * c / tot:5.1f}%')
