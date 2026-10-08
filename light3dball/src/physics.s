; GPL-3.0. Exact signed Q4 movement; no projection or input dependencies.
.export _step_xy, _aim_bias, _paddle_contact
.import _ball_x, _ball_y, _vel_x, _vel_y, _wall_hits
.import _paddle_x, _paddle_y
.zeropage
contact_lo: .res 1
contact_hi: .res 1
contact_limit: .res 1
.code
.macro STEP position, velocity
.local lower, upper, negate, check_upper, done
    clc
    lda position
    adc velocity
    sta position
    lda position+1
    adc velocity+1
    sta position+1
    bmi lower
    bne check_upper
    lda position
    cmp #32
    bcs done
lower:
    sec
    lda #64
    sbc position
    sta position
    lda #0
    sbc position+1
    sta position+1
    jmp negate
check_upper:
    cmp #7
    bcc done
    bne upper
    lda position
    cmp #209
    bcc done
upper:
    sec
    lda #<4000
    sbc position
    sta position
    lda #>4000
    sbc position+1
    sta position+1
negate:
    sec
    lda #0
    sbc velocity
    sta velocity
    lda #0
    sbc velocity+1
    sta velocity+1
    inc _wall_hits
done:
.endmacro
_step_xy:
    STEP _ball_x, _vel_x
    STEP _ball_y, _vel_y
    rts

; fastcall AX, offset -212..212. floor(abs(offset)/32), signed symmetrically.
; The central -31..31 interval leaves the incoming tangent unchanged.
_aim_bias:
    cpx #0
    beq @positive
    eor #255
    clc
    adc #1
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    beq @positive
    eor #255
    clc
    adc #1
    ldx #255
    rts
@positive:
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    ldx #0
    rts

; Perspective tolerance in Q4: half-width 144 + abs(paddle_x-64),
; half-height 160 + abs(paddle_y-64). The center keeps the original box;
; each axis grows smoothly and symmetrically toward its screen edges.
; The adjacent ball_x/ball_y words are the game's world-coordinate pair.
_paddle_contact:
    lda _paddle_x
    ldy #144
    ldx #0
    jsr contact_axis
    cmp #0
    beq contact_miss
    lda _paddle_y
    ldy #160
    ldx #2
contact_axis:
    pha
    sec
    sbc #64
    bcs @absolute
    eor #255
    clc
    adc #1
@absolute:
    sty contact_limit
    clc
    adc contact_limit
    sta contact_limit
    pla
    sta contact_hi
    asl a
    asl a
    asl a
    asl a
    sta contact_lo
    lda contact_hi
    lsr a
    lsr a
    lsr a
    lsr a
    sta contact_hi
    sec
    lda _ball_x,x
    sbc contact_lo
    sta contact_lo
    lda _ball_x+1,x
    sbc contact_hi
    bmi @negative
    bne contact_miss
    lda contact_lo
    jmp @compare
@negative:
    cmp #255
    bne contact_miss
    lda contact_lo
    eor #255
    clc
    adc #1
    bcs contact_miss       ; -256 or farther cannot fit a byte-sized radius
@compare:
    cmp contact_limit
    bcc @hit
    bne contact_miss
@hit:
    lda #1
    ldx #0
    rts
contact_miss:
    lda #0
    ldx #0
    rts
