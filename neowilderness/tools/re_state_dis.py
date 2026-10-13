#!/usr/bin/env python3
"""re_state_dis.py: compact da65 listing "ADDR  label: instr" of a binary.

Usage: re_state_dis.py BIN START [FROM TO]
"""
import re, subprocess, sys, tempfile

b, start = sys.argv[1], int(sys.argv[2], 16)
lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x10000
with tempfile.NamedTemporaryFile(suffix='.s') as f:
    subprocess.run(['da65', '--start-addr', hex(start), '--comments', '4', '-o', f.name, b], check=True)
    for line in open(f.name):
        m = re.match(r'^(\w*:?)\s+(\S.*?)\s*; ([0-9A-F]{4}) ', line)
        if m:
            a = int(m.group(3), 16)
            if lo <= a < hi:
                print(f'{a:04X} {m.group(1):8} {m.group(2)}')
