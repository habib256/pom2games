; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; phys.inc -- the half-pipe's tick: 6502 transcription of tools/halfpipe.py
; ============================================================================
; Read tools/halfpipe.py first (the model explains the rules; this file only
; follows it, bit for bit: tests/test_halfpipe.py compares the two).
;
;   phys_reset  the rider on the left lip, at rest, score 0
;   phys_again  the same, keeping the score
;   phys_tick   one tick with in_pump / in_lean
; ============================================================================

.segment "CODE"

phys_reset:
        LDA     #0
        STA     hp_score
        STA     hp_score+1
        STA     hp_score+2
phys_again:
        LDX     #2
@p:     LDA     #0
        STA     vl_xf,X
        STA     vl_xh,X
        STA     vl_yf,X
        STA     vl_oxf,X
        STA     vl_oxh,X
        STA     vl_oyf,X
        STA     vl_gnd,X
        LDA     start_x,X
        STA     vl_xl,X
        STA     vl_oxl,X
        LDA     start_y,X
        STA     vl_yh,X
        STA     vl_oyh,X
        LDA     #$FF
        STA     vl_sgi,X
        DEX
        BPL     @p
        LDA     #0
        STA     hp_status
        STA     hp_timer
        STA     hp_air
        STA     hp_rot
        STA     hp_spins
        STA     hp_last
        STA     hp_last+1
        STA     hp_add
        STA     hp_pumping
        LDA     #START_OCT
        STA     hp_oct
        LDA     #$FF
        STA     hp_peak
        RTS

phys_tick:
        LDA     hp_status
        BEQ     ride
        LDA     #0                      ; crashed: the links are broken
        STA     hp_pumping
        JSR     vl_integrate_all
        JSR     grounds
        JSR     vl_ceiling
        LDA     hp_timer
        CMP     #255
        BEQ     :+
        INC     hp_timer
:       RTS

ride:   LDA     in_pump
        STA     hp_pumping
        JSR     vl_integrate_all
        LDA     hp_air
        BEQ     @nair
        JSR     vl_pair_damp            ; in the air: the spin fades,
        LDA     in_lean                 ; lean turns
        BEQ     @nair
        BMI     @left
        LDA     #ROT_K
        BNE     @turn
@left:  LDA     #<-ROT_K
@turn:  STA     vl_turn
        JSR     vl_turn_pair
@nair:  JSR     vl_con_pass
        JSR     vl_con_pass
        JSR     grounds
        JSR     vl_con_pass
        JSR     vl_ceiling
        ; --- the rules -----------------------------------------------------
        LDA     vl_gnd+2                ; the body on the pipe
        BEQ     :+
        JMP     crash
:       LDA     vl_gnd
        ORA     vl_gnd+1
        BNE     @down
        LDA     hp_air                  ; in the air
        CMP     #255
        BEQ     :+
        INC     hp_air
:       JSR     octant
        PHA
        SEC                             ; rot += ((o - oct + 4) & 7) - 4
        SBC     hp_oct
        CLC
        ADC     #4
        AND     #7
        SEC
        SBC     #4
        CLC
        ADC     hp_rot
        STA     hp_rot
        PLA
        STA     hp_oct
        LDA     vl_yh+2                 ; the highest row of the body
        CMP     hp_peak
        BCS     :+
        STA     hp_peak
:       RTS
@down:  LDA     hp_air
        CMP     #AIR_MIN
        BCC     @reset
        LDX     #0                      ; a landing: on wheel 0 if it is down
        LDA     vl_gnd
        BNE     :+
        INX
:       JSR     upright
        BPL     :+
        JMP     crash
:       LDA     hp_peak                 ; not above the lip: no trick
        CMP     #LIP_Y
        BCS     @reset
        LDA     hp_rot                  ; spins = (|rot| + 4) >> 3
        BPL     :+
        EOR     #$FF
        CLC
        ADC     #1
:       CLC
        ADC     #4
        LSR     A
        LSR     A
        LSR     A
        STA     hp_spins
        CMP     #10                     ; last = 100 min(spins, 9) +
        BCC     :+
        LDA     #9
:       STA     hp_last+1
        LDA     hp_air                  ;        10 min(air >> 4, 9) (BCD)
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        CMP     #10
        BCC     :+
        LDA     #9
:       ASL     A
        ASL     A
        ASL     A
        ASL     A
        STA     hp_last
        LDA     #<hp_score
        STA     bcd_ptr
        LDA     #>hp_score
        STA     bcd_ptr+1
        LDA     #<hp_last
        LDY     #>hp_last
        LDX     #3
        JSR     bcd_add_sat
@reset: LDA     #0
        STA     hp_air
        STA     hp_rot
        JSR     octant
        STA     hp_oct
        LDA     #$FF
        STA     hp_peak
        RTS

crash:  LDA     #CRASHED
        STA     hp_status
        LDA     #0
        STA     hp_timer
        LDX     #2                      ; the kicks: old -= kick
@k:     LDY     #0
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
        SEC
        LDA     vl_oyf,X
        SBC     kick_yl,X
        STA     vl_oyf,X
        LDA     vl_oyh,X
        SBC     kick_yh,X
        STA     vl_oyh,X
        DEX
        BPL     @k
        RTS

grounds:
        LDX     #0
        JSR     vl_seg_ground
        LDX     #1
        JSR     vl_seg_ground
        LDX     #2
        JMP     vl_seg_ground

; A = the octant 0..7 of the wheels' axis (vl_dx, vl_dy = point 1 - point 0):
; g = |dx| > |dy|; dy >= 0: dx >= 0 -> 1 - g, else 2 + g; dy < 0: dx < 0 ->
; 5 - g, else 6 + g
octant: LDA     #0
        STA     vl_ca
        LDA     #1
        STA     vl_cb
        JSR     vl_delta_ab
        LDA     vl_dx                   ; |dx| -> vl_val
        LDX     vl_dx+1
        BPL     :+
        EOR     #$FF
        CLC
        ADC     #1
        PHA
        TXA
        EOR     #$FF
        ADC     #0
        TAX
        PLA
:       STA     vl_val
        STX     vl_val+1
        LDA     vl_dy                   ; |dy| -> vl_vx
        LDX     vl_dy+1
        BPL     :+
        EOR     #$FF
        CLC
        ADC     #1
        PHA
        TXA
        EOR     #$FF
        ADC     #0
        TAX
        PLA
:       STA     vl_vx
        STX     vl_vx+1
        LDY     #0                      ; Y = g: |dy| - |dx| borrows
        LDA     vl_vx
        CMP     vl_val
        LDA     vl_vx+1
        SBC     vl_val+1
        BCS     :+
        INY
:       STY     vl_w0
        LDA     vl_dy+1
        BMI     @up
        LDA     vl_dx+1
        BMI     @q2
        LDA     #1                      ; 1 - g
        SEC
        SBC     vl_w0
        RTS
@q2:    LDA     #2                      ; 2 + g
        CLC
        ADC     vl_w0
        RTS
@up:    LDA     vl_dx+1
        BPL     @q4
        LDA     #5                      ; 5 - g
        SEC
        SBC     vl_w0
        RTS
@q4:    LDA     #6                      ; 6 + g
        CLC
        ADC     vl_w0
        RTS

; X = the wheel down: N = 1 if the body is less than LAND_MIN along the
; normal of its segment: (bx nx + by ny) >> 6 < LAND_MIN, b = body - wheel
upright:
        STX     vl_ca
        LDA     #2
        STA     vl_cb
        JSR     vl_delta_ab
        LDX     vl_ca
        LDY     vl_sgi,X
        LDA     vl_sg_ny,Y
        STA     vl_ny
        LDA     vl_sg_nx,Y
        TAY
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     mul_dir
        JSR     mul_acc_set
        LDY     vl_ny
        LDA     vl_dy
        LDX     vl_dy+1
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1                  ; dot - LAND_MIN, signed
        CMP     #<LAND_MIN
        LDA     mul_p2
        SBC     #>LAND_MIN
        BVC     :+
        EOR     #$80
:       ORA     #0                      ; (N = the sign)
        RTS
