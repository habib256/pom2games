; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; For a visible x, fetch the byte column and the bit phase (x / 7, x % 7).
.macro hgr_sprite_column_phase pixel_x, column, phase
        jsr _hgr_build_columns
        jsr _hgr_build_phases
        lda pixel_x+1
        bne :+
        ldx pixel_x
        lda _hgr_col7,x
        ldy _hgr_phase7,x
        jmp :++
:       ldx pixel_x
        lda _hgr_col7+256,x
        ldy _hgr_phase7+256,x
:       sta column
        sty phase
.endmacro
