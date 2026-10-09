#!/usr/bin/env python3
"""Cached HUD pixels and page histories, shrinking values and colored backgrounds."""
from pathlib import Path
import tempfile
import argparse
from test_hgr import build, fonts, pixel, offset
import a2test

# page, value, invalidate (0 none, 1 selected page, 2 both), clear page
OPS=[(1,54321,0,False),(1,54321,0,False),(1,54322,0,False),
     (1,9,0,False),(1,0,0,False),(2,0,0,False),(2,0,0,False),
     (2,12345,0,False),(1,0,1,True),(2,12345,0,False),
     (1,65535,2,False),(2,65535,0,False),
     (1,8,0,False),(1,9,0,False),(1,10,0,False),
     (1,99,0,False),(1,101,0,False),(2,999,0,False),(2,1000,0,False),
     (1,9999,0,False),(1,10000,0,False),
     (2,65534,0,False),(2,65535,0,False),(2,0,0,False)]


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--iie',action='store_true')
    ap.add_argument('--compact',action='store_true'); args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-hud-') as directory:
        work=Path(directory); source=work/'hud.c'
        source.write_text('''#include "hgr.h"
static hgr_hud_field_t field, narrow;
static const struct { unsigned char page; unsigned value; unsigned char invalidate, clear; } ops[]={'''+
            ','.join('{%d,%d,%d,%d}'%op for op in OPS)+'''};
int main(void) {
    unsigned char phase,i,n;
    hgr_init();
    for (phase=0;phase<7;++phase) {
        hgr_set_draw_page(1);hgr_clear(0xaa);
        hgr_set_draw_page(2);hgr_clear(0x55);
        if (!hgr_hud_init(&field,14u+phase,32,5)) return 1;
        for (i=0;i<sizeof(ops)/sizeof(ops[0]);++i) {
            hgr_set_draw_page(ops[i].page);
            if(ops[i].clear) hgr_clear(0xaa);
            if(ops[i].invalidate) hgr_hud_invalidate(&field,ops[i].invalidate==2 ? 0 : ops[i].page);
            n=hgr_hud_putu(&field,ops[i].value);
            *(volatile unsigned char*)0x1000=n;
            apple2_getkey();
        }
    }
    hgr_set_draw_page(1);hgr_clear(0xaa);
    if(!hgr_hud_init(&narrow,180,160,3)) return 2;
    if(hgr_hud_putu(&narrow,42)!=3) return 3;
    if(hgr_hud_putu(&narrow,1000)!=HGR_HUD_INVALID) return 4;
    if(hgr_hud_init(&narrow,279,0,1) || hgr_hud_init(&narrow,0,177,1) ||
       hgr_hud_init(&narrow,0,0,0) || hgr_hud_init(&narrow,0,0,15) ||
       hgr_hud_init(0,0,0,5)) return 5;
    if(hgr_hud_putu(&narrow,42)!=0 || hgr_hud_putu(0,42)!=HGR_HUD_INVALID) return 6;
    if(hgr_hud_putu(&narrow,999)!=3 ||
       hgr_hud_putu(&narrow,1000)!=HGR_HUD_INVALID ||
       hgr_hud_putu(&narrow,999)!=0 || hgr_hud_putu(&narrow,42)!=3) return 10;
    hgr_hud_invalidate(&narrow,3); /* invalid page keeps history */
    if(hgr_hud_putu(&narrow,42)!=0) return 7;
    *(volatile unsigned char*)0x1000=99;
    apple2_getkey();
    /* Full cells at the bottom/right edge, including exact byte boundaries. */
    for(phase=0;phase<7;++phase) {
        hgr_set_draw_page(1);hgr_clear(0xaa);
        hgr_set_draw_page(2);hgr_clear(0x55);
        hgr_set_draw_page((phase&1)?2:1);
        if(!hgr_hud_init(&narrow,258u+phase,176,1)) return 8;
        for(i=0;i<10;++i) {
            if(hgr_hud_putu(&narrow,i)!=1) return 9;
            apple2_getkey();
        }
    }
    return 0;
}''')
        if args.compact:
            source.write_text(source.read_text().replace('hgr_hud_', 'hgr_hud8_')
                              .replace('0,177,1','0,185,1').replace('0,0,15','0,0,6')
                              .replace('258u+phase,176','266u+phase,184'))
        pitch, height = (8,8) if args.compact else (18,16)
        disk=build(work,source)
        labels=a2test.labels(work/'test.lbl')
        steps=[]
        for _ in range(7*len(OPS)+1):
            steps += [labels.until('_apple2_getkey'),'peek:1000:1','peek:2000:16384','key: ']
        for _ in range(70):
            steps += [labels.until('_apple2_getkey'),'peek:2000:16384','key: ']
        result=a2test.run(disk,steps,iie=args.iie)
        for phase in range(7):
            pages=[bytearray([0xaa])*8192,bytearray([0x55])*8192]
            history=[None,None]
            for i,(page,value,invalidate,clear) in enumerate(OPS):
                pg=page-1
                if clear: pages[pg]=bytearray([0xaa])*8192
                if invalidate==1: history[pg]=None
                if invalidate==2: history=[None,None]
                digits=str(value).rjust(5); changed=0
                for cell,ch in enumerate(digits):
                    if history[pg] is not None and history[pg][cell]==ch: continue
                    changed+=1
                    x=14+phase+cell*pitch
                    draw_cell(pages[pg],x,32,ch,height if cell==4 else pitch,height)
                history[pg]=digits
                index=phase*len(OPS)+i
                assert result.dumps[2*index]==bytes((changed,)),(phase,i,'changed cells')
                assert result.dumps[2*index+1]==pages[0]+pages[1],(phase,i,'HUD pixels/palette/holes')
        end=7*len(OPS)*2
        assert result.dumps[end]==b'\x63','invalid geometry/overflow changed the cache'
        page=bytearray([0xaa])*8192
        for cell,ch in enumerate(' 42'):
            draw_cell(page,180+cell*pitch,160,ch,height if cell==2 else pitch,height)
        assert result.dumps[end+1][:8192]==page,'overflow modified the field'
        for phase in range(7):
            pages=[bytearray([0xaa])*8192,bytearray([0x55])*8192]
            for value in range(10):
                draw_cell(pages[phase&1],(266 if args.compact else 258)+phase,
                          192-height,str(value),height,height)
                assert result.dumps[end+2+phase*10+value]==pages[0]+pages[1],(phase,value,'HUD right/bottom edge')
    print(f'HGR HUD {height}x{height}: {7*len(OPS)} page-aware updates, seven phases, decimal carry/wrap, invalidation, overflow and colored backgrounds and 70 right/bottom edge glyphs OK.')


def draw_cell(page,x,y,ch,width,height=16):
    scale=height//8
    for yy in range(y,y+height):
        for xx in range(x,x+width): pixel(page,xx,yy,0,white=True)
    if ch!=' ':
        for row,bits in enumerate(fonts.glyph(ch)):
            for col in range(8):
                if bits & (1<<col):
                    for dy in range(scale):
                        for dx in range(scale): pixel(page,x+scale*col+dx,y+scale*row+dy,1)


if __name__=='__main__': main()
