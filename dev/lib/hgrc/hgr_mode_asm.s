; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_mode_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
; Always linked (hgr_init). hgr_init_clear, hgr_lores_init and the page flip
; are separate objects (hgr_mode_clear_asm.s, hgr_lores_init_asm.s,
; hgr_rows_asm.s) so a program only pays for the entry points it calls and a
; DHGR-only program never needs the HGR row tables.
.export _hgr_init, _hgr_text_restore

.segment "CODE"
.include "apple2.inc"
_hgr_init         = hgr_init         ; referenced before the include: assembled
_hgr_text_restore = text_restore
.include "hgr.asm"
