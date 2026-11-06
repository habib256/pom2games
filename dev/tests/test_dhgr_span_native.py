#!/usr/bin/env python3
"""Native DHGR spans: independent pixels, ordered stores, real IRQs and guards.

Run legal native endpoints across every bit/byte phase, both pages, tall rows
and full screens on NMOS/65C02. --source substitutes a candidate, --reference
compares a git revision with production. The native entry requires clipped
rows and ordered endpoints; public clipping and refusal tests remain separate.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from test_hgr import DEV, ROOT, run

KERNEL = DEV / 'lib/hgrc/dhgr_span_asm.s'
STUB = '''.exportzp ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4,aux_read
.export _dhgr_base,_dhgr_pattern,_dhgr_first,_dhgr_last,_dhgr_first_mask,_dhgr_last_mask
.zeropage
ptr1: .res 2
ptr2: .res 2
ptr3: .res 2
ptr4: .res 2
tmp1: .res 1
tmp2: .res 1
tmp3: .res 1
tmp4: .res 1
aux_read: .res 9
.data
_dhgr_base: .byte $20
_dhgr_pattern: .res 4
.bss
_dhgr_first: .res 1
_dhgr_last: .res 1
_dhgr_first_mask: .res 1
_dhgr_last_mask: .res 1
'''
CONFIG = '''MEMORY {
 ZP: start=$80,size=$80,type=rw;
 RAM: start=$6000,size=$4000,file=%O;
}
SEGMENTS {
 ZEROPAGE:load=ZP,type=zp;
 CODE:load=RAM,type=ro;
 RODATA:load=RAM,type=ro;
 DATA:load=RAM,type=rw;
 BSS:load=RAM,type=bss,define=yes;
}
'''


def build_native(work, source):
    work.mkdir()
    (work / 'stub.s').write_text(STUB)
    (work / 'config.cfg').write_text(CONFIG)
    text = Path(source).read_text()
    text = text.replace('.bss\n', '.bss\n.export span_bss_begin,span_bss_end\nspan_bss_begin:\n', 1)
    text = text.replace('.rodata\n', 'span_bss_end:\n.rodata\n', 1)
    (work / 'kernel.s').write_text(text)
    objects = []
    for member in (work / 'stub.s', work / 'kernel.s',
                   DEV / 'lib/hgrc/dhgr_rows.s', DEV / 'lib/hgrc/dhgr_cells.s'):
        obj = work / (member.stem + '.o')
        run(['ca65', '-t', 'none', '-I', DEV / 'lib/apple2', '-I', DEV / 'lib/hgrc',
             '-o', obj, member])
        objects.append(obj)
    run(['ld65', '-C', work / 'config.cfg', '-o', work / 'test.bin',
         '-Ln', work / 'test.lbl', *objects])
    return work


def negative_controls(work, executable, before, source, rom):
    text = Path(source).read_text()
    mutations = {
        'duplicate': text.replace('        sta (ptr1),y',
                                  '        sta (ptr1),y\n        sta (ptr1),y', 1),
        'mask': text.replace('        sei', '        nop', 1),
        'lifetime': text.replace('        stx ptr1+1', '        stx tmp3', 1),
        'stack': text.replace('_dhgr_span_asm:\n',
                              '_dhgr_span_asm:\n        sta $01F5\n', 1),
    }
    for name, mutation in mutations.items():
        assert mutation != text, ('missing mutation marker', name)
        path = work / (name + '.s')
        path.write_text(mutation)
        mutant = build_native(work / name, path)
        result = subprocess.run([str(p) for p in (executable, before / 'test.bin',
                                before / 'test.lbl', mutant / 'test.bin', mutant / 'test.lbl',
                                rom, 0, 0)], capture_output=True, text=True)
        assert result.returncode != 0 and 'assert' in result.stderr.lower(), (name, result.stderr)
        print('Native span negative control:', name, 'rejected')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--source', type=Path, help='compare a candidate with production')
    group.add_argument('--reference', help='compare a git revision with production')
    parser.add_argument('--negative', action='store_true', help='test duplicate/mask/lifetime/stack faults')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='dhgr-span-native-') as directory:
        work = Path(directory)
        before, after = KERNEL, args.source or KERNEL
        if args.reference:
            before = work / 'reference.s'
            before.write_bytes(subprocess.check_output(
                ['git', 'show', args.reference + ':dev/lib/hgrc/dhgr_span_asm.s'], cwd=ROOT))
        old = build_native(work / 'before', before)
        new = build_native(work / 'after', after)
        rom = work / 'irq.rom'
        image = bytearray(8192)
        image[-2:] = bytes((0, 9))
        rom.write_bytes(image)
        executable = work / 'span-probe'
        run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
             'SRC=' + str(DEV / 'bench/dhgr_span_probe.cpp'), 'OUT=' + str(executable)])
        for cpu in (0, 1):
            for irq in (0, 1):
                print(run([executable, old / 'test.bin', old / 'test.lbl',
                           new / 'test.bin', new / 'test.lbl', rom, cpu, irq]).strip())
        if args.negative:
            negative_controls(work, executable, old, after, rom)


if __name__ == '__main__':
    main()
