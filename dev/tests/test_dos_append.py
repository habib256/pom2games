#!/usr/bin/env python3
"""DOS append: every capacity, source page crossings, return state and guards.

The default samples eight boundary capacities; --full covers DOS_CMD_MAX 1..256.
This guest calls dos_cmd_add directly and performs no DOS or COUT device I/O.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from test_hgr import DEV, run, a2test

BODY = """.code
entry:cld
 sei
 ldx #$FF
 txs
ready:nop
 lda #$A5
 ldx #0
clear_guard:
 sta dos_zp_prog,x
 inx
 bne clear_guard
 ldx #$50
clear_zp:
 sta $00,x
 inx
 bne clear_zp
 ldx #0
clear_buffer:
 sta dos_cmd_buf,x
 inx
.if DOS_CMD_MAX=256
 bne clear_buffer
.else
 cpx #DOS_CMD_MAX
 bne clear_buffer
.endif
 ldx #0
 lda #'A'
source:
 sta $9000,x
 sta $9100,x
 inx
 bne source
 clc
 lda $1000
 adc $1002
 sta terminator+1
 lda #$90
 adc $1003
 sta terminator+2
 lda #0
terminator:sta $FFFF
 ldx #0
 lda #'P'
prefix:
 cpx $1004
 bcs prefix_done
 sta dos_cmd_buf,x
 inx
 bne prefix
prefix_done:
 stx dos_cmd_ix
 lda #0
 sta dos_cmd_buf,x
 sta dos_cmd_overflow
begin:
 lda $1000
 ldy #$90
 jsr dos_cmd_add
returned:
 sta result
 php
 pla
 sta result+1
 txa
 sta result+2
 tya
 sta result+3
 tsx
 stx result+4
done:nop
resume:jmp ready
.bss
result:.res 5
apple2_zp_buf:.res 256
.code
"""


def cases_for(capacity):
    cases = []
    for initial in sorted({0, capacity // 2, capacity - 1}):
        space = capacity - 1 - initial
        lengths = {0, 1, max(0, space - 1), space, min(256, space + 1), 255, 256}
        for length in sorted(lengths):
            for offset in (0, 127, 255):
                cases.append((initial, length, offset))
    return cases


def check(work, kernel, capacities):
    implementation = kernel.read_text()
    config = work / 'test.cfg'
    config.write_text('MEMORY{RAM:start=$6000,size=$3600,type=rw,file=%O;}'
                      'SEGMENTS{CODE:load=RAM,type=ro;BSS:load=RAM,type=bss;}')
    count = 0
    for capacity in capacities:
        cases = cases_for(capacity)
        source = work / 'test.s'
        source.write_text(f'.include "apple2.inc"\nDOS_CMD_MAX={capacity}\n' +
                          BODY + implementation)
        obj = work / 'test.o'
        binary = work / 'test.bin'
        labels_file = work / 'test.lbl'
        run(['ca65', '-g', '-I', DEV / 'lib/apple2', '-o', obj, source])
        run(['ld65', '-C', config, '-Ln', labels_file, '-o', binary, obj])
        labels = a2test.labels(labels_file)
        disk = a2test.build_disk(work, 'DOSCAPS', binary)
        steps = []
        for initial, length, offset in cases:
            steps += [labels.until('ready'), f'poke:1000:{offset:02X}',
                      f'poke:1002:{length & 255:02X}', f'poke:1003:{length >> 8:02X}',
                      f'poke:1004:{initial:02X}', labels.until('begin'),
                      labels.until('returned'), labels.until('done'),
                      labels.peek('result', 5), labels.peek('dos_cmd_buf', capacity + 2),
                      labels.peek('dos_zp_prog', 256), 'peek:0050:176',
                      labels.until('resume')]
        size = capacity + 439
        for iie in (False, True):
            result = a2test.run(disk, steps, iie=iie)
            assert len(result.data) == len(cases) * size, (capacity, len(result.data))
            for index, (initial, length, offset) in enumerate(cases):
                data = result.data[index * size:(index + 1) * size]
                space = capacity - 1 - initial
                copied = min(length, space)
                full = int(length > space)
                context = (capacity, iie, initial, length, offset)
                assert data[0] == full and (data[1] & 1) == full, (*context, 'A/carry')
                assert data[2:5] == bytes((initial + copied, copied, 255)), (*context, 'X/Y/S')
                expected = (b'P' * initial + b'A' * copied + b'\0' +
                            b'\xA5' * (capacity - initial - copied - 1) +
                            bytes((initial + copied, full)))
                assert data[5:5 + capacity + 2] == expected, (*context, 'buffer/index/overflow')
                assert data[5 + capacity + 2:] == b'\xA5' * 432, (*context, 'guard/ZP')
        count += len(cases) * 2
        if capacity % 32 == 0 or len(capacities) < 20:
            print(f'DOS append capacity {capacity}: both CPUs OK.', flush=True)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='assemble this DOS command builder instead')
    parser.add_argument('--full', action='store_true', help='test all 256 capacities')
    parser.add_argument('--out', type=Path, help='write the coverage/source report')
    args = parser.parse_args()
    capacities = list(range(1, 257)) if args.full else [1, 2, 3, 8, 40, 128, 255, 256]
    kernel = (args.reference or DEV / 'lib/apple2/dos.asm').resolve()
    with tempfile.TemporaryDirectory(prefix='dos-append-') as directory:
        cases = check(Path(directory), kernel, capacities)
    report = dict(capacities=len(capacities), cases=cases, models=2,
                  source=dict(name=kernel.name, sha256=hashlib.sha256(kernel.read_bytes()).hexdigest()))
    print(json.dumps(report))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
