; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hgr_text8_fast.asm -- a fast white HUD on the two top text lines (HGR)
; ============================================================================
;   ht_diff_row   (ht_fp_src),Y against (ht_fp_shadow),Y for Y = Y .. A - 1:
;                 the characters that differ are drawn at text line
;                 ht_sl / 8 (0 or 1) and recorded in the shadow. A HUD
;                 composed in a buffer costs only its changed characters.
;   ht_fast_put   A = char ($20-$5F), Y = column: the glyph's 8 rows stored
;                 on the draw page (ht_page: 0 = $2000, else $4000), white,
;                 what hgr_putc8 writes there (HGR-order font bbfont,
;                 dev/lib/font) with an unrolled 8-row loop. Keeps Y.
; Zero page, defined by the caller before the include: ht_fp_src (2),
; ht_fp_shadow (2), ht_fp_glyph (2), ht_fp_end, ht_fp_y; ht_sl and ht_page
; are hgr_text8.asm's. Text lines 0 and 1 only (the row bases are constants).
; A textual include, placed where ht_diff_row is wanted (a caller may fall
; into it). From the HALFPIPE and LANDER examples (168 bytes).
; ============================================================================

; (ht_fp_src),Y vs (ht_fp_shadow),Y for Y = Y .. A - 1: the characters that differ
; written at row ht_sl and recorded in (ht_fp_shadow). Clobbers A, Y.
ht_diff_row:
        STA     ht_fp_end
@l:     LDA     (ht_fp_src),Y
        CMP     (ht_fp_shadow),Y
        BEQ     @n
        STA     (ht_fp_shadow),Y
        JSR     ht_fast_put
@n:     INY
        CPY     ht_fp_end
        BNE     @l
        RTS

; A = char ($20-$5F), Y = column: its 8 glyph rows stored at text line
; ht_sl / 8 (0 or 1) of the draw page (ht_page), white: what hgr_putc8
; writes there, ~150 cycles instead of ~470 (a private 8-row STA loop,
; dev/lib/font). Keeps Y.
ht_fast_put:
        STY     ht_fp_y
        SEC
        SBC     #$20                    ; the glyph: bbfont + 8 (char - $20)
        LDX     #0
        STX     ht_fp_glyph+1
        ASL     A
        ROL     ht_fp_glyph+1
        ASL     A
        ROL     ht_fp_glyph+1
        ASL     A
        ROL     ht_fp_glyph+1                    ; (C = 0)
        ADC     #<bbfont
        STA     ht_fp_glyph
        LDA     ht_fp_glyph+1
        ADC     #>bbfont
        STA     ht_fp_glyph+1
        TYA                             ; X = the column, + $80 on line 1
        LDX     ht_sl
        BEQ     :+
        ORA     #$80
:       TAX
        LDY     #0
        LDA     ht_page
        BNE     @p2
        .repeat 8, R
        LDA     (ht_fp_glyph),Y
        STA     $2000 + R * $400,X
        .if R < 7
        INY
        .endif
        .endrepeat
        LDY     ht_fp_y
        RTS
@p2:    .repeat 8, R
        LDA     (ht_fp_glyph),Y
        STA     $4000 + R * $400,X
        .if R < 7
        INY
        .endif
        .endrepeat
        LDY     ht_fp_y
        RTS

