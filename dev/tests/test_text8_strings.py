#!/usr/bin/env python3
"""ASM native text strings must continue across each 256-byte index wrap;
hgr_puts8_at places them from inline arguments, returns after its 4 data
bytes and copies HGR_TEXT8_AT_PAGE into ht_page."""
import tempfile
from pathlib import Path
from test_asm_boundaries import fixture
from test_hgr_native import put
from test_hgr import offset

LENGTHS = (0,255,256,257,300,960,1000)


def check(work, page):
    body = ''
    for index, length in enumerate(LENGTHS):
        body += '''    lda #42
    ldx #$20
    HGR_CLEAR_LOOP
    lda #42
    ldx #$40
    HGR_CLEAR_LOOP
'''
        body += put(ht_sl=0, ht_col=0, ht_src_lo='<string'+str(index), ht_src_hi='>string'+str(index))
        body += f'    jsr hgr_puts8\n    stx $1000\n    sta $1001\nscene{index}:\n'
    source = '''.include "apple2.inc"
.include "hgr.asm"
HGR_TEXT8_HGR_ORDER=1
.globalzp ht_sl, ht_col, ht_src_lo, ht_src_hi
.globalzp ht_wrap, ht_left, ht_page, ht_cm_ev, ht_cm_od, ht_cbit, ht_font_lo, ht_font_hi
.code
entry:
''' + put(ht_wrap=40, ht_left=0, ht_page=page, ht_cm_ev=127, ht_cm_od=127,
          ht_cbit=0, ht_font_lo='<font', ht_font_hi='>font') + body + '''done: jmp done
font: .res 512,$7F
''' + '\n'.join(f'string{i}: .res {n},$41\n.byte 0' for i,n in enumerate(LENGTHS)) + '''
.include "hgr_scanline.inc"
.include "hgr_text8.asm"
'''
    addresses = {}
    def steps(labels):
        addresses.update(labels)
        return [step for index in range(len(LENGTHS)) for step in
                (labels.until('scene'+str(index)), 'peek:2000:16384',
                 labels.peek('ht_col',2), labels.peek('ht_src_lo',2), 'peek:1000:2')]
    result = fixture(work, 'longtext'+str(page), source, steps)
    for index, length in enumerate(LENGTHS):
        expected = bytearray([42]*16384)
        for char in range(min(length,960)):
            col, row = char%40, char//40
            for y in range(row*8,row*8+8):
                expected[(8192 if page else 0)+offset(y)+col] = 127
        assert result.dumps[index*4] == expected, ('text string stopped early',page,length)
        row = min(192,((length-1)//40)*8) if length else 0
        col = (length-1)%40+1 if length else 0
        assert result.dumps[index*4+1] == bytes([col,row]), ('text cursor',page,length)
        assert result.dumps[index*4+2] == addresses['string'+str(index)].to_bytes(2,'little'), 'source pointer changed'
        assert result.dumps[index*4+3] == b'\x60\x00', 'X register or NUL return value changed'
    print(f'ASM strings page {1 if not page else 2}: lengths 0..1000, 256-byte boundaries, cursor and clipping OK.')


def check_at(work):
    """PUTS8_AT from the page-2 program byte, then a second site on page 1:
    both strings land at their inline col/scanline, execution continues after
    each 7-byte site (the a2run stops would never be reached otherwise)."""
    source = '''.include "apple2.inc"
.include "hgr.asm"
HGR_TEXT8_HGR_ORDER=1
HGR_TEXT8_AT_PAGE=mypage
.zeropage
mypage: .res 1
.code
    jmp entry
.include "hgr_text8.asm"           ; core first: ZP and the PUTS8_AT macro
.code
entry:
''' + put(ht_wrap=40, ht_left=0, ht_page=0, ht_cm_ev=127, ht_cm_od=127,
          ht_cbit=0, ht_font_lo='<font', ht_font_hi='>font', mypage='$60') + '''    lda #0
    ldx #$20
    HGR_CLEAR_LOOP
    lda #0
    ldx #$40
    HGR_CLEAR_LOOP
    PUTS8_AT first, 5, 16
first_done:
    lda #0
    sta mypage
    PUTS8_AT second, 37, 100
second_done:
done: jmp done
first: .byte "ABC",0
second: .byte "XY",0
font: .res 512,$7F
.include "hgr_scanline.inc"
.include "hgr_text8.asm"           ; again, after the callers: hgr_puts8_at
'''
    def steps(labels):
        return [labels.until('first_done'), labels.peek('ht_col', 2), labels.peek('ht_page', 1),
                labels.until('second_done'), 'peek:2000:16384', labels.peek('ht_col', 2)]
    result = fixture(work, 'putsat', source, steps)
    assert result.dumps[0] == bytes([8, 16]), ('first cursor', result.dumps[0])
    assert result.dumps[1] == b'\x60', 'HGR_TEXT8_AT_PAGE not copied'
    assert result.dumps[3] == bytes([39, 100]), ('second cursor', result.dumps[3])
    expected = bytearray(16384)
    for page, col0, sl, n in ((0x2000, 5, 16, 3), (0, 37, 100, 2)):
        for col in range(col0, col0 + n):
            for y in range(sl, sl + 8):
                expected[page + offset(y) + col] = 127
    assert result.dumps[2] == expected, 'hgr_puts8_at drew elsewhere'
    print('hgr_puts8_at: inline col/scanline/string, return after the data, page copy OK.')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='text8-strings-') as tmp:
        for page in (0,0x60):
            check(Path(tmp),page)
        check_at(Path(tmp))
