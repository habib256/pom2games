; VERHILLE Arnaud — GPL-3.0. Opaque white 16x16 HUD cell, width 16/18.
; Init validates the full box; the native controller prepares the row table.
; A = ASCII digit or space. Main RAM/ZP, D=0. IRQ flags/banks unchanged.
; Reuses text parameters, destroys A/X/Y, ptr1/ptr2/tmp1. Non-reentrant.
.export _hgr_hud_cell_run, _hgr_hud_cell_width
.import _hgr_font, _hgr_rowlo, _hgr_rowhi, glyph_addr, hgr_dbl_lo, hgr_dbl_hi
.importzp _hgr_g_col, _hgr_g_bit, _hgr_g_y, _hgr_g_glyph, _hgr_t_font
.importzp ptr1, ptr2, tmp1
.bss
_hgr_hud_cell_width: .res 1
keep: .res 4
cells: .res 1
row: .res 1
m0: .res 1
m1: .res 1
m2: .res 1
shift: .res 1                   ; pen bit * 16
.code
_hgr_hud_cell_run:
        pha
        lda #<_hgr_font
        sta _hgr_t_font
        lda #>_hgr_font
        sta _hgr_t_font+1
        pla
        sec
        sbc #$20
        jsr glyph_addr
        lda #0
        sta keep+1
        sta keep+2
        sta keep+3
        sta row
        ldx _hgr_g_bit
        lda lowbits,x
        sta keep
        txa
        asl
        asl
        asl
        asl
        sta shift
        txa
        clc
        adc _hgr_hud_cell_width
        ldx #0
@divide:
        inx
        cmp #7
        bcc @last
        sbc #7
        bne @divide
        ; End on byte boundary: last byte fully owned, no extra cell.
        stx cells
        jmp @rows
@last:
        stx cells
        tay
        lda lowbits,y
        eor #$7f
        dex
        sta keep,x
@rows:
        lda row
        asl
        clc
        adc _hgr_g_y
        tay
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        iny
        lda _hgr_rowlo,y
        sta ptr2
        lda _hgr_rowhi,y
        sta ptr2+1
        ; Doubled and shifted by the pen bit through hgr_glyph_shift.s.
        ldy row
        lda (_hgr_g_glyph),y
        tax
        and #15
        ora shift
        tay
        lda hgr_dbl_lo,y
        sta m0
        lda hgr_dbl_hi,y
        sta m1
        txa
        lsr
        lsr
        lsr
        lsr
        ora shift
        tay
        lda hgr_dbl_lo,y
        ora m1
        sta m1
        lda hgr_dbl_hi,y
        sta m2
        ldy _hgr_g_col
        lda m0
        and #$7f
        jsr store0
        iny
        lda m0
        asl
        lda m1
        rol
        and #$7f
        jsr store1
        iny
        lda m1
        lsr
        lsr
        lsr
        lsr
        lsr
        lsr
        sta tmp1
        lda m2
        asl
        asl
        and #$7c
        ora tmp1
        jsr store2
        lda cells
        cmp #4
        bne @next
        iny
        lda m2
        lsr
        lsr
        lsr
        lsr
        lsr
        jsr store3
@next:
        inc row
        lda row
        cmp #8
        beq @done
        jmp @rows
@done:  rts
store0:
        sta tmp1
        lda (ptr1),y
        and keep+0
        ora tmp1
        sta (ptr1),y
        lda (ptr2),y
        and keep+0
        ora tmp1
        sta (ptr2),y
        rts
store1:
        sta tmp1
        lda (ptr1),y
        and keep+1
        ora tmp1
        sta (ptr1),y
        lda (ptr2),y
        and keep+1
        ora tmp1
        sta (ptr2),y
        rts
store2:
        sta tmp1
        lda (ptr1),y
        and keep+2
        ora tmp1
        sta (ptr1),y
        lda (ptr2),y
        and keep+2
        ora tmp1
        sta (ptr2),y
        rts
store3:
        sta tmp1
        lda (ptr1),y
        and keep+3
        ora tmp1
        sta (ptr1),y
        lda (ptr2),y
        and keep+3
        ora tmp1
        sta (ptr2),y
        rts
lowbits: .byte 0,1,3,7,15,31,63
