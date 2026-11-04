; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_blit7(unsigned x, byte y, byte width, byte height, source, byte mode).
; cc65 fastcall: mode in A; source/height/width/y/x at C-stack offsets 0/2/3/4/5.
; Keep the full source stride, clip against remaining screen space and
; load the existing kernel block directly. No extra RAM or zero page.
.export _hgr_blit7
.import _hgr_build_rows, _hgr_build_columns, _hgr_col7, _hgr_blit7_run, incsp7
.importzp sp, tmp4
.importzp _hgr_b_col, _hgr_b_w, _hgr_b_h, _hgr_b_stride, _hgr_b_y, _hgr_b_mode, _hgr_b_src
.code
_hgr_blit7:
        sta tmp4                ; preserved by both normal and folded builders
        jsr _hgr_build_rows      ; retain lazy initialization even on rejection
        jsr _hgr_build_columns
        ldy #3
        lda (sp),y
        beq done                ; empty width
        dey
        lda (sp),y
        beq done                ; empty height
        ldy #4
        lda (sp),y
        cmp #192
        bcs done
        ldy #6
        lda (sp),y
        beq low_x
        cmp #1
        bne done
        dey
        lda (sp),y
        cmp #24
        bcs done                ; x >= 280
        tax
        lda _hgr_col7+256,x
        bcc column              ; CMP #24 left C=0
low_x:
        dey
        lda (sp),y
        tax
        lda _hgr_col7,x
column:
        sta _hgr_b_col
        lda #40
        sec
        sbc _hgr_b_col
        ldy #3
        cmp (sp),y              ; min(width, 40-column), no 8-bit sum overflow
        bcc width_ready
        lda (sp),y
width_ready:
        sta _hgr_b_w
        lda (sp),y
        sta _hgr_b_stride       ; original source width, even after clipping
        iny
        lda (sp),y
        sta _hgr_b_y
        lda #192
        sec
        sbc _hgr_b_y
        ldy #2
        cmp (sp),y
        bcc height_ready
        lda (sp),y
height_ready:
        sta _hgr_b_h
        ldy #0
        lda (sp),y
        sta _hgr_b_src
        iny
        lda (sp),y
        sta _hgr_b_src+1
        lda tmp4
        sta _hgr_b_mode
        jsr _hgr_blit7_run
done:
        jmp incsp7
