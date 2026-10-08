#!/usr/bin/env python3
"""Regression checks for DOS command bounds and HGR ASM text/sprite integration."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'dev/tools'))
import a2test


def fixture(work, name, source, steps, iie=False):
    src=work/(name+'.s'); src.write_text(source)
    cfg=work/(name+'.cfg'); cfg.write_text('''MEMORY {
 ZP: start=$50,size=$B0,type=rw;
 RAM: start=$6000,size=$3600,type=rw,file=%O;
}
SEGMENTS { ZEROPAGE: load=ZP,type=zp; CODE: load=RAM,type=ro; BSS: load=RAM,type=bss; }
''')
    obj=src.with_suffix('.o'); binary=src.with_suffix('.bin'); lbl=src.with_suffix('.lbl')
    subprocess.run(['ca65','-g','-I',str(ROOT/'dev/lib/apple2'),'-I',str(ROOT/'dev/lib/hgr'),'-o',str(obj),str(src)],check=True)
    subprocess.run(['ld65','-C',str(cfg),'-Ln',str(lbl),'-o',str(binary),str(obj)],check=True)
    labels=a2test.labels(lbl)
    disk=a2test.build_disk(work,name.upper(),binary)
    return a2test.run(disk,steps(labels),iie=iie)


def dos(work):
    source='''.include "apple2.inc"
DOS_CMD_MAX=8
.code
entry:
    ldx #0
    lda #$A5
@guard: sta dos_zp_prog,x
    inx
    bne @guard
    jsr dos_cmd_new
    lda #<long_command
    ldy #>long_command
    jsr dos_cmd_add
long_done:
    jsr dos_cmd_run
abort_done:
    jsr dos_cmd_new
    lda #<five
    ldy #>five
    jsr dos_cmd_add
    lda #$AB
    jsr dos_cmd_hex
exact_done:
    lda #$CD
    jsr dos_cmd_hex
hex_full_done:
    jsr dos_cmd_new
    lda #<six
    ldy #>six
    jsr dos_cmd_add
    lda #$EF
    jsr dos_cmd_hex
hex_short_done:
    jsr dos_cmd_new
reset_done:
    jmp reset_done
long_command: .byte "ABCDEFGHIJK",0
five: .byte "12345",0
six: .byte "123456",0
.bss
apple2_zp_buf: .res 256
.code
.include "dos.asm"
'''
    stages=('long_done','abort_done','exact_done','hex_full_done','hex_short_done','reset_done')
    result=fixture(work,'dosbounds',source,lambda l:[s for name in stages for s in
                    (l.until(name),l.peek('dos_cmd_buf',8),l.peek('dos_zp_prog',256))])
    expected=(b'ABCDEFG\0',b'ABCDEFG\0',b'12345AB\0',b'12345AB\0',b'123456\0\0')
    for i,data in enumerate(expected):
        assert result.dumps[i*2][:len(data)] == data, (stages[i],result.dumps[i*2])
        assert result.dumps[i*2+1] == bytes([0xA5])*256, 'command overwrote ZP snapshot or ran after overflow'
    assert result.dumps[10][0] == 0, 'dos_cmd_new did not recover'


def text(work):
    source='''.include "apple2.inc"
HGR_TEXT8_HGR_ORDER=1
.globalzp ht_sl, ht_col, ht_left, ht_wrap, ht_page, ht_cbit
.globalzp ht_cm_ev, ht_cm_od, ht_font_lo, ht_font_hi
.include "hgr.asm"
.code
entry:
    lda #0
    ldx #$20
    HGR_CLEAR_LOOP
    lda #0
    ldx #$40
    HGR_CLEAR_LOOP
    ldx #0
    lda #$5A
@guard: sta $8500,x
    inx
    bne @guard
    lda #0
    sta ht_col
    sta ht_left
    sta ht_page
    sta ht_cbit
    lda #40
    sta ht_wrap
    lda #$7F
    sta ht_cm_ev
    sta ht_cm_od
    lda #<font
    sta ht_font_lo
    lda #>font
    sta ht_font_hi
    lda #190
    sta ht_sl
    lda #' '
    jsr hgr_putc8
bottom_done:
    lda #248
    sta ht_sl
    lda #40
    sta ht_col
    lda #' '
    jsr hgr_putc8
wrap_done:
    jmp wrap_done
font: .res 512,$7F
.include "hgr_scanline.inc"
.include "hgr_text8.asm"
'''
    result=fixture(work,'textbounds',source,lambda l:[l.until('bottom_done'),'peek:2000:16384','peek:8500:256',
                            l.until('wrap_done'),'peek:2000:16384','peek:8500:256'])
    expected=bytearray(16384)
    expected[a2test.hgr_offset(190)]=0x7F
    expected[a2test.hgr_offset(191)]=0x7F
    assert result.dumps[0] == expected, 'bottom glyph did not clip'
    assert result.dumps[1] == bytes([0x5A])*256, 'bottom glyph wrote outside video memory'
    assert result.dumps[3] == bytes([0x5A])*256, 'wrapped glyph wrote outside video memory'
    assert result.dumps[2] == expected, 'off-screen cursor wrapped back to the top'


def sprite_mix(work):
    for order in (('hgr_sprite16.asm','hgr_sprite_packed.asm'),
                  ('hgr_sprite_packed.asm','hgr_sprite16.asm')):
        source='.code\nentry: jmp entry\n.include "hgr_scanline.inc"\n'+''.join(f'.include "{file}"\n' for file in order)
        fixture(work,'mix'+str(order[0]=='hgr_sprite16.asm'),source,lambda l:[l.until('entry')])


def packed_palette(work, background=255, source_byte=0):
    # Source padding can be lit. Both black and lit sprites must preserve
    # outside pixels, holes and the other page while installing their palette.
    cases = [(page, width, tail, palette, col, colored)
             for page in (0, 0x60) for width in (1, 3)
             for tail in (1, 0x7F) for palette in (0, 0x80)
             for col in (1, 2) for colored in (False, True)]
    body = ''
    for i, (page, width, tail, palette, col, colored) in enumerate(cases):
        body += f'''    jsr fill_background
    lda #{page}
    jsr hgr_set_draw_page
    lda #<sprite_data
    sta sp_ptr
    lda #>sprite_data
    sta sp_ptr+1
    lda #{col}
    sta hsp_col
    lda #1
    sta packed_rows
    lda #189
    sta sp_yy
    lda #{width}
    sta sp_wout
    lda #3
    sta packed_repeat
    lda #{tail}
    sta packed_tail
    lda #{0x2a if colored else 0x7f}
    sta sp_cm_ev
    lda #{0x55 if colored else 0x7f}
    sta sp_cm_od
    lda #{palette}
    sta sp_cbit
    jsr hgr_sprite_packed
packed_done_{i}:
'''
    source = '''.include "apple2.inc"
.globalzp sp_ptr, sp_yy, sp_wout, sp_cm_ev, sp_cm_od, sp_cbit
.include "hgr.asm"
.code
entry:
''' + body + f'''    jmp entry
fill_background:
    lda #{background}
    ldx #$20
    HGR_CLEAR_LOOP
    ldx #$40
    HGR_CLEAR_LOOP
    rts
sprite_data: .byte {source_byte},{source_byte},{source_byte}
.include "hgr_scanline.inc"
.include "hgr_flip.asm"
.include "hgr_sprite_packed.asm"
'''
    result = fixture(work, f'packedpalette{background}_{source_byte}', source, lambda l:
                     [step for i in range(len(cases)) for step in
                      (l.until(f'packed_done_{i}'), 'peek:2000:16384')])
    for data, (page, width, tail, palette, col, colored) in zip(result.dumps, cases):
        expected = bytearray([background] * 16384)
        base = 8192 if page else 0
        for y in range(189, 192):
            offset = base + a2test.hgr_offset(y) + col
            for x in range(width):
                mask = (0x2a if (col+x) % 2 == 0 else 0x55) if colored else 0x7f
                bits = source_byte & mask
                if x == width - 1:
                    bits = (bits & tail) | (background & (0x7f ^ tail))
                expected[offset+x] = bits | palette
        assert data == expected, f'packed sprite edge: {page=}, {width=}, {tail=}, {palette=}, {col=}, {colored=}, {background=}, {source_byte=}'


def packed_edges(work):
    for background in (0, 255):
        for source_byte in (0, 255):
            packed_palette(work, background, source_byte)


def main():
    with tempfile.TemporaryDirectory(prefix='asm-bounds-') as tmp:
        work=Path(tmp)
        for name,fn in (('DOS command bounds',dos),('HGR text edges',text),('mixed sprite modules',sprite_mix),
                        ('packed sprite edges and palette',packed_edges)):
            fn(work)
            print(name+': OK')


if __name__=='__main__':
    main()
