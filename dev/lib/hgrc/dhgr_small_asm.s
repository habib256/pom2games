; VERHILLE Arnaud — GPL-3.0. Compact DHGR font, every color-pixel phase.
; RAMRD/WRT remain main between byte writes. Short per-row transactions use
; the zero-page auxiliary read trampoline and preserve IRQ state for the mouse.
.import _dhgr_small_x, _dhgr_small_y, _dhgr_base
.importzp ptr1, ptr2, ptr3
.importzp aux_read
.export _dhgr_small_char
.bss
small_first: .res 1
small_count: .res 1
small_phase: .res 1
small_row: .res 1
small_left: .res 1
small_right: .res 1
small_remaining: .res 1
small_inverse: .res 4
small_main_start: .res 1
small_aux_start: .res 1
small_bits: .res 1
.ifdef DHGR_SMALL_FONT_EXTERNAL
; Optional relocated data: the application copies dhgr_small_data.inc to
; $0800 before using this member. Default library users need no relocation.
small_font = $0800
small_font_lo = small_font+384
small_font_hi = small_font_lo+64
small_xbyte = small_font_hi+64
small_xphase = small_xbyte+140
small_left_masks = small_xphase+140
small_right_masks = small_left_masks+7
small_row_lo = small_right_masks+7
small_row_hi = small_row_lo+192
small_ink = small_row_hi+192
small_ink_lo = small_ink+448
small_ink_hi = small_ink_lo+7
.else
.rodata
.include "dhgr_small_data.inc"
.endif
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
        sta small_first
        lda small_xphase,x
        sta small_phase
        tax
        lda small_left_masks,x
        sta small_left
        lda small_right_masks,x
        sta small_right
        lda #3
        cpx #2
        bcc :+
        lda #4
:       sta small_count
        sty small_row
        lda small_first
        and #1
        sta small_aux_start
        eor #1
        sta small_main_start
        ldx #3
        lda #0
@inverse: sta small_inverse,x
        dex
        bpl @inverse
        lda small_left
        eor #$7F
        sta small_inverse
        ldx small_count
        dex
        lda small_right
        eor #$7F
        sta small_inverse,x
        lda #5
        sta small_remaining
        jmp small_next_row
small_done:
        rts
small_next_row:
        ldy #0
        lda (ptr2),y
        asl
        asl
        ldx small_phase
        clc
        adc small_ink_lo,x
        sta ptr3
        lda small_ink_hi,x
        adc #0
        sta ptr3+1
        ldx small_row
        lda small_first
        lsr
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
        tay
        lda (ptr3),y
        sta small_bits
        ldy small_aux_start
        jsr aux_read
        and small_inverse,x
        ora small_bits
        sta $C005
        sta (ptr1),y
        sta $C004
        inx
        inx
        cpx small_count
        bcs small_row_done
        txa
        tay
        lda (ptr3),y
        sta small_bits
        ldy small_aux_start
        iny
        jsr aux_read
        and small_inverse,x
        ora small_bits
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
