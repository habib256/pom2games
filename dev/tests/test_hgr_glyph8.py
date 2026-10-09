#!/usr/bin/env python3
"""Native glyph STORE/OR/CELL: full eight bits, clipping, palette and pages."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test
GLYPH=bytes((255,129,66,165,0,127,128,1))
PALETTE=[0]*4+[128]*6+[0]*6


def build(work,page,colored):
    source=work/'fixture.s'
    source.write_text('''.globalzp hg_src,hg_ptr,hg_x
.zeropage
fill: .res 2
.bss
params: .res 6
.code
entry: cld
ready:
@key:  lda $c000
       bpl @key
       bit $c010
       lda #0
       sta fill
       lda #$20
       sta fill+1
       ldy #0
@fill: lda #$a5
       sta (fill),y
       iny
       bne @fill
       inc fill+1
       lda fill+1
       cmp #$60
       bne @fill
       lda #<glyph
       sta hg_src
       lda #>glyph
       sta hg_src+1
       lda params
       sta hg_x
       lda params+1
       sta hg_x+1
       lda params+2
       sta hg_y
       lda params+3
       sta hg_col
''' + ('       lda params+5\n       sta hg_color\n' if colored else '') + '''       lda params+4
       beq @store
       cmp #1
       beq @or
       jsr hgr_glyph8_cell
       jmp done
@store:jsr hgr_glyph8_store
       jmp done
@or:   jsr hgr_glyph8_or
done:  jmp ready
glyph: .byte 255,129,66,165,0,127,128,1
''' + ('HG_COLOR_TABLE=palette\npalette: .byte '+','.join(map(str,PALETTE))+'\n' if colored else '') + '''.include "hgr_glyph8.asm"
hgr_lo:
.byte '''+','.join(str(a2test.hgr_offset(y)&255) for y in range(192))+'''
hgr_hi:
.byte '''+','.join(str((page*8192+a2test.hgr_offset(y))>>8) for y in range(192))+'\n')
    cfg=work/'fixture.cfg'
    cfg.write_text('MEMORY {ZP:start=$50,size=$B0,type=rw; MAIN:start=$6000,size=$3600,type=rw,file=%O;}\nSEGMENTS {ZEROPAGE:load=ZP,type=zp; CODE:load=MAIN,type=ro; BSS:load=MAIN,type=bss;}\n')
    binary=work/'fixture.bin'
    subprocess.run(['ca65','-g','-I',str(ROOT/'dev/lib/hgr'),'-o',str(work/'fixture.o'),str(source)],check=True)
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(work/'fixture.lbl'),'-o',str(binary),str(work/'fixture.o')],check=True)
    return a2test.build_disk(work,'GLYPH',binary),a2test.labels(work/'fixture.lbl')


def reference(page,params,colored):
    xlo,xhi,y,col,mode,color=params
    x=xlo+256*xhi
    wanted=bytearray([165])*16384
    for row,bits in enumerate(GLYPH):
        py=y+row
        if py>=192: continue
        if mode==0:
            if col<40: wanted[(page-1)*8192+a2test.hgr_offset(py)+col]=bits
            continue
        if x>=280: continue
        touched=set()
        for bit in range(8):
            px=x+bit
            if px>=280: continue
            a=(page-1)*8192+a2test.hgr_offset(py)+px//7
            mask=1<<(px%7)
            if mode==2:
                wanted[a]&=127^mask
                touched.add(a)
            if bits&(1<<bit):
                wanted[a]|=mask
                if mode==1 and colored: wanted[a]=(wanted[a]&127)|PALETTE[color]
        for a in touched: wanted[a]&=127
    return wanted


def check(work,page,colored):
    disk,L=build(work,page,colored)
    positions=[(n,80) for n in range(98,105)]+[(0,0),(252,184),(255,188),(256,191),(273,80),(279,191),(280,80),(511,80),(65535,80),(10,192),(10,250),(10,255)]
    cases=[(x&255,x>>8,y,0,mode,color) for x,y in positions for mode in (1,2) for color in (4,15)]
    cases += [(0,0,y,col,0,15) for col in (0,39,40,255) for y in (0,184,188,191,192,250,255)]
    cases += [(255,0,96,0,1,color) for color in range(16)]
    steps=[L.until('ready')]
    for params in cases:
        steps += [L.poke('params',v,i) for i,v in enumerate(params)]
        steps += ['press: ',L.until('done'),'peek:2000:16384',L.until('ready')]
    result=a2test.run(disk,steps)
    assert len(result.dumps)==len(cases)
    for params,actual in zip(cases,result.dumps):
        assert actual==reference(page,params,colored),(page,colored,params)
    print(f'HGR page {page}, {"palette" if colored else "default"}: {len(cases)} exact glyph rasters, 8th bit, seven phases, clipping, cell masks, holes and inactive page OK.')


if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='hgr-glyph8-') as tmp:
        for page in (1,2):
            for colored in (False,True):
                work=Path(tmp)/f'{page}-{colored}';work.mkdir();check(work,page,colored)
