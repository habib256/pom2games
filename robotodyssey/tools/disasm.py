#!/usr/bin/env python3
"""disasm.py: annotated disassembly of a Robot Odyssey 64 KB memory image.

    python3 -I tools/disasm.py IMAGE LO HI [--entry ADDR ...] [--region LO-HI ...]

Traces code from the entries (default: $0803 and the known engine entry
points) with ../dev/tools/re6502, then prints LO..HI: code lines with the
names of the world / circuit tables (tools/symbols.py) as comments, data
runs as .byte lines of 16.  Branch and call targets are flagged with '*'.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'dev' / 'tools'))
sys.path.insert(0, str(HERE))
from re6502.opcodes import decode, operand_text  # noqa: E402
from re6502.trace import trace  # noqa: E402
from symbols import name_of  # noqa: E402

REGIONS = [(0x0800, 0x2000), (0x8200, 0x8EF0), (0x9500, 0xC000), (0xD000, 0x10000)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('lo')
    ap.add_argument('hi')
    ap.add_argument('--entry', action='append', default=[])
    ap.add_argument('--region', action='append', default=[])
    o = ap.parse_args(argv)
    img = Path(o.image).read_bytes()
    regions = [tuple(int(x, 16) for x in r.split('-')) for r in o.region] or REGIONS
    entries = [int(e, 16) for e in o.entry] + [0x0803]
    code, targets, _ = trace(img, entries, regions)
    a, hi = int(o.lo, 16), int(o.hi, 16)
    while a < hi:
        if a in code:
            mn, mo, _, v = decode(img, a)
            txt = '%-4s%s' % (mn, operand_text(img, a))
            note = name_of(v) if code[a] == 3 or mo in ('zp', 'zpx', 'zpy', 'izx', 'izy') else ''
            raw = ' '.join('%02X' % img[a + k] for k in range(code[a]))
            print('%s%04X: %-9s %-16s%s' % ('*' if a in targets else ' ', a, raw, txt,
                                           ('; ' + note) if note else ''))
            a += code[a]
        else:
            e = a
            while e < hi and e not in code and e - a < 16:
                e += 1
            chunk = img[a:e]
            asc = ''.join(chr(c & 0x7F) if 32 <= (c & 0x7F) < 127 else '.' for c in chunk)
            print(' %04X: .byte %-48s %s' % (a, ' '.join('%02X' % c for c in chunk), asc))
            a = e


if __name__ == '__main__':
    main()
