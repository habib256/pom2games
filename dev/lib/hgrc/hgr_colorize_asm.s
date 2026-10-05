; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_colorize_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_colorize_asm
.exportzp _hgr_z_col0, _hgr_z_ncols, _hgr_z_y0, _hgr_z_rows
.import _hgr_rowhi, _hgr_rowlo
.importzp _hgr_z_ce, _hgr_z_co, _hgr_z_hi
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_z_col0:  .res 1        ; first byte column of the text box
_hgr_z_ncols: .res 1        ; number of byte columns
_hgr_z_y0:    .res 1        ; top scanline
_hgr_z_rows:  .res 1        ; number of scanlines

.segment "CODE"
_hgr_colorize_asm:
        lda _hgr_z_y0
        sta tmp1             ; current scanline
        lda _hgr_z_rows
        sta tmp2             ; rows remaining
@zrow:
        ldy tmp1
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ldx _hgr_z_ncols    ; column counter
        ldy _hgr_z_col0     ; current (absolute) byte column
@zcol:
        tya                  ; carrier = (col & 1) ? co : ce
        and #1
        bne @zodd
        lda _hgr_z_ce
        jmp @zhave
@zodd:
        lda _hgr_z_co
@zhave:
        and (ptr1),y         ; keep only the carrier bits of the white glyph
        ora _hgr_z_hi       ; set the palette high bit (orange/blue) or nothing
        sta (ptr1),y
        iny
        dex
        bne @zcol
        inc tmp1             ; next scanline
        dec tmp2
        bne @zrow
        rts
