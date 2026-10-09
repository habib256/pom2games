#!/usr/bin/env python3
"""Simplified title, ESC options, sound, difficulty, controller and DOS exit."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
from fonts import glyph

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk',type=Path,default=ROOT/'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels',type=Path,default=ROOT/'arkabreakout/build/game.lbl')
    a=ap.parse_args();L=a2test.labels(a.labels)
    boot=[L.until('menu_loop',2000)]
    options=['key:\\e',L.until('title_menu_key')]
    def run(steps):return a2test.run(a.disk,boot+steps)
    r=run(['peek:2000:8192']+options+['peek:2000:8192','key:S',L.until('title_menu_key'),L.peek('sound_muted'),'key:S',L.until('title_menu_key'),L.peek('sound_muted'),'key:\\e',L.until('menu_loop'),L.peek('state')])
    assert r.mem(L['sound_muted'],1,0)==b'\1' and r.mem(L['sound_muted'],1,1)==b'\0'
    assert r.mem(L['state'],1)==b'\0'
    title=r.mem(0x2000,8192,0);menu=r.mem(0x2000,8192,1)
    for image,text,col,y in [(title,'SPACE / ENTER : PLAY',10,104),(title,'ESC : MENU',14,132),(menu,'ARKABREAKOUT MENU',11,24),(menu,'ESC : TITLE',12,180)]:
        for row in range(8):
            start=a2test.hgr_offset(y+row)+col
            assert image[start:start+len(text)]==bytes(glyph(c)[row] for c in text)
    # Old dense instruction rows have left the title.
    for y in list(range(88,96))+list(range(144,176)):
        start=a2test.hgr_offset(y)
        assert title[start:start+40]==bytes(40)
    for key,mode in [('1',0),('2',1),('3',2)]:
        r=run(options+[f'key:{key}',L.until('menu_loop'),L.peek('difficulty')])
        assert r.mem(L['difficulty'],1)==bytes([mode])
    for key,controller in [('K',0),('J',1)]:
        r=run(options+[f'key:{key}',L.until('loop'),L.peek('state'),L.peek('mode')])
        assert r.mem(L['state'],1)==b'\1' and r.mem(L['mode'],1)==bytes([controller])
    r=run(options+['key: ',L.until('loop'),L.peek('state')]);assert r.mem(L['state'],1)==b'\1'
    r=run(options+['key:Q','wait:300','text']);assert ']' in r.out
    print('Title/menu: simplified glyph layout, ESC open/close, sound, 3 difficulties, controller starts, play and DOS exit passed.')

if __name__=='__main__':main()
