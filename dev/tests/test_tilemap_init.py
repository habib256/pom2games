#!/usr/bin/env python3
"""Tile-map initialization: complete count domain, map boundaries and transactional state."""
import argparse
import tempfile
from pathlib import Path
from test_hgr import build, a2test


def batches():
    def case(count, valid, pointer=0x1000):
        return (int(valid), *( (pointer&255,pointer>>8,0,0x18,count&255,count>>8)
                              if valid else (0xA5,)*6 ))
    for high in range(256):
        yield [case(n,1 <= n <= 256) for n in range(high*256,(high+1)*256)]
    # The first byte past the 960-cell map must not be validated.
    for high in range(4):
        yield [case(8,n >= 960) for n in range(high*256,(high+1)*256)]
    yield [case(128,n < 128) for n in range(256)]
    yield [case(n,n > 0) for n in range(256)]
    yield [case(n,False) for n in range(256)]
    for invalid in (False,True):
        yield [case(1,not invalid,0x1000+n) for n in range(256)]
    yield [case(256 if n&8 else 1,not n&7) for n in range(256)]
    for mode in range(4):
        yield [case(256 if mode==1 else 257 if mode==2 else 8,mode<2)]*256


def expected(cases):
    return bytes(case[plane] for plane in range(7) for case in cases)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iie',action='store_true')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='tilemap-init-') as directory:
        work=Path(directory);source=work/'entry.c'
        source.write_text('''#include "hgr.h"
void page_done(void); void finished(void); unsigned char align_call(void);
unsigned char records[7][256],index,align_mode;
#define STATE ((unsigned char*)0x15FC)
#define MAP ((unsigned char*)0x1000)
#define TILES ((unsigned char*)0x1800)
static void fill(unsigned char value) {
    unsigned i;for(i=0;i<1280;++i) MAP[i]=value;
}
static void check(unsigned char value) {
    unsigned i;for(i=0;i<1024;++i) if(MAP[i]!=value)for(;;) {}
}
static void prepare(void) {
    unsigned char j;for(j=0;j<8;++j) STATE[j-1]=0xA5u;
}
static void record(unsigned char result) {
    unsigned char j;records[0][index]=result;
    for(j=0;j<6;++j)records[j+1][index]=STATE[j];
    if(STATE[-1]!=0xA5u || STATE[6]!=0xA5u)for(;;) {}
}
static void call(unsigned count) {
    prepare();record(hgr_tilemap_init((hgr_tilemap_t*)STATE,MAP,TILES,count));
}
int main(void) {
    unsigned value;
    unsigned char mode;
    volatile unsigned guard=0xA55Au;
    fill(0);value=0;
    do {
        index=(unsigned char)value;call(value);++value;
        if((unsigned char)value==0)page_done();
    } while(value);
    check(0);fill(7);
    for(value=0;value<1024;++value) {
        index=(unsigned char)value;MAP[value]=8;call(8);MAP[value]=7;
        if(index==255) {check(7);page_done();}
    }
    fill(0);
    for(value=0;value<256;++value) {
        index=(unsigned char)value;MAP[959]=index;call(128);
    }
    MAP[959]=0;check(0);page_done();
    for(mode=0;mode<2;++mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;MAP[959]=(unsigned char)(value-1+mode);call(value);
        }
        MAP[959]=0;check(0);page_done();
    }
    for(mode=0;mode<2;++mode) {
        for(value=0;value<256;++value) {
            index=(unsigned char)value;fill(0);
            if(mode)MAP[value+959]=1;
            prepare();record(hgr_tilemap_init((hgr_tilemap_t*)STATE,MAP+value,TILES,1));
            if(mode)MAP[value+959]=0;
            check(0);
        }
        page_done();
    }
    for(value=0;value<256;++value) {
        index=(unsigned char)value;prepare();
        record(hgr_tilemap_init((index&1)?0:(hgr_tilemap_t*)STATE,
               (index&2)?0:MAP,(index&4)?0:TILES,(index&8)?256:1));
    }
    page_done();
    for(align_mode=0;align_mode<4;++align_mode) {
        fill(0);if(align_mode==3)MAP[959]=8;
        for(value=0;value<256;++value) {
            index=(unsigned char)value;prepare();record(align_call());
            if(guard!=0xA55Au)for(;;) {}
        }
        if(align_mode==3)MAP[959]=0;check(0);page_done();
    }
    if(guard!=0xA55Au)for(;;) {}
    finished();for(;;) {} return 0;
}
''')
        marker=work/'marker.s';marker.write_text('.export _page_done, resume, _finished\n.code\n_page_done: nop\nresume: rts\n_finished: rts\n')
        align=work/'align.s';align.write_text('''.export _align_call
.import _index, _align_mode, _hgr_tilemap_init
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
 ldy #0
 lda #0
 sta (sp),y
 iny
 lda #$18
 sta (sp),y
 iny
 lda #0
 sta (sp),y
 iny
 lda #$10
 sta (sp),y
 iny
 lda #$fc
 sta (sp),y
 iny
 lda #$15
 sta (sp),y
 iny
 lda #$a5
 sta (sp),y
 iny
 sta (sp),y
 lda #8
 ldx #0
 ldy _align_mode
 cpy #1
 bne invalid
 lda #0
 ldx #1
 bne call
invalid:
 cpy #2
 bne call
 lda #1
 tax
call:
 jsr _hgr_tilemap_init
 sta result
 cpx #0
 bne fail
 clc
 lda _index
 adc #6
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
            steps += [labels.until('_page_done',limit=10000),labels.peek('_records',1792),labels.until('resume')]
        steps += [labels.until('_finished')]
        result=a2test.run(disk,steps,iie=args.iie)
        assert len(result.dumps)==len(cases)
        for index,batch in enumerate(cases):
            assert result.dumps[index]==expected(batch),('tile init batch',index,batch[0])
        print(f'HGR tilemap init: {len(cases)*256:,} calls, all 65,536 counts, 960 invalid-ID '
              f'positions plus 64 excluded bytes, all ID bytes, map alignments/NULL combinations, '
              f'transactional state and 1,024 stack placements; IIe={args.iie}.')


if __name__=='__main__':
    main()
