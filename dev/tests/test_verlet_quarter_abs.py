#!/usr/bin/env python3
"""Quarter-distance values/registers and I/D; arithmetic flags are clobbered."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import tempfile
from test_hgr import DEV, run, a2test


SOURCE = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
.include "verlet.inc"
.zeropage
input: .res 2
current: .res 1
saved_hw: .res 1
flags: .res 1
.code
start:
 sei
 cld
 lda #0
 sta input
 sta input+1
sweep_start:
 nop
loop:
 ; Alternate the caller's IRQ state, and dirty the incoming Y register.
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
 ldy input
 lda input
 ldx input+1
 jsr vl_quarter_abs
 sta current
 cpx input+1
 bne fail
 lda input+1
 bmi negative
 cpy #0
 bne fail
 beq check_flags
negative:
 cpy #$ff
 bne fail
check_flags:
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
 inc input
 bne loop
page_done:
 nop
resume:
 inc input+1
 bne loop
done:
 jmp done
fail:
 jmp fail
measure_setup:
 sei
 cld
 ldy input
 lda input
 ldx input+1
measure_start:
 jsr vl_quarter_abs
measure_done:
 jmp measure_done
.align 256
.include "verlet_con.asm"
kernel_end:
.bss
results: .res 256
.export start,sweep_start,page_done,resume,done,results
.export measure_setup,measure_start,measure_done,vl_quarter_abs,kernel_end
.exportzp input
'''

CONFIG = '''MEMORY {
 ZP: start=$50, size=$B0, type=rw;
 MAIN: start=$6000, size=$3000, type=rw, file=%O;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 CODE: load=MAIN, type=ro, align=$100;
 BSS: load=MAIN, type=bss;
}
'''


def primitive(work, include, iie, cycles):
    source, config = work / 'entry.s', work / 'entry.cfg'
    source.write_text(SOURCE)
    config.write_text(CONFIG)
    obj, binary, labels = (source.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    run(['ca65', '-I', include, '-I', DEV / 'lib/physics', '-I', DEV / 'lib/math',
         '-o', obj, source])
    run(['ld65', '-C', config, '-Ln', labels, '-o', binary, obj])
    points = a2test.labels(labels)
    disk = a2test.build_disk(work, 'TEST', binary) if iie else None
    steps = a2test.bin_steps(binary) + [points.until('sweep_start')]
    for _ in range(256):
        steps.extend((points.until('page_done'), points.peek('results', 256),
                      points.until('resume')))
    steps.append(points.until('done'))
    result = a2test.run(disk, steps, iie=iie)
    expected = bytes(min(abs((n if n < 32768 else n - 65536) // 64), 180)
                     for n in range(65536))
    assert result.data == expected, 'quarter distance / signed floor / clamp'
    report = dict(code_bytes=points['kernel_end'] - points['vl_quarter_abs'],
                  sweep_cycles=result.cycles[-1] - result.cycles[0])
    print(f'Verlet quarter distance: all 65,536 signed inputs, X preserved, Y sign, '
          f'IRQ/decimal state and hardware stack unchanged; IIe={iie}, '
          f'{report["code_bytes"]} code bytes, {report["sweep_cycles"]:,} sweep cycles.')
    if cycles:
        report['direct_cycles'] = {}
        for value in (0, 63, 64, 11519, 11520, 32767, -1, -64, -65,
                      -11520, -11521, -32768):
            bits = value & 65535
            steps = a2test.bin_steps(binary, start=points['measure_setup']) + [
                points.poke('input', bits & 255),
                f'poke:{points["input"] + 1:04X}:{bits >> 8:02X}',
                points.until('measure_start'), points.until('measure_done')]
            result = a2test.run(disk, steps, iie=iie)
            cost = result.cycles[1] - result.cycles[0]
            report['direct_cycles'][str(value)] = cost
            print(f'  quarter({value}): {cost} cycles including JSR/RTS')
    return report


def constraints(work, include, iie):
    # Reuse the maintained physics fixture and its model, rather than adding
    # separate game constants. Seed 7 selects deterministic mixed plain/heavy
    # and saturated/near-rest calls from the existing constraint cases.
    import test_verlet as verlet
    from verlet import harness
    rows = [row for row in verlet.cases(random.Random(7))
            if verlet.OPS[row[1]] == 'con'][:12]
    script = [(1, list(row[0]) + [row[1], row[2], row[3], row[4], row[5],
                                row[6] & 255, row[6] >> 8, row[7], row[8]], 1)
              for row in rows]
    expected = b''.join(verlet.model1(row) for row in rows)
    report = {}
    for definitions, name in verlet.SPEED:
        target = work / name.replace(' ', '_')
        target.mkdir()
        prelude = verlet.prelude1().replace('.include "verlet.inc"',
                                           definitions + '\n.include "verlet.inc"')
        text = harness.source(prelude, verlet.EPILOGUE1, verlet.INPUTS1,
                              verlet.SNAPS1, script, init='mul_init', snap_seg='LOWBSS')
        text = text.replace('hs_tick: JSR    tick\n',
                            'hs_tick: JSR    tick\nmeasure_end:\n')
        text += '\n.export hs_tick,measure_end\n'
        points, binary = harness.build(target, text, includes=(include,))
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)
        for _ in rows:
            steps.extend((points.until('hs_tick'), points.until('measure_end')))
        steps.extend((points.until('hs_done'), points.peek('hs_snaps', len(expected))))
        result = a2test.run(disk, steps, iie=iie)
        assert result.data == expected, ('integrated constraints', name)
        costs = [result.cycles[i * 2 + 1] - result.cycles[i * 2]
                 for i in range(len(rows))]
        report[name] = dict(cycles=costs, binary_bytes=binary.stat().st_size,
                            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        print(f'  {name}: {binary.stat().st_size} loaded bytes; '
              f'12 model-checked constraint calls {costs}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path,
                        help='test a saved verlet_con.asm source instead of the current one')
    parser.add_argument('--cycles', '--bench', action='store_true',
                        help='also measure isolated calls and 12 constraints under all speed switches')
    parser.add_argument('--out', type=Path, help='write the measured results as JSON')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='verlet-quarter-') as directory:
        work = Path(directory)
        include = DEV / 'lib/physics'
        if args.reference:
            include = work / 'reference'
            include.mkdir()
            (include / 'verlet_con.asm').write_bytes(args.reference.read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502',
                      reference=bool(args.reference),
                      primitive=primitive(work, include, args.iie, args.cycles))
        if args.cycles:
            report['constraints'] = constraints(work, include, args.iie)
        if args.out:
            args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
