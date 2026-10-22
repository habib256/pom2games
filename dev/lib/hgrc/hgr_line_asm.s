; VERHILLE Arnaud — GPL-3.0. Full-width HGR Bresenham, same ties as gfx_line.
; Inputs hgr_l_x0/x1=0..279, hgr_l_y0/y1=0..191; tables built by C wrapper.
; OR drawing, bit 7 and holes preserved. Current draw-page row tables.
; Main RAM/ZP, non-reentrant. A/X/Y, flags, ptr1-ptr4, tmp1-tmp3 destroyed.
; No self modification, no bank/IRQ changes. Endpoints/scratch overwritten.
;
; gfx_line steps x when 2*err > -dy and y when 2*err < dx (both tests on the
; same err). Along the major axis the first test always holds when dx >= dy,
; the second when dy > dx, so only the minor step is decided, by the sign of
; D = 2*minor - major - 1, += 2*minor per pixel and -= 2*major per minor step.
; The pixel moves incrementally: mask shift, row reloaded on y steps only.
.export _hgr_line_asm, _hgr_l_x0, _hgr_l_x1, _hgr_l_y0, _hgr_l_y1
.import _hgr_col7, _hgr_mask7, _hgr_rowlo, _hgr_rowhi
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3
mask = tmp1
endcol = tmp2                   ; x-major: last pixel's column and mask
endmask = tmp3
d = ptr2
flat = ptr3                     ; D increment, major step only
minor = ptr4                    ; D increment, major and minor steps
.bss
_hgr_l_x0: .res 2
_hgr_l_x1: .res 2
_hgr_l_y0: .res 1
_hgr_l_y1: .res 1
dx: .res 2
sx: .res 1                      ; bit 7: x decreases
sy: .res 1                      ; bit 7: y decreases
.code
_hgr_line_asm:
        lda #0
        sta sx
        sta sy
        sec
        lda _hgr_l_x1
        sbc _hgr_l_x0
        sta dx
        lda _hgr_l_x1+1
        sbc _hgr_l_x0+1
        sta dx+1
        bcs @dx_done
        dec sx
        lda #0
        sec
        sbc dx
        sta dx
        lda #0
        sbc dx+1
        sta dx+1
@dx_done:
        sec
        lda _hgr_l_y1
        sbc _hgr_l_y0
        bcs @dy_done
        dec sy
        eor #$FF
        adc #1                  ; C=0 here
@dy_done:
        sta tmp2                ; dy, 0..191
        ; Start pixel and row.
        ldx _hgr_l_x0
        lda _hgr_l_x0+1
        beq @start_low
        lda _hgr_mask7+256,x
        sta mask
        ldy _hgr_col7+256,x
        jmp @start_row
@start_low:
        lda _hgr_mask7,x
        sta mask
        ldy _hgr_col7,x
@start_row:
        ldx _hgr_l_y0
        lda _hgr_rowlo,x
        sta ptr1
        lda _hgr_rowhi,x
        sta ptr1+1
        lda dx+1
        bne @x_major
        lda dx
        cmp tmp2
        bcs @x_major
        jmp y_major
@x_major:
        ; flat = 2*dy, minor = 2*dy - 2*dx, D = 2*dy - dx - 1.
        lda tmp2
        asl
        sta flat
        lda #0
        rol
        sta flat+1
        lda dx
        asl
        sta minor
        lda dx+1
        rol
        sta minor+1
        sec
        lda flat
        sbc minor
        sta minor
        lda flat+1
        sbc minor+1
        sta minor+1
        clc                     ; D = flat - dx - 1
        lda flat
        sbc dx
        sta d
        lda flat+1
        sbc dx+1
        sta d+1
        ; Last pixel.
        stx tmp2                ; (dy no longer needed) y0 back in X below
        ldx _hgr_l_x1
        lda _hgr_l_x1+1
        beq @end_low
        lda _hgr_mask7+256,x
        sta endmask
        lda _hgr_col7+256,x
        jmp @end_col
@end_low:
        lda _hgr_mask7,x
        sta endmask
        lda _hgr_col7,x
@end_col:
        ldx tmp2
        sta endcol
        bit sx
        bpl x_right
        jmp x_left

; x-major, increasing x. X = row, Y = column.
x_right:
        lda mask
        ora (ptr1),y
        sta (ptr1),y
        cpy endcol
        beq @maybe_end
@next:  lda d+1
        bmi @flat
        clc
        lda d
        adc minor
        sta d
        lda d+1
        adc minor+1
        sta d+1
        bit sy
        bmi @up
        inx
        bne @row                ; always (row < 192)
@up:    dex
@row:   lda _hgr_rowlo,x
        sta ptr1
        lda _hgr_rowhi,x
        sta ptr1+1
        jmp @step
@flat:  clc
        lda d
        adc flat
        sta d
        lda d+1
        adc flat+1
        sta d+1
@step:  asl mask
        bpl x_right
        lda #1
        sta mask
        iny
        bne x_right             ; always (column < 40)
@maybe_end:
        lda mask
        cmp endmask
        bne @next
        rts

; x-major, decreasing x.
x_left:
        lda mask
        ora (ptr1),y
        sta (ptr1),y
        cpy endcol
        beq @maybe_end
@next:  lda d+1
        bmi @flat
        clc
        lda d
        adc minor
        sta d
        lda d+1
        adc minor+1
        sta d+1
        bit sy
        bmi @up
        inx
        bne @row
@up:    dex
@row:   lda _hgr_rowlo,x
        sta ptr1
        lda _hgr_rowhi,x
        sta ptr1+1
        jmp @step
@flat:  clc
        lda d
        adc flat
        sta d
        lda d+1
        adc flat+1
        sta d+1
@step:  lsr mask
        bne x_left
        lda #$40
        sta mask
        dey
        jmp x_left
@maybe_end:
        lda mask
        cmp endmask
        bne @next
        rts

; y-major (dy > dx, so dx < 192): flat = 2*dx, minor = 2*dx - 2*dy,
; D = 2*dx - dy - 1. X = row, Y = column.
y_major:
        lda dx
        asl
        sta flat
        lda #0
        rol
        sta flat+1
        lda tmp2
        asl
        sta minor
        lda #0
        rol
        sta minor+1
        sec
        lda flat
        sbc minor
        sta minor
        lda flat+1
        sbc minor+1
        sta minor+1
        clc
        lda flat
        sbc tmp2
        sta d
        lda flat+1
        sbc #0
        sta d+1
@pixel: lda mask
        ora (ptr1),y
        sta (ptr1),y
        cpx _hgr_l_y1
        beq @done
        lda d+1
        bmi @flat
        clc
        lda d
        adc minor
        sta d
        lda d+1
        adc minor+1
        sta d+1
        bit sx
        bmi @left
        asl mask
        bpl @y
        lda #1
        sta mask
        iny
        bne @y                  ; always
@left:  lsr mask
        bne @y
        lda #$40
        sta mask
        dey
        jmp @y
@flat:  clc
        lda d
        adc flat
        sta d
        lda d+1
        adc flat+1
        sta d+1
@y:     bit sy
        bmi @up
        inx
        bne @row                ; always
@up:    dex
@row:   lda _hgr_rowlo,x
        sta ptr1
        lda _hgr_rowhi,x
        sta ptr1+1
        jmp @pixel
@done:  rts
