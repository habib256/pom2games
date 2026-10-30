; Robot Space Station — the mouse pointer on DHGR page 1 (ui.c). It covers
; 4 byte columns x ptr_h rows from column ptr_bx, row ptr_y: pointer_draw
; saves them in ptr_under and ORs in the arrow (ptr_bits, 4 bytes a row);
; pointer_restore writes ptr_under back. Even columns are in aux memory.
; Read through aux_read in zero page (dev/lib/hgrc dhgr_asm.s), IRQs off
; while a bank is switched; 80STORE stays off.
.setcpu "65C02"
.importzp ptr1, ptr2, aux_read
.import dhgr_rowlo, dhgr_rowhi, _dhgr_base
.export _pointer_draw, _pointer_restore
.export _ptr_bx, _ptr_y, _ptr_h, _ptr_bits, _ptr_under

RAMWRTOFF = $C004
RAMWRTON  = $C005

.segment "BSS"
_ptr_bx:    .res 1
_ptr_y:     .res 1
_ptr_h:     .res 1
_ptr_bits:  .res 2
_ptr_under: .res 24
drawing:    .res 1
half:       .res 1              ; ptr_bx / 2: the row's first byte offset
row:        .res 1
k:          .res 1
idx:        .res 1              ; row * 4 + k
col:        .res 1
off:        .res 1
odd:        .res 1
byte:       .res 1

.segment "CODE"
_pointer_draw:
        lda #1
        bra go
_pointer_restore:
        lda #0
go:     sta drawing
        php
        sei
        lda _ptr_bits
        sta ptr2
        lda _ptr_bits+1
        sta ptr2+1
        lda _ptr_bx
        lsr a
        sta half
        stz row
        stz idx
@row:   lda row
        cmp _ptr_h
        bcc @line
        plp
        rts
@line:  clc
        adc _ptr_y
        tax
        lda half
        clc
        adc dhgr_rowlo,x
        sta ptr1
        lda dhgr_rowhi,x
        adc #0
        ora _dhgr_base
        sta ptr1+1
        stz k
@byte:  lda _ptr_bx
        clc
        adc k
        sta col
        cmp #80
        bcs @next                   ; past the right edge
        lsr a
        sec
        sbc half
        sta off
        lda col
        and #1
        sta odd
        ldx idx
        lda drawing
        beq @restore
        ldy off
        lda odd
        bne @read_main
        jsr aux_read
        bra @got
@read_main:
        lda (ptr1),y
@got:   and #$7F
        sta _ptr_under,x
        sta byte
        txa
        tay
        lda (ptr2),y
        ora byte
        bra @write
@restore:
        lda _ptr_under,x
@write: ldy off
        ldx odd
        bne @write_main
        sta RAMWRTON
@write_main:
        sta (ptr1),y
        sta RAMWRTOFF
@next:  inc idx
        inc k
        lda k
        cmp #4
        bne @byte
        inc row
        jmp @row
