; VERHILLE Arnaud — GPL-3.0. Opaque white 16x16 HUD cell, width 16/18.
; Init validates the full box; the native controller prepares the row table.
; A = ASCII digit or space. Main RAM/ZP, D=0. IRQ flags/banks unchanged.
; Reuses text parameters, destroys A/X/Y, ptr1..ptr4/tmp1..tmp4.
; Non-reentrant; the controller restores its field pointer after each cell.
.export _hgr_hud_cell_run, _hgr_hud_cell_width
.import _hgr_font, _hgr_rowlo, _hgr_rowhi, glyph_addr, hgr_dbl_lo, hgr_dbl_hi
.importzp _hgr_g_col, _hgr_g_bit, _hgr_g_y, _hgr_g_glyph, _hgr_t_font
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
; glyph_addr finishes using tmp2 before the row fragments are initialized.
m0 = tmp2
m1 = tmp3
m2 = tmp4
keep0 = ptr3
row = ptr3+1
keep_tail = ptr4                ; columns 2/3; column 1 is always fully owned
.bss
_hgr_hud_cell_width: .res 1
cells: .res 1
shift: .res 1                   ; pen bit * 16
.code
; Each edge is written once per row: expand in place to avoid JSR/RTS
; overhead and return addresses on the hardware stack.
.macro STORE_EDGE mask
        sta tmp1
        lda (ptr1),y
        and mask
        ora tmp1
        sta (ptr1),y
        lda (ptr2),y
        and mask
        ora tmp1
        sta (ptr2),y
.endmacro
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
        sta keep_tail
        sta keep_tail+1
        sta row
        ldx _hgr_g_bit
        lda lowbits,x
        sta keep0
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
        sta keep_tail-2,x       ; last column is 2 or 3 (width 16/18)
@rows:
        lda row
        asl                     ; row < 8, so C=0 for the addition
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
        STORE_EDGE keep0
        iny
        lda m0
        asl
        lda m1
        rol
        and #$7f
        ; The second column lies wholly inside every 16/18-pixel cell.
        sta (ptr1),y
        sta (ptr2),y
        iny
        lda m1
        asl
        rol m2
        asl
        rol m2                  ; m2 now contains doubled bits 14..21
        lda m2
        and #$7f
        STORE_EDGE keep_tail
        lda cells
        cmp #4
        bne @next
        iny
        asl m2                  ; only doubled bit 21 reaches column 3
        lda #0
        rol
        STORE_EDGE keep_tail+1
@next:
        inc row
        lda row
        cmp #8
        beq @done
        jmp @rows
@done:  rts
lowbits: .byte 0,1,3,7,15,31,63
