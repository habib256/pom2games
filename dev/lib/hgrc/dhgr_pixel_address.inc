; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Y = scanline. Return the draw-page address in ptr1 (low byte) and A (high).
.macro dhgr_scanline_address
        lda dhgr_rowlo,y
        sta ptr1
        lda dhgr_rowhi,y
        ora _dhgr_base
.endmacro

; X:tmp1 = pixel x, tmp2 = x & 3. Return the four-pixel cell in X
; and its bit offset from the start of the cell's first byte (0..9) in Y.
.macro dhgr_pixel_cell_phase
        txa
        lsr
        ror tmp1
        lsr
        ror tmp1
        ldx tmp1
        lda _dhgr_cellphase,x
        clc
        adc tmp2
        tay
.endmacro
