#!/usr/bin/env python3
"""Legacy TMS sprite magnification must clip without wrapping or touching holes."""
import tempfile
from pathlib import Path
from test_asm_boundaries import fixture
from test_hgr_native import put
from test_hgr import offset

CASES = [(248,184,4), (0,248,1), (0,248,2), (0,248,4),
         (248,248,4), (0,192,4), (0,184,1),
         (80,32,1), (80,32,2), (80,32,4)]


def check(work, page):
    body = ''
    for index, (x,y,scale) in enumerate(CASES):
        body += '''    lda #42
    ldx #$20
    HGR_CLEAR_LOOP
    lda #42
    ldx #$40
    HGR_CLEAR_LOOP
'''
        body += put(sp_ptr='<pattern', **{'sp_ptr+1': '>pattern'}, sp_x=x, sp_y=y)
        body += f'    jsr hgr_spr16_x{scale}\nscene{index}:\n'
    source = '''.include "apple2.inc"
.include "hgr.asm"
.globalzp sp_ptr, sp_x, sp_y
.code
entry:
    lda #0
    sta hgr_front_page
''' + f'    lda #{page}\n    jsr hgr_set_draw_page\n' + '''    lda #HSPR_WHITE
    jsr hgr_spr16_color_a
''' + body + '''done: jmp done
pattern: .res 32,$FF
.include "hgr_scanline.inc"
.include "hgr_flip.asm"
.include "hgr_sprite16.asm"
'''
    result = fixture(work, 'tms'+str(page), source, lambda labels: [step
        for i in range(len(CASES)) for step in (labels.until('scene'+str(i)), 'peek:2000:16384')])
    for index, (x,y,scale) in enumerate(CASES):
        expected = bytearray([42]*16384)
        width = 16*scale
        start = 4+x//8
        for row in range(y,min(192,y+width)):
            for col in range(start,min(40,start+(width+6)//7)):
                valid = min(7,width-7*(col-start))
                expected[(8192 if page else 0)+offset(row)+col] = (1<<valid)-1
        assert result.dumps[index] == expected, ('TMS sprite clipping',page,x,y,scale)
    print(f'TMS sprites page {1 if not page else 2}: x1/x2/x4, off-screen Y, bottom/right clipping and screen holes OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='sprite16-bounds-') as tmp:
        for page in (0,0x60):
            check(Path(tmp), page)
