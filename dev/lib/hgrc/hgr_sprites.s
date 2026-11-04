; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_blit(unsigned x, byte y, byte width, byte height, bitmap, byte mode).
; cc65 fastcall: mode in A; source/height/width/y/x at C-stack offsets 0/2/3/4/5.
; MSB-first source rows retain ceil(original width/8) bytes after clipping.
; No stack locals, new RAM or zero page; uses the existing kernel block.
.export _hgr_blit
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_masks, _hgr_col7, _hgr_mask7
.import _hgr_blit_run, incsp7
.importzp sp, tmp4
.importzp _hgr_b_col, _hgr_b_mask, _hgr_b_w, _hgr_b_h, _hgr_b_stride
.importzp _hgr_b_y, _hgr_b_mode, _hgr_b_src
.code
_hgr_blit:
        sta tmp4                ; all three builders preserve tmp4
        jsr _hgr_build_rows      ; even rejected calls initialize the tables
        jsr _hgr_build_columns
        jsr _hgr_build_masks
        ldy #4
        lda (sp),y
        cmp #192
        bcs outside
        dey
        lda (sp),y
        beq outside             ; width zero
        dey
        lda (sp),y
        beq outside             ; height zero
        ldy #6
        lda (sp),y
        beq low_x
        cmp #1
        bne outside
        dey
        lda (sp),y
        cmp #24
        bcs outside             ; x >= 280
        tax
        lda _hgr_col7+256,x
        ldy _hgr_mask7+256,x
        bcc column              ; CMP #24 left C=0
outside:
        jmp incsp7
low_x:
        dey
        lda (sp),y
        tax
        lda _hgr_col7,x
        ldy _hgr_mask7,x
column:
        sta _hgr_b_col
        sty _hgr_b_mask
        ldy #3
        lda (sp),y
        sta _hgr_b_w
        sec
        sbc #1                  ; ceil(width/8) = ((width-1)>>3)+1, width > 0
        lsr a
        lsr a
        lsr a
        tax
        inx
        stx _hgr_b_stride
        ldy #5
        lda #<280
        sec
        sbc (sp),y
        tax                     ; low byte of remaining horizontal space
        iny
        lda #>280
        sbc (sp),y
        bne width_ready         ; >=256 remaining: every byte width fits
        txa
        cmp _hgr_b_w
        bcs width_ready
        sta _hgr_b_w
width_ready:
        ldy #4
        lda (sp),y
        sta _hgr_b_y
        lda #192
        sec
        sbc _hgr_b_y
        ldy #2
        cmp (sp),y              ; min(height, 192-y), without sum overflow
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
        jsr _hgr_blit_run
        jmp incsp7
