; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_pixel_asm.s — single white pixel set/clear: x 0..279, y 0..191, others
; ignored. col7/mask7 LUTs + the scanline table, NO per-pixel division; the
; three lazy tables are built on first use (their guards return at once).
.export _hgr_plot, _hgr_unplot, _hgr_plot_asm, _hgr_unplot_asm
.exportzp _hgr_p_x, _hgr_p_y
.import _hgr_col7, _hgr_mask7, _hgr_rowhi, _hgr_rowlo
.import _hgr_build_rows, _hgr_build_columns, _hgr_build_masks, incsp2
.importzp sp, ptr1, tmp1, tmp2

.segment "ZEROPAGE"
_hgr_p_x:     .res 2        ; pixel x (0..279)
_hgr_p_y:     .res 1        ; pixel y (0..191)

.segment "CODE"
; void hgr_plot(unsigned x, unsigned char y) — set (OR in) one white pixel.
_hgr_plot:
        jsr hgr_pixarg
        bcs @out
        ora (ptr1),y
        sta (ptr1),y
@out:   jmp incsp2

; void hgr_unplot(unsigned x, unsigned char y) — clear (AND off) one pixel.
_hgr_unplot:
        jsr hgr_pixarg
        bcs @out
        eor #$ff
        and (ptr1),y
        sta (ptr1),y
@out:   jmp incsp2

; C arguments (y in A, x on the C stack, left there) -> C=1 off-screen, else
; C=0 and hgr_pixsetup's Y=col, A=mask, ptr1=scanline, tables built.
hgr_pixarg:
        cmp #192
        bcs @rts
        sta _hgr_p_y
        ldy #1
        lda (sp),y
        sta _hgr_p_x+1
        tax
        dey
        lda (sp),y
        sta _hgr_p_x
        cpx #1
        bcc @in
        bne @rts                ; C=1
        cmp #24                 ; 256..279
        bcs @rts
@in:    jsr _hgr_build_rows
        jsr _hgr_build_columns
        jsr _hgr_build_masks
        jsr hgr_pixsetup
        clc
@rts:   rts

hgr_pixsetup:
        lda _hgr_p_x+1      ; x high byte
        bne @hi
        ldx _hgr_p_x        ; x low (0..255)
        lda _hgr_col7,x
        sta tmp1
        lda _hgr_mask7,x
        jmp @row
@hi:
        ldx _hgr_p_x        ; x low (0..23 -> x 256..279)
        lda _hgr_col7+256,x
        sta tmp1
        lda _hgr_mask7+256,x
@row:
        sta tmp2             ; mask
        ldy _hgr_p_y
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ldy tmp1             ; Y = byte column
        lda tmp2             ; A = mask
        rts

; --- _hgr_plot_asm : set (OR in) one white pixel ----------------------------
_hgr_plot_asm:
        jsr hgr_pixsetup    ; Y=col, A=mask, ptr1=scanline base
        ora (ptr1),y
        sta (ptr1),y
        rts

; --- _hgr_unplot_asm : clear (AND off) one pixel ----------------------------
_hgr_unplot_asm:
        jsr hgr_pixsetup
        eor #$ff             ; ~mask
        and (ptr1),y
        sta (ptr1),y
        rts
