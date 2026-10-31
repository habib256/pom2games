; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; verlet_hmap.asm -- lib/physics: ground contact on a height map
; ============================================================================
; Include at the END (after the callers, before verlet_con.asm, verlet_rot.asm,
; verlet.asm and mul.asm). dev/tools/verlet/ground.py is the reference.
;
;   vl_height_at   A = the row VL_HEIGHTS[vl_hxh:vl_hxl] (no wrap). Keeps X.
;                  ~30 cycles.
;   vl_ground      X = point (< VL_GROUND): the disc of radius VL_RADIUS
;                  against the ground; vl_gnd,X = 1 in contact. The slope
;                  h[x + VL_PROBE] - h[x - VL_PROBE] (a byte difference,
;                  keep it within +-127), clamped to +-VL_SLOPE_MAX, picks
;                  the normal (vl_norm_x / vl_norm_y, 64 = 1.0); the point
;                  is pushed out along it, its speed split into vl_vn (along
;                  the normal) and vl_vt (along the tangent -ny, nx), a
;                  negative vn bounces (vn = -vn * VL_BOUNCE / 256), then the
;                  speed is rebuilt from vn and vt (old position = position -
;                  speed). Ground further than VL_FAR below: no test.
;                  ~250 cycles without contact, 1000-2500 with (the mul_dir
;                  short cuts make a flat ground cheaper).
;                  VL_Y_HIGH: y is 24 bits, the ground row is the height +
;                  VL_GROUND_BASE (default 0; a 16-bit row): the ground lies
;                  within rows BASE..BASE+255 of a world taller than 256 rows.
;
; Hooks (macros, empty unless the program defines them before this include):
;   VL_GROUND_ENTER    after vl_gnd,X = 0 (A = 0, X = the point)
;   VL_GROUND_TANGENT  in contact, after the bounce, before the rebuild:
;                      change vl_vt (and vl_vn): traction, brake, friction
;                      (JSR vl_damp). vl_cur = the point; A, X, Y free;
;                      the old position is still the tick's.
;   VL_GROUND_AFTER    in contact, after the rebuild (X = the point, vl_vt
;                      the final tangential speed): spokes, spin...
; Hook code should use unnamed labels (or names no @label here uses:
; @hx @hx2 @sneg @sok @wneg @wok @touch @nob @xp).
; ============================================================================

.ifndef _VERLET_HMAP_ASM_LOADED_
_VERLET_HMAP_ASM_LOADED_ = 1

.ifndef _VERLET_INC_LOADED_
.error "verlet_hmap.asm: include verlet.inc at the top first"
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

.ifref vl_ground
.ifndef VL_GROUND
.error "vl_ground: define VL_GROUND (and VL_HEIGHTS, VL_RADIUS...) before verlet.inc"
.endif
.assert <VL_FAR = 0, error, "vl_ground: VL_FAR in whole rows"
.assert VL_FAR > 0 .and VL_FAR < $8000, error, "vl_ground: VL_FAR is 1..127 rows"
.assert VL_BOUNCE >= 0 .and VL_BOUNCE < 128, error, "vl_ground: VL_BOUNCE is 0..127 (/256)"
.assert VL_SLOPE_MAX >= 0 .and VL_SLOPE_MAX < 128, error, "vl_ground: VL_SLOPE_MAX < 128"
.assert VL_PROBE >= 1 .and VL_PROBE < 128, error, "vl_ground: VL_PROBE is 1..127"
.ifdef VL_GROUND_BASE
.ifndef VL_Y_HIGH
.error "vl_ground: VL_GROUND_BASE needs VL_Y_HIGH (y 16.8)"
.endif
.else
VL_GROUND_BASE = 0
.endif
vl_ground:
        STX     vl_cur
        LDA     #0
        STA     vl_gnd,X
        VL_GROUND_ENTER
        SEC                             ; ground rows at px - p, px, px + p
        LDA     vl_xl,X
        SBC     #VL_PROBE
        STA     vl_hxl
        LDA     vl_xh,X
        SBC     #0
        STA     vl_hxh
        JSR     vl_height_at
        PHA
        CLC
        LDA     vl_hxl
        ADC     #2 * VL_PROBE
        STA     vl_hxl
        BCC     @hx
        INC     vl_hxh
@hx:    JSR     vl_height_at
        PHA
        SEC
        LDA     vl_hxl
        SBC     #VL_PROBE
        STA     vl_hxl
        BCS     @hx2
        DEC     vl_hxh
@hx2:   JSR     vl_height_at
        STA     vl_hgt
        PLA                             ; slope = h[+p] - h[-p], +-VL_SLOPE_MAX
        STA     vl_hp2
        PLA
        STA     vl_hm2
        LDA     vl_hp2
        SEC
        SBC     vl_hm2
        BMI     @sneg
        CMP     #VL_SLOPE_MAX+1
        BCC     @sok
        LDA     #VL_SLOPE_MAX
        BNE     @sok
@sneg:  CMP     #<(-VL_SLOPE_MAX)
        BCS     @sok
        LDA     #<(-VL_SLOPE_MAX)
@sok:   CLC
        ADC     #VL_SLOPE_MAX
        TAY
        LDA     vl_norm_x,Y
        STA     vl_nx
        LDA     vl_norm_y,Y
        STA     vl_ny
.ifdef VL_Y_HIGH
        CLC                             ; w = ((h + base) << 8) - y, 24 bits
        LDA     vl_hgt
        ADC     #<VL_GROUND_BASE
        STA     vl_w1
        LDA     #>VL_GROUND_BASE
        ADC     #0
        STA     vl_w2
        SEC
        LDA     #0
        SBC     vl_yf,X
        STA     vl_w0
        LDA     vl_w1
        SBC     vl_yh,X
        STA     vl_w1
        LDA     vl_w2
        SBC     vl_yu,X
        STA     vl_w2
        BMI     @wneg
        BNE     @far
        LDA     vl_w1
        CMP     #>VL_FAR
        BCC     @wok
@far:   RTS                             ; ground far below: no contact
@wneg:  CMP     #$FF
        BNE     @wmin
        LDA     vl_w1
        CMP     #>(-VL_FAR)
        BCS     @wok
@wmin:  LDA     #>(-VL_FAR)
        STA     vl_w1
        LDA     #0
        STA     vl_w0
.else
        SEC                             ; w = (h << 8) - y, 24 bits
        LDA     #0
        SBC     vl_yf,X
        STA     vl_w0
        LDA     vl_hgt
        SBC     vl_yh,X
        STA     vl_w1
        LDA     #0
        SBC     #0
        STA     vl_w2
        BMI     @wneg
        LDA     vl_w1
        CMP     #>VL_FAR
        BCC     @wok
        RTS                             ; ground far below: no contact
@wneg:  LDA     vl_w1
        CMP     #>(-VL_FAR)
        BCS     @wok
        LDA     #>(-VL_FAR)
        STA     vl_w1
        LDA     #0
        STA     vl_w0
.endif
@wok:   SEC                             ; dist = (w * -ny) >> 6
        LDA     #0
        SBC     vl_ny
        TAY
        LDA     vl_w0
        LDX     vl_w1
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p2                   ; dist >= VL_RADIUS: no contact
        BMI     @touch
        LDA     mul_p1
        CMP     #<VL_RADIUS
        LDA     mul_p2
        SBC     #>VL_RADIUS
        BCC     @touch
        RTS
@touch: LDX     vl_cur
        LDA     #1
        STA     vl_gnd,X
        SEC                             ; pen = VL_RADIUS - dist
        LDA     #<VL_RADIUS
        SBC     mul_p1
        STA     vl_pen
        LDA     #>VL_RADIUS
        SBC     mul_p2
        STA     vl_pen+1
        LDA     vl_pen                     ; x += (pen * nx) >> 6
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
        LDA     vl_pen                     ; y += (pen * ny) >> 6
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
        ; vn = (vx nx + vy ny) >> 6
        LDA     vl_vx
        LDX     vl_vx+1
        LDY     vl_nx
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vl_vy
        LDX     vl_vy+1
        LDY     vl_ny
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vl_vn
        LDA     mul_p2
        STA     vl_vn+1
        ; vt = (vx (-ny) + vy nx) >> 6
        SEC
        LDA     #0
        SBC     vl_ny
        TAY
        LDA     vl_vx
        LDX     vl_vx+1
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vl_vy
        LDX     vl_vy+1
        LDY     vl_nx
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vl_vt
        LDA     mul_p2
        STA     vl_vt+1
        ; bounce: vn < 0 -> vn = (-vn * VL_BOUNCE) >> 8
        LDA     vl_vn+1
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
        ; vx = (vn nx + vt (-ny)) >> 6
        LDA     vl_vn
        LDX     vl_vn+1
        LDY     vl_nx
        JSR     mul_dir
        JSR     mul_acc_set
        SEC
        LDA     #0
        SBC     vl_ny
        TAY
        LDA     vl_vt
        LDX     vl_vt+1
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        LDX     vl_cur                     ; old x = x - vx
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
        ; vy = (vn ny + vt nx) >> 6
        LDA     vl_vn
        LDX     vl_vn+1
        LDY     vl_ny
        JSR     mul_dir
        JSR     mul_acc_set
        LDA     vl_vt
        LDX     vl_vt+1
        LDY     vl_nx
        JSR     mul_dir
        JSR     mul_acc_add
        JSR     mul_acc_shr6
        LDX     vl_cur                     ; old y = y - vy
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
        RTS
.endif

.ifref vl_height_at
vl_height_at:
        CLC
        LDA     vl_hxl
        ADC     #<VL_HEIGHTS
        STA     vl_tptr
        LDA     vl_hxh
        ADC     #>VL_HEIGHTS
        STA     vl_tptr+1
        LDY     #0
        LDA     (vl_tptr),Y
        RTS
.endif

.endif  ; _VERLET_HMAP_ASM_LOADED_
