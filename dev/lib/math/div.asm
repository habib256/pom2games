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
; Compared with the former full-width 16-step path: one code byte less,
; 92 cycles less for 16-bit quotients, two cycles more for 8-bit quotients
; (excluding branch page crossings). No extra RAM or stack.
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
@high:   ASL     mul_x+1
        ROL     A
        CMP     mul_y
        BCC     @next_high
        SBC     mul_y
        INC     mul_x+1
@next_high:   DEX
        BNE     @high
        BEQ     @low                    ; X=0: always, one byte less than JMP
.endif

.endif  ; _DIV_ASM_LOADED_
