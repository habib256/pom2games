; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; dhgr_clear_rows(y, rows, color): A=color, C stack=rows,y.
; Reject before preparing the pattern; clip in the consumed argument slot.
.export _dhgr_clear_rows
.import _dhgr_prepare_pattern, _dhgr_clear_rows_asm, addysp
.importzp sp
.code
_dhgr_clear_rows:
        tax                    ; keep color while validating the two arguments
        ldy #0
        lda (sp),y
        beq reject
        iny
        lda (sp),y
        cmp #192
        bcs reject
        lda #192
        sec
        sbc (sp),y
        dey
        cmp (sp),y
        bcs clipped
        sta (sp),y             ; rows=min(rows,192-y), always at least one
clipped:
        txa
        jsr _dhgr_prepare_pattern
        ldy #0
        lda (sp),y
        tax                    ; fastcall high byte: row count
        iny
        lda (sp),y             ; fastcall low byte: first row
        ldy #2
        jsr addysp             ; preserves A/X; discard caller's two arguments
        jmp _dhgr_clear_rows_asm
reject:
        ldy #2
        jmp addysp
