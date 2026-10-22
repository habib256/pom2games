; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2io_str.s — a2_puts and a2_print_hexword (see apple2io.h).
;
; A separate object from apple2io_asm.s: only programs that print strings or
; words pay for it (formerly apple2io.c, 72 bytes of cc65 code).
; ----------------------------------------------------------------------------
        .export _a2_puts, _a2_print_hexword
        .importzp ptr1

.include "../apple2/apple2.inc"

        .segment "CODE"

; void a2_puts(const unsigned char *s): A/X = s, NUL-terminated, normal video.
; Nothing is kept in registers across COUT (an output hook may clobber them);
; ptr1 is cc65's, which the Monitor, DOS and firmware leave alone.
_a2_puts:
        sta     ptr1
        stx     ptr1+1
@next:  ldy     #0
        lda     (ptr1),y
        beq     @done
        ora     #$80
        jsr     COUT
        inc     ptr1
        bne     @next
        inc     ptr1+1
        bne     @next
@done:  rts

; void a2_print_hexword(unsigned w): A = low byte, X = high, high first.
_a2_print_hexword:
        pha
        txa
        jsr     PRBYTE
        pla
        jmp     PRBYTE
