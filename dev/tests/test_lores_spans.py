#!/usr/bin/env python3
"""LORES runs/rectangles against pixels: clipping, paired rows and preservation."""
from pathlib import Path
import random
import tempfile
from test_hgr import build, a2test


def cases():
    result = []
    for y in range(48):
        for x0, x1 in ((0,39), (1,38), (39,39), (0,0), (5,3), (38,255)):
            result.append((0, x0, y, x1, 0, y*13 & 255))
    for x in range(40):
        for y0, y1 in ((0,47), (1,46), (0,0), (1,1), (46,47), (47,47), (47,255), (20,3)):
            result.append((1, x, y0, 0, y1, x*17 & 255))
    for x in (0,1,38,39,40,255):
        for y in (0,1,46,47,48,255):
            result += [(0,x,y,255,0,0xFA), (1,x,y,0,255,0xB6)]
            for w,h in ((0,0),(0,255),(255,0),(1,1),(2,2),(3,3),(255,255),(40,48),(255,1),(1,255)):
                result.append((2,x,y,w,h,(x+y+7) & 255))
    rng = random.Random(314)
    for _ in range(64):
        result.append((2,rng.randrange(44),rng.randrange(52),rng.randrange(256),
                       rng.randrange(256),rng.randrange(256)))
    return [(kind,page,x,y,w,h,color) for kind,x,y,w,h,color in result for page in (1,2)]


def expected(case):
    kind,page,x,y,w,h,color = case
    screen = bytearray([0xA5]*2048)
    if kind == 0:
        right, bottom = min(w+1,40), min(y+1,48)
    elif kind == 1:
        right, bottom = min(x+1,40), min(h+1,48)
    else:
        right, bottom = min(x+w,40), min(y+h,48)
    for yy in range(y,bottom):
        shift = (yy & 1)*4
        for xx in range(x,right):
            addr = (page-1)*1024+a2test.text_offset(yy//2)+xx
            screen[addr] = (screen[addr] & (255 ^ (15 << shift))) | ((color & 15) << shift)
    return screen


def main():
    with tempfile.TemporaryDirectory(prefix='lores-spans-') as directory:
        work = Path(directory)
        source = work / 'spans.c'
        source.write_text('''#include "hgr.h"
void ready(void); void done(void);
unsigned char args[7];
int main(void) {
    unsigned i;
    for(;;) {
        ready();
        for(i=0x400; i<0xC00; ++i) *(unsigned char *)i=0xA5;
        hgr_set_draw_page(args[1]);
        if(args[0]==0) hgr_lores_hlin(args[2],args[4],args[3],args[6]);
        else if(args[0]==1) hgr_lores_vlin(args[2],args[3],args[5],args[6]);
        else hgr_lores_fill_rect(args[2],args[3],args[4],args[5],args[6]);
        done();
    }
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _ready, _done\n.code\n_ready: rts\n_done: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work / 'test.lbl')
        entries = cases()
        tested = []
        for iie in (False,True):
            if iie and not a2test.have_a2shot('LORES spans on IIe'):
                continue
            for start in range(0,len(entries),128):
                batch = entries[start:start+128]
                steps = [labels.until('_ready')]
                for case in batch:
                    steps += labels.poke('_args',case)
                    steps += [labels.until('_done'), 'peek:0400:2048', labels.until('_ready')]
                result = a2test.run(disk,steps,iie=iie)
                assert len(result.dumps) == len(batch)
                for case, actual in zip(batch,result.dumps):
                    assert actual == expected(case), ('LORES span/rectangle',iie,case)
            tested.append('IIe' if iie else 'II+')
        print(f'LORES spans: {len(entries):,} cases per target ({"/".join(tested)}), '
              'every row/column, nibble edges, full bytes, clipping, empty ranges, '
              '255-byte extents, firmware holes and other page preserved.')


if __name__ == '__main__':
    main()
