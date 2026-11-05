; VERHILLE Arnaud — GPL-3.0. Compact DHGR font, every color-pixel phase.
; RAMRD/WRT remain main between byte writes. Short per-row transactions use
; the zero-page auxiliary read trampoline and preserve IRQ state for the mouse.
; Column, ink-table base and edge masks are prepared once per glyph. Fully
; covered auxiliary bytes are stored without a read through the trampoline.
; Destroys A/X/Y, ptr1..ptr3/tmp1/tmp2; preserves the string cursor in ptr4.
; Non-reentrant. aux_read only changes A and flags, so scratch survives it.
.import _dhgr_small_x, _dhgr_small_y, _dhgr_base
.importzp ptr1, ptr2, ptr3, tmp1, tmp2
.importzp aux_read
.export _dhgr_small_char
small_bits = tmp1
small_ink_index = tmp2
.bss
small_first: .res 1
small_count: .res 1
small_row: .res 1
small_remaining: .res 1
small_inverse: .res 4
small_main_start: .res 1
small_aux_start: .res 1
.include "dhgr_small_layout.inc"
.ifdef DHGR_SMALL_FONT_EXTERNAL
small_font = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::font
small_font_lo = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::font_lo
small_font_hi = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::font_hi
small_xbyte = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::xbyte
small_xphase = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::xphase
small_left_masks = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::left_masks
small_right_masks = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::right_masks
small_row_lo = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::row_lo
small_row_hi = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::row_hi
small_ink = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::ink
small_ink_lo = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::ink_lo
small_ink_hi = DHGR_SMALL_FONT_BASE+DhgrSmallLayout::ink_hi
.else
.rodata
.include "dhgr_small_data.inc"
.endif
; Public immutable data, shared by custom renderers and enlarged logos.
.export _dhgr_small_font := small_font
.export _dhgr_row_lo := small_row_lo, _dhgr_row_hi := small_row_hi
.export _dhgr_color_byte := small_xbyte
.code
_dhgr_small_char:
        ldx _dhgr_small_x
        cpx #136
        bcc :+
        rts
:
        ldy _dhgr_small_y
        cpy #188
        bcc :+
        rts
:
        cmp #'a'
        bcc :+
        cmp #'z'+1
        bcs :+
        and #$DF
:       cmp #32
        bcc small_question
        cmp #96
        bcc small_valid
small_question:
        lda #'?'
small_valid:
        sec
        sbc #32
        tax
        lda small_font_lo,x
        sta ptr2
        lda small_font_hi,x
        sta ptr2+1
        ldx _dhgr_small_x
        lda small_xbyte,x
        lsr
        sta small_first         ; bank column, invariant over the five rows
        lda #0
        rol
        sta small_aux_start
        eor #1
        sta small_main_start
        lda small_xphase,x
        tax
        lda small_ink_lo,x
        sta ptr3
        lda small_ink_hi,x
        sta ptr3+1
        lda #3
        cpx #2
        bcc :+
        lda #4
:       sta small_count
        sty small_row
        ; Only the two ends preserve old pixels. Slot 3 is either the
        ; right edge (four bytes) or unused (three bytes).
        lda #0
        sta small_inverse+1
        sta small_inverse+2
        lda small_left_masks,x
        eor #$7F
        sta small_inverse
        ldy small_count
        dey
        lda small_right_masks,x
        eor #$7F
        sta small_inverse,y
        lda #5
        sta small_remaining
small_next_row:
        ldy #0
        lda (ptr2),y
        asl
        asl
        sta small_ink_index     ; multiples of four: OR the byte index below
        ldx small_row
        lda small_first
        clc
        adc small_row_lo,x
        sta ptr1
        lda small_row_hi,x
        adc _dhgr_base
        sta ptr1+1
        php
        sei
        ldx small_main_start
        txa
        ora small_ink_index
        tay
        lda (ptr3),y
        sta small_bits
        ldy #0
        lda (ptr1),y
        and small_inverse,x
        ora small_bits
        sta (ptr1),y
        inx
        inx
        cpx small_count
        bcs small_aux_first
        txa
        ora small_ink_index
        tay
        lda (ptr3),y
        sta small_bits
        ldy #1
        lda (ptr1),y
        and small_inverse,x
        ora small_bits
        sta (ptr1),y
small_aux_first:
        ldx small_aux_start
        txa
        ora small_ink_index
        tay
        lda (ptr3),y
        sta small_bits
        ldy small_aux_start
        lda small_inverse,x
        beq :+                  ; a fully covered byte needs no auxiliary read
        jsr aux_read
        and small_inverse,x
:       ora small_bits
        sta $C005
        sta (ptr1),y
        sta $C004
        inx
        inx
        cpx small_count
        bcs small_row_done
        txa
        ora small_ink_index
        tay
        lda (ptr3),y
        sta small_bits
        ldy small_aux_start
        iny
        lda small_inverse,x
        beq :+
        jsr aux_read
        and small_inverse,x
:       ora small_bits
        sta $C005
        sta (ptr1),y
        sta $C004
small_row_done:
        plp
        inc ptr2
        bne :+
        inc ptr2+1
:       inc small_row
        dec small_remaining
        beq :+
        jmp small_next_row
:       ldx #0
        rts
