; hgr_byte_rect_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_fill_rect_asm
.exportzp _hgr_f_y0, _hgr_f_rows, _hgr_f_col0, _hgr_f_cols, _hgr_f_val
.import _hgr_rowhi, _hgr_rowlo
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_f_y0:    .res 1        ; top scanline of the rectangle
_hgr_f_rows:  .res 1        ; number of scanlines (>= 1)
_hgr_f_col0:  .res 1        ; first byte column
_hgr_f_cols:  .res 1        ; number of byte columns (>= 1)
_hgr_f_val:   .res 1        ; fill byte (0 = erase)

.segment "CODE"
_hgr_fill_rect_asm:
        lda _hgr_f_y0
        sta tmp1             ; current scanline
        lda _hgr_f_rows
        sta tmp2             ; rows remaining
@frow:
        ldy tmp1
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ldx _hgr_f_cols     ; column counter
        ldy _hgr_f_col0     ; current column
        lda _hgr_f_val      ; (preserved across STA/INY/DEX)
@fcol:
        sta (ptr1),y
        iny
        dex
        bne @fcol
        inc tmp1             ; next scanline
        dec tmp2
        bne @frow
        rts
