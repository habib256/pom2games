; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet_seg.asm -- lib/physics: ground contact on line segments
; ============================================================================
; Include at the END, BEFORE verlet_hmap.asm (vl_ground_any references
; vl_ground), then verlet_con.asm, verlet_rot.asm, verlet.asm, mul.asm.
; dev/tools/verlet/segments.py (SegmentGround) is the reference.
;
;   vl_seg_ground  X = point (< VL_GROUND): the disc of radius VL_RADIUS
;                  against the VL_GROUND_SEGMENTS segments; vl_gnd,X = 1 and
;                  vl_sgi,X = the segment in contact ($FF: none). Each
;                  segment whose box (whole pixels) holds the point's pixel
;                  is a candidate: d = (dx nx + dy ny) >> 6 (dx, dy = point -
;                  segment start, 8.8), kept if -VL_SEG_DEPTH <= d < the best
;                  so far (VL_RADIUS at first) and the position along the
;                  tangent s = (dy nx - dx ny) >> 6 is within 0..smax. The
;                  deepest wins (the first of the scan, n-1 down to 0, on a
;                  tie); then the same resolve as vl_ground: push by pen =
;                  VL_RADIUS - d along the normal, vn / vt, bounce, the
;                  hooks, rebuild. Any slope: walls, ceilings, loops.
;                  ~30 cycles a segment out of its box; a candidate ~250-900
;                  (the mul_dir short cuts: axis-aligned segments are cheap);
;                  the resolve ~1,600-2,600 (as vl_ground). 22 segments: 660
;                  far, 2,640 on a floor, 4,210 on a 45-degree slope.
;                  VL_SEG_CACHE = m (8.8): the point's last segment (vl_sgi,X
;                  < VL_GROUND_SEGMENTS) is taken without the scan when the
;                  point is still on it (-VL_SEG_DEPTH <= d < VL_RADIUS) and
;                  m <= s <= smax - m: ~500-1,500 cycles less there.
;   vl_ground_any  VL_GROUND_KIND = a table (VL_GROUND bytes, the program's):
;                  0 = vl_ground (height map) for point X, else vl_seg_ground.
;
; Tables (the program's, dev/tools/verlet/segments.py SegmentGround.tables()):
;   vl_sg_x0f, vl_sg_x0l   segment start x (8.8 low 16 bits of the 16.8)
;   vl_sg_y0f, vl_sg_y0h   start y (8.8 low 16 bits)
;   vl_sg_nx, vl_sg_ny     the normal (signed, 64 = 1.0, to the free side)
;   vl_sg_sl, vl_sg_sh     smax: the length along the tangent (-ny, nx), 8.8
;   vl_sg_bx0l/h, vl_sg_bx1l/h   the box, whole px (16 bits, unsigned)
;   vl_sg_by0, vl_sg_by1   rows (bytes; VL_Y_HIGH: + vl_sg_by0h, vl_sg_by1h)
; The box must keep |point - start| < 128 px (segments.py: at most 88 px).
;
; Parameters: VL_GROUND_SEGMENTS (1..128), VL_SEG_DEPTH (8.8, > 0: a point
; deeper than this behind a segment's line does not touch it: a thin wall
; seen from behind), VL_RADIUS, VL_BOUNCE (shared with the height map).
; Hooks: VL_GROUND_ENTER / VL_GROUND_TANGENT / VL_GROUND_AFTER, as
; vl_ground (vl_nx / vl_ny = the segment's normal in the hooks).
; Zero page: none of its own (the ground tier's vl_hxl, vl_hxh, vl_hgt,
; vl_hm2, vl_hp2, vl_tptr as scratch; vl_dx, vl_dy, vl_vn, vl_pen).
; Hook code: unnamed labels (or names no @label here uses: @scan @next
; @done @no @hit @xp @yp @rts @nob @miss @cs @c0 @scan0).
; ============================================================================

.ifndef _VERLET_SEG_ASM_LOADED_
_VERLET_SEG_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet_seg.asm: include verlet.inc at the top first"
.endif

.if .not .definedmacro(VL_GROUND_ENTER)
.macro VL_GROUND_ENTER
.endmacro
.endif
.if .not .definedmacro(VL_GROUND_TANGENT)
.macro VL_GROUND_TANGENT
.endmacro
.endif
.if .not .definedmacro(VL_GROUND_AFTER)
.macro VL_GROUND_AFTER
.endmacro
.endif

.segment "CODE"

.ifref vl_ground_any
.ifndef VL_GROUND_KIND
.error "vl_ground_any: define VL_GROUND_KIND (a table: 0 = height map) before verlet_seg.asm"
.endif
vl_ground_any:
        LDA     VL_GROUND_KIND,X
        BNE     :+
        JMP     vl_ground
:       JMP     vl_seg_ground
.endif

.ifref vl_seg_ground
.ifndef VL_GROUND_SEGMENTS
.error "vl_seg_ground: define VL_GROUND_SEGMENTS (and VL_GROUND, VL_SEG_DEPTH...) before verlet.inc"
.endif
.assert VL_SEG_DEPTH > 0 .and VL_SEG_DEPTH < $8000, error, "vl_seg_ground: VL_SEG_DEPTH is 8.8, 1..$7FFF"
.assert VL_RADIUS > 0 .and VL_RADIUS < $8000, error, "vl_seg_ground: VL_RADIUS is 8.8, 1..$7FFF"
.assert VL_BOUNCE >= 0 .and VL_BOUNCE < 128, error, "vl_seg_ground: VL_BOUNCE is 0..127 (/256)"
_sg_pxl  = vl_hxl                       ; the point's pixel
_sg_pxh  = vl_hxh
_sg_py   = vl_hgt
_sg_pyh  = vl_hm2                       ; (VL_Y_HIGH)
_sg_k    = vl_hp2                       ; segment under test
_sg_best = vl_tptr                      ; the deepest so far ($FF: none)
_sg_d    = vl_vn                        ; d of the candidate; best d: vl_pen

; dx, dy = point vl_cur - segment Y start (8.8); vl_nx, vl_ny; _sg_d = d =
; (dx nx + dy ny) >> 6 (also in mul_p1 / A = mul_p2); _sg_k = Y
.macro _SG_D
        STY     _sg_k
        LDX     vl_cur
        SEC
        LDA     vl_xf,X
        SBC     vl_sg_x0f,Y
        STA     vl_dx
        LDA     vl_xl,X
        SBC     vl_sg_x0l,Y
        STA     vl_dx+1
        SEC
        LDA     vl_yf,X
        SBC     vl_sg_y0f,Y
        STA     vl_dy
        LDA     vl_yh,X
        SBC     vl_sg_y0h,Y
        STA     vl_dy+1
        LDA     vl_sg_ny,Y
        STA     vl_ny
        LDA     vl_sg_nx,Y
        STA     vl_nx
        TAY
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     mul_dir
        _SG_ACC
        LDY     vl_ny
        LDA     vl_dy
        LDX     vl_dy+1
        JSR     mul_dir
        _SG_SUM6
        STA     _sg_d+1
        LDA     mul_p1
        STA     _sg_d
.endmacro
; s = (dy nx - dx ny) >> 6 -> mul_p1 / mul_p2 (A = mul_p2)
.macro _SG_S
        LDY     vl_nx
        LDA     vl_dy
        LDX     vl_dy+1
        JSR     mul_dir
        _SG_ACC
        SEC
        LDA     #0
        SBC     vl_ny
        TAY
        LDA     vl_dx
        LDX     vl_dx+1
        JSR     mul_dir
        _SG_SUM6
.endmacro
.macro _SG_ACC                          ; mul_acc = mul_p (inline mul_acc_set)
        LDA     mul_p0
        STA     mul_acc0
        LDA     mul_p1
        STA     mul_acc1
        LDA     mul_p2
        STA     mul_acc2
.endmacro
.macro _SG_SUM6                         ; mul_p1:A = (mul_acc + mul_p) >> 6
        CLC
        LDA     mul_acc0
        ADC     mul_p0
        STA     mul_p0
        LDA     mul_acc1
        ADC     mul_p1
        STA     mul_p1
        LDA     mul_acc2
        ADC     mul_p2
        ASL     mul_p0
        ROL     mul_p1
        ROL     A
        ASL     mul_p0
        ROL     mul_p1
        ROL     A
        STA     mul_p2
.endmacro

vl_seg_ground:
        STX     vl_cur
        LDA     #0
        STA     vl_gnd,X
        VL_GROUND_ENTER
        LDX     vl_cur
.ifdef VL_SEG_CACHE
        .assert VL_SEG_CACHE >= 0 .and VL_SEG_CACHE < $4000, error, "VL_SEG_CACHE: 8.8, 0..$3FFF"
        LDY     vl_sgi,X                ; the last segment: still on it, and
        CPY     #VL_GROUND_SEGMENTS     ; VL_SEG_CACHE or more from its ends?
        BCC     @c0
        JMP     @scan0
@c0:    _SG_D
        LDA     _sg_d                   ; d < VL_RADIUS (signed)
        CMP     #<VL_RADIUS
        LDA     _sg_d+1
        SBC     #>VL_RADIUS
        BVC     :+
        EOR     #$80
:       BPL     @miss
        LDA     _sg_d                   ; d >= -VL_SEG_DEPTH
        CMP     #<(-VL_SEG_DEPTH)
        LDA     _sg_d+1
        SBC     #>(-VL_SEG_DEPTH)
        BVC     :+
        EOR     #$80
:       BPL     @cs
@miss:  JMP     @scan0
@cs:    _SG_S
        LDA     mul_p1                  ; s >= VL_SEG_CACHE (signed)
        CMP     #<VL_SEG_CACHE
        LDA     mul_p2
        SBC     #>VL_SEG_CACHE
        BVC     :+
        EOR     #$80
:       BMI     @scan0
        CLC                             ; s + VL_SEG_CACHE <= smax
        LDA     mul_p1
        ADC     #<VL_SEG_CACHE
        STA     mul_p1
        LDA     mul_p2
        ADC     #>VL_SEG_CACHE
        STA     mul_p2
        LDY     _sg_k
        LDA     vl_sg_sl,Y
        CMP     mul_p1
        LDA     vl_sg_sh,Y
        SBC     mul_p2
        BCC     @scan0
        LDA     _sg_d                   ; taken without the scan
        STA     vl_pen
        LDA     _sg_d+1
        STA     vl_pen+1
        JMP     @hit
@scan0: LDX     vl_cur
.endif
        LDA     #$FF
        STA     vl_sgi,X
        STA     _sg_best
        LDA     vl_xl,X
        STA     _sg_pxl
        LDA     vl_xh,X
        STA     _sg_pxh
        LDA     vl_yh,X
        STA     _sg_py
.ifdef VL_Y_HIGH
        LDA     vl_yu,X
        STA     _sg_pyh
.endif
        LDA     #<VL_RADIUS             ; best d = the radius
        STA     vl_pen
        LDA     #>VL_RADIUS
        STA     vl_pen+1
        LDY     #VL_GROUND_SEGMENTS
@next:  DEY                             ; segments n-1 .. 0
        BPL     @scan
        JMP     @done
@scan:  LDA     _sg_pxl                 ; px >= bx0
        CMP     vl_sg_bx0l,Y
        LDA     _sg_pxh
        SBC     vl_sg_bx0h,Y
        BCC     @next
        LDA     vl_sg_bx1l,Y            ; bx1 >= px
        CMP     _sg_pxl
        LDA     vl_sg_bx1h,Y
        SBC     _sg_pxh
        BCC     @next
.ifdef VL_Y_HIGH
        LDA     _sg_py                  ; py >= by0 (16 bits, unsigned)
        CMP     vl_sg_by0,Y
        LDA     _sg_pyh
        SBC     vl_sg_by0h,Y
        BCC     @next
        LDA     vl_sg_by1,Y             ; by1 >= py
        CMP     _sg_py
        LDA     vl_sg_by1h,Y
        SBC     _sg_pyh
        BCC     @next
.else
        LDA     _sg_py                  ; by0 <= py <= by1
        CMP     vl_sg_by0,Y
        BCC     @next
        LDA     vl_sg_by1,Y
        CMP     _sg_py
        BCC     @next
.endif
        _SG_D                           ; a candidate: d < best (signed)
        LDA     _sg_d
        CMP     vl_pen
        LDA     _sg_d+1
        SBC     vl_pen+1
        BVC     :+
        EOR     #$80
:       BPL     @no
        LDA     _sg_d                   ; d >= -VL_SEG_DEPTH (signed)
        CMP     #<(-VL_SEG_DEPTH)
        LDA     _sg_d+1
        SBC     #>(-VL_SEG_DEPTH)
        BVC     :+
        EOR     #$80
:       BMI     @no
        _SG_S                           ; 0 <= s <= smax
        BMI     @no
        LDY     _sg_k
        LDA     vl_sg_sl,Y
        CMP     mul_p1
        LDA     vl_sg_sh,Y
        SBC     mul_p2
        BCC     @no
        STY     _sg_best                ; the deepest so far
        LDA     _sg_d
        STA     vl_pen
        LDA     _sg_d+1
        STA     vl_pen+1
@no:    LDY     _sg_k
        JMP     @next
@done:  LDY     _sg_best
        BPL     @hit
        RTS                             ; no contact
@hit:   LDX     vl_cur
        TYA
        STA     vl_sgi,X
        LDA     #1
        STA     vl_gnd,X
        LDA     vl_sg_nx,Y
        STA     vl_nx
        LDA     vl_sg_ny,Y
        STA     vl_ny
        SEC                             ; pen = VL_RADIUS - d
        LDA     #<VL_RADIUS
        SBC     vl_pen
        STA     vl_pen
        LDA     #>VL_RADIUS
        SBC     vl_pen+1
        STA     vl_pen+1
        ; --- the resolve, as vl_ground (verlet_hmap.asm) -------------------
        LDA     vl_pen                  ; x += (pen * nx) >> 6
        LDX     vl_pen+1
        LDY     vl_nx
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        LDX     vl_cur
        JSR     vl_add_xv
        LDA     vl_pen                  ; y += (pen * ny) >> 6
        LDX     vl_pen+1
        LDY     vl_ny
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        LDX     vl_cur
        JSR     vl_add_yv
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
        LDY     vl_nx
        JSR     mul_dir
        _SG_ACC
        LDA     vl_vy
        LDX     vl_vy+1
        LDY     vl_ny
        JSR     mul_dir
        _SG_SUM6
        LDA     mul_p1
        STA     vl_vn
        LDA     mul_p2
        STA     vl_vn+1
        SEC                             ; vt = (vx (-ny) + vy nx) >> 6
        LDA     #0
        SBC     vl_ny
        TAY
        LDA     vl_vx
        LDX     vl_vx+1
        JSR     mul_dir
        _SG_ACC
        LDA     vl_vy
        LDX     vl_vy+1
        LDY     vl_nx
        JSR     mul_dir
        _SG_SUM6
        LDA     mul_p1
        STA     vl_vt
        LDA     mul_p2
        STA     vl_vt+1
        LDA     vl_vn+1                 ; bounce: vn < 0 -> (-vn * VL_BOUNCE) >> 8
        BPL     @nob
        SEC
        LDA     #0
        SBC     vl_vn
        PHA
        LDA     #0
        SBC     vl_vn+1
        TAX
        PLA
        LDY     #VL_BOUNCE
        JSR     mul_dir
        LDA     mul_p1
        STA     vl_vn
        LDA     mul_p2
        STA     vl_vn+1
@nob:   VL_GROUND_TANGENT
        LDA     vl_vn                   ; vx = (vn nx + vt (-ny)) >> 6
        LDX     vl_vn+1
        LDY     vl_nx
        JSR     mul_dir
        _SG_ACC
        SEC
        LDA     #0
        SBC     vl_ny
        TAY
        LDA     vl_vt
        LDX     vl_vt+1
        JSR     mul_dir
        _SG_SUM6
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        LDX     vl_cur                  ; old x = x - vx
        LDY     #0
        LDA     vl_val+1
        BPL     @xp
        DEY
@xp:    STY     vl_w2
        SEC
        LDA     vl_xf,X
        SBC     vl_val
        STA     vl_oxf,X
        LDA     vl_xl,X
        SBC     vl_val+1
        STA     vl_oxl,X
        LDA     vl_xh,X
        SBC     vl_w2
        STA     vl_oxh,X
        LDA     vl_vn                   ; vy = (vn ny + vt nx) >> 6
        LDX     vl_vn+1
        LDY     vl_ny
        JSR     mul_dir
        _SG_ACC
        LDA     vl_vt
        LDX     vl_vt+1
        LDY     vl_nx
        JSR     mul_dir
        _SG_SUM6
        LDX     vl_cur                  ; old y = y - vy
.ifdef VL_Y_HIGH
        LDY     #0
        LDA     mul_p2
        BPL     @yp
        DEY
@yp:    STY     vl_w2
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
        VL_GROUND_AFTER
@rts:   RTS
.endif

.endif  ; _VERLET_SEG_ASM_LOADED_
