; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2rand.s — a2_rand16() for cc65 (see apple2rand.h).
;
; The same 16-bit Galois LFSR transition as ../math/random.asm's rand8
; (taps $B400), with the high byte kept in A until feedback is applied.
; Return the new state directly in A/X, preserving Y. No nested call.
; State a2_rand_state (absolute, not zero page), $ACE1 at load. A separate
; object (APPLE2C_RAND_SRCS): 19 bytes of code and 2 of DATA.
; ----------------------------------------------------------------------------
        .export _a2_rand16, _a2_rand_state

        .segment "DATA"
_a2_rand_state:
prng_lo:        .byte $E1
prng_hi:        .byte $AC

        .segment "CODE"
; unsigned int a2_rand16(void): one LFSR step; A/X = the new state.
_a2_rand16:
        lda     prng_hi
        lsr     a
        ror     prng_lo
        bcc     ready
        eor     #$B4
ready:  sta     prng_hi
        tax
        lda     prng_lo
        rts
