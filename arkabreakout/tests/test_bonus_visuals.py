#!/usr/bin/env python3
"""Bonus appearance and exact XOR restoration, both pages and seven alignments."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test

def toggle(image,x,y,w,h):
    for page in (0,8192):
        for yy in range(y,y+h):
            for xx in range(x,x+w):
                image[page+a2test.hgr_offset(yy)+xx//7] ^= 1 << (xx%7)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels',type=Path,default=ROOT/'arkabreakout/build/game.lbl')
    a=ap.parse_args();L=a2test.labels(a.labels)
    for align in range(7):
        for px,py,width in [(98+align,175,35),(2,100,28),(209,175,42)]:
            bx,by=98+align,140
            steps=[L.until('menu_loop',1500),'key: ',L.until('loop'),'key:P','wait:15',L.until('loop')]
            steps += [L.poke(k,v) for k,v in [('pad_x',px),('pad_y',py),('pad_width',width),('ball_x',bx),('ball_y',by),('capsule',0)]]
            for effect in (0,6,5,0):
                steps += [L.poke('effect',effect),L.poke('hud1',1),L.poke('hud2',1),'wait:12','peek:2000:16384']
            r=a2test.run(a.disk,steps)
            baseline=r.mem(0x2000,16384,0)
            for occurrence,effect in enumerate((6,5),1):
                expected=bytearray(baseline)
                if effect==6:
                    toggle(expected,bx+1,by+1,1,1)
                else:
                    toggle(expected,px+1,py-4,3,4)
                    toggle(expected,px+width-4,py-4,3,4)
                actual=r.mem(0x2000,16384,occurrence)
                # Bonus names legitimately change in the footer; everything
                # above it, including phase bits/padding, must match exactly.
                for page in (0,8192):
                    for y in range(184):
                        start=page+a2test.hgr_offset(y)
                        assert actual[start:start+40]==expected[start:start+40],(align,px,py,effect,page,y)
            assert r.mem(0x2000,16384,3)==baseline,'bonus switch left sprite trails'
    print('Bonus visuals: outlined Pierce ball, two aligned laser barrels, seven shifts, edge/raised paddles and exact two-page restoration passed.')

if __name__=='__main__':main()
