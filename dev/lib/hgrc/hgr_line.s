; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_line(x0,y0,x1,y1), cc65 fastcall: A=y1, C stack=x1lo,x1hi,y0,x0lo,x0hi.
; Reject either invalid endpoint before any lazy table construction. Preserve
; the axis routines' sorting/palette semantics and the core's Bresenham ties.
.export _hgr_line
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_masks
.import _hgr_line_asm, _hgr_hline, _hgr_vline, incsp1, incsp2, incsp5
.import _hgr_l_x0, _hgr_l_x1, _hgr_l_y0, _hgr_l_y1
.importzp sp
.code
rejected:
        jmp incsp5
_hgr_line:
        cmp #192
        bcs rejected
        sta _hgr_l_y1
        ldy #2
        lda (sp),y
        cmp #192
        bcs rejected
        sta _hgr_l_y0
        ldy #4
        lda (sp),y
        cmp #2
        bcs rejected
        sta _hgr_l_x0+1
        tax
        dey
        lda (sp),y
        sta _hgr_l_x0
        cpx #0
        beq x0_ready
        cmp #24
        bcs rejected
x0_ready:
        ldy #1
        lda (sp),y
        cmp #2
        bcs rejected
        sta _hgr_l_x1+1
        tax
        dey
        lda (sp),y
        sta _hgr_l_x1
        cpx #0
        beq x1_ready
        cmp #24
        bcs rejected
x1_ready:
        lda _hgr_l_y0
        cmp _hgr_l_y1
        beq horizontal
        lda _hgr_l_x0
        cmp _hgr_l_x1
        bne diagonal
        lda _hgr_l_x0+1
        cmp _hgr_l_x1+1
        beq vertical
diagonal:
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_masks
        jsr _hgr_line_asm
        jmp incsp5
horizontal:
        ; Shift x1 up one slot, replacing y0, then discard the first slot.
        ; x0 remains in place: the hline stack is now x1lo,x1hi,x0lo,x0hi.
        ldy #2
        lda _hgr_l_x1+1
        sta (sp),y
        dey
        lda _hgr_l_x1
        sta (sp),y
        jsr incsp1
        lda _hgr_l_y0
        jmp _hgr_hline
vertical:
        ; Dropping x1 leaves y0,x0lo,x0hi in the exact vline layout.
        jsr incsp2
        lda _hgr_l_y1
        jmp _hgr_vline
