; ============================================================================
; physics.inc -- the bike: three Verlet points on a height-map ground
; ============================================================================
; 6502 transcription of tools/physics.py (read it first: the model explains
; the method, this file only follows it). The two must agree bit for bit;
; tests/test_physics.py runs both and compares the state after N ticks.
;
;   phys_reset   bike at rest at world column START_X
;   phys_tick    one tick with the inputs in in_throttle / in_brake / in_lean
;
; Points: 0 = rear wheel, 1 = front wheel, 2 = rider. x is 16.8 (pt_xf/xl/xh),
; y is 8.8 (pt_yf/yh); o* are the previous positions. Caller provides
; track_h (one ground row per world pixel), physconst.inc and lib/math
; (math.inc with MUL_ACC = 1 first, mul.asm after).
;
; The generic part is lib/physics (dev/lib/physics: verlet.inc here, the
; routines at the end of dirtbike.s): points, constraints, ground. Its zero
; page and variables are DIRTBIKE's own below (the vl_ names alias them,
; the order of the tests' snapshot block stays); this file keeps the bike:
; the order of a tick, the traction / brake hooks of the ground, the crash
; tests.
; ============================================================================

.segment "ZEROPAGE"
val:    .res 2                  ; signed 8.8 operand of the add/sub helpers
vx:     .res 2
vy:     .res 2
dx:     .res 2
dy:     .res 2
vn:     .res 2
vt:     .res 2
pen:    .res 2
w0:     .res 1                  ; 24-bit scratch
w1:     .res 1
w2:     .res 1
nx:     .res 1                  ; ground normal, 64 = 1.0 (tangent = -ny, nx)
ny:     .res 1
fcoef:  .res 1
qx:     .res 1
cur:    .res 1                  ; current point / constraint
ca:     .res 1
cb:     .res 1
cpass:  .res 1
tptr:   .res 2                  ; into the track
hxl:    .res 1                  ; height_at argument (world pixel)
hxh:    .res 1
hgt:    .res 1                  ; ground row under a wheel
hm2:    .res 1                  ; and 2 pixels to each side
hp2:    .res 1

.segment "BSS"
pt_xf:  .res 3
pt_xl:  .res 3
pt_xh:  .res 3
pt_yf:  .res 3
pt_yh:  .res 3
pt_oxf: .res 3
pt_oxl: .res 3
pt_oxh: .res 3
pt_oyf: .res 3
pt_oyh: .res 3
wheel_gnd:  .res 2              ; 1 = wheel touched the ground this tick
wheel_ang:  .res 2              ; spoke angle, 256 = one turn
crashed:    .res 1
laps:       .res 1              ; laps behind (looping tracks)
wrapped:    .res 1              ; set when the bike moved back a lap
in_throttle: .res 1             ; 0..THROTTLE_MAX
in_brake:   .res 1              ; 0 / non-zero
in_lean:    .res 1              ; signed, -LEAN_MAX..LEAN_MAX
turn:       .res 1              ; this tick's turn of the wheel axis (do_lean)
lidx:       .res 1              ; in_lean + LEAN_MAX (rider link tables)
flev:       .res 1              ; forward lean level of the last tick (fwd_k)
cidx:       .res 1              ; constraint table index
squashed:   .res 1              ; a rider link too short (pass after the ground)
spin_l:     .res 2              ; rolling speed at the last contact (8.8):
spin_h:     .res 2              ; the brake stops it in the air (phys_tick)
hold_on:    .res 2              ; the brake stopped the wheel this tick: it holds
hold_xf:    .res 2              ; at its x when the tick began
hold_xl:    .res 2
hold_xh:    .res 2

.segment "DATA"
lap_len:    .word 0             ; set by the game per track; 0: no loop
.segment "CODE"

; ---------------------------------------------------------------------------
; lib/physics: DIRTBIKE's parameters and switches, its variables as the
; library's, verlet.inc
; ---------------------------------------------------------------------------
VL_NPOINTS      = 3
VL_NCON         = NCONSTRAINTS
VL_GRAVITY      = GRAVITY
VL_VMAX_X       = VMAX_X
VL_VMAX_Y       = VMAX_Y
VL_GROUND       = 2                     ; the wheels touch the ground
VL_HEIGHTS      = track_h
VL_RADIUS       = WHEEL_R
VL_PROBE        = 2
VL_SLOPE_MAX    = SLOPE_MAX
VL_FAR          = FAR
VL_BOUNCE       = BOUNCE
VL_WRAP_MARGIN  = WRAP_MARGIN
VL_INTEGRATE_LEFTWALL = LEFT_WALL
VL_CEILING_CLAMP = CEILING
VL_CON_VARIANTS = NLEAN                 ; rest lengths per lean level
VL_CON_HEAVY_POINT = 2                  ; the rider is heavier than a wheel
VL_CON_HEAVY_SHIFT = RIDER_HEAVY
VL_CON_MINLEN_POINT = 2                 ; a rider link squashed: a crash
VL_CON_MINLEN   = L2Q_MIN
VL_PAIR_DAMP    = SPIN_DAMP             ; the spin of the wheel axis fades
VL_SHIFT_POINT  = 2                     ; the lean moves the rider
.define VL_ROT_SEG     "TXTC4"          ; (text page: no room in main RAM)
.define VL_MULTURN_SEG "TXTC7"

vl_val  = val
vl_vx   = vx
vl_vy   = vy
vl_dx   = dx
vl_dy   = dy
vl_vn   = vn
vl_vt   = vt
vl_pen  = pen
vl_w0   = w0
vl_w1   = w1
vl_w2   = w2
vl_nx   = nx
vl_ny   = ny
vl_fcoef = fcoef
vl_qx   = qx
vl_cur  = cur
vl_ca   = ca
vl_cb   = cb
vl_tptr = tptr
vl_hxl  = hxl
vl_hxh  = hxh
vl_hgt  = hgt
vl_hm2  = hm2
vl_hp2  = hp2
vl_xf   = pt_xf
vl_xl   = pt_xl
vl_xh   = pt_xh
vl_yf   = pt_yf
vl_yh   = pt_yh
vl_oxf  = pt_oxf
vl_oxl  = pt_oxl
vl_oxh  = pt_oxh
vl_oyf  = pt_oyf
vl_oyh  = pt_oyh
vl_gnd  = wheel_gnd
vl_turn = turn
vl_con_row = lidx
vl_cidx = cidx
vl_squashed = squashed
vl_lap_len = lap_len
vl_con_a = con_a
vl_con_b = con_b
vl_con_l2l = con_l2l
vl_con_l2h = con_l2h
vl_con_k8 = con_k8
vl_norm_x = norm_x
vl_norm_y = norm_y
.include "verlet.inc"

; the ground hooks (lib/physics vl_ground)
.macro VL_GROUND_ENTER                  ; (A = 0)
        STA     hold_on,X
.endmacro

; traction (rear wheel only): throttle, no brake (it wins: gas held from the
; keys or button 0 drowned it) and vt < VT_MAX; brake; engine brake (rear
; wheel, no throttle); rolling loss
.macro VL_GROUND_TANGENT
        LDA     cur
        BNE     @nothr
        LDA     in_brake
        BNE     @nothr
        LDY     in_throttle
        BEQ     @nothr
        LDA     vt+1
        BMI     @push
        LDA     vt
        CMP     #<VT_MAX
        LDA     vt+1
        SBC     #>VT_MAX
        BCS     @nothr
@push:  CLC
        LDA     vt
        ADC     thr_acc,Y
        STA     vt
        BCC     @nothr
        INC     vt+1
@nothr: LDA     in_brake
        BEQ     @nobrk
        LDA     vt+1                    ; vt > BRAKE ?
        BMI     @bneg
        LDA     #<BRAKE
        CMP     vt
        LDA     #>BRAKE
        SBC     vt+1
        BCS     @bzero
        SEC
        LDA     vt
        SBC     #<BRAKE
        STA     vt
        LDA     vt+1
        SBC     #>BRAKE
        STA     vt+1
        JMP     @nobrk
@bneg:  LDA     vt                      ; vt < -BRAKE ?
        CMP     #<(-BRAKE)
        LDA     vt+1
        SBC     #>(-BRAKE)
        BCS     @bzero
        CLC
        LDA     vt
        ADC     #<BRAKE
        STA     vt
        LDA     vt+1
        ADC     #>BRAKE
        STA     vt+1
        JMP     @nobrk
@bzero: LDA     #0                      ; stopped: the wheel holds where
        STA     vt                      ; the tick found it (old x, not yet
        STA     vt+1                    ; rewritten; phys_tick)
        LDX     cur
        LDA     pt_oxf,X
        STA     hold_xf,X
        LDA     pt_oxl,X
        STA     hold_xl,X
        LDA     pt_oxh,X
        STA     hold_xh,X
        INC     hold_on,X
@nobrk: LDA     cur                     ; engine brake: rear wheel, no throttle
        BNE     @noeb                   ; (or braking: it cut the throttle)
        LDA     in_brake
        BNE     @eb
        LDA     in_throttle
        BNE     @noeb
@eb:    LDY     #8 - ENGINE_BRAKE
        JSR     vl_damp
@noeb:  LDY     #8 - ROLL_LOSS          ; rolling loss
        JSR     vl_damp
.endmacro

; spokes: angle += low byte of floor(vt / 32); the spin, for the air (X = the
; wheel)
.macro VL_GROUND_AFTER
        LDA     vt+1
        STA     w1
        LDA     vt
        LSR     w1
        ROR     A
        LSR     w1
        ROR     A
        LSR     w1
        ROR     A
        LSR     w1
        ROR     A
        LSR     w1
        ROR     A
        CLC
        ADC     wheel_ang,X
        STA     wheel_ang,X
        LDA     vt
        STA     spin_l,X
        LDA     vt+1
        STA     spin_h,X
.endmacro

; past the line: a lap more, and the camera told
.macro VL_WRAP_AFTER
        INC     laps
        LDA     #1
        STA     wrapped
.endmacro

; generic routines (lib/physics, at the end of the program)
integrate      = vl_integrate
delta_ab       = vl_delta_ab
spin_damp      = vl_pair_damp
phys_wrap      = vl_wrap
do_lean        = vl_turn_pair
do_shift       = vl_shift_point
con_pass       = vl_con_pass
ground_contact = vl_ground
height_at      = vl_height_at


; ---------------------------------------------------------------------------
; phys_reset -- A = start column (< 256): wheels on the ground, rider above
; ---------------------------------------------------------------------------
phys_reset:
        STA     hxl
        LDA     #0
        STA     hxh
        STA     laps
        STA     wrapped
        ; fall through

; phys_place -- the bike at rest, rear wheel at world pixel hxh:hxl, both
; wheels on the ground row there (the game's restart after a crash)
phys_place:
        LDA     hxl
        STA     pt_xl
        LDA     hxh
        STA     pt_xh
        CLC
        LDA     hxl
        ADC     #WHEELBASE
        STA     pt_xl+1
        LDA     hxh
        ADC     #0
        STA     pt_xh+1
        CLC
        LDA     hxl
        ADC     #WHEELBASE/2
        STA     pt_xl+2
        LDA     hxh
        ADC     #0
        STA     pt_xh+2
        LDA     #0
        LDX     #2
@clr:   STA     pt_xf,X
        STA     pt_yf,X
        DEX
        BPL     @clr
        STA     wheel_gnd
        STA     wheel_gnd+1
        STA     wheel_ang
        STA     wheel_ang+1
        STA     spin_l
        STA     spin_l+1
        STA     spin_h
        STA     spin_h+1
        STA     crashed
        STA     flev                    ; (the rider placed in the middle)
        JSR     height_at               ; ground row under the rear wheel
        SEC
        SBC     #6
        STA     pt_yh
        STA     pt_yh+1
        SEC
        SBC     #RIDER_UP
        STA     pt_yh+2
        VL_REST                         ; at rest
        RTS


; ---------------------------------------------------------------------------
; phys_tick
; ---------------------------------------------------------------------------
phys_tick:
        LDX     #2
@int:   JSR     integrate
        DEX
        BPL     @int
        ; the turn: a wheel in the air (last tick's contact) that the brake
        ; stops gives its spin to the frame, 1 a tick (+: rolling forward)
        ; while it still turns; in the air also air_turn - throttle / 8; in the
        ; air or on one wheel the spin of the axis fades
        LDA     #0
        STA     turn
        LDA     in_brake
        BEQ     @nsb
        LDX     #1
@sb:    LDA     wheel_gnd,X             ; down: the brake acts on the ground
        BNE     @snx
        LDA     spin_h,X
        BMI     @sng
        ORA     spin_l,X
        BEQ     @snx                    ; stopped
        SEC                             ; s -= AIR_SPIN_BRAKE, not below 0
        LDA     spin_l,X
        SBC     #<AIR_SPIN_BRAKE
        STA     spin_l,X
        LDA     spin_h,X
        SBC     #>AIR_SPIN_BRAKE
        BPL     @sp
        LDA     #0
        STA     spin_l,X
@sp:    STA     spin_h,X
        INC     turn
        BNE     @snx                    ; (always: turn 1 or 2)
@sng:   CLC                             ; s += AIR_SPIN_BRAKE, not above 0
        LDA     spin_l,X
        ADC     #<AIR_SPIN_BRAKE
        STA     spin_l,X
        LDA     spin_h,X
        ADC     #>AIR_SPIN_BRAKE
        BMI     @sm
        LDA     #0
        STA     spin_l,X
@sm:    STA     spin_h,X
        DEC     turn
@snx:   DEX
        BPL     @sb
@nsb:   LDA     wheel_gnd
        CMP     wheel_gnd+1
        BEQ     @both
        JSR     spin_damp               ; one wheel down
        JMP     @turn
@both:  LDA     wheel_gnd               ; both down: no damping, or the air
        BNE     @turn
        JSR     spin_damp
        LDA     in_throttle
        LSR     A
        LSR     A
        LSR     A
        .assert GYRO_DIV = 8, error, "phys_tick: throttle / GYRO_DIV"
        STA     w0
        CLC                             ; the lean's turn: air_turn (by level)
        LDA     in_lean
        ADC     #LEAN_MAX
        TAY
        CLC
        LDA     turn
        ADC     air_turn,Y
        SEC
        SBC     w0
        STA     turn
@turn:  LDA     turn
        BEQ     @noturn
        JSR     do_lean
@noturn:
        CLC
        LDA     in_lean
        ADC     #LEAN_MAX
        STA     lidx
        LDY     #0                      ; forward of the middle the rider
        LDA     in_lean                 ; moves along the axis (fwd_k:
        BMI     @fw                     ; no speed, no kick)
        TAY
@fw:    LDX     flev
        STY     flev
        LDA     fwd_k,Y
        SEC
        SBC     fwd_k,X
        BEQ     @nosh
        STA     turn                    ; (the multiplier of do_shift)
        JSR     do_shift
@nosh:  LDA     #CONSTRAINT_PASSES
        STA     cpass
@pass:  JSR     con_pass
        DEC     cpass
        BNE     @pass
        LDX     #0
        JSR     ground_contact
        LDX     #1
        JSR     ground_contact
        LDA     #0                      ; the frame again, after the ground
        STA     squashed
        JSR     con_pass
        LDX     #1                      ; a stopped, braked wheel holds (static
@hold:  LDA     hold_on,X               ; friction): x = old x = its x at the
        BEQ     @nohold                 ; tick's start
        LDA     hold_xf,X
        STA     pt_xf,X
        STA     pt_oxf,X
        LDA     hold_xl,X
        STA     pt_xl,X
        STA     pt_oxl,X
        LDA     hold_xh,X
        STA     pt_xh,X
        STA     pt_oxh,X
@nohold:
        DEX
        BPL     @hold
        VL_CEILING                      ; no point above the ceiling
        ; rider hit: y2 + RIDER_HIT > h << 8 (unsigned)
        LDA     pt_xl+2
        STA     hxl
        LDA     pt_xh+2
        STA     hxh
        JSR     height_at
        STA     hgt
        CLC
        LDA     pt_yf+2
        ADC     #<RIDER_HIT
        STA     w0
        LDA     pt_yh+2
        ADC     #>RIDER_HIT
        STA     w1
        LDA     #0
        CMP     w0
        LDA     hgt
        SBC     w1
        BCC     @crash
        LDA     squashed                ; a rider link squashed
        BNE     @crash
        JSR     head_hit                ; the head under the ground
        BCS     @crash
        LDA     wheel_gnd               ; over: a wheel down and the front
        ORA     wheel_gnd+1             ; more than FLIP_DX behind the rear
        BEQ     @alive
        SEC
        LDA     pt_xf+1
        SBC     pt_xf
        LDA     pt_xl+1
        SBC     pt_xl
        BPL     @alive
        CMP     #<(-(FLIP_DX >> 8))
        .assert <FLIP_DX = 0, error, "phys_tick: FLIP_DX whole pixels"
        BCS     @alive                  ; (hi >= -4: not past it)
@crash: LDA     #1
        STA     crashed
@alive: JMP     phys_wrap

; head_hit -- C = 1: the head, at rider + 3 (dy >> 3, -dx >> 3) (wheel
; axis (dx, dy), as drawn), is under the ground: hy > h[hx >> 8] << 8
head_hit:
        LDA     #0
        STA     ca
        LDA     #1
        STA     cb
        JSR     delta_ab
        LDA     dy                      ; hx = x2 + 3 (dy >> 3), 24 bits
        LDX     dy+1
        JSR     times3_8
        CLC
        LDA     pt_xf+2
        ADC     w0
        LDA     pt_xl+2
        ADC     w1
        STA     hxl
        LDA     pt_xh+2
        ADC     w2
        STA     hxh
        LDA     dx                      ; hy = y2 - 3 (dx >> 3), 24 bits
        LDX     dx+1
        JSR     times3_8
        SEC
        LDA     pt_yf+2
        SBC     w0
        STA     w0
        LDA     pt_yh+2
        SBC     w1
        STA     w1
        LDA     #0
        SBC     w2
        BMI     @no                     ; above the screen
        BNE     @yes                    ; (row >= 256)
        JSR     height_at
        CMP     w1                      ; h << 8 < hy ?
        BCC     @yes
        BNE     @no
        LDA     w0
        BEQ     @no
@yes:   SEC
        RTS
@no:    CLC
        RTS

; A/X = signed 16 -> w0, w1, w2 = 3 * (value >> 3) (arithmetic), sign-extended
times3_8:
        STA     w0
        STX     w1
        LDY     #3
@s:     LDA     w1
        CMP     #$80
        ROR     w1
        ROR     w0
        DEY
        BNE     @s
        LDA     w0                      ; 3 t = 2 t + t
        ASL     A
        STA     val
        LDA     w1
        ROL     A
        STA     val+1
        CLC
        LDA     w0
        ADC     val
        STA     w0
        LDA     w1
        ADC     val+1
        STA     w1
        LDA     #0
        BIT     w1
        BPL     @p
        LDA     #$FF
@p:     STA     w2
        RTS



