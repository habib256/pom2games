; ============================================================================
; tricks.inc -- points for jumps and flips (model: tools/tricks.py)
; ============================================================================
;   trick_reset  race start
;   trick_tick   after each phys_tick: air time, turns, landing, banking
;   trick_bank   bank the waiting points now (the finish)
; The two must agree bit for bit (tests/test_physics.py). Points: AIR_PTS
; per tick of a jump of AIR_MIN ticks or more, FLIP_PTS per full turn
; x turns^2 (8 sectors of 45 degrees of the wheel axis, counted while both wheels
; are off the ground); they wait in pend and are banked after SAFE ticks on
; the wheels -- a crash loses them. A wheelie (rear wheel down, front up) of
; WH_MIN ticks or more pays WH_PTS a tick when it ends. pend (4 digits) and
; score (6) are BCD. A bank shows "FLIP +NNNN" / "JUMP +NNNN" /
; "WHEELIE +NNNN" for TR_MSG_FRAMES frames.
; ============================================================================

AIR_MIN  = 12
SAFE     = 20
WH_MIN   = 15
TR_MSG_W = 13                   ; message width
TR_MSG_FRAMES = 60

.segment "BSS"
score:    .res 3                ; BCD, low byte first
pend:     .res 2                ; BCD
tr_flips: .res 1                ; flips in pend
tr_air:   .res 1
tr_rot:   .res 1                ; signed sectors turned in this jump
tr_sec:   .res 1                ; sector of the wheel axis, 0..7
tr_safe:  .res 1
tr_wh:    .res 1                ; ticks of the wheelie going on
tr_jmp:   .res 1                ; a jump scored in pend (the message)
tr_msgt:  .res 1                ; frames left for the message
tr_t:     .res 1                ; scratch: turns of this jump
.segment "TXT4"
tr_msg:   .res TR_MSG_W + 1     ; "FLIP +1234", 0

.segment "CODE"

trick_reset:
        LDA     #0
        LDX     #tr_jmp - score
@z:     STA     score,X
        DEX
        BPL     @z
        STA     tr_msgt
        RTS

trick_tick:
        LDA     crashed
        BEQ     @alive
        LDA     #0
        STA     pend
        STA     pend+1
        STA     tr_flips
        STA     tr_air
        STA     tr_rot
        STA     tr_wh
        STA     tr_jmp
        RTS
@alive: LDA     #0                      ; the wheel axis: dx, dy
        STA     ca
        LDA     #1
        STA     cb
        JSR     delta_ab
        JSR     tr_octant               ; A = its sector
        TAX
        SEC
        SBC     tr_sec
        AND     #7
        TAY
        STX     tr_sec
        LDA     wheel_gnd+1             ; a wheelie: rear down, front up
        BNE     @wend
        LDA     wheel_gnd
        BEQ     @wend
        INC     tr_wh
        BNE     @wh
        DEC     tr_wh
        BNE     @wh                     ; (always)
@wend:  LDX     tr_wh                   ; it ends: WH_PTS a tick
        CPX     #WH_MIN
        BCC     @wh0
        JSR     tr_add10
@wh0:   LDA     #0
        STA     tr_wh
@wh:    LDA     wheel_gnd
        ORA     wheel_gnd+1
        BNE     @ground
        LDA     tr_step,Y               ; in the air: turn, time
        BEQ     @t
        BMI     @neg
        CLC
        ADC     tr_rot
        BVC     @st
        LDA     #127
        BNE     @st
@neg:   CLC
        ADC     tr_rot
        BVC     @st
        LDA     #<(-128)
@st:    STA     tr_rot
@t:     INC     tr_air
        BNE     @t1
        DEC     tr_air
@t1:    LDA     tr_air
        CMP     #AIR_MIN
        BCC     @rts
        LDA     #0                      ; a real jump: wait again
        STA     tr_safe
@rts:   RTS
@ground:
        LDA     tr_air
        BEQ     @safe
        CMP     #AIR_MIN                ; landing: AIR_PTS a tick...
        BCC     @flips
        TAX
        JSR     tr_add10
        LDA     #1
        STA     tr_jmp
@flips: LDA     tr_rot                  ; ...and FLIP_PTS a turn,
        BPL     @abs                    ; turns = (|rot| + 2) >> 3
        EOR     #$FF
        CLC
        ADC     #1
@abs:   CLC
        ADC     #2
        LSR     A
        LSR     A
        LSR     A
        BEQ     @landed
        STA     tr_t
        CLC
        ADC     tr_flips
        BCC     @f0
        LDA     #255
@f0:    STA     tr_flips
        LDA     #0                      ; FLIP_PTS x flips^2: X = flips^2
        LDX     tr_t                    ; (16 turns: 256 = 0 here, 256 loops:
                                        ;  9999 either way, like the model)
@sq:    CLC
        ADC     tr_t
        DEX
        BNE     @sq
        TAX
        SED
@flip:  CLC
        LDA     pend+1
        ADC     #$10
        STA     pend+1
        BCC     @f1
        LDA     #$99
        STA     pend
        STA     pend+1
@f1:    DEX
        BNE     @flip
        CLD
@landed:
        LDA     #0
        STA     tr_air
        STA     tr_rot
@safe:  INC     tr_safe
        BNE     @s1
        DEC     tr_safe
@s1:    LDA     pend
        ORA     pend+1
        BEQ     @rts2
        LDA     tr_safe
        CMP     #SAFE
        BCS     trick_bank
@rts2:  RTS

; bank pend into score, and the message
trick_bank:
        LDA     pend
        ORA     pend+1
        BEQ     @none
        SED
        CLC
        LDA     score
        ADC     pend
        STA     score
        LDA     score+1
        ADC     pend+1
        STA     score+1
        LDA     score+2
        ADC     #0
        STA     score+2
        CLD
        BCC     @msg
        LDA     #$99                    ; 999999 at most
        STA     score
        STA     score+1
        STA     score+2
@msg:   LDX     #0                      ; "FLIP +", "JUMP +" or "WHEELIE +"
        LDY     #msg_whl - msg_saut
        LDA     tr_jmp
        BEQ     @f
        LDY     #0
@f:     LDA     tr_flips
        BEQ     @w
        LDY     #msg_salto - msg_saut
@w:     LDA     msg_saut,Y
        BEQ     @dig
        STA     tr_msg,X
        INX
        INY
        BNE     @w
@dig:   LDY     #0                      ; 4 digits, no leading zeros
        LDA     pend+1
        JSR     tr_hex2
        LDA     pend
        JSR     tr_hex2
@pad:   LDA     #' '                    ; full width: covers a longer one
        STA     tr_msg,X
        INX
        CPX     #TR_MSG_W
        BCC     @pad
        LDA     #0
        STA     tr_msg,X
        LDA     #TR_MSG_FRAMES
        STA     tr_msgt
@none:  LDA     #0
        STA     pend
        STA     pend+1
        STA     tr_flips
        STA     tr_jmp
        RTS

; pend += 10 x X (BCD, 9999 at most), X > 0. Keeps Y.
tr_add10:
        SED
@a:     CLC
        LDA     pend
        ADC     #$10
        STA     pend
        LDA     pend+1
        ADC     #0
        STA     pend+1
        BCC     @n
        LDA     #$99
        STA     pend
        STA     pend+1
@n:     DEX
        BNE     @a
        CLD
        RTS

; two BCD digits of A into tr_msg,X (Y = 0 while only zeros so far)
tr_hex2:
        PHA
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        JSR     tr_digit
        PLA
        AND     #$0F
tr_digit:
        BNE     @put
        CPY     #0
        BEQ     @skip
@put:   ORA     #'0'
        STA     tr_msg,X
        INX
        LDY     #1
@skip:  RTS

; tr_octant -- A = sector 0..7 of (dx, dy): 0 level, nose right (y down)
tr_octant:
        LDA     dx                      ; val = |dx|, pen = |dy|
        LDX     dx+1
        JSR     tr_abs
        STA     val
        STX     val+1
        LDA     dy
        LDX     dy+1
        JSR     tr_abs
        STA     pen
        STX     pen+1
        LDA     val                     ; C = |dx| >= |dy|
        CMP     pen
        LDA     val+1
        SBC     pen+1
        LDA     dx+1
        BMI     @xneg
        LDA     dy+1
        BMI     @q6
        LDA     #0                      ; dx >= 0, dy >= 0: 0 / 1
        BCS     @r
        LDA     #1
@r:     RTS
@q6:    LDA     #7                      ; dx >= 0, dy < 0: |dy| >= |dx|: 6
        BCC     @r6                     ;  (C clear: |dx| < |dy|)
        BNE     @r
@r6:    LDA     #6
        RTS
@xneg:  LDA     dy+1
        BMI     @q4
        LDA     #3                      ; dx < 0, dy >= 0: |dy| >= |dx|: 2
        BCS     @r
        LDA     #2
        RTS
@q4:    LDA     #4                      ; dx < 0, dy < 0: |dx| >= |dy|: 4
        BCS     @r
        LDA     #5
        RTS

; A/X = 16-bit signed -> A/X = |value|
tr_abs: CPX     #$80
        BCC     @p
        EOR     #$FF
        CLC
        ADC     #1
        PHA
        TXA
        EOR     #$FF
        ADC     #0
        TAX
        PLA
@p:     RTS

.segment "RODATA"
tr_step:   .byte 0, 1, 2, 0, 0, 0, <(-2), <(-1)
msg_saut:  .byte "JUMP +", 0
msg_salto: .byte "FLIP +", 0
msg_whl:   .byte "WHEELIE +", 0
.segment "CODE"
