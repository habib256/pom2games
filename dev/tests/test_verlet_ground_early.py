#!/usr/bin/env python3
"""Complete ground calls at far/near/wrapped boundaries, with alias fallbacks.

Ordinary worlds use the independent HeightMap model directly. Extreme worlds
first normalize the existing 16-bit ground row and signed 24-bit difference,
then use the same model; these extra cases preserve legacy overflow behavior.
Returned A/X/NZCV are recorded for reference comparisons. Y is scratch:
its near-path fingerprint is recorded separately from early-rejection values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
from test_hgr import DEV, run, a2test
from test_verlet_helpers import CONFIG
from test_verlet_ground_probes import identity, metadata
from verlet import Points, HeightMap, harness
from verlet.ground import normals


def verticals(work, include, iie):
    report = {}
    domains = [(False, 0, 0)] + [(True, base, anchor) for base, anchor in (
        (0, 0), (255, 1), (256, 1), (384, 1), (384, 2), (384, 127),
        (384, 128), (384, 255), (65535, 0), (65535, 127), (65535, 128), (65535, 255))]
    domains = [(*domain, 0, 2) for domain in domains]
    # Steep normals can contact just below FAR. They make the early bound
    # numerically observable, including its fractional boundary.
    domains += [(False, 0, 0, 127, 1), (False, 0, 0, -127, 1),
                (True, 384, 1, 127, 1), (True, 65535, 128, -127, 1)]
    for high, base, anchor, slope, probe in domains:
        slope_max = max(15, abs(slope))
        nx, ny = normals(slope_max, 2*probe)
        heights = [128]*256
        if slope:
            heights[128-probe], heights[128+probe] = (64, 191) if slope > 0 else (191, 64)
        name = f'high{int(high)}_base{base}_anchor{anchor}_slope{slope}'
        w=work/name
        w.mkdir(exist_ok=True)
        coords=['xf','xl','xh','yf','yh']+(['yu'] if high else [])+['oxf','oxl','oxh','oyf','oyh']+(['oyu'] if high else [])
        fields=['vl_'+p for p in coords]+['vl_gnd','vl_vt','vl_vt+1','returned_flags','vl_tptr','vl_tptr+1','vl_hgt','returned_a','returned_x','returned_p','returned_y']
        copy=''.join(f' lda {p}\n sta results+{i*256},x\n' for i,p in enumerate(fields))
        s=f'''MUL_TABLES=$0800
MUL_ACC=1
.include "math.inc"
VL_NPOINTS=1
VL_GROUND=1
VL_HEIGHTS=$2000
VL_PROBE={probe}
VL_SLOPE_MAX={slope_max}
VL_FAR=$2000
VL_RADIUS=$0600
VL_BOUNCE=64
'''+(f'VL_Y_HIGH=1\nVL_GROUND_BASE={base}\n' if high else '')+'''.include "verlet.inc"
.zeropage
input:.res 2
saved_hw:.res 1
returned_a:.res 1
returned_x:.res 1
returned_p:.res 1
returned_y:.res 1
returned_flags:.res 1
.code
start:
    sei
    ldx #255
    txs
    cld
    jsr mul_init
    lda #0
    sta input
    sta input+1
loop:
    lda #0
    sta vl_xf
    sta vl_xh
    sta vl_oxh
    lda #128
    sta vl_xl
    lda #$dd
    sta vl_oxf
    lda #$7e
    sta vl_oxl
    lda input
    sta vl_yf
    lda input+1
    sta vl_yh
'''+(f' lda #{anchor}\n sta vl_yu\n' if high else '')+''' sec
    lda input
    sbc #$37
    sta vl_oyf
    lda input+1
    sbc #1
    sta vl_oyh
'''+(f' lda #{anchor}\n sbc #0\n sta vl_oyu\n' if high else '')+''' lda #$5a
    sta vl_vt
    lda #$a5
    sta vl_vt+1
    lda input
    and #1
    beq irq
    sei
    bne invoke
irq:cli
invoke:
    tsx
    stx saved_hw
    ldx #0
    jsr vl_ground
    sta returned_a
    stx returned_x
    sty returned_y
    php
    pla
    sta returned_p
    and #$0c
    sta returned_flags
    tsx
    cpx saved_hw
    beq :+
    jmp fail
:ldx input
'''+copy+''' inc input
    beq page_done
    jmp loop
page_done:nop
resume:
    inc input+1
    beq done
    jmp loop
done:jmp done
fail:jmp fail
watch_far_setup:
    sei
    lda #0
    sta vl_yf
    sta vl_yh
'''+(' sta vl_yu\n' if high else '')+''' ldx #0
watch_far_begin:jsr vl_ground
watch_far_end:nop
    lda #0
    sta vl_yf
'''+(f' lda #{(128+base)&255}\n sta vl_yh\n lda #{((128+base)&65535)>>8}\n sta vl_yu\n' if high else ' lda #128\n sta vl_yh\n')+''' ldx #0
watch_touch_begin:jsr vl_ground
watch_touch_end:jmp watch_touch_end
.include "verlet_hmap.asm"
.include "verlet.asm"
.include "mul.asm"
.rodata
vl_norm_x:.byte '''+','.join(str(v&255) for v in nx)+'''
vl_norm_y:.byte '''+','.join(str(v&255) for v in ny)+f'''
.bss
results:.res {len(fields)*256}
.export start,page_done,resume,done,results,watch_far_setup,watch_far_begin,watch_far_end,watch_touch_begin,watch_touch_end
'''
        (w/'e.s').write_text(s)
        (w/'e.cfg').write_text(CONFIG)
        (w/'heights.bin').write_bytes(bytes(heights))
        run(['ca65','-I',include,'-I',DEV/'lib/physics','-I',DEV/'lib/math','-o',w/'e.o',w/'e.s'])
        run(['ld65','-C',w/'e.cfg','-Ln',w/'e.lbl','-o',w/'e.bin',w/'e.o'])
        L=a2test.labels(w/'e.lbl')
        binary=w/'e.bin'
        entry={}
        hm=HeightMap(heights, slope_max, probe, base=base if high else 0)
        expected=[]
        fars=[]
        normalized=0
        for n in range(65536):
            p=Points(1,y_high=high)
            p.x[0]=0x8000
            p.ox[0]=0x7edd
            y=n+(anchor<<16 if high else 0)
            if high and y&0x800000:y-=1<<24
            p.y[0]=y
            oy=(y-0x137)&((1<<(24 if high else 16))-1)
            if high and oy&0x800000:oy-=1<<24
            p.oy[0]=oy
            # Only overflow cases adjust the model's virtual ground row.
            # Ordinary worlds retain their original base exactly.
            ground=((base+128)&65535)<<8
            distance=ground-y
            if high:
                distance=(distance+(1<<23))%(1<<24)-(1<<23)
                hm.base=(y+distance)//256-128
            normalized += int(distance != ((base+128)<<8)-y)
            fars.append(distance >= 0x2000)
            vt=hm.contact(p,0)
            expected.append(p.soa_bytes()+bytes([int(vt is not None)])+((vt if vt is not None else 0xa55a)&65535).to_bytes(2,'little')+bytes([(n&1)*4,128,32,128]))
        disk=a2test.build_disk(w,'TEST',binary) if iie else None
        steps=a2test.bin_steps(binary)+[f'load:{w/"heights.bin"}@2000']
        for _ in range(256):steps += [L.until('page_done'),L.peek('results',len(fields)*256),L.until('resume')]
        steps += [L.until('done'),f'go:{L["watch_far_setup"]:04X}',L.until('watch_far_begin'),'hwstackwatch',L.until('watch_far_end'),'hwstack',L.until('watch_touch_begin'),'hwstackwatch',L.until('watch_touch_end'),'hwstack',f'peek:6000:{binary.stat().st_size}']
        r=a2test.run(disk,steps,iie=iie,timeout=240)
        assert r.dumps[-1]==binary.read_bytes(),('code',name,iie)
        digest=hashlib.sha256()
        near_y=hashlib.sha256()
        far_y=set()
        for hi,have in enumerate(r.dumps[:256]):
            for lo in range(256):
                actual=bytes(have[p*256+lo] for p in range(len(fields)))
                assert actual[:-4]==expected[hi*256+lo],(name,iie,hi*256+lo,actual.hex(),expected[hi*256+lo].hex())
                digest.update(actual[:-1])
                if fars[hi*256+lo]:far_y.add(actual[-1])
                else:near_y.update(actual[-1:])
        peaks=list(map(int,re.findall(r'hwstack peak=(\d+) available=',r.out)))
        assert peaks==[4,6],(name,peaks)
        entry={'cases':65536,'public_sha256':digest.hexdigest(),'hardware_peaks':peaks,'normalized_world_cases':normalized,'near_y_sha256':near_y.hexdigest(),'far_y_values':sorted(far_y),'binary_bytes':binary.stat().st_size}
        print(name,iie,'65536 model/ABI/code/pointer cases',peaks,flush=True)
        report[name]=entry
    return report


def alias_profiles(work, include, iie, supports_early):
    import test_verlet as model
    modes = {
        'default': ('', 'early'),
        'absolute': ('vl_w0=$3000\nvl_w1=$3001\nvl_w2=$3002\n', 'fallback'),
        'w0_hxl': ('vl_w0=vl_hxl\n', 'early'),
        'w1_hgt': ('vl_w1=vl_hgt\n', 'early'),
    }
    for slot in ('w0', 'w1', 'w2'):
        for sample in ('vl_hm2', 'vl_hp2', 'vl_tptr', 'vl_tptr+1', 'vl_nx', 'vl_ny'):
            # Normal aliases may violate older live ranges. They still must
            # choose fallback and remain byte-identical to a saved reference.
            behavior = 'legacy' if sample in ('vl_nx', 'vl_ny') else 'fallback'
            modes[slot+'_'+sample] = ('vl_'+slot+'='+sample+'\n', behavior)
    report = {}
    for high in (False, True):
        if high:
            prelude, epilogue = model.prelude3(), model.EPILOGUE3
            inputs, snapshots = model.INPUTS3, model.SNAPS3
            rows = [row for row in model.cases3(model.random.Random(11))
                    if model.OPS3[row[2]] == 'gnd'][::5][:60]
            script = [(1, list(row[0])+[int(v) for v in row[1]]+
                       [row[2], row[3], row[4], row[5], row[6], row[7]]+
                       model.le(row[8][0], 2)+model.le(row[8][1], 2), 1) for row in rows]
            expected = b''.join(model.model3(row) for row in rows)
        else:
            prelude, epilogue = model.prelude1(), model.EPILOGUE1
            inputs, snapshots = model.INPUTS1, model.SNAPS1
            rows = [row for row in model.cases(model.random.Random(7))
                    if model.OPS[row[1]] == 'gnd'][::7][:60]
            script = [(1, list(row[0])+[row[1], row[2], row[3], row[4], row[5],
                       row[6] & 255, row[6] >> 8, row[7], row[8]], 1) for row in rows]
            expected = b''.join(model.model1(row) for row in rows)
        for mode, (aliases, behavior) in modes.items():
            name = f'high{int(high)}_'+mode
            target = work / name
            target.mkdir()
            pre = prelude.replace('.include "verlet.inc"', aliases+'.include "verlet.inc"')
            text = harness.source(pre, epilogue, inputs, snapshots, script,
                                  init='mul_init', snap_seg='LOWBSS')
            text += '''
.if .defined(_VL_GROUND_DISTANCE_EARLY)
 .if _VL_GROUND_DISTANCE_EARLY
  early_selected=1
 .else
  early_selected=0
 .endif
.else
 early_selected=0
.endif
.export early_selected
'''
            points, binary = harness.build(target, text, includes=(include,))
            assert points['early_selected'] == int(supports_early and behavior == 'early'), name
            disk = a2test.build_disk(target, 'TEST', binary) if iie else None
            result = a2test.run(disk, a2test.bin_steps(binary)+[
                points.until('hs_done', 60000), points.peek('hs_snaps', len(expected))], iie=iie)
            if behavior != 'legacy':
                assert result.data == expected, ('alias model', name)
            report[name] = dict(cases=len(rows), behavior=behavior,
                                early=points['early_selected'], binary=identity(binary),
                                binary_bytes=binary.stat().st_size,
                                public_sha256=hashlib.sha256(result.data).hexdigest())
            print(name, behavior, 'selected; public states recorded', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--reference', type=Path, help='saved verlet_hmap.asm source')
    parser.add_argument('--compare', type=Path, help='also compare alias code/state with this saved source')
    parser.add_argument('--only', choices=('verticals', 'aliases'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    source = args.reference or DEV / 'lib/physics/verlet_hmap.asm'
    text = source.read_text()
    report = dict(cpu='65C02' if args.iie else 'NMOS6502', metadata=metadata(source, args.iie))
    report['metadata'].pop('probe_config_sha256', None)
    report['metadata']['test_sha256'] = identity(__file__)['sha256']
    report['metadata']['fixture_config_sha256'] = hashlib.sha256(CONFIG.encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='verlet-ground-early-') as directory:
        work = Path(directory)
        include = work / 'selected'
        include.mkdir()
        (include / 'verlet_hmap.asm').write_text(text)
        if args.only != 'aliases':
            report['verticals'] = verticals(work, include, args.iie)
        if args.only != 'verticals':
            target = work / 'aliases'
            target.mkdir()
            report['aliases'] = alias_profiles(target, include, args.iie,
                                                '_VL_GROUND_DISTANCE_EARLY' in text)
            if args.compare:
                compare = work / 'reference'
                compare.mkdir()
                reference = args.compare.read_text()
                (compare / 'verlet_hmap.asm').write_text(reference)
                target = work / 'reference-aliases'
                target.mkdir()
                previous = alias_profiles(target, compare, args.iie,
                                          '_VL_GROUND_DISTANCE_EARLY' in reference)
                for name, current in report['aliases'].items():
                    assert current['public_sha256'] == previous[name]['public_sha256'], ('reference states', name)
                    if current['behavior'] != 'early':
                        assert current['binary'] == previous[name]['binary'], ('fallback bytes', name)
                report['reference_aliases'] = previous
                report['reference_source'] = identity(args.compare)
    if args.out:
        args.out.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
