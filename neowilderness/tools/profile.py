#!/usr/bin/env python3
"""profile.py: cycles per routine for one frame of dist/NEOWILDERNESS.po.

Boots the disk, types the command KEY (default V, the full view) and profiles
what it draws with a2shot's pcprof step, from view_full (or the command) to
the next command line; cycles are summed per label of build/wild.lbl.
"""
import bisect, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
key = sys.argv[1] if len(sys.argv) > 1 else 'V'
labs = sorted((int(a, 16), n) for a, n in
              re.findall(r'^al ([0-9A-F]+) \.(\S+)$', (HERE / 'build/wild.lbl').read_text(), re.M)
              if not n.startswith('__'))
L = {n: a for a, n in labs}
out = subprocess.run([str(HERE.parent / 'dev/tools/a2shot/a2shot'), '--iie', '--disk', str(HERE.parent / 'dist/NEOWILDERNESS.po'),
                      f'until:{L["menu_key"]:04X}:40000', 'key:2\\r',   # start menu: Sierra, level 4
                      f'until:{L["idle"]:04X}:4000', f'key:{key}', 'press:\r', f'until:{L["view_full"]:04X}:400',
                      f'pcprof:{L["idle"]:04X}:8000'], capture_output=True, text=True).stdout
prof = {int(a, 16): int(c) for a, c in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', out, re.M)}
addrs = [a for a, _ in labs]
agg = {}
for a, c in prof.items():
    i = bisect.bisect_right(addrs, a) - 1
    name = labs[i][1] if i >= 0 else f'{a:04X}'
    if a >= 0xD000:
        name = 'ROM'
    agg[name] = agg.get(name, 0) + c
tot = sum(prof.values())
print(f'frame: {tot} cycles')
for n, c in sorted(agg.items(), key=lambda x: -x[1])[:20]:
    print(f'  {n:20} {c:9d} {100 * c / tot:5.1f}%')
