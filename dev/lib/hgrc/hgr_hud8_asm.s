; VERHILLE Arnaud — GPL-3.0. Opaque white 8x8 numeric HUD cell.
; Init validates geometry. A=ASCII digit/space, main RAM/ZP, D=0.
; Shared text arguments, no extra ZP. Destroys A/X/Y, ptr1/tmp1. Not reentrant.
.export _hgr_hud8_cell_run
.import hgr_hud8_digitlo, hgr_hud8_digithi, hgr_fixed_rowlo, hgr_fixed_rowhi, _hgr_base
.importzp _hgr_g_col, _hgr_g_bit, _hgr_g_y, _hgr_g_glyph
.importzp ptr1
.bss
keep0: .res 1
keep1: .res 1
row: .res 1
base: .res 1
glyph_row: .res 1
.code
_hgr_hud8_cell_run:
        cmp #$20
        bne digit
        lda #$2f
digit:
        sec
        sbc #$2f
        ldx _hgr_g_bit
        clc
        adc phase_start,x
        tax
        lda hgr_hud8_digitlo,x
        sta _hgr_g_glyph
        lda hgr_hud8_digithi,x
        sta _hgr_g_glyph+1
        ldx _hgr_g_bit
        lda lowbits,x
        sta keep0
        lda lowbits+1,x
        eor #$7f
        sta keep1
        lda #0
        sta row
        sta glyph_row
        lda _hgr_base
        bne selected_base
        lda #$20
selected_base:
        sta base
@rows:
        lda row
        clc
        adc _hgr_g_y
        tay
        lda hgr_fixed_rowlo,y
        sta ptr1
        lda hgr_fixed_rowhi,y
        ora base
        sta ptr1+1
        ldy _hgr_g_col
        lda (ptr1),y
        and keep0
        ldy glyph_row
        ora (_hgr_g_glyph),y
        ldy _hgr_g_col
        sta (ptr1),y
        iny
        lda (ptr1),y
        and keep1
        ldy glyph_row
        iny
        ora (_hgr_g_glyph),y
        ldy _hgr_g_col
        iny
        sta (ptr1),y
        inc glyph_row
        inc glyph_row
        inc row
        lda row
        cmp #8
        bne @rows
        rts
lowbits: .byte 0,1,3,7,15,31,63,127
phase_start: .byte 0,11,22,33,44,55,66
