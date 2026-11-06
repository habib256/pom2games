; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text8_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
; _hgr_blit_glyph8: D=0; destroys A/X/Y, ptr1 and tmp1..tmp3.
; Glyph arguments, other scratch, banks and IRQ mask are preserved.
; The string entry also advances its private text/glyph parameter blocks.
.export _hgr_blit_glyph8, _hgr_puts_run8
.import _hgr_rowhi, _hgr_rowlo
.import glyph_addr
.importzp _hgr_g_col, _hgr_g_glyph, _hgr_g_bit, _hgr_g_y, _hgr_t_bit, _hgr_t_col, _hgr_t_font, _hgr_t_n, _hgr_t_s
.importzp ptr1, tmp1, tmp2, tmp3
curmask = tmp2
curbits = tmp3

.segment "CODE"
_hgr_blit_glyph8:
; Row at a time: the 7 glyph pixels become bits bit..bit+6 of the 14-bit span
; at columns g_col / g_col+1 (left = row << bit, right = row >> (7-bit)), ORed
; in as two bytes. ~350 cycles per glyph against ~2 500 for the old
; pixel-by-pixel pen walk.
        ldx _hgr_g_y          ; current physical scanline
        txa
        clc
        adc #8
        sta tmp1              ; physical end, modulo 256
@rowloop:
        txa
        sec
        sbc _hgr_g_y
        tay                    ; source row = (physical - top), 0..7
        lda (_hgr_g_glyph),y
        beq @next
        ; Y builds the destination pointer without disturbing the glyph A.
        ldy _hgr_rowlo,x
        sty ptr1
        ldy _hgr_rowhi,x
        sty ptr1+1
        ; Shift the low byte in A (2 cycles), rather than ZP (5 cycles).
        ; curmask still receives carries for the high byte of the span.
        ldy #0
        sty curmask           ; high byte
        ldy _hgr_g_bit
        beq @shifted
@shift: asl a
        rol curmask
        dey
        bne @shift
@shifted:
        sta curbits           ; shifted 16-bit span, low byte
        ldy _hgr_g_col
        and #$7F
        beq @right
        ora (ptr1),y
        sta (ptr1),y
@right: lda curbits
        asl a                 ; C = span bit 7
        lda curmask
        rol a                 ; span bits 7..13 -> next column
        ; An 8-bit row shifted by at most six occupies at most 14 bits:
        ; these upper seven bits cannot contain the palette bit.
        beq @next             ; also keeps column 40 untouched (bit = 0 there)
        iny
        ora (ptr1),y
        sta (ptr1),y
@next:  inx
        cpx tmp1
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
        jsr glyph_addr
        lda _hgr_t_col
        sta _hgr_g_col
        lda _hgr_t_bit
        sta _hgr_g_bit
        jsr _hgr_blit_glyph8
        ; pen += 8px: one column and one bit, with a second column
        ; when bit 6 wraps to 0. No duplicated column arithmetic.
        inc _hgr_t_col
        inc _hgr_t_bit
        lda _hgr_t_bit
        cmp #7
        bcc @adv2
        lda #0
        sta _hgr_t_bit
        inc _hgr_t_col
@adv2:
        inc _hgr_t_s           ; ++s
        bne @sok
        inc _hgr_t_s+1
@sok:
        dec _hgr_t_n
        jmp @loop
