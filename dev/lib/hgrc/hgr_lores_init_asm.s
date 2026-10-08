; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_lores_init_asm.s — LORES mode switch for C, its own archive member.
.export _hgr_lores_init

.segment "CODE"
.include "apple2.inc"
_hgr_lores_init:
        jsr native_video        ; leave DHGR/80-column banking before LORES
        lda TXTCLR
        lda LORES
        lda LOWSCR
        lda MIXCLR
        rts

; Reuse the model-checked native video reset; only this referenced entry is
; assembled, so a LORES-only program does not link the HIRES mode routines.
.include "hgr.asm"
