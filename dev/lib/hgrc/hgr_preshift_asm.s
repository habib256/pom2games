; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_preshift_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_xs_run, _hgr_xs_setup
.exportzp _hgr_xs_x, _hgr_xs_y, _hgr_xs_spr
.import _hgr_col7, _hgr_phase7, _hgr_rowhi, _hgr_rowlo
.import _hgr_build_columns, _hgr_build_phases, _hgr_preshift_xor_run
.importzp _hgr_b_col, _hgr_b_h, _hgr_b_src, _hgr_b_stride, _hgr_b_w, _hgr_b_y
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_xs_x:    .res 2        ; pixel x (0..279)
_hgr_xs_y:    .res 1        ; pixel y (0..191)
_hgr_xs_spr:  .res 2        ; pointer to the hgr_sprite_t {bits, stride, h}

.segment "CODE"
; hgr_xs_x/y/spr -> the clipped hgr_b_* block of the selected phase, for the
; XOR loop below or hgr_blit7_run (SET/CLEAR). Rows built by the caller.
; Requires x<280, y<192, nonzero stride/height (the public entries validate).
; Setup clobbers A/X/Y, ptr1/ptr2, tmp1/tmp2/tmp3 and hgr_b_* parameters.
; tmp4 is preserved, including through the normal/folded table builders.
_hgr_xs_setup:
        jsr _hgr_build_columns
        jsr _hgr_build_phases
        ; col = hgr_col7[x] -> _hgr_b_col ; phase = hgr_phase7[x] -> tmp1
        lda _hgr_xs_x+1
        bne @xhi
        ldx _hgr_xs_x
        lda _hgr_col7,x
        ldy _hgr_phase7,x
        jmp @xset
@xhi:
        ldx _hgr_xs_x
        lda _hgr_col7+256,x
        ldy _hgr_phase7+256,x
@xset:
        sta _hgr_b_col
        sty tmp1                  ; tmp1 = phase (0..6)
        ; deref spr -> ptr2 ; read bits/stride/h
        lda _hgr_xs_spr
        sta ptr2
        lda _hgr_xs_spr+1
        sta ptr2+1
        ldy #0
        lda (ptr2),y              ; bits low
        sta _hgr_b_src
        iny
        lda (ptr2),y              ; bits high
        sta _hgr_b_src+1
        iny
        lda (ptr2),y              ; stride
        sta _hgr_b_stride
        sta _hgr_b_w             ; default w = stride
        sta tmp2                  ; tmp2 = stride
        iny
        lda (ptr2),y              ; h
        sta _hgr_b_h             ; default h
        sta tmp3                  ; tmp3 = full h (for the phase offset)
        lda _hgr_xs_y
        sta _hgr_b_y
        ; Right clip against the remaining columns: no overflowing sum.
        lda #40
        sec
        sbc _hgr_b_col
        cmp tmp2
        bcs @wok
        sta _hgr_b_w
@wok:
        ; Bottom clip against the remaining rows, preserving full source h.
        lda #192
        sec
        sbc _hgr_xs_y
        cmp tmp3
        bcs @hok
        sta _hgr_b_h
@hok:
        ; src += phase * (h * stride). Phase zero needs no product.
        ldx tmp1
        beq @offdone
        ; Count the smaller factor for narrow/short sprites (below ten).
        ; Otherwise use eight binary steps: no height-proportional loop.
        lda tmp2
        ldy tmp3
        cmp tmp3
        bcs @sorted
        sty tmp2
        tay
@sorted:
        cpy #10
        bcc @small
        ; Eight shift/add steps for larger factors. A:tmp3 is the
        ; running 16-bit product; carry from ROR supplies the next bit.
        sty tmp3
        lda #0
        ldy #8
        lsr tmp3
@multiply:
        bcc @noadd
        clc
        adc tmp2
@noadd:
        ror a
        ror tmp3
        dey
        bne @multiply
        sta ptr1+1
        lda tmp3
        bcc @product_ready       ; initial LSR cleared bit 7: eighth ROR leaves C=0
@small:
        ; Start with one copy, so a factor of one needs no loop at all.
        lda #0
        sta ptr1+1
        lda tmp2
        dey
        beq @product_ready
@hloop:
        clc
        adc tmp2                  ; add the larger factor, keeping the low byte in A
        bcc @h2
        inc ptr1+1
@h2:
        dey
        bne @hloop
@product_ready:
        sta ptr1
@ploop:
        clc
        lda _hgr_b_src
        adc ptr1
        sta _hgr_b_src
        lda _hgr_b_src+1
        adc ptr1+1
        sta _hgr_b_src+1
        dex
        bne @ploop
@offdone:
        rts

_hgr_xs_run:
        jsr _hgr_xs_setup
        jmp _hgr_preshift_xor_run   ; the XOR row loop, in hgr_blit7_asm.s
