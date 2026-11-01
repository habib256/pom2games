#!/usr/bin/env python3
"""re_surv_text.py: print text page 1 ($0400) of RAM dumps."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test  # noqa: E402
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev/tools'))
import a2test  # noqa: E402
for f in sys.argv[1:]:
    m = open(f, 'rb').read()
    print('==', f)
    for r, row in enumerate(a2test.text_rows(m, base=0)):
        line = ''.join(chr(c & 0x7F) if 32 <= (c & 0x7F) < 127 else ' ' for c in row).rstrip()
        if line.strip():
            print(f'{r:2d} {line}')
