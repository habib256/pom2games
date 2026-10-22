; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_native_asm.s — native_video (IIe/IIc: main banks, 80STORE/80COL/DHGR
; off) as its own archive member: hgr_init, hgr_init_clear and
; hgr_lores_init share this one copy.
.export native_video

.segment "CODE"
.include "apple2.inc"
.include "hgr.asm"
