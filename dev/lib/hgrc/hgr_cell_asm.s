; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_cell_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_cell_asm
.exportzp _hgr_c_cx, _hgr_c_cy, _hgr_c_set
.import _hgr_pixrect_asm
.importzp _hgr_r_mode, _hgr_r_rows, _hgr_r_x, _hgr_r_xr, _hgr_r_y0
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_c_cx:    .res 1        ; cell column (px = cx*8)
_hgr_c_cy:    .res 1        ; cell row    (py = cy*8)
_hgr_c_set:   .res 1        ; 1 = fill, 0 = clear

.segment "CODE"
_hgr_cell_asm:
        lda     _hgr_c_cx
        sta     _hgr_r_x
        lda     #0
        sta     _hgr_r_x+1
        asl     _hgr_r_x
        rol     _hgr_r_x+1
        asl     _hgr_r_x
        rol     _hgr_r_x+1
        asl     _hgr_r_x
        rol     _hgr_r_x+1          ; hgr_r_x = cx*8
        clc
        lda     _hgr_r_x
        adc     #5
        sta     _hgr_r_xr
        lda     _hgr_r_x+1
        adc     #0
        sta     _hgr_r_xr+1         ; hgr_r_xr = hgr_r_x + 5
        lda     _hgr_c_cy
        asl     a
        asl     a
        asl     a
        sta     _hgr_r_y0           ; hgr_r_y0 = cy*8
        lda     #6
        sta     _hgr_r_rows         ; 6-row block
        lda     _hgr_c_set
        sta     _hgr_r_mode
        ; tail-call the independently linked rectangle kernel
        jmp _hgr_pixrect_asm
