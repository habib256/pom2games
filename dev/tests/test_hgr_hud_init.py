#!/usr/bin/env python3
"""HUD initialization: full argument domains, state bytes, guards and stack pages."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import build, a2test


def batches():
    for compact in (0, 1):
        maximum, bottom = (5, 184) if compact else (14, 176)
        for width in (1, maximum):
            for high in range(256):
                yield [(compact, x, bottom, width, False) for x in range(high*256, (high+1)*256)]
        for x in (0, 255, 280):
            yield [(compact, x, bottom, w, False) for w in range(256)]
        for width in (1, maximum):
            extent = width*8 if compact else width*18-2
            yield [(compact, 280-extent, y, width, False) for y in range(256)]
        for overrun in (0, 1):
            yield [(compact, (280-(w*8 if compact else w*18-2)+overrun)&65535,
                    bottom, w, False) for w in range(256)]
        yield [(compact, 0, 0, w, True) for w in range(256)]
        # Four stack-page sweeps: valid, horizontal rejection, width rejection, NULL.
        for mode in range(4):
            yield [(compact, 0 if mode != 1 else 65535, 0,
                    0 if mode == 2 else maximum, mode == 3)]*256


def expected(cases):
    output = bytearray(6*256)
    for index,(compact,x,y,width,null) in enumerate(cases):
        maximum,bottom = (5,184) if compact else (14,176)
        extent = width*8 if compact else width*18-2
        valid = not null and 1 <= width <= maximum and x+extent <= 280 and y <= bottom
        state = (x&255,x>>8,y,width,0) if valid else (0xA5,)*5
        for plane,value in enumerate((int(valid),*state)):
            output[plane*256+index] = value
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='hgr-hud-init-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void page_done(void); void finished(void); unsigned char align_call(void);
unsigned char records[6][256],index,compact,align_mode;
#define STATE ((unsigned char*)0x40FC)
static void prepare(void) {
    unsigned char j;
    for(j=0;j<39;++j) STATE[j-1]=0xA5u;
}
static void record(unsigned char result) {
    unsigned char j;
    records[0][index]=result;
    for(j=0;j<5;++j) records[j+1][index]=STATE[j];
    if(STATE[-1]!=0xA5u) for(;;) {}
    for(j=5;j<38;++j) if(STATE[j]!=0xA5u) for(;;) {}
}
static void call(unsigned x,unsigned char y,unsigned char width,unsigned char null) {
    unsigned char result;
    prepare();
    if(compact) result=hgr_hud8_init(null?0:(hgr_hud8_field_t*)STATE,x,y,width);
    else result=hgr_hud_init(null?0:(hgr_hud_field_t*)STATE,x,y,width);
    record(result);
}
int main(void) {
    unsigned value,x;
    unsigned char mode,width,maximum,bottom;
    volatile unsigned guard=0xA55Au;
    for(compact=0;compact<2;++compact) {
        maximum=compact?5:14;bottom=compact?184:176;
        for(mode=0;mode<2;++mode) {
            width=mode?maximum:1;value=0;
            do { index=(unsigned char)value;call(value,bottom,width,0);
                ++value;if((unsigned char)value==0)page_done();
            } while(value);
        }
        for(mode=0;mode<3;++mode) {
            x=mode==0?0:mode==1?255:280;
            for(value=0;value<256;++value) {index=(unsigned char)value;call(x,bottom,index,0);}
            page_done();
        }
        for(mode=0;mode<2;++mode) {
            width=mode?maximum:1;x=280-(compact?width*8u:width*18u-2u);
            for(value=0;value<256;++value) {index=(unsigned char)value;call(x,index,width,0);}
            page_done();
        }
        for(mode=0;mode<2;++mode) {
            for(value=0;value<256;++value) {
                index=(unsigned char)value;x=280-(compact?value*8u:value*18u-2u)+mode;
                call(x,bottom,index,0);
            }
            page_done();
        }
        for(value=0;value<256;++value) {index=(unsigned char)value;call(0,0,index,1);}
        page_done();
        for(align_mode=0;align_mode<4;++align_mode) {
            for(value=0;value<256;++value) {
                index=(unsigned char)value;prepare();record(align_call());
                if(guard!=0xA55Au)for(;;) {}
            }
            page_done();
        }
    }
    if(guard!=0xA55Au)for(;;) {}
    finished();for(;;) {} return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _compact, _align_mode, _hgr_hud_init, _hgr_hud8_init
.importzp sp
.bss
saved_sp: .res 2
result: .res 1
.code
_align_call:
 lda sp
 sta saved_sp
 lda sp+1
 sta saved_sp+1
 lda _index
 sta sp
 lda #$91
 sta sp+1
 lda #0
 ldy #0
 sta (sp),y
 iny
 sta (sp),y
 iny
 sta (sp),y
 lda _align_mode
 cmp #1
 bne pointer
 lda #$ff
 sta (sp),y
 dey
 sta (sp),y
pointer:
 lda #$fc
 ldx #$40
 ldy _align_mode
 cpy #3
 bne store_pointer
 lda #0
 tax
store_pointer:
 ldy #3
 sta (sp),y
 iny
 txa
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda #14
 ldx _compact
 beq width
 lda #5
width:
 ldy _align_mode
 cpy #2
 bne call
 lda #0
call:
 cpx #0
 bne small
 jsr _hgr_hud_init
 jmp verify
small:
 jsr _hgr_hud8_init
verify:
 sta result
 cpx #0
 bne fail
 clc
 lda _index
 adc #5
 tax
 lda #$91
 adc #0
 cmp sp+1
 bne fail
 cpx sp
 bne fail
 ldy #0
 lda (sp),y
 cmp #$a5
 bne fail
 iny
 lda (sp),y
 cmp #$a5
 bne fail
 lda saved_sp
 sta sp
 lda saved_sp+1
 sta sp+1
 lda result
 ldx #0
 rts
fail: jmp fail
''')
        build(work,source,extra_sources=(marker,align))
        labels=a2test.labels(work/'test.lbl');disk=a2test.build_disk(work,'TEST',work/'test.bin')
        cases=list(batches());steps=[]
        for _ in cases:
            steps += [labels.until('_page_done'),labels.peek('_records',1536),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('HUD init batch',index,batch[0])
        print(f'HGR HUD init: {len(cases)*256:,} calls, all x/y/width domains, NULL, '
              f'untouched history/guards, crossing state pointer and 2,048 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
