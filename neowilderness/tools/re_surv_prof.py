#!/usr/bin/env python3
"""re_surv_prof.py: profile one command of the original (after its last key).

Usage: re_surv_prof.py "CMD|ANSWER..." [SETUP CMDS...]  -> code ranges executed,
grouped by engine block, cycles per routine-sized chunk (label of build/re/*.s).
"""
import re, subprocess, sys
cmd, setup = sys.argv[1], sys.argv[2:]
steps = ['wait:5000', 'key:1\\r', 'wait:3000', 'insert:build/JOURNEY.dsk', 'key:\\r', 'wait:3000',
         'key:\\r', 'wait:600', 'key:\\r', 'wait:60', 'until:B0E2:8000']
for c in setup:
    first, *ans = c.split('|')
    steps += [f'key:{first}\\r'] + [s for a in ans for s in ('wait:400', f'key:{a}\\r')] + ['wait:60', 'until:B0E2:8000']
first, *ans = cmd.split('|')
keys = [f'key:{first}\\r'] + [s for a in ans for s in ('wait:400', f'key:{a}\\r')]
steps += keys + ['pcprof:B0E2:6000']
out = subprocess.run(['../dev/tools/a2shot/a2shot', '--disk', 'build/SIERRA.woz'] + steps,
                     capture_output=True, text=True).stdout
prof = {int(a, 16): int(c) for a, c in re.findall(r'^pc ([0-9A-F]{4}) (\d+)$', out, re.M)}
print([l for l in out.splitlines() if l.startswith('pcprof')])
# group contiguous executed addresses into ranges (gap > 16)
addrs = sorted(prof)
ranges, start, last = [], None, None
for a in addrs:
    if start is None:
        start = last = a
    elif a - last > 16:
        ranges.append((start, last)); start = a
    last = a
if start is not None:
    ranges.append((start, last))
for s, e in ranges:
    if s >= 0xD000:
        continue
    cyc = sum(prof[a] for a in addrs if s <= a <= e)
    print(f'{s:04X}-{e:04X} {cyc:9d}')
