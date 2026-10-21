; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; sqrt.asm -- integer square root from a seed table and the square tables
; ============================================================================
;   sqrt_init   build sqrt_seed (after mul_init). ~60 000 cycles.
;   isqrt16     A = floor(sqrt(mul_x)), mul_x unsigned 16 bits. Keeps mul_x.
;               Clobbers X, Y. ~40 cycles + ~25 per step: one step for
;               most numbers, up to 15 below 256.
;
; sqrt_seed[h] = floor(sqrt(h * 256)) never overshoots any number whose high
; byte is h; isqrt16 then steps up while (r+1)^2 <= mul_x. A square needs no
; multiply: n^2 = sqr1[2n] (mul.asm's quarter squares). From the PHYSICS
; demo's isqrt16, its seed table built at start instead of loaded.
;
; SQRT_SEED = address (256 bytes) before the include places the table;
; otherwise it is reserved in BSS. Include this file BEFORE mul.asm.
; ============================================================================

.ifndef _SQRT_ASM_LOADED_
_SQRT_ASM_LOADED_ = 1

.ifdef SQRT_SEED
sqrt_seed = SQRT_SEED
.else
.segment "BSS"
sqrt_seed: .res 256
.endif

.segment "CODE"

.ifref sqrt_init
sqrt_init:
        LDA     #0
        STA     mul_x
        STA     mul_x+1
        TAY                             ; r, carried from one h to the next
@h:     JSR     isqrt_from_y
        LDX     mul_x+1
        STA     sqrt_seed,X
        TAY
        INC     mul_x+1
        BNE     @h
        RTS
.endif

.ifref isqrt16
isqrt16:
        LDX     mul_x+1
        LDY     sqrt_seed,X
.endif
.if .referenced(isqrt16) .or .referenced(isqrt_from_y)
isqrt_from_y:                           ; Y = r <= floor(sqrt(mul_x))
@step:  CPY     #255
        BEQ     @done
        INY                             ; c = r + 1: c^2 <= mul_x ?
        TYA
        ASL     A
        TAX
        BCS     @hi
        LDA     mul_x
        CMP     mul_sqr1_lo,X
        LDA     mul_x+1
        SBC     mul_sqr1_hi,X
        BCS     @step
        DEY
@done:  TYA
        RTS
@hi:    LDA     mul_x
        CMP     mul_sqr1_lo+256,X
        LDA     mul_x+1
        SBC     mul_sqr1_hi+256,X
        BCS     @step
        DEY
        TYA
        RTS
.endif

.endif  ; _SQRT_ASM_LOADED_
