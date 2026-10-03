; hgr_text8_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_blit_glyph8, _hgr_puts_run8
.import _hgr_rowhi, _hgr_rowlo
.importzp _hgr_g_col, _hgr_g_glyph, _hgr_g_mask, _hgr_g_y, _hgr_t_bit, _hgr_t_col, _hgr_t_font, _hgr_t_n, _hgr_t_s
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "CODE"
_hgr_blit_glyph8:
        lda #0
        sta rowcnt
@rowloop:
        ; ptr1 = hgr_row(g_y + row)   (single scanline — no paired ptr2)
        lda rowcnt
        clc
        adc _hgr_g_y
        tay
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ; load this row's 8 source bits
        ldy rowcnt
        lda (_hgr_g_glyph),y
        sta curbits
        ; reset pen to the glyph's left edge
        lda _hgr_g_col
        sta curcol
        lda _hgr_g_mask
        sta curmask
        ldx #8                ; 8 bits (bit 7 is blank -> a no-op plot)
@bitloop:
        lsr curbits           ; bit 0 (leftmost) -> carry
        bcc @skip
        ldy curcol            ; lit: one pixel on this scanline
        lda curmask
        ora (ptr1),y
        sta (ptr1),y
@skip:
        asl curmask           ; advance the pen one pixel
        lda curmask
        cmp #$80
        bne @nextbit
        lda #$01
        sta curmask
        inc curcol
@nextbit:
        dex
        bne @bitloop
        inc rowcnt
        lda rowcnt
        cmp #8
        bne @rowloop
        rts

; --- _hgr_puts_run8 : native 8x8 string render (8px pitch) ------------------
; Same param block as _hgr_puts_run (hgr_t_col/bit/n/s/font); draws each glyph
; with hgr_blit_glyph8 and steps the pen 8px (= 1 byte column + 1 bit).
_hgr_puts_run8:
@loop:
        lda _hgr_t_n
        beq @done
        ldy #0
        lda (_hgr_t_s),y       ; c = *s
        bne @go
@done:
        rts
@go:
        cmp #$20                ; clamp non-printable -> space
        bcc @space
        cmp #$80
        bcc @okc
@space:
        lda #$20
@okc:
        sec                     ; hgr_g_glyph = font + (c-$20)*8
        sbc #$20
        sta tmp1
        lda #0
        sta tmp2
        asl tmp1
        rol tmp2
        asl tmp1
        rol tmp2
        asl tmp1
        rol tmp2
        lda tmp1
        clc
        adc _hgr_t_font
        sta _hgr_g_glyph
        lda tmp2
        adc _hgr_t_font+1
        sta _hgr_g_glyph+1
        lda _hgr_t_col
        sta _hgr_g_col
        ldx _hgr_t_bit         ; hgr_g_mask = 1 << bit
        lda #1
@mk:
        dex
        bmi @mkd
        asl a
        jmp @mk
@mkd:
        sta _hgr_g_mask
        jsr _hgr_blit_glyph8
        ; pen += 8px: bit += 1 (+ carry into col on the 7px wrap)
        lda _hgr_t_bit
        clc
        adc #1
        cmp #7
        bcc @nowrap
        sbc #7                  ; carry set by cmp (>=7): A = bit+1-7
        sta _hgr_t_bit
        lda _hgr_t_col
        clc
        adc #2                  ; col += 1, +1 for the bit wrap
        sta _hgr_t_col
        jmp @adv2
@nowrap:
        sta _hgr_t_bit
        lda _hgr_t_col
        clc
        adc #1
        sta _hgr_t_col
@adv2:
        inc _hgr_t_s           ; ++s
        bne @sok
        inc _hgr_t_s+1
@sok:
        dec _hgr_t_n
        jmp @loop
