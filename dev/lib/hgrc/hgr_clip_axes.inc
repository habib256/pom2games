; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; A and rows hold the two unsigned y endpoints. Return the first visible
; scanline in top and the inclusive height in rows, or branch to reject.
.macro hgr_clip_y top, rows, reject
        .local y_ordered, y_clipped
        cmp rows
        bcc y_ordered
        beq y_ordered
        tax
        lda rows
        stx rows
y_ordered:
        cmp #192
        bcs reject
        sta top
        lda rows
        cmp #192
        bcc y_clipped
        lda #191
y_clipped:
        sec
        sbc top
        adc #0                  ; carry from nonnegative subtraction: inclusive
        sta rows
.endmacro

; left and right hold unsigned 16-bit endpoints. A holds the high byte of left.
; Return the sorted, clipped endpoints, or branch to reject. When width
; is below 256, consumers use only the low byte of the right endpoint.
.macro hgr_clip_x width, left, right, reject
        .local x_ordered, swap, left_ready, clip, ready
        cmp right+1
        bcc x_ordered
        bne swap
        lda left
        cmp right
        bcc x_ordered
        beq x_ordered
swap:
        ldx left
        lda right
        sta left
        stx right
        ldx left+1
        lda right+1
        sta left+1
        stx right+1
x_ordered:
        lda left+1
        .if width < 256
        bne reject
        .else
        cmp #(>width)+1
        bcs reject
        cmp #>width
        bne left_ready
        .endif
        lda left
        cmp #<width
        bcs reject
left_ready:
        lda right+1
        .if width < 256
        bne clip
        .else
        cmp #>width
        bcc ready
        bne clip
        .endif
        lda right
        cmp #<width
        bcc ready
clip:
        lda #<(width-1)
        sta right
        .if width >= 256
        lda #>(width-1)
        sta right+1
        .endif
ready:
.endmacro

; Load a 16-bit pixel x from the cc65 stack, starting at its high byte.
; Branch directly for x < 256 or x >= 512. For 256..511, the caller
; chooses the fall-through path: C=0 if x < 280, C=1 otherwise.
.macro hgr_load_pixel_x high_slot, dest, valid, reject
        ldy #high_slot
        lda (sp),y
        cmp #2
        bcs reject
        sta dest+1
        tax
        dey
        lda (sp),y
        sta dest
        cpx #0
        beq valid
        cmp #<280
.endmacro

; Visible origin, exclusive limit. The caller initializes clipped to full.
; Use the same byte for both when the original extent is no longer needed.
.macro hgr_clip_extent limit, origin, full, clipped
        lda #limit
        sec
        sbc origin
        cmp full
        bcs :+
        sta clipped
:
.endmacro
