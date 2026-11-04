; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; C fill/clear rectangle (unsigned x, byte y, byte width, byte height).
; Parameters live in the existing kernel block across the lazy builders.
; Only cc65 scratch is used for clipping; no extra RAM or zero page.
.export _hgr_fill_pixrect, _hgr_clear_pixrect
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_masks, _hgr_pixrect_asm, incsp4
.importzp sp, tmp4, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows, _hgr_r_mode
.code
_hgr_fill_pixrect:
        ldx #1
        bne begin
_hgr_clear_pixrect:
        ldx #0
begin:
        stx _hgr_r_mode
        sta _hgr_r_rows
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_masks
        lda _hgr_r_rows
        beq outside
        ldy #0
        lda (sp),y
        beq outside
        sta tmp4                ; width, after builders clobber cc65 scratch
        iny
        lda (sp),y
        cmp #192
        bcs outside
        sta _hgr_r_y0
        lda #192
        sec
        sbc _hgr_r_y0
        cmp _hgr_r_rows
        bcs height_ready
        sta _hgr_r_rows
height_ready:
        ldy #3
        lda (sp),y
        cmp #2
        bcs outside
        sta _hgr_r_x+1
        tax
        dey
        lda (sp),y
        sta _hgr_r_x
        cpx #0
        beq x_ready
        cmp #24
        bcs outside
x_ready:
        lda tmp4
        sec
        sbc #1
        clc
        adc _hgr_r_x
        sta _hgr_r_xr
        lda _hgr_r_x+1
        adc #0
        sta _hgr_r_xr+1
        cmp #1
        bcc right_ready
        bne clip_right
        lda _hgr_r_xr
        cmp #24
        bcc right_ready
clip_right:
        lda #23
        sta _hgr_r_xr
        lda #1
        sta _hgr_r_xr+1
right_ready:
        jsr _hgr_pixrect_asm
        jmp incsp4
outside:
        jmp incsp4
