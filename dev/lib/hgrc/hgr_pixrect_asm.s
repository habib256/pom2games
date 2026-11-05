; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_pixrect_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
; Leaf kernel, destroys A/X/Y, ptr1..ptr4/tmp1..tmp4. Non-reentrant.
.export _hgr_pixrect_asm
.import _hgr_col7, _hgr_mask7, _hgr_rowhi, _hgr_rowlo
.importzp _hgr_r_mode, _hgr_r_rows, _hgr_r_x, _hgr_r_xr, _hgr_r_y0
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
; The arguments stay intact; edge state lives only until this call returns.
gr_colL = tmp3              ; left byte column
gr_colR = tmp4              ; right byte column (== colL for one byte)
gr_keepL = ptr3             ; left byte: AND mask
gr_setL = ptr3+1            ; left byte: OR mask
gr_keepR = ptr4             ; right byte: AND mask
gr_setR = ptr4+1            ; right byte: OR mask

.segment "ZEROPAGE"
gr_setF:  .res 1             ; full bytes: stored directly ($7F fill / $00 erase)

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
        eor #$7f             ; A-1 is already in 0..63
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
        sbc #0               ; ASL cleared C: subtract one, result in 1..127
        sta tmp2             ; tmp2 = rightMask
        ; --- build keep/set from leftMask/rightMask + mode ------------------
        lda gr_colR
        cmp gr_colL          ; C=1 (ordered edges); mask setup preserves it
        bne @multi
        ; single byte: combined mask = leftMask & rightMask
        lda tmp1
        and tmp2
        sta tmp1             ; tmp1 = combined mask
@multi:
        ; Share mask preparation with single-byte rectangles. Their right
        ; edge values are unused; no second rendering path is needed.
        lda _hgr_r_mode
        bne @multi_set
        ; clear: keep = ~mask & $7F (drop palette too), set/full = 0
        lda tmp1
        eor #$7f
        sta gr_keepL
        lda tmp2
        eor #$7f
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
        sta gr_setF
        lda tmp1
        sta gr_setL
        lda tmp2
        sta gr_setR
@fill:
        lda _hgr_r_y0
        sta tmp1             ; current scanline
        lda _hgr_r_rows
        sta tmp2             ; rows remaining
        ; Full bytes between the edges: pairs in ptr2, odd one in ptr2+1.
        ; A single-byte rectangle uses neither. C=1 from the edge comparison.
        lda gr_colR
        sbc gr_colL
        beq @prow
        sbc #1               ; C = 1: colR - colL - 1
        lsr
        sta ptr2
        lda #0
        rol
        sta ptr2+1
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
        cpy gr_colR          ; Y is still the left byte column
        beq @prowend
        ; full bytes colL+1 .. colR-1: pairs, then the odd one (A holds setF)
        iny
        ldx ptr2
        beq @podd            ; adjacent edges have no pair between them
        lda gr_setF
@pfull: sta (ptr1),y         ; 21 cycles for two bytes
        iny
        sta (ptr1),y
        iny
        dex
        bne @pfull           ; clipped columns stay in 0..39
@podd:  ldx ptr2+1
        beq @pright
        lda gr_setF
        sta (ptr1),y
        iny
@pright:
        lda (ptr1),y
        and gr_keepR
        ora gr_setR
        sta (ptr1),y
@prowend:
        inc tmp1             ; next scanline
        dec tmp2
        bne @prow
        rts
