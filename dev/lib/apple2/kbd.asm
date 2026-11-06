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
; (KC_LEFT / KC_RIGHT in apple2.inc).
;
; Only the routines referenced before the include are assembled (.ifref).
; Caller responsibility: KBD / KBDSTRB must be in scope (.include "apple2.inc").
; ============================================================================

.ifndef _KBD_ASM_LOADED_
_KBD_ASM_LOADED_ = 1

.segment "CODE"

; ----------------------------------------------------------------------------
; wait_key -- block until a key is ready. A = key & $7F, upper-cased.
;             Clobbers A. X, Y preserved.
; ----------------------------------------------------------------------------
.ifref wait_key
wait_key:
@wk:    LDA     KBD
        BPL     @wk             ; bit 7 = 0 -> no key, keep polling
        .ifref poll_key
        JMP     kbd_take         ; skip the nonblocking entry
        .endif
.endif

; ----------------------------------------------------------------------------
; poll_key -- non-blocking. A = key & $7F (upper-cased), or 0 if none.
;             Z flag reflects A. Clobbers A. X, Y preserved.
; ----------------------------------------------------------------------------
.ifref poll_key
poll_key:
        LDA     KBD
        BMI     kbd_take        ; bit 7 = 1 -> take the pending key
        LDA     #$00
        RTS
.endif

; Shared pending-key path, reached only after observing the latch set.
.if .referenced(wait_key) .or .referenced(poll_key)
kbd_take:
        BIT     KBDSTRB         ; acknowledge once, after reading the key
        AND     #$7F
.endif

; kbd_upcase -- 'a'..'z' -> 'A'..'Z', anything else unchanged. Sets Z/N from A.
.if .referenced(kbd_upcase) .or .referenced(wait_key) .or .referenced(poll_key)
kbd_upcase:
        CMP     #'a'
        BCC     @done
        CMP     #'z'+1
        BCS     @done
        AND     #$DF
@done:  CMP     #$00            ; Z/N reflect the returned key
        RTS
.endif

.endif  ; _KBD_ASM_LOADED_
