; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_filled_rect(x0,y0,x1,y1): A=y1, stack=x1lo,x1hi,y0,x0lo,x0hi.
; Sort full-width corners before clipping. Inclusive dimensions are computed
; only after clipping; no overflow at x1=$ffff or y1=$ff. Rejected rectangles
; never initialize tables. The existing span kernel owns all rendering.
.export _gfx_filled_rect
.import _hgr_fill_span
.importzp sp, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows
.code
_gfx_filled_rect:
        sta _hgr_r_rows          ; temporary y maximum
        ldy #2
        lda (sp),y
        cmp _hgr_r_rows
        bcc y_ordered
        beq y_ordered
        tax
        lda _hgr_r_rows
        stx _hgr_r_rows
y_ordered:
        cmp #192
        bcs done
        sta _hgr_r_y0
        lda _hgr_r_rows
        cmp #192
        bcc y_clipped
        lda #191
y_clipped:
        sec
        sbc _hgr_r_y0
        adc #0                  ; carry from nonnegative subtraction: inclusive
        sta _hgr_r_rows
        ldy #0
        lda (sp),y
        sta _hgr_r_xr
        iny
        lda (sp),y
        sta _hgr_r_xr+1
        ldy #3
        lda (sp),y
        sta _hgr_r_x
        iny
        lda (sp),y
        sta _hgr_r_x+1
        cmp _hgr_r_xr+1
        bcc x_ordered
        bne swap
        lda _hgr_r_x
        cmp _hgr_r_xr
        bcc x_ordered
        beq x_ordered
swap:
        ldx _hgr_r_x
        lda _hgr_r_xr
        sta _hgr_r_x
        stx _hgr_r_xr
        ldx _hgr_r_x+1
        lda _hgr_r_xr+1
        sta _hgr_r_x+1
        stx _hgr_r_xr+1
x_ordered:
        lda _hgr_r_x+1
        cmp #2
        bcs done
        cmp #1
        bne left_ready
        lda _hgr_r_x
        cmp #24
        bcs done
left_ready:
        lda _hgr_r_xr+1
        cmp #1
        bcc draw
        bne clip
        lda _hgr_r_xr
        cmp #24
        bcc draw
clip:
        lda #<279
        sta _hgr_r_xr
        lda #>279
        sta _hgr_r_xr+1
draw:
        jsr _hgr_fill_span
done:
        clc
        lda sp
        adc #5
        sta sp
        bcc :+
        inc sp+1
:       rts
