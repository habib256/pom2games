.setcpu "65C02"
.import _gfx_u16_digits
.export _fast_number := _gfx_u16_digits
.code
; Copy the five score digits straight into the current page's HUD buffer.
.export _hud_number
.import _hud_wanted
.importzp ptr1
_hud_number:
        jsr _gfx_u16_digits
        sta ptr1
        stx ptr1+1
        ldx #0
        ldy #0
@copy: lda (ptr1),y
        sta _hud_wanted,x
        inx
        iny
        cpy #5
        bne @copy
        rts
