; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text8_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_blit_glyph8, _hgr_puts_run8
.import _hgr_rowhi, _hgr_rowlo
.import glyph_addr
.importzp _hgr_g_col, _hgr_g_glyph, _hgr_g_bit, _hgr_g_y, _hgr_t_bit, _hgr_t_col, _hgr_t_font, _hgr_t_n, _hgr_t_s
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "CODE"
_hgr_blit_glyph8:
; Row at a time: the 7 glyph pixels become bits bit..bit+6 of the 14-bit span
; at columns g_col / g_col+1 (left = row << bit, right = row >> (7-bit)), ORed
; in as two bytes. ~350 cycles per glyph against ~2 500 for the old
; pixel-by-pixel pen walk.
        lda #0
        sta rowcnt
@rowloop:
        lda rowcnt
        clc
        adc _hgr_g_y
        tay
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ldy rowcnt
        lda (_hgr_g_glyph),y
        beq @next             ; blank row: nothing to OR
        sta curbits           ; 16-bit span, low byte
        ldx #0
        stx curmask           ; high byte
        ldy _hgr_g_bit
        beq @shifted
@shift: asl curbits
        rol curmask
        dey
        bne @shift
@shifted:
        ldy _hgr_g_col
        lda curbits
        and #$7F
        beq @right
        ora (ptr1),y
        sta (ptr1),y
@right: lda curbits
        asl a                 ; C = span bit 7
        lda curmask
        rol a                 ; span bits 7..13 -> next column
        and #$7F
        beq @next             ; also keeps column 40 untouched (bit = 0 there)
        iny
        ora (ptr1),y
        sta (ptr1),y
@next:  inc rowcnt
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
        jsr glyph_addr
        lda _hgr_t_col
        sta _hgr_g_col
        lda _hgr_t_bit
        sta _hgr_g_bit
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
