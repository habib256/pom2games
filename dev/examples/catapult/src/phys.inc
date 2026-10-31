; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; phys.inc -- the catapult's tick: 6502 transcription of tools/catapult.py
; ============================================================================
; Read tools/catapult.py first (the model explains the phases; this file
; only follows it, bit for bit: tests/test_catapult.py compares the two).
;
;   phys_reset  a new round: targets asleep on their boxes, 3 shots, AIM
;   phys_tick   one tick with in_power / in_stop / in_fire
; ============================================================================

.segment "CODE"

phys_reset:
        LDX     #VL_NPOINTS - 1
        LDA     #0
:       STA     vl_xf,X
        STA     vl_oxf,X
        STA     vl_xh,X
        STA     vl_oxh,X
        STA     vl_yf,X
        STA     vl_oyf,X
        STA     vl_pin,X
        DEX
        BPL     :-
        LDX     #VL_CIRC - 1
:       LDA     #RAD
        STA     vl_rad,X
        LDA     #0
        STA     vl_cheavy,X
        STA     vl_still,X
        STA     vl_gnd,X
        DEX
        BPL     :-
        LDA     #1
        STA     vl_cheavy+PROJ
        STA     vl_pin+BASE
        LDA     #BASE_X
        STA     vl_xl+BASE
        STA     vl_oxl+BASE
        LDA     #BASE_Y
        STA     vl_yh+BASE
        STA     vl_oyh+BASE
        LDX     #5                      ; the targets, asleep
:       LDA     tg_xf,X
        STA     vl_xf+1,X
        STA     vl_oxf+1,X
        LDA     tg_xl,X
        STA     vl_xl+1,X
        STA     vl_oxl+1,X
        LDA     tg_yf,X
        STA     vl_yf+1,X
        STA     vl_oyf+1,X
        LDA     tg_yh,X
        STA     vl_yh+1,X
        STA     vl_oyh+1,X
        LDA     #$80
        STA     vl_pin+1,X
        LDA     #0
        STA     cp_down,X
        DEX
        BPL     :-
        LDA     #AIM
        STA     cp_phase
        STA     cp_score
        STA     cp_timer
        STA     cp_timer+1
        STA     cp_power
        LDA     #SHOTS
        STA     cp_shots
        LDA     #2
        STA     cp_stop
        JMP     aim

; the tip and the projectile at rest at the pull angle of cp_power, pinned
aim:    LDX     cp_power
        CLC
        LDA     vl_xf+BASE
        ADC     arm_dxl,X
        STA     vl_xf+TIP
        LDA     vl_xl+BASE
        ADC     arm_dxh,X
        STA     vl_xl+TIP
        LDA     arm_dxh,X               ; (sign of dx)
        AND     #$80
        BEQ     :+
        LDA     #$FF
:       ADC     vl_xh+BASE
        STA     vl_xh+TIP
        CLC
        LDA     vl_yf+BASE
        ADC     arm_dyl,X
        STA     vl_yf+TIP
        LDA     vl_yh+BASE
        ADC     arm_dyh,X
        STA     vl_yh+TIP
        LDX     #TIP
        JSR     rest_x
        JSR     tip_proj
        LDX     #PROJ
        JSR     rest_x
        LDA     #1
        STA     vl_pin+TIP
        STA     vl_pin+PROJ
        LDA     #0
        STA     vl_still+PROJ
        RTS

; point X: old := pos
rest_x: LDA     vl_xf,X
        STA     vl_oxf,X
        LDA     vl_xl,X
        STA     vl_oxl,X
        LDA     vl_xh,X
        STA     vl_oxh,X
        LDA     vl_yf,X
        STA     vl_oyf,X
        LDA     vl_yh,X
        STA     vl_oyh,X
        RTS

; the projectile := the tip (position and old position)
tip_proj:
        LDX     #4
:       LDA     tp_off,X
        TAY
        LDA     vl_xf+TIP,Y
        STA     vl_xf+PROJ,Y
        DEX
        BPL     :-
        LDX     #4
:       LDA     tp_off,X
        TAY
        LDA     vl_oxf+TIP,Y
        STA     vl_oxf+PROJ,Y
        DEX
        BPL     :-
        RTS
tp_off: .byte   0, VL_NPOINTS, 2 * VL_NPOINTS, 3 * VL_NPOINTS, 4 * VL_NPOINTS

phys_tick:
        LDA     cp_phase
        BEQ     ph_aim
        CMP     #SWING
        BEQ     ph_swing
        CMP     #FLY
        BNE     :+
        JMP     ph_fly
:       RTS

ph_aim: LDA     in_power
        STA     cp_power
        LDA     in_stop
        STA     cp_stop
        JSR     aim
        LDA     in_fire
        BEQ     @rts
        LDA     #SWING                  ; fire: the tip free, pushed round
        STA     cp_phase
        LDA     #0
        STA     cp_timer
        STA     cp_timer+1
        STA     vl_pin+TIP
        LDA     cp_power                ; turn = POW0 + power * POW_K
        ASL     A
        ASL     A
        .assert POW_K = 4, error, "phys.inc: POW_K is 4 (two shifts)"
        CLC
        ADC     #POW0
        STA     vl_turn
        JSR     vl_thrust_perp
        LDX     #TIP
        JMP     vl_push
@rts:   RTS

ph_swing:
        JSR     vl_integrate_all
        JSR     vl_con_pass
        JSR     vl_con_pass
        JSR     tip_proj
        INC     cp_timer
        LDA     #BASE                   ; cross = ex sy - ey sx <= 0: let go
        STA     vl_ca
        LDA     #TIP
        STA     vl_cb
        JSR     vl_delta_ab
        LDX     cp_stop
        LDA     vl_dx
        STA     mul_x
        LDA     vl_dx+1
        STA     mul_x+1
        LDA     stop_sy,X
        STA     mul_y
        JSR     mul_s16s8
        LDA     mul_p0
        STA     mul_acc0
        LDA     mul_p1
        STA     mul_acc1
        LDA     mul_p2
        STA     mul_acc2
        LDX     cp_stop
        LDA     vl_dy
        STA     mul_x
        LDA     vl_dy+1
        STA     mul_x+1
        LDA     stop_sx,X
        STA     mul_y
        JSR     mul_s16s8
        SEC
        LDA     mul_acc0
        SBC     mul_p0
        STA     mul_acc0
        LDA     mul_acc1
        SBC     mul_p1
        STA     mul_acc1
        LDA     mul_acc2
        SBC     mul_p2
        BMI     @go                     ; < 0
        ORA     mul_acc0
        ORA     mul_acc1
        BEQ     @go                     ; = 0
        LDA     cp_timer
        CMP     #SWING_MAX
        BCS     @go
        RTS
@go:    LDA     #FLY
        STA     cp_phase
        LDA     #0
        STA     cp_timer
        STA     vl_pin+PROJ
        LDX     cp_stop                 ; the tip stops on its bar, pinned
        CLC
        LDA     vl_xf+BASE
        ADC     stop_dxl,X
        STA     vl_xf+TIP
        LDA     vl_xl+BASE
        ADC     stop_dxh,X
        STA     vl_xl+TIP
        LDA     stop_dxh,X
        AND     #$80
        BEQ     :+
        LDA     #$FF
:       ADC     vl_xh+BASE
        STA     vl_xh+TIP
        CLC
        LDA     vl_yf+BASE
        ADC     stop_dyl,X
        STA     vl_yf+TIP
        LDA     vl_yh+BASE
        ADC     stop_dyh,X
        STA     vl_yh+TIP
        LDX     #TIP
        JSR     rest_x
        LDA     #1
        STA     vl_pin+TIP
        RTS

ph_fly: LDA     #0                      ; (contacts this tick: the game's sound)
        STA     vl_chits
        JSR     vl_integrate_all
        JSR     walls
        LDX     #5                      ; the pins before the contacts
:       LDA     vl_pin+1,X
        STA     cp_was,X
        DEX
        BPL     :-
        JSR     vl_contact_all
        LDA     #0                      ; a target woke: its group
        STA     cp_k
        LDX     #5
:       LDA     cp_was,X
        BEQ     :+
        LDA     vl_pin+1,X
        BNE     :+
        LDA     tg_group,X
        ORA     cp_k
        STA     cp_k
:       DEX
        BPL     :--
        LDX     #5
:       LDA     tg_group,X
        AND     cp_k
        BEQ     :+
        LDA     #0
        STA     vl_pin+1,X
:       DEX
        BPL     :--
@aw:    LDX     #VL_CIRC - 1            ; the awake circles: boxes, ground
        LDA     #0
:       STA     vl_gnd,X
        DEX
        BPL     :-
        LDX     #0
@c:     STX     cp_k
        LDA     vl_pin,X
        BNE     @nc
        JSR     vl_contact_box
        LDX     cp_k
        JSR     vl_ground
@nc:    LDX     cp_k
        INX
        CPX     #VL_CIRC
        BNE     @c
        LDX     #VL_CIRC - 1            ; sleep
:       JSR     vl_circ_sleep
        DEX
        BPL     :-
        LDX     #5                      ; targets CAN_FALL px under their start
@s:     LDA     cp_down,X
        BNE     @ns
        LDA     tg_yh,X
        CLC
        ADC     #CAN_FALL
        STA     cp_k
        LDA     vl_yh+1,X
        CMP     cp_k
        BCC     @ns
        LDA     #1
        STA     cp_down,X
        INC     cp_score
@ns:    DEX
        BPL     @s
        INC     cp_timer
        BNE     :+
        INC     cp_timer+1
:       LDA     cp_score
        CMP     #6
        BEQ     @over
        LDX     #VL_CIRC - 1            ; all asleep?
:       LDA     vl_pin,X
        BEQ     @awake
        DEX
        BPL     :-
        BMI     @end
@awake: LDA     cp_timer                ; or SHOT_MAX ticks
        CMP     #<SHOT_MAX
        LDA     cp_timer+1
        SBC     #>SHOT_MAX
        BCC     @rts
@end:   DEC     cp_shots
        BEQ     @over
        LDA     #AIM
        STA     cp_phase
        JMP     aim
@over:  LDA     #OVER
        STA     cp_phase
@rts:   RTS

; the circles: side walls (x < LEFT_WALL or < 0, x >= RIGHT_WALL or beyond
; 255: x = ox = the wall), then the ceiling (y < CEIL: y = oy = CEIL)
walls:  LDX     #VL_CIRC - 1
@w:     LDA     vl_xh,X
        BEQ     @in
        CMP     #$FF
        BNE     @r
        BEQ     @l
@in:    LDA     vl_xl,X
        CMP     #LEFT_WALL
        BCC     @l
        CMP     #RIGHT_WALL
        BCC     @n
@r:     LDA     #RIGHT_WALL
        BNE     @set
@l:     LDA     #LEFT_WALL
@set:   STA     vl_xl,X
        STA     vl_oxl,X
        LDA     #0
        STA     vl_xf,X
        STA     vl_oxf,X
        STA     vl_xh,X
        STA     vl_oxh,X
@n:     DEX
        BPL     @w
        LDX     #VL_CIRC - 1
@c:     LDA     vl_yh,X
        CMP     #>CEIL
        BCS     :+
        LDA     #>CEIL
        STA     vl_yh,X
        STA     vl_oyh,X
        LDA     #0
        STA     vl_yf,X
        STA     vl_oyf,X
:       DEX
        BPL     @c
        RTS
