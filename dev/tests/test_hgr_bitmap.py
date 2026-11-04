#!/usr/bin/env python3
"""MSB-first HGR bitmaps: source/destination byte boundaries and clipping."""
import argparse
from pathlib import Path
import tempfile

from test_hgr import build, a2test, pixel, DEV, run, offset


def bitmap(page, x, y, width, height, pattern, mode, start):
    stride = (width+7)//8
    for row in range(min(height, max(0, 192-y))):
        for col in range(min(width, max(0, 280-x))):
            address = start + row*stride + col//8
            value = (0 if pattern == 1 else 255 if pattern == 2 else
                     row*stride + col//8 if pattern == 3 else
                     ((address*73+19) ^ (address >> 3)) & 255)
            if value & (128 >> (col % 8)):
                pixel(page, x+col, y+row, mode in (0,2),
                      mode='xor' if mode == 2 else 'set')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie', action='store_true')
    parser.add_argument('--folded', action='store_true')
    args = parser.parse_args()
    boxes = [(28+phase, 63, width, 3, 0)
             for phase in range(7) for width in (1, 7, 8, 9, 14, 15, 16, 17)]
    boxes += [(x, 127, width, 3, 0)
              for x in (252, 255, 256, 272, 273, 279) for width in (1, 8, 16, 255)]
    boxes += [(0, 0, 255, 255, 0), (279, 191, 255, 255, 0),
              (0, 0, 0, 1, 0), (0, 0, 1, 0, 0), (280, 0, 8, 8, 0),
              (65535, 0, 8, 8, 0), (0, 192, 8, 8, 0), (0, 255, 8, 8, 0)]
    boxes += [(28+phase, 7, 16, 8, pattern)
              for phase in range(7) for pattern in (1, 2)]
    boxes += [(28+phase, 31, 16, 128, 3) for phase in range(7)]
    fixed_boxes = list(boxes)
    boxes += [(28+width%7, 189, width, 255, 0) for width in range(256)]
    cold = [(255,189,255,255), (0,0,0,255), (0,0,255,0),
            (65535,0,255,255), (0,192,1,1)]
    cases = [(*box, mode) for box in boxes for mode in range(3)]
    with tempfile.TemporaryDirectory(prefix='hgr-bitmap-') as directory:
        work = Path(directory)
        source = work / 'bitmap.c'
        source.write_text('''#include "hgr.h"
void painted(void); void cold_ready(void); void cold_done(void);
unsigned char cold_index,cold_mode;
static unsigned char data[6400];
#pragma bss-name(push,"LOWBSS")
static unsigned char all_bytes[256];
#pragma bss-name(pop)
static const unsigned char empty[16]={0};
static const unsigned char solid[16]={255,255,255,255,255,255,255,255,
                                     255,255,255,255,255,255,255,255};
static const struct {unsigned x; unsigned char y,w,h,pattern;} cases[]={'''
                          + ','.join('{%du,%du,%du,%du,%du}' % box for box in fixed_boxes) + '''};
static const struct {unsigned x; unsigned char y,w,h;} cold[]={'''
                          + ','.join('{%du,%du,%du,%du}' % box for box in cold) + '''};
int main(void) {
    unsigned i, start;
    unsigned char page,mode;
    const unsigned char *bitmap;
    for (i=0; i<sizeof(data); ++i) data[i]=(unsigned char)((i*73u+19u)^(i>>3));
    for (i=0; i<256; ++i) all_bytes[i]=(unsigned char)i;
    for (i=0x2000; i<0x6000; ++i) *(unsigned char *)i=0xA5;
    cold_ready();
    hgr_blit(cold[cold_index].x,cold[cold_index].y,cold[cold_index].w,
             cold[cold_index].h,data+127,cold_mode);
    cold_done();
    hgr_init();
    for (page=1; page<=2; ++page) {
        for (i=0; i<sizeof(cases)/sizeof(cases[0])+256u; ++i) {
          for (mode=0; mode<3; ++mode) {
            hgr_set_draw_page(1); hgr_clear(0xA5);
            hgr_set_draw_page(2); hgr_clear(0xDA);
            hgr_set_draw_page(page);
            start=(unsigned)mode*127u;
            if(i<sizeof(cases)/sizeof(cases[0])) {
            bitmap=cases[i].pattern == 1 ? empty :
                   cases[i].pattern == 2 ? solid :
                   cases[i].pattern == 3 ? (const unsigned char *)all_bytes :
                   (const unsigned char *)(data+start);
            hgr_blit(cases[i].x,cases[i].y,cases[i].w,cases[i].h,bitmap,mode);
            } else {
                hgr_blit(28u+(i-sizeof(cases)/sizeof(cases[0]))%7u,189,
                         (unsigned char)(i-sizeof(cases)/sizeof(cases[0])),255,data+start,mode);
            }
            painted();
          }
        }
    }
    for (;;) {}
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _painted, resume, _cold_ready, _cold_done\n.code\n'
                          '_cold_ready: rts\n_cold_done: rts\n_painted: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        if args.folded:
            folded=work/'folded.o'
            run(['ca65','-D','HGRC_X7_FOLDED=1','-o',folded,DEV/'lib/hgrc/hgr_columns.s'])
            run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg',
                 '-m',work/'test.map','-Ln',work/'test.lbl','-o',work/'test.bin',
                 work/'crt0_apple2.o',work/'bitmap.o',work/'apple2io_asm.o',folded,work/'hgrc.lib'])
            disk=a2test.build_disk(work,'TEST',work/'test.bin')
        labels = a2test.labels(work / 'test.lbl')
        for base in (0,0x40):
            for index,box in enumerate(cold):
                for mode in (0,1,2,255):
                    steps=[labels.until('_cold_ready'),labels.poke('_cold_index',index),
                           labels.poke('_cold_mode',mode),labels.poke('_hgr_base',base),
                           labels.until('_cold_done'),'peek:2000:16384',
                           labels.peek('_hgr_rowlo',192),labels.peek('_hgr_rowhi',192),
                           labels.peek('_hgr_col7',280),labels.peek('_hgr_mask7',280)]
                    result=a2test.run(disk,steps,iie=args.iie)
                    pages=[bytearray([0xA5])*8192 for _ in range(2)]
                    bitmap(pages[base==0x40],*box,0,mode,127)
                    assert result.mem(0x2000,16384)==pages[0]+pages[1],('cold',base,box,mode)
                    addresses=[((base or 0x20)<<8)+offset(y) for y in range(192)]
                    for name,shift in (('_hgr_rowlo',0),('_hgr_rowhi',8)):
                        assert result.mem(labels[name],192)==bytes(a>>shift&255 for a in addresses),('cold',name)
                    assert result.mem(labels['_hgr_col7'],280)==bytes(x//7 for x in range(280)),('cold','columns')
                    assert result.mem(labels['_hgr_mask7'],280)==bytes(1<<(x%7) for x in range(280)),('cold','masks')
        steps = []
        for _ in range(2*len(cases)):
            steps += [labels.until('_painted'), 'peek:2000:16384', labels.until('resume')]
        result = a2test.run(disk, steps, iie=args.iie)
        frame = 0
        for page in range(2):
            for index, (x, y, width, height, pattern, mode) in enumerate(cases):
                pages = [bytearray([0xA5])*8192, bytearray([0xDA])*8192]
                bitmap(pages[page],x,y,width,height,pattern,mode,(index%3)*127)
                assert result.dumps[frame] == pages[0]+pages[1], (
                    page+1, x, y, width, height, pattern, mode)
                frame += 1
    print(f'HGR bitmaps: {frame} warm SET/CLEAR/XOR and {len(cold)*8} cold cases, seven phases, '
          f'folded={args.folded}, IIe={args.iie};')
    print('all 256 source bytes, source boundaries/stride, clipping, both pages, palette and holes OK.')


if __name__ == '__main__':
    main()
