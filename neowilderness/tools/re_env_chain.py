#!/usr/bin/env python3
"""re_env_chain.py: extract and disassemble the Journey-side overlay chain.

Every block is loaded at $5800 by SMALLDOS ($03DB = load and run) from the
Journey side (SMALLDOS track t = physical 34 - t). Blocks are named tTTsSS.
Usage: re_env_chain.py OUTDIR T:S:N ...
"""
import os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smalldos  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
dk = smalldos.Disk(open('build/JOURNEY.dsk', 'rb').read())
dk.flip = True
for spec in sys.argv[2:]:
    t, s, n = (int(v, 16) for v in spec.split(':'))
    name = f'{out}/t{t:02X}s{s:02X}'
    open(name + '.bin', 'wb').write(dk.run(t, s, n))
    subprocess.run(['da65', '--start-addr', '0x5800', '--comments', '4', '-o', name + '.s', name + '.bin'],
                   check=True, capture_output=True)
    print(name)
