; Fixed 6x6 color sprites and decimal HUD for the DHGR starter.
; All reads of auxiliary RAM use the library's zero-page trampoline.
; Entry/exit: main RAMRD/RAMWRT, 80STORE off. Preserve IRQ state.
.include "apple2.inc"
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, aux_read
.import _dhgr_base, _ball_x, _ball_y, _old_x, _old_y, _frame_text
.export _ball_restore, _ball_draw, _counter_digit
RAMWRTON = $C005

.segment "BSS"
under: .res 180                 ; 2 pages * 3 balls * 30 bytes
slot: .res 1
bx: .res 1
row: .res 1
rows: .res 1
width: .res 1

.segment "RODATA"
row_lo:
.repeat 192, I
    .byte <((I & 7)*1024 + ((I >> 3) & 7)*128 + (I >> 6)*40)
.endrepeat
row_hi:
.repeat 192, I
    .byte >((I & 7)*1024 + ((I >> 3) & 7)*128 + (I >> 6)*40)
.endrepeat
x_byte:
.repeat 140, I
    .byte I*4/7
.endrepeat
x_bank:
.repeat 140, I
    .byte ((I*4) .mod 7)*30
.endrepeat
under_offset: .byte 0,30,60,90,120,150
digit_lo: .byte <0,<32,<64,<96,<128,<160,<192,<224,<256,<288
digit_hi: .byte >0,>32,>64,>96,>128,>160,>192,>224,>256,>288
digits:
.include "digits.inc"
ball_data:
.incbin "ball.bin", 0, 210
ball_mask:
.incbin "ball.bin", 210, 210

.segment "CODE"
; A = ball id. X = page-specific slot. ptr4 = its save-under buffer.
ball_setup:
    tax
    bit _dhgr_base
    bvc @page1                  ; base $40 = page 2
    clc
    adc #3
    tax
@page1:
    stx slot
    lda under_offset,x
    clc
    adc #<under
    sta ptr4
    lda #>under
    adc #0
    sta ptr4+1
    lda #5
    sta width
    lda #6
    sta rows
    rts

; Select a scanline using tables, avoiding division and C per-row calls.
scanline:
    ldx row
    lda bx
    lsr
    clc
    adc row_lo,x
    sta ptr1
    lda row_hi,x
    adc _dhgr_base
    sta ptr1+1
    lda bx
    and #1
    eor #1
    tax
    lda width
    sta tmp2
    ldy #0
    rts

next_byte:
    inc ptr2
    bne @source
    inc ptr2+1
@source:
    cpx #0
    bne @address
    inc ptr1
    bne @address
    inc ptr1+1
@address:
    txa
    eor #1
    tax
    dec tmp2
    rts

_ball_restore:
    php
    sei
    jsr ball_setup
    lda ptr4
    sta ptr2
    lda ptr4+1
    sta ptr2+1
    ldx slot
    lda _old_y,x
    sta row
    lda _old_x,x
    tax
    lda x_byte,x
    sta bx
    jmp write_rows

; A = column 0..4. All digit cells start at phase 0 (x = 63 + 7*column).
_counter_digit:
    php
    sei
    tax
    asl
    asl
    clc
    adc #36
    sta bx
    lda _frame_text,x
    sec
    sbc #'0'
    tax
    lda digit_lo,x
    clc
    adc #<digits
    sta ptr2
    lda digit_hi,x
    adc #>digits
    sta ptr2+1
    lda #24
    sta row
    lda #8
    sta rows
    lda #4
    sta width
write_rows:
    jsr scanline
@byte:
    lda (ptr2),y
    cpx #0
    beq @main
    sta RAMWRTON
@main:
    sta (ptr1),y
    sta RAMWRTOFF
    jsr next_byte
    bne @byte
    inc row
    dec rows
    bne write_rows
    plp
    rts

; Save background and draw the masked ball in a single pass.
_ball_draw:
    php
    sei
    pha
    jsr ball_setup
    pla
    tay
    lda _ball_y,y
    sta row
    ldx slot
    sta _old_y,x
    lda _ball_x,y
    sta _old_x,x
    tax
    lda x_byte,x
    sta bx
    lda x_bank,x
    clc
    adc #<ball_data
    sta ptr2
    lda #>ball_data
    adc #0
    sta ptr2+1
    lda x_bank,x
    clc
    adc #<ball_mask
    sta ptr3
    lda #>ball_mask
    adc #0
    sta ptr3+1
@row:
    jsr scanline
@byte:
    cpx #0
    beq @read_main
    jsr aux_read
    jmp @saved
@read_main:
    lda (ptr1),y
@saved:
    and #$7F
    sta (ptr4),y
    and (ptr3),y
    ora (ptr2),y
    cpx #0
    beq @write_main
    sta RAMWRTON
@write_main:
    sta (ptr1),y
    sta RAMWRTOFF
    inc ptr4
    bne @under
    inc ptr4+1
@under:
    inc ptr3
    bne @mask
    inc ptr3+1
@mask:
    jsr next_byte
    bne @byte
    inc row
    dec rows
    bne @row
    plp
    rts
