; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_pixrect_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_pixrect_asm
.import _hgr_col7, _hgr_mask7, _hgr_rowhi, _hgr_rowlo
.importzp _hgr_r_mode, _hgr_r_rows, _hgr_r_x, _hgr_r_xr, _hgr_r_y0
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
gr_colL:  .res 1             ; left  byte column
gr_colR:  .res 1             ; right byte column (== colL if rect fits one byte)
gr_keepL: .res 1             ; left  byte: AND mask
gr_setL:  .res 1             ; left  byte: OR  mask
gr_setF:  .res 1             ; full bytes: stored directly ($7F fill / $00 erase)
gr_keepR: .res 1             ; right byte: AND mask
gr_setR:  .res 1             ; right byte: OR  mask

.segment "CODE"
_hgr_pixrect_asm:
        ; --- left edge: gr_colL = col7[x], leftMask (bits x%7..6) -> tmp1 ----
        lda _hgr_r_x+1
        bne @xhi
        ldx _hgr_r_x
        lda _hgr_col7,x
        sta gr_colL
        lda _hgr_mask7,x
        jmp @xmask
@xhi:
        ldx _hgr_r_x
        lda _hgr_col7+256,x
        sta gr_colL
        lda _hgr_mask7+256,x
@xmask:
        sec                  ; A = 1<<bitL ; leftMask = (~(A-1)) & $7F
        sbc #1
        eor #$ff
        and #$7f
        sta tmp1             ; tmp1 = leftMask
        ; --- right edge: gr_colR = col7[xr], rightMask (bits 0..xr%7) -> tmp2 -
        lda _hgr_r_xr+1
        bne @rhi
        ldx _hgr_r_xr
        lda _hgr_col7,x
        sta gr_colR
        lda _hgr_mask7,x
        jmp @rmask
@rhi:
        ldx _hgr_r_xr
        lda _hgr_col7+256,x
        sta gr_colR
        lda _hgr_mask7+256,x
@rmask:
        asl a                ; A = 1<<bitR ; rightMask = ((A<<1)-1) & $7F
        sec
        sbc #1
        and #$7f
        sta tmp2             ; tmp2 = rightMask
        ; --- build keep/set from leftMask/rightMask + mode ------------------
        lda gr_colL
        cmp gr_colR
        bne @multi
        ; single byte: combined mask = leftMask & rightMask
        lda tmp1
        and tmp2
        sta tmp1             ; tmp1 = combined mask
        lda _hgr_r_mode
        bne @one_set
        lda tmp1             ; clear: keepL = ~mask & $7F (also drops palette bit)
        eor #$ff
        and #$7f
        sta gr_keepL
        lda #0
        sta gr_setL
        jmp @fill
@one_set:
        lda #$7f             ; fill: keepL = $7F (clears palette), setL = mask
        sta gr_keepL
        lda tmp1
        sta gr_setL
        jmp @fill
@multi:
        lda _hgr_r_mode
        bne @multi_set
        ; clear: keep = ~mask & $7F (drop palette too), set/full = 0
        lda tmp1
        eor #$ff
        and #$7f
        sta gr_keepL
        lda tmp2
        eor #$ff
        and #$7f
        sta gr_keepR
        lda #0
        sta gr_setL
        sta gr_setF
        sta gr_setR
        jmp @fill
@multi_set:
        lda #$7f             ; fill: clear palette + OR edge masks, full = $7F
        sta gr_keepL
        sta gr_keepR
        lda tmp1
        sta gr_setL
        lda tmp2
        sta gr_setR
        lda #$7f
        sta gr_setF
@fill:
        lda _hgr_r_y0
        sta tmp1             ; current scanline
        lda _hgr_r_rows
        sta tmp2             ; rows remaining
@prow:
        ldy tmp1
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        ; left (or single) byte: (byte & keepL) | setL
        ldy gr_colL
        lda (ptr1),y
        and gr_keepL
        ora gr_setL
        sta (ptr1),y
        ; single-byte rectangle? then this row is done
        lda gr_colL
        cmp gr_colR
        beq @prowend
        ; full bytes colL+1 .. colR-1 (A holds setF across the run)
        ldy gr_colL
        iny
        lda gr_setF
@pfull:
        cpy gr_colR
        bcs @pright
        sta (ptr1),y
        iny
        bne @pfull           ; Y is a column 1..39, never 0 -> always loops
@pright:
        ldy gr_colR
        lda (ptr1),y
        and gr_keepR
        ora gr_setR
        sta (ptr1),y
@prowend:
        inc tmp1             ; next scanline
        dec tmp2
        bne @prow
        rts
