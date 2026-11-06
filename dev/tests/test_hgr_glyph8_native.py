#!/usr/bin/env python3
"""Native HGR glyph8: byte rows, phases, pages, raw Y wrap and live IRQs.

The SDK fixture supplies 256 unaligned row-table entries: 192 normal HGR
rows and 64 distinct safe offsets for the raw byte-Y domain. Public clipping
is tested separately. Font data also aliases the framebuffer; the independent
pixel model consumes glyph bytes changed by earlier OR writes. D=0 is the
library contract. Every glyph/pixel read and executed store must match in order.
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

KERNEL = DEV / 'lib/hgrc/hgr_text8_asm.s'
STUB = '''.exportzp ptr1,tmp1,tmp2,tmp3,_hgr_g_glyph,_hgr_g_col,_hgr_g_bit,_hgr_g_y
.exportzp _hgr_t_bit,_hgr_t_col,_hgr_t_n,_hgr_t_s
.export _hgr_rowlo,_hgr_rowhi
.zeropage
ptr1:.res 2
tmp1:.res 1
tmp2:.res 1
tmp3:.res 1
_hgr_g_glyph:.res 2
_hgr_g_col:.res 1
_hgr_g_bit:.res 1
_hgr_g_y:.res 1
_hgr_t_bit:.res 1
_hgr_t_col:.res 1
_hgr_t_n:.res 1
_hgr_t_s:.res 2
.segment "TABLES"
.res 3
_hgr_rowlo:.res 256
.res 4
_hgr_rowhi:.res 256
'''
CONFIG = '''MEMORY {
 ZP:start=$80,size=$80,type=rw;
 RAM:start=$6000,size=$1000,file=%O;
 ROWS:start=$1400,size=$210,type=rw;
}
SEGMENTS {
 ZEROPAGE:load=ZP,type=zp;
 CODE:load=RAM,type=ro;
 TABLES:load=ROWS,type=bss;
}
'''


def build_native(work, kernel):
    work.mkdir()
    (work / 'stub.s').write_text(STUB)
    (work / 'config.cfg').write_text(CONFIG)
    (work / 'kernel.s').write_bytes(Path(kernel).read_bytes())
    objects = []
    for member in (work / 'stub.s', work / 'kernel.s', DEV / 'lib/hgrc/hgr_text_addr.s'):
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
        ('wrong_source_carry', 0, '        sec\n        sbc _hgr_g_y',
         '        clc\n        sbc _hgr_g_y'),
        ('wrong_end', 0, '        cpx tmp1', '        cpx #8'),
        ('palette', 0, '        and #$7F', '        and #$FF'),
        ('bank', 0, '_hgr_blit_glyph8:\n', '_hgr_blit_glyph8:\n        sta $C005\n'),
        ('stack', 0, '_hgr_blit_glyph8:\n', '_hgr_blit_glyph8:\n        sta $01F7\n'),
        ('fake_irq_entry', 0, '_hgr_blit_glyph8:\n', '_hgr_blit_glyph8:\n        jmp $0901\n'),
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
            print(f'Glyph8 negative: {name} rejected; pixels unchanged, {proof[1]} real IRQs serviced',
                  flush=True)
        else:
            print('Glyph8 negative:', name, 'rejected', flush=True)
        results.append(entry)
    return results


def parse_result(output):
    pattern = (r'(NMOS|65C02) IRQ=(\d) (\d+) calls/source, (\d+) exact effective glyph/pixel reads '
               r'\+ (\d+) ordered stores/source; cycles (\d+) -> (\d+); IRQs (\d+)/(\d+); '
               r'full main/aux/code/tables/source/params/stack/bank/I/D guards PASS\n'
               r'(\d+) alias-modified glyph bytes consumed/source; decoded IRQ deferrals (\d+)/(\d+)\n'
               r'Per-call cycles: (\d+) faster/(\d+) equal/(\d+) slower, range (-?\d+)\.\.(-?\d+)')
    match = re.search(pattern, output)
    assert match, output
    keys = ('irq', 'calls_per_source', 'effective_reads_per_source', 'ordered_stores_per_source',
            'before_cycles', 'after_cycles', 'before_irqs', 'after_irqs', 'alias_modified_bytes',
            'before_deferred_operations', 'after_deferred_operations', 'faster', 'equal', 'slower',
            'minimum_cycle_delta', 'maximum_cycle_delta')
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
    with tempfile.TemporaryDirectory(prefix='hgr-glyph8-native-') as directory:
        work = Path(directory)
        before, after = KERNEL, args.source or KERNEL
        if args.reference:
            before = work / 'reference.s'
            before.write_bytes(subprocess.check_output(
                ['git', 'show', args.reference + ':dev/lib/hgrc/hgr_text8_asm.s'], cwd=ROOT))
        old = build_native(work / 'before', before)
        new = build_native(work / 'after', after)
        rom = work / 'irq.rom'
        image = bytearray(8192)
        image[-2:] = bytes((0, 9))
        rom.write_bytes(image)
        executable = work / 'glyph8-probe'
        run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
             'SRC=' + str(DEV / 'bench/hgr_glyph8_probe.cpp'), 'OUT=' + str(executable)])
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
            tables='fixed unaligned 256-entry raw tables, normal HGR coordinates in first192entries',
            irq='real slot4 VIA T1, register-saving SEC-before-RTI handler; precise saved-frame deferrals')
    paths = [KERNEL, DEV / 'lib/hgrc/hgr_text_addr.s', DEV / 'bench/hgr_glyph8_probe.cpp',
             DEV / 'tools/a2shot/probe.hpp', DEV / 'tools/a2shot/sdk/include/pom2/core.hpp',
             DEV / 'tools/a2shot/sdk.mk', Path(__file__).resolve()]
    paths += list(DEV.glob('tools/a2shot/sdk/lib/*/libpom2_core.a'))
    report['source_identities'] = [dict(path=str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
