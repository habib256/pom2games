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
cidx:       .res 1              ; constraint table index
squashed:   .res 1              ; a rider link too short (pass after the ground)

.segment "CODE"

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
        STA     crashed
        JSR     height_at               ; ground row under the rear wheel
        SEC
        SBC     #6
        STA     pt_yh
        STA     pt_yh+1
        SEC
        SBC     #RIDER_UP
        STA     pt_yh+2
        LDX     #2
@old:   LDA     pt_xf,X
        STA     pt_oxf,X
        LDA     pt_xl,X
        STA     pt_oxl,X
        LDA     pt_xh,X
        STA     pt_oxh,X
        LDA     pt_yf,X
        STA     pt_oyf,X
        LDA     pt_yh,X
        STA     pt_oyh,X
        DEX
        BPL     @old
        RTS

; ---------------------------------------------------------------------------
; height_at -- A = ground row at world pixel hxh:hxl (track_h[x]). Keeps X.
; ---------------------------------------------------------------------------
height_at:
        CLC
        LDA     hxl
        ADC     #<track_h
        STA     tptr
        LDA     hxh
        ADC     #>track_h
        STA     tptr+1
        LDY     #0
        LDA     (tptr),Y
        RTS

; ---------------------------------------------------------------------------
; phys_tick
; ---------------------------------------------------------------------------
phys_tick:
        LDX     #2
@int:   JSR     integrate
        DEX
        BPL     @int
        ; the turn: brake (nose down); in the air also lean - throttle / 8;
        ; in the air or on one wheel (last tick's contact) the spin fades
        LDA     #0
        LDX     in_brake
        BEQ     @nb
        LDA     #GYRO_BRAKE
@nb:    STA     turn
        LDA     wheel_gnd
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
        CLC
        LDA     turn
        ADC     in_lean
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
        LDA     #CONSTRAINT_PASSES
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
        LDX     #2
@ceil:  LDA     pt_yh,X
        CMP     #>CEILING
        BCS     @below
        LDA     #>CEILING
        STA     pt_yh,X
        STA     pt_oyh,X
        LDA     #0
        STA     pt_yf,X
        STA     pt_oyf,X
@below: DEX
        BPL     @ceil
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

; con_pass -- the constraints once, in the model's order
con_pass:
        LDX     #0
@con:   STX     cur
        JSR     constrain
        LDX     cur
        INX
        CPX     #NCONSTRAINTS
        BNE     @con
        RTS

; spin_damp -- the spin of the wheel axis fades: d = (v1 - v0) >> SPIN_DAMP
; (velocities right after integrate: 16 bits), old front += d, old rear -= d
spin_damp:
        SEC                             ; x: d = (x1 - ox1) - (x0 - ox0)
        LDA     pt_xf+1
        SBC     pt_oxf+1
        STA     w0
        LDA     pt_xl+1
        SBC     pt_oxl+1
        STA     w1
        SEC
        LDA     pt_xf
        SBC     pt_oxf
        STA     val
        LDA     pt_xl
        SBC     pt_oxl
        STA     val+1
        SEC
        LDA     w0
        SBC     val
        STA     val
        LDA     w1
        SBC     val+1
        STA     val+1
        JSR     sd_shift
        CLC                             ; ox1 += d (24 bits)
        LDA     pt_oxf+1
        ADC     val
        STA     pt_oxf+1
        LDA     pt_oxl+1
        ADC     val+1
        STA     pt_oxl+1
        LDA     pt_oxh+1
        ADC     w2
        STA     pt_oxh+1
        SEC                             ; ox0 -= d
        LDA     pt_oxf
        SBC     val
        STA     pt_oxf
        LDA     pt_oxl
        SBC     val+1
        STA     pt_oxl
        LDA     pt_oxh
        SBC     w2
        STA     pt_oxh
        SEC                             ; y: d = (y1 - oy1) - (y0 - oy0)
        LDA     pt_yf+1
        SBC     pt_oyf+1
        STA     w0
        LDA     pt_yh+1
        SBC     pt_oyh+1
        STA     w1
        SEC
        LDA     pt_yf
        SBC     pt_oyf
        STA     val
        LDA     pt_yh
        SBC     pt_oyh
        STA     val+1
        SEC
        LDA     w0
        SBC     val
        STA     val
        LDA     w1
        SBC     val+1
        STA     val+1
        JSR     sd_shift
        CLC
        LDA     pt_oyf+1
        ADC     val
        STA     pt_oyf+1
        LDA     pt_oyh+1
        ADC     val+1
        STA     pt_oyh+1
        SEC
        LDA     pt_oyf
        SBC     val
        STA     pt_oyf
        LDA     pt_oyh
        SBC     val+1
        STA     pt_oyh
        RTS

; val >>= SPIN_DAMP (arithmetic), w2 = its sign byte
sd_shift:
        LDY     #SPIN_DAMP
@s:     LDA     val+1
        CMP     #$80
        ROR     val+1
        ROR     val
        DEY
        BNE     @s
        LDA     #0
        BIT     val+1
        BPL     @p
        LDA     #$FF
@p:     STA     w2
        RTS

; ---------------------------------------------------------------------------
; phys_wrap -- a looping track (lap_len > 0) repeats its first pixels after
; lap_len: past lap_len + WRAP_MARGIN the three points move back by lap_len
; (positions and old positions: the physics sees nothing), laps + 1,
; wrapped = 1 for the camera.
; ---------------------------------------------------------------------------
phys_wrap:
        LDA     lap_len
        ORA     lap_len+1
        BEQ     @rts
        CLC
        LDA     lap_len
        ADC     #WRAP_MARGIN
        STA     w0
        LDA     lap_len+1
        ADC     #0
        STA     w1
        LDA     pt_xl
        CMP     w0
        LDA     pt_xh
        SBC     w1
        BCC     @rts
        LDX     #2
@p:     SEC
        LDA     pt_xl,X
        SBC     lap_len
        STA     pt_xl,X
        LDA     pt_xh,X
        SBC     lap_len+1
        STA     pt_xh,X
        SEC
        LDA     pt_oxl,X
        SBC     lap_len
        STA     pt_oxl,X
        LDA     pt_oxh,X
        SBC     lap_len+1
        STA     pt_oxh,X
        DEX
        BPL     @p
        INC     laps
        LDA     #1
        STA     wrapped
@rts:   RTS

.segment "DATA"
lap_len:    .word 0             ; set by the game per track; 0: no loop
.segment "CODE"

; ---------------------------------------------------------------------------
; add / subtract the signed 8.8 `val` to point X (x is 24 bits)
; ---------------------------------------------------------------------------
add_xv: LDY     #0
        LDA     val+1
        BPL     @p
        DEY
@p:     CLC
        LDA     pt_xf,X
        ADC     val
        STA     pt_xf,X
        LDA     pt_xl,X
        ADC     val+1
        STA     pt_xl,X
        TYA
        ADC     pt_xh,X
        STA     pt_xh,X
        RTS

sub_xv: LDY     #0
        LDA     val+1
        BPL     @p
        DEY
@p:     STY     w2
        SEC
        LDA     pt_xf,X
        SBC     val
        STA     pt_xf,X
        LDA     pt_xl,X
        SBC     val+1
        STA     pt_xl,X
        LDA     pt_xh,X
        SBC     w2
        STA     pt_xh,X
        RTS

add_yv: CLC
        LDA     pt_yf,X
        ADC     val
        STA     pt_yf,X
        LDA     pt_yh,X
        ADC     val+1
        STA     pt_yh,X
        RTS

sub_yv: SEC
        LDA     pt_yf,X
        SBC     val
        STA     pt_yf,X
        LDA     pt_yh,X
        SBC     val+1
        STA     pt_yh,X
        RTS

; val = clamp(val, -lim, lim)
.macro CLAMP_VAL lim
        LDA     val+1
        BMI     @neg
        LDA     #<(lim)
        CMP     val
        LDA     #>(lim)
        SBC     val+1
        BCS     @ok
        LDA     #<(lim)
        STA     val
        LDA     #>(lim)
        STA     val+1
@ok:    RTS
@neg:   LDA     val
        CMP     #<(-(lim))
        LDA     val+1
        SBC     #>(-(lim))
        BCS     @ok
        LDA     #<(-(lim))
        STA     val
        LDA     #>(-(lim))
        STA     val+1
        RTS
.endmacro
; vt -= vt >> (8 - Y) (floor), Y = 1..7. Keeps X.
vt_less:
        LDA     vt
        STA     w0
        LDA     vt+1
        STA     w1
        LDA     #0
        BIT     vt+1
        BPL     @p
        LDA     #$FF
@p:     STA     w2
@s:     ASL     w0
        ROL     w1
        ROL     w2
        DEY
        BNE     @s
        SEC
        LDA     vt
        SBC     w1
        STA     vt
        LDA     vt+1
        SBC     w2
        STA     vt+1
        RTS

clamp_vx: CLAMP_VAL VMAX_X
clamp_vy: CLAMP_VAL VMAX_Y

; ---------------------------------------------------------------------------
; integrate -- point X: gravity, clamp, old := pos, pos += v, left wall
; ---------------------------------------------------------------------------
integrate:
        SEC
        LDA     pt_xf,X
        SBC     pt_oxf,X
        STA     val
        LDA     pt_xl,X
        SBC     pt_oxl,X
        STA     val+1
        JSR     clamp_vx
        LDA     val
        STA     vx
        LDA     val+1
        STA     vx+1
        SEC
        LDA     pt_yf,X
        SBC     pt_oyf,X
        STA     val
        LDA     pt_yh,X
        SBC     pt_oyh,X
        STA     val+1
        CLC
        LDA     val
        ADC     #<GRAVITY
        STA     val
        LDA     val+1
        ADC     #>GRAVITY
        STA     val+1
        JSR     clamp_vy                ; val = vy
        LDA     pt_xf,X
        STA     pt_oxf,X
        LDA     pt_xl,X
        STA     pt_oxl,X
        LDA     pt_xh,X
        STA     pt_oxh,X
        LDA     pt_yf,X
        STA     pt_oyf,X
        LDA     pt_yh,X
        STA     pt_oyh,X
        JSR     add_yv
        LDA     vx
        STA     val
        LDA     vx+1
        STA     val+1
        JSR     add_xv
        LDA     pt_xh,X                 ; x < LEFT_WALL ?
        BNE     @ok
        LDA     pt_xl,X
        CMP     #>LEFT_WALL
        BCS     @ok
        LDA     #>LEFT_WALL
        STA     pt_xl,X
        STA     pt_oxl,X
        LDA     #0
        STA     pt_xf,X
        STA     pt_oxf,X
        STA     pt_oxh,X
@ok:    RTS

; dx/dy = point cb - point ca (low 16 bits of x)
delta_ab:
        LDX     cb
        LDY     ca
        SEC
        LDA     pt_xf,X
        SBC     pt_xf,Y
        STA     dx
        LDA     pt_xl,X
        SBC     pt_xl,Y
        STA     dx+1
        SEC
        LDA     pt_yf,X
        SBC     pt_yf,Y
        STA     dy
        LDA     pt_yh,X
        SBC     pt_yh,Y
        STA     dy+1
        RTS

; ---------------------------------------------------------------------------
; do_lean -- turn the axis: front += turn * perp, rear -= turn * perp,
; perp = (-dy, dx)
; ---------------------------------------------------------------------------
do_lean:
        LDA     #0
        STA     ca
        LDA     #1
        STA     cb
        JSR     delta_ab
        SEC                             ; mul_x = -dy
        LDA     #0
        SBC     dy
        STA     mul_x
        LDA     #0
        SBC     dy+1
        STA     mul_x+1
        LDA     turn
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDX     #1
        JSR     add_xv
        LDX     #0
        JSR     sub_xv
        LDA     dx
        STA     mul_x
        LDA     dx+1
        STA     mul_x+1
        LDA     turn
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDX     #1
        JSR     add_yv
        LDX     #0
        JMP     sub_yv

; A/X = 16-bit signed delta (lo/hi) -> A = min(|floor(d / 64)|, 180)
quarter_abs:
        STA     w0
        STX     w1
        LDY     #0
        TXA
        BPL     @p
        DEY
@p:     STY     w2
        ASL     w0
        ROL     w1
        ROL     w2
        ASL     w0
        ROL     w1
        ROL     w2                      ; w2:w1 = floor(d / 64)
        LDA     w2
        BPL     @pos
        SEC
        LDA     #0
        SBC     w1
        STA     w1
        LDA     #0
        SBC     w2
        STA     w2
@pos:   LDA     w2
        BNE     @max
        LDA     w1
        CMP     #181
        BCC     @ok
@max:   LDA     #180
@ok:    RTS

; A = x (0..180) -> A/Y = x^2 (lo/hi) = 4 floor(x^2 / 4) + (x & 1), from the
; quarter-square table (lib/math): ~40 cycles instead of a product
square:
        TAX
        LDA     mul_sqr1_hi,X
        STA     w2
        LDA     mul_sqr1_lo,X
        ASL     A
        ROL     w2
        ASL     A
        ROL     w2
        STA     w0
        TXA
        AND     #1
        ORA     w0
        LDY     w2
        RTS

; ---------------------------------------------------------------------------
; constrain -- constraint `cur`
; ---------------------------------------------------------------------------
constrain:
        LDX     cur
        LDA     con_a,X
        STA     ca
        LDA     con_b,X
        STA     cb
        LDA     con_nl,X                ; cidx = cur * NLEAN + lean + LEAN_MAX
        CLC
        ADC     lidx
        STA     cidx
        JSR     delta_ab
        LDA     dy
        LDX     dy+1
        JSR     quarter_abs
        STA     qx                      ; (qy, kept while qx is squared)
        LDA     dx
        LDX     dx+1
        JSR     quarter_abs
        JSR     square                  ; qx^2 (16 bits)
        STA     pen
        STY     pen+1
        LDA     qx
        JSR     square                  ; qy^2
        LDX     cidx                    ; w = qx^2 + qy^2 - L^2 (24 bits)
        CLC
        ADC     pen
        STA     w0
        TYA
        ADC     pen+1
        STA     w1
        LDA     #0
        ADC     #0
        STA     w2
        LDA     cb                      ; a rider link: squashed below L2Q_MIN?
        CMP     #2
        BNE     @nsq
        LDA     w2
        BNE     @nsq
        LDA     w0
        CMP     #<L2Q_MIN
        LDA     w1
        SBC     #>L2Q_MIN
        BCS     @nsq
        LDA     #1
        STA     squashed
@nsq:   SEC
        LDA     w0
        SBC     con_l2l,X
        STA     w0
        LDA     w1
        SBC     con_l2h,X
        STA     w1
        LDA     w2
        SBC     #0
        STA     w2
        LDY     #3                      ; >> 3, arithmetic
@sh:    LDA     w2
        CMP     #$80
        ROR     w2
        ROR     w1
        ROR     w0
        DEY
        BNE     @sh
        LDA     w2                      ; clamp to +-4095
        BMI     @dneg
        BNE     @dmax
        LDA     w1
        CMP     #$10
        BCC     @dok
@dmax:  LDA     #$FF
        STA     w0
        LDA     #$0F
        STA     w1
        BNE     @dok
@dneg:  CMP     #$FF
        BNE     @dmin
        LDA     w0
        CMP     #$01
        LDA     w1
        SBC     #$F0
        BCS     @dok
@dmin:  LDA     #$01
        STA     w0
        LDA     #$F0
        STA     w1
@dok:   LDA     w0
        STA     mul_x
        LDA     w1
        STA     mul_x+1
        LDA     con_k8,X
        STA     mul_y
        JSR     mul_s16s8               ; f = clamp(prod >> 8, +-127)
        LDA     mul_p2
        BMI     @fneg
        BNE     @fmax
        LDA     mul_p1
        BPL     @fok
@fmax:  LDA     #$7F
        BNE     @fok
@fneg:  CMP     #$FF
        BNE     @fmin
        LDA     mul_p1
        CMP     #$81
        BCS     @fok
@fmin:  LDA     #$81
@fok:   STA     fcoef
        LDA     dx                      ; cx = (dx * f) >> 8
        STA     mul_x
        LDA     dx+1
        STA     mul_x+1
        LDA     fcoef
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDA     cb
        CMP     #2
        BNE     @px
        JSR     heavy                   ; the rider: c - c >> 3, the wheel c + c >> 3
        LDX     ca
        JSR     add_xv
        LDA     vn
        STA     val
        LDA     vn+1
        STA     val+1
@px:    LDX     cb
        JSR     sub_xv
        LDA     cb
        CMP     #2
        BEQ     @cy
        LDX     ca
        JSR     add_xv
@cy:    LDA     dy                      ; cy = (dy * f) >> 8
        STA     mul_x
        LDA     dy+1
        STA     mul_x+1
        LDA     fcoef
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDA     cb
        CMP     #2
        BNE     @py
        JSR     heavy
        LDX     ca
        JSR     add_yv
        LDA     vn
        STA     val
        LDA     vn+1
        STA     val+1
        LDX     cb
        JMP     sub_yv
@py:    LDX     ca
        JSR     add_yv
        LDX     cb
        JMP     sub_yv

; heavy -- a rider link's move c (val): val = c + (c >> RIDER_HEAVY) for the
; wheel, vn = c - (c >> RIDER_HEAVY) for the rider (heavier than a wheel)
heavy:
        LDA     val
        STA     pen
        LDA     val+1
        STA     pen+1
        LDY     #RIDER_HEAVY
@s:     LDA     pen+1
        CMP     #$80
        ROR     pen+1
        ROR     pen
        DEY
        BNE     @s
        SEC
        LDA     val
        SBC     pen
        STA     vn
        LDA     val+1
        SBC     pen+1
        STA     vn+1
        CLC
        LDA     val
        ADC     pen
        STA     val
        LDA     val+1
        ADC     pen+1
        STA     val+1
        RTS

.segment "RODATA"
con_nl: .byte 0, NLEAN, 2 * NLEAN       ; constraint * NLEAN
.segment "CODE"

; ---------------------------------------------------------------------------
; ground_contact -- wheel X (0 rear: traction; 1 front)
; ---------------------------------------------------------------------------
ground_contact:
        STX     cur
        LDA     #0
        STA     wheel_gnd,X
        SEC                             ; ground rows at px - 2, px, px + 2
        LDA     pt_xl,X
        SBC     #2
        STA     hxl
        LDA     pt_xh,X
        SBC     #0
        STA     hxh
        JSR     height_at
        PHA
        CLC
        LDA     hxl
        ADC     #4
        STA     hxl
        BCC     @hx
        INC     hxh
@hx:    JSR     height_at
        PHA
        SEC
        LDA     hxl
        SBC     #2
        STA     hxl
        BCS     @hx2
        DEC     hxh
@hx2:   JSR     height_at
        STA     hgt
        PLA                             ; slope = h[+2] - h[-2], +-SLOPE_MAX
        STA     hp2
        PLA
        STA     hm2
        LDA     hp2
        SEC
        SBC     hm2
        BMI     @sneg
        CMP     #SLOPE_MAX+1
        BCC     @sok
        LDA     #SLOPE_MAX
        BNE     @sok
@sneg:  CMP     #<(-SLOPE_MAX)
        BCS     @sok
        LDA     #<(-SLOPE_MAX)
@sok:   CLC
        ADC     #SLOPE_MAX
        TAY
        LDA     norm_x,Y
        STA     nx
        LDA     norm_y,Y
        STA     ny
        SEC                             ; w = (h << 8) - y, 24 bits
        LDA     #0
        SBC     pt_yf,X
        STA     w0
        LDA     hgt
        SBC     pt_yh,X
        STA     w1
        LDA     #0
        SBC     #0
        STA     w2
        BMI     @wneg
        LDA     w1
        CMP     #>FAR
        BCC     @wok
        RTS                             ; ground far below: no contact
@wneg:  LDA     w1
        CMP     #>(-FAR)
        BCS     @wok
        LDA     #>(-FAR)
        STA     w1
        LDA     #0
        STA     w0
@wok:   SEC                             ; dist = (w * -ny) >> 6
        LDA     #0
        SBC     ny
        TAY
        LDA     w0
        LDX     w1
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p2                   ; dist >= WHEEL_R: no contact
        BMI     @touch
        LDA     mul_p1
        CMP     #<WHEEL_R
        LDA     mul_p2
        SBC     #>WHEEL_R
        BCC     @touch
        RTS
@touch: LDX     cur
        LDA     #1
        STA     wheel_gnd,X
        SEC                             ; pen = WHEEL_R - dist
        LDA     #<WHEEL_R
        SBC     mul_p1
        STA     pen
        LDA     #>WHEEL_R
        SBC     mul_p2
        STA     pen+1
        LDA     pen                     ; x += (pen * nx) >> 6
        LDX     pen+1
        LDY     nx
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDX     cur
        JSR     add_xv
        LDA     pen                     ; y += (pen * ny) >> 6
        LDX     pen+1
        LDY     ny
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDX     cur
        JSR     add_yv
        SEC                             ; v = pos - old
        LDA     pt_xf,X
        SBC     pt_oxf,X
        STA     vx
        LDA     pt_xl,X
        SBC     pt_oxl,X
        STA     vx+1
        SEC
        LDA     pt_yf,X
        SBC     pt_oyf,X
        STA     vy
        LDA     pt_yh,X
        SBC     pt_oyh,X
        STA     vy+1
        ; vn = (vx nx + vy ny) >> 6
        LDA     vx
        LDX     vx+1
        LDY     nx
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vy
        LDX     vy+1
        LDY     ny
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vn
        LDA     mul_p2
        STA     vn+1
        ; vt = (vx (-ny) + vy nx) >> 6
        SEC
        LDA     #0
        SBC     ny
        TAY
        LDA     vx
        LDX     vx+1
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vy
        LDX     vy+1
        LDY     nx
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vt
        LDA     mul_p2
        STA     vt+1
        ; bounce: vn < 0 -> vn = (-vn * BOUNCE) >> 8
        LDA     vn+1
        BPL     @nob
        SEC
        LDA     #0
        SBC     vn
        PHA
        LDA     #0
        SBC     vn+1
        TAX
        PLA
        LDY     #BOUNCE
        JSR     mul_dir
        LDA     mul_p1
        STA     vn
        LDA     mul_p2
        STA     vn+1
@nob:   ; traction (rear wheel only): throttle and vt < VT_MAX
        LDA     cur
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
@bzero: LDA     #0
        STA     vt
        STA     vt+1
@nobrk: LDA     cur                     ; engine brake: rear wheel, no throttle
        ORA     in_throttle
        BNE     @noeb
        LDY     #8 - ENGINE_BRAKE
        JSR     vt_less
@noeb:  LDY     #8 - ROLL_LOSS          ; rolling loss
        JSR     vt_less
        ; vx = (vn nx + vt (-ny)) >> 6
        LDA     vn
        LDX     vn+1
        LDY     nx
        JSR     mul_dir
        JSR     mul_acc_set
        SEC
        LDA     #0
        SBC     ny
        TAY
        LDA     vt
        LDX     vt+1
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     val
        LDA     mul_p2
        STA     val+1
        LDX     cur                     ; old x = x - vx
        LDY     #0
        LDA     val+1
        BPL     @xp
        DEY
@xp:    STY     w2
        SEC
        LDA     pt_xf,X
        SBC     val
        STA     pt_oxf,X
        LDA     pt_xl,X
        SBC     val+1
        STA     pt_oxl,X
        LDA     pt_xh,X
        SBC     w2
        STA     pt_oxh,X
        ; vy = (vn ny + vt nx) >> 6
        LDA     vn
        LDX     vn+1
        LDY     ny
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vt
        LDX     vt+1
        LDY     nx
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDX     cur                     ; old y = y - vy
        SEC
        LDA     pt_yf,X
        SBC     mul_p1
        STA     pt_oyf,X
        LDA     pt_yh,X
        SBC     mul_p2
        STA     pt_oyh,X
        ; spokes: angle += low byte of floor(vt / 32)
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
        RTS
