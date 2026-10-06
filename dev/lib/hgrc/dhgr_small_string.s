; VERHILLE Arnaud — GPL-3.0. Bank-safe compact string renderer.
; Coordinates: dhgr_small_x/y; string: A/X. Optional progress between cells
; supports application VBL accounting without coupling the library to a game.
.import _dhgr_small_x, _dhgr_small_y, _dhgr_small_char
.importzp ptr4
.include "dhgr_small_layout.inc"
.export _dhgr_small_string
.ifdef DHGR_SMALL_USE_PROGRESS
.import _dhgr_small_progress
.endif
.code
_dhgr_small_string:
        sta ptr4
        stx ptr4+1
        lda _dhgr_small_x
        cmp #(141-DHGR_SMALL_ADVANCE)
        bcs @done
        lda _dhgr_small_y
        cmp #(193-DHGR_SMALL_HEIGHT)
        bcs @done
@char:
.ifdef DHGR_SMALL_USE_PROGRESS
        jsr _dhgr_small_progress
.endif
        ldy #0
        lda (ptr4),y
        beq @done
        jsr _dhgr_small_char
        lda _dhgr_small_x
        clc
        adc #DHGR_SMALL_ADVANCE
        sta _dhgr_small_x
        cmp #(141-DHGR_SMALL_ADVANCE)
        bcs @done
        inc ptr4
        bne @char
        inc ptr4+1
        jmp @char
@done: rts
