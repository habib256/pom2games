; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; joy.asm -- joystick (two paddle timers) for the Apple II game port
; ============================================================================
;   read_stick -- sample both axes. joy_x, joy_y = 0 (left / up) .. ~120
;                 (right / down), ~60 centred. Clobbers A, X, Y. ~6 ms.
;                 An open axis never discharges its timer (PADDLn still
;                 reads bit 7 after the 6 ms): that axis is set to centre
;                 (60), so stick_dir ignores it -- e.g. a single paddle.
;                 C = 1 when both are open: no stick is connected.
;   read_stick_fast -- the same two timers, but returns as soon as both have
;                 run out: ~0.1-2.8 ms instead of 6 ms (a game loop at
;                 30 fps keeps ~5 ms a frame). A 35-cycle turn (34 with
;                 joy_cnt in zero page), so its counts run ~0..80, centre
;                 ~40, not read_stick's scale (23-25 cycles, centre ~56):
;                 calibrate (take the rest position at start) rather than
;                 using JOY_LO / JOY_HI. C = 1 after 255 turns with an
;                 axis still running: no stick, or one axis missing (read_stick
;                 centres it instead); joy_x / joy_y then hold the raw counts. That
;                 case takes ~8.7 ms, longer than read_stick: test C once at
;                 start and skip the call when there is no stick.
;                 Clobbers A, X, Y. From DIRTBIKE.
;   stick_dir  -- after read_stick: A = JOY_UP / JOY_DOWN / JOY_LEFT /
;                 JOY_RIGHT, or JOY_NONE (0, Z set) inside the dead zone.
;                 The vertical axis wins a diagonal. Clobbers A.
;   stick_key  -- the stick as one-shot key events: reads the stick, then
;                 event X = JOY_UP..JOY_RIGHT (1..4), STICK_B0 (5, button 0)
;                 or STICK_B1 (6, button 1). Each fires once on its own
;                 edge: a button when pressed, a direction when it changes
;                 to a non-centre value (centring rearms it; letting go of
;                 a button while a direction is held fires nothing). Button
;                 0 wins over button 1, a button over a direction; the loser
;                 fires on the next call. Out: A = STICK_KEYS[X-1] (Z = 0)
;                 from the caller's 6-byte table (keys for UP, DOWN, LEFT,
;                 RIGHT, B0, B1), or A = 0 (Z = 1) when nothing new. Without
;                 STICK_KEYS, A = X = the event number. read_stick C = 1 (no
;                 stick) is "nothing": the buttons are then not read (they
;                 float on a II+ without a stick). Clobbers A, X, Y.
;                 State: stick_key_last (1 B, zero it at start) and
;                 stick_key_btn (2 B, no init needed: a junk value can at
;                 worst fire a button held at the first call); BSS, define
;                 them first for ZP aliases. 50 B (with STICK_KEYS) on top
;                 of read_stick (52) and stick_dir (37), which it pulls in.
;                 Options: STICK_KEY_FAST = 1 samples with read_stick_fast
;                 (retune JOY_LO / JOY_HI to its scale); STICK_KEY_REPEAT =
;                 n repeats a held direction every n calls (+1 B BSS
;                 stick_key_rep, +20 B code; buttons never repeat).
;   joy_buttons -- A = buttons held (bit 0 = button 0, bit 1 = button 1),
;                 X = newly pressed since the last call (same bits), Z from
;                 A. State joy_btn_last (1 B BSS, zero it at start). 25 B.
;                 Clobbers A, X, Y. Reads BUTN0/1 unconditionally: on a II+,
;                 call it only once a stick is known to be there.
;
; Otherwise the buttons need no routine: BUTN0 / BUTN1 (apple2.inc) read
; bit 7 = 1 while pressed (`LDA BUTN0 / BMI pressed`).
;
; Why one fixed loop: PTRIG starts both timers, and each PADDLn reads bit 7
; = 1 until its capacitor has charged (up to ~2.8 ms). Counting both in the
; same 256-turn loop (23-25 cycles a turn, 25 while both run: 6 ms, longer
; than a full charge) avoids the classic bug of reading the second paddle
; before the first has discharged.
;
; Dead zone: JOY_LO / JOY_HI (count below / above = deflected). Define them
; before the include to retune; defaults suit a centred stick at ~60.
;
; BSS: joy_x, joy_y, joy_cnt, each skipped if defined before the include
; (a zero-page alias is fine). No zero page otherwise. Only the routines referenced
; before the include are assembled (.ifref); stick_key pulls in its reader
; and stick_dir.
; Caller responsibility: .include "apple2.inc" first (PTRIG, PADDL0/1).
; Mirror for C: a2_read_stick() in ../apple2c/apple2game.h.
; ============================================================================

.ifndef _JOY_ASM_LOADED_
_JOY_ASM_LOADED_ = 1

.ifndef JOY_LO
JOY_LO = 30
.endif
.ifndef JOY_HI
JOY_HI = 90
.endif
.ifndef STICK_KEY_FAST                  ; options: values, 0 = undefined
STICK_KEY_FAST = 0
.endif
.ifndef STICK_KEY_REPEAT
STICK_KEY_REPEAT = 0
.endif

JOY_NONE  = 0
JOY_UP    = 1
JOY_DOWN  = 2
JOY_LEFT  = 3
JOY_RIGHT = 4
STICK_B0  = 5                   ; stick_key events after the directions
STICK_B1  = 6

.segment "BSS"
.ifndef joy_x
joy_x:          .res 1
.endif
.ifndef joy_y
joy_y:          .res 1
.endif
.ifndef joy_cnt
joy_cnt:        .res 1
.endif

.segment "CODE"


.if .referenced(read_stick) .or (.referenced(stick_key) .and (STICK_KEY_FAST = 0))
read_stick:
        LDX     #$00
        LDY     #$00
        STX     joy_cnt         ; 256 turns
        LDA     PTRIG
@lp:    LDA     PADDL0
        BPL     @xd
        INX
@xd:    LDA     PADDL1
        BPL     @yd
        INY
@yd:    DEC     joy_cnt
        BNE     @lp
        LDA     PADDL0          ; a timer still running after 6 ms: that
        BPL     @x              ; axis is open (its count wrapped), centre it
        LDX     #60
@x:     STX     joy_x
        AND     PADDL1          ; both open: nothing is plugged in, C = 1
        ASL     A
        LDA     PADDL1
        BPL     @y
        LDY     #60
@y:     STY     joy_y
        RTS
.endif

.if .referenced(read_stick_fast) .or (.referenced(stick_key) .and (STICK_KEY_FAST <> 0))
read_stick_fast:
        LDX     #0
        LDY     #0
        LDA     #255
        STA     joy_cnt
        LDA     PTRIG
@lp:    LDA     PADDL0
        BPL     @xd
        INX
@xd:    LDA     PADDL1
        BPL     @yd
        INY
@yd:    LDA     PADDL0                  ; both run out: done
        ORA     PADDL1
        BPL     @done
        DEC     joy_cnt
        BNE     @lp
        STX     joy_x
        STY     joy_y
        SEC
        RTS
@done:  STX     joy_x
        STY     joy_y
        CLC
        RTS
.endif

.if .referenced(stick_dir) .or .referenced(stick_key)
stick_dir:
        LDA     joy_y
        CMP     #JOY_LO
        BCC     @up
        CMP     #JOY_HI+1
        BCS     @down
        LDA     joy_x
        CMP     #JOY_LO
        BCC     @left
        CMP     #JOY_HI+1
        BCS     @right
        LDA     #JOY_NONE
        RTS
@up:    LDA     #JOY_UP
        RTS
@down:  LDA     #JOY_DOWN
        RTS
@left:  LDA     #JOY_LEFT
        RTS
@right: LDA     #JOY_RIGHT
        RTS
.endif

; stick_key: see the header. Each event fires on its own edge. The buttons
; are shift registers, stick_key_btn+0 / +1 for BUTN0 / BUTN1: bit 7 = held
; now, bit 6 = held at the last call; a press is now and not before.
; stick_key_last = the last direction: a direction fires when it changes to
; a non-centre value, so a held direction fires again only after centring
; or turning, and pressing or releasing a button leaves it alone. An event
; that loses the priority stays pending for the next call.
.ifref stick_key
.segment "BSS"
.ifndef stick_key_last
stick_key_last: .res 1
.endif
.ifndef stick_key_btn
stick_key_btn:  .res 2
.endif
.if STICK_KEY_REPEAT
stick_key_rep:  .res 1
.endif
.segment "CODE"
stick_key:
.if STICK_KEY_FAST
        JSR     read_stick_fast
.else
        JSR     read_stick
.endif
        LDA     #JOY_NONE
        BCS     @dir_in         ; no stick: never read the floating buttons
        LDX     #STICK_B0       ; button 0 first
@btn:   LDA     BUTN0-STICK_B0,X
        ASL     A               ; C = held
        ROR     stick_key_btn-STICK_B0,X
        LDA     stick_key_btn-STICK_B0,X
        ASL     A               ; C = held now, N = held before
        BCC     @next
        BPL     @fire           ; pressed since the last call
@next:  INX
        CPX     #STICK_B1+1
        BNE     @btn
        JSR     stick_dir
@dir_in:
        CMP     stick_key_last
        BEQ     @same
        STA     stick_key_last
.if STICK_KEY_REPEAT
        LDX     #STICK_KEY_REPEAT
        STX     stick_key_rep
.endif
        TAX                     ; centred: A = 0, Z = 1
        BNE     @fire
@none:  LDA     #0
        RTS
@fire:
.ifdef STICK_KEYS
        LDA     STICK_KEYS-1,X
.else
        TXA
.endif
        RTS
.if STICK_KEY_REPEAT
@same:  TAX
        BEQ     @none           ; centred
        DEC     stick_key_rep
        BNE     @none
        LDX     #STICK_KEY_REPEAT
        STX     stick_key_rep
        TAX
        BNE     @fire           ; always
.else
@same = @none
.endif
.endif

; joy_buttons: A = held (bit 0 = BUTN0, bit 1 = BUTN1), X = newly pressed.
.ifref joy_buttons
.segment "BSS"
.ifndef joy_btn_last
joy_btn_last:   .res 1
.endif
.segment "CODE"
joy_buttons:
        LDA     BUTN1
        CMP     #$80            ; C = button 1
        LDA     BUTN0
        ROL     A               ; C = button 0, bit 0 = button 1
        ROL     A               ; bit 1 = button 1, bit 0 = button 0
        AND     #3
        TAY
        EOR     joy_btn_last    ; changed
        STY     joy_btn_last
        AND     joy_btn_last    ; changed and held = newly pressed
        TAX
        TYA
        RTS
.endif

.endif  ; _JOY_ASM_LOADED_
