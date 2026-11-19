; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; C must be clear on entry. Advance a row pointer by the full source
; stride, including bytes clipped from the right edge.
.macro hgr_add_stride pointer, stride
        lda pointer
        adc stride
        sta pointer
        bcc :+
        inc pointer+1
:
.endmacro

; Advance to the next bitmap row and return after the last visible row.
.macro hgr_blit_next_row row
        clc
        hgr_add_stride _hgr_b_src, _hgr_b_stride
        inc _hgr_b_y
        dec _hgr_b_h
        bne row
        rts
.endmacro
