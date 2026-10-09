#!/usr/bin/env python3
"""Check centered title bands and brick relief at the actual gameplay grid."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels',type=Path,default=ROOT/'arkabreakout/build/game.lbl')
    a=ap.parse_args();L=a2test.labels(a.labels)
    boot=[L.until('menu_loop',2000)]
    title=a2test.run(a.disk,boot+['peek:2000:8192']).mem(0x2000,8192)
    for row in (24,60):
        pixels=[]
        for y in range(row,row+8):
            for x in range(280):
                if title[a2test.hgr_offset(y)+x//7] & (1<<(x%7)):
                    pixels.append(x)
        left,right=min(pixels),279-max(pixels)
        assert abs(left-right)<=1,(row,left,right)
        assert left>=14 and right>=14
        # Twelve separated brick caps, framed symmetrically around the logo.
        line=title[a2test.hgr_offset(row):a2test.hgr_offset(row)+40]
        assert sum(bool(b&127) for b in line)==36
    for sector in (0,20,59):
        steps=['key: ',L.until('loop'),'key:P','wait:15',L.poke('level',sector),L.poke('furthest',59),'key:\\e',L.until('menu_input'),'key: ',L.until('loop'),'key:P','wait:15',L.peek('bricks',96),'peek:2000:16384']
        r=a2test.run(a.disk,boot+steps);bricks=r.mem(L['bricks'],96);image=r.mem(0x2000,16384)
        for i,kind in enumerate(bricks):
            row,col=divmod(i,12);y=24+row*12;x=col*3
            for page in (0,8192):
                top=page+a2test.hgr_offset(y)+x
                bottom=page+a2test.hgr_offset(y+7)+x
                if kind:
                    assert image[top+1]==127,(sector,i,page,'highlight row/grid alignment')
                    assert image[top]&6==6
                    assert image[top+2]&0x70==0,'right shadow/gap'
                    assert image[bottom]&6==6,'left bevel'
                    assert image[bottom+1]==image[bottom+2]==0,'lower shadow'
                else:
                    assert image[top+1]==image[top+2]==0,'empty tile erased'
    print('Bricks: centered title bands, both gameplay pages, correct grid rows, lit bevel, right/bottom shadows and empty-cell erasure passed.')

if __name__=='__main__':main()
