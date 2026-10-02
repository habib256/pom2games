; ----------------------------------------------------------------------------
; apple2game_asm.s — speaker + joystick for cc65 (see apple2game.h).
;
; Thin wrappers over ../apple2/sound.asm and ../apple2/joy.asm, so asm and C
; programs share one implementation. A separate object from apple2io_asm.s:
; only programs that call these pay for them. Assemble with
; -I dev/lib/apple2.
; ----------------------------------------------------------------------------
        .export _a2_tone, _a2_read_stick, _a2_button
        .export _a2_joy_x, _a2_joy_y
        .import popa

.include "apple2.inc"
.include "sound.asm"
.include "joy.asm"

_a2_joy_x = joy_x
_a2_joy_y = joy_y

        .segment "CODE"

; void a2_tone(unsigned char flips, unsigned char period): period in A,
; flips on the C stack.
_a2_tone:
        pha
        jsr     popa            ; A = flips
        tay
        pla
        tax                     ; X = period
        tya
        jmp     tone

; unsigned char a2_read_stick(void): sample, return A2_JOY_* direction.
_a2_read_stick:
        jsr     read_stick
        jsr     stick_dir
        ldx     #0
        rts

; unsigned char a2_button(unsigned char n): $80 while button n (0-2) is down.
_a2_button:
        tax
        lda     BUTN0,x
        and     #$80
        ldx     #0
        rts
