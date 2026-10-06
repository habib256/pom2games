; VERHILLE Arnaud — GPL-3.0. cc65 ProDOS 8 graphics startup at $6000.
.export __STARTUP__ : absolute = 1
.export _exit, apple2_zp_buf, _prodos_quit
.import __STACKSTART__, zerobss, copydata, initlib, donelib
.import _main, _game_shutdown
.importzp sp
.segment "STARTUP"
        cld
        ldx #0
save:   lda $00,x
        sta zp_save,x
        inx
        bne save
        ldx #2
:       lda $03F2,x
        sta rst_save,x
        dex
        bpl :-
        ldx #23
:       lda $BF58,x
        sta bitmap,x
        dex
        bpl :-
        ; Protect the font at $0800..$0FFF and video/code pages $20..$BE.
        ; A bitmap bit of 1 means unavailable. Low RAM
        ; $1000..$1FFF holds MLI buffers: GET_PREFIX/READ must be allowed to
        ; write there. OPEN temporarily protects its own four buffer pages.
        lda #$FF
        sta $BF59
        ldx #4
:       sta $BF58,x
        inx
        cpx #23
        bne :-
        lda $BF6F
        ora #$FE
        sta $BF6F
        lda #<reset_exit
        sta $03F2
        lda #>reset_exit
        sta $03F3
        eor #$A5
        sta $03F4
        lda #<__STACKSTART__
        sta sp
        lda #>__STACKSTART__
        sta sp+1
        jsr zerobss
        jsr copydata
        jsr initlib
        jsr _main
_exit:  jsr donelib
        jmp cleanup
reset_exit:
        cld
        ldx #$FF
        txs
        lda #<__STACKSTART__
        sta sp
        lda #>__STACKSTART__
        sta sp+1
cleanup:
        sta $C002
        sta $C004
        sta $C000
        sta $C00C
        bit $C05F
        bit $C082
        jsr _game_shutdown
        ldx #23
:       lda bitmap,x
        sta $BF58,x
        dex
        bpl :-
        ldx #2
:       lda rst_save,x
        sta $03F2,x
        dex
        bpl :-
        ldx #0
:       lda zp_save,x
        sta $00,x
        inx
        bne :-
        bit $C051
        bit $C052
        bit $C054
        bit $C056
        bit $C010
_prodos_quit:
        jsr $BF00
        .byte $65
        .word quit_params
        ; QUIT has no caller to return to. If no dispatcher is installed,
        ; ProDOS supplies its standard program launcher.
halt:   jmp halt
.rodata
quit_params: .byte 4,0
        .word 0
        .byte 0
        .word 0
.segment "ZPSAVE"
apple2_zp_buf:
zp_save: .res 256
rst_save: .res 3
bitmap: .res 24
