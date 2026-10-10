#!/usr/bin/env python3
"""Reusable corridor kernel: all unsigned depths, coordinates and IRQ masks."""
from pathlib import Path
import sys
import tempfile
from test_hgr import DEV, run, a2test
from test_audio import load_tool

sys.path.insert(0,str(DEV/'bench'))
from corridor_projection import probe


def build(work, shift, centers, tables):
    source=work/'corridor.s'
    source.write_text(f'''PC_DEPTH_SHIFT = {shift}
PC_CENTER_X = {centers[0]}
PC_CENTER_Y = {centers[1]}
.include "corridor.asm"
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
    run(['ca65','-t','none','-I',DEV/'lib/perspective','-o',obj,source])
    run(['ca65','-t','none','-o',table_obj,table_source])
    run(['ld65','-C',cfg,'-Ln',labels,'-o',binary,obj,table_obj])
    return binary,a2test.labels(labels,strip=True)


def main():
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
        for shift in range(9):
            centers=(140,96)
            custom=tool.corridor_scales(span_x=224,span_y=180,focal=47,
                                        center_x=centers[0],center_y=centers[1])
            binary,labels=build(work,shift,centers,custom)
            stats=probe(work,labels,binary,centers=centers,shift=shift,sanitize=True)
            assert stats[0][-1]==131072
            print(f'Corridor shift={shift}: all 65536 distances, all valid spans/coordinates, '
                  'both IRQ masks, immutable tables and centered outputs OK')
        for centers in ((0,0),(255,255)):
            binary,labels=build(work,1,centers,tool.corridor_scales(
                span_x=0,span_y=0,center_x=centers[0],center_y=centers[1]))
            probe(work,labels,binary,centers=centers,sanitize=True)
        # Invalid compile-time settings fail early in ca65.
        for shift in (-1,9):
            try:build(work,shift,(128,80),tables)
            except RuntimeError:pass
            else:raise AssertionError('invalid depth shift assembled')
        for centers in ((-1,80),(256,80),(128,-1),(128,256)):
            try:build(work,1,centers,tables)
            except RuntimeError:pass
            else:raise AssertionError('invalid center assembled')
    print('Corridor: default tables preserved, custom cameras, extreme centers, '
          'zero spans and invalid configuration refusal OK')


if __name__=='__main__':
    main()
