; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; phys.inc -- the lander's tick: 6502 transcription of tools/lander.py
; ============================================================================
; Read tools/lander.py first (the model explains the rules; this file only
; follows it, bit for bit: tests/test_lander.py compares the two).
;
;   phys_reset  the lander at (st_x, st_y: a 16-bit row) with the speed st_vx / st_vy
;   phys_tick   one tick with in_thr / in_rot
;
; ~11,000 cycles a tick in flight (3 integrations, pair damping, 3
; constraint passes, 3 ground probes), +1,000 with the engine, +650 turning.
; ============================================================================

.segment "CODE"

phys_reset:
        LDX     #2
@p:     LDA     #0
        STA     vl_xf,X
        STA     vl_xh,X
        STA     vl_yf,X
        STA     vl_gnd,X
        CLC
        LDA     st_x
        ADC     start_dx,X
        STA     vl_xl,X
        CLC
        LDA     st_y
        ADC     start_dy,X
        STA     vl_yh,X
        LDA     st_y+1
        ADC     start_du,X
        STA     vl_yu,X
        LDY     #0                      ; old = position - speed (24 bits)
        LDA     st_vx+1
        BPL     :+
        DEY
:       STY     vl_w2
        SEC
        LDA     #0
        SBC     st_vx
        STA     vl_oxf,X
        LDA     vl_xl,X
        SBC     st_vx+1
        STA     vl_oxl,X
        LDA     #0
        SBC     vl_w2
        STA     vl_oxh,X
        LDY     #0
        LDA     st_vy+1
        BPL     :+
        DEY
:       STY     vl_w2
        SEC
        LDA     #0
        SBC     st_vy
        STA     vl_oyf,X
        LDA     vl_yh,X
        SBC     st_vy+1
        STA     vl_oyh,X
        LDA     vl_yu,X
        SBC     vl_w2
        STA     vl_oyu,X
        DEX
        BPL     @p
        LDA     #0
        STA     lv_status
        STA     lv_fsub
        STA     lv_settle
        STA     lv_contact
        STA     lv_timer
        STA     lv_pad
        LDA     #FUEL
        STA     lv_fuel
        RTS

start_dx: .byte <-LEG_HALF, LEG_HALF, 0
start_dy: .byte 0, 0, <-TOP_UP
start_du: .byte 0, 0, $FF

phys_tick:
        LDA     lv_status
        BEQ     fly
        CMP     #CRASHED
        BEQ     debris
        RTS                             ; landed: nothing moves

debris:                                 ; the links are broken
        JSR     vl_integrate_all
        JSR     walls
        JSR     grounds
        JSR     vl_ceiling
        LDA     lv_timer
        CMP     #255
        BEQ     :+
        INC     lv_timer
:       RTS

fly:    SEC                             ; vy = speed of the top
        LDA     vl_yf+2
        SBC     vl_oyf+2
        STA     lv_vy
        LDA     vl_yh+2
        SBC     vl_oyh+2
        STA     lv_vy+1
        JSR     vl_integrate_all
        JSR     walls
        JSR     vl_pair_damp
        LDA     in_rot
        BEQ     @nrot
        BMI     @left
        LDA     #ROT_K
        BNE     @turn
@left:  LDA     #<-ROT_K
@turn:  STA     vl_turn
        JSR     vl_turn_pair
@nrot:  LDA     in_thr
        BEQ     @nthr
        LDA     lv_fuel
        BEQ     @nthr
        LDA     #THRUST_K               ; the engine: along the body
        STA     vl_turn
        JSR     vl_thrust_perp
        JSR     vl_push_all
        LDA     lv_fsub
        EOR     #1
        STA     lv_fsub
        BNE     @nthr
        DEC     lv_fuel
@nthr:  JSR     vl_con_pass
        JSR     vl_con_pass
        JSR     grounds
        JSR     vl_con_pass
        JSR     vl_ceiling
        ; --- the rules -----------------------------------------------------
        SEC                             ; tilt = y1 - y0, steep = |tilt| > max
        LDA     vl_yf+1
        SBC     vl_yf
        STA     lv_tilt
        LDA     vl_yh+1
        SBC     vl_yh
        STA     lv_tilt+1
        LDY     #0
        LDX     lv_tilt                 ; X/A = |tilt| (low / high)
        LDA     lv_tilt+1
        BPL     :+
        SEC
        LDA     #0
        SBC     lv_tilt
        TAX
        LDA     #0
        SBC     lv_tilt+1
:       CPX     #<(TILT_MAX + 1)        ; |tilt| >= TILT_MAX + 1 (unsigned)
        SBC     #>(TILT_MAX + 1)
        BCC     :+
        INY
:       STY     lv_steep
        LDA     vl_gnd+2                ; the top on the ground
        BNE     crash
        LDA     vl_gnd
        ORA     vl_gnd+1
        BNE     @touch
        STA     lv_contact              ; (A = 0) in the air
        STA     lv_settle
        RTS
@touch: LDA     lv_contact
        BNE     @was
        LDA     lv_steep                ; first contact: too fast, too tilted
        BNE     crash
        LDA     lv_vy+1                 ; vy > V_SAFE (signed)
        BMI     @was
        LDA     #<V_SAFE
        CMP     lv_vy
        LDA     #>V_SAFE
        SBC     lv_vy+1
        BCC     crash
@was:   LDA     #1
        STA     lv_contact
        LDA     lv_steep
        BNE     crash
        INC     lv_settle
        LDA     lv_settle
        CMP     #SETTLE
        BCC     @rts
        LDX     #0                      ; both legs on the same pad?
        JSR     pad_of
        BEQ     crash
        STA     lv_pad
        LDX     #1
        JSR     pad_of
        CMP     lv_pad
        BNE     crash
        LDA     #LANDED
        STA     lv_status
@rts:   RTS

; the explosion: the links break, each point gets its kick
crash:  LDA     #CRASHED
        STA     lv_status
        LDA     #0
        STA     lv_timer
        STA     lv_pad
        LDX     #2
@k:     LDY     #0                      ; old x -= kick x (24 bits)
        LDA     kick_xh,X
        BPL     :+
        DEY
:       STY     vl_w2
        SEC
        LDA     vl_oxf,X
        SBC     kick_xl,X
        STA     vl_oxf,X
        LDA     vl_oxl,X
        SBC     kick_xh,X
        STA     vl_oxl,X
        LDA     vl_oxh,X
        SBC     vl_w2
        STA     vl_oxh,X
        LDY     #0                      ; old y -= kick y
        LDA     kick_yh,X
        BPL     :+
        DEY
:       STY     vl_w2
        SEC
        LDA     vl_oyf,X
        SBC     kick_yl,X
        STA     vl_oyf,X
        LDA     vl_oyh,X
        SBC     kick_yh,X
        STA     vl_oyh,X
        LDA     vl_oyu,X
        SBC     vl_w2
        STA     vl_oyu,X
        DEX
        BPL     @k
        RTS

; point X's column on a pad -> A = the pad 1..NPADS (Z = 0), or 0 (Z = 1)
pad_of: LDA     vl_xl,X
        LDY     #0
@p:     CMP     pad_x0,Y
        BCC     @n
        CMP     pad_x1,Y
        BEQ     @y
        BCC     @y
@n:     INY
        CPY     #NPADS
        BNE     @p
        LDA     #0
        RTS
@y:     INY
        TYA
        RTS

; the right wall: a point at or past it stops there (x = ox = the wall)
walls:  LDX     #2
@w:     LDA     vl_xl,X
        CMP     #RIGHT_WALL
        BCC     @ok
        LDA     #RIGHT_WALL
        STA     vl_xl,X
        STA     vl_oxl,X
        LDA     #0
        STA     vl_xf,X
        STA     vl_oxf,X
        STA     vl_oxh,X
@ok:    DEX
        BPL     @w
        RTS

grounds:
        LDX     #0
        JSR     vl_ground
        LDX     #1
        JSR     vl_ground
        LDX     #2
        JMP     vl_ground
