; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; delay.asm -- approximate millisecond delay for Apple II (1.0205 MHz)
; ============================================================================
; One routine, no ZP usage (X = outer count, Y = inner).
;
;   delay_ms_a -- delay approximately A milliseconds. A = ms count.
;                 Clobbers A, X, Y.
;
; Calibration: the Apple II clock averages 1 020 484 Hz (65 CPU cycles of
; 14.31818 MHz / 14, with the long 65th cycle every scanline):
;   - Inner loop (LDY #202 / DEY / BNE @i): 2 + 5*201 + 4 = 1011 cycles
;   - Outer wrap (DEX / BNE @o): 5 cycles
;   - Per ms: ~1016 cycles -> 0.996 ms, accuracy ~0.4 %.
;
; Edge case: A = 0 -> 256 ms. Interrupts are not masked, so an IRQ card can
; stretch the delay.
; Assembled only if referenced before the include (.ifref).
; ============================================================================

.ifndef _DELAY_ASM_LOADED_
_DELAY_ASM_LOADED_ = 1

.segment "CODE"

.ifref delay_ms_a
delay_ms_a:
        TAX                     ; X = ms count
@o:     LDY     #202            ; inner reload calibrated for ~1 ms @ 1.02 MHz
@i:     DEY
@bi:    BNE     @i
        DEX
@bo:    BNE     @o
        RTS
        ; A taken branch that crosses a page costs one more cycle per turn
        ; (~20 % slower). The crossing is decided by the PC AFTER the branch
        ; (@bi+2 / @bo+2) against its target -- not by the target's own
        ; neighbourhood, which let a loop straddling $xxFF assemble silently.
        ; If this fires, move the include (or pad a few bytes before it).
        .assert >(@bi+2) = >@i, error, "delay_ms_a inner branch crosses a page"
        .assert >(@bo+2) = >@o, error, "delay_ms_a outer branch crosses a page"
.endif

.endif  ; _DELAY_ASM_LOADED_
