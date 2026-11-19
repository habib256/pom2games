; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.ifndef _VERLET_CONTACT_INC_LOADED_
_VERLET_CONTACT_INC_LOADED_ = 1

; Signed 8.8 velocity of point X on one axis. Relative velocities use
; separate scratch slots for the two result bytes.
.macro _VL_CONTACT_VELOCITY frac, old_frac, whole, old_whole, low, high
        SEC
        LDA     frac,X
        SBC     old_frac,X
        STA     low
        LDA     whole,X
        SBC     old_whole,X
        STA     high
.endmacro

; Multiply a signed velocity component by a component of the contact
; direction. The tangent uses -ny, formed before loading the velocity.
.macro _VL_CONTACT_PRODUCT velocity, direction, negate
        .if negate
        SEC
        LDA     #0
        SBC     direction
        TAY
        .endif
        LDA     velocity
        LDX     velocity+1
        .if !negate
        LDY     direction
        .endif
        JSR     mul_dir
.endmacro

; Encode the new signed 8.8 velocity in the previous position.
.macro _VL_CONTACT_OLD_POSITION low, high, frac, old_frac, whole, old_whole, upper, old_upper
        LDX     vl_cur
        .ifnblank upper
        _VL_OFFSET_SIGN high, 1
        STY     vl_w2
        .endif
        SEC
        LDA     frac,X
        SBC     low
        STA     old_frac,X
        LDA     whole,X
        SBC     high
        STA     old_whole,X
        .ifnblank upper
        LDA     upper,X
        SBC     vl_w2
        STA     old_upper,X
        .endif
.endmacro

.endif
