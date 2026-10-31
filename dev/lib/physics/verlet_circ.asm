; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet_circ.asm -- lib/physics: circle contacts (point pairs, static boxes)
; ============================================================================
; Include at the END, FIRST of the verlet_*.asm (before verlet_hmap.asm,
; verlet_con.asm -- vl_square --, verlet_rot.asm, verlet.asm), then sqrt.asm
; (isqrt16: call sqrt_init at start) and mul.asm (MUL_ACC = 1).
; dev/tools/verlet/contact.py is the reference, bit for bit.
;
; The points 0..VL_CIRC-1 are circles of radius vl_rad,X (BSS, set by the
; program) in units of 2^VL_CIRC_Q / 256 px (Q = 5, the default: 1/8 px; 4:
; 1/16; 6: 1/4); two radii add up to 127 units at most (Q = 5: 15.9 px).
;
;   vl_contact_pair  A = R (radii sum), points vl_ca, vl_cb. C = 1 in contact.
;                    |d| per axis (x 24 bits, y 17 / 24 bits), q = |d| >> Q,
;                    q2 = qx^2 + qy^2 < R^2: s = isqrt16(q2), pen = R - s, the
;                    normal n = q * ceil(2^14 / s) >> 8 (64 = 1.0; s = 0:
;                    (0, -64)); each point and its old position move by half
;                    of (pen |n|) >> (6 - Q) along n (no speed from the push);
;                    a closing normal speed vn = (v_b - v_a) . n >> 6 < 0 gets
;                    the impulse j = m + (m e >> 8), m = -vn (m > VL_CIRC_VMIN,
;                    e = VL_CIRC_BOUNCE; else j = m), half each, through the
;                    old positions. Pins (VL_PIN): a pinned point does not move,
;                    the other takes all; both pinned: no contact.
;                    VL_CIRC_HEAVY = n: vl_cheavy,X non-zero marks heavy points;
;                    a heavy point against a light one takes half - half >> n
;                    of each share (the VL_CON_HEAVY rule).
;                    VL_CIRC_SLEEP = v (VL_PIN): vl_pin,X = $80 is a sleeping point,
;                    pinned in a pair until a closing speed > v wakes it (pin 0).
;   vl_circ_sleep    X = point (VL_CIRC_SLEEP): free and |vx|, |vy| <= v for
;                    VL_CIRC_SLEEP_TICKS (16) ticks in a row (vl_still,X counts):
;                    asleep (vl_pin,X = $80, at rest; C = 1). Keeps X. The
;                    program skips vl_ground / its own code for pinned points
;                    (vl_integrate, vl_contact_box already do).
;   vl_contact_all   every pair a < b of the VL_CIRC points, both radii non-zero
;                    (radius 0: not a circle); vl_chits += the contacts.
;   vl_contact_box   X = point: against the VL_NBOX static boxes vl_box_x0,
;                    vl_box_y0, vl_box_x1, vl_box_y1 (program tables, whole px,
;                    edges included; the point at x < 256 px, y < 256 rows):
;                    the closest point of each box, the same q, s, pen, n, the
;                    whole push to the point; the centre inside (or within a
;                    unit: s = 0): out through the nearest face (top, left,
;                    right, bottom first on ties) to exactly r from it. The
;                    speed splits into vn, vt (like vl_ground), a closing vn
;                    bounces (m > VL_CIRC_VMIN: (m e) >> 8, else 0), VL_CIRC_
;                    FRICTION = f: vt -= vt >> f (vl_damp), then old = pos - v.
;                    C = 1 in contact (vl_chits += the boxes touched). Keeps X.
;                    A pinned point or radius 0: nothing.
;
; Parameters: VL_CIRC (1..VL_NPOINTS), VL_CIRC_Q (4..6, 5), VL_CIRC_BOUNCE
; (0..255 / 256, 0), VL_CIRC_VMIN (8.8, 0), VL_CIRC_HEAVY (shift 1..7, off),
; VL_CIRC_FRICTION (1..7, off), VL_CIRC_SLEEP (8.8 speed, off; VL_PIN),
; VL_CIRC_SLEEP_TICKS (16), VL_NBOX (for vl_contact_box).
; Velocities: keep |VMAX| <= $2000 (8 px a tick) so that vn fits 16 bits.
; ============================================================================

.ifndef _VERLET_CIRC_ASM_LOADED_
_VERLET_CIRC_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet_circ.asm: include verlet.inc at the top first"
.endif

.segment "CODE"

.if .referenced(vl_contact_pair) .or .referenced(vl_contact_all) .or .referenced(vl_contact_box)
.ifndef VL_CIRC
.error "vl_contact_*: define VL_CIRC (the circle points) before verlet.inc"
.endif
.assert MUL_ACC, error, "vl_contact_*: needs MUL_ACC = 1 (lib/math)"
.ifndef VL_CIRC_Q
VL_CIRC_Q = 5
.endif
.assert VL_CIRC_Q >= 4 .and VL_CIRC_Q <= 6, error, "VL_CIRC_Q is 4..6"
.ifndef VL_CIRC_BOUNCE
VL_CIRC_BOUNCE = 0
.endif
.assert VL_CIRC_BOUNCE >= 0 .and VL_CIRC_BOUNCE <= 255, error, "VL_CIRC_BOUNCE is 0..255"
.ifndef VL_CIRC_VMIN
VL_CIRC_VMIN = 0
.endif
.ifdef VL_CIRC_HEAVY
.assert VL_CIRC_HEAVY >= 1 .and VL_CIRC_HEAVY <= 7, error, "VL_CIRC_HEAVY is 1..7"
.endif
.ifdef VL_CIRC_SLEEP
.ifndef VL_PIN
.error "VL_CIRC_SLEEP: the sleeping points are pinned ($80): define VL_PIN"
.endif
.assert VL_CIRC_SLEEP >= 1 .and VL_CIRC_SLEEP < $8000, error, "VL_CIRC_SLEEP is a speed (8.8) 1..$7FFF"
.endif
.ifdef VL_CIRC_FRICTION
.assert VL_CIRC_FRICTION >= 1 .and VL_CIRC_FRICTION <= 7, error, "VL_CIRC_FRICTION is 1..7"
.endif
_VL_COFF = vl_oxf - vl_xf               ; a point's old position: X + _VL_COFF
.assert vl_oxf - vl_xf = vl_oyf - vl_yf, error, "verlet_circ: vl_ox*, vl_oy* at the same offset from vl_x*, vl_y*"
.assert VL_NPOINTS - 1 + _VL_COFF < 256, error, "verlet_circ: old points out of X range"
_VL_CQLIM = 1 << (VL_CIRC_Q - 1)        ; |d| hi byte >= this: q >= 128
.endif

; ----------------------------------------------------------------------------
.ifref vl_contact_all
vl_contact_all:
.if VL_CIRC >= 2
        LDX     #0
@a:     STX     vl_ca
        LDA     vl_rad,X
        BEQ     @na
        INX
@b:     STX     vl_cb
        LDA     vl_rad,X
        BEQ     @nb
        LDY     vl_ca
        CLC
        ADC     vl_rad,Y
        JSR     vl_contact_pair
        BCC     @nb
        INC     vl_chits
@nb:    LDX     vl_cb
        INX
        CPX     #VL_CIRC
        BNE     @b
@na:    LDX     vl_ca
        INX
        CPX     #VL_CIRC - 1
        BNE     @a
.endif
        RTS
.endif

; ----------------------------------------------------------------------------
.ifref vl_contact_box
.ifndef VL_NBOX
.error "vl_contact_box: define VL_NBOX (and the vl_box_x0/y0/x1/y1 tables)"
.endif
vl_contact_box:
        STX     vl_cur
        LDA     vl_rad,X
        BEQ     @none
        STA     vl_crad
.ifdef VL_PIN
        LDA     vl_pin,X
        BNE     @none
.endif
        LDA     vl_xh,X                 ; x < 256 px, y < 256 rows
        BNE     @none
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        BNE     @none
.endif
        LDA     #0
        STA     vl_cb                   ; boxes touched
        TAY
@k:     STY     vl_ca
        JSR     vl_cbox1
        BCC     @n
        INC     vl_cb
        INC     vl_chits
@n:     LDY     vl_ca
        INY
        CPY     #VL_NBOX
        BNE     @k
        LDX     vl_cur
        LDA     vl_cb
        CMP     #1                      ; C = 1: a contact
        RTS
@none:  CLC
        RTS

; point vl_cur (radius vl_crad) against box Y = vl_ca -> C = 1 in contact
vl_cbox1:
        LDX     vl_cur
        LDA     #0
        STA     vl_csgn
        STA     vl_qx
        STA     vl_qy
        LDA     vl_xl,X                 ; x side: left of x0, right of x1
        CMP     vl_box_x0,Y
        BCC     @xl
        LDA     vl_box_x1,Y
        CMP     vl_xl,X
        BCC     @xr
        BNE     @xin
        LDA     vl_xf,X
        BEQ     @xin
@xr:    LDA     vl_xf,X                 ; |d| = x - x1
        STA     vl_w0
        SEC
        LDA     vl_xl,X
        SBC     vl_box_x1,Y
        LDX     #$02
        BNE     @xq
@xl:    SEC                             ; |d| = x0 - x
        LDA     #0
        SBC     vl_xf,X
        STA     vl_w0
        LDA     vl_box_x0,Y
        SBC     vl_xl,X
        LDX     #$82
@xq:    STX     vl_csgn
        CMP     #_VL_CQLIM
        BCS     @no
.repeat 8 - VL_CIRC_Q
        ASL     vl_w0
        ROL     A
.endrepeat
        CMP     vl_crad
        BCS     @no
        STA     vl_qx
        LDX     vl_cur
@xin:   LDA     vl_yh,X                 ; y side: above y0, below y1
        CMP     vl_box_y0,Y
        BCC     @yt
        LDA     vl_box_y1,Y
        CMP     vl_yh,X
        BCC     @yb
        BNE     @yin
        LDA     vl_yf,X
        BEQ     @yin
@yb:    LDA     vl_yf,X
        STA     vl_w0
        SEC
        LDA     vl_yh,X
        SBC     vl_box_y1,Y
        LDX     #$01
        BNE     @yq
@yt:    SEC
        LDA     #0
        SBC     vl_yf,X
        STA     vl_w0
        LDA     vl_box_y0,Y
        SBC     vl_yh,X
        LDX     #$41
@yq:    PHA
        TXA
        ORA     vl_csgn
        STA     vl_csgn
        PLA
        CMP     #_VL_CQLIM
        BCS     @no
.repeat 8 - VL_CIRC_Q
        ASL     vl_w0
        ROL     A
.endrepeat
        CMP     vl_crad
        BCS     @no
        STA     vl_qy
@yin:   JSR     vl_cnorm
        BCC     @hit
@no:    CLC
        RTS
@hit:   BEQ     @face
        JSR     vl_csigned              ; the whole push to the point
        LDA     vl_cnx
        JSR     vl_cpent
        LDX     vl_cur
        BIT     vl_csgn
        BMI     :+
        JSR     vl_cadd_x2
        JMP     :++
:       JSR     vl_csub_x2
:       LDA     vl_cny
        JSR     vl_cpent
        LDX     vl_cur
        BIT     vl_csgn
        BVS     :+
        JSR     vl_cadd_y2
        JMP     vl_cbvel
:       JSR     vl_csub_y2
        JMP     vl_cbvel

; s = 0: out through a face, to exactly r from it
@face:  LDA     vl_crad                 ; vl_vx = r << Q
        STA     vl_vx
        LDA     #0
.repeat VL_CIRC_Q
        ASL     vl_vx
        ROL     A
.endrepeat
        STA     vl_vx+1
        LDX     vl_cur
        LDY     vl_ca
        LDA     vl_csgn
        AND     #$03
        BNE     @fout
        LDA     vl_yf,X                 ; inside: the nearest face
        STA     vl_pen                  ; (vl_pen: the best depth, vl_qx: face)
        SEC
        LDA     vl_yh,X
        SBC     vl_box_y0,Y
        STA     vl_pen+1
        LDA     vl_xf,X                 ; left: x - x0
        STA     vl_cj
        SEC
        LDA     vl_xl,X
        SBC     vl_box_x0,Y
        STA     vl_cj+1
        LDA     #1
        JSR     vl_cmin
        SEC                             ; right: x1 - x
        LDA     #0
        SBC     vl_xf,X
        STA     vl_cj
        LDA     vl_box_x1,Y
        SBC     vl_xl,X
        STA     vl_cj+1
        LDA     #2
        JSR     vl_cmin
        SEC                             ; bottom: y1 - y
        LDA     #0
        SBC     vl_yf,X
        STA     vl_cj
        LDA     vl_box_y1,Y
        SBC     vl_yh,X
        STA     vl_cj+1
        LDA     #3
        JSR     vl_cmin
        LDA     vl_qx
        JMP     @fsel
@fout:  LDA     #0                      ; outside, within a unit
        BIT     vl_csgn
        BVS     @fsel                   ; above: top
        LDA     #1
        BIT     vl_csgn
        BMI     @fsel                   ; left
        LDA     vl_csgn
        LSR     A
        LSR     A
        LDA     #2                      ; right (x outside)
        BCS     @fsel
        LDA     #3
@fsel:  CMP     #1
        BEQ     @fl
        BCC     @ft
        CMP     #2
        BEQ     @fr
        CLC                             ; bottom: y = y1 + r
        LDA     #0
        ADC     vl_vx
        STA     vl_val
        LDA     vl_box_y1,Y
        ADC     vl_vx+1
        STA     vl_val+1
        LDA     #0
        LDY     #$00
        BEQ     @fy
@ft:    SEC                             ; top: y = y0 - r
        LDA     #0
        SBC     vl_vx
        STA     vl_val
        LDA     vl_box_y0,Y
        SBC     vl_vx+1
        STA     vl_val+1
        LDA     #0
        LDY     #$40
@fy:    STA     vl_cnx
        STY     vl_csgn
        LDA     #64
        STA     vl_cny
        SEC                             ; val -= y (16 bits)
        LDA     vl_val
        SBC     vl_yf,X
        STA     vl_val
        LDA     vl_val+1
        SBC     vl_yh,X
        STA     vl_val+1
        JSR     vl_cadd_y2
        JMP     @fn
@fr:    CLC                             ; right: x = x1 + r
        LDA     #0
        ADC     vl_vx
        STA     vl_val
        LDA     vl_box_x1,Y
        ADC     vl_vx+1
        STA     vl_val+1
        LDY     #$00
        BEQ     @fx
@fl:    SEC                             ; left: x = x0 - r
        LDA     #0
        SBC     vl_vx
        STA     vl_val
        LDA     vl_box_x0,Y
        SBC     vl_vx+1
        STA     vl_val+1
        LDY     #$80
@fx:    STY     vl_csgn
        LDA     #64
        STA     vl_cnx
        LDA     #0
        STA     vl_cny
        SEC
        LDA     vl_val
        SBC     vl_xf,X
        STA     vl_val
        LDA     vl_val+1
        SBC     vl_xl,X
        STA     vl_val+1
        JSR     vl_cadd_x2
@fn:    JSR     vl_csigned
        ; (falls into vl_cbvel)

; the point's speed: vn, vt on the normal, bounce, friction, rebuilt
vl_cbvel:
        LDX     vl_cur
        SEC                             ; v = pos - old
        LDA     vl_xf,X
        SBC     vl_oxf,X
        STA     vl_vx
        LDA     vl_xl,X
        SBC     vl_oxl,X
        STA     vl_vx+1
        SEC
        LDA     vl_yf,X
        SBC     vl_oyf,X
        STA     vl_vy
        LDA     vl_yh,X
        SBC     vl_oyh,X
        STA     vl_vy+1
        LDA     vl_vx                   ; vn = (vx nx + vy ny) >> 6
        LDX     vl_vx+1
        LDY     vl_csnx
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vl_vy
        LDX     vl_vy+1
        LDY     vl_csny
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vl_vn
        LDA     mul_p2
        STA     vl_vn+1
        SEC                             ; vt = (vx (-ny) + vy nx) >> 6
        LDA     #0
        SBC     vl_csny
        TAY
        LDA     vl_vx
        LDX     vl_vx+1
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vl_vy
        LDX     vl_vy+1
        LDY     vl_csnx
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vl_vt
        LDA     mul_p2
        STA     vl_vt+1
        LDA     vl_vn+1                 ; closing: bounce or stop
        BPL     @nob
        SEC
        LDA     #0
        SBC     vl_vn
        STA     mul_x
        LDA     #0
        SBC     vl_vn+1
        STA     mul_x+1
.if VL_CIRC_BOUNCE > 0
        LDA     #<VL_CIRC_VMIN          ; m > vmin: vn = (m e) >> 8
        CMP     mul_x
        LDA     #>VL_CIRC_VMIN
        SBC     mul_x+1
        BCS     @stop
        MUL_K16 VL_CIRC_BOUNCE
        LDA     mul_p1
        STA     vl_vn
        LDA     mul_p2
        STA     vl_vn+1
        JMP     @nob
@stop:
.endif
        LDA     #0
        STA     vl_vn
        STA     vl_vn+1
@nob:
.ifdef VL_CIRC_FRICTION
        LDY     #8 - VL_CIRC_FRICTION
        JSR     vl_damp
.endif
        LDA     vl_vn                   ; vx = (vn nx + vt (-ny)) >> 6
        LDX     vl_vn+1
        LDY     vl_csnx
        JSR     mul_dir
        JSR     mul_acc_set
        SEC
        LDA     #0
        SBC     vl_csny
        TAY
        LDA     vl_vt
        LDX     vl_vt+1
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDX     vl_cur                  ; old x = x - vx
        LDY     #0
        LDA     mul_p2
        BPL     :+
        DEY
:       STY     vl_w2
        SEC
        LDA     vl_xf,X
        SBC     mul_p1
        STA     vl_oxf,X
        LDA     vl_xl,X
        SBC     mul_p2
        STA     vl_oxl,X
        LDA     vl_xh,X
        SBC     vl_w2
        STA     vl_oxh,X
        LDA     vl_vn                   ; vy = (vn ny + vt nx) >> 6
        LDX     vl_vn+1
        LDY     vl_csny
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vl_vt
        LDX     vl_vt+1
        LDY     vl_csnx
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDX     vl_cur                  ; old y = y - vy
.ifdef VL_Y_HIGH
        LDY     #0
        LDA     mul_p2
        BPL     :+
        DEY
:       STY     vl_w2
.endif
        SEC
        LDA     vl_yf,X
        SBC     mul_p1
        STA     vl_oyf,X
        LDA     vl_yh,X
        SBC     mul_p2
        STA     vl_oyh,X
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        SBC     vl_w2
        STA     vl_oyu,X
.endif
        SEC
        RTS

; A = face: vl_cj < vl_pen (unsigned) -> vl_pen = vl_cj, vl_qx = A
vl_cmin:
        STA     vl_w2
        LDA     vl_cj
        CMP     vl_pen
        LDA     vl_cj+1
        SBC     vl_pen+1
        BCS     :+
        LDA     vl_cj
        STA     vl_pen
        LDA     vl_cj+1
        STA     vl_pen+1
        LDA     vl_w2
        STA     vl_qx
:       RTS
.endif

; ----------------------------------------------------------------------------
.ifref vl_contact_pair
vl_contact_pair:
        STA     vl_crad
        CLC                             ; whole pixels first (mod 256, safe):
        ADC     #(1 << (8 - VL_CIRC_Q)) - 1     ; min(|db - da|) > ceil(R): out
.repeat 8 - VL_CIRC_Q
        LSR     A
.endrepeat
        STA     vl_w2
        LDX     vl_cb
        LDY     vl_ca
        SEC
        LDA     vl_xl,X
        SBC     vl_xl,Y
        BPL     :+
        EOR     #$FF
        CLC
        ADC     #1
:       CMP     vl_w2
        BEQ     :+
        BCS     @no
:       SEC
        LDA     vl_yh,X
        SBC     vl_yh,Y
        BPL     :+
        EOR     #$FF
        CLC
        ADC     #1
:       CMP     vl_w2
        BEQ     :+
        BCS     @no
:       LDA     #0
.ifdef VL_PIN
        LDA     vl_pin,Y                ; bit 7: a pinned, bit 6: b
        BEQ     :+
        LDA     #$80
:       LDY     vl_pin,X
        BEQ     :+
        ORA     #$40
:       CMP     #$C0
        BEQ     @no                     ; both pinned
.endif
        STA     vl_cflag
.ifdef VL_CIRC_HEAVY
        LDY     vl_ca                   ; bit 5: a heavy, bit 4: b
        LDA     vl_cheavy,Y
        BEQ     :+
        LDA     #$20
        ORA     vl_cflag
        STA     vl_cflag
:       LDA     vl_cheavy,X
        BEQ     :+
        LDA     #$10
        ORA     vl_cflag
        STA     vl_cflag
:
.endif
        LDY     vl_ca
        LDA     #0
        STA     vl_csgn
        SEC                             ; dx = b - a, 24 bits
        LDA     vl_xf,X
        SBC     vl_xf,Y
        STA     vl_w0
        LDA     vl_xl,X
        SBC     vl_xl,Y
        STA     vl_w1
        LDA     vl_xh,X
        SBC     vl_xh,Y
        BEQ     @xp
        CMP     #$FF
        BNE     @no
        LDA     vl_w1
        BMI     @xn
@no:    CLC
        RTS
@xn:    SEC                             ; |dx|
        LDA     #0
        SBC     vl_w0
        STA     vl_w0
        LDA     #0
        SBC     vl_w1
        STA     vl_w1
        LDA     #$80
        STA     vl_csgn
@xp:    LDA     vl_w1
        CMP     #_VL_CQLIM
        BCS     @no
.repeat 8 - VL_CIRC_Q
        ASL     vl_w0
        ROL     A
.endrepeat
        CMP     vl_crad
        BCS     @no
        STA     vl_qx
        SEC                             ; dy = b - a
        LDA     vl_yf,X
        SBC     vl_yf,Y
        STA     vl_w0
        LDA     vl_yh,X
        SBC     vl_yh,Y
        STA     vl_w1
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        SBC     vl_yu,Y
        BEQ     @yp
        CMP     #$FF
        BNE     @no
        LDA     vl_w1
        BPL     @no
.else
        BCS     @yp                     ; (17 bits: the borrow is the sign)
        BPL     @no
.endif
        SEC                             ; |dy|
        LDA     #0
        SBC     vl_w0
        STA     vl_w0
        LDA     #0
        SBC     vl_w1
        STA     vl_w1
        LDA     #$40
        ORA     vl_csgn
        STA     vl_csgn
@yp:    LDA     vl_w1
        CMP     #_VL_CQLIM
        BCS     @no
.repeat 8 - VL_CIRC_Q
        ASL     vl_w0
        ROL     A
.endrepeat
        CMP     vl_crad
        BCS     @no
        STA     vl_qy
        JSR     vl_cnorm
        BCS     @no
        BNE     :+
        STA     vl_cnx                  ; s = 0: n = (0, -64)
        LDA     #64
        STA     vl_cny
        LDA     #$40
        STA     vl_csgn
:       JSR     vl_csigned
        ; the relative speed along n (the push moves pos and old: the same)
        LDX     vl_ca                   ; rvx = (xb - oxb) - (xa - oxa)
        SEC
        LDA     vl_xf,X
        SBC     vl_oxf,X
        STA     vl_val
        LDA     vl_xl,X
        SBC     vl_oxl,X
        STA     vl_val+1
        LDX     vl_cb
        SEC
        LDA     vl_xf,X
        SBC     vl_oxf,X
        STA     vl_w0
        LDA     vl_xl,X
        SBC     vl_oxl,X
        STA     vl_w1
        SEC
        LDA     vl_w0
        SBC     vl_val
        STA     vl_w0
        LDA     vl_w1
        SBC     vl_val+1
        TAX
        LDA     vl_w0
        LDY     vl_csnx
        JSR     mul_dir
        JSR     mul_acc_set
        LDX     vl_ca                   ; rvy
        SEC
        LDA     vl_yf,X
        SBC     vl_oyf,X
        STA     vl_val
        LDA     vl_yh,X
        SBC     vl_oyh,X
        STA     vl_val+1
        LDX     vl_cb
        SEC
        LDA     vl_yf,X
        SBC     vl_oyf,X
        STA     vl_w0
        LDA     vl_yh,X
        SBC     vl_oyh,X
        STA     vl_w1
        SEC
        LDA     vl_w0
        SBC     vl_val
        STA     vl_w0
        LDA     vl_w1
        SBC     vl_val+1
        TAX
        LDA     vl_w0
        LDY     vl_csny
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6            ; vn = p2:p1
        LDA     mul_p1
        STA     vl_vy                   ; (vl_vy: vn)
        LDA     mul_p2
        STA     vl_vy+1
.ifdef VL_CIRC_SLEEP
        LDA     vl_cflag                ; a sleeping point (pin $80) and a
        AND     #$C0                    ; closing speed > VL_CIRC_SLEEP: wake
        BEQ     @awake
        LDA     vl_vy+1
        BPL     @awake
        SEC
        LDA     #0
        SBC     vl_vy
        STA     vl_w0
        LDA     #0
        SBC     vl_vy+1
        STA     vl_w1
        LDA     #<VL_CIRC_SLEEP
        CMP     vl_w0
        LDA     #>VL_CIRC_SLEEP
        SBC     vl_w1
        BCS     @awake
        BIT     vl_cflag
        BPL     @wb
        LDX     vl_ca
        LDA     vl_pin,X
        CMP     #$80
        BNE     @wb
        LDA     #0
        STA     vl_pin,X
        LDA     vl_cflag
        AND     #$7F
        STA     vl_cflag
@wb:    BIT     vl_cflag
        BVC     @awake
        LDX     vl_cb
        LDA     vl_pin,X
        CMP     #$80
        BNE     @awake
        LDA     #0
        STA     vl_pin,X
        LDA     vl_cflag
        AND     #$BF
        STA     vl_cflag
@awake:
.endif
        ; the push: (pen |n|) >> (6 - Q) per axis, shared, pos and old pos
        LDA     vl_cnx
        JSR     vl_cpent
        JSR     vl_cshare
        LDX     vl_ca
        BIT     vl_csgn
        BMI     :+
        JSR     vl_csub_x2              ; n x > 0: a left, b right
        JSR     vl_cvn_val
        LDX     vl_cb
        JSR     vl_cadd_x2
        JMP     @py
:       JSR     vl_cadd_x2
        JSR     vl_cvn_val
        LDX     vl_cb
        JSR     vl_csub_x2
@py:    LDA     vl_cny
        JSR     vl_cpent
        JSR     vl_cshare
        LDX     vl_ca
        BIT     vl_csgn
        BVS     :+
        JSR     vl_csub_y2
        JSR     vl_cvn_val
        LDX     vl_cb
        JSR     vl_cadd_y2
        JMP     @imp
:       JSR     vl_cadd_y2
        JSR     vl_cvn_val
        LDX     vl_cb
        JSR     vl_csub_y2
@imp:   LDA     vl_vy+1
        BMI     @close
        SEC                             ; separating: contact, no impulse
        RTS
@close: SEC                             ; m = -vn
        LDA     #0
        SBC     vl_vy
        STA     mul_x
        STA     vl_cj
        LDA     #0
        SBC     vl_vy+1
        STA     mul_x+1
        STA     vl_cj+1
.if VL_CIRC_BOUNCE > 0
        LDA     #<VL_CIRC_VMIN          ; m > vmin: j = m + (m e) >> 8
        CMP     mul_x
        LDA     #>VL_CIRC_VMIN
        SBC     mul_x+1
        BCS     @inel
        MUL_K16 VL_CIRC_BOUNCE
        CLC
        LDA     vl_cj
        ADC     mul_p1
        STA     vl_cj
        LDA     vl_cj+1
        ADC     mul_p2
        STA     vl_cj+1
@inel:
.endif
        JSR     vl_cshare               ; vl_cj = a's part, vl_vn = b's
        LDA     vl_cnx                  ; x: old a +=, old b -= (j |nx|) >> 6
        BEQ     @jy
        LDA     vl_cj
        LDX     vl_cj+1
        LDY     vl_cnx
        JSR     vl_cjmul
        LDA     #_VL_COFF
        CLC
        ADC     vl_ca
        TAX
        BIT     vl_csgn
        BMI     :+
        JSR     vl_add_xv
        JMP     :++
:       JSR     vl_sub_xv
:       LDA     vl_vn                   ; b's share: the same product?
        CMP     vl_cj
        BNE     :+
        LDX     vl_vn+1
        CPX     vl_cj+1
        BEQ     :++
:       LDX     vl_vn+1
        LDY     vl_cnx
        JSR     vl_cjmul
:
        LDA     #_VL_COFF
        CLC
        ADC     vl_cb
        TAX
        BIT     vl_csgn
        BMI     :+
        JSR     vl_sub_xv
        JMP     @jy
:       JSR     vl_add_xv
@jy:    LDA     vl_cny                  ; y
        BEQ     @done
        LDA     vl_cj
        LDX     vl_cj+1
        LDY     vl_cny
        JSR     vl_cjmul
        LDA     #_VL_COFF
        CLC
        ADC     vl_ca
        TAX
        BIT     vl_csgn
        BVS     :+
        JSR     vl_add_yv
        JMP     :++
:       JSR     vl_sub_yv
:       LDA     vl_vn                   ; b's share: the same product?
        CMP     vl_cj
        BNE     :+
        LDX     vl_vn+1
        CPX     vl_cj+1
        BEQ     :++
:       LDX     vl_vn+1
        LDY     vl_cny
        JSR     vl_cjmul
:
        LDA     #_VL_COFF
        CLC
        ADC     vl_cb
        TAX
        BIT     vl_csgn
        BVS     :+
        JSR     vl_sub_yv
        JMP     @done
:       JSR     vl_add_yv
@done:  SEC
        RTS

; vl_val = vl_vn (b's share of the push)
vl_cvn_val:
        LDA     vl_vn
        STA     vl_val
        LDA     vl_vn+1
        STA     vl_val+1
        RTS

; vl_cj = total (16 bits) -> vl_cj = vl_val = a's part, vl_vn = b's (vl_cflag:
; bit 7 a pinned, 6 b pinned, 5 a heavy, 4 b heavy)
vl_cshare:
        LDA     vl_cflag
        BMI     @apin
        ASL     A
        BMI     @bpin
        LSR     vl_cj+1                 ; half each
        ROR     vl_cj
        LDA     vl_cj
        STA     vl_vn
        LDA     vl_cj+1
        STA     vl_vn+1
.ifdef VL_CIRC_HEAVY
        LDA     vl_cflag                ; exactly one heavy: +-(half >> n)
        AND     #$30
        BEQ     @rts
        CMP     #$30
        BEQ     @rts
        PHA
        LDA     vl_cj
        STA     vl_w0
        LDA     vl_cj+1
.repeat VL_CIRC_HEAVY
        LSR     A
        ROR     vl_w0
.endrepeat
        STA     vl_w1
        PLA
        CMP     #$20
        BEQ     @aheavy
        CLC                             ; b heavy: a = half + d, b = half - d
        LDA     vl_cj
        ADC     vl_w0
        STA     vl_cj
        LDA     vl_cj+1
        ADC     vl_w1
        STA     vl_cj+1
        SEC
        LDA     vl_vn
        SBC     vl_w0
        STA     vl_vn
        LDA     vl_vn+1
        SBC     vl_w1
        STA     vl_vn+1
        JMP     @rts
@aheavy:
        SEC                             ; a heavy: a = half - d, b = half + d
        LDA     vl_cj
        SBC     vl_w0
        STA     vl_cj
        LDA     vl_cj+1
        SBC     vl_w1
        STA     vl_cj+1
        CLC
        LDA     vl_vn
        ADC     vl_w0
        STA     vl_vn
        LDA     vl_vn+1
        ADC     vl_w1
        STA     vl_vn+1
.endif
@rts:   LDA     vl_cj                   ; vl_val = a's part
        STA     vl_val
        LDA     vl_cj+1
        STA     vl_val+1
        RTS
@apin:  LDA     vl_cj                   ; a pinned: b takes all
        STA     vl_vn
        LDA     vl_cj+1
        STA     vl_vn+1
        LDA     #0
        STA     vl_cj
        STA     vl_cj+1
        BEQ     @rts
@bpin:  LDA     #0                      ; b pinned: a takes all
        STA     vl_vn
        STA     vl_vn+1
        BEQ     @rts

; vl_val = (A/X (unsigned) * Y) >> 6
vl_cjmul:
        STA     mul_x
        STX     mul_x+1
        STY     mul_y
        JSR     mul_u16u8
        JSR     mul_shr6
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        RTS
.endif

; ----------------------------------------------------------------------------
.ifref vl_circ_sleep
.ifndef VL_CIRC_SLEEP
.error "vl_circ_sleep: define VL_CIRC_SLEEP (the speed, 8.8) and VL_PIN"
.endif
.ifndef VL_CIRC_SLEEP_TICKS
VL_CIRC_SLEEP_TICKS = 16
.endif
; X = point: a free point slow on both axes VL_CIRC_SLEEP_TICKS ticks in a
; row goes to sleep (vl_pin,X = $80, at rest; C = 1 then). Keeps X.
vl_circ_sleep:
        LDA     vl_pin,X
        BNE     @rts0
        SEC
        LDA     vl_xf,X
        SBC     vl_oxf,X
        STA     vl_w0
        LDA     vl_xl,X
        SBC     vl_oxl,X
        JSR     @slow
        BCC     @move
        SEC
        LDA     vl_yf,X
        SBC     vl_oyf,X
        STA     vl_w0
        LDA     vl_yh,X
        SBC     vl_oyh,X
        JSR     @slow
        BCC     @move
        INC     vl_still,X
        LDA     vl_still,X
        CMP     #VL_CIRC_SLEEP_TICKS
        BCC     @rts
        LDA     #$80
        STA     vl_pin,X
        LDA     #0
        STA     vl_still,X
        LDA     vl_xf,X                 ; at rest
        STA     vl_oxf,X
        LDA     vl_xl,X
        STA     vl_oxl,X
        LDA     vl_xh,X
        STA     vl_oxh,X
        LDA     vl_yf,X
        STA     vl_oyf,X
        LDA     vl_yh,X
        STA     vl_oyh,X
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        STA     vl_oyu,X
.endif
        SEC
        RTS
@move:  LDA     #0
        STA     vl_still,X
@rts0:  CLC
@rts:   RTS
; A:vl_w0 = a speed (hi:lo) -> C = 1 when |v| <= VL_CIRC_SLEEP
@slow:  BPL     :+
        STA     vl_w1
        SEC
        LDA     #0
        SBC     vl_w0
        STA     vl_w0
        LDA     #0
        SBC     vl_w1
:       STA     vl_w1
        LDA     #<VL_CIRC_SLEEP
        CMP     vl_w0
        LDA     #>VL_CIRC_SLEEP
        SBC     vl_w1
        RTS
.endif

; ----------------------------------------------------------------------------
; shared by the pair and the boxes
.if .referenced(vl_contact_pair) .or .referenced(vl_contact_box)

; vl_qx, vl_qy, vl_crad -> C = 1: q2 >= R^2, no contact. C = 0: vl_pen = pen,
; vl_cnx / vl_cny = |n|, A = s (Z = 1: s = 0, the normal left to the caller)
vl_cnorm:
        LDA     vl_qx
        JSR     vl_square
        STA     vl_pen
        STY     vl_pen+1
        LDA     vl_qy
        JSR     vl_square
        CLC
        ADC     vl_pen
        STA     mul_x
        TYA
        ADC     vl_pen+1
        STA     mul_x+1
        LDA     vl_crad
        JSR     vl_square
        STA     vl_pen
        STY     vl_pen+1
        LDA     mul_x
        CMP     vl_pen
        LDA     mul_x+1
        SBC     vl_pen+1
        BCS     @rts                    ; q2 >= R^2
        LDA     mul_x
        ORA     mul_x+1
        BNE     @root
        LDA     vl_crad                 ; s = 0: pen = R
        STA     vl_pen
        LDA     #0
        CLC
        RTS
@root:  JSR     isqrt16                 ; A = s
        STA     vl_pen+1
        TAX
        SEC
        LDA     vl_crad
        SBC     vl_pen+1
        STA     vl_pen
        LDA     vl_crcp_lo,X            ; |n| = q * rcp[s] >> 8
        STA     mul_x
        LDA     vl_crcp_hi,X
        STA     mul_x+1
        LDA     vl_qx
        STA     mul_y
        JSR     mul_u16u8
        LDA     mul_p1
        STA     vl_cnx
        LDA     vl_qy
        STA     mul_y
        JSR     mul_u16u8
        LDA     mul_p1
        STA     vl_cny
        LDA     vl_pen+1                ; Z = 0
        CLC
@rts:   RTS

; vl_csnx / vl_csny = the signed normal (|n| and the signs of vl_csgn)
vl_csigned:
        LDA     vl_cnx
        BIT     vl_csgn
        BPL     :+
        EOR     #$FF
        CLC
        ADC     #1
:       STA     vl_csnx
        LDA     vl_cny
        BIT     vl_csgn
        BVC     :+
        EOR     #$FF
        CLC
        ADC     #1
:       STA     vl_csny
        RTS

; vl_cj = vl_val = (pen * A) >> (6 - Q), A = |n| (the whole push on an axis)
vl_cpent:
        STA     mul_y
        LDA     vl_pen
        STA     mul_x
        JSR     mul_u8u8
.repeat 6 - VL_CIRC_Q
        LSR     mul_p1
        ROR     mul_p0
.endrepeat
        LDA     mul_p0
        STA     vl_cj
        STA     vl_val
        LDA     mul_p1
        STA     vl_cj+1
        STA     vl_val+1
        RTS

; point X and its old position +/- vl_val (x or y). Keep X.
vl_cadd_x2:
        JSR     vl_add_xv
        TXA
        CLC
        ADC     #_VL_COFF
        TAX
        JSR     vl_add_xv
        JMP     vl_cback
vl_csub_x2:
        JSR     vl_sub_xv
        TXA
        CLC
        ADC     #_VL_COFF
        TAX
        JSR     vl_sub_xv
        JMP     vl_cback
vl_cadd_y2:
        JSR     vl_add_yv
        TXA
        CLC
        ADC     #_VL_COFF
        TAX
        JSR     vl_add_yv
        JMP     vl_cback
vl_csub_y2:
        JSR     vl_sub_yv
        TXA
        CLC
        ADC     #_VL_COFF
        TAX
        JSR     vl_sub_yv
vl_cback:
        TXA
        SEC
        SBC     #_VL_COFF
        TAX
        RTS

.segment "RODATA"
; ceil(2^14 / s), s = 0..127 (the normal's reciprocal; s = 0 unused)
vl_crcp_lo:
.repeat 128, I
.if I = 0
        .byte   0
.else
        .byte   <((16384 + I - 1) / I)
.endif
.endrepeat
vl_crcp_hi:
.repeat 128, I
.if I = 0
        .byte   0
.else
        .byte   >((16384 + I - 1) / I)
.endif
.endrepeat
.segment "CODE"
.endif

.endif  ; _VERLET_CIRC_ASM_LOADED_
