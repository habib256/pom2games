; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_hud_init(field, x, y, width): A=width; stack=y,xlo,xhi,fieldlo,fieldhi.
.export _hgr_hud_init
.import hgr_hud_init_store, hgr_hud_init_fail
.importzp sp, ptr1, tmp1
.code
_hgr_hud_init:
        cmp #1
        bcc reject
        cmp #15
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
        cmp #177
        bcs reject
        lda tmp1
        asl a
        asl a
        asl a
        clc
        adc tmp1
        asl a                  ; 18*width <= 252
        sec
        sbc #2                 ; last glyph is 16 pixels, pitch is 18
        tax
        jmp hgr_hud_init_store
reject: jmp hgr_hud_init_fail
