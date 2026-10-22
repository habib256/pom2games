; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2io_asm.s — Apple II Monitor + keyboard hooks for cc65 (see apple2io.h).
;
; a2_puts and a2_print_hexword are a separate object, apple2io_str.s.
;
; cc65 calling convention: an `unsigned char` argument arrives in A, a char
; return value leaves in A (X cleared so an int promotion reads it right).
; ----------------------------------------------------------------------------
        .export _a2_putc, _a2_print_hex, _a2_home, _a2_text, _a2_dos, _a2_wait
        .export _apple2_iskeypressed, _apple2_getkey, _apple2_readkey
        .import _exit

; Equates from lib/apple2 (found next to this file: no -I needed). The key
; routines stay here rather than wrapping kbd.asm's wait_key/poll_key: the
; wrappers (X = 0 for cc65) would cost 18 bytes more than this shared tail.
.include "../apple2/apple2.inc"

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

_a2_wait:
        jmp     WAIT            ; A = delay code (clobbers A)

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
