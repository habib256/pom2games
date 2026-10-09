#!/usr/bin/env python3
"""Saved-background byte compositor on both pages, including overlap/hide."""
from pathlib import Path
import random
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test


def build(work,page):
    source=work/'fixture.s'
    source.write_text('''.globalzp ds_data
.zeropage
fill: .res 2
.bss
params: .res 6
mask: .res 192
.code
entry:
        cld
        lda #0
        sta fill
        lda #$20
        sta fill+1
        ldy #0
@fill:  lda #$a5
        sta (fill),y
        iny
        bne @fill
        inc fill+1
        lda fill+1
        cmp #$60
        bne @fill
        jsr ds_init
ready:
@key:   lda $c000
        bpl @key
        bit $c010
        lda params
        sta ds_col
        lda params+1
        sta ds_y
        lda params+2
        sta ds_w
        lda params+3
        sta ds_h
        lda params+4
        sta ds_color
        lda params+5
        sta ds_palette
        lda #<mask
        sta ds_data
        lda #>mask
        sta ds_data+1
        jsr ds_present
done:   jmp ready
.include "hgr_sprite_update.asm"
.include "hgr_scanline.inc"
''')
    if page==2:
        # Tables are immutable here: emit page-two addresses directly.
        # Use a private table with the shared layout formula.
        source.write_text(source.read_text().replace('.include "hgr_scanline.inc"',
            'hgr_lo:\n'+'.byte '+','.join(str(a2test.hgr_offset(y)&255) for y in range(192))+
            '\nhgr_hi:\n'+'.byte '+','.join(str((0x4000+a2test.hgr_offset(y))>>8) for y in range(192))+'\n'))
    cfg=work/'fixture.cfg'
    cfg.write_text('MEMORY {ZP:start=$50,size=$B0,type=rw; MAIN:start=$6000,size=$3600,type=rw,file=%O;}\nSEGMENTS {ZEROPAGE:load=ZP,type=zp; CODE:load=MAIN,type=ro; BSS:load=MAIN,type=bss;}\n')
    subprocess.run(['ca65','-g','-I',str(ROOT/'dev/lib/hgr'),'-o',str(work/'fixture.o'),str(source)],check=True)
    binary=work/'fixture.bin'
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(work/'fixture.lbl'),'-o',str(binary),str(work/'fixture.o')],check=True)
    return a2test.build_disk(work,'SPRITE',binary),a2test.labels(work/'fixture.lbl')


def check(work,page):
    disk,L=build(work,page)
    rng=random.Random(1977)
    geometries=[(12,60,6,32),(12,60,6,32),(13,60,5,32),(13,61,5,31),
                (0,0,1,1),(34,160,6,32),(39,191,1,1),(0,0,1,0)]
    geometries += [(rng.randrange(35),rng.randrange(161),rng.randrange(1,7),rng.randrange(1,33)) for _ in range(16)]
    geometries += [(0,0,1,0),(0,0,1,0)]
    steps=[L.until('ready')]; expected=[]
    for n,(col,y,w,h) in enumerate(geometries):
        color=n%2; palette=128 if n%3 else 0
        mask=bytes(rng.randrange(128) if rng.randrange(3) else 0 for _ in range(192))
        steps += [L.poke('params',v,i) for i,v in enumerate((col,y,w,h,color,palette))]
        steps += [L.poke('mask',v,i) for i,v in enumerate(mask)]
        steps += ['press: ',L.until('done'),'peek:2000:16384',L.until('ready')]
        frame=bytearray([165])*16384
        for row in range(h):
            for x in range(w):
                bits=mask[row*6+x]
                addr=(page-1)*8192+a2test.hgr_offset(y+row)+col+x
                frame[addr] |= bits
                if bits and color: frame[addr]=(frame[addr]&127)|palette
        expected.append(frame)
    result=a2test.run(disk,steps)
    assert len(result.dumps)==len(expected)
    for index,(actual,wanted) in enumerate(zip(result.dumps,expected)):
        assert actual==wanted, (page,index,geometries[index])
    # Two frames with no foreground rows in common must never disappear
    # between removal of the old first row and arrival of the new last row.
    first=bytearray(192);first[0]=64
    last=bytearray(192);last[31*6+5]=64
    steps=[L.until('ready')]
    steps += [L.poke('params',v,i) for i,v in enumerate((12,60,6,32,0,0))]
    steps += [L.poke('mask',v,i) for i,v in enumerate(first)]
    steps += ['press: ',L.until('done'),L.until('ready')]
    steps += [L.poke('mask',v,i) for i,v in enumerate(last)]
    steps += ['press: ',L.until('ds_seed_visible'),'peek:2000:16384',L.until('done'),'peek:2000:16384']
    transition=a2test.run(disk,steps).data
    both=bytearray([165])*16384
    a=(page-1)*8192+a2test.hgr_offset(60)+12
    b=(page-1)*8192+a2test.hgr_offset(91)+17
    both[a]|=64;both[b]|=64
    assert transition[:16384]==both, ('empty intermediate frame',page)
    both[a]=165
    assert transition[16384:]==both, ('seed background corrupted',page)
    print(f'HGR page {page}: {len(expected)} byte sprite transitions, exact backgrounds, palette, overlap, hide, holes and inactive page OK.')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='hgr-sprite-update-') as tmp:
        for page in (1,2):
            work=Path(tmp)/str(page);work.mkdir();check(work,page)
