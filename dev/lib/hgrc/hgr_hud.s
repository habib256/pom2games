; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_hud_init(field, x, y, width): A=width; stack=y,xlo,xhi,fieldlo,fieldhi.
.export _hgr_hud_init
.import hgr_hud_init_store, hgr_hud_init_fail
.importzp sp, ptr1, tmp1
.include "hgr_hud_init.inc"
.code
_hgr_hud_init:
        hgr_hud_init_extent 14, 16, reject
        clc
        adc tmp1
        asl a                  ; 18*width <= 252
        sec
        sbc #2                 ; last glyph is 16 pixels, pitch is 18
        tax
        jmp hgr_hud_init_store
reject: jmp hgr_hud_init_fail
