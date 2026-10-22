; ============================================================================
; input.inc -- joystick and keyboard -> in_throttle / in_brake / in_lean
; ============================================================================
;   input_init   detects the joystick (its rest position: the centre); inp_boot
;                then sets the device DIRTHOF names
;   read_input   once per frame. C = 1 and A = key when a key was typed
;                (upper case), for the main loop's own keys.
;   stick_menu, stick_button   the stick in the menus
;
; The keyboard always drives. The stick drives too when it is the device
; chosen in the main menu (inp_dev, kept in DIRTHOF: hof.inc's inp_pref);
; a new disk takes it when one answers at start. Without a stick nothing
; is read from the game port: the paddle timers never run out and the
; button inputs float (they can read "pressed" on a II+).
; Joystick: X = lean, analog (stick_lean: the further, the more, a dead zone
; in the middle); button 0 = full throttle, button 1 = brake (the brake
; wins, physics.inc). Button 0 is the trigger of most Apple sticks and the
; Open Apple key of the //e: the gas, held most of the race; Y is not read
; in a race. Keyboard: A / up arrow = full throttle, Z / down arrow = half,
; for GAS_HOLD frames, then it fades one level a frame (the bike never runs
; on by itself); SPACE brakes for BRAKE_HOLD frames and cuts the keyboard's
; gas (gas cuts the brake); left / right (J / L) lean for KEY_HOLD frames.
; The keyboard's auto-repeat renews them while a key is held (GAS_HOLD and
; BRAKE_HOLD cover its first delay: a held SPACE once braked 6 frames, then
; not at all until the repeat, and never on a II+).
; ============================================================================

KEY_HOLD = 6
GAS_HOLD = 20
BRAKE_HOLD = GAS_HOLD
JOY_DEAD = 6                    ; counts of read_stick_fast (lib/apple2/joy.asm,
JOY_STEP = 2                    ; centre ~40): lean 1 past it, one more every
                                ; 2^JOY_STEP counts, LEAN_MAX (8) from 34 on
                                ; (= tests/test_input.py); physics.py's tables
                                ; make the levels fine near the middle
STICK_ON  = 16                  ; stick_menu: a push, and back inside
STICK_OFF = 8                   ; this: armed again

.segment "ZEROPAGE"
joy_ok:      .res 1
joy_x:       .res 1
joy_y:       .res 1
joy_mx:      .res 1             ; centre, measured at start
joy_my:      .res 1
joy_cnt:     .res 1
kb_throttle: .res 1
kb_lean:     .res 1
lean_tm:     .res 1
brake_tm:    .res 1
inkey:       .res 1
jphase:      .res 1             ; frame parity of the race (new_race clears it)
mrep:        .res 1             ; stick_menu: looks before a held push repeats

.segment "BSS"
gas_tm:      .res 1
bheld:       .res 1             ; bit 7: a button held, not pressed yet
.segment "SYSBSS"
inp_dev:     .res 1             ; INP_STICK / INP_KEYS
joy_found:   .res 1             ; a stick answered at start
INP_STICK = 0                   ; (DIRTHOF's 0, a new disk: the stick if found)
INP_KEYS  = 1

.segment "INIT"                 ; boot only: overwritten by the pool
input_init:
        LDA     #0
        STA     kb_throttle
        STA     gas_tm
        STA     lean_tm
        STA     brake_tm
        STA     mrep
        STA     bheld
        JSR     read_stick_fast         ; the stick at rest is the centre
        LDA     #0
        ROL     A                       ; C = 1: no stick
        EOR     #1
        STA     joy_found
        LDA     joy_x
        STA     joy_mx
        LDA     joy_y
        STA     joy_my
        RTS

; inp_boot -- the device of DIRTHOF (after hof_load): the stick if it is
; there, else the keyboard
inp_boot:
        LDA     inp_pref
        .assert INP_STICK = 0, error, "inp_boot: INP_STICK = 0"
        BNE     @k
        LDX     joy_found
        BNE     @set
@k:     LDA     #INP_KEYS
@set:   JMP     inp_set
.segment "CODE"

; inp_set -- A = the input device (INP_STICK / INP_KEYS)
inp_set:
        STA     inp_dev
        EOR     #INP_KEYS               ; the stick only when chosen
        STA     joy_ok
        RTS
.assert INP_KEYS = 1, error, "inp_set: joy_ok = 1 for INP_STICK"

read_input:
        LDA     #0
        STA     inkey
        LDA     lean_tm                 ; keyboard holds run out
        BEQ     @l0
        DEC     lean_tm
@l0:    LDA     brake_tm
        BEQ     @b0
        DEC     brake_tm
@b0:    LDA     gas_tm                  ; throttle held, then fading
        BEQ     @g1
        DEC     gas_tm
        BPL     @g0                     ; (always)
@g1:    LDA     kb_throttle
        BEQ     @g0
        DEC     kb_throttle
@g0:    LDA     KBD
        BPL     @nokey
        BIT     KBDSTRB
        AND     #$7F
        JSR     kbd_upcase
        STA     inkey
        CMP     #KC_UP
        BEQ     @up
        CMP     #'A'
        BNE     @n1
@up:    LDA     #THROTTLE_MAX
        BNE     @gas
@n1:    CMP     #KC_DOWN
        BEQ     @down
        CMP     #'Z'
        BNE     @n2
@down:  LDA     #THROTTLE_MAX / 2
@gas:   STA     kb_throttle
        LDA     #GAS_HOLD
        STA     gas_tm
        LDA     #0                      ; gas: the brake off
        STA     brake_tm
        BEQ     @nokey
@n2:    CMP     #KC_LEFT
        BEQ     @left
        CMP     #'J'
        BNE     @n3
@left:  LDA     #<(-LEAN_MAX)
        BNE     @lean
@n3:    CMP     #KC_RIGHT
        BEQ     @right
        CMP     #'L'
        BNE     @n4
@right: LDA     #LEAN_MAX
@lean:  STA     kb_lean
        LDA     #KEY_HOLD
        STA     lean_tm
        BNE     @nokey
@n4:    CMP     #' '
        BNE     @nokey
        LDA     #BRAKE_HOLD             ; brake: the gas off
        STA     brake_tm
        LDA     #0
        STA     kb_throttle
        STA     gas_tm
@nokey: ; keyboard values
        LDA     kb_throttle
        STA     in_throttle
        LDA     #0
        LDX     lean_tm
        BEQ     @kl
        LDA     kb_lean
@kl:    STA     in_lean
        LDA     brake_tm
        STA     in_brake
        LDA     joy_ok
        BEQ     @out
        LDA     jphase                  ; the stick every other frame (~1500
        EOR     #1                      ; cycles; the hand is not faster)
        STA     jphase
        BEQ     @jold
        JSR     read_stick_fast
@jold:  LDA     lean_tm                 ; lean from X, unless a key holds it
        BNE     @btn
        SEC
        LDA     joy_x
        SBC     joy_mx
        JSR     stick_lean
        STA     in_lean
@btn:   LDA     BUTN1                   ; button 1: brake
        BPL     @b1
        STA     in_brake                ; (bit 7: non-zero)
@b1:    LDA     BUTN0                   ; button 0: full throttle
        BPL     @out
        LDA     #THROTTLE_MAX
        STA     in_throttle
@out:   LDA     inkey
        CMP     #1                      ; C = 1 when a key came
        RTS

; stick_lean -- A = stick X - centre (C = 0: negative, SBC's borrow) ->
; A = lean: 0 within JOY_DEAD, then 1 + (|d| - JOY_DEAD) >> JOY_STEP, at
; most LEAN_MAX, with the sign of d
stick_lean:
        BCS     lean_level
        EOR     #$FF                    ; left: |d| = -d
        ADC     #1
        JSR     lean_level
        EOR     #$FF
        CLC
        ADC     #1
        RTS
lean_level:
        SEC
        SBC     #JOY_DEAD
        BCS     @on
        LDA     #0
        RTS
@on:    LSR     A
        LSR     A
        .assert JOY_STEP = 2, error, "lean_level: >> JOY_STEP"
        CLC
        ADC     #1
        CMP     #LEAN_MAX+1
        BCC     @ok
        LDA     #LEAN_MAX
@ok:    RTS

; stick_button -- C = 1: the stick is the input device and a button (0 or
; 1) was pressed, now released. A button already down at the last look
; (bheld: the gas through the finish line, new_race sets it) counts only
; once let go. Keeps X, Y.
stick_button:
        LDA     joy_ok
        BEQ     @no
        LDA     BUTN0
        ORA     BUTN1
        BPL     @up
        BIT     bheld
        BMI     @no
@rel:   LDA     BUTN0
        ORA     BUTN1
        BMI     @rel
        SEC
        RTS
@up:    STA     bheld                   ; (bit 7 clear)
@no:    CLC
        RTS

; stick_menu -- one look at the stick for a menu: A = KC_RET (a button, on
; release), KC_UP / KC_DOWN / KC_LEFT / KC_RIGHT (pushed STICK_ON from its
; centre, the vertical axis first), 0 (Z = 1): nothing. One move per push:
; the stick must come back within STICK_OFF before the next; held, it
; repeats after 2 Y looks, then every Y looks (Y < 128).
stick_menu:
        JSR     stick_button
        BCC     @nob
        LDA     #KC_RET
        RTS
@nob:   LDA     joy_ok
        BEQ     @rts
        TYA
        PHA
        JSR     read_stick_fast
        PLA
        TAY
        LDX     #STICK_ON               ; the threshold: a push, or still held
        LDA     mrep
        BEQ     @thr
        LDX     #STICK_OFF
@thr:   STX     joy_cnt
        SEC
        LDA     joy_y
        SBC     joy_my
        LDX     #KC_DOWN
        BCS     @y
        EOR     #$FF                    ; |d| - 1 (near enough)
        LDX     #KC_UP
@y:     CMP     joy_cnt
        BCS     @push
        SEC
        LDA     joy_x
        SBC     joy_mx
        LDX     #KC_RIGHT
        BCS     @x
        EOR     #$FF
        LDX     #KC_LEFT
@x:     CMP     joy_cnt
        BCS     @push
        LDA     #0                      ; back in the middle: armed
        STA     mrep
@rts:   RTS
@push:  LDA     mrep
        BEQ     @first
        DEC     mrep
        BNE     @none
        STY     mrep                    ; held: again every Y looks
        TXA
        RTS
@first: TYA                             ; a new push: the first repeat later
        ASL     A
        STA     mrep
        TXA
        RTS
@none:  LDA     #0
        RTS
