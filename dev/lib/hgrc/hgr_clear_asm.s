; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_clear_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
; void hgr_clear(unsigned char fill): fill the 8 KB draw page (hgr_base) with
; HGR_CLEAR_LOOP from lib/apple2/hgr.asm: ~46 000 cycles instead of ~90 000.
.export _hgr_clear
.import _hgr_base

.segment "CODE"
.include "hgr.asm"              ; HGR_CLEAR_LOOP only (routines are .ifref)
_hgr_clear:
        ldx _hgr_base        ; draw-page high byte ($20 page1 / $40 page2)
        bne @baseok          ; 0 = unset (BSS) -> default to page 1
        ldx #$20
        stx _hgr_base
@baseok:
        HGR_CLEAR_LOOP       ; A = fill byte, X = first page
        rts
