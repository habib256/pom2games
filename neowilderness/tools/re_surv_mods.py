#!/usr/bin/env python3
"""re_surv_mods.py: extract and disassemble the chained modules listed in
build/re_surv/mods.txt (track sector count page kind) from the Journey side."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smalldos  # noqa: E402
dk = smalldos.Disk(open('build/JOURNEY.dsk', 'rb').read())
dk.flip = True
seen = set()
for line in open('build/re_surv/mods.txt'):
    t, s, n, page, kind = line.split()
    t, s, n, page = int(t, 16), int(s, 16), int(n), int(page, 16)
    if page != 0x58 or (t, s) in seen:
        continue
    seen.add((t, s))
    name = f'build/re_surv/m{t:02X}{s:X}'
    open(name + '.bin', 'wb').write(dk.run(t, s, n))
    subprocess.run(['da65', '--start-addr', '0x5800', '--comments', '4', '-o', name + '.s', name + '.bin'],
                   check=True, capture_output=True)
    print(name, n)
