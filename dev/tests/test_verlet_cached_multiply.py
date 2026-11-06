#!/usr/bin/env python3
"""Prepared FAST-axis products: exact link fallbacks and native multiplication.

The baseline uses the ordinary signed entry. Candidate/reference sources keep
all other library members fixed. Independent integer/ABI/store guards reuse
the existing math pointer probe on both CPUs, including cached-setter and
reinitialization transitions. Link profiles protect both pointer lows and the
operand across every product/correction store; unsafe profiles must retain
identical target bytes. --negative proves guard and arithmetic fault detection.
"""
import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path
import re
import subprocess
import tempfile

from test_hgr import DEV, ROOT, run, a2test
import test_math_pointer_alias as math_test

CALL = 'JSR     mul_s16s8 + (mul_s16s8_ready - mul_s16s8) * _VL_CON_MUL_CACHE_SAFE'
CONFIG = '''MEMORY { ZP:start=$50,size=$b0,type=rw;
RAM:start=$6000,size=$3000,file=%O; }
SEGMENTS { ZEROPAGE:load=ZP,type=zp; CODE:load=RAM,type=ro;
RODATA:load=RAM,type=ro; BSS:load=RAM,type=bss; }
'''
profiles=[]
def add(name,math='',physics='',heavy=False,fast=True,shared=False,safe=False):profiles.append((name,math,physics,heavy,fast,shared,safe))
add('default',safe=True);add('heavy',heavy=True,safe=True);add('shared',shared=True,safe=True);add('nonfast',fast=False)
add('coalesced_s1l','mul_y=mul_s1l\n',safe=True);add('coalesced_s1h','mul_y=mul_s1h\n',safe=True)
add('absolute_operand','mul_y=$3000\n',safe=True)
for y in ('mul_s2l','mul_s2h','mul_p0','mul_p1','mul_p2','mul_x','mul_x+1','$100','$1FE','$C000','$D000'):
 add('operand_'+y.replace('$','').replace('+','_'),'mul_y='+y+'\n')
for pointer in ('mul_s1l','mul_s1h','mul_s2l','mul_s2h'):
 for product in ('mul_p0','mul_p1','mul_p2'):add(product+'_'+pointer,product+'='+pointer+'\n')
 for offset in (0,-1):add('mulx_'+pointer+str(offset),'mul_x='+pointer+('' if not offset else '-1')+'\n')
 for array in ('vl_xf','vl_xl','vl_xh'):add(array+'_'+pointer,physics=array+'='+pointer+'\n')
 for temporary in ('vl_val','vl_vn','vl_pen'):
  for offset in (0,-1):add(temporary+'_'+pointer+str(offset),physics=temporary+'='+pointer+('' if not offset else '-1')+'\n',heavy=True)
for array in ('vl_xf','vl_xl','vl_xh'):
 for address in ('$F0','$FF80','$FFFF'):add(array+'_'+address,physics=array+'='+address+'\n')
 add(array+'_operand_absolute','mul_y=$3080\n',array+'=$3000\n')
for temporary in ('vl_val','vl_vn','vl_pen'):
 for offset in (0,-1):add(temporary+'_operand'+str(offset),'mul_y=$70\n',temporary+'=mul_y'+('' if not offset else '-1')+'\n',heavy=True)


def alias_build(work, kernels, profile, phase):
    name, math, physics, heavy, fast, shared, safe = profile
    work.mkdir()
    for member, text in kernels[phase].items():
        (work/member).write_text(text)
    source = math+'''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=4
VL_NCON=1
'''+('VL_CON_FAST=1\n' if fast else '')+('VL_CON_HEAVY_POINT=2\nVL_CON_HEAVY_SHIFT=2\n' if heavy else '')+physics+'''.include "verlet.inc"
.code
entry:ldx #0
jsr vl_constrain
rts
.rodata
vl_con_a:.byte 0
vl_con_b:.byte 1
vl_con_l2l:.byte 100
vl_con_l2h:.byte 0
vl_con_k8:.byte 128
'''+('.word mul_u16u8\n' if shared else '')+'''.code
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
.export entry,mul_s16s8
'''+('.export _VL_CON_MUL_CACHE_SAFE,mul_s16s8_ready\n' if fast and phase=='after' else '')
    (work/'f.s').write_text(source)
    (work/'f.cfg').write_text(CONFIG)
    run(['ca65', '-I', work, '-I', DEV/'lib/math', '-I', DEV/'lib/physics',
         '-o', work/'f.o', work/'f.s'])
    run(['ld65', '-C', work/'f.cfg', '-m', work/'f.map', '-Ln', work/'f.lbl',
         '-o', work/'f.bin', work/'f.o'])
    return (work/'f.bin').read_bytes(), a2test.labels(work/'f.lbl')


def aliases(work, kernels, selected=profiles):
    results = {}
    for profile in selected:
        name, _, _, _, fast, shared, safe = profile
        old, _ = alias_build(work/(name+'-before'), kernels, profile, 'before')
        new, labels = alias_build(work/(name+'-after'), kernels, profile, 'after')
        assert len(old)==len(new), (name, 'footprint grew')
        if fast:
            assert labels['_VL_CON_MUL_CACHE_SAFE']==int(safe), (name, 'wrong alias choice')
        if not safe or not fast or shared:
            assert old==new, (name, 'fallback bytes changed')
        else:
            assert labels['mul_s16s8_ready']>labels['mul_s16s8']
            assert 0<sum(x!=y for x,y in zip(old,new))<=2, (name, 'only JSR operand may change')
            normal, ready = labels['mul_s16s8'], labels['mul_s16s8_ready']
            calls = [at for at in range(len(old)-2) if old[at]==new[at]==0x20
                     and old[at+1] | (old[at+2]<<8)==normal
                     and new[at+1] | (new[at+2]<<8)==ready]
            assert len(calls)==1, (name, 'resolved JSR target')
            assert all(x==y for at,(x,y) in enumerate(zip(old,new))
                       if at not in (calls[0]+1,calls[0]+2))
        results[name] = dict(cache_safe=safe, shared=shared, fast=fast,
                             identical=old==new, binary_bytes=len(new),
                             before_sha256=hashlib.sha256(old).hexdigest(),
                             after_sha256=hashlib.sha256(new).hexdigest())
    return results



def standalone_helpers(work, kernels):
    results = {}
    for name, options in (
        ('square_fast', ''),
        ('square_unused_heavy', 'VL_CON_HEAVY_POINT=0\n'),
        ('square_unused_constraints', 'VL_NCON=1\nVL_CON_HEAVY_POINT=0\n')):
        binaries = {}
        for phase in ('before','after'):
            target = work/(name+'-'+phase)
            target.mkdir()
            for member,text in kernels[phase].items():
                (target/member).write_text(text)
            source = '''MUL_TABLES=$0800
.include "math.inc"
VL_NPOINTS=1
VL_CON_FAST=1
'''+options+'''.include "verlet.inc"
.code
entry:lda #5
jsr vl_square
rts
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
'''
            (target/'f.s').write_text(source)
            (target/'f.cfg').write_text(CONFIG)
            run(['ca65','-I',target,'-I',DEV/'lib/math','-I',DEV/'lib/physics',
                 '-o',target/'f.o',target/'f.s'])
            run(['ld65','-C',target/'f.cfg','-o',target/'f.bin',target/'f.o'])
            binaries[phase]=(target/'f.bin').read_bytes()
        assert binaries['before']==binaries['after'], (name,'unused options changed helper')
        results[name]=dict(binary_bytes=len(binaries['after']),
            sha256=hashlib.sha256(binaries['after']).hexdigest())
    return results


def prepared_build(work, kernel, layout, kind, prepared):
    math_test.build(work, kernel.encode(), layout, kind)
    target = 'mul_s16s8_ready' if prepared else 'mul_s16s8'
    source = (work/'f.s').read_text()
    assert 'entry=mul_s16s8' in source
    # Both callers explicitly prepare the pointers. The reference then calls
    # the ordinary entry; the candidate may omit that redundant second setup.
    source = source.replace('entry=mul_s16s8', 'entry:\n MUL_SET_POINTERS\n jmp '+target)
    (work/'f.s').write_text(source)
    run(['ca65', '-I', work, '-I', DEV/'lib/math', '-o', work/'f.o', work/'f.s'])
    run(['ld65', '-C', work/'f.cfg', '-Ln', work/'f.lbl', '-o', work/'f.bin', work/'f.o'])
    return (work/'f.bin').read_bytes()


def native(work, executable, kernels):
    results = {}
    for layout in math_test.LAYOUTS:
        for kind in ('inline', 'shared'):
            name = layout+'_'+kind
            before, after = work/(name+'-before'), work/(name+'-after')
            old = prepared_build(before, kernels['before']['mul.asm'], layout, kind, False)
            new = prepared_build(after, kernels['after']['mul.asm'], layout, kind, True)
            assert len(old)==len(new), name
            if kind=='shared':
                assert old==new, (name, 'shared linkage must keep ordinary entry')
            result = dict(binary_bytes=len(new), cpus={})
            for cpu, label in ((0, 'NMOS6502'), (1, 'CMOS65C02')):
                proof = run([executable, before/'f.bin', before/'f.lbl', after/'f.bin',
                             after/'f.lbl', cpu, 2, int(layout=='coalesced')]).strip()
                assert '/0 slower)' in proof, proof
                result['cpus'][label] = proof
                print(name, proof, flush=True)
            results[name] = result
    return results


def negative_controls(work, executable, kernels):
    results = []
    controls = (
        ('product_low', ' .and _VL_CACHE_P0', '', 'mul_p0_mul_s1l'),
        ('complement_operand', '(mul_y <> mul_s2l)', '1', 'operand_mul_s2l'),
        ('operand_store', 'operand = ((mul_y - first) & $FFFF) >= count',
         'operand = 1', 'vl_xf_operand_absolute'),
        ('zp_wrap', '(first >= minimum)', '1', 'vl_xf_$F0'),
        ('absolute_wrap', '_VL_CACHE_XF, vl_xf, 256, 256',
         '_VL_CACHE_XF, vl_xf, 4, 256', 'vl_xf_$FF80'),
        ('stack_operand', '((mul_y < $100) .or (mul_y >= $200))', '1', 'operand_1FE'),
    )
    for name, old, new, profile_name in controls:
        selected = [p for p in profiles if p[0]==profile_name]
        assert len(selected)==1
        mutant = {phase:dict(members) for phase,members in kernels.items()}
        text = mutant['after']['verlet_con.asm']
        assert old in text, name
        mutant['after']['verlet_con.asm'] = text.replace(old,new,1)
        try:
            aliases(work, mutant, [(name+'_'+selected[0][0], *selected[0][1:])])
        except AssertionError:
            results.append(dict(name=name, rejected=True))
        else:
            raise AssertionError((name, 'guard fault escaped'))
        print('Cached product negative:', name, 'rejected', flush=True)
    # Move the private entry past its initial LDY/SEC. This must fail the
    # independent integer/register oracle, rather than only the byte guard.
    old = '''        .if .paramcount
ready:
        .endif
        LDY     mul_x+1
        SEC'''
    new = '''        LDY     mul_x+1
        SEC
        .if .paramcount
ready:
        .endif'''
    assert old in kernels['after']['mul.asm']
    before, after = work/'wrong_entry_before', work/'wrong_entry_after'
    prepared_build(before, kernels['before']['mul.asm'], 'coalesced', 'inline', False)
    prepared_build(after, kernels['after']['mul.asm'].replace(old,new,1), 'coalesced', 'inline', True)
    for cpu in (0,1):
        result = subprocess.run([str(x) for x in [executable, before/'f.bin', before/'f.lbl',
            after/'f.bin', after/'f.lbl', cpu, 2, 0]], capture_output=True, text=True)
        assert result.returncode!=0 and 'assert' in result.stderr.lower(), result.stderr
    results.append(dict(name='wrong_prepared_entry', rejected=True, cpus=2))
    print('Cached product negative: wrong prepared entry rejected on both CPUs', flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mul-source', type=Path, default=DEV/'lib/math/mul.asm')
    parser.add_argument('--con-source', type=Path, default=DEV/'lib/physics/verlet_con.asm')
    parser.add_argument('--reference', help='git revision for exact paired source comparison')
    parser.add_argument('--negative', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    selected = {'mul.asm':args.mul_source.read_text(),
                'verlet_con.asm':args.con_source.read_text()}
    if args.reference:
        reference = {}
        for member,family in (('mul.asm','math'),('verlet_con.asm','physics')):
            reference[member] = subprocess.run(['git','-C',str(ROOT),'show',
                args.reference+':dev/lib/'+family+'/'+member], check=True,
                capture_output=True, text=True).stdout
    else:
        assert CALL in selected['verlet_con.asm']
        reference = dict(selected)
        reference['verlet_con.asm'] = reference['verlet_con.asm'].replace(CALL, 'JSR     mul_s16s8')
    kernels = dict(before=reference, after=selected)
    report = dict(metadata=math_test.metadata(args.mul_source,True), sources={
        phase:{name:hashlib.sha256(text.encode()).hexdigest() for name,text in members.items()}
        for phase,members in kernels.items()})
    report['metadata']['test_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['metadata']['environment']['model'] = 'SDK NMOS6502 and CMOS65C02, direct RAM calls'
    report['metadata'].pop('probe_config_sha256')
    report['metadata']['native_compiler'] = subprocess.run(
        [*shlex.split(os.environ.get('CXX','c++')), '--version'], check=True,
        capture_output=True, text=True).stdout.strip()
    report['metadata']['native_flags'] = '-std=c++17 -O2; dev/tools/a2shot/sdk.mk'
    report['config_sha256'] = dict(alias=hashlib.sha256(CONFIG.encode()).hexdigest(),
        prepared=hashlib.sha256(math_test.CONFIG.encode()).hexdigest())
    report['support_sources'] = [math_test.identity(DEV/p) for p in (
        'bench/math_pointer_alias_probe.cpp','tests/test_math_pointer_alias.py',
        'lib/math/math.inc','lib/physics/verlet.inc','lib/physics/verlet.asm')]
    with tempfile.TemporaryDirectory(prefix='verlet-cached-multiply-') as directory:
        work = Path(directory)
        executable = work/'probe'
        run(['make','-s','-C',DEV/'tools/a2shot','probe',
             'SRC='+str(DEV/'bench/math_pointer_alias_probe.cpp'),'OUT='+str(executable)])
        report['alias_profiles'] = aliases(work,kernels)
        report['standalone_profiles'] = standalone_helpers(work,kernels)
        report['native_profiles'] = native(work,executable,kernels)
        if args.negative:
            report['negative_controls'] = negative_controls(work,executable,kernels)
    if args.out:
        args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('92 alias/link + 3 standalone profiles; 10 prepared profiles on both CPUs: PASS')


if __name__=='__main__':
    main()
