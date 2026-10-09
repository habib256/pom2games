#!/usr/bin/env python3
"""LOGO's real text adapter: glyph font, byte phases, palette and clipping."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
PALETTE=[0]*4+[128]*6+[0]*6


def build(work,adapter=None):
    source=work/'fixture.s'
    source.write_text('''.import text_blit_glyph
.importzp pix_x,pix_xh,pix_y,pen_color
.exportzp tmp,tmp2,mptr_lo,mptr_hi
.export plot_mode,emote_plot_background
.zeropage
fill: .res 2
tmp: .res 1
tmp2: .res 1
mptr_lo: .res 1
mptr_hi: .res 1
.bss
params: .res 4
plot_mode: .res 1
.code
entry: cld
ready:
@key: lda $c000
      bpl @key
      bit $c010
      lda #0
      sta fill
      lda #$20
      sta fill+1
      ldy #0
@fill:lda #$a5
      sta (fill),y
      iny
      bne @fill
      inc fill+1
      lda fill+1
      cmp #$60
      bne @fill
      lda params+1
      sta pix_x
      lda params+2
      sta pix_y
      lda params+3
      sta pen_color
      lda #0
      sta pix_xh
      lda params
glyph_begin:
      jsr text_blit_glyph
glyph_done:
      jmp ready
emote_plot_background: rts
''')
    cfg=work/'fixture.cfg'
    cfg.write_text('MEMORY {ZP:start=$50,size=$B0,type=rw;MAIN:start=$6000,size=$3600,type=rw,file=%O;}\nSEGMENTS {ZEROPAGE:load=ZP,type=zp;CODE:load=MAIN,type=ro;BSS:load=MAIN,type=bss;}\n')
    objects=[]
    for i,src in enumerate((source,adapter or ROOT/'logo/src/text_bitmap.asm',ROOT/'logo/src/hgr_logom2.asm')):
        obj=work/f'{i}.o'
        subprocess.run(['ca65','-g','-D','CODETANK_BUILD','-I',str(ROOT/'dev/lib/apple2'),
                        '-I',str(ROOT/'dev/lib/hgr'),'-I',str(ROOT/'dev/lib/font'),'-o',str(obj),str(src)],check=True)
        objects.append(str(obj))
    binary=work/'fixture.bin'
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(work/'fixture.lbl'),'-o',str(binary),*objects],check=True)
    L=a2test.labels(work/'fixture.lbl')
    data=binary.read_bytes();font=data[L['bbfont']-0x6000:L['bbfont']-0x6000+2048]
    return a2test.build_disk(work,'TEXT',binary),L,font


def check(work):
    disk,L,font=build(work)
    cases=[(char,x,80,15) for char in range(128) for x in range(98,105)]
    cases += [(65,x,96,pen) for pen in range(16) for x in range(98,105)]
    cases += [(char,x,y,4) for char in (0,32,65,127,193) for x,y in ((0,0),(255,184),(255,188),(255,191),(255,192),(255,250),(255,255))]
    for start in range(0,len(cases),64):
        check_batch(disk,L,font,cases[start:start+64])
    print(f'LOGO adapter: {len(cases)} exact glyph rasters, 128 characters, seven phases, all pens, clipping and preserved origins OK.')


def check_batch(disk,L,font,cases):
    steps=[L.until('ready')]
    for params in cases:
        steps += [L.poke('params',v,i) for i,v in enumerate(params)]
        steps += ['press: ',L.until('glyph_done'),'peek:2000:16384',L.peek('pix_x',3),L.until('ready')]
    result=a2test.run(disk,steps)
    data=result.data
    offset=0
    for char,x,y,pen in cases:
        expected=bytearray([165])*16384
        for row,bits in enumerate(font[(char&127)*8:(char&127)*8+8]):
            for bit in range(8):
                if bits&(1<<bit) and y+row<192 and x+bit<280:
                    a=a2test.hgr_offset(y+row)+(x+bit)//7
                    expected[a]=(expected[a]|(1<<((x+bit)%7)))&127|PALETTE[pen]
        actual=data[offset:offset+16384];offset+=16384
        assert actual==expected,('LOGO glyph raster',char,x,y,pen)
        assert data[offset:offset+3]==bytes((x,0,y)),('glyph origin changed',char,x,y)
        offset+=3
    assert len(data)==offset


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='logo-glyphs-') as tmp:check(Path(tmp))
