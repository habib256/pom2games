; GPL-3.0. Exact signed Q4 movement; no projection or input dependencies.
.export _step_xy, _aim_bias, _paddle_contact
.import _ball_x, _ball_y, _vel_x, _vel_y, _wall_hits
.import _paddle_x, _paddle_y
.zeropage
contact_lo: .res 1
contact_hi: .res 1
contact_limit: .res 1
contact_limit_hi: .res 1
aim_negative: .res 1
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

; fastcall AX, offset -312..312. floor(abs(offset)/32), signed symmetrically.
; The central -31..31 interval leaves the incoming tangent unchanged.
_aim_bias:
    sta contact_lo
    stx contact_hi
    txa
    and #128
    sta aim_negative
    beq @absolute
    lda contact_lo
    eor #255
    clc
    adc #1
    sta contact_lo
    lda contact_hi
    eor #255
    adc #0
    sta contact_hi
@absolute:
    .repeat 5
        lsr contact_hi
        ror contact_lo
    .endrepeat
    lda contact_lo
    ldx aim_negative
    beq @positive
    cmp #0
    beq @positive
    eor #255
    clc
    adc #1
    ldx #255
    rts
@positive:
    ldx #0
    rts

; Perspective tolerance in Q4: half-width 256 + abs(paddle_x-64),
; half-height 240 + abs(paddle_y-64). Full 16-bit limits let the large
; paddle accept aiming offsets beyond one byte without wraparound;
; each axis grows smoothly and symmetrically toward its screen edges.
; The adjacent ball_x/ball_y words are the game's world-coordinate pair.
_paddle_contact:
    lda #1
    sta contact_limit_hi
    lda _paddle_x
    ldy #0
    ldx #0
    jsr contact_axis
    cmp #0
    beq contact_miss
    lda #0
    sta contact_limit_hi
    lda _paddle_y
    ldy #240
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
    bcc @limit_ready
    inc contact_limit_hi
@limit_ready:
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
    sta contact_hi
    bpl @compare
    lda contact_lo
    eor #255
    clc
    adc #1
    sta contact_lo
    lda contact_hi
    eor #255
    adc #0
    sta contact_hi
@compare:
    lda contact_hi
    cmp contact_limit_hi
    bcc @hit
    bne contact_miss
    lda contact_lo
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
