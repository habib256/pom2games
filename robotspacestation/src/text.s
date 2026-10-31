; Robot Space Station — the text bank (tools/gen_text.py) in auxiliary
; memory from $6000: a table of the texts' aux addresses, then the texts,
; NUL-terminated, lines split by $0A. Read a byte at a time through the
; DHGR library's aux_read (zero page: RAMRD cannot switch out the code).
.setcpu "65C02"
.importzp ptr1, ptr2, aux_read
.export _text_store, _text_open, _text_line, _text_buf, _store_src

TEXT_AUX = $6000
RAMWRTOFF = $C004
RAMWRTON = $C005

.segment "LOWBSS"
_text_buf: .res 32                      ; the line text_line() copied
.segment "BSS"
text_ptr: .res 2
.segment "DATA"
_store_src: .byte $20                   ; text_store's source page

.segment "CODE"
; text_store(pages, aux_page): A pages from main store_src (page, $20 at
; first) to aux (X = page). At boot: $2000-$5FFF are free then.
_text_store:
        stx ptr2+1
        tax
        php
        sei
        stz ptr1
        stz ptr2
        lda _store_src
        sta ptr1+1
        ldy #0
        sta RAMWRTON
@copy:  lda (ptr1),y
        sta (ptr2),y
        iny
        bne @copy
        inc ptr1+1
        inc ptr2+1
        dex
        bne @copy
        sta RAMWRTOFF
        plp
        rts

; text_open(id): the next text_line() reads text id.
_text_open:
        asl
        sta ptr1
        lda #>TEXT_AUX
        adc #0
        sta ptr1+1
        ldy #0
        jsr aux_read
        sta text_ptr
        iny
        jsr aux_read
        sta text_ptr+1
        rts

; text_line(): the next line into text_buf; 1 if another follows, else 0
; (and the text stays at its end).
_text_line:
        lda text_ptr
        sta ptr1
        lda text_ptr+1
        sta ptr1+1
        ldy #0
@char:  jsr aux_read
        beq @last
        cmp #$0A
        beq @next
        sta _text_buf,y
        iny
        cpy #31
        bne @char
@last:  lda #0
        sta _text_buf,y
        tax
        bra @move
@next:  lda #0
        sta _text_buf,y
        iny                             ; past the line break
        lda #1
        ldx #0
@move:  pha
        tya
        clc
        adc ptr1
        sta text_ptr
        lda ptr1+1
        adc #0
        sta text_ptr+1
        pla
        rts
