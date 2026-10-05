; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; kbd.asm -- Apple II keyboard primitives
; ============================================================================
; Two routines, no ZP usage. X and Y are preserved.
;
;   wait_key  -- block until a key is ready, return A = key with bit 7
;                cleared (lower case folded to upper case).
;
;   poll_key  -- non-blocking read. A = key (bit 7 cleared, upper-cased) if a
;                key was pending, A = 0 otherwise. The Z flag reflects the same:
;                BEQ branches when no key was available.
;
; The key latch at $C000 is NOT cleared by reading it. Both routines touch
; KBDSTRB ($C010) after taking the key to acknowledge it.
;
; The II+ keyboard only sends upper case, but a //e (or an emulator fed a host
; keyboard) can send lower case: folding keeps `CMP #'I'` style tests working
; everywhere. Arrow keys arrive as control codes: left $08, right $15
; (KEY_LEFT/KEY_RIGHT & $7F in apple2.inc).
;
; Caller responsibility: KBD / KBDSTRB must be in scope (.include "apple2.inc").
; ============================================================================

.segment "CODE"

; ----------------------------------------------------------------------------
; wait_key -- block until a key is ready. A = key & $7F, upper-cased.
;             Clobbers A. X, Y preserved.
; ----------------------------------------------------------------------------
wait_key:
@wk:    LDA     KBD
        BPL     @wk             ; bit 7 = 0 -> no key, keep polling
        BIT     KBDSTRB         ; acknowledge (clear the strobe)
        AND     #$7F
        JMP     kbd_upcase

; ----------------------------------------------------------------------------
; poll_key -- non-blocking. A = key & $7F (upper-cased), or 0 if none.
;             Z flag reflects A. Clobbers A. X, Y preserved.
; ----------------------------------------------------------------------------
poll_key:
        LDA     KBD
        BPL     @none           ; bit 7 = 0 -> no key
        BIT     KBDSTRB
        AND     #$7F
        JMP     kbd_upcase
@none:  LDA     #$00
        RTS

; kbd_upcase -- 'a'..'z' -> 'A'..'Z', anything else unchanged. Sets Z/N from A.
kbd_upcase:
        CMP     #'a'
        BCC     @done
        CMP     #'z'+1
        BCS     @done
        AND     #$DF
@done:  CMP     #$00            ; Z/N reflect the returned key
        RTS
