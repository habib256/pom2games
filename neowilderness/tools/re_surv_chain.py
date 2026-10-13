#!/usr/bin/env python3
"""re_surv_chain.py: trace the module chain ($03DB load-and-run, $03DE load)
of each command; print the chains and save the union to build/re_surv/mods.txt.

Usage: re_surv_chain.py "CMD|ANS" ...  (commands run in sequence)
"""
import re, subprocess, sys
steps = ['wait:5000', 'key:1\\r', 'wait:3000', 'insert:build/JOURNEY.dsk', 'key:\\r', 'wait:3000',
         'key:\\r', 'wait:600', 'key:\\r', 'wait:60', 'until:B0E2:8000',
         'watch:03DB:BAFD:1', 'watch:03DE:BAFD:1', 'watch:B0E2']
for c in sys.argv[1:]:
    first, *ans = c.split('|')
    steps += ['watch:B0C9', f'key:{first}\\r'] + [s for a in ans for s in ('wait:400', f'key:{a}\\r')]
    steps += ['wait:60', 'until:B0E2:8000', 'unwatch', 'watch:03DB:BAFD:1', 'watch:03DE:BAFD:1']
out = subprocess.run(['../dev/tools/a2shot/a2shot', '--disk', 'build/SIERRA.woz'] + steps,
                     capture_output=True, text=True).stdout
mods = set()
chain = []
for line in out.splitlines():
    m = re.match(r'watch (03DB|03DE) A=(..) X=(..) Y=(..) .* mem=(..)', line)
    if m:
        kind, a, x, y, page = m.groups()
        chain.append(f'{"run" if kind == "03DB" else "ld"}:T{x}S{y}x{int(a, 16)}@{page}')
        mods.add((int(x, 16), int(y, 16), int(a, 16), int(page, 16), kind))
    elif line.startswith('until'):
        print(' -> '.join(chain)); chain = []
with open('build/re_surv/mods.txt', 'a') as f:
    for m in sorted(mods):
        f.write('%02X %02X %d %02X %s\n' % m)
