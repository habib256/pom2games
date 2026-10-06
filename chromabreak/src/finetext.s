; VERHILLE Arnaud — GPL-3.0. Beautiful Boot text on DHGR, white on black.
; Each HGR dot of the 7x7 glyph becomes two DHGR dots: 14 dots, two bytes.
; The doubling tables are built at start in the free top of the $0800 image.
; fine_x counts 7-dot units (0..78): even units start in AUX, odd in MAIN.
; Whole bytes are written with bit 7 clear, so the cell background becomes
; black and, in Chat Mauve mixed mode, the text shows as 560-dot mono.
; Main RAM/ZP on entry and exit; AUX is selected only for single accesses,
; with IRQs masked (glyph rows are read from the AUX font).
.setcpu "65C02"
.importzp ptr1, ptr2, ptr3, tmp1, tmp2, tmp3, aux_read
.import _dhgr_row_lo, _dhgr_row_hi, _dhgr_base
.export _fine_char, _fine_text, _fine_x, _fine_y, _fine_init
.bss
_fine_x: .res 1
_fine_y: .res 1
.include "tables.inc"
fine_left = FINE_LEFT
fine_right = FINE_RIGHT
FINE_FONT_CONSTANTS_ONLY = 1
.include "fine_font.inc"
.include "levels.inc"
; The font planes sit in AUX right after the level bank (startup.s).
fine_font = LEVELS_AUX+LEVELS_SIZE
.export _fine_font := fine_font, _glyph_fetch, _glyph
.bss
_glyph: .res FINE_HEIGHT
.code
; Build fine_left/fine_right: HGR row bits 0..6 become dot pairs 0..13.
_fine_init:
        ldx #127
@glyph: stx tmp1
        stz tmp2
        stz tmp3
        ldy #7
@dot:   asl tmp2
        rol tmp3
        asl tmp2
        rol tmp3
        lda tmp1
        and #$40
        beq :+
        lda tmp2
        ora #3
        sta tmp2
:       asl tmp1
        dey
        bne @dot
        lda tmp2
        and #$7F
        sta fine_left,x
        lda tmp2
        asl
        lda tmp3
        rol
        sta fine_right,x
        dex
        bpl @glyph
        rts
; A = character; draws at fine_x/fine_y on the draw page, then advances fine_x.
; IRQs stay masked for the whole glyph (seven short rows, about 600 cycles).
_fine_char:
        cmp #'a'
        bcc :+
        cmp #'z'+1
        bcs :+
        and #$DF
:       sec
        sbc #FINE_FIRST
        cmp #FINE_COUNT
        bcc :+
        lda #0
:       clc
        adc #<fine_font
        sta ptr1
        lda #>fine_font
        adc #0
        sta ptr1+1
        ldx _fine_y
        stx tmp2
        lda _fine_x
        lsr
        sta tmp3
        lda #FINE_HEIGHT
        sta tmp1
        php
        sei
        bcs @odd_row
        ; Even unit: left half in AUX at tmp3, right half in MAIN at tmp3.
@even_row:
        ldx tmp2
        lda _dhgr_row_lo,x
        sta ptr3
        lda _dhgr_row_hi,x
        clc
        adc _dhgr_base
        sta ptr3+1
        ldy #0
        jsr aux_read
        tax
        ldy tmp3
        lda fine_right,x
        sta (ptr3),y
        lda fine_left,x
        sta $C005
        sta (ptr3),y
        sta $C004
        lda ptr1
        clc
        adc #FINE_COUNT
        sta ptr1
        bcc :+
        inc ptr1+1
:       inc tmp2
        dec tmp1
        bne @even_row
        beq @done
        ; Odd unit: left half in MAIN at tmp3, right half in AUX at tmp3+1.
@odd_row:
        ldx tmp2
        lda _dhgr_row_lo,x
        sta ptr3
        lda _dhgr_row_hi,x
        clc
        adc _dhgr_base
        sta ptr3+1
        ldy #0
        jsr aux_read
        tax
        ldy tmp3
        lda fine_left,x
        sta (ptr3),y
        iny
        lda fine_right,x
        sta $C005
        sta (ptr3),y
        sta $C004
        lda ptr1
        clc
        adc #FINE_COUNT
        sta ptr1
        bcc :+
        inc ptr1+1
:       inc tmp2
        dec tmp1
        bne @odd_row
@done:  plp
        inc _fine_x
        inc _fine_x
        rts
; The seven rows of glyph A, from AUX, into glyph (for the title logo).
_glyph_fetch:
        sec
        sbc #FINE_FIRST
        clc
        adc #<fine_font
        sta ptr1
        lda #>fine_font
        adc #0
        sta ptr1+1
        php
        sei
        ldx #0
@row:   ldy #0
        jsr aux_read
        sta _glyph,x
        lda ptr1
        clc
        adc #FINE_COUNT
        sta ptr1
        bcc :+
        inc ptr1+1
:       inx
        cpx #FINE_HEIGHT
        bne @row
        plp
        rts

; Zero-terminated string from A/X at fine_x/fine_y. The byte left of the
; string turns mono black too: in mixed mode a colour cell ending there would
; otherwise take its colour from the first glyph's dots.
_fine_text:
        sta ptr2
        stx ptr2+1
        lda _fine_x
        beq @next
        dec _fine_x
        lda #' '
        jsr _fine_char
        dec _fine_x
@next:  lda (ptr2)
        beq @done
        jsr _fine_char
        inc ptr2
        bne @next
        inc ptr2+1
        bra @next
@done:  rts
