; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text16_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_blit_glyph, _hgr_puts_run
.import _hgr_rowhi, _hgr_rowlo, glyph_addr
.importzp _hgr_g_col, _hgr_g_glyph, _hgr_g_bit, _hgr_g_y, _hgr_t_bit, _hgr_t_col, _hgr_t_font, _hgr_t_n, _hgr_t_s, _hgr_z_ce, _hgr_z_co, _hgr_z_hi
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
gr_or:    .res 1             ; scratch: byte to OR into the framebuffer (cell|hi)
gbc_bit:  .res 1             ; shift count derived from g_mask (0..6)
gbc_car0: .res 1             ; carrier byte for cell at g_col + 0
gbc_car1: .res 1             ; carrier byte for cell at g_col + 1
gbc_car2: .res 1             ; carrier byte for cell at g_col + 2
gbc_car3: .res 1             ; carrier byte for cell at g_col + 3 (used only when bit = 6)
gbc_m0:   .res 1             ; row's shifted doubled mask, byte 0 (bits 0..7)
gbc_m1:   .res 1             ;   byte 1 (bits 8..15)
gbc_m2:   .res 1             ;   byte 2 (bits 16..23 — only bits 0..5 ever set)

.segment "CODE"
; --- _hgr_blit_glyph : row-at-a-time 16x16 glyph blitter, white or tinted --
; Expand the 8-bit source row to a 16-bit doubled mask in two nibble LUT
; lookups (dbl4tbl), shift left by `bit` to align with the pen offset, then OR
; each of the 3-4 spanning bytes (one per 7-bit cell) into both scanlines —
; carrier and palette bit applied per BYTE, not per pixel. White text is the
; carrier pair $7F/$7F with hgr_z_hi = 0 (hgr_text.c sets it): the same OR of
; the same doubled bits the old pixel-by-pixel white blitter produced, about
; five times faster and one blitter instead of two. Cell carriers + the shift
; count are precomputed once per glyph (they depend on g_col parity and g_mask,
; both fixed across the 8 source rows).
_hgr_blit_glyph:
        ldx _hgr_g_bit         ; pen bit 0..6 = shift count
        stx gbc_bit
        ; Precompute carriers for cells 0..3. Carrier parity alternates from
        ; g_col: even col -> ce/co/ce/co ; odd col -> co/ce/co/ce.
        lda _hgr_g_col
        and #1
        bne @codd
        lda _hgr_z_ce
        sta gbc_car0
        sta gbc_car2
        lda _hgr_z_co
        sta gbc_car1
        sta gbc_car3
        jmp @cdn
@codd:  lda _hgr_z_co
        sta gbc_car0
        sta gbc_car2
        lda _hgr_z_ce
        sta gbc_car1
        sta gbc_car3
@cdn:   lda #0
        sta rowcnt
@crow:
        ; ptr1 = scanline yy ; ptr2 = scanline yy+1 (paired pixel-doubling).
        lda rowcnt
        asl a                  ; row * 2
        clc
        adc _hgr_g_y          ; yy = y + 2*row
        tay
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        iny                    ; yy + 1
        lda _hgr_rowlo,y
        sta ptr2
        lda _hgr_rowhi,y
        sta ptr2+1
        ; Expand 8 source bits to 16 doubled bits via two nibble lookups.
        ldy rowcnt
        lda (_hgr_g_glyph),y
        pha
        and #$0F
        tay
        lda _hgr_dbl4tbl,y
        sta gbc_m0             ; doubled bits 0..7
        pla
        lsr a
        lsr a
        lsr a
        lsr a
        tay
        lda _hgr_dbl4tbl,y
        sta gbc_m1             ; doubled bits 8..15
        lda #0
        sta gbc_m2             ; doubled bits 16..23 (filled in by the shift)
        ; Shift (m2:m1:m0) left by `bit` positions; bit = 0 leaves them as-is.
        ; A 3-byte chain is enough: the original 16 bits occupy positions
        ; bit..bit+15 (<= 21), so m2 bits 6..7 stay zero and m3 isn't needed.
        ldy gbc_bit
        beq @nosh
@sh:    asl gbc_m0
        rol gbc_m1
        rol gbc_m2
        dey
        bne @sh
@nosh:
        ; --- Cell 0 (column g_col): doubled bits 0..6 = m0 & $7F ------------
        lda gbc_m0
        and #$7F
        beq @c0sk
        and gbc_car0
        ora _hgr_z_hi
        sta gr_or
        ldy _hgr_g_col
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c0sk:
        ; --- Cell 1 (column g_col+1): doubled bits 7..13 -------------------
        ; bits 7..13 = ((m1 << 1) | (m0 >> 7)) & $7F
        lda gbc_m0
        asl a                  ; CF = m0 bit 7 (= doubled bit 7)
        lda gbc_m1
        rol a                  ; A = (m1 << 1) | (m0 bit 7)
        and #$7F
        beq @c1sk
        and gbc_car1
        ora _hgr_z_hi
        sta gr_or
        ldy _hgr_g_col
        iny
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c1sk:
        ; --- Cell 2 (column g_col+2): doubled bits 14..20 ------------------
        ; bits 14..20 = ((m2 << 2) & $7C) | ((m1 >> 6) & $03)
        ; m2 bit 5 (= doubled bit 21) belongs to cell 3, so $7C drops it.
        lda gbc_m1
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a                  ; A = m1 >> 6 (low 2 bits = m1 bits 6..7)
        sta gr_or              ; partial cell 2 in bits 0..1
        lda gbc_m2
        asl a
        asl a                  ; A = m2 << 2 (m2 bit 5 spilled to bit 7)
        and #$7C               ; keep bits 2..6 only
        ora gr_or
        beq @c2sk
        and gbc_car2
        ora _hgr_z_hi
        sta gr_or
        ldy _hgr_g_col
        iny
        iny
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c2sk:
        ; --- Cell 3 (column g_col+3): doubled bit 21 only, set iff bit = 6 -
        ; (m2 << 0 ... actually m2 bits 5..7, but bits 6..7 stay 0 by design)
        lda gbc_m2
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a                  ; A = m2 >> 5 (low 3 bits, but bits 1..2 = 0)
        and #$07
        beq @c3sk
        and gbc_car3
        ora _hgr_z_hi
        sta gr_or
        ldy _hgr_g_col
        iny
        iny
        iny
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c3sk:
        inc rowcnt
        lda rowcnt
        cmp #8
        beq @cdone
        jmp @crow
@cdone: rts

; 4-bit -> 8-bit doubled bit LUT: dbl4tbl[n] has each of n's bits 0..3
; replicated horizontally (bit k of n -> bits 2k and 2k+1 of the entry).
_hgr_dbl4tbl:
        .byte $00, $03, $0C, $0F, $30, $33, $3C, $3F
        .byte $C0, $C3, $CC, $CF, $F0, $F3, $FC, $FF

; --- _hgr_puts_run : draw a whole NUL-terminated string in ONE asm loop -------
; Replaces the per-character C loop of hgr_puts / hgr_puts_color. Walks
; hgr_t_s, drawing at most hgr_t_n glyph cells (the C wrapper precomputes how
; many fit from x, so there is NO per-char 16-bit clip here). Per glyph: form the
; font address font+(c-$20)*8, set hgr_g_col/bit, JSR the blitter (the
; carriers decide white or colour), then step the 18px pen (bit+=4, col+=2,
; +1 col on wrap). hgr_g_y set by the caller.
_hgr_puts_run:
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
        jsr _hgr_blit_glyph
        lda _hgr_t_bit         ; pen: bit += 4 (+ carry into col on wrap)
        clc
        adc #4
        cmp #7
        bcc @nowrap
        sbc #7                  ; carry set by cmp (>=7): A = bit+4-7
        sta _hgr_t_bit
        lda _hgr_t_col
        clc
        adc #3                  ; col += 2, +1 for the bit wrap
        sta _hgr_t_col
        jmp @adv2
@nowrap:
        sta _hgr_t_bit
        lda _hgr_t_col
        clc
        adc #2
        sta _hgr_t_col
@adv2:
        inc _hgr_t_s           ; ++s
        bne @sok
        inc _hgr_t_s+1
@sok:
        dec _hgr_t_n
        jmp @loop
