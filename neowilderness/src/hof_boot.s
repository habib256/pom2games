; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; NEOHOF.SYSTEM -- ProDOS 8 loader of the hall of fame bench (lot 7).
; ProDOS runs it at $2000. It moves itself to $0800 (the bench uses
; $2000), sets the prefix to the boot volume, then loads HOFTEST and SCENE
; at their auxiliary-type addresses and jumps to HOFTEST. Same pattern as
; chromabreak/src/boot.s. A ][ or ][+ gets a message and returns to ProDOS.
.setcpu "6502"
.macpack longbranch
.import __LOADER_LOAD__, __LOADER_SIZE__
MLI = $BF00
.segment "CODE"
        cld
        lda     $FBB3           ; $06: Apple //e or //c ROM
        cmp     #$06
        bne     old
        ldx     #0
copy:   lda     __LOADER_LOAD__,x
        sta     $0800,x
        lda     __LOADER_LOAD__+$100,x
        sta     $0900,x
        inx
        bne     copy
        jmp     start
old:    ldx     #0
:       lda     old_text,x
        beq     :+
        ora     #$80
        jsr     $FDED
        inx
        bne     :-
:       bit     $C000
        bpl     :-
        bit     $C010
        jsr     MLI
        .byte   $65             ; QUIT
        .word   quit_params
quit_params: .byte 4, 0, 0, 0, 0, 0, 0
old_text: .byte "NEOHOF NEEDS AN APPLE //E OR //C, 128K.", $0D
        .byte "PRESS A KEY TO RETURN TO PRODOS.", 0

.segment "LOADER"
start:  lda     $BF30           ; boot unit
        sta     online_unit
        jsr     MLI
        .byte   $C5             ; ON_LINE: name of the boot volume
        .word   online
        jcs     error
        lda     volume
        and     #$0F
        jeq     error
        tax
        inx                     ; leading slash
        stx     prefix
        lda     #'/'
        sta     volume          ; "/NAME" in place of the length byte
        jsr     MLI
        .byte   $C6             ; SET_PREFIX
        .word   set_prefix
        jcs     error
        lda     #<name_bench
        ldx     #>name_bench
        jsr     load
        lda     info_aux
        sta     entry+1
        lda     info_aux+1
        sta     entry+2
        lda     #<name_scene
        ldx     #>name_scene
        jsr     load
entry:  jmp     $FFFF

; A/X = pathname: GET_FILE_INFO, then READ the whole file at its aux type.
load:   sta     info_path
        stx     info_path+1
        sta     open_path
        stx     open_path+1
        jsr     MLI
        .byte   $C4             ; GET_FILE_INFO
        .word   info
        jcs     error
        jsr     MLI
        .byte   $C8             ; OPEN, buffer $1000
        .word   open
        jcs     error
        lda     open_ref
        sta     read_ref
        sta     close_ref
        lda     info_aux
        sta     read_addr
        lda     info_aux+1
        sta     read_addr+1
        sec                     ; request = $BF00 - address
        lda     #0
        sbc     info_aux
        sta     read_count
        lda     #$BF
        sbc     info_aux+1
        sta     read_count+1
        jsr     MLI
        .byte   $CA             ; READ
        .word   read
        php
        jsr     MLI
        .byte   $CC             ; CLOSE
        .word   close
        plp
        jcs     error
        rts
error:  ldx     #0
:       lda     message,x
        beq     halt
        ora     #$80
        jsr     $FDED
        inx
        bne     :-
halt:   jmp     halt

online: .byte   2
online_unit: .byte 0
        .word   volume
set_prefix: .byte 1
        .word   prefix
info:   .byte   10
info_path: .word 0
        .byte   0, 0
info_aux: .word 0
        .res    11
open:   .byte   3
open_path: .word 0
        .word   $1000
open_ref: .byte 0
read:   .byte   4
read_ref: .byte 0
read_addr: .word 0
read_count: .word 0
        .word   0
close:  .byte   1
close_ref: .byte 0
name_bench: .byte 7, "HOFTEST"
name_scene: .byte 5, "SCENE"
message: .byte  "NEOHOF: CANNOT LOAD HOFTEST/SCENE", 0
prefix: .byte   0               ; length, then "/" + volume name
volume: .res    16
.assert * - start <= $200, error, "loader must fit in two pages"
