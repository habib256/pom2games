#!/usr/bin/env python3
"""Stable prefixes, overlapping suffixes and foreign draw-page presentation."""
import argparse
from pathlib import Path
import tempfile
from test_hgr import build
from test_sprengine import banks, SHAPES, scene
import a2test

# Active positions for both sprites in each rendered frame.
OPS=[((14,40),(16,41)),((14,40),(16,41)),
     ((14,40),(16,41)),((14,40),(16,41)),
     ((14,40),(19,42)),((15,40),(16,41)),
     ((14,40),None),((279,191),(278,190)),
     (None,None),(None,None)]+[((14,40),(16,41))]*8

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--iie',action='store_true')
    ap.add_argument('--damage',action='store_true'); args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-dirty-') as directory:
        work=Path(directory); source=work/'dirty.c'
        data=''
        for i,shape in enumerate(SHAPES):
            for name,values in zip(('data','mask'),banks(shape)):
                data+=f'static const unsigned char {name}{i}[]={{'+','.join(map(str,values))+'};\n'
            data+=f'static const hgr_mspr_t shape{i}={{data{i},mask{i},2,3}};\n'
        data+='static const unsigned positions[][4]={'+','.join(
            '{%d,%d,%d,%d}'%tuple(v for pos in op for v in (pos or (65535,0))) for op in OPS)+'};\n'
        source.write_text('#include "hgr.h"\n'+data+'''
void begin(void); void end(void);
static unsigned char pool[24];
int main(void) {
    unsigned char i,id,page;
    hgr_init(); hgr_set_draw_page(1);hgr_clear(0xaa);
    hgr_set_draw_page(2);hgr_clear(0x55);
    if(!hgr_spr_init_pool(1,pool,24,2,6)) return 1;
    if(!hgr_spr_define(0,&shape0)||!hgr_spr_define(1,&shape1)) return 2;
    for(i=0;i<18;++i) {
        page=(i&1)?1:2;
        for(id=0;id<2;++id) {
            if(positions[i][id*2]==65535) hgr_spr_hide(id);
            else hgr_spr_move(id,positions[i][id*2],positions[i][id*2+1]);
        }
        if(i==12) hgr_spr_invalidate(0); /* both page histories */
        if(i==14) hgr_spr_invalidate(2); /* only page 2 */
        if(i==2 || i==16) hgr_spr_invalidate(3); /* ignored */
        begin(); hgr_spr_render(); end();
        /* An application can use the other page after render. */
        hgr_set_draw_page(page==1?2:1);
        hgr_spr_present();
        *(volatile unsigned char*)0x1000=hgr_get_draw_page();
        *(volatile unsigned char*)0x1001=*(volatile unsigned char*)0xc01c;
        apple2_getkey();
    }
    return 0;
}''')
        asm=work/'markers.s';asm.write_text('.export _begin,_end\n.code\n_begin:rts\n_end:rts\n')
        disk=build(work,source,extra_sources=[asm],
                   cflags=['-DHGR_SPR_DAMAGE=1'] if args.damage else ())
        labels=a2test.labels(work/'test.lbl')
        steps=[]
        for _ in OPS:
            steps += [labels.until('_begin'),labels.until('_end'),labels.until('_apple2_getkey'),
                      'peek:1000:2','peek:2000:16384','press: ']
        result=a2test.run(disk,steps,iie=args.iie)
        backgrounds=[bytes([0xaa])*8192,bytes([0x55])*8192]; pages=list(backgrounds)
        for frame,op in enumerate(OPS):
            pg=1-(frame&1)
            pages[pg]=scene(backgrounds[pg],[(id,*pos) for id,pos in enumerate(op) if pos])
            state=result.dumps[2*frame]
            assert state[0]==(1 if pg==1 else 2),(frame,'next draw page')
            if args.iie: assert bool(state[1]&128)==bool(pg),(frame,'wrong presented page')
            assert result.dumps[2*frame+1]==pages[0]+pages[1],(frame,'dirty/overlapping framebuffer')
        times=[result.cycles[3*i+1]-result.cycles[3*i] for i in range(len(OPS))]
        assert times[2]<times[0]//2 and times[3]<times[1]//2,times
        assert times[12]>times[16]*2 and times[13]>times[15]*2,('both-page invalidation',times)
        assert times[14]>times[16]*2,('selected-page invalidation',times)
        if not args.damage: assert times[4]<times[5],('unchanged lower layer redrawn',times)
    print('Sprite dirty suffix: stable pages skip drawing, upper/lower movement, overlap, hiding, clipping and invalidation and foreign-page presentation OK.')

if __name__=='__main__': main()
