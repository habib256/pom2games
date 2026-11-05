#!/usr/bin/env python3
"""Contact-all pin bytes, radii, ordered wake-ups and real Catapult budgets."""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from test_hgr import DEV, a2test
from test_verlet_ground_probes import identity, metadata
from verlet import Points, contact, harness

ROOT = DEV.parent
CONFIG = '''MEMORY {
 ZP: start=$0050, size=$00b0, type=rw, define=yes;
 LOWRAM: start=$1000, size=$1000, type=rw, define=yes;
 SNAP: start=$2000, size=$4000, type=rw;
 MAIN: start=$6000, size=$3600, type=rw, define=yes, file=%O;
}
SEGMENTS {
 ZEROPAGE: load=ZP, type=zp;
 LOWBSS: load=LOWRAM, type=bss, optional=yes, define=yes;
 SNAPS: load=SNAP, type=bss, optional=yes;
 CODE: load=MAIN, type=ro;
 RODATA: load=MAIN, type=ro, optional=yes;
 DATA: load=MAIN, type=rw, optional=yes;
 BSS: load=MAIN, type=bss, optional=yes, define=yes;
}
'''


def arrays(high):
    return (('xf', 'xl', 'xh', 'yf', 'yh', 'yu', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh', 'oyu')
            if high else ('xf', 'xl', 'xh', 'yf', 'yh', 'oxf', 'oxl', 'oxh', 'oyf', 'oyh'))


def byte_domains(work, include, config, iie):
    fields = [f'vl_{name}+{index}' for name in arrays(False) for index in range(2)]
    fields += ['vl_pin', 'vl_pin+1', 'vl_rad', 'vl_rad+1', 'vl_still', 'vl_still+1',
               'vl_chits', 'vl_ca', 'vl_cb', 'returned_x']
    # Positions (64,68)px, velocity (+1,-1)px; y=64px and no y speed.
    positions = bytes((0, 0, 64, 68, 0, 0, 0, 0, 64, 64,
                       0, 0, 63, 69, 0, 0, 0, 0, 64, 64))
    variants = [('pins', pair) for pair in ((40, 40), (0, 40), (40, 0), (0, 0),
                                          (63, 64), (127, 0))]
    variants += [('radii', pair) for pair in ((0, 0), (0, 128), (128, 0), (1, 128))]
    report = {}
    for mode, constants in variants:
        name = f'{mode}_{constants[0]}_{constants[1]}'
        setup = ''.join(f' lda #{value}\n sta {field}\n'
                        for field, value in zip(fields, positions))
        if mode == 'pins':
            setup += ' lda input\n sta vl_pin\n lda input+1\n sta vl_pin+1\n'
            setup += f' lda #{constants[0]}\n sta vl_rad\n lda #{constants[1]}\n sta vl_rad+1\n'
        else:
            setup += f' lda #{constants[0]}\n sta vl_pin\n lda #{constants[1]}\n sta vl_pin+1\n'
            setup += ' lda input\n sta vl_rad\n lda input+1\n sta vl_rad+1\n'
            # The documented physical domain is radius sum <=127. Skip the
            # other input words; all 8,256 supported pairs are checked.
            setup += ' clc\n lda input\n adc input+1\n bcs record\n cmp #128\n bcs record\n'
        setup += ' lda #3\n sta vl_still\n lda #15\n sta vl_still+1\n'
        copy = ''.join(f' lda {field}\n sta records+{plane*256},x\n'
                       for plane, field in enumerate(fields))
        text = '''MUL_TABLES=$0800
MUL_ACC=1
.include "math.inc"
VL_NPOINTS=2
VL_CIRC=2
VL_CIRC_Q=5
VL_PIN=1
VL_CIRC_SLEEP=$40
VL_CIRC_BOUNCE=96
VL_CIRC_VMIN=$30
.include "verlet.inc"
.zeropage
input: .res 2
saved_hw: .res 1
saved_flags: .res 1
returned_x: .res 1
.code
start:
 sei
 cld
 jsr mul_init
 jsr sqrt_init
 lda #0
 sta input
 sta input+1
loop:
''' + setup + ''' lda #255
 sta vl_chits
 lda #$a5
 sta vl_ca
 lda #$5a
 sta vl_cb
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
 jsr vl_contact_all
 stx returned_x
 php
 pla
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
 beq record
 jmp fail
record:
 ldx input
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
.include "verlet_circ.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
.segment "SNAPS"
records: .res ''' + str(len(fields)*256) + '''
.export done,page_done,resume,records
'''
        target = work / name
        target.mkdir()
        labels, binary = harness.build(target, text, includes=(include,), cfg=config)
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)
        for _ in range(256):
            steps += [labels.until('page_done'), labels.peek('records', len(fields)*256),
                      labels.until('resume')]
        steps.append(labels.until('done'))
        result = a2test.run(disk, steps, iie=iie, timeout=180)
        digest, cases = hashlib.sha256(), 0
        for high in range(256):
            for low in range(256):
                pins = [low, high] if mode == 'pins' else list(constants)
                radii = list(constants) if mode == 'pins' else [low, high]
                if sum(radii) > 127:
                    continue
                points = Points.from_soa(positions, 2)
                points.pin = list(pins)
                hits = contact.contact_all(points, radii, Q=5, bounce=96, vmin=0x30, sleep=0x40)
                expected = (points.soa_bytes()+bytes(points.pin)+bytes(radii)+bytes((3, 15)) +
                            bytes(((255+hits) & 255, 0, 1 if radii[0] else 0x5a, 1)))
                actual = bytes(result.dumps[high][low+plane*256] for plane in range(len(fields)))
                assert actual == expected, (name, low, high, actual.hex(), expected.hex())
                digest.update(actual)
                cases += 1
        report[name] = dict(cases=cases, state_sha256=digest.hexdigest(),
                            binary_bytes=binary.stat().st_size)
        print(f'{name}: {cases:,} public states, chits/ca/cb, X/I/D and stack exact.', flush=True)
    return report


def ordered_rows(q, high, heavy):
    rows, wakes, postwake = [], 0, 0
    for pins in itertools.product((0, 1, 128, 255), repeat=4):
        for mask in range(16):
            radii = [40 if mask & (1 << index) else 0 for index in range(4)]
            weights, still = [0, 1, 0, 1], [3, 7, 15, 255]
            points = Points(4, y_high=high)
            points.x = [value*256 for value in (64, 68, 60, 64)]
            points.y = [(300 if high else 64)*256+offset for offset in (0, 0, 0, 4*256)]
            points.ox = [value-(speed if not pins[index] else 0)
                         for index, (value, speed) in enumerate(zip(points.x, (0, -256, 0, 0)))]
            points.oy = [value-(-256 if index == 3 and not pins[index] else 0)
                         for index, value in enumerate(points.y)]
            points.pin = list(pins)
            fixed = bytes(radii)+(bytes(weights) if heavy else b'')+bytes(still)
            initial = points.soa_bytes()+bytes(pins)+fixed+bytes((253, 165, 90))
            hits = 0
            # Apply the maintained pair model in the documented ascending
            # order, and count later pairs whose outer point has just woken.
            for a in range(3):
                if not radii[a]:
                    continue
                for b in range(a+1, 4):
                    if not radii[b]:
                        continue
                    before = list(points.pin)
                    if pins[a] and not points.pin[a] and points.pin[b]:
                        postwake += 1
                    hits += contact.pair(points, a, b, radii[a]+radii[b], Q=q, bounce=96,
                                         vmin=0x30, heavy=heavy, hv=weights, sleep=0x40)
                    wakes += sum(old == 128 and not new for old, new in zip(before, points.pin))
            expected = (points.soa_bytes()+bytes(points.pin)+fixed +
                        bytes(((253+hits) & 255, 2, 3 if any(radii[:3]) else 90, 3)))
            rows.append((initial+bytes(((mask ^ pins[0]) & 1,)), expected))
    assert wakes and postwake, (q, wakes, postwake)
    return rows, wakes, postwake


def ordered_clusters(work, include, config, iie):
    report = {}
    for q, high, heavy, fast in ((5, False, 2, False), (4, True, 0, True), (6, True, 2, True)):
        name = f'q{q}_high{int(high)}_heavy{heavy}_fast{int(fast)}'
        fields = [f'vl_{field}+{index}' for field in arrays(high) for index in range(4)]
        fields += [f'vl_pin+{index}' for index in range(4)]
        fields += [f'vl_rad+{index}' for index in range(4)]
        snaps = [('vl_xf', len(arrays(high))*4), ('vl_pin', 4), ('vl_rad', 4)]
        if heavy:
            fields += [f'vl_cheavy+{index}' for index in range(4)]
            snaps.append(('vl_cheavy', 4))
        fields += [f'vl_still+{index}' for index in range(4)]+['vl_chits', 'vl_ca', 'vl_cb']
        snaps += [('vl_still', 4), ('vl_chits', 1), ('vl_ca', 1), ('vl_cb', 1), ('returned_x', 1)]
        rows, wakes, postwake = ordered_rows(q, high, heavy)
        definitions = f'''MUL_TABLES=$0800
MUL_ACC=1
.include "math.inc"
VL_NPOINTS=4
VL_CIRC=4
VL_CIRC_Q={q}
VL_PIN=1
VL_CIRC_SLEEP=$40
VL_CIRC_BOUNCE=96
VL_CIRC_VMIN=$30
'''
        if high:
            definitions += 'VL_Y_HIGH=1\n'
        if heavy:
            definitions += f'VL_CIRC_HEAVY={heavy}\n'
        if fast:
            definitions += 'VL_CON_FAST=1\n'
        prelude = definitions + '''.include "verlet.inc"
.zeropage
saved_hw: .res 1
saved_flags: .res 1
returned_x: .res 1
irq_state: .res 1
'''
        epilogue = '''init:
 cld
 jsr mul_init
 jmp sqrt_init
tick:
 lda irq_state
 beq allow_irq
 sei
 bne invoke
allow_irq: cli
invoke:
 tsx
 stx saved_hw
 ldx #$a5
 jsr vl_contact_all
 stx returned_x
 php
 pla
 and #$0c
 sta saved_flags
 lda irq_state
 asl
 asl
 cmp saved_flags
 beq :+
 jmp fail
:tsx
 cpx saved_hw
 beq :+
 jmp fail
:rts
fail: jmp fail
.include "verlet_circ.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
'''
        digest = hashlib.sha256()
        for offset in range(0, len(rows), 80):
            part = rows[offset:offset+80]
            text = harness.source(prelude, epilogue, fields+['irq_state'], snaps,
                                  [(1, list(state), 1) for state, _ in part],
                                  init='init', snap_seg='SNAPS')
            text = text.replace('        BEQ     hs_next', '        BNE     :+\n        JMP     hs_next\n:')
            target = work / f'{name}_{offset}'
            target.mkdir()
            labels, binary = harness.build(target, text, includes=(include,), cfg=config)
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            expected = b''.join(state for _, state in part)
            result = a2test.run(disk, a2test.bin_steps(binary)+[
                labels.until('hs_done'), labels.peek('hs_snaps', len(expected))], iie=iie)
            assert result.data == expected, (name, offset)
            digest.update(result.data)
        report[name] = dict(cases=len(rows), wakes=wakes, postwake_pairs=postwake,
                            state_sha256=digest.hexdigest())
        print(f'{name}: {len(rows):,} ordered states, {wakes} wakes, '
              f'{postwake} later pairs after an outer point woke.', flush=True)
    return report


def count_bounds(work, include, config, iie):
    report = {}
    # Contact helpers address old points with X+5*N (or X+6*N for 24-bit
    # y), so their existing assembly assertions limit N to42 /36.
    for count, pin, high in ((1, True, False), (4, False, False),
                             (42, True, False), (36, True, True)):
        name = f'n{count}_pin{int(pin)}_high{int(high)}'
        definitions = f'MUL_TABLES=$0800\nMUL_ACC=1\n.include "math.inc"\nVL_NPOINTS={count}\nVL_CIRC={count}\n'
        if pin:
            definitions += 'VL_PIN=1\n'
        if high:
            definitions += 'VL_Y_HIGH=1\n'
        zero = ''.join(f' sta vl_{field},x\n' for field in arrays(high))
        setup = ' lda #80\n sta vl_yh,x\n sta vl_oyh,x\n'
        if high:
            setup = ' lda #44\n sta vl_yh,x\n sta vl_oyh,x\n lda #1\n sta vl_yu,x\n sta vl_oyu,x\n'
        if pin:
            setup += ' lda #128\n sta vl_pin,x\n'
        text = definitions+'''.include "verlet.inc"
.bss
returned_x: .res 1
.code
start:
 sei
 cld
 ldx #'''+str(count-1)+'''
init:
 lda #0
'''+zero+''' txa
 asl
 asl
 clc
 adc #20
 sta vl_xl,x
 sta vl_oxl,x
 lda #1
 sta vl_rad,x
'''+setup+''' dex
 bpl init
 lda #253
 sta vl_chits
 lda #165
 sta vl_ca
 lda #90
 sta vl_cb
 ldx #165
 jsr vl_contact_all
 stx returned_x
done: jmp done
.include "verlet_circ.asm"
.include "verlet_con.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
.export done,returned_x
'''
        target = work / name
        target.mkdir()
        labels, binary = harness.build(target, text, includes=(include,), cfg=config)
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)+[labels.until('done'),
                labels.peek('vl_xf', count*len(arrays(high)))]
        if pin:
            steps.append(labels.peek('vl_pin', count))
        steps += [labels.peek('vl_rad', count), labels.peek('vl_chits'),
                  labels.peek('vl_ca'), labels.peek('vl_cb'), labels.peek('returned_x')]
        result = a2test.run(disk, steps, iie=iie)
        points = Points(count, y_high=high, pins=pin)
        points.x = [(20+4*index)*256 for index in range(count)]
        points.y = [(300 if high else 80)*256]*count
        points.ox, points.oy = list(points.x), list(points.y)
        if pin:
            points.pin = [128]*count
        hits = contact.contact_all(points, [1]*count, Q=5)
        assert not hits
        expected = (points.soa_bytes()+(bytes(points.pin) if pin else b'') + bytes([1]*count) +
                    bytes((253, count-2 if count > 1 else 165,
                           count-1 if count > 1 else 90, count-1 if count > 1 else 165)))
        assert result.data == expected, name
        report[name] = dict(binary_bytes=binary.stat().st_size,
                            binary_sha256=identity(binary)['sha256'],
                            state_sha256=hashlib.sha256(result.data).hexdigest(),
                            entry_code_bytes=labels.get('vl_contact_pair', labels['vl_contact_all']+1) -
                            labels['vl_contact_all'])
        print(f'{name}: public count boundary exact.', flush=True)
    return report


def catapult_budget(work, include):
    # Build a private real game and reuse its existing disk/model/cadence
    # checks, including worst flying frames. This benchmark runs the II+
    # game in a2run regardless of the focused test's --iie selection.
    game = DEV / 'examples/catapult'
    includes = [include, game / 'src']+[DEV / 'lib' / name
                                      for name in ('apple2', 'hgr', 'font', 'math', 'physics')]
    args = [str(argument) for path in includes for argument in ('-I', path)]
    obj, binary, labels = (work / ('catapult'+suffix) for suffix in ('.o', '.bin', '.lbl'))
    subprocess.run(['ca65', '-t', 'none', '-g', *args, '-o', str(obj),
                    str(game / 'src/catapult.s')], check=True)
    subprocess.run(['ld65', '-C', str(DEV / 'cc65/apple2_hgr.cfg'), '-Ln', str(labels),
                    '-o', str(binary), str(obj)], check=True)
    disk = work / 'CATAPULT.dsk'
    subprocess.run([sys.executable, str(DEV / 'tools/dos33.py'), '--master',
                    str(DEV / 'tools/dos33_system.bin'), '--out', str(disk),
                    '--bas', f'HELLO={game}/src/hello.bas',
                    '--bin', f'CATAPULT={binary}@0x6000'], check=True, capture_output=True)
    spec = importlib.util.spec_from_file_location('contact_all_catapult_disk',
                                                 game / 'tests/test_catapult_disk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DISK, module.LBL = disk, labels
    measured = module.main()
    return dict(cpu='NMOS6502', binary_bytes=binary.stat().st_size,
                binary_sha256=identity(binary)['sha256'],
                work={name: dict(cases=len(costs), median=statistics.median(costs),
                                 maximum=max(costs), cycles=costs)
                      for name, costs in measured.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='saved verlet_circ.asm source')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--only', choices=('bytes', 'clusters', 'bounds'))
    parser.add_argument('--bench', action='store_true', help='also run private Catapult II+ disk budgets')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or DEV / 'lib/physics/verlet_circ.asm'
    with tempfile.TemporaryDirectory(prefix='verlet-contact-all-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        (include / 'verlet_circ.asm').write_bytes(selected.read_bytes())
        config = work / 'fixture.cfg'
        config.write_text(CONFIG)
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference))
        if args.only in (None, 'bytes'):
            report['bytes'] = byte_domains(work, include, config, args.iie)
        if args.only in (None, 'clusters'):
            report['clusters'] = ordered_clusters(work, include, config, args.iie)
        if args.only in (None, 'bounds'):
            report['bounds'] = count_bounds(work, include, config, args.iie)
        if args.bench:
            report['catapult'] = catapult_budget(work, include)
        report.update(metadata(selected, args.iie))
        report['test_sha256'] = identity(__file__)['sha256']
        report['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
        del report['probe_config_sha256']
        report['model_sha256'] = identity(DEV / 'tools/verlet/contact.py')['sha256']
        report['dependencies'] = [identity(DEV / path) for path in (
            'lib/physics/verlet.asm', 'lib/physics/verlet_con.asm', 'lib/physics/verlet.inc',
            'lib/math/mul.asm', 'lib/math/sqrt.asm')]
        if args.bench:
            report['budget_test_sha256'] = identity(DEV / 'examples/catapult/tests/test_catapult_disk.py')['sha256']
            report['budget_runner'] = identity(DEV / 'tools/a2run/a2run')
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
