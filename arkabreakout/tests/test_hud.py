#!/usr/bin/env python3
"""Compare HUD glyph pixels at their intended coordinates on both HGR pages."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dev/tools'))
import a2test
from fonts import glyph


def offset(y):
    return (y % 8) * 1024 + ((y // 8) % 8) * 128 + (y // 64) * 40


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--disk', type=Path, default=ROOT/'dist/ARKABREAKOUT.dsk')
    ap.add_argument('--labels', type=Path, default=ROOT/'arkabreakout/build/game.lbl')
    args = ap.parse_args()
    L = a2test.labels(args.labels)
    steps = [L.until('menu_loop',1500), 'key: ', L.until('loop'),
             'key:P', 'wait:15', L.until('loop')]
    snapshots = [('000000',3,1,0,'     ','WARMUP    '),
                 ('123456',5,8,59,'LASER','LAST BOARD'),
                 ('000007',2,1,9,'     ','TEN       ')]
    for score,lives,combo,level,bonus,name in snapshots:
        for field,data in [('score',score),('level_name',name+'\0')]:
            steps += [L.poke(field,ord(c),i) for i,c in enumerate(data)]
        steps += [L.poke(k,v) for k,v in [('lives',lives),('multiplier',combo),
                  ('level',level),('effect',5 if bonus=='LASER' else 0),('hud1',1),('hud2',1)]]
        steps += ['wait:12','peek:2000:16384']
    result = a2test.run(args.disk,steps)
    for index,(score,lives,combo,level,bonus,name) in enumerate(snapshots):
        screen = result.mem(0x2000,16384,index)
        top = [' ']*40
        bottom = [' ']*40
        for col,text in [(1,'S:       L:  X:  N:                  '),
                         (3,score),(12,str(lives)),(16,str(combo)),
                         (20,f'{level+1:02}'),(24,name)]:
            top[col:col+len(text)] = text
        for col,text in [(1,'SPACE/BUTTON FIRE ESC MENU '),(28,bonus),(34,'PAUSE')]:
            bottom[col:col+len(text)] = text
        for page in (0,8192):
            for y,text in [(4,top),(184,bottom)]:
                for row in range(8):
                    expected = bytes(glyph(c)[row] for c in text)
                    start = page+offset(y+row)
                    actual = screen[start:start+40]
                    assert actual==expected,(index,page,y+row,actual.hex(),expected.hex())
    print('HUD: score, lives, combo, sectors 01/10/60, board names and bonus pixels match on both pages, including cached updates.')

if __name__=='__main__':
    main()
