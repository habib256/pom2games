#!/usr/bin/env python3
"""Independent HGR save-under initialization and definition state oracle.

Checks the complete private state, return value, software-stack cleanup,
interrupt flag and page-selection callbacks. The callbacks destroy every
cc65 pointer and temporary. --reference uses the retained C implementation;
--full adds exhaustive 16-bit pointer and pool-size axes. --bench measures
archive-linked clients separately from the direct state-control fixture.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import tempfile
from pathlib import Path

import test_hgr
from test_hgr import DEV, a2test, compile_source, run

SLOT = 192


def case(mode=0, db=1, count=1, cap=96, pool=0xfff0, size=65535,
         w=2, h=3, data=65535, mask=0x8001, d0=0, d1=0):
    return bytes((mode, db, count, cap, pool & 255, pool >> 8,
                  size & 255, size >> 8, w, h, data & 255, data >> 8,
                  mask & 255, mask >> 8, d0, d1))


def cases(n, full):
    result = []
    # Every capacity, count boundary, raw double-buffer flag and size boundary.
    for db in (0, 1, 255):
        for count in range(n + 2):
            for cap in range(256):
                required = count * cap * (2 if db else 1)
                for size in sorted({0, max(0, required - 1), required, 65535}):
                    result.append(case(db=db, count=count, cap=cap, size=size))
    for value in range(256):
        result += [case(db=value, count=n, cap=255, pool=(value * 257) ^ 65535),
                   case(db=value, count=value, cap=255), case(db=value, pool=0)]
    # Complete raw stride/height domain, then valid multiplication boundaries.
    for stride in range(256):
        for height in range(256):
            result.append(case(1, n, 0, (stride * 17 + height) & 255,
                               w=stride, h=height))
    for stride in range(1, 41):
        for height in range(1, 193):
            product = stride * height
            if product <= 255:
                for cap in {max(0, product - 1), product, min(255, product + 1)}:
                    result.append(case(1, n, 0, cap, w=stride, h=height))
    # Invalid IDs and drawn sprites reject before reading the shape header.
    for ident in range(256):
        for d0, d1 in ((0, 0), (1, 0), (0, 255), (255, 255)):
            for mode in (1, 3):
                result.append(case(mode, n, ident, 96, d0=d0, d1=d1))
    for count in range(n + 1):
        for ident in range(n + 1):
            result += [case(1, count, ident, 255), case(3, count, ident, 255)]
    for value in range(256):
        for pointer in (value, value << 8):
            result += [case(1, n, 0, 255, data=pointer),
                       case(1, n, 0, 255, mask=pointer)]
        result.append(case(2, db=value))
        for pointer in (value, value << 8):
            result += [case(4, n, n, 255, pool=pointer),
                       case(5, n, 0, 255, pool=pointer, d0=255)]
    if full:
        for value in range(65536):
            result += [case(4, n, n, 255, pool=value),
                       case(5, n, 0, 255, pool=value, d0=255),
                       case(db=255, count=n, cap=255, size=value),
                       case(db=255, count=n, cap=255, pool=value),
                       case(1, n, 0, 255, data=value),
                       case(1, n, 0, 255, mask=value)]
    while len(result) % 16:
        result.append(result[-1])
    return result


FIXTURE='''#include "hgr.h"
#include <string.h>
extern const hgr_mspr_t *spr_shape[HGR_SPR_MAX];
extern unsigned spr_x[HGR_SPR_MAX],spr_px[2][HGR_SPR_MAX];
extern unsigned char spr_y[HGR_SPR_MAX],spr_active[HGR_SPR_MAX];
extern unsigned char spr_py[2][HGR_SPR_MAX],spr_drawn[2][HGR_SPR_MAX];
extern unsigned char *spr_under[2];
extern unsigned char spr_count,spr_capacity,spr_invalid,spr_dbuf,spr_drawpage;
#if HGR_SPR_DAMAGE
extern unsigned char spr_box[HGR_SPR_MAX][4];
#endif
extern unsigned char spr_block[HGR_SPR_MAX],spr_dirty;
extern void (*spr_damage_fn)(void);
typedef struct {unsigned char *data;unsigned char size;} region_t;
#define R(field) {(unsigned char*)&spr_##field,sizeof(spr_##field)}
static const region_t regions[]={R(shape),R(x),R(y),R(active),R(px),R(py),R(drawn),R(under),
 R(count),R(capacity),R(invalid),R(dbuf),R(drawpage),
#if HGR_SPR_DAMAGE
 R(box),
#endif
 R(block),R(dirty),R(damage_fn)};
void ready(void);void done(void);void probe_call(void);
#ifdef STATE_GUARDS
void guard_fill(void);unsigned char guard_check(void);
#endif
unsigned char inputs[16][16],records[16][192],result[16],headers[512],*current,*shape_pointer,index;
static void poison(unsigned char value){
 unsigned char r;
 for(r=0;r<sizeof(regions)/sizeof(regions[0]);++r)memset(regions[r].data,value,regions[r].size);
}
static void snapshot(unsigned char *destination){
 unsigned char r;
 for(r=0;r<sizeof(regions)/sizeof(regions[0]);++r){
  memcpy(destination,regions[r].data,regions[r].size);destination+=regions[r].size;
 }
}
int main(void){
 unsigned serial=0;unsigned char slot;
 for(;;){ready();for(slot=0;slot<16;++slot){
  current=inputs[slot];index=(unsigned char)serial++;
#ifdef STATE_GUARDS
  guard_fill();
#endif
  poison(index);memset(result,0,16);
  shape_pointer=headers+index;
  shape_pointer[0]=current[10];shape_pointer[1]=current[11];
  shape_pointer[2]=current[12];shape_pointer[3]=current[13];
  shape_pointer[4]=current[8];shape_pointer[5]=current[9];
  if(current[0]!=0&&current[0]!=2){
   spr_count=current[1];spr_capacity=current[3];
   if(current[2]<HGR_SPR_MAX){spr_drawn[0][current[2]]=current[14];spr_drawn[1][current[2]]=current[15];}
  }
  if(index&1){asm("sei");}else{asm("cli");}
  probe_call();asm("cli");
#ifdef STATE_GUARDS
  result[15]=guard_check();
#endif
  memcpy(records[slot],result,16);memcpy(records[slot]+16,shape_pointer,6);
  snapshot(records[slot]+22);
 }done();}
 return 0;
}
'''
PROBE='''.export _ready,_done,resume,_probe_call,_hgr_set_draw_page,_hgr_show_page
.import _hgr_spr_init_pool,_hgr_spr_define,_hgr_spr_init,_spr_drawpage
.import _inputs,_current,_index,_result,_shape_pointer
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.bss
saved_sp:.res 2
.code
_ready:rts
_done:nop
resume:rts
.macro ARG input_offset,frame_offset
 ldy #input_offset
 lda (ptr4),y
 ldy #frame_offset
 sta (sp),y
.endmacro
_probe_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _current
 sta ptr4
 lda _current+1
 sta ptr4+1
 lda _index
 sta sp
 lda #$10
 sta sp+1
 ldy #0
 lda (ptr4),y
 cmp #2
 beq compat
 cmp #0
 bne define
 ARG 2,0
 ARG 6,1
 ARG 7,2
 ARG 4,3
 ARG 5,4
 ARG 1,5
 ldy #6
 lda #$a5
 sta (sp),y
 iny
 lda #$5a
 sta (sp),y
 ldy #3
 lda (ptr4),y
 jsr _hgr_spr_init_pool
 jmp returned
compat:
 lda #$a5
 sta (sp),y
 iny
 lda #$5a
 sta (sp),y
 lda (ptr4),y
 jsr _hgr_spr_init
 jmp returned
define:
 ARG 2,0
 ldy #1
 lda #$a5
 sta (sp),y
 iny
 lda #$5a
 sta (sp),y
 ldy #0
 lda (ptr4),y
 cmp #3
 beq null
 cmp #4
 bcc normal_shape
 ldy #5
 lda (ptr4),y
 tax
 dey
 lda (ptr4),y
 jmp call_define
normal_shape:
 lda _shape_pointer
 ldx _shape_pointer+1
 bne call_define
 beq call_define
null:
 lda #0
 tax
call_define:
 jsr _hgr_spr_define
returned:
 sta _result
 stx _result+1
 php
 pla
 and #4
 sta _result+6
 lda sp
 sta _result+2
 lda sp+1
 sta _result+3
 ldy #0
 lda (sp),y
 sta _result+4
 iny
 lda (sp),y
 sta _result+5
 lda saved_sp
 sta sp
 lda saved_sp+1
 sta sp+1
 rts
_hgr_set_draw_page:
 cpx #0
 beq :+
 inc _result+14
: ldx _result+7
 sta _result+8,x
 lda _spr_drawpage
 sta _result+11,x
 inc _result+7
 jmp clobber
_hgr_show_page:
 ldx _result+7
 lda #$80
 sta _result+8,x
 lda _spr_drawpage
 sta _result+11,x
 inc _result+7
clobber:
 lda #$a5
'''+''.join(' sta '+name+'\n' for name in ('ptr1','ptr1+1','ptr2','ptr2+1','ptr3','ptr3+1','ptr4','ptr4+1','tmp1','tmp2','tmp3','tmp4'))+''' tax
 tay
 rts
'''


def c_reference(work, flags, engine=None):
    """Explicit C objects win over the independent native archive entries."""
    objects = []
    for name in ('hgr_sprengine', 'hgr_sprdefault'):
        obj = work / ('ref_' + name + '.o')
        source = engine if name == 'hgr_sprengine' and engine else DEV / 'lib/hgrc' / (name + '.c')
        compile_source(source, obj,
                       ['-t', 'none', '-Oirs', '-DHGR_SPR_C_ENTRY=1', *flags,
                        '-I', DEV / 'lib/hgrc', '-I', DEV / 'lib/apple2c'])
        objects.append(obj)
    return objects


def state_regions(n,damage):
    result=[('shape',2*n),('x',2*n),('y',n),('active',n),('px',4*n),('py',2*n),('drawn',2*n),('under',4),('count',1),('capacity',1),('invalid',1),('dbuf',1),('drawpage',1)]
    if damage:result.append(('box',4*n))
    return result+[('block',n),('dirty',1),('damage_fn',2)]


def module_bss(text, member):
    marker = member + '.o):'
    if marker not in text:
        return 0
    section = text.split(marker)[1].split('.o):')[0]
    match = re.search(r'BSS\s+Offs=[0-9A-F]+\s+Size=([0-9A-F]+)', section)
    return int(match[1], 16) if match else 0


def guard_source(n,damage):
    lines=['.bss']
    guards=[]
    for i,(name,size) in enumerate(state_regions(n,damage)):
        for suffix in ('before','after'):guards.append(f'guard_{i}_{suffix}')
        lines +=[f'.export _spr_{name}',f'guard_{i}_before:.res 1',f'_spr_{name}:.res {size}',f'guard_{i}_after:.res 1']
    lines +=['.code','.export _guard_fill,_guard_check','_guard_fill:',' lda #$6d']
    lines +=[' sta '+g for g in guards]
    lines +=[' rts','_guard_check:',' ldx #0']
    for g in guards:lines+=[' lda '+g,' cmp #$6d',' beq :+',' inx',':']
    lines+=[' txa',' beq :+',' lda #0',' ldx #0',' rts',': lda #1',' ldx #0',' rts']
    return '\n'.join(lines)+'\n'


def extern_state(source):
    """Keep the actual C entries/types; the guard object supplies their backing.

    Only mutable data declarations become extern. The slot/factory constants
    and all function bodies remain intact, including the retained C reference.
    """
    first = source.index('/* --- per-sprite state:')
    last = source.index('/* Native cc65 entries', first)
    declarations = source[first:last].splitlines()
    for index, line in enumerate(declarations):
        if line.startswith(('const hgr_mspr_t *spr_shape', 'unsigned ',
                            'unsigned char ', 'void (*spr_damage_fn')):
            declarations[index] = 'extern ' + line
    return source[:first] + '\n'.join(declarations) + '\n\n' + source[last:]


def build_control(work, source, probe, flags, n, damage, reference, guarded, overrun):
    extra = [probe]
    engine = None
    if guarded:
        flags = [*flags, '-DSTATE_GUARDS=1']
        guards = work / 'guards.s'
        guards.write_text(guard_source(n, damage))
        extra.append(guards)
        engine = work / 'guard_engine.c'
        engine.write_text(extern_state((DEV / 'lib/hgrc/hgr_sprengine.c').read_text()))
    corrupted = None
    if overrun:
        corrupted = work / 'overrun_init.s'
        text = (DEV / 'lib/hgrc/hgr_spr_init_pool.s').read_text()
        needle = ' lda _spr_slots\n asl a\n tax\n lda #0\n'
        assert needle in text
        corrupted.write_text(text.replace(needle, needle.replace(' tax\n', ' tax\n inx\n')))
    original_compile, original_run = test_hgr.compile_source, test_hgr.run

    def compile_member(member, obj, options):
        if engine and Path(member).name == 'hgr_sprengine.c':
            member = engine
        if corrupted and Path(member).name == 'hgr_spr_init_pool.s':
            member = corrupted
        return original_compile(member, obj, options)

    def link_guards(args, **kwargs):
        # build() performs an initial fixture link. Guard definitions must be
        # explicit before the archive so its ordinary state members stay out.
        if guarded and str(args[0]) == 'cl65' and work / 'hgrc.lib' in args:
            at = args.index(work / 'hgrc.lib')
            args = [*args[:at], work / 'guards.o', *args[at:]]
        return original_run(args, **kwargs)

    try:
        test_hgr.compile_source, test_hgr.run = compile_member, link_guards
        test_hgr.build(work, source, extra_sources=extra, cflags=flags)
    finally:
        test_hgr.compile_source, test_hgr.run = original_compile, original_run
    objects = c_reference(work, flags, engine) if reference else []
    return [*objects, *([work / 'guards.o'] if guarded else [])]


def check(n, damage, reference=False, iie=False, full=False, guarded=False, overrun=False):
    with tempfile.TemporaryDirectory(prefix='hgr-spr-control-') as directory:
        work = Path(directory)
        source, probe = work / 'control.c', work / 'probe.s'
        source.write_text(FIXTURE)
        probe.write_text(PROBE)
        flags = [f'-DHGR_SPR_MAX={n}', f'-DHGR_SPR_DAMAGE={damage}']
        objects = build_control(work, source, probe, flags, n, damage, reference, guarded, overrun)
        binary, mapfile, labelsfile = (work / name for name in
                                      ('control.bin', 'control.map', 'control.lbl'))
        run(['cl65', '-t', 'none', '-C', DEV / 'cc65/apple2_hgr_c.cfg',
             '-m', mapfile, '-Ln', labelsfile, '-o', binary,
             work / 'crt0_apple2.o', work / 'control.o', work / 'probe.o',
             work / 'apple2io_asm.o', *objects, work / 'hgrc.lib'])
        labels = a2test.labels(labelsfile)
        disk = a2test.build_disk(work, 'CONTROL', binary)
        fields = {};length=0
        for name,size in state_regions(n,damage):fields[name]=length;length+=size
        assert length==15*n+12+4*n*damage and 22+length<=SLOT
        text = mapfile.read_text()
        if not guarded and not reference:
            sizes={'hgr_sprshape':2*n,'hgr_sprtargets':3*n,'hgr_spractive':n,'hgr_sprhistory':6*n,'hgr_sprengine':3*n+12}
            if damage:
                sizes={name:0 for name in sizes};sizes['hgr_sprengine']=19*n+12
            for member,size in sizes.items():
                actual=module_bss(text,member)
                assert actual==size,(member,actual,size)
        bss_start = int(re.search(r'(?m)^BSS\s+([0-9A-F]+)',
                                 text.split('Segment list:')[1])[1], 16)
        # The C fallback deliberately keeps its compatibility pool static.
        member = 'ref_hgr_sprdefault.o' if reference else 'hgr_sprdefault.o'
        separator = member + (':' if reference else '):')
        section = text.split(separator)[1].split('.o:')[0] if reference else \
            text.split(separator)[1].split('.o):')[0]
        pool = bss_start + int(re.search(r'BSS\s+Offs=([0-9A-F]+)', section)[1], 16)
        factory = labels['_hgr_spr_damage'] if damage else 0

        def expected(c, index):
            (mode, db, arg, cap, pl, ph, bl, bh, stride, height,
             dl, dh, ml, mh, d0, d1) = c
            pool_arg, size = pl + 256 * ph, bl + 256 * bh
            state = bytearray([index]) * length
            shape = labels['_headers'] + index
            header = bytes((dl, dh, ml, mh, stride, height))
            result = bytearray(16)
            result[15]=int(guarded)
            frame = 6 if mode == 0 else 0 if mode == 2 else 1
            result[2] = (index + frame) & 255
            result[3] = 0x10 + int(index + frame > 255)
            result[4:6] = b'\xa5\x5a'
            result[6] = 4 if index & 1 else 0

            def byte(field, value, at=0):
                state[fields[field] + at] = value

            def word(field, value, at=0):
                start = fields[field] + at
                state[start:start + 2] = bytes((value & 255, (value >> 8) & 255))

            if mode in (0, 2):
                if mode == 2:
                    arg, cap, pool_arg, size = n, 96, pool, 2 * n * 96
                valid = (pool_arg and 0 < arg <= n and cap and
                         size >= arg * cap * (2 if db else 1))
                if valid:
                    page = arg * cap
                    word('under', pool_arg)
                    word('under', (pool_arg + page if db else pool_arg) & 65535, 2)
                    byte('invalid', 0)
                    word('damage_fn', factory)
                    byte('count', arg)
                    byte('capacity', cap)
                    byte('dbuf', db)
                    for field, size in (('shape', 2 * n), ('active', n),
                                        ('drawn', 2 * n)):
                        state[fields[field]:fields[field] + size] = bytes(size)
                    byte('drawpage', 2 if db else 1)
                    result[0] = 1
                    calls = [1, 128] + ([2] if db else [])
                    result[7] = len(calls)
                    result[8:8 + len(calls)] = bytes(calls)
                    result[11:11 + len(calls)] = bytes([index, index] + ([2] if db else []))
            else:
                byte('count', db)
                byte('capacity', cap)
                if arg < n:
                    byte('drawn', d0, arg)
                    byte('drawn', d1, n + arg)
                if arg < db and not d0 and not d1:
                    if mode == 3:
                        word('shape', 0, 2 * arg)
                        byte('active', 0, arg)
                        byte('block', 0, arg)
                        result[0] = 1
                    elif ((dl or dh) and (ml or mh) and 0 < stride <= 40 and
                          0 < height <= 192 and stride * height <= cap):
                        word('shape', shape, 2 * arg)
                        byte('active', 1, arg)
                        byte('block', stride * height, arg)
                        result[0] = 1
                    else:
                        word('shape', 0, 2 * arg)
                        byte('active', 0, arg)
            return result + header + state

        inputs = cases(n, full)
        # A boot handles 256 batches; the serial byte repeats on that boundary.
        for first in range(0, len(inputs), 4096):
            chunk = inputs[first:first + 4096]
            steps = []
            for offset in range(0, len(chunk), 16):
                path = work / f'p{offset // 16:04x}.bin'
                path.write_bytes(b''.join(chunk[offset:offset + 16]))
                steps += [labels.until('_ready'),
                          f'load:{path}@{labels["_inputs"]:04X}',
                          labels.until('_done'), labels.peek('_records', 16 * SLOT),
                          labels.until('resume')]
            result = a2test.run(disk, steps, iie=iie, timeout=120)
            assert len(result.dumps) == len(chunk) // 16
            for batch, raw in enumerate(result.dumps):
                for slot in range(16):
                    ordinal = first + batch * 16 + slot
                    current = chunk[batch * 16 + slot]
                    want = expected(current, ordinal & 255)
                    got = raw[slot * SLOT:slot * SLOT + len(want)]
                    assert got == want, (n, damage, reference, iie, ordinal,
                                         current.hex(), got.hex(), want.hex())
        print(f'HGR controls: {len(inputs):,} calls; MAX={n}, DAMAGE={damage}, '
              f'{"C reference" if reference else "native"}, {"IIe" if iie else "NMOS"}, '
              f'array guards={guarded}.', flush=True)


SCENES = {
    'pool_single': dict(call='hgr_spr_init_pool(0,pool,sizeof(pool),4,64);'),
    'pool_double': dict(call='hgr_spr_init_pool(1,pool,sizeof(pool),4,64);'),
    'pool_rawdb': dict(call='hgr_spr_init_pool(255,pool,sizeof(pool),4,64);'),
    'pool_count1': dict(call='hgr_spr_init_pool(1,pool,sizeof(pool),1,255);'),
    'pool_no_pool': dict(call='hgr_spr_init_pool(1,0,sizeof(pool),4,64);'),
    'pool_no_count': dict(call='hgr_spr_init_pool(1,pool,sizeof(pool),0,64);'),
    'pool_no_capacity': dict(call='hgr_spr_init_pool(1,pool,sizeof(pool),4,0);'),
    'pool_too_small': dict(call='hgr_spr_init_pool(1,pool,511,4,64);'),
    'compat_single': dict(call='hgr_spr_init(0);'),
    'compat_double': dict(call='hgr_spr_init(1);'),
    'define_valid': dict(setup='hgr_spr_init_pool(0,pool,sizeof(pool),4,64);',
                         call='hgr_spr_define(0,&shape);'),
    'define_null': dict(setup='hgr_spr_init_pool(0,pool,sizeof(pool),4,64);',
                        call='hgr_spr_define(0,0);'),
    'define_large': dict(setup='hgr_spr_init_pool(0,pool,sizeof(pool),4,255);'
                             'shape.stride=1;shape.h=192;',
                         call='hgr_spr_define(0,&shape);'),
    'define_overflow': dict(setup='hgr_spr_init_pool(0,pool,sizeof(pool),4,64);'
                                'shape.stride=40;shape.h=192;',
                            call='hgr_spr_define(0,&shape);'),
    'define_badstride': dict(setup='hgr_spr_init_pool(0,pool,sizeof(pool),4,64);'
                                 'shape.stride=41;',
                             call='hgr_spr_define(0,&shape);'),
    'define_badid': dict(setup='hgr_spr_init_pool(0,pool,sizeof(pool),4,64);',
                         call='hgr_spr_define(255,&shape);'),
}


def bench(out=None, reference=False):
    spec = importlib.util.spec_from_file_location('hgr_control_bench', DEV / 'bench/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='hgr-spr-control-bench-') as directory:
        work = Path(directory)
        module.build(work)
        if reference:
            # Replace members within this isolated archive, preserving normal
            # archive extraction and the optional compatibility-pool linkage.
            objects = c_reference(work, [])
            replacements = []
            for obj in objects:
                member = work / obj.name.removeprefix('ref_')
                member.write_bytes(obj.read_bytes())
                replacements.append(member)
            run(['ar65', 'd', work / 'hgrc.lib', 'hgr_spr_init_pool.o',
                 'hgr_spr_define.o', 'hgr_spr_init.o'])
            run(['ar65', 'a', work / 'hgrc.lib', *replacements])
        markers = work / 'markers.s'
        markers.write_text('.export _bench_begin, _bench_end\n.code\n'
                           '_bench_begin:rts\n_bench_end:rts\n')
        run(['ca65', '-o', work / 'markers.o', markers])
        declarations = ('static unsigned char pool[2048],data[64],mask[64];'
                        'static hgr_mspr_t shape={data,mask,2,3};')
        results = {name: module.measure(work, 'hgr_spr_native_' + name,
                                       warmup=False, declarations=declarations, **scene)
                   for name, scene in SCENES.items()}
        if out:
            version = subprocess.run(['cl65', '--version'], capture_output=True,
                                     text=True, check=True)
            sources = ('hgr_sprengine.c', 'hgr_sprdefault.c', 'hgr_spr_init_pool.s',
                       'hgr_sprshape.c', 'hgr_sprtargets.c', 'hgr_spractive.c', 'hgr_sprhistory.c',
                       'hgr_spr_define.s', 'hgr_spr_init.s', 'hgr_sprengine_asm.s',
                       'hgr_spr_control.s', 'hgr_spr_visibility.s',
                       'hgr_sprdamage.s', 'hgr_sprmask.s', 'hgr.h', 'hgrc.mk', 'hgrc_build.mk')
            report = dict(schema=2, compiler=(version.stdout + version.stderr).strip(),
                          flags='-Oirs', results=results,
                          case_environments={name: 'ii_plus' for name in results},
                          environments={'ii_plus': module.environment(False)},
                          entry_mode='C reference' if reference else 'native',
                          stack_sampling='coherent cc65 call/return/jump/(sp),Y boundaries; '
                                         'observed workload, not a static bound',
                          source_artifacts=[module.identity(DEV / 'lib/hgrc' / name)
                                            for name in sources] +
                                           [module.identity(Path(__file__))])
            out.write_text(json.dumps(report, indent=2) + '\n')
        for name, values in results.items():
            print(f'{name}: {values["cycles"]:,} cycles; '
                  f'{values["binary_bytes"]:,} loaded bytes; '
                  f'C stack {values["c_stack_peak_bytes"]}, '
                  f'hardware stack {values["hardware_stack_peak_bytes"]}.')


ARCHIVE_ENTRIES = {
    'init': 'hgr_spr_init_pool(1,pool,sizeof(pool),HGR_SPR_MAX,16);',
    'define': 'hgr_spr_define(0,0);', 'compat': 'hgr_spr_init(1);',
    'move': 'hgr_spr_move(0,17,40);', 'hide': 'hgr_spr_hide(0);',
    'invalidate': 'hgr_spr_invalidate(0);', 'render': 'hgr_spr_render();',
    'present': 'hgr_spr_present();', 'update': 'hgr_spr_update();',
}


def check_source_order():
    """Both direct test archives and the shared builder retain the state order."""
    with tempfile.TemporaryDirectory(prefix='hgr-state-order-') as directory:
        work = Path(directory)
        hgr = DEV / 'lib/hgrc'
        mk = work / 'order.mk'
        mk.write_text(f'DEV := {DEV}\nHGRC := {hgr}\nGFX := {DEV}/lib/gfx\n'
                      f'include {hgr}/hgrc.mk\n'
                      'all:\n\t@true\n'
                      f'HGRC_BUILD := {work}/objects\nHGRC_LIB := {work}/hgrc.lib\n'
                      f'HGRC_EXTRA_SRCS := {DEV}/lib/apple2c/apple2io_asm.s '
                      f'{hgr}/hgr_sprhistory.c\n'
                      f'include {hgr}/hgrc_build.mk\n'
                      'print:\n\t@echo DIRECT $(HGRC_ALL_SRCS)\n'
                      '\t@echo BUILDER $(HGRC_ARCHIVE_SRCS)\n')
        expected = [str(hgr / ('hgr_spr' + name + '.c'))
                    for name in ('shape', 'targets', 'active', 'history')]
        for line in run(['make', '-s', '-f', mk, 'print']).splitlines():
            mode, *sources = line.split()
            assert mode in ('DIRECT', 'BUILDER'), line
            at = sources.index(str(hgr / 'hgr_sprengine.c'))
            assert sources[at-4:at] == expected, (mode, sources[at-4:at])
            assert len(sources) == len(set(sources)), (mode, 'duplicates')
            others = [source for source in sources if source not in expected]
            assert others == sorted(others), (mode, 'unrelated member order changed')
        print('Sprite state order: direct/shared archives keep original member positions; extras deduplicated.')


def check_archive():
    """Link each public entry separately; assert the actual archive closure."""
    check_source_order()
    for n in (1, 2, 8):
        for damage in (0, 1):
            with tempfile.TemporaryDirectory(prefix='hgr-spr-extract-') as directory:
                work = Path(directory)
                flags = [f'-DHGR_SPR_MAX={n}', f'-DHGR_SPR_DAMAGE={damage}']
                test_hgr.build(work, cflags=flags)
                for name, call in ARCHIVE_ENTRIES.items():
                    source = work / (name + '.c')
                    source.write_text('#include "hgr.h"\nstatic unsigned char pool[256];\n'
                                      'int main(void){' + call + 'return 0;}\n')
                    obj, mapfile = source.with_suffix('.o'), source.with_suffix('.map')
                    compile_source(source, obj, ['-t', 'none', '-Oirs', *flags,
                                                '-I', DEV / 'lib/hgrc',
                                                '-I', DEV / 'lib/apple2c'])
                    run(['cl65', '-t', 'none', '-C', DEV / 'cc65/apple2_hgr_c.cfg',
                         '-m', mapfile, '-o', source.with_suffix('.bin'),
                         work / 'crt0_apple2.o', obj, work / 'apple2io_asm.o',
                         work / 'hgrc.lib'])
                    text = mapfile.read_text()
                    control = name in ('move', 'hide', 'invalidate')
                    frame = name in ('render', 'present', 'update')
                    expected = {
                        'hgr_spr_control.o': control,
                        'hgr_sprengine_asm.o': frame,
                        'hgr_spr_visibility.o': frame or bool(damage),
                        'hgr_sprmask.o': frame, 'hgr_phases.o': frame,
                        'hgr_sprdefault.o': name == 'compat',
                        'hgr_spr_init_pool.o': name in ('init', 'compat'),
                        'hgr_spr_define.o': name == 'define',
                    }
                    for member, wanted in expected.items():
                        assert (member in text) == wanted, (n, damage, name, member, wanted)
                    state = {'hgr_sprshape': 2*n, 'hgr_sprtargets': 3*n,
                             'hgr_spractive': n, 'hgr_sprhistory': 6*n}
                    used = {'hgr_sprshape': not damage, 'hgr_spractive': not damage,
                            'hgr_sprtargets': not damage and (control or frame),
                            'hgr_sprhistory': not damage and frame}
                    for member, size in state.items():
                        assert module_bss(text, member) == (size if used[member] else 0), (
                            n, damage, name, member, size, used[member])
                    assert module_bss(text, 'hgr_sprengine') == (
                        (19*n+12) if damage else (3*n+12))
                print(f'Sprite archive MAX={n}, DAMAGE={damage}: nine independent entries OK.',
                      flush=True)


def bench_archive(out=None):
    """Measure the extraction clients alongside 45 existing renderer cases."""
    spec = importlib.util.spec_from_file_location('hgr_archive_bench', DEV / 'bench/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prefixes = ('hgr_masked_', 'hgr_scene_phase', 'hgr_scene_large',
                'hgr_damage_', 'hgr_dirty_', 'hgr_pool_')
    scenes = {name: scene for name, scene in module.SCENES.items() if name.startswith(prefixes)}
    setup = 'hgr_spr_init_pool(1,pool,sizeof(pool),4,64);'
    declarations = ('static unsigned char pool[512],data[64],mask[64];'
                    'static hgr_mspr_t shape={data,mask,2,3};')
    for name, call in ARCHIVE_ENTRIES.items():
        if name in ('init', 'define', 'compat'):
            continue
        scenes['hgr_sprite_archive_' + name] = dict(
            setup=setup, call=call, declarations=declarations, warmup=False)
    scenes['hgr_sprite_archive_damage_init'] = dict(
        call=setup, declarations=declarations, warmup=False, damage=True)
    scenes['hgr_sprite_archive_damage_define'] = dict(
        setup=setup, call='hgr_spr_define(0,&shape);', declarations=declarations,
        warmup=False, damage=True)
    with tempfile.TemporaryDirectory(prefix='hgr-spr-archive-bench-') as directory:
        work = Path(directory)
        module.build(work)
        markers = work / 'markers.s'
        markers.write_text('.export _bench_begin,_bench_end\n.code\n'
                           '_bench_begin:rts\n_bench_end:rts\n')
        run(['ca65', '-o', work / 'markers.o', markers])
        results = {name: module.measure(work, name, **scene) for name, scene in scenes.items()}
    if out:
        version = subprocess.run(['cl65', '--version'], capture_output=True,
                                 text=True, check=True)
        members = ('hgr_sprengine.c', 'hgr_sprdefault.c', 'hgr_spr_init_pool.s',
                   'hgr_sprshape.c', 'hgr_sprtargets.c', 'hgr_spractive.c', 'hgr_sprhistory.c',
                   'hgr_spr_define.s', 'hgr_spr_init.s', 'hgr_sprengine_asm.s',
                   'hgr_spr_control.s', 'hgr_spr_visibility.s', 'hgr_sprdamage.s',
                   'hgr_sprmask.s', 'hgr.h', 'hgrc.mk', 'hgrc_build.mk')
        artifacts = [DEV / 'lib/hgrc' / name for name in members]
        report = dict(schema=2, compiler=(version.stdout + version.stderr).strip(),
                      flags='-Oirs', results=results,
                      case_environments={name: 'ii_plus' for name in results},
                      environments={'ii_plus': module.environment(False)},
                      stack_sampling='coherent cc65 call/return/jump/(sp),Y boundaries; '
                                     'observed workload, not a static bound',
                      source_artifacts=[module.identity(p) for p in artifacts if p.exists()] +
                                       [module.identity(Path(__file__))])
        out.write_text(json.dumps(report, indent=2) + '\n')
    for name, values in results.items():
        print(f'{name}: {values["cycles"]:,} cycles; {values["binary_bytes"]:,} loaded bytes; '
              f'{values["ram_bytes"]:,} RAM; {values["zp_bytes"]} ZP.')


def negative_guard_check():
    """A one-past clear must fail the canary while named fields still match."""
    try:
        check(8, 0, guarded=True, overrun=True)
    except AssertionError as error:
        result = error.args[0]
        actual, wanted = bytes.fromhex(result[-2]), bytes.fromhex(result[-1])
        assert [i for i, pair in enumerate(zip(actual, wanted)) if pair[0] != pair[1]] == [15]
        print('State guard negative control: one-past clear detected; named fields unchanged.')
    else:
        raise AssertionError('state guard negative control unexpectedly passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max', type=int, choices=range(1, 9), default=8,
                        help='HGR_SPR_MAX for the control fixture (default 8)')
    parser.add_argument('--damage', type=int, choices=(0, 1), default=0)
    parser.add_argument('--reference', action='store_true', help='use retained C entries')
    parser.add_argument('--iie', action='store_true', help='run the control fixture on IIe')
    parser.add_argument('--full', action='store_true', help='exhaust every 16-bit pointer/size')
    parser.add_argument('--matrix', action='store_true',
                        help='check MAX 1/2/8, DAMAGE 0/1, native/C, NMOS/IIe')
    parser.add_argument('--guards', action='store_true', help='place canaries around every state array/scalar')
    parser.add_argument('--negative-guard', action='store_true', help='prove detection of a one-past clear')
    parser.add_argument('--bench', action='store_true', help='measure 16 archive-linked clients')
    parser.add_argument('--archive', action='store_true',
                        help='check 54 archive links; with --bench measure 53 render/extraction cases')
    parser.add_argument('--out', type=Path, help='benchmark JSON output')
    args = parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    if args.bench and (args.max != 8 or args.damage or args.iie or args.full or args.matrix or
                       args.guards or args.negative_guard):
        parser.error('--bench uses default MAX=8, DAMAGE=0 and NMOS')
    if args.archive and (args.max != 8 or args.damage or args.iie or args.full or
                         args.matrix or args.reference or args.guards or args.negative_guard):
        parser.error('--archive checks all MAX/DAMAGE variants; use no control-fixture options')
    if args.negative_guard:
        negative_guard_check()
    elif args.archive:
        bench_archive(args.out) if args.bench else check_archive()
    elif args.bench:
        bench(args.out, args.reference)
    elif args.matrix:
        for n in (1, 2, 8):
            for damage in (0, 1):
                for reference in (False, True):
                    for iie in (False, True):
                        check(n, damage, reference, iie, args.full, args.guards)
    else:
        check(args.max, args.damage, args.reference, args.iie, args.full, args.guards)


if __name__ == '__main__':
    main()
