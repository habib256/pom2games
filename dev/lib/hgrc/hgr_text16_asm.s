; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text16_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_blit_glyph, _hgr_puts_run
.import _hgr_rowhi, _hgr_rowlo, glyph_addr, hgr_dbl_lo, hgr_dbl_hi
.importzp _hgr_g_col, _hgr_g_glyph, _hgr_g_bit, _hgr_g_y, _hgr_t_bit, _hgr_t_col, _hgr_t_font, _hgr_t_n, _hgr_t_s, _hgr_z_ce, _hgr_z_co, _hgr_z_hi
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
; The blitter makes no nested calls: phase and temporary masks can use
; cc65 scratch rather than additional private zero-page allocations.
gr_or = tmp1                 ; byte to OR into the framebuffer (cell|hi)
gbc_bit = tmp2               ; pen bit (shift count 0..6) * 16
gbc_m0 = tmp3                ; shifted doubled mask, bits 0..7
rowcnt = tmp4

.segment "ZEROPAGE"
gbc_car0: .res 1             ; carrier byte for cell at g_col + 0
gbc_car1: .res 1             ; carrier byte for cell at g_col + 1
gbc_car2 = gbc_car0          ; the carriers repeat every two byte columns
gbc_car3 = gbc_car1
gbc_m1:   .res 1             ;   byte 1 (bits 8..15)
gbc_m2:   .res 1             ; bits 16..21, shifted to bits 14..21 for cell 2

.segment "CODE"
; --- _hgr_blit_glyph : row-at-a-time 16x16 glyph blitter, white or tinted --
; Expand the 8-bit source row to a 16-bit doubled mask, already shifted left
; by `bit` to align with the pen offset, in two nibble lookups, then OR
; each of the 3-4 spanning bytes (one per 7-bit cell) into both scanlines —
; carrier and palette bit applied per BYTE, not per pixel. White text is the
; carrier pair $7F/$7F with hgr_z_hi = 0 (hgr_text.c sets it): the same OR of
; the same doubled bits the old pixel-by-pixel white blitter produced, about
; five times faster and one blitter instead of two. Cell carriers + the shift
; count are precomputed once per glyph (they depend on g_col parity and g_bit,
; both fixed across the 8 source rows).
_hgr_blit_glyph:
        lda _hgr_g_bit         ; pen bit 0..6 = shift count, times 16
        asl a
        asl a
        asl a
        asl a
        sta gbc_bit
        ; Precompute carriers for cells 0..3. Carrier parity alternates from
        ; g_col: even col -> ce/co/ce/co ; odd col -> co/ce/co/ce.
        lda _hgr_g_col
        lsr a
        lda _hgr_z_ce
        ldx _hgr_z_co
        bcc @carriers
        lda _hgr_z_co
        ldx _hgr_z_ce
@carriers:
        sta gbc_car0
        stx gbc_car1
        lda #0
        sta rowcnt
@crow:
        ldy rowcnt
        lda (_hgr_g_glyph),y
        bne @visible
        jmp @c3sk              ; a blank source row touches neither scanline
@visible:
        tax
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
        ; Expand 8 source bits to 16 doubled bits shifted left by `bit`, by
        ; two nibble lookups (hgr_glyph_shift.s). The bits occupy positions
        ; bit..bit+15 (<= 21), so m2 bits 6..7 stay zero.
        txa
        and #$0F
        ora gbc_bit
        tay
        lda hgr_dbl_lo,y
        sta gbc_m0             ; doubled bits 0..7
        lda hgr_dbl_hi,y
        sta gbc_m1
        txa
        lsr a
        lsr a
        lsr a
        lsr a
        ora gbc_bit
        tay
        lda hgr_dbl_lo,y
        ora gbc_m1
        sta gbc_m1             ; doubled bits 8..15
        lda hgr_dbl_hi,y
        sta gbc_m2             ; doubled bits 16..23
        ldy _hgr_g_col          ; walk the four destination columns once
        ; --- Cell 0 (column g_col): doubled bits 0..6 = m0 & $7F ------------
        lda gbc_m0
        and #$7F
        beq @c0sk
        and gbc_car0
        ora _hgr_z_hi
        sta gr_or
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c0sk:
        iny
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
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c1sk:
        iny
        ; --- Cell 2 (column g_col+2): doubled bits 14..20 ------------------
        ; Shift m1:m2 twice: m2 now holds doubled bits 14..21. Keep its
        ; top bit for cell 3 while drawing the low seven bits in cell 2.
        lda gbc_m1
        asl a
        rol gbc_m2
        asl a
        rol gbc_m2
        lda gbc_m2
        and #$7F
        beq @c2sk
        and gbc_car2
        ora _hgr_z_hi
        sta gr_or
        ora (ptr1),y
        sta (ptr1),y
        lda gr_or
        ora (ptr2),y
        sta (ptr2),y
@c2sk:
        iny
        ; --- Cell 3 (column g_col+3): doubled bit 21 only, set iff bit = 6 -
        ; Cell 2's shifts put doubled bit 21 in m2's sign bit.
        lda gbc_m2
        bpl @c3sk
        lda #1
        and gbc_car3
        ora _hgr_z_hi
        sta gr_or
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
@nowrap:
        sta _hgr_t_bit
        lda _hgr_t_col
        ; CMP leaves C=0 without wrap; SBC leaves C=1 after wrap.
        ; STA/LDA preserve it, so this adds either two or three columns.
        adc #2
        sta _hgr_t_col
@adv2:
        inc _hgr_t_s           ; ++s
        bne @sok
        inc _hgr_t_s+1
@sok:
        dec _hgr_t_n
        jmp @loop
