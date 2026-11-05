#!/usr/bin/env python3
"""Masked HGR row oracle: ordered stores, independent pointer crossings and IRQs.

Both pages and all four kernels run with independent source/under alignments,
right/bottom clipping, tall rectangles, and enabled/disabled IRQs. Compare
whole screens and save-under buffers to a host model, including untouched
bytes, unchanged sources and arguments, and exact screen-write order.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import test_hgr
from test_hgr import DEV, ROOT, build, a2test, offset
from test_dhgr_spr import STORE

CASES=[(28+p,y,s,h) for p in range(7) for y,s,h in ((0,2,3),(40,3,16),(187,2,16))]
CASES += [(273+p,185,3,16) for p in range(7)]
CASES += [(0,0,1,192),(0,0,2,128),(21,127,4,65),(7,57,7,31),(256,0,255,1),(0,191,255,255)]
C='''#include "hgr.h"
#include "hgr_internal.h"
void started(void);void finished(void);void ended(void);
unsigned char data[2304],mask[2304],under[768],irq_after,intact,serial;
static hgr_mspr_t shape;
static const struct {unsigned x;unsigned char y,stride,h;} cases[]={CASES};
int main(void){
 unsigned i,block;unsigned char page,mode,c,irq;
 for(i=0;i<2304;++i){data[i]=(unsigned char)((i*29u+17u)&127u);mask[i]=(unsigned char)(128u|((i*73u+91u)&127u));}
 hgr_init();serial=0;
 for(page=1;page<=2;++page)for(mode=0;mode<4;++mode)for(c=0;c<sizeof(cases)/sizeof(cases[0]);++c)for(irq=0;irq<2;++irq){
  hgr_set_draw_page(1);hgr_clear(42);hgr_set_draw_page(2);hgr_clear(165);hgr_set_draw_page(page);
  for(i=0;i<768;++i)under[i]=(unsigned char)(i*13u+5u);
  shape.data=data+((serial*37u)&255u);shape.mask=mask+((serial*73u+17u)&255u);
  shape.stride=cases[c].stride;shape.h=cases[c].h;block=(unsigned)shape.stride*shape.h;
  hgr_ms_x=cases[c].x;hgr_ms_y=cases[c].y;hgr_ms_spr=&shape;hgr_ms_under=under+((serial*131u+5u)&255u);
  hgr_ms_block=(serial&2)&&block<=255?block:0;
  if(irq){asm("sei");}else{asm("cli");}
  started();
  switch(mode){case 0:hgr_ms_run();break;case 1:hgr_ms_save_run();break;case 2:hgr_ms_restore_run();break;case 3:hgr_msu_run();break;}
  asm("php");asm("pla");asm("sta _irq_after");
  intact=hgr_ms_x==cases[c].x&&hgr_ms_y==cases[c].y&&hgr_ms_spr==&shape&&hgr_ms_under==under+((serial*131u+5u)&255u)
   &&hgr_ms_block==((mode==1||mode==2)&&((serial&2)&&block<=255)?block:0);
  finished();asm("cli");++serial;
 }
 ended();for(;;){}return 0;
}'''.replace('CASES',','.join('{%d,%d,%d,%d}'%c for c in CASES))
ASM='''.export _started,_finished,_ended
.importzp sp,ptr2,ptr3
.bss
saved:.res 2
.code
_started:lda sp
 sta saved
 lda sp+1
 sta saved+1
 ; No kernel may depend on pointer scratch from an earlier call. Its documented
 ; outputs, not the volatile pointer values on return, are checked by the host.
 lda #$5a
 sta ptr2
 lda #$a5
 sta ptr2+1
 lda #$c3
 sta ptr3
 lda #$69
 sta ptr3+1
 rts
_finished:lda sp
 cmp saved
 bne bad
 lda sp+1
 cmp saved+1
 bne bad
 rts
bad:jmp bad
_ended:rts
'''


def check(source_member):
    with tempfile.TemporaryDirectory(prefix='hgr-mask-store-') as directory:
        work=Path(directory);source=work/'fixture.c';source.write_text(C);probe=work/'probe.s';probe.write_text(ASM)
        original=test_hgr.compile_source
        def compile_member(source,obj,flags):
            return original(source_member if Path(source).name=='hgr_sprmask.s' else source,obj,flags)
        test_hgr.compile_source=compile_member
        try:disk=build(work,source,extra_sources=[probe])
        finally:test_hgr.compile_source=original
        labels=a2test.labels(work/'test.lbl');steps=[]
        for _ in range(2*4*len(CASES)*2):
            steps +=[labels.until('_started'),'storewatch:2000:5FFF',labels.until('_finished'),'unstorewatch',labels.peek('_irq_after',2),labels.peek('_under',768),'peek:2000:16384','peek:C013:2']
        steps +=[labels.until('_ended'),labels.peek('_data',2304),labels.peek('_mask',2304)]
        result=a2test.run(disk,steps,iie=True,timeout=300)
        stores=[];frame=0
        for page in (1,2):
            for mode in range(4):
                for x,y,stride,height in CASES:
                    for irq in range(2):
                        serial=frame&255;data_start=serial*37&255;mask_start=(serial*73+17)&255;under_start=(serial*131+5)&255
                        saved=bytearray((i*13+5)&255 for i in range(768));screen=bytearray(bytes([42])*8192+bytes([165])*8192)
                        width=min(stride,40-x//7);rows=min(height,192-y);phase=x%7
                        order=range(width) if mode in (2,3) and width in (2,4) else range(width-1,-1,-1)
                        for row in range(rows):
                            for col in order:
                                index=row*stride+col;at=8192*(page-1)+offset(y+row)+x//7+col;u=under_start+index
                                if mode in (1,3):saved[u]=screen[at]
                                if mode in (0,3):
                                    d=((data_start+phase*stride*height+index)*29+17)&127;m=128|(((mask_start+phase*stride*height+index)*73+91)&127)
                                    screen[at]=(screen[at]&m)|d;stores.append((8192+at,screen[at],irq))
                                elif mode==2:screen[at]=saved[u];stores.append((8192+at,screen[at],irq))
                        state,under,pages,banks=result.dumps[4*frame:4*frame+4]
                        assert state[0]&4==4*irq and state[1]==1,(frame,'IRQ/args',state)
                        assert under==saved,(frame,'under')
                        assert pages==screen,(frame,'screen')
                        assert not any(v&128 for v in banks),(frame,'banks')
                        frame+=1
        guard=b''.join(result.dumps[4*frame:])
        assert guard==bytes((i*29+17)&127 for i in range(2304))+bytes(128|((i*73+91)&127) for i in range(2304)),('source guards',len(guard))
        observed=[]
        for line in result.out.splitlines():
            m=STORE.match(line)
            if m:
                assert tuple(m[i] for i in range(9,12))==('0','0','0'),line
                observed.append((int(m[2],16),int(m[3],16),1 if int(m[6],16)&4 else 0))
        assert observed==stores,('stores',len(observed),len(stores),next((i for i,(a,b)in enumerate(zip(observed,stores))if a!=b),None))
        print('HGR masked ordered oracle',frame,'calls',len(stores),'ordered writes; pages, under/source guards, args/stack, IRQ and banks PASS')


def bench(source, out):
    spec = importlib.util.spec_from_file_location('hgr_masked_bench', DEV / 'bench/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CASES = {}
    module.SCENES = {name: scene for name, scene in module.SCENES.items()
                     if name.startswith(('hgr_masked_', 'hgr_scene_phase', 'hgr_scene_large',
                                         'hgr_damage_', 'hgr_dirty_', 'hgr_pool_'))}
    original = test_hgr.compile_source

    def compile_member(member, obj, flags):
        return original(source if Path(member).name == 'hgr_sprmask.s' else member, obj, flags)

    saved = sys.argv
    try:
        test_hgr.compile_source = compile_member
        sys.argv = ['run.py'] + (['--out', str(out)] if out else [])
        module.main()
    finally:
        test_hgr.compile_source = original
        sys.argv = saved
    if out:
        report = json.loads(out.read_text())
        report['source_artifacts'] = [module.identity(source), module.identity(Path(__file__)),
                                      module.identity(DEV / 'tests/test_sprmask_setup.py')]
        out.write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEV / 'lib/hgrc/hgr_sprmask.s')
    parser.add_argument('--reference', help='also check a source file or git revision')
    parser.add_argument('--bench', action='store_true', help='measure 45 canonical masked/engine cases')
    parser.add_argument('--out', type=Path, help='benchmark JSON; reference gets a -reference sibling')
    args = parser.parse_args()
    if args.out and not args.bench:
        parser.error('--out requires --bench')
    with tempfile.TemporaryDirectory(prefix='hgr-masked-reference-') as directory:
        sources = []
        if args.reference:
            reference = Path(args.reference)
            if not reference.is_file():
                reference = Path(directory) / 'hgr_sprmask_reference.s'
                reference.write_bytes(subprocess.check_output(
                    ['git', 'show', args.reference + ':dev/lib/hgrc/hgr_sprmask.s'], cwd=ROOT))
            sources.append(('reference', reference))
        sources.append(('current', args.source))
        for label, source in sources:
            print(f'Masked rows {label}: {source}', flush=True)
            if args.bench:
                out = args.out
                if label == 'reference' and out:
                    out = out.with_name(out.stem + '-reference' + out.suffix)
                bench(source, out)
            else:
                check(source)


if __name__ == '__main__':
    main()
