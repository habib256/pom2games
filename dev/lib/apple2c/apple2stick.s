; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2stick.s — a2_stick_present() for cc65 (see apple2game.h).
;
; A separate object (APPLE2C_STICK_SRCS), with apple2game_asm.s whose
; a2_read_stick it calls: 17 bytes for the programs that detect a stick.
; Assemble with -I dev/lib/apple2.
; ----------------------------------------------------------------------------
        .export _a2_stick_present
        .import _a2_read_stick

.include "apple2.inc"

        .segment "CODE"
; unsigned char a2_stick_present(void): 1 if both paddle timers ran out
; during a read (~6 ms): a two-axis stick answers. 0 if either still runs.
_a2_stick_present:
        jsr     _a2_read_stick
        lda     PADDL0
        ora     PADDL1          ; bit 7: a timer still charging
        eor     #$80
        asl     a               ; C = 1: both ran out
        lda     #0
        tax
        rol     a
        rts
