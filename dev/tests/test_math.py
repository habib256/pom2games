#!/usr/bin/env python3
"""lib/math in a2run against Python: products, short cuts, constants,
floor shifts, sums, square roots, division and the LFSR, bit for bit.
Built twice: tables at $0800 with the seed in BSS, then both in HGR page 2."""
from pathlib import Path
import math
import random
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test  # noqa: E402

KS = (0, 1, 2, 64, 73, 128, 183, 255)


def s8(v):
    return v - 256 if v & 0x80 else v


def s16(v):
    return v - 65536 if v & 0x8000 else v


def le(v, n):
    return [(v >> (8 * i)) & 0xFF for i in range(n)]


def edge16():
    return [0, 1, 2, 0x7F, 0x80, 0xFF, 0x100, 0x1234, 0x7FFF, 0x8000, 0x8001, 0xFF00, 0xFFFF]


def cases(rng):
    """name -> (inputs, outputs, call, [(input bytes, expected bytes)])."""
    w16 = edge16() + [rng.randrange(65536) for _ in range(40)]
    w8 = [0, 1, 0x3F, 0x40, 0x7F, 0x80, 0xC0, 0xFF] + [rng.randrange(256) for _ in range(8)]
    pairs = [(x, y) for x in w16[:13] for y in w8[:8]] + \
        [(rng.randrange(65536), rng.randrange(256)) for _ in range(60)]
    p = ['mul_p0', 'mul_p1', 'mul_p2']
    xy = ['mul_x', 'mul_x+1', 'mul_y']
    out = {
        'u8u8': (['mul_x', 'mul_y'], p[:2], 'JSR mul_u8u8',
                 [((x & 255, y), le((x & 255) * y, 2)) for x, y in pairs[:160]]),
        'u16u8': (xy, p, 'JSR mul_u16u8', [(le(x, 2) + [y], le(x * y, 3)) for x, y in pairs[:160]]),
        's16s8': (xy, p, 'JSR mul_s16s8',
                  [(le(x, 2) + [y], le(s16(x) * s8(y), 3)) for x, y in pairs[:160]]),
        'dir': (['A', 'X', 'Y'], p, 'JSR mul_dir',
                [(le(x, 2) + [d], le(s16(x) * s8(d), 3)) for x in w16
                 for d in (0, 0x40, 0xC0, 1, 0x3F, 0x41, 0xBF, 0x80)][:160]),
        'shr6': (xy, p[1:], 'JSR mul_s16s8\n JSR mul_shr6',
                 [(le(x, 2) + [y], le(s16(x) * s8(y) >> 6, 2)) for x, y in pairs[:160]]),
        'acc': (['mul_x', 'mul_x+1', 'mul_y', 'v3', 'v4', 'v5'], p[1:],
                'JSR mul_s16s8\n JSR mul_acc_set\n LDA v3\n STA mul_x\n LDA v4\n STA mul_x+1\n'
                ' LDA v5\n STA mul_y\n JSR mul_s16s8\n JSR mul_acc_add\n JSR mul_acc_shr6',
                [(le(a, 2) + [b] + le(c, 2) + [d], le((s16(a) * s8(b) + s16(c) * s8(d)) >> 6, 2))
                 for a, b, c, d in ((rng.randrange(65536), rng.randrange(256),
                                     rng.randrange(65536), rng.randrange(256)) for _ in range(80))]),
        'isqrt': (['mul_x', 'mul_x+1'], ['A', 'mul_x', 'mul_x+1'], 'JSR isqrt16',
                  [(le(n, 2), [math.isqrt(n)] + le(n, 2)) for n in sorted(set(
                      list(range(0, 300)) + [k * k + e for k in range(16, 256) for e in (-1, 0)
                                             if 0 <= k * k + e < 65536][::2] +
                      [65535, 65025, 65024, 256 * 255] + [rng.randrange(65536) for _ in range(40)]))][::2][:200]),
        'div': (['mul_x', 'mul_x+1', 'A'], ['mul_x', 'mul_x+1', 'A'], 'JSR div16by8',
                [(le(n, 2) + [d], le(n // d, 2) + [n % d]) for n, d in
                 [(n, d) for n in edge16() for d in (1, 2, 3, 7, 0x80, 0xFF) ] +
                 [(rng.randrange(65536), rng.randrange(1, 256)) for _ in range(40)] +
                 [(rng.randrange(256 * d), d) for d in (rng.randrange(1, 256) for _ in range(40))]]),
    }
    w16 = w16[:25]
    for k in KS:
        out[f'k{k}'] = (['mul_x', 'mul_x+1'], p, f'MUL_K16 {k}', [(le(x, 2), le(x * k, 3)) for x in w16])
        out[f'ks{k}'] = (['mul_x', 'mul_x+1'], p, f'MUL_KS16 {k}',
                         [(le(x, 2), le(s16(x) * k, 3)) for x in w16])
    return out


def lfsr(lo, hi, n):
    s, vals = lo | hi << 8, []
    for _ in range(n):
        c = s & 1
        s >>= 1
        if c:
            s ^= 0xB400
        vals.append(s & 0xFF)
    return vals


def loop(name, ins, outs, call, rows):
    """Run `call` on each row of the input table, store the outputs."""
    nin, nout, n = len(ins), len(outs), len(rows)
    assert 0 < n <= 255, (name, n)
    load = []
    for i, dst in enumerate(ins):
        load += [f' LDY #{i}', ' LDA (ip),Y', f' STA {"v" + str(i) if dst in "AXY" else dst}']
    for i, dst in enumerate(ins):
        if dst in 'XY':
            load.append(f' LD{dst} v{i}')
    for i, dst in enumerate(ins):
        if dst == 'A':
            load.append(f' LDA v{i}')
    store = [' STA va'] if 'A' in outs else []
    for i, src in enumerate(outs):
        store += [f' LDA {"va" if src == "A" else src}', f' LDY #{i}', ' STA (op),Y']
    data = ', '.join(str(b) for inp, _ in rows for b in inp)
    return f'''
 LDA #<in_{name}
 STA ip
 LDA #>in_{name}
 STA ip+1
 LDA #<out_{name}
 STA op
 LDA #>out_{name}
 STA op+1
 LDA #{n}
 STA cnt
@{name}:
''' + '\n'.join(load) + f'\n {call}\n' + '\n'.join(store) + f'''
 CLC
 LDA ip
 ADC #{nin}
 STA ip
 BCC :+
 INC ip+1
:CLC
 LDA op
 ADC #{nout}
 STA op
 BCC :+
 INC op+1
:DEC cnt
 BEQ :+
 JMP @{name}
:
.pushseg
.rodata
in_{name}: .byte {data}
.segment "{'BSS' if name[0] == 'k' else 'LOWBSS'}"
out_{name}: .res {n * nout}
.popseg
'''


def build(work, defines, table):
    body = []
    for name, (ins, outs, call, rows) in table.items():
        body.append(loop(name, ins, outs, call, rows))
    src = f'''{defines}
MUL_ACC = 1
.include "apple2.inc"
.include "zp.inc"
.include "math.inc"
.zeropage
ip: .res 2
op: .res 2
cnt: .res 1
v0: .res 1
v1: .res 1
v2: .res 1
v3: .res 1
v4: .res 1
v5: .res 1
va: .res 1
.code
 JSR mul_init
 JSR sqrt_init
''' + ''.join(body) + '''
 LDA #$3C
 STA prng_lo
 LDA #$AD
 STA prng_hi
 LDX #0
@r: JSR rand8
 STA out_rand,X
 INX
 BNE @r
done: JMP done
.bss
out_rand: .res 256
.code
.include "sqrt.asm"
.include "div.asm"
.include "random.asm"
.include "mul.asm"
.export done
''' + ''.join(f'.export out_{n}\n' for n in table) + '.export out_rand\n'
    (work / 'm.s').write_text(src)
    inc = ['-I', str(ROOT / 'dev/lib/apple2'), '-I', str(ROOT / 'dev/lib/math')]
    subprocess.run(['ca65', *inc, '-o', str(work / 'm.o'), str(work / 'm.s')], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'), '-Ln', str(work / 'm.lbl'),
                    '-o', str(work / 'm.bin'), str(work / 'm.o')], check=True)
    return a2test.labels(work / 'm.lbl'), a2test.build_disk(work, 'MATH', work / 'm.bin')


def check(defines, table, label):
    with tempfile.TemporaryDirectory(prefix='math-') as tmp:
        work = Path(tmp)
        L, disk = build(work, defines, table)
        names = list(table)
        steps = [L.until('done', 20000)]
        for n in names:
            steps.append(L.peek(f'out_{n}', len(table[n][1]) * len(table[n][3])))
        steps.append(L.peek('out_rand', 256))
        r = a2test.run(disk, steps)
        for n in names + ['rand']:
            if n == 'rand':
                want = bytes(lfsr(0x3C, 0xAD, 256))
            else:
                want = bytes(b for _, o in table[n][3] for b in o)
            got = r.mem(L[f'out_{n}'], len(want))
            if got != want:
                k = next(i for i in range(len(want)) if got[i] != want[i])
                w = len(table[n][1]) if n != 'rand' else 1
                row = k // w
                inp = table[n][3][row][0] if n != 'rand' else row
                raise SystemExit(f'{label} {n}: row {row} input {inp}: got {list(got[row*w:row*w+w])} '
                                 f'want {list(want[row*w:row*w+w])}')
        return sum(len(t[3]) for t in table.values()) + 256


def main():
    table = cases(random.Random(1))
    n = check('MUL_TABLES = $0800', table, 'tables at $0800')
    check('MUL_TABLES = $4000\nSQRT_SEED = $4800', table, 'tables in HGR page 2')
    print(f'lib/math: {n} cases x 2 table placements == Python (products, mul_dir short cuts, '
          f'MUL_K16/KS16, shr6, sums, isqrt16, div16by8, rand8).')


if __name__ == '__main__':
    main()
