; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_colorize(unsigned x, byte y, byte width, byte height, byte color).
; Preserve the color across both lazy builders; their scratch contracts
; leave tmp4 intact, including HGRC_X7_FOLDED. No extra RAM or zero page.
.export _hgr_colorize
.import _hgr_build_rows, _hgr_build_columns, _hgr_col7
.import _hgr_set_carrier, _hgr_colorize_asm, incsp5
.importzp sp, ptr2, tmp3, tmp4
.importzp _hgr_z_col0, _hgr_z_ncols, _hgr_z_y0, _hgr_z_rows
.code
_hgr_colorize:
        sta tmp4
        jsr _hgr_build_rows
        jsr _hgr_build_columns
        ldy #0
        lda (sp),y
        beq outside
        sta _hgr_z_rows
        iny
        lda (sp),y
        beq outside
        sta tmp3
        iny
        lda (sp),y
        cmp #192
        bcs outside
        sta _hgr_z_y0
        ldy #4
        lda (sp),y
        cmp #2
        bcs outside
        sta ptr2+1
        tax
        dey
        lda (sp),y
        sta ptr2
        cpx #0
        beq valid
        cmp #24
        bcc valid
outside:
        jmp incsp5
valid:
        lda tmp4
        jsr _hgr_set_carrier     ; preserves ptr2/tmp3; rejects without mutation
        cmp #0                  ; C return value is A/X, not processor flags
        beq outside
        lda #192
        sec
        sbc _hgr_z_y0
        cmp _hgr_z_rows
        bcs height_ready
        sta _hgr_z_rows
height_ready:
        ldy ptr2
        lda ptr2+1
        bne left_high
        lda _hgr_col7,y
        jmp left_ready
left_high:
        lda _hgr_col7+256,y
left_ready:
        sta _hgr_z_col0
        lda tmp3
        sec
        sbc #1
        clc
        adc ptr2
        tay
        lda ptr2+1
        adc #0
        cmp #1
        bcc right_low
        bne clip_right
        cpy #24
        bcs clip_right
        lda _hgr_col7+256,y
        bne right_ready         ; high x always maps to column 36..39
right_low:
        lda _hgr_col7,y
        jmp right_ready
clip_right:
        lda #39
right_ready:
        sec
        sbc _hgr_z_col0          ; ordered endpoints leave carry set
        adc #0                  ; inclusive count = difference + carry
        sta _hgr_z_ncols
        jsr _hgr_colorize_asm
        jmp incsp5
