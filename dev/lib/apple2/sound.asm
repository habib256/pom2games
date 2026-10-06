; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; sound.asm -- square-wave tones on the Apple II speaker ($C030)
; ============================================================================
; The speaker is a single bit: every access to SPKR flips the cone. A tone is
; a run of flips with a fixed delay between them; a lone `LDA SPKR` is a
; click. The CPU does nothing else meanwhile (no timer, no interrupt).
;
;   tone -- A = flips (0 -> 256), X = half-period delay (0 -> 256).
;           Clobbers A, X, Y. ~(13 + 5*X) cycles per flip at 1.02 MHz:
;           X = $28 -> ~4.8 kHz blip, $C0 -> ~1 kHz, $FF -> ~780 Hz thud.
;           Length ~ A * (13 + 5*X) cycles: A = $60, X = $C0 ~ 95 ms.
;
; One byte of BSS (snd_period), no zero page. A taken branch that crosses a
; page costs one more cycle per turn: the pitch shifts by <1 %, so no assert.
;
; Caller responsibility: .include "apple2.inc" first (SPKR).
; Mirror for C: a2_tone() in ../apple2c/apple2game.h.
; ============================================================================

.ifndef _SOUND_ASM_LOADED_
_SOUND_ASM_LOADED_ = 1

.segment "BSS"
snd_period:     .res 1

.segment "CODE"

tone:
        TAY                     ; Y = flips left
        STX     snd_period
@t:     LDA     SPKR
        LDX     snd_period
@d:     DEX
        BNE     @d
        DEY
        BNE     @t
        RTS

.endif  ; _SOUND_ASM_LOADED_
