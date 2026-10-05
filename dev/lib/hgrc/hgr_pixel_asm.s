; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_pixel_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_plot_asm, _hgr_unplot_asm
.exportzp _hgr_p_x, _hgr_p_y
.import _hgr_col7, _hgr_mask7, _hgr_rowhi, _hgr_rowlo
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_p_x:     .res 2        ; pixel x (0..279)
_hgr_p_y:     .res 1        ; pixel y (0..191)

.segment "CODE"
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
