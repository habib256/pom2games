; ============================================================================
; print_num.asm -- decimal byte output for Apple II (COUT)
; ============================================================================
;   print_byte_dec -- A = unsigned byte (0..255). Prints exactly three ASCII
;                     decimal digits through COUT ($FDED). Leading zeros are
;                     emitted ("042", not " 42") so columns stay aligned.
;                     Clobbers A, X. Y preserved (COUT preserves Y).
;
; Same API as dev/lib/apple1/print_num.asm. No ZP usage — intermediate digits
; live on the 6502 stack.
;
; Caller responsibility: COUT in scope (.include "apple2.inc").
; ============================================================================

.segment "CODE"

print_byte_dec:
        ; Hundreds digit -- subtract 100 until carry clear, X counts how many.
        LDX     #$00
@h:     CMP     #100
        BCC     @hd
        SBC     #100            ; C set by the CMP, no SEC needed
        INX
        JMP     @h
@hd:    PHA
        TXA
        ORA     #'0' | $80
        JSR     COUT
        PLA

        ; Tens digit -- same pattern.
        LDX     #$00
@t:     CMP     #10
        BCC     @td
        SBC     #10
        INX
        JMP     @t
@td:    PHA
        TXA
        ORA     #'0' | $80
        JSR     COUT
        PLA

        ; Units digit -- whatever's left in A.
        ORA     #'0' | $80
        JMP     COUT
