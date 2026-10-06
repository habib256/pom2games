; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_text_params.s — Apple II HGR kernel; linked independently from hgrc.lib.
; The glyph/text parameter block shared by the 8x8 and 16x16 kernels, plus
; glyph_addr, the font address helper both use.
.exportzp _hgr_g_glyph, _hgr_g_col, _hgr_g_bit, _hgr_g_y, _hgr_t_col, _hgr_t_bit, _hgr_t_n, _hgr_t_s, _hgr_t_font
.export glyph_addr
.importzp tmp1, tmp2

.segment "ZEROPAGE"
_hgr_g_glyph: .res 2        ; pointer to 8 glyph bytes
_hgr_g_col:   .res 1        ; starting byte column
_hgr_g_bit:   .res 1        ; starting bit within the column (0..6)
_hgr_g_y:     .res 1        ; top scanline
_hgr_t_col:   .res 1        ; current byte column of the pen
_hgr_t_bit:   .res 1        ; current bit within the column (0..6)
_hgr_t_n:     .res 1        ; glyph cells left to draw (C precomputes the fit)
_hgr_t_s:     .res 2        ; string pointer
_hgr_t_font:  .res 2        ; glyph table base (hgr_font, 96 glyphs)

.segment "CODE"
; glyph_addr: hgr_g_glyph = hgr_t_font + A*8, A < 96 (10-bit product: the
; high bits come out of the shifts' carry). Clobbers A, tmp1, tmp2.
glyph_addr:
        sta tmp1
        lda #0
        sta tmp2
        lda tmp1
        asl a
        rol tmp2
        asl a
        rol tmp2
        asl a
        rol tmp2
        clc
        adc _hgr_t_font
        sta _hgr_g_glyph
        lda tmp2
        adc _hgr_t_font+1
        sta _hgr_g_glyph+1
        rts
