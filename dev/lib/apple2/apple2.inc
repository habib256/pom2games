; ============================================================================
; apple2.inc -- shared hardware equates for Apple II / II+ programs
; ============================================================================
; The Apple II counterpart of POM1's dev/lib/apple1/apple1.inc: machine
; equates plus the APPLE2_PREAMBLE macro (emits no code until invoked), no
; segments. Safe to include from any segment, idempotent.
;
; Target: Apple II+ 48 KB with DOS 3.3 (any later model runs it too). Programs
; are DOS binary files started with BRUN; see dev/cc65/apple2_hgr.cfg.
;
; THE DIFFERENCES THAT BITE WHEN PORTING FROM THE APPLE-1:
;   - Keyboard: one latch at $C000 (bit 7 = key ready, low 7 bits = key),
;     cleared by touching $C010. Reading $C000 does NOT clear it: a port of
;     `LDA KBD` must add `BIT KBDSTRB` (kbd.asm does).
;   - Display: text goes through COUT ($FDED) onto the SAME screen as the
;     graphics — there is no second terminal. Show text with TXTSET, graphics
;     with TXTCLR; the text page ($0400) and HGR pages ($2000/$4000) are
;     separate memory, so flipping never destroys either.
;   - Soft switches toggle on ANY access (read or write) at $C050-$C057:
;     they are address decodes, the data is ignored. LDA/BIT is the idiom.
;   - No V-blank signal on a II/II+ ($C019 is a //e addition).
;   - RAM: $1000-$1FFF and $6000-$95FF are free under DOS 3.3. $0800-$0FFF
;     holds the BASIC greeting program DOS keeps (HELLO), $0300-$03FF the
;     DOS/monitor vectors (reset vector at $03F2) — keep out of both.
;   - Zero page is shared with the Monitor ($20-$4F), DOS and Applesoft
;     ($50-$FF). A program that returns to DOS must preserve it (exit.asm).
;
; cc65 include path: dev/lib/apple2/
; ============================================================================

.ifndef _APPLE2_INC_LOADED_
_APPLE2_INC_LOADED_ = 1

; --- Keyboard ---------------------------------------------------------------
KBD      = $C000        ; key latch: bit 7 = key ready, bits 0-6 = ASCII
KBDSTRB  = $C010        ; any access clears the key-ready strobe

; --- Key codes, 7-bit (as returned by kbd.asm; OR #$80 for a raw KBD byte) --
; KC_ prefix on purpose: games tend to own KEY_* names for their own bindings.
KC_LEFT  = $08          ; left arrow  (= Ctrl-H / backspace)
KC_RIGHT = $15          ; right arrow (= Ctrl-U)
KC_UP    = $0B          ; up arrow    (//e and later; Ctrl-K on a II+)
KC_DOWN  = $0A          ; down arrow  (//e and later; Ctrl-J on a II+)
KC_RET   = $0D
KC_ESC   = $1B
KC_SPACE = $20

; --- Sound / cassette -------------------------------------------------------
SPKR     = $C030        ; any access toggles the speaker

; --- Video soft switches (any access toggles) --------------------------------
TXTCLR   = $C050        ; graphics
TXTSET   = $C051        ; text
MIXCLR   = $C052        ; full screen
MIXSET   = $C053        ; split screen: bottom 4 text rows
LOWSCR   = $C054        ; display page 1
HISCR    = $C055        ; display page 2
LORES    = $C056        ; low-resolution graphics
HIRES    = $C057        ; high-resolution graphics

; --- Game port --------------------------------------------------------------
BUTN0    = $C061        ; button 0 / Open-Apple (bit 7)
BUTN1    = $C062        ; button 1 / Solid-Apple (bit 7)
BUTN2    = $C063        ; button 2 (bit 7)
PADDL0   = $C064        ; paddle 0 timer (bit 7 while charging)
PADDL1   = $C065        ; paddle 1 timer
PTRIG    = $C070        ; start all paddle timers

; --- Display memory ---------------------------------------------------------
TEXT1    = $0400        ; text/lores page 1 (40x24)
HGR1     = $2000        ; hi-res page 1 (280x192, interleaved rows)
HGR2     = $4000        ; hi-res page 2

; --- Monitor ROM (II+ Autostart) --------------------------------------------
; These use the Monitor's zero page ($20-$4F): keep your own ZP out of it
; while you call them (dev/cc65/apple2_hgr.cfg puts program ZP at $50+).
COUT     = $FDED        ; print A (set bit 7 for normal video) via CSW
CROUT    = $FD8E        ; print a carriage return
PRBYTE   = $FDDA        ; print A as two hex digits
PRHEX    = $FDE3        ; print low nibble of A as one hex digit
HOME     = $FC58        ; clear the text window, cursor top-left
VTAB     = $FC22        ; recompute BASL from CV ($25)
RDKEY    = $FD0C        ; wait for a key via KSW (returns A = key | $80)
BELL     = $FF3A        ; beep
WAIT     = $FCA8        ; delay, ~ (26 + 27*A + 5*A*A)/2 cycles
SETTXT   = $FB39        ; text mode, full window (TEXT)

CH       = $24          ; Monitor: cursor column (0..39)
CV       = $25          ; Monitor: cursor row    (0..23)

; --- DOS 3.3 ----------------------------------------------------------------
DOSWARM  = $03D0        ; DOS warm start: back to the ']' prompt, program kept
SOFTEV   = $03F2        ; RESET vector (low, high), $03F4 = power-up byte

; --- Canonical entry preamble -----------------------------------------------
; Put APPLE2_PREAMBLE first in every program started with BRUN. DOS jumps to
; the load address with whatever flags and stack the caller left:
;   CLD        clear a possibly stale decimal flag
;   LDX #$FF   \ fresh full-depth stack (a BRUN program never RTSes to DOS;
;   TXS        /  leave through exit.asm's apple2_exit instead)
; No SEI: the II+ has no IRQ source of its own, and cards that use one expect
; interrupts to stay enabled.
.macro APPLE2_PREAMBLE
        cld
        ldx #$FF
        txs
.endmacro

; APPLE2_PREAMBLE_CALL: for a program started by CALL (a BASIC menu doing
; BLOAD + CALL) that returns with apple2_return. The caller's hardware stack
; holds BASIC's return path, so it must NOT be reset.
.macro APPLE2_PREAMBLE_CALL
        cld
.endmacro

.endif  ; _APPLE2_INC_LOADED_
