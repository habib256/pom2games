#!/usr/bin/env python3
"""Evaluate pinned HGR techniques on the real NMOS 6502 in a2run.

All prototypes live here, outside dev/lib. No network access is needed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
DEV = HERE.parents[1]
ROOT = DEV.parent
sys.path.insert(0, str(DEV / 'tests'))
from test_hgr import build, run
_spec = importlib.util.spec_from_file_location('hgr_metrics', DEV/'bench/run.py')
_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_metrics)
segments = _metrics.segments
from merlin import translate
import a2test


def compile_asm(work, name, text):
    src = work / (name + '.s')
    src.write_text(text)
    obj = src.with_suffix('.o')
    run(['ca65', '-t', 'none', '-o', obj, src])
    return obj


def execute(work, name, source, objects=(), extra_disk=(), pad_binary=0):
    """Time a complete C call, then verify both full pages, including holes."""
    src = work / (name + '.c')
    src.write_text(source)
    obj, binary = src.with_suffix('.o'), src.with_suffix('.bin')
    run(['cl65', '-t', 'none', '-Oirs', '-I', DEV / 'lib/hgrc',
         '-I', DEV / 'lib/apple2c', '-I', DEV / 'lib/gfx', '-c', '-o', obj, src])
    mapfile, labels = src.with_suffix('.map'), src.with_suffix('.lbl')
    run(['cl65', '-t', 'none', '-C', work / 'bench.cfg', '-m', mapfile,
         '-Ln', labels, '-o', binary, work / 'crt0_apple2.o', obj,
         work / 'markers.o', *objects, work / 'hgrc.lib'])
    if pad_binary:
        assert binary.stat().st_size <= pad_binary
        binary.write_bytes(binary.read_bytes().ljust(pad_binary,b'\0'))
    points = a2test.labels(labels)
    disk = a2test.build_disk(work, name.upper()[:28], binary, extra=extra_disk)
    result = a2test.run(disk, [points.until('_bench_begin'), points.until('_bench_end'),
                              'peek:2000:16384'])
    assert len(result.cycles) == 2, name
    metrics = dict(segments(mapfile), binary_bytes=binary.stat().st_size,
                   cycles=result.cycles[1] - result.cycles[0] - 12)
    if objects:
        section = mapfile.read_text().split('Segment list:')[1].split('Exports list')[0]
        match = re.search(r'^FDRAW\s+\w+\s+\w+\s+(\w+)', section, re.M)
        if match:
            metrics['fdraw_package_bytes'] = int(match[1], 16)
            metrics['code_bytes'] += metrics['fdraw_package_bytes']
    return metrics, result.mem(0x2000, 16384)


def c_fixture(body, setup='', extra='', page=1, background=0):
    return ('#include "hgr.h"\n#include "hgr_internal.h"\n#include "gfx.h"\n'
            'void bench_begin(void); void bench_end(void);\n' + extra +
            '\nint main(void) {\n'
            f'hgr_init(); hgr_set_draw_page(1); hgr_clear({background}); '
            f'hgr_set_draw_page(2); hgr_clear({background}); hgr_set_draw_page({page});\n' +
            setup + '\nbench_begin();\n' + body +
            '\nbench_end(); for (;;) {} return 0; }\n')


FD_DECL = '''
extern unsigned char fd_arg, fd_x0l, fd_x0h, fd_y0, fd_x1l, fd_x1h, fd_y1;
void fd_init(void); void fd_color(void); void fd_page(void);
void fd_drawline(void); void fd_fillrect(void); void fd_clear(void);
void fd_line(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1) {
    fd_x0l=(unsigned char)x0; fd_x0h=(unsigned char)(x0>>8); fd_y0=y0;
    fd_x1l=(unsigned char)x1; fd_x1h=(unsigned char)(x1>>8); fd_y1=y1;
    fd_drawline();
}
void fd_rect(unsigned x0, unsigned char y0, unsigned x1, unsigned char y1) {
    fd_x0l=(unsigned char)x0; fd_x0h=(unsigned char)(x0>>8); fd_y0=y0;
    fd_x1l=(unsigned char)x1; fd_x1h=(unsigned char)(x1>>8); fd_y1=y1;
    fd_fillrect();
}
'''


def fdraw_object(work, fast):
    text = translate(HERE / 'upstream/fdraw/FDRAW.S', fast=fast, allocate_zp=True)
    text = text.replace('.segment "CODE"', '.segment "FDRAW"')
    aliases = {'arg': 'in_arg', 'x0l': 'in_x0l', 'x0h': 'in_x0h', 'y0': 'in_y0',
               'x1l': 'in_x1l', 'x1h': 'in_x1h', 'y1': 'in_y1',
               'init': 'Init', 'color': 'SetColor', 'page': 'SetPage',
               'drawline': 'DrawLine', 'fillrect': 'FillRect', 'clear': 'Clear'}
    text += '\n'.join(f'.export _fd_{key}\n_fd_{key} = {value}' for key, value in aliases.items()) + '\n'
    return compile_asm(work, 'fdraw_' + str(fast), text)


def pixels(page):
    return {(x, y) for y in range(192) for x in range(280)
            if page[a2test.hgr_offset(y) + x // 7] & (1 << (x % 7))}


def validate_line(page, ends):
    """Permit Bresenham tie choices, but require connected, accurate coverage."""
    x0, y0, x1, y1 = ends
    points = pixels(page)
    assert (x0, y0) in points and (x1, y1) in points
    dx, dy = x1-x0, y1-y0
    assert len(points) == max(abs(dx), abs(dy)) + 1
    assert all(min(x0,x1) <= x <= max(x0,x1) and min(y0,y1) <= y <= max(y0,y1)
               and abs(dy*(x-x0)-dx*(y-y0)) <= max(abs(dx),abs(dy)) / 2
               for x,y in points)
    ordered = sorted(points, key=lambda p: p[0] if abs(dx)>=abs(dy) else p[1])
    assert all(max(abs(a[0]-b[0]),abs(a[1]-b[1])) == 1 for a,b in zip(ordered,ordered[1:]))
    assert all(not (b & 128) for b in a2test.hgr_visible(page))
    assert all(page[i:i+8]==bytes(8) for i in range(120,8192,128)), 'line changed screen holes'


def graphics(work):
    objects = {name: fdraw_object(work, fast) for name, fast in [('fast',1),('small',0)]}
    cases = [('horizontal',(0,40,279,40)), ('vertical',(137,0,137,191)),
             ('diagonal',(0,0,279,191)), ('shallow',(5,30,263,73)),
             ('steep',(40,10,73,181)), ('reverse',(263,181,5,10)),
             ('short',(20,20,27,23)), ('point',(279,191,279,191))]
    results = []
    for name, ends in cases:
        for page in (1,2):
            args = ','.join(map(str, ends))
            ref, memory = execute(work, f'g_{name}_{page}_current', c_fixture(f'hgr_line({args});',page=page))
            target = memory[(page-1)*8192:page*8192]
            validate_line(target, ends)
            assert memory[(2-page)*8192:(3-page)*8192] == bytes(8192)
            row = dict(case=name, page=page, current=ref, alternatives={})
            for mode, obj in objects.items():
                metrics, actual = execute(work, f'g_{name}_{page}_{mode}',
                    c_fixture(f'fd_line({args});',
                        f'fd_init(); fd_arg=3; fd_color(); fd_arg={page*32}; fd_page();', FD_DECL, page), [obj])
                validate_line(actual[(page-1)*8192:page*8192], ends)
                assert actual[(2-page)*8192:(3-page)*8192] == bytes(8192)
                # Holes must remain untouched. Different tie choices are recorded.
                differing = len(pixels(target) ^ pixels(actual[(page-1)*8192:page*8192]))
                metrics.update(speedup=round(ref['cycles']/metrics['cycles'],3), different_pixels=differing)
                row['alternatives'][mode] = metrics
            results.append(row)
            print('graphics',name,'page',page,ref['cycles'],row['alternatives']['fast']['cycles'],flush=True)
    for name, current, alternative, expected in [
        ('clear', 'hgr_clear(0);', 'fd_clear();', bytes(8192)),
        ('rectangle', 'hgr_fill_pixrect(7,32,140,16);', 'fd_rect(7,32,146,47);', None),
        ('rectangle_wide', 'gfx_filled_rect(3,20,276,99);', 'fd_rect(3,20,276,99);', None),
    ]:
        for page in (1,2):
            # Nonzero background catches clearing/edge preservation mistakes.
            ref, memory = execute(work,f'g_{name}_{page}_current',c_fixture(current,page=page,background=42))
            row=dict(case=name,page=page,current=ref,alternatives={})
            for mode,obj in objects.items():
                setup=f'fd_init(); fd_arg={0 if name=="clear" else 3}; fd_color(); fd_arg={page*32}; fd_page();'
                metrics,actual=execute(work,f'g_{name}_{page}_{mode}',c_fixture(alternative,setup,FD_DECL,page,42),[obj])
                # Clear differs in screen-hole writes; those are excluded here.
                assert a2test.hgr_visible(actual[(page-1)*8192:page*8192]) == a2test.hgr_visible(memory[(page-1)*8192:page*8192]), name
                assert actual[(2-page)*8192:(3-page)*8192] == memory[(2-page)*8192:(3-page)*8192]
                if name!='clear':
                    assert all(actual[i:i+8]==memory[i:i+8] for i in range(120,16384,128)), 'rectangle changed screen holes'
                metrics.update(speedup=round(ref['cycles']/metrics['cycles'],3),
                               different_hole_bytes=sum(a!=b for a,b in zip(memory,actual)))
                row['alternatives'][mode]=metrics
            results.append(row)
            print('graphics',name,'page',page,ref['cycles'],row['alternatives']['fast']['cycles'],flush=True)
    results.extend(maze_lines(work,objects['fast']))
    return results


def maze_lines(work, fdraw):
    """Measure the actual maze3d assembly, not just the slower generic C API."""
    original=(ROOT/'maze3d/src/maze3d.s').read_text()
    routine=original[original.index('calc_pix_addr:\n'):original.index('\nhline:\n')]
    variables=['pix_x','pix_y','pix_col','pix_mask','pix_addr_lo','pix_addr_hi',
               'ln_x0','ln_y0','ln_x1','ln_y1','ln_dx','ln_dy','ln_sx','ln_sy',
               'ln_err','ln_err_hi','tmp','tmp2']
    source='.import _hgr_rowlo, _hgr_rowhi\nhgr_lo = _hgr_rowlo\nhgr_hi = _hgr_rowhi\n.segment "ZEROPAGE"\n'
    source+='\n'.join(v+': .res 1' for v in variables)+'\n.segment "CODE"\n'
    source+='hgr_bitmask: .byte 1,2,4,8,16,32,64,64\n'+routine
    source+='\n.export _maze_draw\n_maze_draw = line_xy\n'
    for key,alias in [('x0','ln_x0'),('y0','ln_y0'),('x1','ln_x1'),('y1','ln_y1')]:
        source+=f'.exportzp _maze_{key}\n_maze_{key} = {alias}\n'
    obj=compile_asm(work,'maze_line',source)
    decl='extern unsigned char maze_x0,maze_y0,maze_x1,maze_y1;\nvoid maze_draw(void);\n'
    decl+='\n'.join(f'#pragma zpsym("maze_{key}")' for key in ('x0','y0','x1','y1'))+'\n'
    results=[]
    for name,ends in [('maze_side',(0,0,40,25)),('maze_long',(0,0,255,159)),('maze_reverse',(220,140,35,20))]:
        x0,y0,x1,y1=ends
        call=f'maze_x0={x0};maze_y0={y0};maze_x1={x1};maze_y1={y1};maze_draw();'
        current,memory=execute(work,name+'_cur',c_fixture(call,extra=decl),[obj])
        # Independent virtual-coordinate Bresenham, then the game's 8 -> 7 mapping.
        expected=bytearray(16384)
        x,y=x0,y0; dx=abs(x1-x0); dy=abs(y1-y0)
        sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx-dy
        while True:
            xx=28+(x//8)*7+min(x%8,6)
            expected[a2test.hgr_offset(y)+xx//7]|=1<<(xx%7)
            if (x,y)==(x1,y1):break
            e2=err*2
            if e2>-dy:err-=dy;x+=sx
            if e2<dx:err+=dx;y+=sy
        assert memory==expected,name
        mapped=(28+(x0//8)*7+min(x0%8,6),y0,28+(x1//8)*7+min(x1%8,6),y1)
        metrics,actual=execute(work,name+'_fd',c_fixture('fd_line('+','.join(map(str,mapped))+');',
            'fd_init();fd_arg=3;fd_color();',FD_DECL),[fdraw])
        validate_line(actual[:8192],mapped)
        assert actual[8192:]==bytes(8192)
        metrics.update(speedup=round(current['cycles']/metrics['cycles'],3),
                       different_pixels=len(pixels(memory[:8192])^pixels(actual[:8192])))
        results.append(dict(case=name,page=1,baseline='actual maze3d asm, virtual 8px -> HGR 7px mapping',
                            current=current,alternatives={'fast':metrics},
                            source_sha256=hashlib.sha256(original.encode()).hexdigest()))
        print('maze assembly',name,current['cycles'],'->',metrics['cycles'],'cycles',flush=True)
    return results


def shape(width, height, dense=False):
    """A white ship with transparent margins, or an opaque checker tile."""
    return [[(1 if (x+y)%3 else 0) if dense else
             (1 if abs(x-width//2) <= min(y,height-1-y) else None)
             for x in range(width)] for y in range(height)]


def sprite_banks(rows):
    height, width = len(rows), len(rows[0])
    stride = (width+12)//7
    bits, masks = [], []
    for phase in range(7):
        for row in rows:
            data = [0]*stride
            mask = [255]*stride
            for x,value in enumerate(row):
                if value is not None:
                    col,bit=divmod(x+phase,7)
                    mask[col] &= ~(1<<bit)
                    data[col] |= value<<bit
            bits.extend(data); masks.extend(mask)
    return stride, bits, masks


def compiled_sprite(work, name, rows, masked):
    """Original prototype of HiSprite's technique, using our existing ABI.

    Seven fully unrolled, immediate-data routines. Supports both pages and
    arbitrary 16-bit x; right/bottom clipping falls back to the generic kernel.
    No HiSprite source is copied (its repository has no explicit licence).
    """
    stride,bits,masks=sprite_banks(rows)
    width,height=len(rows[0]),len(rows)
    prefix='ms' if masked else 'xs'
    fallback='_hgr_ms_run' if masked else '_hgr_xs_run'
    text=[f'.export _compiled_run\n.import {fallback}',
          '.import _hgr_col7, _hgr_phase7, _hgr_rowlo, _hgr_rowhi',
          f'.importzp _hgr_{prefix}_x, _hgr_{prefix}_y, ptr1, tmp1',
          '.segment "CODE"\n_compiled_run:',
          f'lda _hgr_{prefix}_x+1\nbeq low\nldx _hgr_{prefix}_x',
          'lda _hgr_col7+256,x\nsta tmp1\nlda _hgr_phase7+256,x\njmp select',
          f'low: ldx _hgr_{prefix}_x\nlda _hgr_col7,x\nsta tmp1\nlda _hgr_phase7,x',
          f'select: pha\nlda tmp1\ncmp #{41-stride}\nbcs clipped',
          f'lda _hgr_{prefix}_y\ncmp #{193-height}\nbcs clipped',
          'pla\nasl a\ntax\nlda jumps+1,x\npha\nlda jumps,x\npha\nrts',
          f'clipped: pla\njmp {fallback}',
          'jumps: .addr '+','.join(f'phase{p}-1' for p in range(7))]
    for phase in range(7):
        text += [f'phase{phase}:',f'ldx _hgr_{prefix}_y']
        for dy in range(height):
            active=[j for j in range(stride) if (masks[(phase*height+dy)*stride+j]!=255 if masked else bits[(phase*height+dy)*stride+j]!=0)]
            if active:
                text += ['lda _hgr_rowlo,x\nsta ptr1\nlda _hgr_rowhi,x\nsta ptr1+1\nldy tmp1']
                offset=0
                for j in active:
                    text += ['iny']*(j-offset)
                    offset=j
                    idx=(phase*height+dy)*stride+j
                    text += ['lda (ptr1),y']
                    if masked:
                        text += [f'and #{masks[idx]}']
                        if bits[idx]: text += [f'ora #{bits[idx]}']
                    else: text += [f'eor #{bits[idx]}']
                    text += ['sta (ptr1),y']
            if dy+1<height: text += ['inx']
        text += ['rts']
    return compile_asm(work,name,'\n'.join(text)+'\n')


def expected_sprite(memory, rows, x, y, page, masked):
    expected=bytearray(memory)
    for dy,row in enumerate(rows):
        for dx,value in enumerate(row):
            xx,yy=x+dx,y+dy
            if xx>=280 or yy>=192 or value is None: continue
            addr=(page-1)*8192+a2test.hgr_offset(yy)+xx//7
            bit=1<<(xx%7)
            if masked:
                expected[addr]=(expected[addr]&~bit)|(value*bit)
            elif value: expected[addr]^=bit
    return bytes(expected)


def sprites(work):
    results=[]
    demo=(ROOT/'demos/src/preshift_sprites.txt').read_text().split('sprite ship 21x9\n')[1].splitlines()[:9]
    demo_rows=[[1 if ch=='#' else None for ch in row.ljust(21,'.')] for row in demo]
    for size,rows in [('ship8',shape(8,8)),('ship16',shape(16,16)),('tile16',shape(16,16,True)),('demo_ship',demo_rows)]:
        stride,bits,masks=sprite_banks(rows)
        for mode in ('xor','masked','save_draw_restore'):
            masked=mode!='xor'
            arrays='static const unsigned char bits[]={'+','.join(map(str,bits))+'};\n'
            if masked:
                arrays+='static const unsigned char masks[]={'+','.join(map(str,masks))+'};\n'
                arrays+=f'static const hgr_mspr_t mspr={{bits,masks,{stride},{len(rows)}}};\n'
            else:
                arrays+=f'static const hgr_sprite_t spr={{bits,{stride},{len(rows)}}};\n'
            if mode=='save_draw_restore': arrays+=f'static unsigned char under[{stride*len(rows)}];\n'
            arrays+='void compiled_run(void);\n'
            obj=compiled_sprite(work,'compiled_'+size+'_'+mode,rows,masked)
            positions=[(42+p,40,1) for p in range(7)]+[(257,60,2),(274,188,2)]
            if mode=='save_draw_restore': positions=[(45,40,1),(257,60,2),(274,188,2)]
            for x,y,page in positions:
                params=(f'hgr_ms_x={x};hgr_ms_y={y};hgr_ms_spr=&mspr;'
                        if masked else f'hgr_xs_x={x};hgr_xs_y={y};hgr_xs_spr=&spr;')
                if mode=='save_draw_restore':params+='hgr_ms_under=under;'
                current=('hgr_msu_run();hgr_ms_restore_run();' if mode=='save_draw_restore' else
                         'hgr_ms_run();' if masked else 'hgr_xs_run();')
                compiled=('hgr_ms_save_run();compiled_run();hgr_ms_restore_run();' if mode=='save_draw_restore'
                          else 'compiled_run();')
                background=165 if page==2 else 42
                initial=bytes([background])*16384
                expected=initial if mode=='save_draw_restore' else expected_sprite(initial,rows,x,y,page,masked)
                key=f's_{size}_{mode}_{x}_{page}'
                ref,memory=execute(work,key+'_cur',c_fixture(params+current,extra=arrays,page=page,background=background))
                assert memory==expected,(key,'generic')
                metrics,actual=execute(work,key+'_cmp',c_fixture(params+compiled,extra=arrays,page=page,background=background),[obj])
                assert actual==expected,(key,'compiled')
                results.append(dict(shape=size,mode=mode,x=x,y=y,page=page,
                    phase=x%7,generic_bank_bytes=len(bits)+(len(masks) if masked else 0),
                    current=ref,compiled=metrics,speedup=round(ref['cycles']/metrics['cycles'],3)))
            print('sprites',size,mode,'passed',flush=True)
    return results


def asm_measure(work, name, body, payload, expected, page, decoder=''):
    data=work/(name+'.data');data.write_bytes(payload)
    source=f'''.segment "ZEROPAGE"
copy_src: .res 2
copy_dst: .res 2
.segment "CODE"
.export start, finish
entry_point:
    lda #$a5
    ldy #0
clear:
.repeat 64, i
    sta $2000+i*256,y
.endrepeat
    iny
    beq cleared
    jmp clear
cleared:
    jsr start
{body}
    jsr finish
halt: jmp halt
start: rts
finish: rts
.export decoder_begin, decoder_end
decoder_begin:
{decoder}
decoder_end:
.align 256
payload: .incbin "{data}"
'''
    obj=compile_asm(work,name,source)
    cfg=work/'asm.cfg'
    cfg.write_text('MEMORY { ZP: start=$50,size=$b0,type=rw; RAM: start=$6000,size=$3600,type=rw,file=%O; }\n'
                   'SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE: load=RAM,type=rw,align=$100; }\n')
    binary=work/(name+'.bin');labels=work/(name+'.lbl')
    run(['ld65','-C',cfg,'-Ln',labels,'-o',binary,obj])
    points=a2test.labels(labels)
    disk=a2test.build_disk(work,name.upper()[:28],binary)
    result=a2test.run(disk,[points.until('start'),points.until('finish'),'peek:2000:16384'])
    assert len(result.cycles)==2,name
    actual=result.mem(0x2000,16384)
    assert actual[(page-1)*8192:page*8192]==expected,name
    assert actual[(2-page)*8192:(3-page)*8192]==bytes([165])*8192,name
    return dict(cycles=result.cycles[1]-result.cycles[0]-12,
                payload_bytes=len(payload),binary_bytes=binary.stat().st_size,
                decoder_bytes=points['decoder_end']-points['decoder_begin'],
                harness_and_decoder_bytes=binary.stat().st_size-len(payload))


def compression(work):
    compressor=work/'fhpack'
    run(['c++','-O2','-o',compressor,HERE/'upstream/fhpack/fhpack.cpp'])
    decoder=translate(HERE/'upstream/fhpack/LZ4FH6502.S').replace('entry:','fh_entry:')
    small=translate(HERE/'upstream/fhpack/LZ4FH6502.SMA.S').replace('entry:','fh_entry:')
    corpus={}
    for game,diskname in [('arkabreakout','ARKABREAKOUT'),('micro_sokoban','MICRO-SOKOBAN')]:
        disk=ROOT/'dist'/(diskname+'.dsk')
        for state,steps in [('title',['wait:1100']),('after_space',['wait:1100','key: ','wait:60'])]:
            result=a2test.run(disk,steps+['peek:2000:8192'])
            corpus[game+'_'+state]=result.mem(0x2000,8192)
    corpus['blank']=bytes(8192)
    corpus['checker']=bytes([0x55,0x2a])*4096
    rng=random.Random(6502)
    corpus['noise']=rng.randbytes(8192)
    results=[]
    for name,data in corpus.items():
        raw=work/(name+'.hgr');raw.write_bytes(data)
        packed=work/(name+'.lz4fh')
        run([compressor,'-c','-9','-h',raw,packed])
        decoded=work/(name+'.roundtrip')
        run([compressor,'-d',packed,decoded])
        assert decoded.read_bytes()==data,name
        encoded=packed.read_bytes()
        for page in (1,2):
            dest=page*8192
            copy=f'''lda #<payload
sta copy_src
lda #>payload
sta copy_src+1
lda #0
sta copy_dst
lda #{dest>>8}
sta copy_dst+1
ldx #32
ldy #0
copy_loop:
lda (copy_src),y
sta (copy_dst),y
iny
bne copy_loop
inc copy_src+1
inc copy_dst+1
dex
bne copy_loop'''
            ref=asm_measure(work,f'c_{name}_{page}_raw',copy,data,data,page)
            unrolled=f'''ldy #0
unrolled_loop:
.repeat 32, i
lda payload+i*256,y
sta ${dest:04x}+i*256,y
.endrepeat
iny
beq copy_done
jmp unrolled_loop
copy_done:'''
            fast_copy=asm_measure(work,f'c_{name}_{page}_unrolled',unrolled,data,data,page)
            body=f'''lda #<payload
sta $2fc
lda #>payload
sta $2fd
lda #0
sta $2fe
lda #{dest>>8}
sta $2ff
jsr fh_entry'''
            alternatives={}
            for mode,src in [('fast',decoder),('small',small)]:
                metrics=asm_measure(work,f'c_{name}_{page}_{mode}',body,encoded,data,page,src)
                # Actual sectors for a DOS binary include its 4-byte header.
                saved=(len(data)+4+255)//256-(len(encoded)+4+255)//256
                extra_cycles=metrics['cycles']-ref['cycles']
                metrics.update(saved_data_sectors=saved,
                    breakeven_cycles_per_saved_sector=round(extra_cycles/saved,1) if saved>0 else None)
                alternatives[mode]=metrics
            row=dict(image=name,page=page,sha256=hashlib.sha256(data).hexdigest(),
                                raw=ref,raw_unrolled=fast_copy,alternatives=alternatives,
                                reduction_percent=round(100*(1-len(encoded)/8192),2))
            if page==2 and name not in ('blank','checker','noise'):
                row['disk_load']=disk_load(work,name,raw,packed,data,decoder)
            results.append(row)
        print('compression',name,'8192 ->',len(encoded),'bytes; round trips passed',flush=True)
    return results


def disk_load(work,name,raw,packed,data,decoder):
    """Actual cold DOS BLOAD, with equal-sized boot binaries/asset placement."""
    source=decoder+'\n.export _fh_entry\n_fh_entry = fh_entry\n'
    obj=compile_asm(work,'disk_decoder',source)
    dos=work/'apple2dos_asm.o'
    run(['cl65','-t','none','--asm-include-dir',DEV/'lib/apple2','-c','-o',dos,
         DEV/'lib/apple2c/apple2dos_asm.s'])
    extra='#include "apple2dos.h"\nvoid fh_entry(void);\n'
    base='a2_dos_cmd("BLOAD IMAGE,A$4000");'
    compressed='a2_dos_cmd("BLOAD IMAGE,A$2000");*((unsigned*)0x2fc)=0x2000;*((unsigned*)0x2fe)=0x4000;fh_entry();'
    measurements={}
    for mode,file,body,objects in [('raw',raw,base,[dos]),('compressed',packed,compressed,[dos,obj])]:
        metrics,memory=execute(work,'disk_'+name+'_'+mode,c_fixture(body,extra=extra),objects,
            extra_disk=[f'IMAGE={file}@0x4000'],pad_binary=8192)
        assert memory[8192:]==data,(name,mode,'disk load')
        metrics['milliseconds']=round(metrics['cycles']*1000/a2test.CPU_HZ,2)
        measurements[mode]=metrics
    measurements['speedup']=round(measurements['raw']['cycles']/measurements['compressed']['cycles'],3)
    print('disk load',name,measurements['raw']['milliseconds'],'->',measurements['compressed']['milliseconds'],'ms',flush=True)
    return measurements


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--suite', choices=('all','graphics','sprites','compression'), default='all')
    ap.add_argument('--out', type=Path, default=HERE/'build/results.json')
    args = ap.parse_args()
    work = HERE / 'build' / args.suite
    work.mkdir(parents=True, exist_ok=True)
    run(['make','-s','-C',DEV/'tools/a2run'])
    build(work)
    config=(DEV/'cc65/apple2_hgr_c.cfg').read_text().replace(
        '    RODATA:', '    FDRAW: load = RAM, type = rw, align = $100, optional = yes;\n    RODATA:')
    (work/'bench.cfg').write_text(config)
    compile_asm(work,'markers','.export _bench_begin, _bench_end\n.segment "CODE"\n_bench_begin: rts\n_bench_end: rts\n')
    compiler=subprocess.run(['cl65','--version'],capture_output=True,text=True,check=True)
    report=dict(compiler=(compiler.stdout+compiler.stderr).strip(),cpu='NMOS 6502 / a2run',flags='-Oirs',
                upstream={name:(HERE/'upstream'/name/'REVISION').read_text().strip() for name in ('fdraw','fhpack')})
    report['cpu_hz']=a2test.CPU_HZ
    report['host_cxx']=run(['c++','--version']).splitlines()[0]
    report['upstream_sha256']={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((HERE/'upstream').rglob('*')) if p.is_file()}
    if args.suite in ('all','graphics'): report['graphics']=graphics(work)
    if args.suite in ('all','sprites'): report['sprites']=sprites(work)
    if args.suite in ('all','compression'): report['compression']=compression(work)
    report['comparison_scenarios']=sum(len(report.get(key,[])) for key in ('graphics','sprites','compression'))
    report['measured_guest_runs']=(sum(1+len(r['alternatives']) for r in report.get('graphics',[]))
        +2*len(report.get('sprites',[]))
        +sum(2+len(r['alternatives'])+(2 if 'disk_load' in r else 0) for r in report.get('compression',[])))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('Correctness checks passed; measurements:',args.out)


if __name__=='__main__':
    main()
