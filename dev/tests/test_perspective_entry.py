#!/usr/bin/env python3
"""Projection public product/domain matrices, stack, IRQ and output guards.

The model uses unbounded integer products and sums. Rows/depth, input X and
shift domains are exhausted independently; every product x=0..279, q=0..255
is checked. Reference C and native entries use the same public harness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from test_hgr import DEV, compile_source, run, a2test
sys.path.insert(0,str(DEV/'bench'))
import run as bench


def products(source,iie):
    with tempfile.TemporaryDirectory(prefix='perspective-products-') as tmp:
        work=Path(tmp);c=work/'fixture.c';c.write_text('''#include "perspective.h"
unsigned shift=0;
unsigned char scale,sy=191;
a2_perspective_t camera={&scale,&shift,&sy,1};
typedef struct { a2_projected_t point; unsigned char ok; } result_t;
result_t outputs[280];
void completed(void);void done(void);
int main(void){unsigned q,x;for(q=0;q<256;++q){scale=(unsigned char)q;
    for(x=0;x<280;++x){outputs[x].point.x=0x1234;outputs[x].point.y=0x56;
    outputs[x].ok=a2_perspective_project(&camera,x,0,&outputs[x].point);}
    completed();}done();return 0;}
''')
        m=work/'marker.s';m.write_text('.export _completed,_resume,_done\n.code\n_completed:nop\n_resume:rts\n_done:rts\n')
        objects=[]
        for j,s in enumerate((DEV/'cc65/crt0_apple2.s',c,m,source)):
            o=work/f'{j}.o';compile_source(s,o,['-t','none','-Oirs','-I',DEV/'lib/perspective']);objects.append(o)
        binary=work/'p.bin';lab=work/'p.lbl';run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',lab,'-o',binary,*objects]);labels=a2test.labels(lab)
        disk=a2test.build_disk(work,'PROJ',binary) if iie else None
        steps=[] if iie else a2test.bin_steps(binary)
        for q in range(256):steps += [labels.until('_completed',3000),labels.peek('_outputs',1120),labels.until('_resume',2)]
        steps.append(labels.until('_done',2));r=a2test.run(disk,steps,iie=iie,timeout=180)
        assert len(r.dumps)==256,len(r.dumps)
        for q,data in enumerate(r.dumps):
            wanted=b''.join(bytes((x*(q or 256)//256&255,x*(q or 256)//256>>8,191,1)) for x in range(280))
            assert data==wanted,(q, data[:32],wanted[:32])
        print(source.name,iie,'71680 public products exact',flush=True)
        return dict(cases=71680,snapshot_sha256=hashlib.sha256(b"".join(r.dumps)).hexdigest())


def domains(source,iie):
    with tempfile.TemporaryDirectory(prefix='perspective-domains-') as tmp:
        work=Path(tmp);c=work/'fixture.c';c.write_text('''#include "perspective.h"
unsigned shifts[256];unsigned char scales[256],screen[256];
a2_perspective_t camera={scales,shifts,screen,1};
typedef struct {a2_projected_t point;unsigned char ok,flags,intact;} result_t;
struct {unsigned char before[8];result_t rows[256];unsigned char after[8];} frame;
unsigned char hw_before,hw_after,flags;
unsigned before_sp,after_sp;
unsigned getsp(void);void completed(void);void done(void);
int main(void){unsigned group,index,x;unsigned char mode,y;
    for(index=0;index<256;++index){scales[index]=(unsigned char)(index*71u);shifts[index]=0;screen[index]=(unsigned char)index;}
    for(index=0;index<8;++index){frame.before[index]=frame.after[index]=0xa5;}
    for(mode=0;mode<3;++mode)for(group=0;group<256;++group){
        for(index=0;index<256;++index){
            if(mode==0){camera.rows=(unsigned char)group;y=(unsigned char)index;x=279;}
            else{camera.rows=1;y=0;x=mode==1?(group*256u+index):279;shifts[0]=mode==2?(group*256u+index):0;}
            frame.rows[index].point.x=0x1234;frame.rows[index].point.y=0x56;
            if(index&1){asm("sei");}else{asm("cli");}
            if(group&1){asm("bit $C055");}else{asm("bit $C054");}
            before_sp=getsp();asm("tsx");asm("stx _hw_before");
            frame.rows[index].ok=a2_perspective_project(&camera,x,y,&frame.rows[index].point);
            asm("php");asm("pla");asm("sta _flags");asm("tsx");asm("stx _hw_after");after_sp=getsp();
            frame.rows[index].flags=flags&12;
            frame.rows[index].intact=before_sp==after_sp&&hw_before==hw_after;
        }completed();
    }done();return 0;}
''')
        m=work/'marker.s';m.write_text('.export _completed,_resume,_done,_getsp\n.importzp sp\n.code\n_completed:nop\n_resume:rts\n_done:rts\n_getsp:lda sp\nldx sp+1\nrts\n')
        objects=[]
        for j,s in enumerate((DEV/'cc65/crt0_apple2.s',c,m,source)):
            o=work/f'{j}.o';compile_source(s,o,['-t','none','-Oirs','-I',DEV/'lib/perspective']);objects.append(o)
        binary=work/'p.bin';lab=work/'p.lbl';run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-Ln',lab,'-o',binary,*objects]);labels=a2test.labels(lab)
        disk=a2test.build_disk(work,'PROJ',binary) if iie else None
        steps=[] if iie else a2test.bin_steps(binary)
        for mode in range(3):
            for group in range(256):
                steps += [labels.until('_completed',3000),labels.peek('_frame',1552)]
                if iie:steps+=['peek:C013:2','peek:C01C:1']
                steps += [labels.until('_resume',2)]
        steps.append(labels.until('_done',2));r=a2test.run(disk,steps,iie=iie,timeout=240)
        expected_dumps=768*(3 if iie else 1);assert len(r.dumps)==expected_dumps,len(r.dumps)
        for mode in range(3):
            for group in range(256):
                at=(mode*256+group)*(3 if iie else 1);wanted=bytearray([0xa5]*8)
                for index in range(256):
                    if mode==0:
                        y=index;x=279;q=index*71&255;s=0;valid=0<group<=192 and y<group
                    else:
                        y=0;x=group*256+index if mode==1 else 279;q=0;s=group*256+index if mode==2 else 0;valid=x<=279 and x+s<=279
                    px=x*(q or 256)//256+s
                    wanted+=bytes((px&255,px>>8,y,1,index%2*4,1)) if valid else bytes((0x34,0x12,0x56,0,index%2*4,1))
                wanted+=bytes([0xa5]*8)
                assert r.dumps[at]==wanted,(mode,group,r.dumps[at][:32],wanted[:32])
                if iie:
                    assert not any(v&128 for v in r.dumps[at+1]),('RAM bank',mode,group)
                    assert r.dumps[at+2][0]&128==group%2*128,('display bank',mode,group)
        print(source.name,iie,'196608 public domain calls: outputs, guards, stack, IRQ and banks exact',flush=True)
        return dict(cases=196608,snapshot_sha256=hashlib.sha256(b"".join(r.dumps)).hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,help='selected C or assembler source')
    parser.add_argument('--iie',action='store_true')
    parser.add_argument('--only',choices=('products','domains'))
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    source=(args.reference or DEV/'lib/perspective/perspective_asm.s').resolve()
    results={}
    for name,check in (('products',products),('domains',domains)):
        if args.only is None or args.only==name:results[name]=check(source,args.iie)
    digest=lambda p:dict(name=Path(p).name,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
    version=subprocess.run(['cl65','--version'],text=True,capture_output=True,check=True)
    report=dict(schema=1,source=digest(source),test_source=digest(__file__),
                support_sources=[digest(DEV/'cc65/crt0_apple2.s'),digest(DEV/'cc65/apple2_hgr_c.cfg'),
                                 digest(DEV/'lib/perspective/perspective.h')],
                compiler=(version.stdout+version.stderr).strip(),flags='-t none -Oirs',
                environment=bench.environment(args.iie),results=results)
    if args.out:args.out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
