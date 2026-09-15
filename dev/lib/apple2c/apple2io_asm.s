; ----------------------------------------------------------------------------
; apple2io_asm.s — Apple II Monitor + keyboard hooks for cc65 (see apple2io.h).
;
; Named *_asm.s (not apple2io.s) because cc65 compiles apple2io.c through an
; intermediate apple2io.s, which would clobber a hand-written file.
;
; cc65 calling convention: an `unsigned char` argument arrives in A, a char
; return value leaves in A (X cleared so an int promotion reads it right).
; ----------------------------------------------------------------------------
        .export _a2_putc, _a2_print_hex, _a2_home, _a2_text, _a2_dos
        .export _apple2_iskeypressed, _apple2_getkey, _apple2_readkey
        .import _exit

COUT    = $FDED
PRBYTE  = $FDDA
HOME    = $FC58
KBD     = $C000
KBDSTRB = $C010
TXTSET  = $C051
MIXCLR  = $C052
LOWSCR  = $C054

        .segment "CODE"

_a2_putc:
        ora     #$80            ; normal video
        jmp     COUT

_a2_print_hex:
        jmp     PRBYTE

_a2_home:
        jmp     HOME

_a2_text:
        bit     TXTSET
        bit     MIXCLR
        bit     LOWSCR
        rts

_a2_dos:
        jmp     _exit           ; crt0_apple2.s: restore ZP, text, DOS prompt

_apple2_iskeypressed:
        lda     KBD
        and     #$80
        ldx     #0
        rts

_apple2_getkey:
@wait:  lda     KBD
        bpl     @wait
        bit     KBDSTRB
        jmp     take

_apple2_readkey:
        lda     KBD
        bpl     none
        bit     KBDSTRB
take:   and     #$7F
        cmp     #'a'            ; fold lower case
        bcc     done
        cmp     #'z'+1
        bcs     done
        and     #$DF
done:   ldx     #0
        rts
none:   lda     #0
        tax
        rts
