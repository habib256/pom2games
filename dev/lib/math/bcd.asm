; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; bcd.asm -- packed BCD scores: saturating add, digits out
; ============================================================================
; A score kept in packed BCD (two digits a byte, low byte first) needs no
; binary-to-decimal conversion to be shown, and its addition is ADC in
; decimal mode.
;
;   bcd_add_sat -- (bcd_ptr) += the number at A (lo) / Y (hi), X bytes each
;                  (1..255, low byte first). On overflow every byte becomes
;                  $99 (99..99): C = 1 then, else C = 0. Clobbers A, X, Y.
;                  D is set during the add (~15 cycles a byte): an IRQ
;                  handler that does arithmetic must CLD itself, or wrap the
;                  call in SEI / CLI. 32 B.
;   bcd_put     -- the X-byte number at A (lo) / Y (hi) as 2 * X ASCII
;                  digits, most significant first, each sent in A to the
;                  program's routine BCD_PUT_OUT (which must keep X; e.g.
;                  hgr_putc8, COUT). Clobbers A, X, Y. 33 B.
;                  BCD_PUT_LEAD = c: leading zeros become char c (e.g. ' '),
;                  or are left out with c = 0; the units digit always
;                  shows (+1 B BSS bcd_seen, +27 B).
;
; Zero page: bcd_ptr (2) if bcd_add_sat is used, skipped if defined before
; the include. Operands are reached through patched absolute addresses.
; .ifref: include after the callers. From DIRTBIKE (tricks.inc
; trick_bank / tr_add10, hof.inc put_points / put_bcd).
; ============================================================================

.ifref bcd_add_sat
.ifndef _BCD_ADD_SAT_LOADED_
_BCD_ADD_SAT_LOADED_ = 1
.ifndef bcd_ptr
.zeropage
bcd_ptr:        .res 2
.endif
.segment "CODE"
bcd_add_sat:
        STA     @src+1
        STY     @src+2
        LDY     #0
        SED
        CLC
@lp:    LDA     (bcd_ptr),Y
@src:   ADC     $FFFF,Y         ; patched: the addend
        STA     (bcd_ptr),Y
        INY
        DEX
        BNE     @lp
        CLD
        BCC     @rts
        LDA     #$99            ; overflow: 99..99, C stays 1
@sat:   DEY
        STA     (bcd_ptr),Y
        BNE     @sat
@rts:   RTS
.endif
.endif

.ifref bcd_put
.ifndef _BCD_PUT_LOADED_
_BCD_PUT_LOADED_ = 1
.ifdef BCD_PUT_LEAD
.segment "BSS"
bcd_seen:       .res 1          ; 0 while only zeros were met
.endif
.segment "CODE"
bcd_put:
        STA     @num+1
        STY     @num+2
.ifdef BCD_PUT_LEAD
        LDA     #0
        STA     bcd_seen
.endif
@byte:  DEX
@num:   LDA     $FFFF,X         ; patched: the number, top byte first
        PHA
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        JSR     @digit
        PLA
        AND     #$0F
.ifdef BCD_PUT_LEAD
        CPX     #0
        BNE     @low
        INC     bcd_seen        ; the units digit always shows
@low:
.endif
        JSR     @digit
        TXA
        BNE     @byte
        RTS
@digit:
.ifdef BCD_PUT_LEAD
        TAY
        ORA     bcd_seen
        BEQ     @lead
        STA     bcd_seen        ; non-zero from now on
        TYA
.endif
        ORA     #'0'
        JMP     BCD_PUT_OUT
.ifdef BCD_PUT_LEAD
@lead:
.if BCD_PUT_LEAD
        LDA     #BCD_PUT_LEAD
        JMP     BCD_PUT_OUT
.else
        RTS
.endif
.endif
.endif
.endif
