; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_byte_rect_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_fill_rect_asm
.exportzp _hgr_f_y0, _hgr_f_rows, _hgr_f_col0, _hgr_f_cols, _hgr_f_val
.import _hgr_rowhi, _hgr_rowlo
.importzp ptr1, tmp1, tmp2, tmp3

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
        lda _hgr_f_cols
        and #1               ; an odd width starts with a single byte
        sta tmp3
@frow:
        ldy tmp1
        lda _hgr_rowlo,y
        clc
        adc _hgr_f_col0       ; clipped row offset + column <= $F7: no carry
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ldy _hgr_f_cols
        dey                  ; Y counts backwards from the last byte
        lda _hgr_f_val
        ldx tmp3
        bne @fsingle
@fpair: sta (ptr1),y          ; 19 cycles per pair; Y is also the counter
        dey
@fsingle:
        sta (ptr1),y
        dey
        bpl @fpair
        inc tmp1             ; next scanline
        dec tmp2
        bne @frow
        rts
