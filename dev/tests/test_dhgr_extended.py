#!/usr/bin/env python3
"""DHGR page/bank, sprites, blocks, geometry, capability and exit regression."""
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
from test_dhgr import DEV, ROOT, PATTERNS, offset, pixel, color_pixel, run

spec=importlib.util.spec_from_file_location('assets',DEV/'tools/assets/convert.py')
assets=importlib.util.module_from_spec(spec); spec.loader.exec_module(assets)
sys.path.insert(0,str(DEV/'tools'))
import fonts


def build(work, mono):
    colors=[15,9,6,0]
    pixels=[assets.PALETTE[c]+(0 if i==3 else 255,) for i,c in enumerate(colors)]
    assets.png_write(work/'sprite.png',2,2,pixels)
    assets.convert(work/'sprite.png',work/'sprite','dhgr','sprite','sprite')
    sources=[DEV/'cc65/crt0_apple2.s',DEV/'tests/dhgr_extended_fixture.c',
             *[DEV/'lib/hgrc'/name for name in ('dhgr.c','dhgr_pixel.c','dhgr_getpixel.c','dhgr_pixel_address.c','dhgr_write_asm.s','dhgr_read_asm.s','dhgr_fill.c','dhgr_clear.c','dhgr_pattern.c','dhgr_plot_color.c','dhgr_fill_bits.c','dhgr_bit_rect.c','dhgr_clear_asm.s','dhgr_span_asm.s','dhgr_access_asm.s','dhgr_address.c','dhgr_asm.s','dhgr_span.c','dhgr_block.c','dhgr_sprite.c','dhgr_transfer_params.c','dhgr_block_asm.s','dhgr_text.c','dhgr_text_asm.s','dhgr_small.c','dhgr_small_params.c','dhgr_small_asm.s','dhgr_small_string.s','hgr_font.c','hgr_mode_asm.s')],
             DEV/'lib/gfx'/('gfx_backend_dhgr_mono.c' if mono else 'gfx_backend_dhgr_color.c'),
             DEV/'lib/apple2c/apple2io_asm.s']
    objects=[]
    for source in sources:
        obj=work/(source.stem+'.o')
        run(['cl65','-t','none','-Oirs','-I',work,'-I',DEV/'lib/hgrc','-I',DEV/'lib/gfx',
             '-I',DEV/'lib/apple2c','--asm-include-dir',DEV/'lib/hgrc','--asm-include-dir',DEV/'lib/apple2','-c','-o',obj,source]);objects.append(obj)
    binary=work/'test.bin'
    run(['cl65','-t','none','-C',DEV/'cc65/apple2_hgr_c.cfg','-o',binary,*objects])
    hello=work/'hello.bas';hello.write_text('10 PRINT CHR$(4);"BRUN TEST"\n')
    disk=work/'test.dsk'
    run(['python3',DEV/'tools/dos33.py','--master',DEV/'tools/dos33_system.bin','--out',disk,
         '--bas',f'HELLO={hello}','--bin',f'TEST={binary}@0x6000'])
    return disk


def dump(block, base):
    rows=re.findall(rf'(?m)^[{base:X}{base+1:X}][0-9A-F]{{3}}: ((?:[0-9A-F]{{2}} ?)+)$',block)
    return bytes.fromhex(' '.join(rows))


def main():
    emulator=DEV/'tools/a2shot/a2shot'
    for mono in (False,True):
        with tempfile.TemporaryDirectory(prefix='dhgr-extended-') as directory:
            work=Path(directory); disk=build(work,mono)
            steps=['wait:1100']
            for stage in range(24):
                steps += ['peek:1000:2','peek:C013:2','peek:C018:8',
                          'poke:C002:0','peek:2000:16384',
                          'poke:C003:0','peek:2000:16384','poke:C002:0','key: ','wait:600']
            steps+=['peek:C013:2','peek:C018:8']
            output=run([emulator,'--iie','--disk',disk,*steps])
            blocks=re.split(r'(?m)^1000:',output)[1:]
            assert len(blocks)==24
            pages=[]
            for c in (6,9):
                pat=PATTERNS[c]
                pages.append([bytearray([pat[1],pat[3]])*4096,bytearray([pat[0],pat[2]])*4096])
            for stage,block in enumerate(blocks):
                assert bytes.fromhex(block.splitlines()[0])==bytes([stage,0]),(mono,stage,'guest status')
                flags=bytes.fromhex(re.search(r'(?m)^C018: (.*)$',block)[1])
                bankflags=bytes.fromhex(re.search(r'(?m)^C013: (.*)$',block)[1])
                assert not any(v&128 for v in bankflags),(stage,'bank state')
                assert not flags[0]&128,(stage,'80STORE')
                expected_display=2 if stage==17 else 1 if stage==0 or stage>=18 else 2 if stage==1 or 3<=stage<=9 else 1
                assert bool(flags[4]&128)==(expected_display==2),(stage,'display')
                assert bool(flags[2]&128)==(stage==23),(stage,'text')
                assert bool(flags[7]&128)==(stage not in (21,23)),(stage,'80COL')
                if stage in (1,2):
                    banks=pages[stage-1]
                    for x in range(551,560):pixel(banks,x,190,1)
                    for y in range(189,192):pixel(banks,559,y,0)
                    for y in (20,21):
                        for x in range(6,14):pixel(banks,x,y,1)
                elif 3<=stage<=16:
                    page=(stage-3)//7;phase=(stage-3)%7
                    for dx,dy,c in ((0,0,15),(1,0,9),(0,1,6)):
                        color_pixel(pages[page],phase+dx,30+phase*3+dy,c)
                elif stage==17:
                    for y in range(2):
                        for i in range(3):
                            src=1+i; dst=77+i
                            pages[0][1-dst%2][offset(190+y)+dst//2]=pages[1][1-src%2][offset(30+y)+src//2]
                elif stage==19:
                    glyph=fonts.glyph('A')
                    for y,row in enumerate(glyph):
                        for x in range(8):color_pixel(pages[1],130+x,180+y,15 if row&(1<<x) else 0)
                    small_glyphs={'A':(2,5,7,5,5),'?':(7,4,2,0,2)}
                    for phase in range(7):
                        for index,ch in enumerate('A?'):
                            for y,row in enumerate(small_glyphs[ch]):
                                for x in range(5):color_pixel(pages[1],phase+index*5+x,130+phase*6+y,15 if row&(1<<x) else 0)
                    for y,row in enumerate(small_glyphs['A']):
                        for x in range(5):color_pixel(pages[1],135+x,187+y,15 if row&(1<<x) else 0)
                elif stage==20:
                    for y in range(188,192):
                        for x in range(560):pixel(pages[1],x,y,1)
                # main page1+2, then aux page1+2
                actual=bytes.fromhex(' '.join(re.findall(r'(?m)^[2345][0-9A-F]{3}: ((?:[0-9A-F]{2} ?)+)$',block)))
                expected=pages[0][0]+pages[1][0]+pages[0][1]+pages[1][1]
                assert actual==expected,(mono,stage,'framebuffer',next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None))
            tail=blocks[-1]
            flags=bytes.fromhex(re.findall(r'(?m)^C018: (.*)$',tail)[-1])
            assert flags[2]&128 and not flags[0]&128 and not flags[7]&128,'DOS exit cleanup'
            unsupported=run([emulator,'--disk',disk,'wait:1100','peek:1000:2','key: ','wait:100'])
            assert '1000: 63 00' in unsupported,'II+ must reject DHGR'
    print('DHGR extended: 48 checkpoints, both backends, both pages/banks, 7 sprite phases,')
    print('block save/restore, clipping, standard/compact white text, mode transitions, II+ rejection and DOS exit.')

if __name__=='__main__':main()
