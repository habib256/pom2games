; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; div.asm -- unsigned division 16 / 8
; ============================================================================
;   div16by8    mul_x = mul_x / A, A = remainder, mul_y = the divisor.
;               Clobbers X. A quotient below 256 (mul_x+1 < A, the usual
;               case for normalising a vector) takes 8 steps, ~190 cycles;
;               otherwise 16 steps, ~400 cycles. A = 0: quotient $FFFF.
;
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
        ; X counts the bits; zero the quotient high byte only on exit.
        ; Compared with a ZP counter: -1 code byte, -24 cycles per short call
        ; (excluding branch page-crossing differences).
        LDX     #8                      ; quotient < 256: start from the high byte
@l8:    ASL     mul_x
        ROL     A
        BCS     @s8                     ; 9-bit remainder: always >= divisor
        CMP     mul_y
        BCC     @n8
@s8:    SBC     mul_y
        INC     mul_x
@n8:    DEX
        BNE     @l8
        STX     mul_x+1                 ; quotient high byte = 0
        RTS
@q16:   LDA     #0
        LDX     #16
@l16:   ASL     mul_x
        ROL     mul_x+1
        ROL     A
        BCS     @s16
        CMP     mul_y
        BCC     @n16
@s16:   SBC     mul_y
        INC     mul_x
@n16:   DEX
        BNE     @l16
        RTS
.endif

.endif  ; _DIV_ASM_LOADED_
