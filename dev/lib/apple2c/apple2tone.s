; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2tone.s — the speaker alone for cc65: a2_tone() (see apple2game.h).
;
; For a program that beeps but reads no joystick: the same a2_tone as
; apple2game_asm.s without read_stick / stick_dir / a2_button (24 bytes
; instead of 131). Link one or the other (APPLE2C_TONE_SRCS or
; APPLE2C_GAME_SRCS), never both. Assemble with -I dev/lib/apple2.
; ----------------------------------------------------------------------------
        .export _a2_tone
        .import popa

.include "apple2.inc"
.include "sound.asm"

        .segment "CODE"

; void a2_tone(unsigned char flips, unsigned char period): period in A,
; flips on the C stack.
_a2_tone:
        tax                     ; X = period
        jsr     popa            ; A = flips (popa keeps X)
        jmp     tone
