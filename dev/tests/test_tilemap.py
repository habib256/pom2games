#!/usr/bin/env python3
"""Tile restore: both pages, clipping, palette bits, holes and atomic failure."""
from pathlib import Path
import tempfile
import argparse
from test_hgr import build, offset, a2test

OPS=[(1,0,0,40,24),(2,3,5,4,3),(2,38,22,255,255),
     (1,39,23,1,1),(0,0,0,1,1),(3,0,0,1,1),
     (1,40,0,1,1),(1,0,24,1,1),(1,0,0,0,1),(1,0,0,1,0)]
TILES=bytes((tile*61+row*23)&255 for tile in range(4) for row in range(8))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-tiles-') as directory:
        work=Path(directory); source=work/'tiles.c'
        source.write_text('''#include "hgr.h"
static unsigned char map[960];
static const unsigned char tiles[]={'''+','.join(map(str,TILES))+'''};
static const unsigned char ops[][5]={'''+','.join('{'+','.join(map(str,op))+'}' for op in OPS)+'''};
static hgr_tilemap_t ctx, copy;
int main(void){
 unsigned i; unsigned char n;
 hgr_init();hgr_set_draw_page(1);hgr_clear(0xaa);
 hgr_set_draw_page(2);hgr_clear(0x55);hgr_show_page();
 for(i=0;i<960;++i)map[i]=(i%40+i/40)&3;
 if(!hgr_tilemap_init(&ctx,map,tiles,4))return 1;
 copy=ctx;
 if(hgr_tilemap_init(&ctx,0,tiles,4)||hgr_tilemap_init(&ctx,map,0,4)||
    hgr_tilemap_init(&ctx,map,tiles,0)||hgr_tilemap_init(&ctx,map,tiles,257)||
    hgr_tilemap_init(0,map,tiles,4))return 2;
 for(n=0;n<sizeof(ops)/sizeof(ops[0]);++n){
  *(volatile unsigned char*)0x1000=hgr_tile_restore(&ctx,ops[n][0],ops[n][1],ops[n][2],ops[n][3],ops[n][4]);
  *(volatile unsigned char*)0x1001=hgr_get_draw_page();apple2_getkey();
 }
 /* Mutable map has an invalid ID in the last tile: no partial writes. */
 map[959]=4;
 if(hgr_tilemap_init(&ctx,map,tiles,4))return 3;
 if(ctx.map!=copy.map||ctx.tiles!=copy.tiles||ctx.count!=copy.count)return 4;
 if(hgr_tile_restore(&ctx,1,0,0,40,24))return 5;
 if(hgr_tile_restore(0,1,0,0,1,1))return 6;
 ctx.count=0;if(hgr_tile_restore(&ctx,1,0,0,1,1))return 7;
 ctx.count=257;if(hgr_tile_restore(&ctx,1,0,0,1,1))return 8;
 *(volatile unsigned char*)0x1000=99;apple2_getkey();
 /* count=256 accepts the complete byte ID range. */
 ctx=copy;ctx.count=256;map[959]=2;
 if(!hgr_tile_restore(&ctx,2,39,23,1,1))return 9;
 *(volatile unsigned char*)0x1000=100;apple2_getkey();return 0;
}''')
        disk=build(work,source);labels=a2test.labels(work/'test.lbl')
        steps=[]
        for _ in range(len(OPS)+2):
            steps += [labels.until('_apple2_getkey'),'peek:1000:2','peek:2000:16384','key: ']
        result=a2test.run(disk,steps,iie=args.iie)
        pages=[bytearray([0xaa])*8192,bytearray([0x55])*8192]
        for i,(page,col,row,width,height) in enumerate(OPS):
            valid=page in (1,2) and col<40 and row<24 and width and height
            if valid:
                for ty in range(row,min(24,row+height)):
                    for tx in range(col,min(40,col+width)):
                        tile=(tx+ty)&3
                        for yy in range(8):pages[page-1][offset(ty*8+yy)+tx]=TILES[tile*8+yy]
            assert result.dumps[2*i]==bytes((bool(valid),2)),(i,'return/page state')
            assert result.dumps[2*i+1]==pages[0]+pages[1],(i,'pixels/palette/holes')
        for i,marker in enumerate((99,100),start=len(OPS)):
            assert result.dumps[2*i][0]==marker,('validation',marker)
            assert result.dumps[2*i+1]==pages[0]+pages[1],('atomic failure',marker)
    print('Native tilemap: full page, clipped regions, both pages, palette/holes and transactional invalid IDs OK')


if __name__=='__main__':main()
