; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; A=x, saved_y holds a validated y. On success ptr1 is the row base,
; Y is the column and carry selects the upper nibble on odd block rows.
.macro lores_point_address saved_y, reject
        cmp #40
        bcs reject
        sta ptr2                ; x
        jsr _hgr_lores_build    ; clobbers only A/X/Y/tmp1
        lda saved_y
        lsr a
        tax                     ; text row; C = odd block-row
        lda _hgr_lo_rowlo,x
        sta ptr1
        lda _hgr_lo_rowhi,x
        sta ptr1+1
        ldy ptr2
.endmacro
