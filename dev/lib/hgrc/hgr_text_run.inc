; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Render up to _hgr_t_n characters from the NUL-terminated string.
; Each renderer supplies its glyph routine and its inline pen advance.
.macro hgr_text_run blit, advance_pen
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
        jsr glyph_addr
        lda _hgr_t_col
        sta _hgr_g_col
        lda _hgr_t_bit
        sta _hgr_g_bit
        jsr blit
        advance_pen
        inc _hgr_t_s           ; ++s
        bne @sok
        inc _hgr_t_s+1
@sok:
        dec _hgr_t_n
        jmp @loop
.endmacro
