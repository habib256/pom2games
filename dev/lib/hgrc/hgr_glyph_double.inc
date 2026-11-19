; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Each 8-pixel source row paints two consecutive scanlines at y + 2*row.
.macro hgr_glyph_row_pair row_index
        lda row_index
        asl a                   ; row < 8, so carry is clear
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
.endmacro

; A and X hold the source row. Double both nibbles at the selected phase
; (pen bit * 16) and leave the shifted 16 pixels in three consecutive fragments.
.macro hgr_expand_glyph_row phase, bits0, bits1, bits2
        and #$0F
        ora phase
        tay
        lda hgr_dbl_lo,y
        sta bits0
        lda hgr_dbl_hi,y
        sta bits1
        txa
        lsr a
        lsr a
        lsr a
        lsr a
        ora phase
        tay
        lda hgr_dbl_lo,y
        ora bits1
        sta bits1
        lda hgr_dbl_hi,y
        sta bits2
.endmacro
