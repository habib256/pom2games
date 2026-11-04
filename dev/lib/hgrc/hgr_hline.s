; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_hline(x0,x1,y), cc65 fastcall: A=y, C stack=x1lo,x1hi,x0lo,x0hi.
; Sort full 16-bit endpoints, reject the minimum, clip the maximum to 279.
.export _hgr_hline
.import _hgr_fill_span, incsp4
.importzp sp, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows
.code
rejected:
        jmp incsp4
_hgr_hline:
        cmp #192
        bcs rejected
        sta _hgr_r_y0
        ldy #0
        lda (sp),y
        sta _hgr_r_xr
        iny
        lda (sp),y
        sta _hgr_r_xr+1
        iny
        lda (sp),y
        sta _hgr_r_x
        iny
        lda (sp),y
        sta _hgr_r_x+1
        cmp _hgr_r_xr+1
        bcc ordered
        bne swap
        lda _hgr_r_x
        cmp _hgr_r_xr
        bcc ordered
        beq ordered
swap:
        ldx _hgr_r_x
        lda _hgr_r_xr
        sta _hgr_r_x
        stx _hgr_r_xr
        ldx _hgr_r_x+1
        lda _hgr_r_xr+1
        sta _hgr_r_x+1
        stx _hgr_r_xr+1
ordered:
        lda _hgr_r_x+1
        cmp #2
        bcs rejected
        cmp #1
        bne left_ready
        lda _hgr_r_x
        cmp #24
        bcs rejected
left_ready:
        lda _hgr_r_xr+1
        cmp #1
        bcc right_ready
        bne clip
        lda _hgr_r_xr
        cmp #24
        bcc right_ready
clip:
        lda #<279
        sta _hgr_r_xr
        lda #>279
        sta _hgr_r_xr+1
right_ready:
        lda #1
        sta _hgr_r_rows
        jsr _hgr_fill_span
        jmp incsp4
