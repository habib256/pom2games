; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_mode_clear_asm.s — hgr_init_clear for C, its own archive member.
.export _hgr_init_clear
.import _hgr_init

.segment "CODE"
.include "apple2.inc"
hgr_init = _hgr_init                 ; the tail JMP lands on hgr_mode_asm's copy
_hgr_init_clear = hgr_init_clear
.include "hgr.asm"
