; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; sound.asm -- square-wave tones on the Apple II speaker ($C030)
; ============================================================================
; The speaker is a single bit: every access to SPKR flips the cone. A tone is
; a run of flips with a fixed delay between them; a lone `LDA SPKR` is a
; click. The CPU does nothing else meanwhile (no timer, no interrupt).
;
;   tone -- A = flips (0 -> 256), X = half-period delay (0 -> 256).
;           Clobbers A, X, Y. 12 + 5*X cycles per flip (LDA 4, LDX 4, delay
;           5*X - 1, DEY 2, BNE 3). A flip is HALF a period, so the pitch
;           is 1.02 MHz / (2 * (12 + 5*X)): X = $28 -> ~2.4 kHz blip,
;           $C0 -> ~526 Hz, $FF -> ~397 Hz thud.
;           Length = A * (12 + 5*X) cycles: A = $60, X = $C0 ~ 91 ms.
;
; One byte of BSS (snd_period), no zero page. The loops must not cross a
; page: a taken branch that does costs one more cycle per turn (6 X
; instead of 5 X: notes ~20 % longer and lower; the outer loop +1 a flip);
; the link fails if one does (place the include where it fits, e.g. at the
; start of CODE).
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
.assert >(@d) = >(* - 4), lderror, "tone: its delay loop crosses a page (+20 % per note)"
.assert >(@t) = >(* - 1), lderror, "tone: its flip loop crosses a page (+1 cycle per flip)"

.endif  ; _SOUND_ASM_LOADED_
