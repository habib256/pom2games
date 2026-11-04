#!/usr/bin/env python3
"""LORES C calls: every cell, nibble preservation, page switches and clipping."""
from pathlib import Path
import tempfile
from test_hgr import build, a2test


def main():
    with tempfile.TemporaryDirectory(prefix='lores-pixels-') as directory:
        work = Path(directory)
        source = work / 'pixels.c'
        source.write_text('''#include "hgr.h"
#include "hgr_internal.h"
void checkpoint(void);
unsigned char samples[1920], invalid, color_samples[512], cold_reads[2];
static void snapshot(void) {
    unsigned char x,y;
    unsigned i=0;
    for(y=0; y<48; ++y) for(x=0; x<40; ++x)
        samples[i++]=hgr_lores_getblock(x,y);
    checkpoint();
}
int main(void) {
    unsigned i;
    unsigned char x,y,color,phase;
    for(i=0x400; i<0xC00; ++i)
        *(unsigned char *)i=(unsigned char)(i*13u+(i>>8));
    cold_reads[0]=hgr_lores_getblock(39,47); /* nonzero x/y across lazy init */
    snapshot();
    hgr_lo_ready=0;
    hgr_lores_setblock(39,47,0xFE); /* cold/default page, high color bits ignored */
    snapshot();
    for(phase=0; phase<3; ++phase) {
        if(!phase) hgr_lo_ready=0; /* also rebuild lazily on page 2 */
        hgr_set_draw_page(phase==1 ? 1 : 2);
        if(!phase) {
            cold_reads[1]=hgr_lores_getblock(38,46);
            snapshot(); hgr_lo_ready=0; /* cold read then cold write */
        }
        for(color=0; color<16; ++color) {
            for(y=0; y<48; ++y) for(x=0; x<40; ++x)
                if(!((x+y+color)&1))
                    hgr_lores_setblock(x,y,(unsigned char)(x+3u*y+color));
            snapshot();
        }
    }
    hgr_lores_setblock(40,0,15); hgr_lores_setblock(255,47,15);
    hgr_lores_setblock(0,48,15); hgr_lores_setblock(39,255,15);
    invalid=hgr_lores_getblock(40,0)|hgr_lores_getblock(255,47)|
            hgr_lores_getblock(0,48)|hgr_lores_getblock(39,255);
    snapshot();
    for(i=0; i<256; ++i) {
        hgr_lores_setblock(0,0,(unsigned char)i);
        color_samples[2*i]=hgr_lores_getblock(0,0);
        hgr_lores_setblock(0,1,(unsigned char)i);
        color_samples[2*i+1]=hgr_lores_getblock(0,1);
    }
    checkpoint();
    for(;;) {}
    return 0;
}
''')
        marker = work / 'marker.s'
        marker.write_text('.export _checkpoint, resume\n.code\n_checkpoint: nop\nresume: rts\n')
        disk = build(work, source, extra_sources=(marker,))
        labels = a2test.labels(work / 'test.lbl')
        cases = [(0, None), (0, None), (1, None)] + [
            (page, color) for page in (1, 0, 1) for color in range(16)] + [(1, None)]
        steps = []
        for _ in cases:
            steps += [labels.until('_checkpoint'), 'peek:0400:2048',
                      labels.peek('_samples', 1920), labels.until('resume')]
        steps += [labels.peek('_invalid'), labels.until('_checkpoint'),
                  labels.peek('_color_samples',512), labels.peek('_cold_reads',2)]
        tested = []
        for iie in (False, True):
            if iie and not a2test.have_a2shot('LORES pixels on the IIe'):
                continue
            result = a2test.run(disk, steps, iie=iie)
            expected = bytearray((i*13+(i>>8)) & 255 for i in range(0x400, 0xC00))
            for index, (page, color) in enumerate(cases):
                if index == 1:
                    addr = a2test.text_offset(23)+39
                    expected[addr] = (expected[addr] & 15) | 0xE0
                pixels = bytearray()
                for y in range(48):
                    for x in range(40):
                        addr = page*1024 + a2test.text_offset(y//2) + x
                        shift = 4*(y & 1)
                        if color is not None and not ((x+y+color) & 1):
                            expected[addr] = ((expected[addr] & (255 ^ (15 << shift))) |
                                              (((x+3*y+color) & 15) << shift))
                        pixels.append((expected[addr] >> shift) & 15)
                assert result.mem(0x400, 2048, index) == expected, ('LORES write/page/hole', iie, index)
                assert result.mem(labels['_samples'], 1920, index) == pixels, ('LORES read', iie, index)
            assert result.mem(labels['_invalid'], 1) == b'\0', ('off-screen read', iie)
            assert result.mem(labels['_color_samples'],512) == bytes(c & 15 for c in range(256) for _ in range(2)), iie
            cold_expected = []
            for page,x,y in ((0,39,47),(1,38,46)):
                addr = 0x400+page*1024+a2test.text_offset(y//2)+x
                cold_expected.append((((addr*13+(addr>>8)) & 255) >> (4*(y & 1))) & 15)
            assert result.mem(labels['_cold_reads'],2) == bytes(cold_expected), ('cold read coordinates',iie)
            tested.append('IIe' if iie else 'II+')
        print('LORES pixels: all 1,920 cells, 256 color selectors, alternating nibbles, cold reads/writes on both pages, '
              f'three page switches and off-screen calls passed on {"/".join(tested)}.')


if __name__ == '__main__':
    main()
