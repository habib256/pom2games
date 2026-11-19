; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.ifndef _VERLET_GROUND_RESPONSE_INC_LOADED_
_VERLET_GROUND_RESPONSE_INC_LOADED_ = 1
.include "verlet_contact.inc"

; Displace one coordinate of the current point by penetration * normal / 64.
.macro _VL_GROUND_PUSH normal, add_axis
        LDA     vl_pen
        LDX     vl_pen+1
        LDY     normal
        JSR     mul_dir
        JSR     mul_shr6
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        LDX     vl_cur
        JSR     add_axis
.endmacro

; Both ground types enter with vl_pen and the contact normal set. The
; height map uses the math routines, while segments inline the accumulation.
.macro _VL_GROUND_RESOLVE save_product, finish_sum
        _VL_GROUND_PUSH vl_nx, vl_add_xv
        _VL_GROUND_PUSH vl_ny, vl_add_yv
        _VL_CONTACT_VELOCITY vl_xf, vl_oxf, vl_xl, vl_oxl, vl_vx, vl_vx+1
        _VL_CONTACT_VELOCITY vl_yf, vl_oyf, vl_yh, vl_oyh, vl_vy, vl_vy+1
        ; vn = (vx nx + vy ny) >> 6
        _VL_CONTACT_PRODUCT vl_vx, vl_nx, 0
        save_product
        _VL_CONTACT_PRODUCT vl_vy, vl_ny, 0
        finish_sum
        LDA     mul_p1
        STA     vl_vn
        LDA     mul_p2
        STA     vl_vn+1
        ; vt = (vx (-ny) + vy nx) >> 6
        _VL_CONTACT_PRODUCT vl_vx, vl_ny, 1
        save_product
        _VL_CONTACT_PRODUCT vl_vy, vl_nx, 0
        finish_sum
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
        _VL_CONTACT_PRODUCT vl_vn, vl_nx, 0
        save_product
        _VL_CONTACT_PRODUCT vl_vt, vl_ny, 1
        finish_sum
        LDA     mul_p1
        STA     vl_val
        LDA     mul_p2
        STA     vl_val+1
        _VL_CONTACT_OLD_POSITION vl_val, vl_val+1, vl_xf, vl_oxf, vl_xl, vl_oxl, vl_xh, vl_oxh
        ; vy = (vn ny + vt nx) >> 6
        _VL_CONTACT_PRODUCT vl_vn, vl_ny, 0
        save_product
        _VL_CONTACT_PRODUCT vl_vt, vl_nx, 0
        finish_sum
.ifdef VL_Y_HIGH
        _VL_CONTACT_OLD_POSITION mul_p1, mul_p2, vl_yf, vl_oyf, vl_yh, vl_oyh, vl_yu, vl_oyu
.else
        _VL_CONTACT_OLD_POSITION mul_p1, mul_p2, vl_yf, vl_oyf, vl_yh, vl_oyh
.endif
.endmacro
.endif
