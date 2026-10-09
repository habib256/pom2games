; VERHILLE Arnaud — GPL-3.0. ProDOS .SYSTEM, NMOS 6502.
; Move loader away from $2000, load DEMO.BIN at its linked address $6000.
.import __LOADER_LOAD__, __LOADER_SIZE__
.segment "CODE"
    cld
    ldx #0
copy:
    lda __LOADER_LOAD__,x
    sta $0800,x
    inx
    cpx #<__LOADER_SIZE__
    bne copy
    jmp start
.segment "LOADER"
start:
    lda $BF30
    sta online_unit
    jsr $BF00
    .byte $C5
    .word online
    bcs error
    lda volume
    and #$0F
    beq error
    tax
    clc
    adc #10                 ; slash + volume + /DEMO.BIN
    sta pathname
    lda #'/'
    sta pathname+1
    ldy #0
names:
    lda volume+1,y
    sta pathname+2,y
    iny
    dex
    bne names
    ldx #0
suffix:
    lda filename,x
    sta pathname+2,y
    iny
    inx
    cpx #9
    bne suffix
    jsr $BF00
    .byte $C8
    .word open
    bcs error
    lda reference
    sta read_reference
    sta close_reference
    jsr $BF00
    .byte $CA
    .word read
    php
    jsr $BF00
    .byte $CC
    .word close
    plp
    bcs error
    jmp $6000
error:
    ldx #0
print:
    lda message,x
    beq halt
    ora #$80
    jsr $FDED
    inx
    bne print
halt: jmp halt
online: .byte 2
online_unit: .byte 0
    .word volume
open: .byte 3
    .word pathname,$1000
reference: .byte 0
read: .byte 4
read_reference: .byte 0
    .word $6000,$5E00,0
close: .byte 1
close_reference: .byte 0
filename: .byte "/DEMO.BIN"
message: .byte "DEMO.BIN LOAD ERROR",0
volume: .res 16
pathname: .res 26
.assert *-start <= $FF, error, "Loader must fit in one page"
