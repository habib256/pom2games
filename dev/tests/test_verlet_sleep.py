#!/usr/bin/env python3
"""Circle sleep: independent velocity bounds, public states, guards and costs.

All 65,536 signed velocities are checked at threshold byte boundaries and
Catapult's threshold, with both IRQ states, preserved X/Y and hardware SP.
Public cases cover both Y widths, all pin/counter bytes and signed velocity
boundaries. w0/w1 and arithmetic NZV are scratch; public C and I/D are checked.
--bench also builds private CUTROPE/Catapult disks and runs their budget tests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, a2test
from test_math_init import CONFIG
from test_verlet_ground_probes import identity, metadata
from test_verlet_integrate_all import game_budgets
from verlet import Points, harness

ROOT = DEV.parent
THRESHOLDS = (1, 2, 3, 0x21, 0x3F, 0x40, 0x7F, 0x80, 0x81, 0xFE, 0xFF,
              0x100, 0x101, 0x17F, 0x180, 0x1FE, 0x1FF, 0x200, 0x201, 0x1234,
              0x3FFF, 0x4000, 0x4001, 0x7F00, 0x7FFE, 0x7FFF)


def helper_text(selected):
    # Compile the actual private helper, including the selected source's
    # comparison instructions and immediate threshold operands.
    return 'slow:' + selected.read_text().split('@slow:', 1)[1].split('\n.endif', 1)[0]


def helper_sweeps(selected, iie):
    report = {}
    for threshold in THRESHOLDS:
        source = f'''VL_CIRC_SLEEP={threshold}
.zeropage
vl_w0: .res 1
vl_w1: .res 1
input: .res 2
saved_hw: .res 1
.code
 cld
 lda #0
 sta input
 sta input+1
loop:
 tsx
 stx saved_hw
 lda input
 and #1
 asl
 asl
 ora #$71
 pha
 plp
 ldx input
 ldy #$A5
 lda input
 sta vl_w0
 lda input+1
 jsr slow
 php
 pla
 and #$0D
 sta results,x
 tya
 sta results+256,x
 tsx
 txa
 sec
 sbc saved_hw
 ldx input
 sta results+512,x
 inc input
 bne loop
page_done: nop
resume:
 inc input+1
 bne loop
done: jmp done
 .align 256
kernel_start:
''' + helper_text(selected) + '''
kernel_end:
.bss
results: .res 768
.export page_done,resume,done,results,kernel_start,kernel_end
'''
        with tempfile.TemporaryDirectory(prefix='sleep-helper-') as directory:
            work = Path(directory)
            cfg = work / 'fixture.cfg'
            cfg.write_text(CONFIG)
            labels, binary = harness.build(work, source, cfg=cfg)
            disk = a2test.build_disk(work, 'TEST', binary) if iie else None
            steps = a2test.bin_steps(binary)
            for _ in range(256):
                steps += [labels.until('page_done'), labels.peek('results', 768),
                          labels.until('resume')]
            steps.append(labels.until('done'))
            result = a2test.run(disk, steps, iie=iie)
            for high in range(256):
                expected = bytes(int(abs(high*256+low-(65536 if high&128 else 0)) <= threshold)
                                 | ((low&1)<<2) for low in range(256))
                expected += bytes([0xA5])*256 + bytes(256)
                assert result.dumps[high] == expected, (threshold, high)
            report[str(threshold)] = dict(cases=65536,
                helper_bytes=labels['kernel_end']-labels['kernel_start'],
                snapshot_sha256=hashlib.sha256(result.data).hexdigest())
    print(f'{len(THRESHOLDS)} thresholds × 65,536 velocities: C/X/Y/I/D/SP exact.', flush=True)
    return report


def helper_costs(selected, iie):
    values = (0, 1, 32, 33, 34, 32767, 32768, 65502, 65503, 65504, 65535)
    source = 'VL_CIRC_SLEEP=$21\n.zeropage\nvl_w0: .res 1\nvl_w1: .res 1\n.code\n cld\n'
    for index, value in enumerate(values):
        source += (f' lda #{value&255}\n sta vl_w0\n lda #{value>>8}\n'
                   f'start{index}: jsr slow\nend{index}: nop\n'
                   f'.export start{index},end{index}\n')
    source += ('done: jmp done\n.align 256\nkernel_start:\n' + helper_text(selected) +
               '\nkernel_end:\n.export done,kernel_start,kernel_end\n')
    with tempfile.TemporaryDirectory(prefix='sleep-costs-') as directory:
        work = Path(directory)
        cfg = work / 'fixture.cfg'
        cfg.write_text(CONFIG)
        labels, binary = harness.build(work, source, cfg=cfg)
        steps = a2test.bin_steps(binary)
        for index in range(len(values)):
            steps += [labels.until(f'start{index}'), labels.until(f'end{index}')]
        steps.append(labels.until('done'))
        disk = a2test.build_disk(work, 'TEST', binary) if iie else None
        result = a2test.run(disk, steps, iie=iie)
        return dict(helper_bytes=labels['kernel_end']-labels['kernel_start'],
                    scope='private helper including JSR/RTS; page-contained branches',
                    cycles={str(value): result.cycles[2*index+1]-result.cycles[2*index]
                            for index, value in enumerate(values)})


def threshold_boundaries(selected, iie):
    # The fixture varies only the immediate operands, equivalent to assembling
    # the same helper at every supported threshold. Production code is never
    # patched. Its final bytes must equal a normal constant-$7FFF assembly.
    helper = helper_text(selected).replace('@negative', 'slow_negative')
    operands = {'#<VL_CIRC_SLEEP': 'patch_pos_lo', '#>VL_CIRC_SLEEP': 'patch_pos_hi',
                '#<(-VL_CIRC_SLEEP)': 'patch_neg_lo', '#>(-VL_CIRC_SLEEP)': 'patch_neg_hi'}
    patched, found = [], set()
    for line in helper.splitlines():
        for operand, label in operands.items():
            if operand in line:
                assert label not in found, label
                found.add(label)
                patched.append(f'{label} = *+1')
        patched.append(line)
    assert found in ({'patch_pos_lo', 'patch_pos_hi'}, set(operands.values()))
    source = '''.macpack longbranch
VL_CIRC_SLEEP=1
.zeropage
vl_w0: .res 1
vl_w1: .res 1
threshold: .res 2
negative: .res 2
saved_hw: .res 1
.code
 cld
 lda #0
 sta threshold+1
 ldx #0
clear:
 .repeat 11,plane
 sta results+plane*256,x
 .endrepeat
 inx
 bne clear
 lda #1
 sta threshold
loop:
 tsx
 stx saved_hw
 lda threshold
 and #1
 asl
 asl
 ora #$71
 pha
 plp
 ldx threshold
 ldy #$A5
 lda threshold
 sta patch_pos_lo
 lda threshold+1
 sta patch_pos_hi
 sec
 lda #0
 sbc threshold
 sta negative
''' + (' sta patch_neg_lo\n' if 'patch_neg_lo' in found else '') + ''' lda #0
 sbc threshold+1
 sta negative+1
''' + (' sta patch_neg_hi\n' if 'patch_neg_hi' in found else '')
    setups = [' lda #0\n sta vl_w0\n lda #0\n']
    for name, delta in (('threshold', -1), ('threshold', 0), ('threshold', 1),
                        ('negative', -1), ('negative', 0), ('negative', 1)):
        setup = f' lda {name}\n'
        if delta:
            setup = (' sec\n' if delta < 0 else ' clc\n') + setup
            setup += ' sbc #1\n' if delta < 0 else ' adc #1\n'
        setup += f' sta vl_w0\n lda {name}+1\n'
        if delta:
            setup += ' sbc #0\n' if delta < 0 else ' adc #0\n'
        setups.append(setup)
    setups += [' lda #$FF\n sta vl_w0\n lda #$7F\n',
               ' lda #0\n sta vl_w0\n lda #$80\n']
    for plane, setup in enumerate(setups):
        source += setup + f' jsr slow\n php\n pla\n and #$0D\n sta results+{plane*256},x\n'
    source += ''' tya
 sta results+9*256,x
 tsx
 txa
 sec
 sbc saved_hw
 ldx threshold
 sta results+10*256,x
 inc threshold
 jne loop
page_done: nop
resume:
 inc threshold+1
 lda threshold+1
 cmp #$80
 beq done
 jmp loop
done: jmp done
.align 256
kernel_start:
''' + '\n'.join(patched) + '''
kernel_end:
.bss
results: .res 11*256
.export page_done,resume,done,results,kernel_start,kernel_end
'''
    with tempfile.TemporaryDirectory(prefix='sleep-thresholds-') as directory:
        work = Path(directory)
        cfg = work / 'fixture.cfg'
        cfg.write_text(CONFIG)
        labels, binary = harness.build(work, source, cfg=cfg)
        disk = a2test.build_disk(work, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)
        for _ in range(128):
            steps += [labels.until('page_done'), labels.peek('results', 11*256),
                      labels.until('resume')]
        steps += [labels.until('done'), labels.peek('kernel_start',
                  labels['kernel_end']-labels['kernel_start'])]
        result = a2test.run(disk, steps, iie=iie)
        for high in range(128):
            expected = bytearray(11*256)
            for low in range(256):
                threshold = high*256+low
                if not threshold:
                    continue
                values = (0, threshold-1, threshold, threshold+1, -threshold-1,
                          -threshold, -threshold+1, 32767, -32768)
                for plane, value in enumerate(values):
                    bits = value&65535
                    signed = bits-65536 if bits&32768 else bits
                    expected[plane*256+low] = int(abs(signed) <= threshold) | ((low&1)<<2)
                expected[9*256+low] = 0xA5
            assert result.dumps[high] == expected, ('threshold boundaries', high)
        original = '''VL_CIRC_SLEEP=$7FFF
.zeropage
vl_w0: .res 1
vl_w1: .res 1
.code
''' + helper_text(selected)
        _, constant = harness.build(work, original, cfg=cfg)
        assert result.dumps[-1] == constant.read_bytes(), 'patched constant differs from normal assembly'
    print('All 32,767 supported thresholds: nine velocity boundaries and guards exact.', flush=True)
    return dict(thresholds=32767, cases=32767*9,
                snapshot_sha256=hashlib.sha256(b''.join(result.dumps[:-1])).hexdigest())


def public_states(include, iie):
    report = {}
    for high in (False, True):
        names = ('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu') if high else (
            'xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh')
        positions = [f'vl_{field}+{point}' for field in names for point in range(2)]
        guards = ['vl_val', 'vl_val+1', 'vl_vx', 'vl_vx+1', 'vl_w2', 'vl_chits',
                  'vl_rad', 'vl_rad+1']
        guard_values = [0xA6, 0xC3, 0x5D, 0x72, 0xB9, 0xE7, 0x55, 0xA1]
        for threshold in (1, 0x21, 0x80, 0x100, 0x7FFF):
            ticks = 19
            velocities = [(v, 0) for v in (-32768, -threshold-1, -threshold,
                          -threshold+1, 0, threshold-1, threshold, threshold+1, 32767)]
            velocities += [(0, v) for v in (-32768, -threshold-1, -threshold,
                           -threshold+1, threshold-1, threshold, threshold+1, 32767)]
            cases = [(point, pin, pin, *velocities[pin % len(velocities)])
                     for point in range(2) for pin in range(256)]
            cases += [(point, 0, counter, *velocities[counter % len(velocities)])
                      for point in range(2) for counter in range(256)]
            cases += [(point, 0, counter, vx, vy) for point in range(2)
                      for counter in (0, ticks-1, ticks, 254, 255) for vx, vy in velocities]
            snapshots = []
            for first in range(0, len(cases), 64):
                rows, expected = [], []
                for index, (point, pin, counter, vx, vy) in enumerate(cases[first:first+64]):
                    p = Points(2, y_high=high, pins=True)
                    p.x = [0x00FF80, 0xFF0101]
                    p.y = [0xFF7F80, 0x010080] if high else [0x7F80, 0xFF80]
                    p.ox = [p.x[0]-0x123, p.x[1]+0x80]
                    p.oy = [p.y[0]+0x80, p.y[1]-0x123]
                    p.ox[point] = p.x[point]-vx
                    p.oy[point] = p.y[point]-vy
                    p.pin = [0x42, 0x42]
                    p.pin[point] = pin
                    still = [0xA7, 0xA7]
                    still[point] = counter
                    flag = 0x71 | ((index&1)<<2)
                    values = list(p.soa_bytes()) + p.pin + still + guard_values + [point, flag]
                    rows.append((1, values, 1))
                    # Independent byte-counter model; 255 increments to zero.
                    # The general contact model uses unbounded Python counters.
                    slept = False
                    if not pin:
                        if abs(vx) <= threshold and abs(vy) <= threshold:
                            still[point] = (counter+1)&255
                            if still[point] >= ticks:
                                still[point] = 0
                                p.pin[point] = 0x80
                                p.ox[point], p.oy[point] = p.x[point], p.y[point]
                                slept = True
                        else:
                            still[point] = 0
                    expected.append(p.soa_bytes() + bytes(p.pin+still+guard_values+
                                    [int(slept)|(flag&12), point, 0x5A, 0]))
                prelude = f'''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=2
VL_PIN=1
VL_CIRC=2
VL_CIRC_SLEEP={threshold}
VL_CIRC_SLEEP_TICKS={ticks}
''' + ('VL_Y_HIGH=1\n' if high else '') + '''.include "verlet.inc"
.zeropage
point_index: .res 1
incoming_flags: .res 1
saved_hw: .res 1
returned_flags: .res 1
returned_x: .res 1
returned_y: .res 1
stack_delta: .res 1
.code
'''
                epilogue = '''tick:
 tsx
 stx saved_hw
 ldx point_index
 ldy #$5A
 lda incoming_flags
 pha
 plp
 jsr vl_circ_sleep
 stx returned_x
 sty returned_y
 php
 pla
 and #$0D
 sta returned_flags
 tsx
 txa
 sec
 sbc saved_hw
 sta stack_delta
 rts
.include "verlet_circ.asm"
'''
                fields = positions + ['vl_pin', 'vl_pin+1', 'vl_still', 'vl_still+1'] + guards
                output = fields + ['returned_flags', 'returned_x', 'returned_y', 'stack_delta']
                source = '.macpack longbranch\n' + harness.source(
                    prelude, epilogue, inputs=fields+['point_index', 'incoming_flags'],
                    snaps=[(field, 1) for field in output], rows=rows)
                source = source.replace('BEQ     hs_next', 'jeq     hs_next')
                with tempfile.TemporaryDirectory(prefix='sleep-public-') as directory:
                    work = Path(directory)
                    labels, binary = harness.build(work, source, includes=(include,))
                    disk = a2test.build_disk(work, 'TEST', binary) if iie else None
                    result = a2test.run(disk, a2test.bin_steps(binary) + [
                        labels.until('hs_done', 3000), labels.peek('hs_snaps', len(output)*len(rows))], iie=iie)
                    assert result.data == b''.join(expected), (high, threshold, first)
                    snapshots.append(result.data)
            report[f'high{int(high)}_threshold{threshold}'] = dict(cases=len(cases),
                snapshot_sha256=hashlib.sha256(b''.join(snapshots)).hexdigest())
            print(f'Public high={int(high)}, threshold={threshold}: {len(cases)} state/guard cases.', flush=True)
    return report


def budget_sources():
    folders = (ROOT / 'cutrope/src', DEV / 'examples/catapult/src',
               *(DEV / 'lib' / part for part in ('apple2', 'hgr', 'font', 'math', 'physics')))
    paths = [path for folder in folders for path in folder.rglob('*')
             if path.suffix in ('.s', '.asm', '.inc')]
    paths.append(DEV / 'cc65/apple2_hgr.cfg')
    return [dict(path=str(path.relative_to(ROOT)), **identity(path)) for path in sorted(paths)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='saved verlet_circ.asm source')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--bench', action='store_true', help='also run private real-game budgets')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or DEV / 'lib/physics/verlet_circ.asm'
    with tempfile.TemporaryDirectory(prefix='verlet-sleep-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        (include / 'verlet_circ.asm').write_bytes(selected.read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        report['velocities'] = helper_sweeps(selected, args.iie)
        report['threshold_boundaries'] = threshold_boundaries(selected, args.iie)
        report['public'] = public_states(include, args.iie)
        report['costs'] = helper_costs(selected, args.iie)
        if args.bench:
            sources = budget_sources()
            report['games'] = game_budgets(work, include)
            assert sources == budget_sources(), 'game sources changed during private builds'
            report['budget_sources'] = sources
        report.update(metadata(selected, args.iie))
        report['test_sha256'] = identity(__file__)['sha256']
        report['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
        del report['probe_config_sha256']
        report['test_dependencies'] = [identity(DEV / 'tests' / name) for name in (
            'test_math_init.py', 'test_verlet_ground_probes.py', 'test_verlet_integrate_all.py')]
        report['model_sources'] = [identity(DEV / 'tools/verlet' / name)
                                   for name in ('harness.py', 'points.py')]
        if args.bench:
            report['budget_flags'] = 'ca65 -t none -g; ld65 dev/cc65/apple2_hgr.cfg'
            report['budget_runner'] = identity(DEV / 'tools/a2run/a2run')
            report['budget_environment'] = metadata(selected, False)['environment']
            report['budget_tests'] = [identity(path) for path in (
                ROOT / 'cutrope/tests/test_cutrope_disk.py',
                DEV / 'examples/catapult/tests/test_catapult_disk.py')]
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
