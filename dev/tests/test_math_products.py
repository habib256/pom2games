#!/usr/bin/env python3
"""Exhaustive constant products and optional accumulator/shift entry points."""
from pathlib import Path
import subprocess
import tempfile
from test_math import ROOT, KS, a2test

MATH = ROOT / 'dev/lib/math'


def assemble(work, source):
    src = work / 'products.s'
    src.write_text(source)
    obj, binary, labels = (src.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(MATH), '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'),
                    '-Ln', str(labels), '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(labels)


def check_constants(work):
    for k in KS:
        source = f'''MUL_TABLES = $0800
.include "math.inc"
.code
        cld
        jsr mul_init
        lda #255
        sta mul_x
        sta mul_x+1
measure_start:
        jsr unsigned_product
measure_end:
        lda #0
        sta mul_x
        sta mul_x+1
sweep_start:
loop:
        ldy #$A5
        jsr unsigned_product
        ldx mul_x
        lda mul_p0
        sta results,x
        lda mul_p1
        sta results+256,x
        lda mul_p2
        sta results+512,x
        jsr signed_product
        ldx mul_x
        lda mul_p0
        sta results+768,x
        lda mul_p1
        sta results+1024,x
        lda mul_p2
        sta results+1280,x
        tya
        sta results+1536,x
        inc mul_x
        bne loop
page_done:
        nop
resume:
        inc mul_x+1
        bne loop
done:   jmp done
.include "mul.asm"
; Keep measured macro branches within a page in both implementations.
.segment "AUDIOCODE"
unsigned_product:
        MUL_K16 {k}
unsigned_end:
        rts
signed_product:
        MUL_KS16 {k}
signed_end:
        rts
.bss
results: .res 1792
.export measure_start, measure_end, sweep_start, page_done, resume, done, results
.export unsigned_product, unsigned_end, signed_product, signed_end
'''
        binary, labels = assemble(work, source)
        steps = a2test.bin_steps(binary) + [labels.until('measure_start'),
                labels.until('measure_end'), labels.until('sweep_start')]
        for _ in range(256):
            steps += [labels.until('page_done'), labels.peek('results',1792), labels.until('resume')]
        steps += [labels.until('done')]
        result = a2test.run(None, steps)
        for high in range(256):
            values = [high*256+low for low in range(256)]
            unsigned = [v*k for v in values]
            signed = [(v if v < 32768 else v-65536)*k for v in values]
            expected = bytes(v>>shift & 255 for array in (unsigned,signed)
                             for shift in (0,8,16) for v in array) + bytes([0xA5])*256
            assert result.mem(labels['results'],1792,high) == expected, (k,high)
        print(f'Constant {k}: all 65,536 unsigned/signed inputs, preserved Y; '
              f'{labels["unsigned_end"]-labels["unsigned_product"]}/'
              f'{labels["signed_end"]-labels["signed_product"]} B; '
              f'unsigned $FFFF {result.cycles[1]-result.cycles[0]} cycles including JSR/RTS; '
              f'sweep {result.cycles[-1]-result.cycles[2]} cycles.')


def check_shift_entries(work):
    for mode in ('acc','shift','both','neither'):
        entry = 'mul_acc' if mode in ('acc','both') else 'mul_p'
        stores = f'sta {entry}0'
        source = f'''MUL_TABLES = $0800
MUL_ACC = 1
.include "math.inc"
.code
        cld
        lda #0
        sta index
loop:   lda index
        {stores}
        eor #$A5
        sta {entry}1
        eor #$FF
        sta {entry}2
'''
        if mode in ('acc','both'):
            source += 'measure_start: jsr mul_acc_shr6\nmeasure_end:\n'
        elif mode == 'shift':
            source += 'measure_start: jsr mul_shr6\nmeasure_end:\n'
        source += ''' ldx index
 lda mul_p0
 sta results,x
 lda mul_p1
 sta results+256,x
 lda mul_p2
 sta results+512,x
 lda mul_acc0
 sta results+768,x
 lda mul_acc1
 sta results+1024,x
 lda mul_acc2
 sta results+1280,x
 inc index
 bne loop
done: jmp done
'''
        if mode == 'both':
            source += 'unused_caller: jsr mul_shr6\n rts\n'
        source += 'kernel_start:\n.include "mul.asm"\nkernel_end:\n'
        if mode == 'neither':
            source += '.assert .not .defined(mul_shr6), error, "unused shift"\n'
        if mode in ('shift','neither'):
            source += '.assert .not .defined(mul_acc_shr6), error, "unused accumulator"\n'
        source += '''.bss
index: .res 1
results: .res 1536
.export done, results, kernel_start, kernel_end
'''
        if mode != 'neither':
            source += '.export measure_start, measure_end\n'
        binary, labels = assemble(work,source)
        cycles = ''
        if mode != 'neither':
            result = a2test.run(None,a2test.bin_steps(binary) + [labels.until('measure_start'), labels.until('measure_end'),
                     labels.until('done'),labels.peek('results',1536)])
            cycles = f', {result.cycles[1]-result.cycles[0]} cycles including JSR/RTS'
            values = [n | ((n^0xA5)<<8) | ((n^0x5A)<<16) for n in range(256)]
            # mul_shr6 shifts left twice: p1:p2 is the signed floor quotient mod 65536.
            expected = bytes((v<<2)>>shift & 255 for shift in (0,8,16) for v in values)
            got = result.mem(labels['results'],1536)
            assert got[:768] == expected, mode
            if mode in ('acc','both'):
                original = bytes(v>>shift & 255 for shift in (0,8,16) for v in values)
                assert got[768:] == original, (mode,'accumulator changed')
        print(f'Shift include {mode}: {labels["kernel_end"]-labels["kernel_start"]} B '
              f'(including mandatory mul_init){cycles}; optional entries and outputs OK.')


def main():
    with tempfile.TemporaryDirectory(prefix='math-products-') as directory:
        work = Path(directory)
        check_constants(work)
        check_shift_entries(work)


if __name__ == '__main__':
    main()
