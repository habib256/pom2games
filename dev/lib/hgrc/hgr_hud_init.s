; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared HUD initialization. X=extent, tmp1=width, ptr1=non-NULL state.
; y/width already checked by the font-specific entry.
; Stack=y,xlo,xhi,fieldlo,fieldhi. Only the common five-byte prefix is written;
; history remains caller-owned and untouched, including on rejected calls.
.export hgr_hud_init_store, hgr_hud_init_fail
.import addysp
.importzp sp, ptr1, tmp1, tmp2
.code
hgr_hud_init_store:
        ldy #2
        lda (sp),y
        cmp #2                 ; reject large x before adding extent can wrap
        bcs hgr_hud_init_fail
        sta tmp2
        dey
        txa
        clc
        adc (sp),y
        tax
        lda tmp2
        adc #0
        cmp #1
        bcc fits
        bne hgr_hud_init_fail
        cpx #25                ; x+extent <= 280 ($118)
        bcs hgr_hud_init_fail
fits:
        ldy #1
        lda (sp),y
        dey
        sta (ptr1),y            ; x low
        ldy #2
        lda (sp),y
        dey
        sta (ptr1),y            ; x high
        ldy #0
        lda (sp),y
        ldy #2
        sta (ptr1),y            ; y
        iny
        lda tmp1
        sta (ptr1),y            ; width
        iny
        lda #0
        sta (ptr1),y            ; valid
        lda #1
        bne finish
hgr_hud_init_fail:
        lda #0
finish:
        ldx #0
        ldy #5
        jmp addysp
