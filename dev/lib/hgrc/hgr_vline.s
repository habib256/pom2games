; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_vline(x,y0,y1), cc65 fastcall: A=y1, C stack=y0,xlo,xhi.
; Sort byte endpoints, reject the minimum, clip the maximum to 191.
.export _hgr_vline
.import _hgr_fill_span, incsp3
.importzp sp, _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows
.code
rejected:
        jmp incsp3
_hgr_vline:
        sta _hgr_r_rows          ; temporarily holds the maximum y
        ldy #2
        lda (sp),y
        cmp #2
        bcs rejected
        sta _hgr_r_x+1
        sta _hgr_r_xr+1
        tax
        dey
        lda (sp),y
        sta _hgr_r_x
        sta _hgr_r_xr
        cpx #0
        beq x_ready
        cmp #24
        bcs rejected
x_ready:
        dey
        lda (sp),y
        cmp _hgr_r_rows
        bcc ordered
        beq ordered
        tax
        lda _hgr_r_rows
        stx _hgr_r_rows
ordered:
        cmp #192
        bcs rejected
        sta _hgr_r_y0
        lda _hgr_r_rows
        cmp #192
        bcc bottom_ready
        lda #191
bottom_ready:
        sec
        sbc _hgr_r_y0
        adc #0                  ; max >= min: SBC leaves C=1, add inclusive row
        sta _hgr_r_rows
        jsr _hgr_fill_span
        jmp incsp3
