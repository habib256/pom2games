#!/usr/bin/env python3
"""Paired quarter-square initialization: tables, all scratch/flags, boot relocation.

Default cases cover four dirty seeds, both IRQ states, three table placements
and CODE/INIT entry placement. --alignments adds every entry low byte. The
18 math zero-page bytes, return A/X/Y/P and hardware stack are checked against
independent expectations, including the former accumulator residue.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, a2test
from test_verlet_ground_probes import identity, metadata
from verlet import harness

CONFIG = '''MEMORY {
 ZP: start=$0050,size=$00b0,type=rw,define=yes;
 MAIN: start=$6000,size=$3600,type=rw,file=%O;
}
SEGMENTS {
 ZEROPAGE: load=ZP,type=zp;
 CODE: load=MAIN,type=ro,align=$100;
 INIT: load=MAIN,type=ro,align=$100,optional=yes;
 BSS: load=MAIN,type=bss,optional=yes;
}
'''
FIELDS = ('mul_x', 'mul_x+1', 'mul_y', 'mul_p0', 'mul_p1', 'mul_p2', 'mul_t',
          'mul_s1l', 'mul_s1l+1', 'mul_s1h', 'mul_s1h+1', 'mul_s2l', 'mul_s2l+1',
          'mul_s2h', 'mul_s2h+1', 'mul_acc0', 'mul_acc1', 'mul_acc2')


def check(include, iie, alignments):
    report = {}
    cases = [(base, boot, offset, seed)
             for base in (0x0800, 0x4000, 0x8000) for boot in (0, 1)
             for offset in (0, 127, 255) for seed in (0, 1, 0xA5, 0xFF)]
    if alignments:
        cases += [(2048, 0, offset, 165) for offset in range(256) if offset not in (0, 127, 255)]
    for base, boot, offset, seed in cases:
        name = f'{base:04x}_boot{boot}_off{offset}_seed{seed}'
        initial = [seed + i * 37 & 255 for i in range(len(FIELDS))]
        setup = ''.join((f' lda #{value}\n sta {field}\n' for field, value in zip(FIELDS, initial)))
        reserve = ('.segment "INIT"\n' if boot else '.align 256\n') + f'.res {offset}\n' + ('.segment "CODE"\n' if boot else '')
        source = f'''MUL_TABLES={base}
MUL_ACC=1
MUL_INIT_BOOT={boot}
.include "math.inc"
.bss
saved_hw: .res 1
returned: .res 4
.code
start:
 cld
''' + setup + ' lda #$73\n pha\n plp\n' + (' sei\n' if seed & 1 else ' cli\n') + ''' tsx
 stx saved_hw
init_start:
 jsr mul_init
init_done:
 sta returned
 stx returned+1
 sty returned+2
 php
 pla
 sta returned+3
 tsx
 cpx saved_hw
 beq done
fail: jmp fail
done: jmp done
''' + reserve + '.include "mul.asm"\n' + ('.segment "INIT"\n' if boot else '') + '''kernel_end:
.export init_start,init_done,done,returned,mul_init,kernel_end
.exportzp mul_x
'''
        with tempfile.TemporaryDirectory(prefix='mul-init-') as directory:
            work = Path(directory)
            cfg = work / 'fixture.cfg'
            cfg.write_text(CONFIG)
            labels, binary = harness.build(work, source, includes=(include,), cfg=cfg)
            disk = a2test.build_disk(work, 'TEST', binary) if iie else None
            result = a2test.run(disk, a2test.bin_steps(binary) + [labels.until('init_start'), 'hwstackwatch', labels.until('init_done'), 'hwstack', labels.until('done'), f'peek:{base:04X}:2048', labels.peek('mul_x', len(FIELDS)), labels.peek('returned', 4)], iie=iie)
            sq = [n * n // 4 for n in range(512)]
            mirror = [sq[abs(n - 255)] for n in range(512)]
            expected = bytes((value >> shift & 255 for table in (sq, mirror) for shift in (0, 8) for value in table))
            assert result.dumps[0] == expected, ('tables', name)
            state = bytearray(initial)
            for index, value in ((3, 0), (4, 255), (6, 0), (8, base >> 8), (10, (base >> 8) + 2), (12, (base >> 8) + 4), (14, (base >> 8) + 6)):
                state[index] = value
            flags = 0x30 | ((seed & 1) << 2) | (((base >> 8) + 6) & 0x80)
            assert result.dumps[1] == state, ('scratch/pointers', name, result.dumps[1].hex(), state.hex())
            assert result.dumps[2] == bytes(((base >> 8) + 6, 0, 255, flags)), ('registers/flags', name, result.dumps[2].hex())
            cycles = result.cycles[1] - result.cycles[0]
            stack = re.search('hwstack peak=(\\d+) available=(\\d+) overflow=(\\d+)', result.out)
            assert stack and (not int(stack[3])), name
            report[name] = {'cycles': cycles, 'code_bytes': labels['kernel_end'] - labels['mul_init'], 'hardware_stack_peak_bytes': int(stack[1]), 'state_sha256': hashlib.sha256(result.data).hexdigest()}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, help='saved mul.asm source')
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--alignments', action='store_true',
                        help='also measure every entry low byte')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = args.reference or DEV / 'lib/math/mul.asm'
    with tempfile.TemporaryDirectory(prefix='math-init-') as directory:
        include = Path(directory)
        (include / 'mul.asm').write_bytes(selected.read_bytes())
        cases = check(include, args.iie, args.alignments)
    report = dict(cpu='65C02' if args.iie else 'NMOS6502',
                  reference=bool(args.reference), cases=cases)
    report.update(metadata(selected, args.iie))
    report['test_sha256'] = identity(__file__)['sha256']
    report['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
    del report['probe_config_sha256']
    report['test_dependencies'] = [identity(DEV / 'tests' / name) for name in (
        'test_hgr.py', 'test_verlet_ground_probes.py')]
    cycles = [case['cycles'] for case in cases.values()]
    sizes = sorted({case['code_bytes'] for case in cases.values()})
    print(f"{report['cpu']}: {len(cases)} exact table/scratch/register/flag/stack cases; "
          f"code {sizes} bytes, {min(cycles)}..{max(cycles)} cycles", flush=True)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
