; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; div.asm -- unsigned division 16 / 8
; ============================================================================
;   div16by8    mul_x = mul_x / A, A = remainder, mul_y = the divisor.
;               Clobbers X. A quotient below 256 (mul_x+1 < A, the usual
;               case for normalising a vector) takes 8 steps, ~190 cycles;
;               otherwise two 8-step stages. A = 0: quotient $FFFF, remainder
;               = original low byte. Y is preserved.
;
; The high-byte stage carries each quotient bit into the next shift,
; replacing per-bit increments with one final rotation. The 51-byte kernel
; saves 0..35 long-path cycles before branch page crossings, with unchanged
; short paths, RAM, stack and Y preservation.
; Shift and subtract, no table. The PHYSICS demo used a 512-byte reciprocal
; table and a correction multiply; for an 8-bit quotient the eight steps
; here cost about the same, without the table.
; Include after the callers (.ifref); needs math.inc (mul_x, mul_y).
; ============================================================================

.ifndef _DIV_ASM_LOADED_
_DIV_ASM_LOADED_ = 1

.segment "CODE"

.ifref div16by8
div16by8:
        STA     mul_y
        LDA     mul_x+1
        CMP     mul_y
        BCS     @q16
        ; Short path: A is already the remainder of the high byte.
        LDX     #0
        STX     mul_x+1
@low:
        LDX     #8                      ; A = high-byte remainder
@l8:    ASL     mul_x
        ROL     A
        BCS     @s8                     ; 9-bit remainder: always >= divisor
        CMP     mul_y
        BCC     @n8
@s8:    SBC     mul_y
        INC     mul_x
@n8:    DEX
        BNE     @l8
        RTS
@q16:   LDA     #0
        LDX     #8
        ; Divide the high byte alone, then reuse the low-byte loop.
        ; Prefixes of an 8-bit input never exceed 255, so this first
        ; stage cannot produce a ninth remainder bit, even for divisor 0.
        ; The entry CMP left C=1: seed a discarded leading one. Each
        ; CMP/SBC leaves the next quotient bit in carry for the next ROL.
@high:   ROL     mul_x+1
        ROL     A
        CMP     mul_y
        BCC     @next_high
        SBC     mul_y
@next_high:   DEX
        BNE     @high
        ROL     mul_x+1                 ; append the last bit, discard the leading one
        BCS     @low                    ; discarded leading one left C=1: always
.endif

.endif  ; _DIV_ASM_LOADED_
