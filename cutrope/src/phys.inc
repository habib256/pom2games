; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; phys.inc -- CUTROPE's tick: 6502 transcription of tools/cutrope.py
; ============================================================================
; Read tools/cutrope.py first (the model explains the rules; this file only
; follows it, bit for bit: tests/test_cutrope.py compares the two).
;
;   phys_load   lvp = a level record: its points at rest, links, segments,
;               stars, frog, bubble, cushions
;   phys_tick   one tick with in_cut / in_cx / in_cy / in_btn
; ============================================================================

.segment "CODE"

phys_load:
        LDX     #NPTS - 1               ; every point: pinned at (0, CEIL)
@pt:    LDA     #0
        STA     vl_xf,X
        STA     vl_xl,X
        STA     vl_xh,X
        STA     vl_yf,X
        STA     vl_oxf,X
        STA     vl_oxl,X
        STA     vl_oxh,X
        STA     vl_oyf,X
        LDA     #>CEIL
        STA     vl_yh,X
        STA     vl_oyh,X
        LDA     #1
        STA     vl_pin,X
        DEX
        BPL     @pt
        LDY     #0                      ; ropes, the candy, stars, frog
        LDA     (lvp),Y
        STA     cr_nrope
        TAX
        LDA     on_tab,X
        STA     cr_on
        INY
        LDA     (lvp),Y
        STA     vl_xl
        STA     vl_oxl
        INY
        LDA     (lvp),Y
        STA     vl_yh
        STA     vl_oyh
        LDA     #0
        STA     vl_pin
        LDX     #0
@st:    INY
        LDA     (lvp),Y
        STA     star_x,X
        INY
        LDA     (lvp),Y
        STA     star_y,X
        INX
        CPX     #3
        BNE     @st
        INY
        LDA     (lvp),Y
        STA     frog_x
        INY
        LDA     (lvp),Y
        STA     frog_y
        INY
        LDA     (lvp),Y
        STA     cr_nseg
        INY                             ; the bubble, the cushions
        LDA     (lvp),Y
        STA     bub_x
        BEQ     :+
        LDA     #BUB_FREE
:       STA     cr_bub
        INY
        LDA     (lvp),Y
        STA     bub_y
        INY
        LDA     (lvp),Y
        STA     cr_ncush
        LDX     #0
@cu:    CPX     cr_ncush
        BCS     @cud
        INY
        LDA     (lvp),Y
        STA     cu_x,X
        INY
        LDA     (lvp),Y
        STA     cu_y,X
        INY
        LDA     (lvp),Y
        STA     cu_dir,X
        INX
        BNE     @cu
@cud:   INY
        LDA     #1                      ; the ropes: points from 1, links from 0
        STA     cr_p
        LDA     #0
        STA     cr_l
        STA     cr_r
@rope:  LDX     cr_r
        CPX     cr_nrope
        BCC     :+
        JMP     @segs
:       LDA     cr_l
        STA     rope_l0,X
        LDX     cr_p                    ; its pin (pinned)
        LDA     (lvp),Y
        STA     vl_xl,X
        STA     vl_oxl,X
        INY
        LDA     (lvp),Y
        STA     vl_yh,X
        STA     vl_oyh,X
        INY
        LDX     cr_r
        LDA     (lvp),Y                 ; links n
        STA     rope_n,X
        STA     cr_k
        CLC
        ADC     cr_p
        STA     cr_end                  ; the next rope's pin
        INY
        LDA     (lvp),Y                 ; rest length^2
        STA     cr_q
        INY
        LDA     (lvp),Y
        STA     cr_q+1
        INY
        LDX     cr_l                    ; links (p + k, p + k + 1), the last
        LDA     cr_p                    ; one (p + n - 1, 0): the candy
@lk:    STA     vl_con_a,X
        CLC
        ADC     #1
        STA     vl_con_b,X
        PHA
        LDA     cr_q
        STA     vl_con_l2l,X
        LDA     cr_q+1
        STA     vl_con_l2h,X
        PLA
        INX
        DEC     cr_k
        BNE     @lk
        LDA     #0
        STA     vl_con_b-1,X
        STX     cr_l
        LDX     cr_p                    ; the inner points p + 1 .. p + n - 1
@in:    INX
        CPX     cr_end
        BCS     @rdone
        LDA     (lvp),Y
        STA     vl_xf,X
        STA     vl_oxf,X
        INY
        LDA     (lvp),Y
        STA     vl_xl,X
        STA     vl_oxl,X
        INY
        LDA     (lvp),Y
        STA     vl_yf,X
        STA     vl_oyf,X
        INY
        LDA     (lvp),Y
        STA     vl_yh,X
        STA     vl_oyh,X
        INY
        LDA     #0
        STA     vl_pin,X
        BEQ     @in
@rdone: LDA     cr_end
        STA     cr_p
        INC     cr_r
        JMP     @rope
@segs:  LDX     #0                      ; the segments: drawing, kind, the
@sg:    CPX     cr_nseg                 ; vl_sg_* rows
        BCS     @free
        LDA     (lvp),Y
        STA     seg_kind,X
        INY
        LDA     (lvp),Y
        STA     seg_x0,X
        INY
        LDA     (lvp),Y
        STA     seg_y0,X
        INY
        LDA     (lvp),Y
        STA     seg_x1,X
        INY
        LDA     (lvp),Y
        STA     seg_y1,X
        INY
        STX     cr_k
        LDA     #14
        STA     cr_end
@row:   LDA     (lvp),Y
        STA     vl_sg_x0f,X
        INY
        TXA
        CLC
        ADC     #NSEG
        TAX
        DEC     cr_end
        BNE     @row
        LDX     cr_k
        INX
        BNE     @sg
@free:  CPX     #NSEG                   ; the slots left: a box from $FFFF
        BCS     @state
        LDA     #$FF
        STA     vl_sg_bx0l,X
        STA     vl_sg_bx0h,X
        INX
        BNE     @free
@state: LDA     #PLAY
        STA     cr_state
        LDA     #0
.repeat NCUSH, I
        STA     cr_cool+I
.endrepeat
        STA     cr_stars
        STA     cr_nstar
        STA     cr_ev
        STA     vl_gnd
        LDA     #$FF
        STA     vl_sgi
        RTS
.assert vl_sg_by1 = vl_sg_x0f + 13 * NSEG, error, "phys_load: the vl_sg_* rows in the record's order"
.assert 14 * NSEG < 256, error, "phys_load: the vl_sg_* rows indexed by X"

phys_tick:
        LDA     #0
        STA     cr_ev
        LDA     cr_state
        BEQ     :+
        RTS
:       LDX     #0                      ; the cuts: keys, the cursor
@r:     CPX     cr_nrope
        BCS     @go
        LDA     bit_tab,X
        AND     cr_on
        BEQ     @nx
        LDA     bit_tab,X
        AND     in_cut
        BNE     @cut
        LDA     in_btn
        BEQ     @nx
        STX     cr_r
        JSR     near
        LDX     cr_r
        BCC     @nx
@cut:   JSR     cut_rope
@nx:    INX
        BNE     @r
@go:    LDA     cr_bub                  ; the bubble popped: key 6, or the
        CMP     #BUB_CAUGHT             ; button on the candy
        BNE     @cus
        LDA     in_cut
        AND     #M_POP
        BNE     @pop
        LDA     in_btn
        BEQ     @cus
        LDA     vl_xl
        LDY     vl_yh
        LDX     #POP_R
        JSR     cursor_in
        BCC     @cus
@pop:   LDA     #BUB_NONE
        STA     cr_bub
        LDA     cr_ev
        ORA     #EV_POP
        STA     cr_ev
@cus:   LDX     #0                      ; the cushions: waiting, or a puff
@c:     CPX     cr_ncush
        BCS     @int
        LDA     cr_cool,X
        BEQ     :+
        DEC     cr_cool,X
        JMP     @cn
:       LDA     bit_tab+3,X
        AND     in_cut
        BNE     @puff
        LDA     in_btn
        BEQ     @cn
        STX     cr_r
        LDA     cu_x,X
        LDY     cu_y,X
        LDX     #CUSH_R
        JSR     cursor_in
        LDX     cr_r
        BCC     @cn
@puff:  LDA     #PUFF_COOL
        STA     cr_cool,X
        LDA     cr_ev
        ORA     #EV_PUFF
        STA     cr_ev
        STX     cr_r
        JSR     puff
        LDX     cr_r
@cn:    INX
        BNE     @c
@int:   JSR     vl_integrate_all
        LDA     cr_bub                  ; caught: the candy floats
        CMP     #BUB_CAUGHT
        BNE     @lk
        JSR     float
@lk:
.repeat PASSES
        JSR     links
.endrepeat
        JSR     vl_ceiling
        SEC                             ; the candy's vy before the contact
        LDA     vl_yf
        SBC     vl_oyf
        STA     cr_vin
        LDA     vl_yh
        SBC     vl_oyh
        STA     cr_vin+1
        LDX     #0
        JSR     vl_seg_ground
        LDA     vl_gnd                  ; on a trampoline: up at |vin|,
        BEQ     @rules                  ; TRAMP_MIN at least
        LDX     vl_sgi
        LDA     seg_kind,X
        CMP     #SEG_TRAMP
        BNE     @rules
        LDA     cr_vin+1
        BPL     :+
        LDA     #0
        SEC
        SBC     cr_vin
        STA     cr_vin
        LDA     #0
        SBC     cr_vin+1
:       STA     cr_vin+1
        LDA     cr_vin
        CMP     #<TRAMP_MIN
        LDA     cr_vin+1
        SBC     #>TRAMP_MIN
        BCS     :+
        LDA     #<TRAMP_MIN
        STA     cr_vin
        LDA     #>TRAMP_MIN
        STA     cr_vin+1
:       CLC                             ; oy = y + v
        LDA     vl_yf
        ADC     cr_vin
        STA     vl_oyf
        LDA     vl_yh
        ADC     cr_vin+1
        STA     vl_oyh
        LDA     cr_ev
        ORA     #EV_BOING
        STA     cr_ev
@rules: JMP     rules

; the rules: off the field, stars, the frog, spikes
rules:  LDA     vl_xh
        BNE     @off
        LDA     vl_xl
        CMP     #X_MIN
        BCC     @off
        CMP     #X_MAX + 1
        BCS     @off
        LDA     vl_yh
        CMP     #LOST_Y
        BCC     @in
@off:   JMP     @lost
@in:    LDA     cr_bub                  ; the bubble: catches the candy, or
        CMP     #BUB_FREE               ; it has floated away
        BNE     @bc
        LDA     bub_x
        LDY     bub_y
        JSR     within
        BCC     @st
        LDA     #BUB_CAUGHT
        STA     cr_bub
        LDA     cr_ev
        ORA     #EV_CATCH
        STA     cr_ev
        BNE     @st
@bc:    CMP     #BUB_CAUGHT
        BNE     @st
        LDA     vl_yh
        CMP     #BUB_TOP
        BCC     @off
@st:    LDX     #2
@s:     LDA     bit_tab,X
        AND     cr_stars
        BNE     @sn
        LDA     star_x,X
        LDY     star_y,X
        JSR     within
        BCC     @sn
        LDA     bit_tab,X
        ORA     cr_stars
        STA     cr_stars
        INC     cr_nstar
        LDA     cr_ev
        ORA     #EV_STAR
        STA     cr_ev
@sn:    DEX
        BPL     @s
        SEC                             ; the frog's box
        LDA     vl_xl
        SBC     frog_x
        BCC     @sp
        CMP     #FROG_W
        BCS     @sp
        SEC
        LDA     vl_yh
        SBC     frog_y
        BCC     @sp
        CMP     #FROG_W
        BCS     @sp
        LDA     #WON
        STA     cr_state
        LDA     #EV_WON
        BNE     @ev
@sp:    LDA     vl_gnd                  ; a spike segment
        BEQ     @rts
        LDX     vl_sgi
        LDA     seg_kind,X
        CMP     #SEG_SPIKES
        BNE     @rts
@lost:  LDA     #LOST
        STA     cr_state
        LDA     #EV_LOST
@ev:    ORA     cr_ev
        STA     cr_ev
@rts:   RTS

; A, Y = a point (px): C = 1 when the candy's pixel is within STAR_R of it
; (|dx|, |dy| <= R, dx^2 + dy^2 <= R^2). Keeps X.
within: STY     cr_ty
        SEC
        EOR     #$FF                    ; |xl - A|: xl + ~A + 1
        ADC     vl_xl
        BCS     :+
        EOR     #$FF
        ADC     #1                      ; (C = 0)
:       CMP     #STAR_R + 1
        BCS     @no
        TAY
        LDA     sq_tab,Y
        STA     cr_k
        SEC
        LDA     vl_yh
        SBC     cr_ty
        BCS     :+
        EOR     #$FF
        ADC     #1
:       CMP     #STAR_R + 1
        BCS     @no
        TAY
        LDA     sq_tab,Y                ; dx^2 + dy^2 <= R^2
        CLC
        ADC     cr_k
        CMP     #STAR_R * STAR_R + 1    ; (C = 0: within)
        BCS     @no
        SEC
        RTS
@no:    CLC
        RTS

; A, Y = a point (px), X = r: C = 1 when the cursor (in_cx, in_cy) is within
; r of it on both axes
cursor_in:
        STX     cr_k
        STY     cr_ty
        SEC
        SBC     in_cx                   ; |A - cx|
        BCS     :+
        EOR     #$FF
        ADC     #1
:       CMP     cr_k
        BEQ     :+
        BCS     @no
:       SEC
        LDA     cr_ty
        SBC     in_cy
        BCS     :+
        EOR     #$FF
        ADC     #1
:       CMP     cr_k
        BEQ     @yes
        BCS     @no
@yes:   SEC
        RTS
@no:    CLC
        RTS

; X = cushion: its puff, a speed change of the candy when it is ahead
; (along 0 .. PUFF_LEN - 1 px on the axis, |across| <= PUFF_W + along / 4):
; PUFF[along >> 3] on the axis
puff:   LDA     cu_dir,X
        BEQ     @r
        CMP     #2
        BEQ     @l
        BCS     @u
        SEC                             ; D: along = yh - y, across xl - x
        LDA     vl_yh
        SBC     cu_y,X
        BCC     @no
        STA     cr_dx
        LDA     vl_xl
        LDY     cu_x,X
        JMP     @ac
@no:    RTS
@r:     SEC                             ; R: along = xl - x, across yh - y
        LDA     vl_xl
        SBC     cu_x,X
        BCC     @no
        STA     cr_dx
        LDA     vl_yh
        LDY     cu_y,X
        JMP     @ac
@l:     SEC                             ; L: along = x - xl
        LDA     cu_x,X
        SBC     vl_xl
        BCC     @no
        STA     cr_dx
        LDA     vl_yh
        LDY     cu_y,X
        JMP     @ac
@u:     SEC                             ; U: along = y - yh
        LDA     cu_y,X
        SBC     vl_yh
        BCC     @no
        STA     cr_dx
        LDA     vl_xl
        LDY     cu_x,X
@ac:    STY     cr_ty                   ; across = |A - Y|
        SEC
        SBC     cr_ty
        BCS     :+
        EOR     #$FF
        ADC     #1
:       STA     cr_dy
        LDA     cr_dx
        CMP     #PUFF_LEN
        BCS     @no
        LSR     A
        LSR     A
        CLC
        ADC     #PUFF_W
        CMP     cr_dy
        BCC     @no
        LDA     cr_dx
        LSR     A
        LSR     A
        LSR     A
        TAY
        LDA     puff_lo,Y
        STA     vl_val
        LDA     puff_hi,Y
        STA     vl_val+1
        LDA     cu_dir,X
        LDX     #0
        CMP     #1
        BCC     @ax
        BEQ     @ay
        CMP     #2
        BEQ     @sx
        JMP     vl_sub_yv
@ax:    JMP     vl_add_xv
@ay:    JMP     vl_add_yv
@sx:    JMP     vl_sub_xv

; the candy in the bubble: v -= v >> BUB_DRAG on both axes, vy -= BUOY
float:  SEC
        LDA     vl_xf
        SBC     vl_oxf
        STA     vl_val
        LDA     vl_xl
        SBC     vl_oxl
        JSR     drag
        LDX     #0
        JSR     vl_sub_xv
        SEC
        LDA     vl_yf
        SBC     vl_oyf
        STA     vl_val
        LDA     vl_yh
        SBC     vl_oyh
        JSR     drag
        CLC
        LDA     vl_val
        ADC     #<BUOY
        STA     vl_val
        LDA     vl_val+1
        ADC     #>BUOY
        STA     vl_val+1
        LDX     #0
        JMP     vl_sub_yv

; vl_val = (A, vl_val) >> BUB_DRAG, arithmetic (floor)
drag:   LDY     #BUB_DRAG
:       CMP     #$80
        ROR     A
        ROR     vl_val
        DEY
        BNE     :-
        STA     vl_val+1
        RTS

; PASSES of: the links of each rope still on, rope by rope, pin to candy
links:  LDX     #0
@r:     CPX     cr_nrope
        BCS     @rts
        LDA     bit_tab,X
        AND     cr_on
        BEQ     @nx
        STX     cr_r
        LDA     rope_l0,X
        STA     vl_cur
        CLC
        ADC     rope_n,X
        STA     cr_end
@l:     JSR     vl_constrain
        INC     vl_cur
        LDA     vl_cur
        CMP     cr_end
        BNE     @l
        LDX     cr_r
@nx:    INX
        BNE     @r
@rts:   RTS

; X = rope: its points pinned (frozen), the rope off, EV_CUT. Keeps X.
cut_rope:
        LDA     rope_l0,X
        STA     cr_k
        CLC
        ADC     rope_n,X
        STA     cr_end
@l:     LDY     cr_k
        LDA     vl_con_a,Y
        TAY
        LDA     #1
        STA     vl_pin,Y
        INC     cr_k
        LDA     cr_k
        CMP     cr_end
        BNE     @l
        LDA     bit_tab,X
        EOR     #$FF
        AND     cr_on
        STA     cr_on
        LDA     cr_ev
        ORA     #EV_CUT
        STA     cr_ev
        RTS

; X = rope: C = 1 when the cursor (in_cx, in_cy) is within CUT_R of one of
; its links (whole pixels: a box, then |dx uy - dy ux| <= R (|dx| + |dy|))
.assert CUT_R = 2, error, "near: the limit is (|dx| + |dy|) << 1"
near:   LDA     rope_l0,X
        STA     cr_l
        CLC
        ADC     rope_n,X
        STA     cr_end
@lk:    LDX     cr_l
        LDY     vl_con_b,X
        LDA     vl_con_a,X
        TAX                             ; X = a, Y = b
        SEC
        LDA     vl_xl,Y
        SBC     vl_xl,X
        STA     cr_dx
        SEC
        LDA     vl_yh,Y
        SBC     vl_yh,X
        STA     cr_dy
        SEC
        LDA     in_cx
        SBC     vl_xl,X
        STA     cr_ux
        SEC
        LDA     in_cy
        SBC     vl_yh,X
        STA     cr_uy
        LDA     cr_dx
        LDX     cr_ux
        JSR     box
        BCC     @nx
        LDA     cr_dy
        LDX     cr_uy
        JSR     box
        BCS     :+
@nx:    JMP     @next
:
        LDA     cr_dx                   ; c = dx uy
        LDX     cr_uy
        JSR     smul
        LDA     mul_p0
        STA     cr_c
        LDA     mul_p1
        STA     cr_c+1
        LDA     mul_p2
        STA     cr_c+2
        LDA     cr_dy                   ; c -= dy ux
        LDX     cr_ux
        JSR     smul
        SEC
        LDA     cr_c
        SBC     mul_p0
        STA     cr_c
        LDA     cr_c+1
        SBC     mul_p1
        STA     cr_c+1
        LDA     cr_c+2
        SBC     mul_p2
        BPL     :+                      ; |c|
        TAY
        SEC
        LDA     #0
        SBC     cr_c
        STA     cr_c
        LDA     #0
        SBC     cr_c+1
        STA     cr_c+1
        TYA
        EOR     #$FF
        ADC     #0
:       BNE     @next                   ; |c| >= 65536
        LDA     cr_dx                   ; lim = (|dx| + |dy|) << 1
        JSR     sabs
        STA     cr_lim
        LDA     cr_dy
        JSR     sabs
        CLC
        ADC     cr_lim
        STA     cr_lim
        LDA     #0
        ROL     A
        ASL     cr_lim
        ROL     A
        STA     cr_lim+1
        LDA     cr_lim                  ; |c| <= lim
        CMP     cr_c
        LDA     cr_lim+1
        SBC     cr_c+1
        BCS     @hit
@next:  INC     cr_l
        LDA     cr_l
        CMP     cr_end
        BEQ     :+
        JMP     @lk
:       CLC
        RTS
@hit:   SEC
        RTS

; A = d, X = u (signed bytes): C = 1 when u - min(0, d) >= -CUT_R and
; u - max(0, d) <= CUT_R (9-bit differences: the borrow is the sign)
box:    STX     cr_q
        LDX     #0
        TAY
        BPL     :+
        STA     cr_lo
        STX     cr_hi
        JMP     @t
:       STX     cr_lo
        STA     cr_hi
@t:     LDA     cr_q
        EOR     #$80
        STA     cr_q+1                  ; u + 128
        LDA     cr_lo
        EOR     #$80
        STA     cr_k
        SEC
        LDA     cr_q+1
        SBC     cr_k
        BCS     :+                      ; u >= lo
        CMP     #<-CUT_R
        BCC     @no
:       LDA     cr_hi
        EOR     #$80
        STA     cr_k
        SEC
        LDA     cr_q+1
        SBC     cr_k
        BCC     @yes                    ; u < hi
        CMP     #CUT_R + 1
        BCS     @no
@yes:   SEC
        RTS
@no:    CLC
        RTS

; mul_p = A * X, both signed bytes (mul_s16s8, A sign-extended)
smul:   STA     mul_x
        STX     mul_y
        LDX     #0
        CMP     #$80
        BCC     :+
        DEX
:       STX     mul_x+1
        JMP     mul_s16s8

; A = |A| of a signed byte (-128 -> 128)
sabs:   CMP     #$80
        BCC     :+
        EOR     #$FF
        ADC     #0                      ; (C = 1: + 1)
:       RTS

.segment "RODATA"
bit_tab:    .byte 1, 2, 4, 8, 16, 32, 64, 128
on_tab:     .byte 0, 1, 3, 7
sq_tab:     .repeat STAR_R + 1, I
            .byte I * I
            .endrepeat
.segment "BSS"
cr_lo:      .res 1
cr_hi:      .res 1
.segment "CODE"
