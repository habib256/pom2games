; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_mode_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_init, _hgr_init_clear, _hgr_lores_init, _hgr_text_restore
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "CODE"
.include "apple2.inc"
.include "hgr.asm"              ; hgr_init / hgr_init_clear / text_restore
_hgr_init       = hgr_init
_hgr_init_clear = hgr_init_clear
_hgr_text_restore   = text_restore
_hgr_lores_init:
        lda TXTCLR
        lda LORES
        lda LOWSCR
        lda MIXCLR
        rts
