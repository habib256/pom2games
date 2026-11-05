#!/usr/bin/env python3
"""All height-map probe distances: exact addresses, metadata, flags and models."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import random
import re
import shutil
import subprocess
import tempfile
from test_hgr import DEV, run, a2test
from test_verlet_quarter_abs import CONFIG


FIELDS = ('vl_hxl', 'vl_hxh', 'vl_hgt', 'vl_hm2', 'vl_hp2',
          'vl_tptr', 'vl_tptr+1', 'slope', 'flags')


def identity(path):
    path = Path(path)
    return dict(name=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def metadata(source_path, iie):
    def version(command):
        result = subprocess.run([command, '--version'], capture_output=True,
                                text=True, check=True)
        return (result.stdout+result.stderr).strip()

    runner = DEV / 'tools' / ('a2shot/a2shot' if iie else 'a2run/a2run')
    paths = [runner, DEV / 'tools/a2shot/roms' / ('apple2e.rom' if iie else 'apple2p.rom'),
             DEV / 'tools/a2shot/roms/disk2.rom', DEV / 'tools/dos33_system.bin']
    if iie:
        host = {'Darwin-arm64': 'darwin-arm64', 'Linux-x86_64': 'linux-x86_64'}[
            platform.system()+'-'+platform.machine()]
        paths.append(DEV / 'tools/a2shot/sdk/lib' / host / 'libpom2_core.a')
    else:
        paths += [DEV / 'tools/a2run/cpu6502.c', DEV / 'tools/a2run/a2run.c']
    return dict(source_sha256=identity(source_path)['sha256'],
                test_sha256=identity(__file__)['sha256'],
                probe_config_sha256=hashlib.sha256(CONFIG.encode()).hexdigest(),
                compiler_version=version('ca65'), linker_version=version('ld65'),
                tool_artifacts=[identity(shutil.which(tool)) for tool in ('ca65', 'ld65')],
                environment=dict(model='IIe enhanced 128K' if iie else 'II+ 48K',
                                 frame_cycles=17030, artifacts=[identity(path) for path in paths]))


def probes(work, source, iie):
    # Compile the actual sampling instructions and height lookup from the
    # selected full source. Integrated model tests below cover the full entry.
    ground = source.split('vl_ground:\n', 1)[1]
    start = ground.index('        VL_GROUND_ENTER\n') + len('        VL_GROUND_ENTER\n')
    stage = ground[start:ground.index('        BMI     @sneg', start)]
    height = source.split('vl_height_at:\n', 1)[1].split('\n.endif', 1)[0]
    pattern = work / 'pattern.bin'
    pattern.write_bytes(bytes((address >> 2) & 63 for address in range(0x1c00, 0x2400)))
    copy = ''.join(f' lda {field}\n sta records+{index*256},x\n'
                   for index, field in enumerate(FIELDS))
    digest, cases, cycles = hashlib.sha256(), 0, 0
    sizes, peaks = set(), set()
    for probe in range(1, 128):
        for table in (0x2000, 0x20ff):
            target = work / f'{probe}_{table:04x}'
            target.mkdir()
            text = f'''VL_HEIGHTS={table}
VL_PROBE={probe}
.zeropage
vl_hxl: .res 1
vl_hxh: .res 1
vl_hgt: .res 1
vl_hm2: .res 1
vl_hp2: .res 1
vl_tptr: .res 2
input: .res 1
index: .res 1
slope: .res 1
flags: .res 1
saved_hw: .res 1
.code
start:
 sei
 cld
 lda #0
 sta index
setup:
 ldx index
 lda highs,x
 sta vl_xh
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
 sta vl_xl
 ldx #0
 jsr probe
 sta slope
 php
 pla
 sta flags
 cpx #0
 bne fail
 tsx
 cpx saved_hw
 bne fail
 ldx input
{copy} inc input
 bne loop
page_done: nop
resume:
 inc index
 lda index
 cmp #3
 bne setup
done: jmp done
fail: jmp fail
probe:
{stage} rts
vl_height_at:
{height}
highs: .byte 0,1,255
.bss
vl_xl: .res 1
vl_xh: .res 1
records: .res {len(FIELDS)*256}
.export start,page_done,resume,done,records,probe,vl_height_at
'''
            asm, config = target / 'entry.s', target / 'entry.cfg'
            asm.write_text(text)
            config.write_text(CONFIG)
            obj, binary, labels = (asm.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
            run(['ca65', '-o', obj, asm])
            run(['ld65', '-C', config, '-Ln', labels, '-o', binary, obj])
            points = a2test.labels(labels)
            sizes.add(points['vl_height_at']-points['probe'])
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            steps = a2test.bin_steps(binary) + [f'load:{pattern}@1C00', 'hwstackwatch']
            for _ in range(3):
                steps.extend((points.until('page_done', limit=2000),
                              points.peek('records', len(FIELDS)*256), points.until('resume')))
            steps.extend((points.until('done'), 'hwstack'))
            result = a2test.run(disk, steps, iie=iie)
            expected = bytearray()
            for high in (0, 1, 255):
                rows = []
                for low in range(256):
                    world = high*256+low
                    center = (table+world)&65535
                    at = lambda address: (address >> 2)&63
                    middle = at(center)
                    left = at((table+world-probe)&65535)
                    right = at((table+world+probe)&65535)
                    slope = right-left
                    # PHP supplies B/reserved bits. The bounded heights make
                    # signed subtraction overflow impossible; I alternates.
                    flags = 0x30 | ((low&1)<<2) | int(right >= left)
                    flags |= (int(slope == 0)<<1) | (int(slope < 0)<<7)
                    rows.append((low, high, middle, left, right,
                                 center&255, center>>8, slope&255, flags))
                for field in range(len(FIELDS)):
                    expected.extend(row[field] for row in rows)
            assert result.data == expected, ('height-map address/value/state', probe, hex(table), iie)
            peaks.update(map(int, re.findall(r'hwstack peak=(\d+) available=', result.out)))
            digest.update(result.data)
            cycles += result.cycles[-1]
            cases += 3*256
        if probe % 32 == 0:
            print(f'Height-map probes: distances 1..{probe}, {cases:,} exact cases.', flush=True)
    assert len(sizes) == 1
    report = dict(cases=cases, stage_bytes=sizes.pop(), state_sha256=digest.hexdigest(),
                  hardware_stack_peaks=sorted(peaks), total_cycles=cycles,
                  probe_range=[1, 127], height_table_addresses=[0x2000, 0x20ff],
                  world_high_bytes=[0, 1, 255])
    print(f'Height-map probes: {cases:,} exact cases, all PROBE 1..127, page/word wrap, '
          f'center/neighbor values and restored pointer, X, I/D and stack; IIe={iie}, '
          f'{report["stage_bytes"]} sampling bytes, hardware peaks {report["hardware_stack_peaks"]}.')
    return report


def benchmark(work, include, iie):
    import test_verlet as verlet
    from verlet import harness
    rows = [row for row in verlet.cases(random.Random(7))
            if verlet.OPS[row[1]] == 'gnd'][:12]
    script = [(1, list(row[0]) + [row[1], row[2], row[3], row[4], row[5],
                                row[6]&255, row[6]>>8, row[7], row[8]], 1)
              for row in rows]
    expected = b''.join(verlet.model1(row) for row in rows)
    report = {}
    for definitions, name in verlet.SPEED:
        target = work / name.replace(' ', '_')
        target.mkdir()
        prelude = verlet.prelude1().replace('.include "verlet.inc"',
                                           definitions+'\n.include "verlet.inc"')
        text = harness.source(prelude, verlet.EPILOGUE1, verlet.INPUTS1,
                              verlet.SNAPS1, script, init='mul_init', snap_seg='LOWBSS')
        text = text.replace('hs_tick: JSR    tick\n', 'hs_tick: JSR    tick\nmeasure_end:\n')
        text += '\n.export hs_tick,measure_end\n'
        points, binary = harness.build(target, text, includes=(include,))
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)
        for _ in rows:
            steps.extend((points.until('hs_tick'), 'hwstackwatch',
                          points.until('measure_end'), 'hwstack'))
        steps.extend((points.until('hs_done'), points.peek('hs_snaps', len(expected))))
        result = a2test.run(disk, steps, iie=iie)
        assert result.data == expected, ('integrated ground', name)
        costs = [result.cycles[2*i+1]-result.cycles[2*i] for i in range(len(rows))]
        peaks = list(map(int, re.findall(r'hwstack peak=(\d+) available=', result.out)))
        assert len(peaks) == len(rows)
        report[name] = dict(cycles=costs, hardware_stack_peaks=peaks,
                            binary_bytes=binary.stat().st_size,
                            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
        print(f'  {name}: {binary.stat().st_size} loaded bytes; '
              f'12 model-checked ground calls {costs}; hardware peaks {peaks}')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path, help='saved verlet_hmap.asm source')
    parser.add_argument('--bench', action='store_true', help='also measure integrated ground calls')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    source_path = args.reference or DEV / 'lib/physics/verlet_hmap.asm'
    source = source_path.read_text()
    with tempfile.TemporaryDirectory(prefix='verlet-ground-probes-') as directory:
        work = Path(directory)
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference),
                      probes=probes(work, source, args.iie))
        if args.bench:
            include = work / 'selected'
            include.mkdir()
            (include / 'verlet_hmap.asm').write_text(source)
            report['ground'] = benchmark(work, include, args.iie)
        report.update(metadata(source_path, args.iie))
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
