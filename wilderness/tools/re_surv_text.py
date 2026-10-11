#!/usr/bin/env python3
"""re_surv_text.py: print text page 1 ($0400) of RAM dumps."""
import sys
for f in sys.argv[1:]:
    m = open(f, 'rb').read()
    print('==', f)
    for r in range(24):
        a = 0x400 + (r % 8) * 128 + (r // 8) * 40
        line = ''.join(chr(c & 0x7F) if 32 <= (c & 0x7F) < 127 else ' ' for c in m[a:a + 40]).rstrip()
        if line.strip():
            print(f'{r:2d} {line}')
