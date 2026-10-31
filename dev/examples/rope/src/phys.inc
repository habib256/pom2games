; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; phys.inc -- the rope's tick: 6502 transcription of tools/rope.py
; ============================================================================
; Read tools/rope.py first (the model explains the rules; this file only
; follows it, bit for bit: tests/test_rope.py compares the two).
;
;   phys_reset  the rope hanging straight down from the pin at START_X
;   phys_tick   one tick with in_mv / in_mode / in_cut
; ============================================================================

.segment "CODE"

phys_reset:
        LDA     #START_X
        STA     rp_px
        LDA     #PIN_Y0
        STA     rp_py
        LDA     #0
        STA     rp_mode
        STA     rp_cut
        LDX     #VL_NPOINTS - 1
        LDA     #PIN_Y0 + LINK * (VL_NPOINTS - 1)
        STA     rp_k
@p:     LDA     #0
        STA     vl_xf,X
        STA     vl_oxf,X
        STA     vl_xh,X
        STA     vl_oxh,X
        STA     vl_yf,X
        STA     vl_oyf,X
        STA     vl_gnd,X
        STA     vl_pin,X
        LDA     #START_X
        STA     vl_xl,X
        STA     vl_oxl,X
        LDA     rp_k
        STA     vl_yh,X
        STA     vl_oyh,X
        SEC
        SBC     #LINK
        STA     rp_k
        DEX
        BPL     @p
        LDA     #1
        STA     vl_pin
        RTS

phys_tick:
        LDA     rp_cut                  ; reattached: the weight under point 7
        BEQ     @nc
        LDA     in_cut
        BNE     @nc
        LDX     #7
        LDA     vl_xf,X
        STA     vl_xf+8
        STA     vl_oxf+8
        LDA     vl_xl,X
        STA     vl_xl+8
        STA     vl_oxl+8
        LDA     vl_xh,X
        STA     vl_xh+8
        STA     vl_oxh+8
        LDA     vl_yf,X
        STA     vl_yf+8
        STA     vl_oyf+8
        CLC
        LDA     vl_yh,X
        ADC     #LINK
        STA     vl_yh+8
        STA     vl_oyh+8
@nc:    LDA     in_cut
        STA     rp_cut
        LDA     in_mode
        STA     rp_mode
        LDA     in_mv                   ; the pin: x += mv * PIN_SPEED, clamped
        BEQ     @y
        BMI     @l
        CLC
        LDA     rp_px
        ADC     #PIN_SPEED
        CMP     #PIN_X1 + 1
        BCC     @sx
        LDA     #PIN_X1
        BNE     @sx
@l:     SEC
        LDA     rp_px
        SBC     #PIN_SPEED
        BCC     :+
        CMP     #PIN_X0
        BCS     @sx
:       LDA     #PIN_X0
@sx:    STA     rp_px
@y:     LDX     #PIN_Y0                 ; y: a step toward the mode's row
        LDA     rp_mode
        BEQ     :+
        LDX     #PIN_Y1
:       STX     rp_k
        LDA     rp_py
        CMP     rp_k
        BEQ     @pin
        BCS     @up
        ADC     #PIN_STEP               ; (C = 0)
        CMP     rp_k
        BCC     @sy
        LDA     rp_k
        BCS     @sy
@up:    SBC     #PIN_STEP               ; (C = 1)
        BCC     :+
        CMP     rp_k
        BCS     @sy
:       LDA     rp_k
@sy:    STA     rp_py
@pin:   LDA     #0                      ; the pin at rest
        STA     vl_xf
        STA     vl_oxf
        STA     vl_xh
        STA     vl_oxh
        STA     vl_yf
        STA     vl_oyf
        LDA     rp_px
        STA     vl_xl
        STA     vl_oxl
        LDA     rp_py
        STA     vl_yh
        STA     vl_oyh
        JSR     vl_integrate_all
        JSR     links
        JSR     links
        JSR     vl_ceiling
        JSR     walls
        LDX     #VL_NPOINTS - 1         ; the ground: the weight, or 1..8
        LDA     #0
:       STA     vl_gnd,X
        DEX
        BPL     :-
        LDX     #8
        LDA     rp_mode
        BEQ     :+
        LDX     #1
:       STX     rp_k
@g:     LDX     rp_k
        JSR     vl_ground
        INC     rp_k
        LDA     rp_k
        CMP     #VL_NPOINTS
        BCC     @g
        RTS

; a pass of the links: all 8, or 7 when the weight is cut
links:  LDA     rp_cut
        BNE     :+
        JMP     vl_con_pass
:       LDX     #0
@c:     STX     vl_cur
        JSR     vl_constrain
        LDX     vl_cur
        INX
        CPX     #VL_NCON - 1
        BNE     @c
        RTS

; the side walls: x < LEFT_WALL (or < 0) -> LEFT_WALL, x >= RIGHT_WALL (or
; beyond 255) -> RIGHT_WALL, at rest on x (x = ox)
walls:  LDX     #VL_NPOINTS - 1
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
        RTS
