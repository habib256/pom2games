; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Save the fastcall string, build tables and check its origin before drawing.
; On the high-x path A is the low byte of x, Y=1 and C=0.
; On the low-x path Y=2 for the caller's lookup.
.macro hgr_text_origin glyph_height, last_x, low_x, reject
        sta _hgr_t_s             ; builders do not touch the string state
        stx _hgr_t_s+1
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_phases
        ldy #0
        lda (sp),y
        cmp #192-glyph_height+1
        bcs reject
        sta _hgr_g_y
        ldy #2
        lda (sp),y
        beq low_x
        cmp #1
        bne reject
        dey
        lda (sp),y
        cmp #<(last_x+1)
        bcs reject
.endmacro
