; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; print.asm -- ASCIIZ string output for Apple II (Monitor COUT at $FDED)
; ============================================================================
; Calling convention:
;   Input    A = low byte, X = high byte of pointer to NUL-terminated string.
;   Output   prints each byte ORed with $80 through COUT, stops at $00.
;            $0D is a carriage return (COUT scrolls the text window).
;            Strings may span pages.
;   Clobbers A, Y. X preserved. print_ptr_hi is modified for long strings.
;
; COUT writes to the TEXT page: switch to text (LDA TXTSET) to see it. It uses
; the Monitor zero page ($20-$4F) — keep your own ZP out of that range.
;
; ZP usage   2 bytes named print_ptr_lo / print_ptr_hi, reserved here unless
;            zp.inc (or an alias) already defined them.
;
; Caller does:  LDA #<msg / LDX #>msg / JSR print_str_ax
; Caller responsibility: COUT in scope (.include "apple2.inc").
; ============================================================================

.ifndef print_ptr_lo
.segment "ZEROPAGE"
print_ptr_lo:   .res 1
print_ptr_hi:   .res 1
.endif

.segment "CODE"

print_str_ax:
        STA     print_ptr_lo
        STX     print_ptr_hi
        LDY     #$00
@lp:    LDA     (print_ptr_lo),Y
        BEQ     @done
        ORA     #$80
        JSR     COUT            ; COUT preserves Y (it saves it in YSAV1)
        INY
        BNE     @lp
        INC     print_ptr_hi    ; Y wrapped -> next page
        BNE     @lp             ; always taken
@done:  RTS
