#!/usr/bin/env python3
"""Run the SYS relocator macros (dev/lib/prodos/sysreloc.inc) on a 65C02.

Both downward variants (default and SYSRELOC_DOWN_FAST) are assembled with
the inline and the subroutine forms and run on overlapping and disjoint
ranges, lengths with and without a tail or whole pages; the result is
compared with a Python model of memmove. The forward page and byte copies
are checked the same way, and the cycles per byte are reported.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / 'dev'
PD = DEV / 'lib/prodos'
sys.path.insert(0, str(DEV / 'tools'))
import a2test

CFG = '''MEMORY { RAM: start=$6000,size=$2000,type=rw,file=%O; }
SEGMENTS { CODE: load=RAM,type=ro; }
'''
LO, HI = 0x2000, 0x5000          # the test window

# (src, dst, len): overlap by 1 byte, by less than a page, by pages, tail
# only, pages only, disjoint downwards (RSS's L8 part), unaligned bases.
DOWN = [(0x2000, 0x2001, 1), (0x2000, 0x2001, 0x300), (0x2010, 0x2080, 0x1FF),
        (0x2000, 0x2100, 0x100), (0x2003, 0x20F0, 0x2345), (0x20FF, 0x2201, 0x2D00),
        (0x3000, 0x2000, 0x3C0), (0x2000, 0x2000 + 0x80, 0x2F00), (0x2001, 0x2002, 0xFF)]
PAGES = [(0x2080, 0x3000, 3), (0x2000, 0x4000, 1)]
BYTES = [(0x2010, 0x4F00, 0xD0), (0x2010, 0x2011, 1)]


def pattern():
    return bytearray(((a * 7) ^ (a >> 8)) & 255 for a in range(LO, HI))


def source(fast):
    s = ['.setcpu "65C02"']
    if fast:
        s.append('SYSRELOC_DOWN_FAST = 1')
    s += ['.include "sysreloc.inc"', '.code',
          # fill: the same pattern as pattern()
          '''fill:   lda #<$2000
        sta $06
        lda #>$2000
        sta $07
        ldy #0
@loop:  lda $06
        asl
        asl
        asl
        sec
        sbc $06                 ; 7 * low byte
        eor $07
        sta ($06),y
        inc $06
        bne @loop
        inc $07
        lda $07
        cmp #>$5000
        bne @loop
        rts''']
    for i, (src, dst, n) in enumerate(DOWN):
        s += [f'down{i}:', f' sysreloc_copy_down ${src:04X}, ${dst:04X}, ${n:04X}', ' rts',
              f'sub{i}:', f' sysreloc_down_args ${src:04X}, ${dst:04X}, ${n:04X}', ' jsr copy', ' rts']
    for i, (src, dst, n) in enumerate(PAGES):
        s += [f'pages{i}:', f' sysreloc_copy_pages ${src:04X}, ${dst:04X}, {n}', ' rts']
    for i, (src, dst, n) in enumerate(BYTES):
        s += [f'bytes{i}:', f' sysreloc_copy_bytes ${src:04X}, ${dst:04X}, {n}', ' rts']
    s += [' sysreloc_down_sub copy', '']
    return '\n'.join(s)


def build(work, fast):
    name = 'fast' if fast else 'default'
    src = work / f'{name}.s'
    src.write_text(source(fast))
    obj, binary, lbl = (src.with_suffix(x) for x in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '--cpu', '65c02', '-g', '-I', str(PD), '-o', str(obj), str(src)], check=True)
    cfg = work / 'test.cfg'
    cfg.write_text(CFG)
    subprocess.run(['ld65', '-C', str(cfg), '-Ln', str(lbl), '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(lbl)


def check(work, fast):
    binary, L = build(work, fast)
    cases = []
    for i, (src, dst, n) in enumerate(DOWN):
        cases += [(f'down{i}', src, dst, n), (f'sub{i}', src, dst, n)]
    cases += [(f'pages{i}', src, dst, n * 256) for i, (src, dst, n) in enumerate(PAGES)]
    cases += [(f'bytes{i}', src, dst, n) for i, (src, dst, n) in enumerate(BYTES)]
    steps = [f'load:{binary}@6000']
    for fn, *_ in cases:
        steps += [f'call:{L["fill"]:04X}:100', 'regs:00:00:00', f'call:{L[fn]:04X}:200',
                  f'peek:{LO:04X}:{HI - LO}']
    disk = work / 'stub.dsk'
    disk.write_bytes(bytes(143360))
    r = a2test.run(disk, steps, iie=True)
    import re
    calls = [int(c) for c in re.findall(r'call [0-9A-F]+ cycles=\d+ elapsed=(\d+)', r.out)]
    per_byte = {}
    for k, (fn, src, dst, n) in enumerate(cases):
        want = pattern()
        want[dst - LO:dst - LO + n] = want[src - LO:src - LO + n]
        got = r.mem(LO, HI - LO, k)
        assert got == bytes(want), (fast, fn, hex(src), hex(dst), hex(n),
                                    next(i for i in range(len(got)) if got[i] != want[i]) + LO)
        if fn.startswith('down'):
            per_byte[n] = calls[2 * k + 1] / n
    big = max(per_byte)
    return len(cases), per_byte[big], big, binary.stat().st_size


if __name__ == '__main__':
    if a2test.have_a2shot('ProDOS SYS relocator (65C02)'):
        with tempfile.TemporaryDirectory(prefix='prodos-sysreloc-') as tmp:
            work = Path(tmp)
            n0, c0, big, _ = check(work, False)
            n1, c1, _, _ = check(work, True)
            print(f'SYS relocator: {n0}+{n1} copies (overlap down, disjoint, tail/pages, '
                  f'inline/subroutine, pages, bytes) match memmove; ${big:04X} bytes down: '
                  f'{c0:.1f} cycles/byte default, {c1:.1f} with SYSRELOC_DOWN_FAST OK.')
