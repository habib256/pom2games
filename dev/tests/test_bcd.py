#!/usr/bin/env python3
"""lib/math/bcd.asm in a2run against Python: bcd_add_sat on 1- to 4-byte
packed BCD numbers (random, carries through every byte, overflow to
99..99 with C = 1), then bcd_put through a caller's output routine in three
builds: every digit, leading zeros as spaces, leading zeros left out (the
units digit always shown)."""
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

# Each case: X = n, then 4 bytes a, 4 bytes b; out: 4 bytes sum, C, then
# the digits of bcd_put(a) (8 chars max) and their count.
SRC = '''{options}
BCD_PUT_OUT = out_char
.zeropage
ptr:    .res 2
bcd_ptr: .res 2                 ; bcd.asm skips its own
.code
        LDA     #0
        STA     k
loop:   LDA     k
        CMP     #NCASES
        BCS     done
        ASL     A               ; case k at cases + 9 * k
        ASL     A
        ASL     A
        ADC     k
        ADC     #<cases
        STA     ptr
        LDA     #>cases
        ADC     #0
        STA     ptr+1
        LDY     #8
@cp:    LDA     (ptr),Y         ; n, a (4), b (4) -> work
        STA     work,Y
        DEY
        BPL     @cp
        LDA     #<(work+1)      ; a += b
        STA     bcd_ptr
        LDA     #>(work+1)
        STA     bcd_ptr+1
        LDX     work
        LDA     #<(work+5)
        LDY     #>(work+5)
        JSR     bcd_add_sat
        LDA     #0
        ROL     A
        PHA
        LDA     k               ; out: sum (4), C, digits (8), count
        ASL     A
        ASL     A
        ASL     A
        ASL     A
        TAY
        LDX     #0
@o:     LDA     work+1,X
        STA     outs,Y
        INY
        INX
        CPX     #4
        BNE     @o
        PLA
        STA     outs,Y
        INY
        STY     dig_ix
        TYA
        PHA
        LDY     #8              ; the original a again, through bcd_put
@cp2:   LDA     (ptr),Y
        STA     work,Y
        DEY
        BPL     @cp2
        LDX     work
        LDA     #<(work+1)
        LDY     #>(work+1)
        JSR     bcd_put
        PLA                     ; count of chars
        STA     tmp
        LDA     dig_ix
        SEC
        SBC     tmp
        LDY     tmp
        STA     outs+8,Y
        INC     k
        JMP     loop
done:   JMP     done
out_char:
        LDY     dig_ix          ; keeps X
        STA     outs,Y
        INC     dig_ix
        RTS
cases:  {cases}
NCASES = {ncases}
.bss
k:      .res 1
tmp:    .res 1
dig_ix: .res 1
work:   .res 9
outs:   .res 16 * NCASES
.code
.include "bcd.asm"
.export done, outs
'''


def bcd(v, n):
    s = f'{v:0{2 * n}d}'
    return bytes(int(s[i:i + 2], 16) for i in range(2 * n - 2, -1, -2))


def digits(v, n, lead):
    s = f'{v:0{2 * n}d}'
    if lead is None:
        return s
    t = s[:-1].lstrip('0') + s[-1]
    pad = len(s) - len(t)
    return (chr(lead) * pad if lead else '') + t


def cases(rng):
    out = []
    for n in (1, 2, 3, 4):
        top = 10 ** (2 * n)
        picks = [(0, 0), (1, top - 2), (top - 1, 1), (top - 1, top - 1), (5, 5), (top // 2, top // 2),
                 (int('9' * (2 * n - 1)), 1)]
        picks += [(rng.randrange(top), rng.randrange(top)) for _ in range(9)]
        out += [(n, a, b) for a, b in picks]
    return out


def run(work, name, options, cs, lead):
    rows = ', '.join(', '.join(str(x) for x in [n] + list(bcd(a, n).ljust(4, b'\0')) + list(bcd(b, n).ljust(4, b'\0')))
                     for n, a, b in cs)
    src = work / (name + '.s')
    src.write_text(SRC.format(options=options, cases='.byte ' + rows, ncases=len(cs)))
    obj, binary, lbl = (src.with_suffix(e) for e in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(ROOT / 'dev/lib/math'), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(lbl),
                    '-o', str(binary), str(obj)], check=True)
    L = a2test.labels(lbl)
    r = a2test.run(None, a2test.bin_steps(binary) + [L.until('done', 200), L.peek('outs', 16 * len(cs))])
    out = r.mem(L['outs'], 16 * len(cs))
    for k, (n, a, b) in enumerate(cs):
        row = out[16 * k:16 * k + 16]
        total = a + b
        sat = total >= 10 ** (2 * n)
        want = bcd(10 ** (2 * n) - 1 if sat else total, n)
        assert row[:n] == want and row[4] == int(sat), f'{name}: {a} + {b} ({n} B) gave {row[:5].hex()}'
        text = digits(a, n, lead)
        count = row[13]
        got = row[5:5 + count].decode('ascii')
        assert got == text, f'{name}: bcd_put {a} ({n} B) gave {got!r}, expected {text!r}'


def main():
    cs = cases(random.Random(1985))
    with tempfile.TemporaryDirectory(prefix='bcd-') as tmp:
        work = Path(tmp)
        for i in range(0, len(cs), 15):         # 16 output bytes a case: Y < 256
            chunk = cs[i:i + 15]
            run(work, f'all{i}', '', chunk, None)
            run(work, f'space{i}', 'BCD_PUT_LEAD = \' \'', chunk, ord(' '))
            run(work, f'skip{i}', 'BCD_PUT_LEAD = 0', chunk, 0)
    print(f'bcd: bcd_add_sat on {len(cs)} cases (1-4 bytes, carries, saturation), bcd_put with zeros, '
          'spaces and no leading zeros match Python.')


if __name__ == '__main__':
    main()
