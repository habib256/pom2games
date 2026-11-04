; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Font address helper, omitted by clients of the preshifted 8x8 HUD bank.
.export glyph_addr
.exportzp _hgr_t_font
.importzp _hgr_g_glyph, tmp1, tmp2
.segment "ZEROPAGE"
_hgr_t_font: .res 2         ; glyph table base (hgr_font, 96 glyphs)
.segment "CODE"
; glyph_addr: hgr_g_glyph = hgr_t_font + A*8, A < 96.
; Form the high part with A>>5 and the low part with A<<3, avoiding
; three slower zero-page rotates. Clobbers A, tmp1, tmp2; keeps X/Y.
glyph_addr:
        sta tmp1
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a
        sta tmp2
        lda tmp1
        asl a
        asl a
        asl a
        clc
        adc _hgr_t_font
        sta _hgr_g_glyph
        lda tmp2
        adc _hgr_t_font+1
        sta _hgr_g_glyph+1
        rts
