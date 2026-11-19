; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.include "hgr_stack_pointer.inc"

; Validate the HUD field and leave eight times its width in A.
.macro hgr_hud_init_extent max_width, glyph_height, reject
        cmp #1
        bcc reject
        cmp #max_width+1
        bcs reject
        sta tmp1
        hgr_stack_pointer 3, ptr1, reject
        ldy #0
        lda (sp),y
        cmp #192-glyph_height+1
        bcs reject
        lda tmp1
        asl a
        asl a
        asl a
.endmacro
