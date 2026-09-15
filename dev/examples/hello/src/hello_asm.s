; =============================================================================
; hello_asm.s -- smallest Apple II program on dev/lib/apple2 (asm track)
; =============================================================================
; Exercises every routine of the library: text through COUT, a decimal byte,
; a key, a delay, and the clean return to DOS. Build with `make`, then on the
; disk: BRUN HELLOASM (the HELLO program does it at boot).
; =============================================================================

.include "apple2.inc"
.include "zp.inc"               ; first ZP allocation: tmp, tmp2, print_ptr_*, ...

.segment "CODE"

main:
        APPLE2_PREAMBLE
        JSR     apple2_zp_save  ; before any ZP write: DOS/BASIC own the page
        LDA     TXTSET
        JSR     HOME
        LDA     #<msg_hello
        LDX     #>msg_hello
        JSR     print_str_ax
        LDA     #42
        JSR     print_byte_dec
        JSR     CROUT
        LDA     #<msg_key
        LDX     #>msg_key
        JSR     print_str_ax
        JSR     wait_key        ; A = key & $7F, upper-cased
        ORA     #$80
        JSR     COUT
        JSR     CROUT
        LDA     #250            ; a quarter of a second
        JSR     delay_ms_a
        JMP     apple2_exit     ; ZP back, text screen, ']' prompt

msg_hello:
        .byte   "HELLO FROM THE APPLE II (ASM)", $0D
        .byte   "PRINT_BYTE_DEC(42) = ", 0
msg_key:
        .byte   "PRESS A KEY: ", 0

.include "print.asm"
.include "print_num.asm"
.include "kbd.asm"
.include "delay.asm"
.include "exit.asm"
