; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Read x from the blit frame. Branch for x < 256 or x >= 280.
; For x = 256..279 return its column in A, its low byte in X, and C clear.
.macro hgr_blit_high_column low_x, reject
        ldy #6
        lda (sp),y
        beq low_x
        cmp #1
        bne reject
        dey
        lda (sp),y
        cmp #24
        bcs reject             ; x >= 280
        tax
        lda _hgr_col7+256,x
.endmacro

; Y points to the y argument. Clip the height, load the source pointer
; and restore the saved drawing mode into the kernel parameters.
.macro hgr_blit_prepare_rows
        .local height_ready
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
.endmacro
