#!/usr/bin/env python3
"""Banked transfers and native masked bytes, including pointer page crossings."""
from pathlib import Path
import tempfile
from test_hgr import build, a2test, offset
from test_dhgr import PATTERNS


def main():
    cases = [(kind, bx, width, (width*7+bx*3) % 192)
             for kind in range(2) for bx in range(2) for width in range(1, 81)]
    with tempfile.TemporaryDirectory(prefix='dhgr-blocks-') as directory:
        work = Path(directory)
        source = work/'blocks.c'
        source.write_text('''#include "dhgr_internal.h"
void painted(void); void tint(void);
unsigned char data[1024], masks[1024], readback[1024], irq_after[2];
static const struct {unsigned char kind,bx,width,y;} cases[]={'''
            + ','.join('{%d,%d,%d,%d}' % case for case in cases) + '''};
int main(void) {
    unsigned i,j,start;
    unsigned char page,count;
    if (!dhgr_init()) return 1;
    for(i=0;i<1024;++i){data[i]=(unsigned char)(i*73u+19u);masks[i]=(unsigned char)i;}
    for(page=1;page<=2;++page) {
      for(i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        dhgr_draw_page(1);dhgr_clear(6);
        dhgr_draw_page(2);dhgr_clear(9);
        dhgr_draw_page(page);
        for(j=0;j<1024;++j)readback[j]=0xD3;
        start=250u+((i*131u)&255u);
        count=cases[i].width;
        if(count>80u-cases[i].bx)count=80u-cases[i].bx;
        if(cases[i].kind) {
          dhgr_byte_address(0,cases[i].y);tint();
          dhgr_byte_address(cases[i].bx,cases[i].y);
          dhgr_count=count;dhgr_buffer=data+start;dhgr_sprite_mask=masks+start;
        }
        if(page==1){asm("sei");}else{asm("cli");}
        if(cases[i].kind)dhgr_sprite_asm();
        else dhgr_write_block(cases[i].bx,cases[i].y,cases[i].width,1,
                              data+start,cases[i].width);
        asm("php");asm("pla");asm("sta _irq_after");
        if(!cases[i].kind)dhgr_read_block(cases[i].bx,cases[i].y,cases[i].width,1,
                                         readback+start,cases[i].width);
        asm("php");asm("pla");asm("sta _irq_after+1");
        painted();asm("cli");
      }
    }
    for(;;){}
    return 0;
}
''')
        marker = work/'marker.s'
        marker.write_text('''.export _painted, resume, _tint
.import _dhgr_addr
.importzp ptr1
.code
_painted: nop
resume: rts
_tint:
        php
        sei
        lda _dhgr_addr
        sta ptr1
        lda _dhgr_addr+1
        sta ptr1+1
        ldy #39
        lda #$A5
@main: sta (ptr1),y
        dey
        bpl @main
        sta $C005
        ldy #39
        lda #$DA
@aux:  sta (ptr1),y
        dey
        bpl @aux
        sta $C004
        plp
        rts
''')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work/'test.lbl')
        steps = []
        for _ in range(2*len(cases)):
            steps += [labels.until('_painted'), labels.peek('_irq_after', 2),
                      labels.peek('_readback', 1024), 'peek:C013:2',
                      'peek:2000:16384', 'poke:C003:0', 'peek:2000:16384',
                      'poke:C002:0', labels.until('resume')]
        result = a2test.run(disk, steps, iie=True)
        frame = 0
        seen_masks = set()
        for page in range(2):
            for i, (kind, bx, width, y) in enumerate(cases):
                banks = [[bytearray(PATTERNS[color][1-bank::2])*4096
                          for bank in range(2)] for color in (6, 9)]
                count = min(width, 80-bx)
                start = 250+((i*131) & 255)
                expected_read = bytearray([0xD3])*1024
                if kind:
                    banks[page][0][offset(y):offset(y)+40] = bytes([0xA5])*40
                    banks[page][1][offset(y):offset(y)+40] = bytes([0xDA])*40
                for j in range(count):
                    bank = 1-(bx+j) % 2
                    address = offset(y)+(bx+j)//2
                    value = ((start+j)*73+19) & 127
                    if kind:
                        mask = (start+j) & 255
                        seen_masks.add(mask)
                        write = (~mask) & 127
                        old = banks[page][bank][address]
                        if write:
                            banks[page][bank][address] = (value if write == 127 else
                                                         (old & ~write) | (value & write))
                    else:
                        banks[page][bank][address] = value
                        expected_read[start+j] = value
                irq, readback, state, main, aux = result.dumps[frame*5:frame*5+5]
                assert all(v & 4 == (4 if page == 0 else 0) for v in irq), 'IRQ mask'
                assert not any(v & 128 for v in state), 'bank state'
                assert readback == expected_read, ('buffer', page, i)
                assert main == banks[0][0]+banks[1][0], ('main', page, i)
                assert aux == banks[0][1]+banks[1][1], ('aux', page, i)
                frame += 1
        assert seen_masks == set(range(256))
    print(f'DHGR blocks: {frame} C transfers/native masks; widths 1..80,')
    print('all 256 masks, both starting banks/pages, pointer crossings, palette and IRQ masks OK.')


if __name__ == '__main__':
    main()
