; ============================================================================
; input.inc -- joystick and keyboard -> in_throttle / in_brake / in_lean
; ============================================================================
;   input_init   detects the joystick and takes its rest position as centre
;   read_input   once per frame. C = 1 and A = key when a key was typed
;                (upper case), for the main loop's own keys.
;
; Joystick: X = lean (dead zone in the middle), up = throttle (further up =
; more), down or button 0 = brake. AppleMouse (//e card, //c built-in,
; dev/lib/mouse): the same from its position (centre 70, 96), button =
; brake; with a mouse the joystick is not read. Keyboard: A / up arrow = full throttle,
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

.segment "BSS"
gas_tm:      .res 1

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
        JSR     _mouse_init             ; a mouse (A = slot): it replaces the stick
        TAX
        BEQ     @nom
        LDA     #0
        STA     joy_ok
        LDA     #70                     ; dev/lib/mouse: X 0..139, starts at 70
        STA     joy_mx
        LDA     #MOUSE_Y_START
        STA     joy_my
@nom:   RTS

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
        LDA     _mouse_slot             ; a mouse: its position for the stick's
        BEQ     @stick                  ; (X = lean, up = gas, down = brake)
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
@btn:   LDA     BUTN0                   ; button 0, or the mouse's
        ORA     _mouse_buttons
        BPL     @out
        LDA     #1
        STA     in_brake
@out:   LDA     inkey
        CMP     #1                      ; C = 1 when a key came
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
