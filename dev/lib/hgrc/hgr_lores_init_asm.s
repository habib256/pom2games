; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_lores_init_asm.s — LORES mode switch for C, its own archive member.
.export _hgr_lores_init

.segment "CODE"
.include "apple2.inc"
_hgr_lores_init:
        lda TXTCLR
        lda LORES
        lda LOWSCR
        lda MIXCLR
        rts
