#!/usr/bin/env python3
"""Damage boxes and transitive overlap closure against an independent graph model."""
import argparse
import random
import tempfile
from pathlib import Path
from test_hgr import build, a2test


def cases():
    rng = random.Random(0xD4A6E)
    dimensions = [(w,h) for w in (1,2,4,7,40) for h in (1,3,8,16,192) if w*h<=255]
    for count in range(1,9):
        for page in range(2):
            for invalid in range(4):
                for style in range(8):
                    slots = []
                    for i in range(8):
                        w,h = rng.choice(dimensions)
                        present,active,drawn = 1,1,1
                        px,py = 14+i*28,40
                        x,y = px,py
                        if style==1 and i==0: x+=1
                        if style==2:
                            w,h=2,3;px=x=14+i*7
                            if i==count-1:x+=1
                        if style==3 and i%2:present=active=drawn=0
                        if style==4 and i%2:active=0
                        if style==5:
                            px=250+3*i;py=187+i%4;x=279;y=191
                        if style==6:
                            x=rng.choice((0,255,256,279,280,65535));y=rng.choice((0,191,192,255))
                        if style==7:
                            present=rng.randrange(2);active=rng.randrange(2)
                            drawn=rng.randrange(2) if present else 0
                            px=rng.randrange(280);py=rng.randrange(192)
                            x=rng.randrange(280);y=rng.randrange(192)
                        slots.append((present,w,h,active,x,y,drawn,px,py))
                    yield count,page,invalid,slots


def expected(case):
    count,page,invalid,slots = case
    boxes=[];dirty=set()
    for i,(present,w,h,active,x,y,drawn,px,py) in enumerate(slots[:count]):
        visible=bool(present and active and x<280 and y<192)
        if invalid & (1<<page) or bool(drawn)!=visible or (visible and (x,y)!=(px,py)):
            dirty.add(i)
        rects=[]
        if present:
            for xx,yy in ([(px,py)] if drawn else [])+([(x,y)] if visible else []):
                rects.append((xx//7,yy,min(40,xx//7+w),min(192,yy+h)))
        boxes.append((min(r[0] for r in rects),min(r[1] for r in rects),
                      max(r[2] for r in rects),max(r[3] for r in rects)) if rects else (40,192,0,0))
    # Reachability in the undirected overlap graph; no emulation of the
    # target's slot-order loops or its fixed-point flag.
    pending=list(dirty)
    while pending:
        a=boxes[pending.pop()]
        for i,b in enumerate(boxes):
            if i not in dirty and max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]):
                dirty.add(i);pending.append(i)
    return bytes(v for b in boxes for v in b)+bytes([0xa5]*(32-4*count)),bytes([sum(1<<i for i in dirty)])


def encoded(case):
    count,page,invalid,slots=case
    data=[count,page,invalid]
    for present,w,h,active,x,y,drawn,px,py in slots:
        data.extend((present,w,h,active,x&255,x>>8,y,drawn,px&255,px>>8,py))
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='sprdamage-state-') as directory:
        work=Path(directory);source=work/'state.c'
        source.write_text('''#include "hgr.h"
extern const hgr_mspr_t *spr_shape[8];
extern unsigned spr_x[8],spr_px[16];
extern unsigned char spr_y[8],spr_active[8],spr_drawn[16],spr_py[16];
extern unsigned char spr_count,spr_invalid,spr_dirty,spr_box[8][4];
void hgr_spr_damage(void);void ready(void);void done(void);
void __fastcall__ select_page(unsigned char page);
unsigned char inputs[91];
static unsigned char dummy,slot,index,page,i;
static hgr_mspr_t shapes[8];
int main(void) {
    for(;;) {
        ready();spr_count=inputs[0];page=inputs[1]*8;select_page(inputs[1]);
        spr_invalid=inputs[2];spr_dirty=0xa5;
        for(i=0;i<16;++i){spr_px[i]=65535u;spr_py[i]=255;spr_drawn[i]=0;}
        for(slot=0;slot<8;++slot) {
            index=3+11*slot;
            shapes[slot].data=&dummy;shapes[slot].mask=&dummy;
            shapes[slot].stride=inputs[index+1];shapes[slot].h=inputs[index+2];
            spr_shape[slot]=inputs[index]?shapes+slot:0;
            spr_active[slot]=inputs[index+3];
            spr_x[slot]=inputs[index+4]+((unsigned)inputs[index+5]<<8);
            spr_y[slot]=inputs[index+6];spr_drawn[page+slot]=inputs[index+7];
            spr_px[page+slot]=inputs[index+8]+((unsigned)inputs[index+9]<<8);
            spr_py[page+slot]=inputs[index+10];
            for(i=0;i<4;++i)spr_box[slot][i]=0xa5;
        }
        hgr_spr_damage();done();
    }
    return 0;
}
''')
        marker=work/'marker.s'
        marker.write_text('''.export _ready,_done,resume,_select_page
.import spr_pgbase
.code
_select_page: asl
 asl
 asl
 sta spr_pgbase
 rts
_ready: rts
_done: nop
resume: rts
''')
        disk=build(work,source,extra_sources=[marker],cflags=['-DHGR_SPR_DAMAGE=1'])
        labels=a2test.labels(work/'test.lbl');all_cases=list(cases())
        for start in range(0,len(all_cases),32):
            batch=all_cases[start:start+32];steps=[]
            for case in batch:
                steps+=[labels.until('_ready')]+labels.poke('_inputs',encoded(case))+[
                    labels.until('_done'),labels.peek('_spr_box',32),labels.peek('_spr_dirty'),labels.until('resume')]
            result=a2test.run(disk,steps,iie=args.iie)
            assert len(result.dumps)==2*len(batch)
            for i,case in enumerate(batch):
                assert tuple(result.dumps[2*i:2*i+2])==expected(case),(start+i,case,result.dumps[2*i:2*i+2],expected(case))
        print(f'Sprite damage state: {len(all_cases)} cases, 1..8 slots, both histories, '
              f'all invalidation masks, clipping, hidden/null shapes and reverse '
              f'overlap chains match the graph model; IIe={args.iie}.')


if __name__=='__main__':main()
