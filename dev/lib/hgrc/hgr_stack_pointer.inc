; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Load a pointer from the cc65 argument stack and reject NULL.
.macro hgr_stack_pointer offset, dest, reject
        ldy #offset
        lda (sp),y
        sta dest
        iny
        lda (sp),y
        sta dest+1
        ora dest
        beq reject
.endmacro
