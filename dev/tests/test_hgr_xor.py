#!/usr/bin/env python3
"""Native XOR spans/glyphs: exact pixels, seven shifts, two pages, colour phase."""
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test

def main():
    operations=[];data=[];expected=bytearray([0xAA]*16384)
    def put(**values):
        return ''.join(f' lda #{value}\n sta {name}\n' for name,value in values.items())
    for page in (0,0x60):
        base=8192 if page else 0
        for shift in range(7):
            x,y,width,height=14+shift,20+shift*12,3+shift*3,3
            operations.append(put(hx_x=x,hx_y=y,hx_w=width,hx_h=height,hx_page=page)+' jsr hgr_xor_rect\n')
            for yy in range(y,y+height):
                for xx in range(x,x+width):expected[base+a2test.hgr_offset(yy)+xx//7]^=1<<(xx%7)
            x,y=245+shift,110+shift*8
            name=f'g{page}_{shift}'
            raw=[]
            for row in range(8):
                bits=(0x55 if row%2 else 0x3E)<<shift
                raw += [bits&127,(bits>>7)&127]
                for col in range(2):expected[base+a2test.hgr_offset(y+row)+x//7+col]^=raw[-2+col]
            data.append(name+': .byte '+','.join(map(str,raw))+'\n')
            operations.append(put(hx_x=x,hx_y=y,hx_page=page,hx_data='<'+name,**{'hx_data+1':'>'+name})+' jsr hgr_xor_sprite\n')
        operations.append(put(hx_x=255,hx_y=191,hx_w=1,hx_h=1,hx_page=page)+' jsr hgr_xor_rect\n')
        expected[base+a2test.hgr_offset(191)+255//7]^=1<<(255%7)
    body=''.join(operations)
    source=''' .include "apple2.inc"
.globalzp hx_x,hx_y,hx_w,hx_h,hx_page,hx_data
.code
 lda #$AA
 ldx #0
@fill:
.repeat 64,I
 sta $2000+I*$100,x
.endrepeat
 inx
 beq :+
 jmp @fill
:
'''+body+'''drawn:
 nop
'''+body+'''restored:
 jmp restored
HGR_XOR_DIV7=div7
HGR_XOR_MOD7=mod7
.include "hgr_xor.asm"
.rodata
div7:
.repeat 256,I
.byte I/7
.endrepeat
mod7:
.repeat 256,I
.byte I .mod 7
.endrepeat
.include "hgr_scanline.inc"
'''+''.join(data)+'\n.export drawn,restored\n'
    with tempfile.TemporaryDirectory(prefix='hgr-xor-') as tmp:
        work=Path(tmp);src=work/'xor.s';src.write_text(source)
        obj=work/'xor.o';binary=work/'xor.bin';lbl=work/'xor.lbl'
        subprocess.run(['ca65','-I',str(ROOT/'dev/lib/hgr'),'-I',str(ROOT/'dev/lib/apple2'),'-o',str(obj),str(src)],check=True)
        subprocess.run(['ld65','-C',str(ROOT/'dev/cc65/apple2_hgr.cfg'),'-Ln',str(lbl),'-o',str(binary),str(obj)],check=True)
        disk=a2test.build_disk(work,'XOR',binary);L=a2test.labels(lbl)
        r=a2test.run(disk,[L.until('drawn'),'peek:2000:16384',L.until('restored'),'peek:2000:16384'])
        assert r.mem(0x2000,16384,0)==expected,'native XOR raster/phase/page mismatch'
        assert r.mem(0x2000,16384,1)==bytes([0xAA])*16384,'erase touched colour phase, padding or other pixels'
    print('HGR XOR: native rectangles/glyphs, seven shifts, both pages and exact background restoration passed.')
if __name__=='__main__':main()
