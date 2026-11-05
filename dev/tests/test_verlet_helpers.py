#!/usr/bin/env python3
"""Independent square/heavy/damping oracles, register/state guards and timings."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, run, a2test
from test_verlet_quarter_abs import CONFIG as QUARTER_CONFIG, constraints

CONFIG = QUARTER_CONFIG.replace(' BSS:', ' RODATA: load=MAIN, type=ro;\n BSS:')


def build(work, text, include):
    source, config = work / 'entry.s', work / 'entry.cfg'
    source.write_text(text)
    config.write_text(CONFIG)
    obj, binary, labels = (source.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    run(['ca65', '-I', include, '-I', DEV / 'lib/physics', '-I', DEV / 'lib/math',
         '-o', obj, source])
    run(['ld65', '-C', config, '-Ln', labels, '-o', binary, obj])
    return a2test.labels(labels), binary


def square(work, include, iie, bench):
    report = {}
    for table in (0x0800, 0x4000):
        for fast in (False, True):
            name = f'{table:04x}_'+('fast' if fast else 'generic')
            target = work / name
            target.mkdir()
            count = 181 if fast else 256
            stop = 'lda input\n cmp #181\n' if fast else ''
            source = f'''MUL_TABLES={table}
.include "math.inc"
VL_NPOINTS=1
'''+('VL_CON_FAST=1\n' if fast else '')+'''.include "verlet.inc"
.zeropage
input: .res 1
current: .res 1
high: .res 1
saved_hw: .res 1
flags: .res 1
.code
start:
 sei
 cld
 jsr mul_init
 lda #0
 sta input
loop:
 lda input
 and #1
 beq allow_irq
 sei
 bne invoke
allow_irq:
 cli
invoke:
 tsx
 stx saved_hw
 lda input
 ldy #$a5
 jsr vl_square
 sta current
 sty high
 php
 pla
 and #$0c
 sta flags
 lda input
 and #1
 asl
 asl
 cmp flags
 bne fail
 tsx
 cpx saved_hw
 bne fail
 ldx input
 lda current
 sta results,x
 lda high
 sta results+256,x
 inc input
'''+stop+''' bne loop
done: jmp done
fail: jmp fail
measure_setup:
 sei
 cld
 lda input
measure_start:
 jsr vl_square
measure_done: jmp measure_done
.align 256
.include "verlet_con.asm"
kernel_end:
.include "mul.asm"
.bss
results: .res 512
.export start,done,results,measure_setup,measure_start,measure_done,vl_square,kernel_end
.exportzp input
'''
            points, binary = build(target, source, include)
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            result = a2test.run(disk, a2test.bin_steps(binary) + [points.until('done'),
                                  points.peek('results', 512)], iie=iie)
            expected = bytearray(512)
            expected[:count] = bytes(n * n & 255 for n in range(count))
            expected[256:256+count] = bytes(n * n >> 8 for n in range(count))
            # The ASM fixture has no CRT clearing BSS: ignore uncalled FAST IDs.
            assert result.data[:count] == expected[:count], ('square low', name)
            assert result.data[256:256+count] == expected[256:256+count], ('square high', name)
            entry = dict(cases=count, code_bytes=points['kernel_end']-points['vl_square'],
                         binary_bytes=binary.stat().st_size,
                         binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
            if bench:
                entry['cycles'] = {}
                for value in (0, 1, 127, 128, 180) + (() if fast else (255,)):
                    steps = a2test.bin_steps(binary) + [points.until('done'),
                        points.poke('input', value), f'go:{points["measure_setup"]:04X}',
                        points.until('measure_start'), points.until('measure_done')]
                    timed = a2test.run(disk, steps, iie=iie)
                    entry['cycles'][str(value)] = timed.cycles[-1]-timed.cycles[-2]
            report[name] = entry
            print(f'Square {name}: {count} exact A/Y results, I/D and hardware stack; '
                  f'{entry["code_bytes"]} code bytes'+
                  (f', JSR/RTS cycles {entry["cycles"]}' if bench else ''))
    return report


def shifts(work, include, iie, bench):
    report = {}
    for kind in ('heavy', 'damp'):
        # HEAVY's immediate bias accepts 0..8. Zero retains the original
        # LDY #0 / DEY loop's 256 shifts; do not silently change that behavior.
        # Damping documents Y=1..7; also guard its neighboring counts 0 and 8.
        for shift in range(9):
            name = f'{kind}_{shift}'
            target = work / name
            target.mkdir()
            variable = 'vl_val' if kind == 'heavy' else 'vl_vt'
            helper = 'vl_heavy' if kind == 'heavy' else 'vl_damp'
            fields = [variable, variable+'+1']
            if kind == 'heavy':
                fields += ['vl_vn', 'vl_vn+1']
            fields += ['returned_flags']
            planes = len(fields)
            copy = ''.join(f' lda {field}\n sta results+{index*256},x\n'
                           for index, field in enumerate(fields))
            source = f'''MUL_TABLES=$0800
.include "math.inc"
.zeropage
vl_vt: .res 2
input: .res 2
current: .res 2
returned_flags: .res 1
saved_hw: .res 1
VL_NPOINTS=1
VL_NCON=1
VL_CON_HEAVY_SHIFT={shift}
.include "verlet.inc"
.code
start:
 sei
 cld
 lda #0
 sta input
 sta input+1
sweep_start: nop
loop:
 lda input
 and #1
 beq allow_irq
 sei
 bne invoke
allow_irq:
 cli
invoke:
 tsx
 stx saved_hw
 lda input
 sta {variable}
 lda input+1
 sta {variable}+1
 ldx #$a5
 ldy #{shift}
 jsr {helper}
 sta current
 php
 pla
 sta returned_flags
 cpx #$a5
 bne fail
 cpy #0
 bne fail
 and #$0c
 sta current+1
 lda input
 and #1
 asl
 asl
 cmp current+1
 bne fail
 lda current
 cmp {variable}+1
 bne fail
 tsx
 cpx saved_hw
 bne fail
 ldx input
{copy} inc input
 bne loop
page_done: nop
resume:
 inc input+1
 bne loop
done: jmp done
fail: jmp fail
measure_setup:
 sei
 cld
 lda input
 sta {variable}
 lda input+1
 sta {variable}+1
 ldx #$a5
 ldy #{shift}
measure_start:
 jsr {helper}
measure_done: jmp measure_done
.align 256
kernel_start:
.include "verlet_con.asm"
.include "verlet.asm"
kernel_end:
.bss
results: .res {planes*256}
.export start,sweep_start,page_done,resume,done,results
.export measure_setup,measure_start,measure_done,kernel_start,kernel_end
.exportzp input
'''
            points, binary = build(target, source, include)
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            steps = a2test.bin_steps(binary) + [points.until('sweep_start')]
            for _ in range(256):
                steps.extend((points.until('page_done'), points.peek('results', planes*256),
                              points.until('resume')))
            steps.append(points.until('done'))
            result = a2test.run(disk, steps, iie=iie, timeout=180)
            for high in range(256):
                values = []
                for low in range(256):
                    bits = high*256+low
                    value = bits if bits < 32768 else bits-65536
                    if kind == 'heavy':
                        biased = value + ((1 << shift)-1 if value < 0 else 0)
                        delta = biased >> (shift or 256)
                        values.append(((value+delta)&65535, (value-delta)&65535))
                    else:
                        # Use the contract's signed floor division, independent
                        # of the implementation's 24-bit left-shift loop.
                        # Count zero retains its original counter-wrap result.
                        delta = value >> (8-shift) if shift else 0
                        values.append(((value-delta)&65535,))
                for plane in range(planes-1):
                    expected = bytes(value[plane//2] >> (8*(plane%2)) & 255
                                     for value in values)
                    actual = result.dumps[high][plane*256:(plane+1)*256]
                    assert actual == expected, (kind, shift, high, plane)
            entry = dict(cases=65536, code_bytes=points['kernel_end']-points['kernel_start'],
                         sweep_cycles=result.cycles[-1]-result.cycles[0],
                         state_sha256=hashlib.sha256(result.data).hexdigest())
            if bench:
                entry['cycles'] = {}
                for value in (0, 1, 32767, -32768, -1):
                    bits = value & 65535
                    steps = a2test.bin_steps(binary, start=points['measure_setup']) + [
                        points.poke('input', bits&255),
                        f'poke:{points["input"]+1:04X}:{bits>>8:02X}',
                        points.until('measure_start'), points.until('measure_done')]
                    timed = a2test.run(disk, steps, iie=iie)
                    entry['cycles'][str(value)] = timed.cycles[-1]-timed.cycles[-2]
            report[name] = entry
            print(f'{name}: all 65,536 inputs, exact model, A/X/Y, I/D and stack; '
                  f'{entry["code_bytes"]} code bytes'+
                  (f', JSR/RTS cycles {entry["cycles"]}' if bench else ''), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path,
                        help='directory containing saved verlet_con.asm and verlet.asm sources')
    parser.add_argument('--only', choices=('square', 'shifts'))
    parser.add_argument('--bench', action='store_true', help='also print direct and integrated timings')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='verlet-helpers-') as directory:
        work = Path(directory)
        include = DEV / 'lib/physics'
        if args.reference:
            include = work / 'reference'
            include.mkdir()
            for name in ('verlet_con.asm', 'verlet.asm'):
                (include / name).write_bytes((args.reference / name).read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        if args.only != 'shifts':
            report['square'] = square(work, include, args.iie, args.bench)
        if args.only != 'square':
            report['shifts'] = shifts(work, include, args.iie, args.bench)
        if args.bench:
            report['constraints'] = constraints(work, include, args.iie)
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
