#!/usr/bin/env python3
"""Explore a 64 KB memory image of a 6502 program.

    cli.py trace   IMAGE [--entry 800 ...] --region 800-1D00 ...
        code runs found from the entries, then the problems
    cli.py listing IMAGE LO HI [--entry ...] --region ...
        linear listing, '*' on branch / call targets, data as .byte
    cli.py refs    IMAGE abs|zp [--entry ...] --region ...
        who reads / writes each absolute address, each zero-page byte

Addresses are hex. --entry defaults to the first region's start.
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from re6502.opcodes import decode, operand_text  # noqa: E402
from re6502.trace import trace, runs  # noqa: E402


def hexint(s):
    return int(s, 16)


def region(s):
    lo, hi = s.split('-')
    return int(lo, 16), int(hi, 16)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=('trace', 'listing', 'refs'))
    ap.add_argument('image', type=Path)
    ap.add_argument('args', nargs='*')
    ap.add_argument('--entry', type=hexint, action='append')
    ap.add_argument('--region', type=region, action='append', required=True)
    o = ap.parse_args(argv)
    img = o.image.read_bytes()
    entries = o.entry or [o.region[0][0]]
    code, targets, probs = trace(img, entries, o.region)
    if o.command == 'trace':
        for s, e in runs(code):
            print('%04X-%04X' % (s, e - 1))
        for p in probs:
            print(p if len(p) < 2 else (p[0],) + tuple(hex(x) if isinstance(x, int) else x for x in p[1:]))
    elif o.command == 'listing':
        a, hi = hexint(o.args[0]), hexint(o.args[1])
        while a < hi:
            if a in code:
                print('%s%04X: %-4s%s' % ('*' if a in targets else ' ', a, decode(img, a)[0], operand_text(img, a)))
                a += code[a]
            else:
                print(' %04X: .byte $%02X' % (a, img[a]))
                a += 1
    else:
        refs, zp = defaultdict(set), defaultdict(set)
        for a, length in code.items():
            mn, mo, _, v = decode(img, a)
            if length == 3 and mn not in ('jsr', 'jmp'):
                refs[v].add((a, mn, mo))
            if mo in ('zp', 'zpx', 'zpy', 'izx', 'izy'):
                zp[v].add(mn + ('' if mo == 'zp' else ',' + mo))
        if o.args[0] == 'abs':
            for k in sorted(refs):
                print('%04X' % k, ' '.join('%04X:%s/%s' % x for x in sorted(refs[k])[:6]),
                      '...' if len(refs[k]) > 6 else '')
        else:
            for k in sorted(zp):
                print('%02X' % k, ' '.join(sorted(zp[k])))


if __name__ == '__main__':
    main()
