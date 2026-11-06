#!/usr/bin/env python3
"""All native 16-bit decimal strings, aliases, pointer crossings and ABI guards."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, run, a2test
from test_verlet_helpers import CONFIG
from test_verlet_ground_probes import identity, metadata


def check(work, include, iie):
    report = {}
    for absolute in (False, True):
        for buffer in (0x4000, 0x40fc, 0x9000):
            name = f'absolute{int(absolute)}_buffer{buffer:04x}'
            target = work / name
            target.mkdir()
            slots = ('dec_lo', 'dec_hi', 'dec_t', 'dec_d')
            aliases = (''.join(f'{field}=${0x3000+index:04x}\n' for index, field in enumerate(slots))
                       if absolute else '.zeropage\n'+''.join(f'{field}:.res 1\n' for field in slots))
            fields = [f'${buffer-1+index:04x}' for index in range(8)]
            fields += ['returned_y', 'returned_a', 'returned_x', 'returned_flags', 'dec_lo',
                       'dec_hi', 'dec_ptr', 'dec_ptr+1', 'left_guard', 'right_guard']
            copy = ''.join(f' lda {field}\n sta records+{index*256},x\n'
                           for index, field in enumerate(fields))
            text = aliases + f'''.zeropage
left_guard:.res 1
dec_ptr:.res 2
right_guard:.res 1
input:.res 2
saved_hw:.res 1
returned_a:.res 1
returned_x:.res 1
returned_y:.res 1
returned_flags:.res 1
.code
start:
 sei
 ldx #255
 txs
 cld
 lda #0
 sta input
 sta input+1
 lda #165
 sta left_guard
 sta right_guard
 lda #<{buffer}
 sta dec_ptr
 lda #>{buffer}
 sta dec_ptr+1
loop:
 lda #165
 ldx #7
clear:
 sta ${buffer-1:04x},x
 dex
 bpl clear
 lda input
 sta dec_lo
 lda input+1
 sta dec_hi
 lda #$3c
 sta dec_t
 lda #$c3
 sta dec_d
 lda input
 and #1
 beq irq
 sei
 bne invoke
irq:cli
invoke:
 tsx
 stx saved_hw
 ldx #$a5
 ldy #$5a
 jsr u16_to_dec
 sta returned_a
 stx returned_x
 sty returned_y
 php
 pla
 and #$0c
 sta returned_flags
 tsx
 cpx saved_hw
 beq :+
 jmp fail
:ldx input
''' + copy + ''' inc input
 beq page_done
 jmp loop
page_done:nop
resume:
 inc input+1
 beq done
 jmp loop
done:jmp done
fail:jmp fail
watch_start:sei
watch_begin:jsr u16_to_dec
watch_end:jmp watch_end
kernel_start:
.include "dec.asm"
kernel_end:
.bss
records:.res ''' + str(len(fields)*256) + '''
.export start,page_done,resume,done,records,kernel_start,kernel_end,watch_start,watch_begin,watch_end
'''
            source, config = target / 'entry.s', target / 'entry.cfg'
            source.write_text(text)
            config.write_text(CONFIG)
            obj, binary, labels = (source.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
            run(['ca65', '-I', include, '-o', obj, source])
            run(['ld65', '-C', config, '-Ln', labels, '-o', binary, obj])
            points = a2test.labels(labels)
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            steps = a2test.bin_steps(binary)
            for _ in range(256):
                steps += [points.until('page_done'), points.peek('records', len(fields)*256),
                          points.until('resume')]
            steps += [points.until('done'), f'go:{points["watch_start"]:04X}', points.until('watch_begin'),
                      'hwstackwatch', points.until('watch_end'), 'hwstack',
                      f'peek:6000:{binary.stat().st_size}']
            result = a2test.run(disk, steps, iie=iie, timeout=180)
            assert result.dumps[-1] == binary.read_bytes(), ('code/tables', name)
            digest = hashlib.sha256()
            for high, have in enumerate(result.dumps[:256]):
                for low in range(256):
                    value = high*256+low
                    digits = str(value).encode()
                    expected = b'\xa5'+digits+b'\0'+b'\xa5'*(6-len(digits))
                    expected += bytes((len(digits), 0, 255, (low & 1)*4, value % 10, 0,
                                       buffer & 255, buffer >> 8, 165, 165))
                    actual = bytes(have[plane*256+low] for plane in range(len(fields)))
                    assert actual == expected, (name, value, actual.hex(), expected.hex())
                digest.update(have)
            stack = re.search(r'hwstack peak=(\d+) available=(\d+) overflow=(\d+)', result.out)
            assert stack and int(stack[1]) == 2 and int(stack[3]) == 0, (name, stack.groups() if stack else 'missing hardware stack record')
            report[name] = dict(cases=65536, kernel_bytes=points['kernel_end']-points['kernel_start'],
                                hardware_stack_peak_bytes=int(stack[1]),
                                snapshot_sha256=digest.hexdigest())
            print(name, '65536 strings / lengths / NUL+buffer guards / A/X/Y / I/D / stack / inputs+pointer+code', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path, help='saved dec.asm source')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    source = args.reference or DEV / 'lib/math/dec.asm'
    report = dict(cpu='65C02' if args.iie else 'NMOS6502', metadata=metadata(source, args.iie))
    report['metadata'].pop('probe_config_sha256', None)
    report['metadata']['test_sha256'] = identity(__file__)['sha256']
    report['metadata']['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='math-decimal-') as directory:
        work = Path(directory)
        include = work / 'include'
        include.mkdir()
        (include / 'dec.asm').write_bytes(source.read_bytes())
        report['cases'] = check(work, include, args.iie)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
