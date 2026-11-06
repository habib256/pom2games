#!/usr/bin/env python3
"""Reusable corridor kernel: all unsigned depths, coordinates and IRQ masks."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from test_hgr import DEV, run, a2test
from test_audio import load_tool

sys.path.insert(0,str(DEV/'bench'))
from corridor_projection import probe


def build(work, shift, centers, tables, *, kernel=None, aliases=None):
    source=work/'corridor.s'
    configuration=''.join(f'PC_{name} = {address}\n' for name,address in (aliases or {}).items())
    selected=Path(kernel or DEV/'lib/perspective/corridor.asm')
    (work/'selected_corridor.asm').write_bytes(selected.read_bytes())
    include='selected_corridor.asm'
    source.write_text(configuration+f'''PC_DEPTH_SHIFT = {shift}
PC_CENTER_X = {centers[0]}
PC_CENTER_Y = {centers[1]}
.include "{include}"
.export PC_BITS
.export _project_x, _project_y, _perspective
.export _sx, _sy, _left, _top, _depth, _scale_x, _scale_y
_project_x = _a2_corridor_x
_project_y = _a2_corridor_y
_perspective = _a2_corridor_select
_sx = _a2_corridor_sx
_sy = _a2_corridor_sy
_left = _a2_corridor_left
_top = _a2_corridor_top
_depth = _a2_corridor_depth
_scale_x = _corridor_scale_x
_scale_y = _corridor_scale_y
''')
    table_source=work/'tables.s'
    table_source.write_text('''.export _corridor_scale_x, _corridor_scale_y
.segment "RODATA"
_corridor_scale_x:
'''+'    .byte '+','.join(map(str,tables[0]))+'\n_corridor_scale_y:\n'+
        '    .byte '+','.join(map(str,tables[1]))+'\n')
    cfg=work/'corridor.cfg'
    cfg.write_text('''MEMORY { ZP: start=$50,size=$B0,type=rw;
RAM: start=$6000,size=$3600,type=rw,file=%O; }
SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE: load=RAM,type=ro;
RODATA: load=RAM,type=ro; BSS: load=RAM,type=bss; }
''')
    obj,binary,labels=work/'corridor.o',work/'corridor.bin',work/'corridor.lbl'
    table_obj=work/'tables.o'
    run(['ca65','-t','none','-I',work,'-I',selected.parent,'-o',obj,source])
    run(['ca65','-t','none','-o',table_obj,table_source])
    run(['ld65','-C',cfg,'-Ln',labels,'-o',binary,obj,table_obj])
    return binary,a2test.labels(labels,strip=True)


def guarded(work, source, reference, tables):
    """Guard independently linked scratch layouts on both physical CPU models."""
    executable=work/'guard-probe'
    run(['make','-s','-C',DEV/'tools/a2shot','probe',
         'SRC='+str(DEV/'bench/corridor_guard_probe.cpp'),'OUT='+str(executable)])
    profiles={}
    for layout in ('default','zp','bss','mixed'):
        aliases={}
        if layout!='default':
            aliases['BITS']=0x80 if layout in ('zp','mixed') else 0x1101
            base=0x90 if layout=='zp' else 0x1201
            aliases.update({name:base+i*3 for i,name in enumerate(('SX','SY','LEFT','TOP','DEPTH'))})
        for shift in (1,8):
            directories=[]
            sizes={}
            for version,kernel in (('before',reference),('after',source)):
                directory=work/(layout+'-shift'+str(shift)+'-'+version);directory.mkdir()
                binary,_=build(directory,shift,(128,80),tables,kernel=kernel,aliases=aliases)
                directories.append(directory);sizes[version]=binary.stat().st_size
            for cpu in (0,1):
                before,after=directories
                output=run([executable,before/'corridor.bin',before/'corridor.lbl',
                            after/'corridor.bin',after/'corridor.lbl',cpu,shift,128,80])
                print(layout,output.strip())
                profiles[layout+('' if shift==1 else '_shift8')+('-65c02' if cpu else '-nmos')]=dict(binary_bytes=sizes,proof=output.strip())
    return profiles


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,help='test this corridor.asm instead of production')
    parser.add_argument('--reference',help='git revision or source file for guarded comparison')
    parser.add_argument('--guarded',action='store_true',help='add SDK NMOS/65C02 full-state, alias and RAM guards')
    parser.add_argument('--out',type=Path,help='write guarded proof and source/environment identities')
    args=parser.parse_args()
    source=(args.source or DEV/'lib/perspective/corridor.asm').resolve()
    tool=load_tool('perspective',DEV/'tools/perspective.py')
    tables=tool.corridor_scales()
    assert tables==([252*32//(32+d) for d in range(256)],
                    [148*32//(32+d) for d in range(256)])
    for kwargs in (dict(focal=0),dict(span_x=256),dict(center_y=-1),
                   dict(center_x=0,span_x=252),dict(center_y=255,span_y=148)):
        try:tool.corridor_scales(**kwargs)
        except ValueError:pass
        else:raise AssertionError(kwargs)
    with tempfile.TemporaryDirectory(prefix='pom2-corridor-') as temp:
        work=Path(temp)
        reference=source
        if args.reference:
            path=Path(args.reference)
            if path.is_file():reference=path.resolve()
            else:
                reference=work/'reference.asm'
                reference.write_bytes(subprocess.check_output(
                    ['git','show',args.reference+':dev/lib/perspective/corridor.asm'],cwd=DEV.parent))
        for shift in range(9):
            centers=(140,96)
            custom=tool.corridor_scales(span_x=224,span_y=180,focal=47,
                                        center_x=centers[0],center_y=centers[1])
            binary,labels=build(work,shift,centers,custom,kernel=source)
            stats=probe(work,labels,binary,centers=centers,shift=shift,sanitize=True)
            assert stats[0][-1]==131072
            print(f'Corridor shift={shift}: all 65536 distances, all valid spans/coordinates, '
                  'both IRQ masks, immutable tables and centered outputs OK')
        for centers in ((0,0),(255,255)):
            binary,labels=build(work,1,centers,tool.corridor_scales(
                span_x=0,span_y=0,center_x=centers[0],center_y=centers[1]),kernel=source)
            probe(work,labels,binary,centers=centers,sanitize=True)
        # Invalid compile-time settings fail early in ca65.
        for shift in (-1,9):
            try:build(work,shift,(128,80),tables,kernel=source)
            except RuntimeError:pass
            else:raise AssertionError('invalid depth shift assembled')
        for centers in ((-1,80),(256,80),(128,-1),(128,256)):
            try:build(work,1,centers,tables,kernel=source)
            except RuntimeError:pass
            else:raise AssertionError('invalid center assembled')
        results=guarded(work,source,reference,tables) if args.guarded else {}
        if args.out:
            digest=lambda path:dict(name=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
            host={'Darwin-arm64':'darwin-arm64','Linux-x86_64':'linux-x86_64'}[platform.system()+'-'+platform.machine()]
            sdk=DEV/'tools/a2shot/sdk/lib'/host/'libpom2_core.a'
            version=subprocess.run(['ca65','--version'],text=True,capture_output=True,check=True)
            report=dict(schema=1,compiler=(version.stdout+version.stderr).strip(),
                        flags='ca65 -t none; C probe -O2 ASan/UBSan; SDK probe -std=c++17 -O2',
                        source=digest(source),reference=digest(reference),test_source=digest(__file__),
                        support_sources=[digest(DEV/'bench/corridor_guard_probe.cpp'),
                                         digest(DEV/'bench/corridor_probe.c'),digest(DEV/'tools/a2run/cpu6502.c'),
                                         digest(DEV/'tools/a2shot/probe.hpp')],
                        sdk=dict(archive=digest(sdk),header=digest(DEV/'tools/a2shot/sdk/include/pom2/core.hpp'),
                                 cpus=['NMOS6502','65C02'],memory='custom IIe 128K, no ROM'),results=results)
            args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('Corridor: default tables preserved, custom cameras, extreme centers, '
          'zero spans and invalid configuration refusal OK')


if __name__=='__main__':
    main()
