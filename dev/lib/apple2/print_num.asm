; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; print_num.asm -- decimal byte output for Apple II (COUT)
; ============================================================================
;   print_byte_dec -- A = unsigned byte (0..255). Prints exactly three ASCII
;                     decimal digits through COUT ($FDED). Leading zeros are
;                     emitted ("042", not " 42") so columns stay aligned.
;                     Clobbers A, X, Y.
;
; No ZP usage — intermediate digits live on the 6502 stack. The conversion is
; lib/math dec.asm (byte_to_dec), included at the end of this file (needs
; -I lib/math, in A2_INCS).
;
; Caller responsibility: COUT in scope (.include "apple2.inc").
; Assembled only if referenced before the include (.ifref).
; ============================================================================

.ifndef _PRINT_NUM_ASM_LOADED_
_PRINT_NUM_ASM_LOADED_ = 1

.segment "CODE"

.ifref print_byte_dec
print_byte_dec:
        JSR     byte_to_dec     ; X = hundreds, Y = tens, A = units
        PHA
        TYA
        PHA
        TXA
        JSR     @digit
        PLA
        JSR     @digit
        PLA
@digit: ORA     #'0' | $80
        JMP     COUT
.endif

.include "dec.asm"

.endif  ; _PRINT_NUM_ASM_LOADED_
