; ============================================================================
; input.inc -- joystick and keyboard -> in_throttle / in_brake / in_lean
; ============================================================================
;   input_init   detects the joystick (its rest position: the centre) and
;                the mouse; inp_boot then sets the device DIRTHOF names
;   read_input   once per frame. C = 1 and A = key when a key was typed
;                (upper case), for the main loop's own keys.
;
; Only the device chosen in the main menu drives the bike (inp_dev, kept in
; DIRTHOF: hof.inc's inp_pref; the keyboard on a new disk): a stick or a
; mouse not quite centred would lean or throttle by itself. The keys R, S
; and ESC work with every device.
; Joystick: X = lean (dead zone in the middle), up = throttle (further up =
; more), down or button 0 = brake. AppleMouse (//e card, //c built-in,
; dev/lib/mouse): the same from its position (centre 70, 96), button =
; brake. Keyboard: A / up arrow = full throttle,
; Z / down arrow = half, for GAS_HOLD frames, then it fades one level a
; frame (the bike never runs on by itself); left / right (J / L) lean and
; SPACE brakes for KEY_HOLD frames. The keyboard's auto-repeat renews them
; while a key is held (GAS_HOLD covers its first delay).
; ============================================================================

KEY_HOLD = 6
GAS_HOLD = 20
JOY_DEAD = 9                    ; counts of read_stick_fast (lib/apple2/joy.asm)
JOY_GAS  = 10                   ; joy_y this far above centre: throttle
JOY_BRK  = 18                   ; this far below: brake

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
.segment "SYSBSS"
inp_dev:     .res 1             ; INP_KEYS / INP_STICK / INP_MOUSE
joy_found:   .res 1             ; a stick answered at start
stk_mx:      .res 1             ; its centre
stk_my:      .res 1
INP_KEYS  = 0
INP_STICK = 1
INP_MOUSE = 2

.segment "CODE"

.segment "INIT"                 ; boot only: overwritten by the pool
input_init:
        LDA     #0
        STA     kb_throttle
        STA     gas_tm
        STA     lean_tm
        STA     brake_tm
        JSR     read_stick_fast            ; the stick at rest is the centre
        LDA     #0
        ROL     A                       ; C = 1: no stick
        EOR     #1
        STA     joy_ok
        LDA     joy_x
        STA     joy_mx
        LDA     joy_y
        STA     joy_my
        STA     stk_my                  ; (the stick's centre, for a change of
        LDA     joy_mx                  ;  device in the main menu)
        STA     stk_mx
        LDA     joy_ok
        STA     joy_found
        JMP     _mouse_init

; inp_boot -- the device of DIRTHOF (after hof_load), if it is there; else
; the keyboard
inp_boot:
        LDA     inp_pref
        CMP     #INP_STICK
        BNE     @m
        LDX     joy_found
        BNE     @set
@m:     CMP     #INP_MOUSE
        BNE     @k
        LDX     _mouse_slot
        BNE     @set
@k:     LDA     #INP_KEYS
@set:   JMP     inp_set
.segment "CODE"

; inp_set -- A = the input device (INP_KEYS / INP_STICK / INP_MOUSE)
inp_set:
        STA     inp_dev
        LDX     #0                      ; the stick only when chosen
        CMP     #INP_STICK
        BNE     @nost
        INX
@nost:  STX     joy_ok
        LDX     stk_mx                  ; centres: the stick's or the mouse's
        LDY     stk_my
        CMP     #INP_MOUSE
        BNE     @c
        LDX     #70                     ; dev/lib/mouse: X 0..139, starts at 70
        LDY     #MOUSE_Y_START
@c:     STX     joy_mx
        STY     joy_my
        LDA     #0
        STA     _mouse_buttons
        RTS

.segment "CODE"
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
        LDX     inp_dev                 ; drive keys: the keyboard's only
        BNE     @nokey
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
        BNE     @nokey
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
        LDA     #KEY_HOLD
        STA     brake_tm
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
        LDA     inp_dev                 ; the mouse: its position for the stick's
        CMP     #INP_MOUSE              ; (X = lean, up = gas, down = brake)
        BNE     @stick
        JSR     _mouse_poll
        LDA     _mouse_x
        STA     joy_x
        LDA     _mouse_y
        STA     joy_y
        JMP     @jold
@stick: LDA     joy_ok
        BEQ     @out
        LDA     jphase                  ; the stick every other frame (~1500
        EOR     #1                      ; cycles; the hand is not faster)
        STA     jphase
        BEQ     @jold
        JSR     read_stick_fast
@jold:
        ; lean from X, unless a key holds it
        LDA     lean_tm
        BNE     @jt
        SEC
        LDA     joy_x
        SBC     joy_mx
        BCS     @jr
        EOR     #$FF                    ; left: |d| = -d (d - 1 + 1 trick)
        ADC     #1
        JSR     lean_level
        EOR     #$FF
        CLC
        ADC     #1
        JMP     @js
@jr:    JSR     lean_level
@js:    STA     in_lean
@jt:    SEC                             ; throttle: the higher, the more
        LDA     joy_my
        SBC     joy_y
        BCC     @jdn                    ; below the centre
        SEC
        SBC     #JOY_GAS
        BCC     @btn
        LSR     A
        LSR     A
        CLC
        ADC     #1
        CMP     #THROTTLE_MAX+1
        BCC     @jg
        LDA     #THROTTLE_MAX
@jg:    CMP     in_throttle
        BCC     @btn
        STA     in_throttle
        BCS     @btn
@jdn:   EOR     #$FF                    ; distance below the centre
        CLC
        ADC     #1
        CMP     #JOY_BRK
        BCC     @btn
        LDA     #1
        STA     in_brake
@btn:   LDA     _mouse_buttons          ; the mouse's button (0 unless it
        LDX     joy_ok                  ; polls), or the stick's
        BEQ     @b
        ORA     BUTN0
@b:     ASL     A
        BCC     @out
        LDA     #1
        STA     in_brake
@out:   LDA     inkey
        CMP     #1                      ; C = 1 when a key came
        RTS

; stick_button -- C = 1: the stick is the input device and its button was
; pressed (now released). Keeps X, Y.
stick_button:
        LDA     joy_ok
        BEQ     @no
        LDA     BUTN0
        BPL     @no
@rel:   LDA     BUTN0
        BMI     @rel
        SEC
        RTS
@no:    CLC
        RTS

; stick_menu -- one look at the stick for a menu: A = KC_RET (its button,
; on release), KC_UP / KC_DOWN / KC_LEFT / KC_RIGHT (pushed past STICK_ON
; from its centre; held, again after Y more looks), 0 (Z = 1): nothing
STICK_ON = 16
stick_menu:
        JSR     stick_button
        BCC     @nob
        LDA     #KC_RET
        RTS
@nob:   LDA     joy_ok
        BEQ     @none
        LDA     mrep                    ; the repeat delay
        BEQ     @read
        DEC     mrep
@none:  LDA     #0
        RTS
@read:  TYA
        PHA
        JSR     read_stick_fast
        PLA
        TAY
        SEC
        LDA     joy_y
        SBC     joy_my
        BCS     @dn
        CMP     #<(-STICK_ON)
        BCS     @x
        LDA     #KC_UP
        BNE     @rep                    ; (always)
@dn:    CMP     #STICK_ON
        BCC     @x
        LDA     #KC_DOWN
        BNE     @rep
@x:     SEC
        LDA     joy_x
        SBC     joy_mx
        BCS     @rt
        CMP     #<(-STICK_ON)
        BCS     @none
        LDA     #KC_LEFT
        BNE     @rep
@rt:    CMP     #STICK_ON
        BCC     @none
        LDA     #KC_RIGHT
@rep:   STY     mrep
        RTS

; A = |stick deflection| -> 0..LEAN_MAX
lean_level:
        SEC
        SBC     #JOY_DEAD
        BCS     @on
        LDA     #0
        RTS
@on:    LSR     A
        LSR     A
        CLC
        ADC     #1
        CMP     #LEAN_MAX+1
        BCC     @ok
        LDA     #LEAN_MAX
@ok:    RTS
