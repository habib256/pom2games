#!/usr/bin/env python3
"""Exhaustive products, alias/state guards and optional shift entry points.

Arithmetic flags NZCV and A/X are scratch. The input, Y, other math slots,
IRQ/decimal state and stack are preserved. Power cases poison all tables.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from test_math import ROOT, KS, a2test
from test_verlet_ground_probes import identity, metadata
from verlet import harness

MATH = ROOT / 'dev/lib/math'
CONSTANTS = sorted(set(KS) | {4,8,16,32})
CHANGED_CONSTANTS = (1, 2, 4, 8, 16)
SLOTS = (('mul_x', 2), ('mul_y', 1), ('mul_p0', 1), ('mul_p1', 1),
         ('mul_p2', 1), ('mul_t', 1), ('mul_s1l', 2), ('mul_s1h', 2),
         ('mul_s2l', 2), ('mul_s2h', 2), ('mul_acc0', 1), ('mul_acc1', 1),
         ('mul_acc2', 1))
FIELDS = tuple(name if index == 0 else f'{name}+{index}'
               for name, size in SLOTS for index in range(size))


def aliases(layout):
    if layout == 'default':
        return ''
    base = 0x10 if layout == 'zp_alias' else 0x4000
    # Independent caller-owned slots: noncontiguous, with gaps around each.
    return ''.join(f'{name} = ${base+index*3:04x}\n'
                   for index, (name, _) in enumerate(SLOTS))


def assemble(work, source, include):
    src = work / 'products.s'
    src.write_text(source)
    obj, binary, labels = (src.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-I', str(include), '-I', str(MATH),
                    '-o', str(obj), str(src)], check=True)
    subprocess.run(['ld65', '-C', str(ROOT / 'dev/cc65/apple2_hgr.cfg'),
                    '-Ln', str(labels), '-o', str(binary), str(obj)], check=True)
    return binary, a2test.labels(labels)


def check_constants(work, include, iie, bench, layout='default'):
    report = {}
    for k in CONSTANTS if layout == 'default' else CHANGED_CONSTANTS:
        table_free = k == 0 or k & (k-1) == 0
        initialize = '''lda #$A5
        ldx #0
poison_tables:
        .repeat 8, page
                sta MUL_TABLES+page*256,x
        .endrepeat
        inx
        bne poison_tables''' if table_free else 'jsr mul_init'
        source = aliases(layout) + f'''MUL_TABLES = $0800
.include "math.inc"
.code
        cld
        {initialize}
        lda #255
        sta mul_x
        sta mul_x+1
measure_start:
        jsr unsigned_product
measure_end:
        nop
signed_negative_start:
        jsr signed_product
signed_negative_end:
        lda #255
        sta mul_x
        lda #127
        sta mul_x+1
signed_positive_start:
        jsr signed_product
signed_positive_end:
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
@caller_scope:
        MUL_K16 {k}
        .assert .defined(@caller_scope), error, "macro changed caller scope"
unsigned_end:
        rts
signed_product:
@caller_scope:
        MUL_KS16 {k}
        .assert .defined(@caller_scope), error, "macro changed caller scope"
signed_end:
        rts
.bss
results: .res 1792
.export measure_start, measure_end, sweep_start, page_done, resume, done, results
.export unsigned_product, unsigned_end, signed_product, signed_end
.export signed_negative_start, signed_negative_end, signed_positive_start, signed_positive_end
'''
        binary, labels = assemble(work, source, include)
        steps = a2test.bin_steps(binary) + [labels.until('measure_start'),
                labels.until('measure_end'), labels.until('signed_negative_start'),
                labels.until('signed_negative_end'), labels.until('signed_positive_start'),
                labels.until('signed_positive_end'), labels.until('sweep_start')]
        for _ in range(256):
            steps += [labels.until('page_done'), labels.peek('results',1792), labels.until('resume')]
        steps += [labels.until('done')]
        disk = a2test.build_disk(work, 'TEST', binary) if iie else None
        result = a2test.run(disk, steps, iie=iie)
        for high in range(256):
            values = [high*256+low for low in range(256)]
            unsigned = [v*k for v in values]
            signed = [(v if v < 32768 else v-65536)*k for v in values]
            expected = bytes(v>>shift & 255 for array in (unsigned,signed)
                             for shift in (0,8,16) for v in array) + bytes([0xA5])*256
            assert result.mem(labels['results'],1792,high) == expected, (k,high)
        row = dict(cases=65536, unsigned_bytes=labels['unsigned_end']-labels['unsigned_product'],
                   signed_bytes=labels['signed_end']-labels['signed_product'],
                   unsigned_ffff_cycles=result.cycles[1]-result.cycles[0],
                   signed_ffff_cycles=result.cycles[3]-result.cycles[2],
                   signed_7fff_cycles=result.cycles[5]-result.cycles[4],
                   sweep_cycles=result.cycles[-1]-result.cycles[6],
                   snapshot_sha256=hashlib.sha256(b''.join(result.dumps)).hexdigest())
        report[str(k)] = row
        cost = (f'; {row["unsigned_bytes"]}/{row["signed_bytes"]} B unsigned/signed; '
                f'signed positive/negative {row["signed_7fff_cycles"]}/{row["signed_ffff_cycles"]} '
                'cycles including JSR/RTS') if bench else ''
        print(f'Constant {k} ({layout}): all 65,536 unsigned/signed inputs, preserved Y'
              f'{" (poisoned tables)" if table_free else ""}{cost}.', flush=True)
    return report


def check_shift_entries(work, include, iie):
    report = {}
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
        binary, labels = assemble(work,source,include)
        cycles = ''
        if mode != 'neither':
            disk = a2test.build_disk(work, 'TEST', binary) if iie else None
            result = a2test.run(disk,a2test.bin_steps(binary) + [labels.until('measure_start'), labels.until('measure_end'),
                     labels.until('done'),labels.peek('results',1536)],iie=iie)
            cycles = f', {result.cycles[1]-result.cycles[0]} cycles including JSR/RTS'
            values = [n | ((n^0xA5)<<8) | ((n^0x5A)<<16) for n in range(256)]
            # mul_shr6 shifts left twice: p1:p2 is the signed floor quotient mod 65536.
            expected = bytes((v<<2)>>shift & 255 for shift in (0,8,16) for v in values)
            got = result.mem(labels['results'],1536)
            assert got[:768] == expected, mode
            if mode in ('acc','both'):
                original = bytes(v>>shift & 255 for shift in (0,8,16) for v in values)
                assert got[768:] == original, (mode,'accumulator changed')
        report[mode] = dict(kernel_bytes=labels['kernel_end']-labels['kernel_start'])
        if mode != 'neither':
            report[mode].update(cycles=result.cycles[1]-result.cycles[0],
                                snapshot_sha256=hashlib.sha256(result.data).hexdigest())
        print(f'Shift include {mode}: {labels["kernel_end"]-labels["kernel_start"]} B '
              f'(including mandatory mul_init){cycles}; optional entries and outputs OK.')
    return report


def check_guards(work, include, iie):
    report = {}
    for layout in ('default', 'zp_alias', 'absolute_alias'):
        for signed in (False, True):
            for k in CHANGED_CONSTANTS:
                name = f'{layout}_{"signed" if signed else "unsigned"}_{k}'
                target = work / name
                target.mkdir()
                rows, expected = [], []
                for value in (0, 1, 127, 128, 255, 256, 32767, 32768, 32769, 65535):
                    # Dirty C/V, both IRQ states, D=0 as required by math.
                    for flag in (0x30, 0x31, 0x70, 0x71, 0x34, 0x35, 0x74, 0x75):
                        values = [(value+flag*7+index*37)&255
                                  for index in range(len(FIELDS))]
                        values[:2] = [value&255, value>>8]
                        operand = value-65536 if signed and value >= 32768 else value
                        product = operand*k & 0xFFFFFF
                        after = values[:]
                        after[3:6] = [product&255, product>>8&255, product>>16]
                        rows.append((1, values+[flag], 1))
                        expected.append(bytes(after+[flag&12, 0x5A, 0]))
                prelude = aliases(layout) + '''MUL_TABLES=$0800
MUL_ACC=1
.include "math.inc"
.zeropage
incoming_flags: .res 1
returned_flags: .res 1
returned_y: .res 1
stack_delta: .res 1
saved_hw: .res 1
.code
'''
                epilogue = f'''init:
 lda #$A5
 ldx #0
@poison:
 .repeat 8,page
 sta MUL_TABLES+page*256,x
 .endrepeat
 inx
 bne @poison
 rts
tick:
 tsx
 stx saved_hw
 ldx #$34
 ldy #$5A
 lda incoming_flags
 pha
 plp
 jsr product
 php
 pla
 and #$0C
 sta returned_flags
 sty returned_y
 tsx
 txa
 sec
 sbc saved_hw
 sta stack_delta
 rts
product:
@caller_scope:
 {"MUL_KS16" if signed else "MUL_K16"} {k}
 .assert .defined(@caller_scope),error,"macro changed caller scope"
 rts
'''
                fields = [*FIELDS, 'returned_flags', 'returned_y', 'stack_delta']
                source = '.macpack longbranch\n' + harness.source(
                    prelude, epilogue, inputs=[*FIELDS, 'incoming_flags'],
                    snaps=[(field, 1) for field in fields], rows=rows, init='init')
                # The many independent alias snapshots exceed a short branch.
                source = source.replace('BEQ     hs_next', 'jeq     hs_next')
                labels, binary = harness.build(target, source, includes=(include,))
                disk = a2test.build_disk(target, 'TEST', binary) if iie else None
                result = a2test.run(disk, a2test.bin_steps(binary) + [
                    labels.until('hs_done', 3000),
                    labels.peek('hs_snaps', len(expected)*len(fields)),
                    'peek:0800:2048'], iie=iie)
                assert result.dumps[0] == b''.join(expected), name
                assert result.dumps[1] == bytes([0xA5])*2048, (name, 'tables touched')
                report[name] = dict(cases=len(expected),
                                    snapshot_sha256=hashlib.sha256(result.data).hexdigest())
    print('2,400 input/scratch/Y/I/D/stack guards and poisoned-table checks OK.', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='saved math.inc source')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--bench', action='store_true', help='print isolated signed call costs')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or MATH / 'math.inc'
    with tempfile.TemporaryDirectory(prefix='math-products-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        (include / 'math.inc').write_bytes(selected.read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        report['constants'] = {
            layout: check_constants(work, include, args.iie, args.bench, layout)
            for layout in ('default', 'zp_alias', 'absolute_alias')}
        report['guards'] = check_guards(work, include, args.iie)
        report['shifts'] = check_shift_entries(work, include, args.iie)
        report.update(metadata(selected, args.iie))
        report['test_sha256'] = identity(__file__)['sha256']
        del report['probe_config_sha256']
        report['support_sources'] = [identity(path) for path in (
            MATH / 'mul.asm', ROOT / 'dev/cc65/apple2_hgr.cfg')]
        report['test_dependencies'] = [identity(path) for path in (
            ROOT / 'dev/tests/test_math.py', ROOT / 'dev/tests/test_verlet_ground_probes.py',
            ROOT / 'dev/tools/verlet/harness.py')]
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
