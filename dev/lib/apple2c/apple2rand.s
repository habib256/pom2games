; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2rand.s — a2_rand16() for cc65 (see apple2rand.h).
;
; A thin wrapper over ../math/random.asm's rand8, the 16-bit Galois LFSR
; (taps $B400) the asm programs use: one step, the new state returned.
; State a2_rand_state (absolute, not zero page), $ACE1 at load. A separate
; object (APPLE2C_RAND_SRCS): 7 bytes of code + rand8's 20 + 2 of DATA.
; Assemble with -I dev/lib/apple2 (the math directory is its sibling).
; ----------------------------------------------------------------------------
        .export _a2_rand16, _a2_rand_state

        .segment "DATA"
_a2_rand_state:
prng_lo:        .byte $E1
prng_hi:        .byte $AC

        .segment "CODE"
; unsigned int a2_rand16(void): one LFSR step; A/X = the new state.
_a2_rand16:
        jsr     rand8           ; A = prng_lo, X/Y kept
        ldx     prng_hi
        rts

; random.asm emits rand8 only when referenced before inclusion.
.include "../math/random.asm"
