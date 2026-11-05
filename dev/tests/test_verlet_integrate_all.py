#!/usr/bin/env python3
"""Integration pin guards: public models, scratch/register flags and caller modes.

Every pin-byte pair is checked with 8.8 and 16.8 y/left-wall configurations,
with direct-entry references present and absent. Count1/max51, no-pin,
direct-only, mixed and exported callers guard conditional assembly and ABI.
--bench additionally runs private CUTROPE/Catapult II+ frame budget tests.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from test_hgr import DEV, a2test
from test_verlet_contact_all import CONFIG as BASE_CONFIG
from test_verlet_ground_probes import identity, metadata
from verlet import Points, harness

ROOT = DEV.parent
CONFIG = BASE_CONFIG.replace('CODE: load=MAIN, type=ro;',
                             'CODE: load=MAIN, type=ro, align=$100;')


def pin_pairs(include, iie):
    report = {}
    for high, wall in ((False, False), (True, True)):
        for direct in (False, True):
            name = f'high{int(high)}_wall{int(wall)}_direct{int(direct)}'
            n = 2
            p = Points(n, y_high=high, pins=True)
            # Cross byte/page boundaries, hit both velocity clamps, and
            # stop a point at the optional 16-pixel left wall.
            p.x = [0x0f80, 0x10080] if wall else [0x00ff80, 0xff0080]
            p.ox = [p.x[0]+0x500, p.x[1]-0x345] if wall else [p.x[0]-0x180, p.x[1]+0x280]
            p.y = [0x00ff80, 0x010080] if high else [0x7f80, 0xff80]
            p.oy = [p.y[0]-0x123, p.y[1]+0x234]
            initial = p.soa_bytes()
            names = ('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu') if high else ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh')
            positions = [f'vl_{field}+{i}' for field in names for i in range(n)]
            fields = positions + ['vl_pin', 'vl_pin+1', 'vl_val', 'vl_val+1', 'vl_vx', 'vl_vx+1', 'vl_w0', 'vl_w1', 'vl_w2', 'returned_a', 'returned_x', 'returned_y', 'returned_flags']
            setup = ''.join((f' lda #{value}\n sta {field}\n' for field, value in zip(positions, initial)))
            setup += ''.join((f' lda #{value}\n sta {field}\n' for field, value in zip(fields[len(positions) + 2:len(positions) + 9], (90, 195, 61, 197, 227, 114, 169))))
            copy = ''.join((f' lda {field}\n sta records+{i*256},x\n' for i, field in enumerate(fields)))
            source = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=2
VL_PIN=1
VL_GRAVITY=$30
VL_VMAX_X=$100
VL_VMAX_Y=$200
''' + ('VL_Y_HIGH=1\n' if high else '') + ('VL_INTEGRATE_LEFTWALL=$1000\n' if wall else '') + '''.include "verlet.inc"
.zeropage
input: .res 2
saved_hw: .res 1
saved_flags: .res 1
returned_a: .res 1
returned_x: .res 1
returned_y: .res 1
returned_flags: .res 1
.code
start:
 sei
 cld
 lda #0
 sta input
 sta input+1
loop:
''' + setup + ''' lda input
 sta vl_pin
 lda input+1
 sta vl_pin+1
 lda input
 and #$41
 ora #$20
 pha
 plp
 lda input
 and #1
 beq allow_irq
 sei
 bne invoke
allow_irq: cli
invoke:
 tsx
 stx saved_hw
 lda #$a5
 ldx #$5a
 ldy #$c3
 jsr vl_integrate_all
 sta returned_a
 stx returned_x
 sty returned_y
 php
 pla
 sta returned_flags
 and #$0c
 sta saved_flags
 lda input
 and #1
 asl
 asl
 cmp saved_flags
 beq :+
 jmp fail
:tsx
 cpx saved_hw
 beq :+
 jmp fail
:ldx input
''' + copy + ''' inc input
 bne :+
 jmp page_done
:jmp loop
page_done: nop
resume:
 inc input+1
 beq done
 jmp loop
done: jmp done
fail: jmp fail
''' + ('''direct_probe: jsr vl_integrate
 rts
''' if direct else '') + '''.align 256
kernel_start:
.include "verlet.asm"
kernel_end:
.segment "SNAPS"
records: .res ''' + str(len(fields) * 256) + '''
.export done,page_done,resume,records,kernel_start,kernel_end
'''
            with tempfile.TemporaryDirectory(prefix='integrate-pin-') as directory:
                work = Path(directory)
                cfg = work / 'fixture.cfg'
                cfg.write_text(CONFIG)
                labels, binary = harness.build(work, source, includes=(include,), cfg=cfg)
                disk = a2test.build_disk(work, 'TEST', binary) if iie else None
                steps = a2test.bin_steps(binary)
                for _ in range(256):
                    steps += [labels.until('page_done'), labels.peek('records', len(fields) * 256), labels.until('resume')]
                steps += [labels.until('done')]
                result = a2test.run(disk, steps, iie=iie, timeout=180)
                digest = hashlib.sha256()
                for high_byte in range(256):
                    for low in range(256):
                        pins = [low, high_byte]
                        points = Points.from_soa(initial, 2, y_high=high)
                        points.pin = pins
                        points.integrate_all(48, 256, 512, 4096 if wall else None)
                        expected = points.soa_bytes() + bytes(pins)
                        actual = bytes((result.dumps[high_byte][low + i * 256] for i in range(len(fields))))
                        assert actual[:len(expected)] == expected, (name, low, high_byte)
                        assert actual[-3] == 255, ('returned X', name, low, high_byte)
                        digest.update(actual)
                report[name] = {'cases': 65536, 'state_and_register_sha256': digest.hexdigest(), 'kernel_bytes': labels['kernel_end'] - labels['kernel_start'], 'binary_bytes': binary.stat().st_size}
                print(name, '65536 full pin pairs / model / scratch / registers+flags / I/D / stack;', report[name]['kernel_bytes'], 'kernel bytes', flush=True)
    return report


def game_budgets(work, include):
    # Build private real games; existing disk tests also check model state,
    # cadence, counters, vblank and the no-floating-bus fallback. The frame
    # measurements use their supported II+ / a2run configuration.
    report = {}
    for name, game in (('cutrope', ROOT / 'cutrope'),
                       ('catapult', DEV / 'examples/catapult')):
        target = work / name
        target.mkdir()
        includes = [include, game / 'src']+[DEV / 'lib' / part
                                          for part in ('apple2', 'hgr', 'font', 'math', 'physics')]
        arguments = [str(arg) for path in includes for arg in ('-I', path)]
        obj, binary, labels = (target / (name+suffix) for suffix in ('.o', '.bin', '.lbl'))
        subprocess.run(['ca65', '-t', 'none', '-g', *arguments, '-o', str(obj),
                        str(game / 'src' / (name+'.s'))], check=True)
        subprocess.run(['ld65', '-C', str(DEV / 'cc65/apple2_hgr.cfg'), '-Ln', str(labels),
                        '-o', str(binary), str(obj)], check=True)
        disk = target / (name.upper()+'.dsk')
        subprocess.run([sys.executable, str(DEV / 'tools/dos33.py'), '--master',
                        str(DEV / 'tools/dos33_system.bin'), '--out', str(disk),
                        '--bas', f'HELLO={game}/src/hello.bas',
                        '--bin', f'{name.upper()}={binary}@0x6000'], check=True, capture_output=True)
        spec = importlib.util.spec_from_file_location('integrate_all_'+name,
                                                     game / 'tests' / ('test_'+name+'_disk.py'))
        test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test)
        test.DISK, test.LBL = disk, labels
        turns, original = [], test.frame_turns

        def frame_turns(*args, **kwargs):
            rows = original(*args, **kwargs)
            turns.append(dict(pre=args[1], count=args[2], work=[row['work'] for row in rows],
                              flips=[row['flip'] for row in rows]))
            return rows

        test.frame_turns = frame_turns
        measured = test.main()
        report[name] = dict(cpu='NMOS6502', binary_bytes=binary.stat().st_size,
                            binary_sha256=identity(binary)['sha256'], turns=turns,
                            work={phase: dict(cases=len(costs), median=statistics.median(costs),
                                              maximum=max(costs), cycles=costs)
                                  for phase, costs in measured.items()})
    return report


def bounds(include, iie):
    report = {}
    for count, high, pinned, mode, wall in ((1, False, True, 'all', False), (51, False, True, 'all', False), (51, True, True, 'all', True), (4, False, False, 'all', False), (4, False, True, 'direct', False), (4, False, True, 'mixed', False), (4, False, True, 'exported', False)):
        for mixed in (False, True):
            name = f'n{count}_high{int(high)}_pin{int(pinned)}_{mode}_pattern{int(mixed)}'
            p = Points(count, y_high=high, pins=pinned)
            p.x = [((8 if wall else 64) + i * 4) * 256 + 128 for i in range(count)]
            p.y = [(300 if high else 64) * 256 + i * 128 for i in range(count)]
            p.ox = [x - (1024 if i & 1 else -1024) for i, x in enumerate(p.x)]
            p.oy = [y - (-1024 if i & 1 else 1024) for i, y in enumerate(p.y)]
            initial = p.soa_bytes()
            names = ('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu') if high else ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh')
            fields = [f'vl_{a}+{i}' for a in names for i in range(count)]
            setup = ''.join((f' lda #{v}\n sta {f}\n' for f, v in zip(fields, initial)))
            if pinned:
                setup += ''.join((f' lda input_class\n eor #{(i*73&255) if mixed else 0}\n sta vl_pin+{i}\n' for i in range(count)))
            setup += ''.join((f' lda #{v}\n sta {f}\n' for f, v in zip(('vl_val', 'vl_val+1', 'vl_vx', 'vl_vx+1', 'vl_w0', 'vl_w1', 'vl_w2'), (90, 195, 61, 197, 227, 114, 169))))
            source = f'''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS={count}
VL_GRAVITY=$30
VL_VMAX_X=$100
VL_VMAX_Y=$200
''' + ('VL_PIN=1\n' if pinned else '') + ('VL_Y_HIGH=1\n' if high else '') + ('VL_INTEGRATE_LEFTWALL=$1000\n' if wall else '') + '''.include "verlet.inc"
.zeropage
input_class: .res 1
saved_hw: .res 1
returned_a: .res 1
returned_x: .res 1
returned_y: .res 1
returned_flags: .res 1
.code
start:
 sei
 cld
''' + setup + ''' tsx
 stx saved_hw
 lda #165
 ldx #0
 ldy #195
 jsr ''' + ('vl_integrate' if mode == 'direct' else 'vl_integrate_all') + '''
 sta returned_a
 stx returned_x
 sty returned_y
 php
 pla
 sta returned_flags
 and #$0c
 cmp #4
 beq :+
 jmp fail
:tsx
 cpx saved_hw
 beq :+
 jmp fail
:done: jmp done
fail: jmp fail
''' + ('''direct_probe: jsr vl_integrate
 rts
''' if mode == 'mixed' else '.export vl_integrate\n' if mode == 'exported' else '') + '''kernel_start:
.include "verlet.asm"
kernel_end:
.export start,done,vl_xf,kernel_start,kernel_end
.exportzp input_class,vl_val,vl_vx,vl_w0,vl_w1,vl_w2,returned_a,returned_x,returned_y,returned_flags
''' + ('.export vl_pin\n' if pinned else '')
            with tempfile.TemporaryDirectory(prefix='integrate-bounds-') as d:
                work = Path(d)
                cfg = work / 'fixture.cfg'
                cfg.write_text(CONFIG)
                labels, binary = harness.build(work, source, includes=(include,), cfg=cfg)
                disk = a2test.build_disk(work, 'TEST', binary) if iie else None
                steps = a2test.bin_steps(binary)
                for value in (0, 1, 128, 255):
                    steps += [labels.poke('input_class', value), f'go:{labels["start"]:04X}', labels.until('done'), labels.peek('vl_xf', len(initial))]
                    if pinned:
                        steps += [labels.peek('vl_pin', count)]
                    steps += [labels.peek('vl_val', 7), labels.peek('returned_a', 4)]
                result = a2test.run(disk, steps, iie=iie)
                size = len(initial) + (count if pinned else 0) + 11
                actuals = result.data
                digest = hashlib.sha256(actuals)
                for at, value in enumerate((0, 1, 128, 255)):
                    points = Points.from_soa(initial, count, y_high=high)
                    if pinned:
                        points.pin = [value ^ (i * 73 & 255 if mixed else 0) for i in range(count)]
                    if mode == 'direct':
                        points.integrate(0, 48, 256, 512, 4096 if wall else None)
                    else:
                        points.integrate_all(48, 256, 512, 4096 if wall else None)
                    expected = points.soa_bytes() + (bytes(points.pin) if pinned else b'')
                    actual = actuals[at * size:(at + 1) * size]
                    assert actual[:len(expected)] == expected, (name, value)
                    assert actual[-3] == (0 if mode == 'direct' else 255), (name, value, 'X')
                report[name] = {'cases': 4, 'state_and_register_sha256': digest.hexdigest(), 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), 'kernel_bytes': labels['kernel_end'] - labels['kernel_start']}
            print(name, 'model and register/stack bounds exact;', report[name]['kernel_bytes'], 'B', flush=True)
    return report



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='saved verlet.asm source')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--only', choices=('pins', 'bounds'))
    parser.add_argument('--bench', action='store_true', help='also run private II+ game budgets')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or DEV / 'lib/physics/verlet.asm'
    with tempfile.TemporaryDirectory(prefix='verlet-integrate-all-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        (include / 'verlet.asm').write_bytes(selected.read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        if args.only != 'bounds':
            report['pins'] = pin_pairs(include, args.iie)
        if args.only != 'pins':
            report['bounds'] = bounds(include, args.iie)
        if args.bench:
            report['games'] = game_budgets(work, include)
        report.update(metadata(selected, args.iie))
        report['test_sha256'] = identity(__file__)['sha256']
        report['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
        del report['probe_config_sha256']
        report['model_sha256'] = identity(DEV / 'tools/verlet/points.py')['sha256']
        report['test_dependencies'] = [identity(DEV / 'tests' / name) for name in (
            'test_verlet_contact_all.py', 'test_verlet_ground_probes.py')]
        if args.bench:
            report['budget_runner'] = identity(DEV / 'tools/a2run/a2run')
            report['budget_tests'] = [identity(path) for path in (
                ROOT / 'cutrope/tests/test_cutrope_disk.py',
                DEV / 'examples/catapult/tests/test_catapult_disk.py')]
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
