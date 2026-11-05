; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_hud8_init: same frame/state prefix as the doubled-font HUD.
.export _hgr_hud8_init
.import hgr_hud_init_store, hgr_hud_init_fail
.importzp sp, ptr1, tmp1
.code
_hgr_hud8_init:
        cmp #1
        bcc reject
        cmp #6
        bcs reject
        sta tmp1
        ldy #3
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        ora ptr1
        beq reject
        ldy #0
        lda (sp),y
        cmp #185
        bcs reject
        lda tmp1
        asl a
        asl a
        asl a
        tax                    ; eight pixels per cell, at most 40
        jmp hgr_hud_init_store
reject: jmp hgr_hud_init_fail
