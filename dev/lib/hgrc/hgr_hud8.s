; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_hud8_init: same frame/state prefix as the doubled-font HUD.
.export _hgr_hud8_init
.import hgr_hud_init_store, hgr_hud_init_fail
.importzp sp, ptr1, tmp1
.include "hgr_hud_init.inc"
.code
_hgr_hud8_init:
        hgr_hud_init_extent 5, 8, reject
        tax                    ; eight pixels per cell, at most 40
        jmp hgr_hud_init_store
reject: jmp hgr_hud_init_fail
