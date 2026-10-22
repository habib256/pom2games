; VERHILLE Arnaud — GPL-3.0. Optional HGR table, main RAM/ZP.
; x -> bit mask (1 << x % 7), x = 0..279, built once by hgr_x7_fill.
; No inputs. Clobbers A/X/Y, ptr1, tmp1..tmp4; not reentrant.
.export _hgr_build_masks, _hgr_mask7
.import hgr_x7_fill
.importzp ptr1
.bss
_hgr_mask7: .res 280
ready: .res 1
.code
_hgr_build_masks:
        lda ready
        bne @done
        inc ready
        lda #<_hgr_mask7
        sta ptr1
        lda #>_hgr_mask7
        sta ptr1+1
        ldx #1
        jmp hgr_x7_fill
@done:  rts
