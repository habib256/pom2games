; VERHILLE Arnaud — GPL-3.0. Shared HGR carrier selection.
; cc65 fastcall: A=color, A/X=1/0 for accepted/rejected. D=0.
; Reject unknown/white colors before changing any parameter; no scratch,
; software-stack access, or extra RAM. hgr.h colors are violet..blue = 1..4.
.export _hgr_set_carrier
.importzp _hgr_z_ce, _hgr_z_co, _hgr_z_hi
.rodata
even_mask: .byte $55,$2a,$2a,$55 ; violet, green, orange, blue
.code
_hgr_set_carrier:
        sec
        sbc #1
        cmp #4
        bcs invalid
        tax
        lda even_mask,x
        sta _hgr_z_ce
        eor #$7f
        sta _hgr_z_co
        cpx #2                 ; orange/blue have the palette bit set
        lda #0
        ror
        sta _hgr_z_hi
        lda #1
        ldx #0
        rts
invalid:
        lda #0
        tax
        rts
