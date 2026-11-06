#!/usr/bin/env python3
"""Native DHGR read/write/masked rows against an independent SDK model.

Every count byte (including zero=256), all raw bank values, independent pointer
page crossings, both pages, buffer/screen aliases, palette bits and D/I states
run on NMOS/65C02 with and without real VIA IRQs. Architectural reads and
executed writes must match in order, including unchanged writes. Whole main/
aux RAM, code, shared parameters, aux-read trampoline and stack canaries are
also guarded. Public wrapper clipping and C-stack cleanup have separate tests.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from test_hgr import DEV, ROOT, run

MEMBERS = ('dhgr_block_asm.s', 'dhgr_block_setup.s', 'dhgr_sprite_asm.s')
STUB = '''.exportzp ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4,aux_read
.export _dhgr_addr,_dhgr_aux,_dhgr_buffer,_dhgr_count,_dhgr_sprite_mask
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
_dhgr_addr: .res 2
_dhgr_aux: .res 1
_dhgr_buffer: .res 2
_dhgr_count: .res 1
_dhgr_sprite_mask: .res 2
'''
CONFIG = '''MEMORY {
 ZP: start=$80,size=$80,type=rw;
 RAM: start=$6000,size=$4000,file=%O;
}
SEGMENTS {
 ZEROPAGE:load=ZP,type=zp;
 CODE:load=RAM,type=ro;
 DATA:load=RAM,type=rw;
}
'''


def build_native(work, members):
    work.mkdir()
    (work / 'stub.s').write_text(STUB)
    (work / 'config.cfg').write_text(CONFIG)
    objects = []
    for index, source in enumerate((work / 'stub.s', *members)):
        obj = work / (str(index) + '_' + source.stem + '.o')
        run(['ca65', '-t', 'none', '-I', DEV / 'lib/apple2', '-o', obj, source])
        objects.append(obj)
    run(['ld65', '-C', work / 'config.cfg', '-o', work / 'test.bin',
         '-Ln', work / 'test.lbl', *objects])
    return work


def probe_command(executable, before, after, rom, cpu, irq, mode):
    return [executable, before / 'test.bin', before / 'test.lbl',
            after / 'test.bin', after / 'test.lbl', rom, cpu, irq, mode]


def negative_controls(work, executable, before, members, rom):
    texts = [path.read_text() for path in members]
    transfer = next(i for i, text in enumerate(texts) if '_dhgr_write_block_asm:' in text)
    masked = next(i for i, text in enumerate(texts) if '_dhgr_sprite_asm:' in text)
    mutations = (
        ('duplicate_write', 0, transfer, '        sta (ptr1),y',
         '        sta (ptr1),y\n        sta (ptr1),y'),
        ('duplicate_read', 1, transfer, '        sta (ptr2),y',
         '        sta (ptr2),y\n        sta (ptr2),y'),
        ('write_palette', 0, transfer, '        and #$7F', '        and #$FF'),
        ('mask_palette', 2, masked, '        ora #$80', '        ora #$00'),
        ('transparent_store', 2, masked, '        beq next', '        nop\n        nop'),
        ('zero_count', 0, transfer, '        jsr dhgr_block_setup\n',
         '        jsr dhgr_block_setup\n        lda tmp2\n        bne :+\n        inc tmp2\n:\n'),
        ('raw_bank', 0, transfer,
         '        cpx #1                  ; raw bank values >=2 historically stay auxiliary\n        bne @aux',
         '        cpx #1'),
        ('source_page', 0, transfer, '        inc ptr2+1', '        nop'),
        ('irq_mask', 2, masked, '        sei', '        nop'),
        ('stack', 0, transfer, '_dhgr_write_block_asm:\n',
         '_dhgr_write_block_asm:\n        sta $01F5\n'),
    )
    for name, mode, member, old, new in mutations:
        assert old in texts[member], ('missing mutation marker', name)
        source = work / (name + '.s')
        source.write_text(texts[member].replace(old, new, 1))
        replacements = list(members)
        replacements[member] = source
        mutant = build_native(work / name, replacements)
        command = probe_command(executable, before, mutant, rom, 0, 0, mode)
        result = subprocess.run([str(arg) for arg in command], capture_output=True,
                                text=True, timeout=60)
        assert result.returncode != 0 and 'assert' in result.stderr.lower(), (name, result.stderr)
        print('Native transfer negative control:', name, 'rejected', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reference', help='compare a historical git revision with production')
    group.add_argument('--sources', nargs='+', type=Path,
                       help='compare candidate assembly members with production')
    parser.add_argument('--negative', action='store_true', help='prove deliberate faults are rejected')
    args = parser.parse_args()
    production = tuple(DEV / 'lib/hgrc' / name for name in MEMBERS)
    with tempfile.TemporaryDirectory(prefix='dhgr-transfer-native-') as directory:
        work = Path(directory)
        before, after = production, tuple(args.sources) if args.sources else production
        if args.reference:
            historical = []
            for name in MEMBERS:
                result = subprocess.run(['git', 'show', args.reference + ':dev/lib/hgrc/' + name],
                                        cwd=ROOT, capture_output=True, check=False)
                if result.returncode:
                    assert name != MEMBERS[0], result.stderr.decode()
                    continue  # Older revisions kept all three kernels in one member.
                source = work / name
                source.write_bytes(result.stdout)
                historical.append(source)
            before = tuple(historical)
        old = build_native(work / 'before', before)
        new = build_native(work / 'after', after)
        rom = work / 'irq.rom'
        image = bytearray(8192)
        image[-2:] = bytes((0, 9))
        rom.write_bytes(image)
        executable = work / 'transfer-probe'
        run(['make', '-s', '-C', DEV / 'tools/a2shot', 'probe',
             'SRC=' + str(DEV / 'bench/dhgr_transfer_probe.cpp'), 'OUT=' + str(executable)])
        for mode in range(3):
            for cpu in (0, 1):
                for irq in (0, 1):
                    print(run(probe_command(executable, old, new, rom, cpu, irq, mode)).strip(),
                          flush=True)
        if args.negative:
            negative_controls(work, executable, old, after, rom)


if __name__ == '__main__':
    main()
