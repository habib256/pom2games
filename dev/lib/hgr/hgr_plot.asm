; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native 280x192 OR/XOR pixel, clipped before table access.
; hp_x: 16-bit unsigned X; hp_y: Y; hp_mode: 0=OR, nonzero=XOR.
; Uses hgr_lo/hi and full-width hgr_col/mask (HGR_FULL_WIDTH_TABLES=1).
; OR preserves bit 7 unless HP_COLOR_TABLE is defined: hp_color indexes
; that caller-owned palette table and replaces bit 7. XOR preserves bit 7.
; HP_OR_PLOT optionally receives/returns the final OR byte in A, with Y
; the framebuffer column. It must preserve Y and hp_* (X may change).
; Define hp_* aliases before inclusion to reuse caller ZP/BSS. Non-reentrant,
; D=0, main RAM, caller selects page/banks; A/X/Y and hp_ptr/mask destroyed.
.ifndef _HGR_PLOT_LOADED_
_HGR_PLOT_LOADED_ = 1
.zeropage
.ifndef hp_x
hp_x: .res 2
.endif
.ifndef hp_y
hp_y: .res 1
.endif
.ifndef hp_ptr
hp_ptr: .res 2
.endif
.ifndef hp_mask
hp_mask: .res 1
.endif
.ifndef hp_mode
hp_mode: .res 1
.endif
.ifdef HP_COLOR_TABLE
.ifndef hp_color
hp_color: .res 1
.endif
.endif
.code
hgr_plot16:
        lda hp_y
        cmp #192
        bcs @off
        lda hp_x+1
        beq @low
        cmp #1
        bne @off
        ldx hp_x
        cpx #24
        bcs @off
        lda hgr_mask+256,x
        sta hp_mask
        ldy hgr_col+256,x
        jmp @row
@low:   ldx hp_x
        lda hgr_mask,x
        sta hp_mask
        ldy hgr_col,x
@row:   ldx hp_y
        lda hgr_lo,x
        sta hp_ptr
        lda hgr_hi,x
        sta hp_ptr+1
        lda (hp_ptr),y
        ldx hp_mode
        bne @xor
        ora hp_mask
.ifdef HP_COLOR_TABLE
        and #$7f
        ldx hp_color
        ora HP_COLOR_TABLE,x
.endif
.ifdef HP_OR_PLOT
        jsr HP_OR_PLOT
.endif
        sta (hp_ptr),y
        rts
@xor:   eor hp_mask
        sta (hp_ptr),y
@off:   rts
.endif
