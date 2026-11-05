#!/usr/bin/env python3
"""Exact 16/8 division, optional full domain, entry alignments and timing reports."""
import argparse
import hashlib
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import json
from test_math import ROOT, a2test

DEV = ROOT / 'dev'
MATH = DEV / 'lib/math'
DIVISORS = (0,1,2,3,7,15,16,31,32,63,64,127,128,129,254,255)
SAMPLES = ((0,1),(255,1),(255,2),(256,1),(65535,255),(32511,127),
           (65535,1),(65535,2),(65535,3),(65535,127),(65535,128),
           (65535,0),(0,0),(32768,17),(0xa5a5,7),(65535,31))
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
SOURCE = '''MUL_TABLES=$0800
.include "math.inc"
.zeropage
input: .res 2
divisor: .res 1
.code
start: sei
 cld
 lda #0
 sta input
 sta input+1
sweep_start:
loop:
 lda input
 sta mul_x
 lda input+1
 sta mul_x+1
 lda divisor
 ldy #$A5
 jsr div16by8
 cpy #$A5
 bne fail
 ldx input
 sta results+512,x
 lda mul_x
 sta results,x
 lda mul_x+1
 sta results+256,x
 inc input
 bne loop
page_done:
 nop
resume:
 inc input+1
 bne loop
done: jmp done
fail: jmp fail
measure_setup:
 cld
 lda input
 sta mul_x
 lda input+1
 sta mul_x+1
 lda divisor
 ldy #$a5
measure_start:
 jsr div16by8
measure_done:
 jmp measure_done
.align 256
.include "div.asm"
kernel_end:
.bss
results: .res 768
.export start,sweep_start,page_done,resume,done,results,measure_setup,measure_start,measure_done
.export div16by8,kernel_end
.exportzp input,divisor
'''


def identity(path):
    path = Path(path)
    return dict(name=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def metadata(source, iie):
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
    return dict(source_sha256=identity(source)['sha256'],
                test_sha256=identity(__file__)['sha256'],
                fixture_config_sha256=hashlib.sha256(CONFIG.encode()).hexdigest(),
                compiler_version=version('ca65'), linker_version=version('ld65'),
                tool_artifacts=[identity(shutil.which(tool)) for tool in ('ca65', 'ld65')],
                environment=dict(model='IIe enhanced 128K' if iie else 'II+ 48K',
                                 frame_cycles=17030, artifacts=[identity(path) for path in paths]))


def build(work, text, include):
    source, config = work / 'divide.s', work / 'divide.cfg'
    source.write_text(text)
    config.write_text(CONFIG)
    obj, binary, labels = (source.with_suffix(ext) for ext in ('.o','.bin','.lbl'))
    subprocess.run(['ca65','-I',str(include),'-I',str(MATH),'-o',str(obj),str(source)],check=True)
    subprocess.run(['ld65','-C',str(config),'-Ln',str(labels),'-o',str(binary),str(obj)],check=True)
    return a2test.labels(labels), binary


def sweeps(work, include, iie, full, bench):
    points, binary = build(work, SOURCE, include)
    disk = a2test.build_disk(work, 'TEST', binary) if iie else None
    divisors = tuple(range(256)) if full else DIVISORS
    digest, raw_cycles, loop_cycles, peaks = hashlib.sha256(), [], [], set()
    for divisor in divisors:
        steps = a2test.bin_steps(binary) + [points.poke('divisor', divisor),
                 points.until('sweep_start'), 'hwstackwatch']
        for _ in range(256):
            steps.extend((points.until('page_done'), points.peek('results', 768),
                          points.until('resume')))
        steps.extend((points.until('done'), 'hwstack'))
        result = a2test.run(disk, steps, iie=iie, timeout=180)
        for high in range(256):
            numbers = range(high*256, (high+1)*256)
            quotients = [n//divisor if divisor else 65535 for n in numbers]
            expected = bytes(q&255 for q in quotients) + bytes(q>>8 for q in quotients)
            expected += bytes(n%divisor if divisor else n&255 for n in numbers)
            assert result.dumps[high] == expected, (divisor, high)
        digest.update(result.data)
        raw_cycles.append(result.cycles[-1])
        loop_cycles.append(result.cycles[-1]-result.cycles[0])
        peaks.update(map(int, re.findall(r'hwstack peak=(\d+) available=', result.out)))
    report = dict(pairs=len(divisors)*65536, divisors=list(divisors),
                  code_bytes=points['kernel_end']-points['div16by8'],
                  result_sha256=digest.hexdigest(), total_cycles=sum(raw_cycles),
                  loop_cycles=sum(loop_cycles), hardware_stack_peaks=sorted(peaks))
    print(f'Division: {report["pairs"]:,} exact pairs, including zero divisor, Y preserved; '
          f'IIe={iie}, {report["code_bytes"]} code bytes; loop {report["loop_cycles"]:,} cycles.')
    if bench:
        report['samples'] = {}
        for numerator, divisor in SAMPLES:
            steps = a2test.bin_steps(binary, start=points['measure_setup']) + [
                points.poke('input', numerator&255),
                f'poke:{points["input"]+1:04X}:{numerator>>8:02X}',
                points.poke('divisor', divisor), points.until('measure_start'),
                points.until('measure_done')]
            result = a2test.run(disk, steps, iie=iie)
            report['samples'][f'{numerator}/{divisor}'] = result.cycles[1]-result.cycles[0]
        print('  JSR/RTS cycles:', report['samples'])
    return report


def alignments(work, include, iie):
    digest, sizes, profiles = hashlib.sha256(), set(), {}
    for offset in range(256):
        target = work / f'align-{offset}'
        target.mkdir()
        source = '''MUL_TABLES=$0800
.include "math.inc"
.zeropage
input: .res 2
divisor: .res 1
remainder: .res 1
seen_y: .res 1
seen_flags: .res 1
saved_hw: .res 1
.code
setup:
 cld
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
 sta mul_x
 lda input+1
 sta mul_x+1
 lda divisor
 ldy #$a5
measure_start:
 jsr div16by8
measure_end:
 sta remainder
 sty seen_y
 php
 pla
 sta seen_flags
 tsx
 cpx saved_hw
 bne fail
done: jmp done
fail: jmp fail
.align 256
'''+f'.res {offset},$ea\n'+'''.include "div.asm"
kernel_end:
.export setup,measure_start,measure_end,done,div16by8,kernel_end
.exportzp input,divisor,remainder,seen_y,seen_flags,mul_x
'''
        points, binary = build(target, source, include)
        assert points['div16by8']&255 == offset
        sizes.add(points['kernel_end']-points['div16by8'])
        disk = a2test.build_disk(target, 'TEST', binary) if iie else None
        steps = a2test.bin_steps(binary)[:1]
        for numerator, divisor in SAMPLES:
            steps.extend((points.poke('input', numerator&255),
                f'poke:{points["input"]+1:04X}:{numerator>>8:02X}',
                points.poke('divisor', divisor), f'go:{points["setup"]:04X}',
                points.until('measure_start'), points.until('measure_end'),
                points.until('done'), points.peek('mul_x',2), points.peek('remainder',3)))
        result = a2test.run(disk, steps, iie=iie, timeout=180)
        costs = []
        for index, (numerator, divisor) in enumerate(SAMPLES):
            quotient = numerator//divisor if divisor else 65535
            remainder = numerator%divisor if divisor else numerator&255
            record = result.data[index*5:(index+1)*5]
            assert record[:4] == bytes((quotient&255, quotient>>8, remainder, 0xa5)), (offset,index)
            assert record[4]&0x0c == (numerator&1)<<2, ('I/D',offset,index,record[4])
            costs.append(result.cycles[index*3+1]-result.cycles[index*3])
        profiles[str(offset)] = costs
        digest.update(result.data)
    assert len(sizes) == 1
    report = dict(offsets=256, cases=256*len(SAMPLES), code_bytes=sizes.pop(),
                  inputs=[list(pair) for pair in SAMPLES], cycles=profiles,
                  result_sha256=digest.hexdigest())
    print(f'Division alignment: all 256 entry offsets, {report["cases"]:,} exact calls, '
          'quotient/remainder, Y, I/D and hardware-stack restoration.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true', help='check all 16,777,216 pairs')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path, help='saved div.asm source')
    parser.add_argument('--bench', action='store_true', help='also report direct call timings')
    parser.add_argument('--alignments', action='store_true', help='check all 256 entry alignments')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    source = args.reference or MATH / 'div.asm'
    with tempfile.TemporaryDirectory(prefix='math-division-') as directory:
        work = Path(directory)
        selected = work / 'selected'
        selected.mkdir()
        (selected / 'div.asm').write_bytes(source.read_bytes())
        report = dict(cpu='65C02' if args.iie else 'NMOS6502', reference=bool(args.reference),
                      sweep=sweeps(work, selected, args.iie, args.full, args.bench))
        if args.alignments:
            report['alignments'] = alignments(work, selected, args.iie)
        report.update(metadata(source, args.iie))
        if args.out:
            args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__=='__main__':
    main()
