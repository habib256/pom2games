#!/usr/bin/env python3
"""Fixed-gain clamp and public links across the documented K=0..8.

Check the selected exact gain block over signed 17-bit words, an inclusive
superset of q2-l2 (-65535..64800), then compose it through public entries
with every FAST/SKIP/PIN/HEAVY/Y_HIGH combination. --expect-bug reproduces
the saved pre-fix source's K0..2 regression; it is never needed normally.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, a2test
from test_verlet_helpers import CONFIG, build
from test_verlet_ground_probes import metadata
from verlet import Points, constrain, harness


def gains(source_path, include, iie, expect_bug):
    # Exercise the actual bias/shift/clamp instructions. Full public calls
    # below independently check source selection and surrounding composition.
    source = source_path.read_text()
    start = source.index('        LDA     vl_w2\n        BPL     @fk')
    stop = source.index('\n.else\n        LDY     #3', start)
    block = source[start:stop]
    report = {}
    for gain in range(9):
        entry = dict(cases=0, mismatches=0, first=None)
        for negative in (False, True):
            text = f'''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
VL_NCON=1
VL_CON_FIXED_K={gain}
_VL_FKN=11-VL_CON_FIXED_K
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
 jsr gain
 cpx #$a5
 bne fail
 cpy #$5a
 bne fail
 cmp vl_fcoef
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
 lda vl_fcoef
 sta results,x
 inc input
 bne loop
page_done: nop
resume:
 inc input+1
 bne loop
done: jmp done
fail: jmp fail
gain:
''' + block + '''
 rts
.bss
results: .res 256
.export done,page_done,resume,results
'''
            with tempfile.TemporaryDirectory(prefix='fixed-gain-') as directory:
                work = Path(directory)
                labels, binary = build(work, text, include)
                disk = a2test.build_disk(work, 'TEST', binary) if iie else None
                steps = a2test.bin_steps(binary)
                for _ in range(256):
                    steps += [labels.until('page_done'), labels.peek('results', 256),
                              labels.until('resume')]
                steps.append(labels.until('done'))
                result = a2test.run(disk, steps, iie=iie, timeout=180)
                for high in range(256):
                    for low, actual in enumerate(result.dumps[high]):
                        value = high*256 + low - (65536 if negative else 0)
                        factor = abs(value) // (1 << (11-gain))
                        if value < 0:
                            factor = -factor
                        expected = max(-127, min(127, factor)) & 255
                        if actual != expected:
                            entry['mismatches'] += 1
                            if entry['first'] is None:
                                entry['first'] = dict(
                                    w=value, actual=actual if actual < 128 else actual-256,
                                    expected=expected if expected < 128 else expected-256)
                entry['cases'] += 65536
        if expect_bug:
            assert bool(entry['mismatches']) == (gain < 3), (gain, entry)
        else:
            assert entry['mismatches'] == 0, (gain, entry)
        report[str(gain)] = entry
        print(f'K={gain}: {entry["cases"]:,} exact-source gain cases, '
              f'{entry["mismatches"]:,} mismatches; A/X/Y, I/D and stack checked.', flush=True)
    return report


def link_rows(high, pin):
    # First row is the minimal regression: (0,32px), rest24px, w=7168.
    # Its factors for K0/1/2 are3/7/14; the former code incorrectly used127.
    probes = ((32*256, 0, 24), (0, 0, 24), (24*256, 0, 24), (64, 0, 24),
              (45*256, 45*256, 1), (-32*256, 0, 24), (0, -32*256, 24),
              (32*256, -32*256, 24), (24*256-1, 1, 24), (24*256+1, -1, 24))
    rows = []
    for index, (dx, dy, rest) in enumerate(probes):
        for pins in (((0, 0), (1, 0), (0, 1), (1, 1)) if pin else ((0, 0),)):
            points = Points(2, y_high=high, pins=pin)
            base_x = 100*256 if index else 0
            base_y = (300 if high else 100)*256 if index else 0
            points.x, points.y = [base_x, base_x+dx], [base_y, base_y+dy]
            points.ox, points.oy = list(points.x), list(points.y)
            if pin:
                points.pin = list(pins)
            rows.append((points.soa_bytes()+bytes(pins if pin else ()), rest))
    return rows


def links(include, iie, expect_bug):
    report = {}
    for high, pin, heavy, fast, skip in itertools.product((False, True), repeat=5):
        switches = (high, pin, heavy, fast, skip)
        name = '_'.join(option for option, enabled in zip(
            ('yhigh', 'pin', 'heavy', 'fast', 'skip'), switches) if enabled) or 'plain'
        rows = link_rows(high, pin)
        arrays = (('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu')
                  if high else ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh'))
        fields = [f'vl_{field}+{index}' for field in arrays for index in range(2)]
        if pin:
            fields += ['vl_pin', 'vl_pin+1']
        for gain in range(9):
            expected = []
            for state, rest in rows:
                points = Points.from_soa(state[:24 if high else 20], 2, y_high=high)
                if pin:
                    points.pin = list(state[-2:])
                constrain(points, 0, 1, (rest*4)**2, 0,
                          heavy=3 if heavy else 0, fixed_k=gain)
                expected.append(points.soa_bytes()+bytes(points.pin if pin else ()))
            expected = b''.join(expected)
            definitions = f'VL_NPOINTS=2\nVL_NCON=1\nVL_CON_FIXED_K={gain}\n'
            for option, enabled in (('VL_Y_HIGH', high), ('VL_PIN', pin),
                                    ('VL_CON_FAST', fast), ('VL_CON_SKIP_ZERO', skip)):
                if enabled:
                    definitions += option+'=1\n'
            if heavy:
                definitions += 'VL_CON_HEAVY_POINT=1\nVL_CON_HEAVY_SHIFT=3\n'
            prelude = 'MUL_TABLES=$0800\n.include "math.inc"\n'+definitions+'''.include "verlet.inc"
.bss
vl_con_l2l: .res 1
vl_con_l2h: .res 1
.rodata
vl_con_a: .byte 0
vl_con_b: .byte 1
'''
            epilogue = '''tick:
 cld
 lda #0
 sta vl_cur
 jmp vl_constrain
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''
            script = [(1, list(state)+[(rest*4)**2 & 255, (rest*4)**2 >> 8], 1)
                      for state, rest in rows]
            text = harness.source(prelude, epilogue, fields+['vl_con_l2l', 'vl_con_l2h'],
                                  [('vl_xf', len(fields))], script,
                                  init='mul_init', snap_seg='LOWBSS')
            with tempfile.TemporaryDirectory(prefix='gain-link-') as directory:
                work = Path(directory)
                labels, binary = harness.build(work, text, includes=(include,))
                disk = a2test.build_disk(work, 'TEST', binary) if iie else None
                result = a2test.run(disk, a2test.bin_steps(binary)+[
                    labels.until('hs_done'), labels.peek('hs_snaps', len(expected))], iie=iie)
                width = len(fields)
                mismatches = sum(result.data[index:index+width] != expected[index:index+width]
                                 for index in range(0, len(expected), width))
                if not expect_bug or gain >= 3:
                    assert mismatches == 0, (name, gain, mismatches)
                else:
                    assert mismatches > 0, (name, gain, 'baseline regression absent')
                report[f'{name}_{gain}'] = dict(
                    cases=len(rows), mismatches=mismatches,
                    result_sha256=hashlib.sha256(result.data).hexdigest(),
                    binary_bytes=binary.stat().st_size,
                    binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        print(f'{name}: all K=0..8 public links checked against the model.', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='saved verlet_con.asm source')
    parser.add_argument('--expect-bug', action='store_true', help='require the old K0..2 failure')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--only', choices=('gains', 'links'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or DEV / 'lib/physics/verlet_con.asm'
    with tempfile.TemporaryDirectory(prefix='verlet-fixed-gain-') as directory:
        include = Path(directory)
        (include / 'verlet_con.asm').write_bytes(selected.read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502',
                      reference=bool(args.reference), expected_baseline_bug=args.expect_bug)
        if args.only != 'links':
            report['gains'] = gains(selected, include, args.iie, args.expect_bug)
        if args.only != 'gains':
            report['links'] = links(include, args.iie, args.expect_bug)
        report.update(metadata(selected, args.iie))
        report['test_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report['kernel_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
        del report['probe_config_sha256']
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
