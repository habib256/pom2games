#!/usr/bin/env python3
"""Signed move/correction and squared-distance oracles, with ABI guards."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from test_hgr import DEV, run, a2test
from test_verlet_helpers import CONFIG
from test_verlet_ground_probes import identity, metadata


def build(work, text, include):
    source, config = work / 'entry.s', work / 'entry.cfg'
    source.write_text(text)
    config.write_text(CONFIG)
    obj, binary, labels = (source.with_suffix(ext) for ext in ('.o', '.bin', '.lbl'))
    run(['ca65', '-I', include, '-I', DEV / 'lib/physics', '-I', DEV / 'lib/math',
         '-o', obj, source])
    run(['ld65', '-C', config, '-Ln', labels, '-o', binary, obj])
    return a2test.labels(labels), binary


def movements(work, include, iie):
    report = {}
    for kind in ('sub_x', 'sub_y', 'corr_x', 'corr_y'):
        axis, paired = kind[-1], kind.startswith('corr')
        for high in ((True,) if axis == 'x' else (False, True)):
            # Numeric edges exercise signed overflow and both low-byte carries.
            # The alias case also crosses an indexed page on every point access.
            for base, aliases in ((0, False), (0x7fffff, False), (0x800000, False),
                                  (0xffffff, False), (0xfffe81, True)):
                name = f'{kind}_high{int(high)}_{base:06x}_alias{int(aliases)}'
                target = work / name
                target.mkdir()
                planes = ['xf', 'xl', 'xh', 'yf', 'yh'] + (['yu'] if high and axis == 'y' else [])
                planes += ['oxf', 'oxl', 'oxh', 'oyf', 'oyh'] + (['oyu'] if high and axis == 'y' else [])
                coordinates = [axis+'f', 'xl' if axis == 'x' else 'yh']
                if high:
                    coordinates += ['xh' if axis == 'x' else 'yu']
                points = (1, 2) if paired else (2,)
                fields = [f'vl_{field}+{point}' for point in points for field in coordinates]
                guarded = [f'vl_{field}+{point}' for field in planes for point in range(4)
                           if f'vl_{field}+{point}' not in fields]
                setup = ''.join(f' lda #{base >> (index % len(coordinates) * 8) & 255}\n sta {field}\n'
                                for index, field in enumerate(fields))
                guard = ''.join(f' lda {field}\n cmp #60\n beq :+\n jmp fail\n:\n'
                                for field in guarded)
                dirty = ' lda #60\n' + ''.join(f' sta {field}\n' for field in guarded)
                extra = ''
                if aliases:
                    extra = 'vl_val=$3000\nvl_w2=$3004\n'
                    extra += ''.join(f'vl_{field}=${0x3ff + index * 0x100:04x}\n'
                                     for index, field in enumerate(planes))
                variable = 'mul_p1' if paired else 'vl_val'
                upper = 'mul_p2' if paired else 'vl_val+1'
                returned = ['returned_a', 'returned_x', 'returned_y', 'returned_flags']
                copy = ''.join(f' lda {field}\n sta results+{index*256},x\n'
                               for index, field in enumerate(fields + returned))
                code = ('_VL_CORR_'+axis.upper()+'\n rts' if paired else
                        'jmp vl_sub_'+axis+'v')
                text = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=4
VL_NCON=1
''' + extra + ('VL_Y_HIGH=1\n' if high and axis == 'y' else '') + \
                    ('VL_CON_FAST=1\n' if paired else '') + '''.include "verlet.inc"
.zeropage
input:.res 2
returned_a:.res 1
returned_x:.res 1
returned_y:.res 1
returned_flags:.res 1
saved_hw:.res 1
check_flags:.res 1
.code
start:
 sei
 cld
 lda #0
 sta input
 sta input+1
''' + dirty + (''' lda #1
 sta vl_ca
 lda #2
 sta vl_cb
''' if paired else '') + '''loop:
''' + setup + f''' lda input
 sta {variable}
 lda input+1
 sta {upper}
 lda #$a5
 sta vl_w2
 lda input
 and #1
 beq allow_irq
 sei
 bne invoke
allow_irq:cli
invoke:
 tsx
 stx saved_hw
 ldx #2
 ldy #$79
 jsr kernel_start
 sta returned_a
 stx returned_x
 sty returned_y
 php
 pla
 sta returned_flags
 and #$0c
 sta check_flags
 lda input
 and #1
 asl
 asl
 cmp check_flags
 beq :+
 jmp fail
:tsx
 cpx saved_hw
 beq :+
 jmp fail
:
''' + guard + ''' ldx input
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
.include "verlet_con.asm"
kernel_start:
''' + code + '''
.include "verlet.asm"
kernel_end:
.bss
results:.res ''' + str((len(fields)+4)*256) + '''
.export start,page_done,resume,done,results,kernel_start,kernel_end
'''
                labels, binary = build(target, text, include)
                disk = a2test.build_disk(target, 'TEST', binary) if iie else None
                steps = a2test.bin_steps(binary)
                for _ in range(256):
                    steps += [labels.until('page_done'), labels.peek('results', (len(fields)+4)*256),
                              labels.until('resume')]
                steps += [labels.until('done'), f'peek:6000:{binary.stat().st_size}']
                result = a2test.run(disk, steps, iie=iie, timeout=180)
                assert result.dumps[-1] == binary.read_bytes(), ('code guard', name)
                digest = hashlib.sha256()
                width = len(coordinates)
                mask = (1 << (8*width)) - 1
                for hi, have in enumerate(result.dumps[:256]):
                    for lo in range(256):
                        bits = hi*256+lo
                        signed = bits if bits < 32768 else bits-65536
                        expected = [((base+signed) & mask), ((base-signed) & mask)] if paired else [((base-signed) & mask)]
                        for point, value in enumerate(expected):
                            for byte in range(width):
                                assert have[(point*width+byte)*256+lo] == value >> (byte*8) & 255, (name, bits, point, byte)
                        # The final operation is the high-byte subtraction.
                        final = expected[-1] >> ((width-1)*8) & 255
                        sign = 255 if signed < 0 else 0
                        borrow = int((base & 65535) < (bits & 65535))
                        old_high = base >> ((width-1)*8) & 255
                        operand = sign if width == 3 else hi
                        if width == 2:
                            borrow = int((base & 255) < lo)
                        carry = int(old_high >= operand+borrow)
                        overflow = int(bool((old_high ^ operand) & (old_high ^ final) & 128))
                        flags = (final & 128) | (overflow << 6) | ((lo & 1) << 2) | (int(final == 0) << 1) | carry
                        got = bytes(have[(len(fields)+index)*256+lo] for index in range(4))
                        assert got[0] == final and got[1] == 2, ('A/X', name, bits, got)
                        expected_y = sign if high else 0x79
                        assert got[2] == expected_y, ('Y', name, bits, got)
                        assert got[3] & 0xcf == flags, ('NZCV/I/D', name, bits, got[3], flags)
                    digest.update(have)
                report[name] = dict(cases=65536, kernel_bytes=labels['kernel_end']-labels['kernel_start'],
                                    binary_bytes=binary.stat().st_size,
                                    snapshot_sha256=digest.hexdigest())
                print(name, '65536 exact moves / A/X/Y/NZCV / I/D / stack / point+code guards', flush=True)
    return report


def squared_distances(work, include, iie):
    report = {}
    for fast in (False, True):
        for gain in (None, 0, 2, 6, 8):
            variants = gain in (None, 0, 6)
            name = f'fast{int(fast)}_gain{gain}_variants{int(variants)}'
            target = work / name
            target.mkdir()
            text = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=2
VL_NCON=''' + ('2\nVL_CON_VARIANTS=2' if variants else '1') + '''
VL_PIN=1
VL_CON_MINLEN_POINT=1
VL_CON_MINLEN=32768
VL_CON_SKIP_ZERO=1
''' + ('VL_CON_FAST=1\n' if fast else '') + \
                (f'VL_CON_FIXED_K={gain}\n' if gain is not None else '') + '''.include "verlet.inc"
.zeropage
qx:.res 1
qy:.res 1
saved_hw:.res 1
.code
start:
 sei
 cld
 jsr mul_init
 lda #0
 sta qx
 sta qy
 sta vl_cur
 sta vl_xf
 sta vl_xl
 sta vl_yf
 sta vl_yh
 lda #1
 sta vl_pin
 sta vl_pin+1
row:
'''
            for axis, q in (('x', 'qx'), ('y', 'qy')):
                text += f' lda {q}\n' + ' asl\n'*6 + f' sta vl_{axis}f+1\n lda {q}\n lsr\n lsr\n sta vl_'+('xl' if axis == 'x' else 'yh')+'+1\n'
            for pattern in range(4):
                text += ' lda #0\n sta vl_squashed\n lda #$a5\n sta vl_w2\n'
                if variants:
                    text += f' lda qx\n and #1\n sta vl_cur\n asl\n ora #{pattern&1}\n tay\n lda #{pattern&1}\n sta vl_con_row\n'
                suffix = ',y' if variants else ''
                if pattern < 2:
                    text += f' lda #{255 if pattern else 0}\n sta vl_con_l2l{suffix}\n sta vl_con_l2h{suffix}\n'
                else:
                    for q, field in (('qx', 'vl_con_l2l'), ('qy', 'vl_con_l2h')):
                        text += f' lda {q}\n'+(' eor #255\n' if pattern == 3 else '')+f' sta {field}{suffix}\n'
                text += f''' tsx
 stx saved_hw
 jsr vl_constrain
 php
 pla
 and #$0c
 cmp #4
 beq :+
 jmp fail
:tsx
 cpx saved_hw
 beq :+
 jmp fail
:ldx qx
 lda vl_fcoef
 sta results+{pattern*512},x
 lda vl_squashed
 sta results+{pattern*512+256},x
'''
            text += ''' inc qx
 lda qx
 cmp #181
 beq page_done
 jmp row
page_done:nop
resume:
 lda #0
 sta qx
 inc qy
 lda qy
 cmp #181
 beq done
 jmp row
done:jmp done
fail:jmp fail
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
.rodata
vl_con_a:.byte 0,0
vl_con_b:.byte 1,1
vl_con_k8:.byte 127,127,127,127
.bss
vl_con_l2l:.res 4
vl_con_l2h:.res 4
results:.res 2048
.export start,page_done,resume,done,results
'''
            labels, binary = build(target, text, include)
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            steps = a2test.bin_steps(binary)
            for _ in range(181):
                steps += [labels.until('page_done'), labels.peek('results', 2048), labels.until('resume')]
            steps += [labels.until('done'), f'peek:6000:{binary.stat().st_size}']
            result = a2test.run(disk, steps, iie=iie, timeout=240)
            assert result.dumps[-1] == binary.read_bytes(), ('code/table guard', name)
            for y, have in enumerate(result.dumps[:181]):
                for x in range(181):
                    q2 = x*x+y*y
                    for pattern, l2 in enumerate((0, 65535, y*256+x, 65535-y*256-x)):
                        delta = q2-l2
                        if gain is None:
                            factor = max(-4095, min(4095, delta >> 3))*127 >> 8
                        else:
                            factor = (1 if delta >= 0 else -1)*(abs(delta) >> (11-gain))
                        factor = max(-127, min(127, factor)) & 255
                        assert have[pattern*512+x] == factor, (name, x, y, l2, 'factor')
                        assert have[pattern*512+256+x] == int(q2 < 32768), (name, x, y, 'squash')
            digest = hashlib.sha256()
            for have in result.dumps[:181]:
                for plane in range(8):
                    digest.update(have[plane*256:plane*256+181])
            report[name] = dict(cases=181*181*4, snapshot_sha256=digest.hexdigest())
            print(name, '131044 independent factors / MINLEN alarms / hardware stack / code+tables', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path, help='directory with saved physics assembly')
    parser.add_argument('--only', choices=('movements', 'squares'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    include = args.reference or DEV / 'lib/physics'
    report = dict(cpu='65C02' if args.iie else 'NMOS6502',
                  sources={name: hashlib.sha256((include / name).read_bytes()).hexdigest()
                           for name in ('verlet.asm', 'verlet_con.asm')})
    report['metadata'] = metadata(include / 'verlet_con.asm', args.iie)
    report['metadata']['test_sha256'] = identity(__file__)['sha256']
    report['metadata']['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='verlet-corrections-') as directory:
        work = Path(directory)
        if args.only != 'squares':
            report['movements'] = movements(work, include, args.iie)
        if args.only != 'movements':
            report['squares'] = squared_distances(work, include, args.iie)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
