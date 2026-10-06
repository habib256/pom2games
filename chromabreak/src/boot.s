; ProDOS boots .SYSTEM files. This small shim loads the game CHROMA.SYS.
; Relocate to $0800 before READ overwrites the entry at $2000.
; The game is 65C02 code: first, with 6502 instructions only, an original
; //e (NMOS 6502) gets a message and returns to ProDOS instead of crashing.
.setcpu "6502"
.import __LOADER_LOAD__, __LOADER_SIZE__
.segment "CODE"
        cld
        lda #0
        .byte $1A                ; 65C02: INC A. NMOS 6502: one-byte NOP.
        beq nmos
        ldx #0
copy:   lda __LOADER_LOAD__,x
        sta $0800,x
        inx
        cpx #<__LOADER_SIZE__
        bne copy
        jmp start
nmos:
        jsr $FC58                ; HOME
        ldx #0
nmos_print:
        lda nmos_text,x
        beq nmos_wait
        ora #$80
        jsr $FDED
        inx
        bne nmos_print
nmos_wait:
        bit $C000
        bpl nmos_wait
        bit $C010
        jsr $BF00
        .byte $65                ; QUIT back to ProDOS
        .word quit
quit:   .byte 4, 0, 0, 0, 0, 0, 0
nmos_text:
        .byte "CHROMABREAK NEEDS A 65C02 CPU:", $0D
        .byte "APPLE //E ENHANCED OR //C, 128K.", $0D, $0D
        .byte "PRESS A KEY TO RETURN TO PRODOS.", 0
.segment "LOADER"
.setcpu "65C02"
start:  lda $BF30                 ; boot device, including drive number
        sta online_unit
        jsr $BF00
        .byte $C5                ; ONLINE: resolve the boot volume's name
        .word online
        bcs error
        lda volume
        and #$0F
        beq error
        tax
        clc
        adc #12                  ; slash + name + /CHROMA.SYS
        sta pathname
        lda #'/'
        sta pathname+1
        ldy #0
names:  lda volume+1,y
        sta pathname+2,y
        iny
        dex
        bne names
        ldx #0
suffix: lda filename,x
        sta pathname+2,y
        iny
        inx
        cpx #11
        bne suffix
        jsr $BF00
        .byte $C8                ; OPEN
        .word open
        bcs error
        lda reference
        sta read_reference
        sta close_reference
        jsr $BF00
        .byte $CA                ; READ the complete SYS into $2000
        .word read
        php
        jsr $BF00
        .byte $CC                ; CLOSE even if READ failed
        .word close
        plp
        bcs error
        jmp $2000
error:  ldx #0
print:  lda message,x
        beq halt
        ora #$80
        jsr $FDED
        inx
        bne print
halt:   jmp halt
online: .byte 2
online_unit: .byte 0
        .word volume
open:   .byte 3
        .word pathname, $1000
reference: .byte 0
read:   .byte 4
read_reference: .byte 0
        .word $2000, $9F00, 0
close:  .byte 1
close_reference: .byte 0
filename: .byte "/CHROMA.SYS"
message: .byte "CHROMA.SYS ERROR", 0
volume: .res 16
pathname: .res 28
.assert *-start <= $FF, error, "Boot loader must fit in one page"
