#!/usr/bin/env python3
"""Native HUD8: clipped columns, digits, phases, pages, byte-Y wrap and IRQs.

Unaligned digit/row tables expose page crossings. The independent model
consumes font bytes changed by earlier framebuffer writes. Every effective
pixel/font read and executed store must match in order. Full memory, bank,
stack and status guards preserve the existing D=0 drawing contract.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import tempfile

from test_hgr import DEV, ROOT, run

KERNEL = DEV / 'lib/hgrc/hgr_hud8_asm.s'
STUB = '''.exportzp ptr1,tmp1,tmp2,tmp3,tmp4,_hgr_g_glyph,_hgr_g_col,_hgr_g_bit,_hgr_g_y
.export hgr_hud8_digitlo,hgr_hud8_digithi,hgr_fixed_rowlo,hgr_fixed_rowhi,_hgr_base
.zeropage
ptr1:.res 2
tmp1:.res 1
tmp2:.res 1
tmp3:.res 1
tmp4:.res 1
_hgr_g_col:.res 1
_hgr_g_bit:.res 1
_hgr_g_y:.res 1
_hgr_g_glyph:.res 2
.segment "STATE"
_hgr_base:.res 1
.segment "DIGITS"
.res $E3
hgr_hud8_digitlo:.res 77
.res 3
hgr_hud8_digithi:.res 77
.segment "ROWS"
.res 3
hgr_fixed_rowlo:.res 256
.res 4
hgr_fixed_rowhi:.res 256
'''
CONFIG = '''MEMORY { ZP:start=$80,size=$80,type=rw; RAM:start=$6000,size=$1000,file=%O; STATE:start=$1100,size=$100,type=rw; DIGITS:start=$1200,size=$200,type=rw; ROWS:start=$1400,size=$210,type=rw; }
SEGMENTS { ZEROPAGE:load=ZP,type=zp; CODE:load=RAM,type=ro; STATE:load=STATE,type=bss; DIGITS:load=DIGITS,type=bss; ROWS:load=ROWS,type=bss; }
'''


def build_native(work, kernel):
    work.mkdir()
    (work / 'stub.s').write_text(STUB)
    (work / 'config.cfg').write_text(CONFIG)
    (work / 'kernel.s').write_bytes(Path(kernel).read_bytes())
    objects = []
    for member in (work / 'stub.s', work / 'kernel.s'):
        obj = work / (member.stem + '.o')
        run(['ca65', '-t', 'none', '-o', obj, member])
        objects.append(obj)
    run(['ld65', '-C', work / 'config.cfg', '-o', work / 'test.bin',
         '-Ln', work / 'test.lbl', *objects])
    return work


def probe_command(executable, before, after, rom, cpu, irq):
    return [executable, before / 'test.bin', before / 'test.lbl',
            after / 'test.bin', after / 'test.lbl', rom, cpu, irq]


def negative_controls(work, executable, before, source, rom):
    text = Path(source).read_text()
    mutations = (
        ('duplicate_live_irq', 1, '        sta (ptr1),y',
         '        sta (ptr1),y\n        sta (ptr1),y'),
        ('wrong_low_cancellation', 0, '        sec                     ; (rowlo+col+1)',
         '        clc                     ; (rowlo+col+1)'),
        ('missing_high_borrow', 0, '        sbc #0', '        nop\n        nop'),
        ('wrong_source_offset', 0, '        ldy tmp1', '        ldy #0'),
        ('palette', 0, '        eor #$7f', '        eor #$ff'),
        ('bank', 0, '_hgr_hud8_cell_run:\n', '_hgr_hud8_cell_run:\n        sta $C005\n'),
        ('stack', 0, '_hgr_hud8_cell_run:\n', '_hgr_hud8_cell_run:\n        sta $01F7\n'),
        ('fake_irq_entry', 0, '_hgr_hud8_cell_run:\n', '_hgr_hud8_cell_run:\n        jmp $0901\n'),
    )
    results = []
    for name, irq, old, new in mutations:
        assert old in text, ('missing fault marker', name)
        path = work / (name + '.s')
        path.write_text(text.replace(old, new, 1))
        mutant = build_native(work / name, path)
        command = probe_command(executable, before, mutant, rom, 0, irq)
        result = subprocess.run([str(arg) for arg in command], capture_output=True,
                                text=True, timeout=60)
        assert result.returncode != 0 and 'assert' in result.stderr.lower(), (name, result.stderr)
        entry = dict(name=name, rejected=True)
        if irq:
            proof = re.search(r'ORDER REJECT serial=0 live_irqs=(\d+) pixels_match=1', result.stderr)
            assert proof and int(proof[1]) > 0, result.stderr
            entry.update(actual_irqs=int(proof[1]), pixels_unchanged=True)
            print(f'HUD8 negative: {name} rejected; pixels unchanged, {proof[1]} real IRQs serviced',
                  flush=True)
        else:
            print('HUD8 negative:', name, 'rejected', flush=True)
        results.append(entry)
    return results


def parse_result(output):
    pattern = (r'(NMOS|65C02) IRQ=(\d) (\d+) cells/source; (\d+) ordered pixel/font reads, '
               r'(\d+) ordered writes; cycles (\d+) -> (\d+); IRQs (\d+)/(\d+); '
               r'(\d+) alias-modified font bytes, (\d+) borrow rows; deferrals (\d+)/(\d+); full guards PASS\n'
               r'Per-cell cycles (\d+) faster/(\d+) equal/(\d+) slower, range (-?\d+)\.\.(-?\d+)')
    match = re.search(pattern, output)
    assert match, output
    keys = ('irq', 'calls_per_source', 'effective_reads_per_source', 'ordered_stores_per_source',
            'before_cycles', 'after_cycles', 'before_irqs', 'after_irqs', 'alias_modified_bytes',
            'borrow_rows', 'before_deferred_operations', 'after_deferred_operations',
            'faster', 'equal', 'slower', 'minimum_cycle_delta', 'maximum_cycle_delta')
    return dict(cpu=match[1], **dict(zip(keys, map(int, match.groups()[1:]))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reference', help='compare a git revision with production')
    group.add_argument('--source', type=Path, help='compare candidate assembly with production')
    parser.add_argument('--negative', action='store_true', help='prove deliberate faults are rejected')
    parser.add_argument('--out', type=Path, help='write measurements and exact source identities')
    args = parser.parse_args()
    report = dict(reference=args.reference, results=[], negative_controls=[])
    with tempfile.TemporaryDirectory(prefix='hgr-hud8-native-') as directory:
        work = Path(directory)
        before, after = KERNEL, args.source or KERNEL
        if args.reference:
            before = work / 'reference.s'
            before.write_bytes(subprocess.check_output(
                ['git', 'show', args.reference + ':dev/lib/hgrc/hgr_hud8_asm.s'], cwd=ROOT))
        old = build_native(work / 'before', before)
        new = build_native(work / 'after', after)
        report['kernel_code_bytes'] = dict(before=(old / 'test.bin').stat().st_size,
                                           after=(new / 'test.bin').stat().st_size)
        rom = work / 'irq.rom'
        image = bytearray(8192)
        image[-2:] = bytes((0, 9))
        rom.write_bytes(image)
        executable = work / 'hud8-probe'
        run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
             'SRC=' + str(DEV / 'bench/hgr_hud8_probe.cpp'), 'OUT=' + str(executable)])
        for cpu in (0, 1):
            for irq in (0, 1):
                output = run(probe_command(executable, old, new, rom, cpu, irq))
                print(output.strip(), flush=True)
                report['results'].append(parse_result(output))
        if args.negative:
            report['negative_controls'] = negative_controls(work, executable, old, after, rom)
        report['kernel_sources'] = [dict(role=role, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                                    for role, path in (('before', before), ('after', after))]
        report['native_environment'] = dict(cpus=['NMOS6502', 'CMOS65C02'], iie_memory=True,
            timing='NTSC', decimal_flag=0, platform=platform.platform(),
            rom_sha256=hashlib.sha256(image).hexdigest(),
            tables='unaligned 77-digit pointers and 256 row entries; first 192 normal HGR rows',
            irq='real slot4 VIA T1, register-saving SEC-before-RTI handler; precise saved-frame deferrals')
    paths = [KERNEL, DEV / 'bench/hgr_hud8_probe.cpp',
             DEV / 'tools/a2shot/probe.hpp', DEV / 'tools/a2shot/sdk/include/pom2/core.hpp',
             DEV / 'tools/a2shot/sdk.mk', Path(__file__).resolve()]
    paths += list(DEV.glob('tools/a2shot/sdk/lib/*/libpom2_core.a'))
    report['source_identities'] = [dict(path=str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
