#!/usr/bin/env python3
"""Bounded constraint shifts and pair damping: independent models and timings."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, a2test
from test_verlet_helpers import CONFIG, build, shifts
from test_verlet_ground_probes import identity, metadata
from test_verlet_quarter_abs import constraints


def generic(work, include, iie, bench):
    source = (include / 'verlet_con.asm').read_text()
    index = source.index('        LDY     #3')
    start = source.rfind('.else\n', 0, index)+len('.else\n')
    block = source[start:source.index('@dok:', start)]+'@dok:\n'
    report = dict(cases=0, code_bytes=None, sweep_cycles=0)
    digest = hashlib.sha256()
    for negative in (False, True):
        text = f'''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
VL_NCON=1
.include "verlet.inc"
.zeropage
input: .res 2
saved_hw: .res 1
saved_flags: .res 1
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
 sta vl_w0
 lda input+1
 sta vl_w1
 lda #{255 if negative else 0}
 sta vl_w2
 ldx #$a5
 ldy #$5a
 jsr kernel
 cpx #$a5
 bne fail
 tsx
 cpx saved_hw
 bne fail
 php
 pla
 and #$0c
 sta saved_flags
 lda input
 and #1
 asl
 asl
 cmp saved_flags
 bne fail
 ldx input
 lda vl_w0
 sta results,x
 lda vl_w1
 sta results+256,x
 lda vl_w2
 sta results+512,x
 inc input
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
 sta vl_w0
 lda input+1
 sta vl_w1
 lda #{255 if negative else 0}
 sta vl_w2
measure_start:
 jsr kernel
measure_done: jmp measure_done
.align 256
kernel:
''' + block + '''
 rts
kernel_end:
.bss
results: .res 768
.export sweep_start,done,page_done,resume,results,kernel,kernel_end
.export measure_setup,measure_start,measure_done
.exportzp input
'''
        target = work / ('negative' if negative else 'positive')
        target.mkdir()
        labels, binary = build(target, text, include)
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)+[labels.until('sweep_start')]
        for _ in range(256):
            steps += [labels.until('page_done'), labels.peek('results', 768), labels.until('resume')]
        steps.append(labels.until('done'))
        result = a2test.run(disk, steps, iie=iie, timeout=180)
        for high in range(256):
            expected = bytearray(768)
            for low in range(256):
                value = high*256+low-(65536 if negative else 0)
                factor = max(-4095, min(4095, value//8)) & 65535
                expected[low], expected[256+low] = factor & 255, factor >> 8
                expected[512+low] = 255 if negative else 0
            assert result.dumps[high] == expected, ('generic shift/clamp', negative, high)
        report['cases'] += 65536
        report['sweep_cycles'] += result.cycles[-1]-result.cycles[0]
        report['code_bytes'] = labels['kernel_end']-labels['kernel']
        digest.update(result.data)
        if bench:
            costs = report.setdefault('cycles', {})
            values = ((-65536, -65535, -32769, -32768, -32761, -8, -1) if negative
                      else (0, 1, 7, 8, 32760, 32767, 32768, 64800, 65535))
            for value in values:
                bits = value & 65535
                timed = a2test.run(disk, a2test.bin_steps(binary, start=labels['measure_setup'])+[
                    labels.poke('input', bits & 255),
                    f'poke:{labels["input"]+1:04X}:{bits>>8:02X}',
                    labels.until('measure_start'), labels.until('measure_done')], iie=iie)
                costs[str(value)] = timed.cycles[-1]-timed.cycles[-2]
    report['state_sha256'] = digest.hexdigest()
    print(f'Generic: {report["cases"]:,} signed words, exact floor/clamp and w2 sign; '
          f'{report["code_bytes"]} code bytes; X/I/D and stack checked.', flush=True)
    return report


def fixed_timings(work, include, iie):
    # Exhaustive fixed-gain results are covered by test_verlet_fixed_gain.py;
    # retain direct size/cycle evidence here beside the other shift timings.
    source = (include / 'verlet_con.asm').read_text()
    start = source.index('        LDA     vl_w2\n        BPL     @fk')
    stop = source.index('\n.else\n', source.index('@fok:   STA     vl_fcoef', start))
    block = source[start:stop]
    report = {}
    for gain in range(9):
        text = f'''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
VL_NCON=1
VL_CON_FIXED_K={gain}
_VL_FKN=11-VL_CON_FIXED_K
.include "verlet.inc"
.zeropage
input: .res 3
.code
setup:
 sei
 cld
 lda input
 sta vl_w0
 lda input+1
 sta vl_w1
 lda input+2
 sta vl_w2
measure_start:
 jsr kernel
measure_done: jmp measure_done
.align 256
kernel:
''' + block + '''
 rts
kernel_end:
.export setup,measure_start,measure_done,kernel,kernel_end
.exportzp input,vl_fcoef
'''
        target = work / f'fixed_{gain}'
        target.mkdir()
        labels, binary = build(target, text, include)
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        entry = dict(code_bytes=labels['kernel_end']-labels['kernel'], cycles={})
        for value in (-65535, -32768, -2048, -1, 0, 1, 2048, 32767, 64800):
            factor = abs(value)//(1 << (11-gain)) * (-1 if value < 0 else 1)
            expected = max(-127, min(127, factor)) & 255
            timed = a2test.run(disk, a2test.bin_steps(binary, start=labels['setup'])+[
                *labels.poke('input', [(value >> shift) & 255 for shift in (0, 8, 16)]),
                labels.until('measure_start'), labels.until('measure_done'),
                labels.peek('vl_fcoef')], iie=iie)
            assert timed.data == bytes([expected]), (gain, value)
            entry['cycles'][str(value)] = timed.cycles[-1]-timed.cycles[-2]
        report[str(gain)] = entry
        print(f'Fixed K={gain}: {entry["code_bytes"]} code bytes, timings model checked.', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path,
                        help='directory containing saved verlet_con.asm and verlet.asm')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--bench', action='store_true')
    parser.add_argument('--only', choices=('generic', 'pair'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='verlet-constraint-shifts-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        original = args.reference or DEV / 'lib/physics'
        for name in ('verlet.asm', 'verlet_con.asm'):
            (include / name).write_bytes((original / name).read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        if args.only != 'pair':
            report['generic'] = generic(work, include, args.iie, args.bench)
        if args.only != 'generic':
            report['pair'] = shifts(work, include, args.iie, args.bench, kinds=('pair',))
        if args.bench:
            report['fixed'] = fixed_timings(work, include, args.iie)
            report['constraints'] = constraints(work, include, args.iie)
        report.update(metadata(original / 'verlet_con.asm', args.iie))
        report['points_source_sha256'] = identity(original / 'verlet.asm')['sha256']
        report['test_sha256'] = identity(__file__)['sha256']
        report['test_dependencies'] = [identity(DEV / 'tests' / name) for name in (
            'test_verlet_helpers.py', 'test_verlet_quarter_abs.py', 'test_verlet_ground_probes.py')]
        report['kernel_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
        del report['probe_config_sha256']
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
