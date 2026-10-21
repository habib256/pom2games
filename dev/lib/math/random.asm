; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; random.asm -- 16-bit Galois LFSR (taps $B400), deterministic
; ============================================================================
;   rand8       next state of prng_lo/prng_hi; A = prng_lo. Keeps X, Y.
;               ~20 cycles.
;
; Period 65535 over every non-zero state: seed prng_lo/prng_hi with anything
; but 0/0 (which stays 0). The same generator as the PHYSICS demo (seed
; $AD3C) and LOGO's roll_lfsr: a fixed seed replays the same run, which
; the tests rely on.
; State: prng_lo / prng_hi from zp.inc (include zp.inc first).
; ============================================================================

.ifndef _RANDOM_ASM_LOADED_
_RANDOM_ASM_LOADED_ = 1

.segment "CODE"

.ifref rand8
rand8:
        LSR     prng_hi
        ROR     prng_lo
        BCC     @out
        LDA     prng_hi
        EOR     #$B4
        STA     prng_hi
@out:   LDA     prng_lo
        RTS
.endif

.endif  ; _RANDOM_ASM_LOADED_
