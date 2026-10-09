; VERHILLE Arnaud — GPL-3.0. Opaque white 16x16 HUD cell, width 16/18.
; Init validates the full box; the native controller prepares the row table.
; A = ASCII digit or space. Main RAM/ZP, D=0. IRQ flags/banks unchanged.
; Reuses text parameters, destroys A/X/Y, ptr1/ptr2/tmp1. Non-reentrant.
.export _hgr_hud_cell_run, _hgr_hud_cell_width
.import _hgr_font, _hgr_rowlo, _hgr_rowhi, glyph_addr
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
        ldy row
        lda (_hgr_g_glyph),y
        pha
        and #15
        tax
        lda doubled,x
        sta m0
        pla
        lsr
        lsr
        lsr
        lsr
        tax
        lda doubled,x
        sta m1
        lda #0
        sta m2
        ldx _hgr_g_bit
        beq @packed
@shift:
        asl m0
        rol m1
        rol m2
        dex
        bne @shift
@packed:
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
; Each source nibble becomes eight doubled pixels.
doubled: .byte $00,$03,$0c,$0f,$30,$33,$3c,$3f
         .byte $c0,$c3,$cc,$cf,$f0,$f3,$fc,$ff
