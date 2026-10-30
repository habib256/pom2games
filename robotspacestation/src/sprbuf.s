; Robot Space Station — sprites composed off screen (src/sprites.c): the
; bytes under a sprite are read into spr_buf, its rectangles painted there,
; then written back at once, so no pixel shows a passing colour (no
; flicker). spr_buf holds interleaved DHGR bytes (dhgr_read_block), 7 a
; row; pixel 0 starts at bit spr_phase of byte 0.
.setcpu "65C02"
.importzp ptr1, tmp1, tmp2
.export _spr_paint, _spr_buf, _spr_r, _spr_n, _spr_w, _spr_west, _spr_phase
.export _spr_special

STRIDE = 7

.segment "BSS"
_spr_buf: .res STRIDE*12
_spr_r: .res 2                          ; the rectangles: x, y, w, h, colour
_spr_n: .res 1                          ; how many
_spr_w: .res 1                          ; the box's width (mirroring)
_spr_west: .res 1                       ; mirrored
_spr_phase: .res 1
_spr_special: .res 5                    ; colours 16..20
lo: .res 7                              ; the colour's nibble at bit q: byte j
hi: .res 7                              ; and byte j+1
rw: .res 1
rh: .res 1
j0: .res 1
q0: .res 1
rowbase: .res 1
cnt: .res 1
q: .res 1

.segment "HIDATA"
; Bits q..q+3 cleared in byte j (mlo) and byte j+1 (mhi, q >= 4).
mlo:    .byte $70, $61, $43, $07, $0F, $1F, $3F
mhi:    .byte $7F, $7F, $7F, $7F, $7E, $7C, $78

.segment "HICODE"
; spr_paint(): spr_n rectangles from spr_r into spr_buf, in order.
_spr_paint:
        lda _spr_r
        sta ptr1
        lda _spr_r+1
        sta ptr1+1
@rect:  lda _spr_n
        bne @colour
        rts
@colour:
        ldy #4
        lda (ptr1),y
        cmp #16
        bcc @plain
        tax
        lda _spr_special-16,x
@plain: and #15                         ; the nibble: ((c >> 1) | (c << 3)) & 15
        sta tmp1
        lsr a
        sta tmp2
        lda tmp1
        asl a
        asl a
        asl a
        ora tmp2
        and #15
        sta tmp1                        ; nibble << q, q = 0..6, over 11 bits
        stz tmp2
        ldx #0
@tab:   lda tmp1
        and #$7F
        sta lo,x
        lda tmp1
        asl a
        lda tmp2
        rol a
        sta hi,x
        asl tmp1
        rol tmp2
        inx
        cpx #7
        bne @tab
        ldy #2
        lda (ptr1),y
        sta rw
        iny
        lda (ptr1),y
        sta rh
        lda (ptr1)                      ; x; west: w - x - width
        ldx _spr_west
        beq @east
        eor #$FF
        sec
        adc _spr_w
        sec
        sbc rw
@east:  asl a                           ; bit phase + 4x: byte j0, bit q0
        asl a
        clc
        adc _spr_phase
        ldx #0
@div:   cmp #7
        bcc @divd
        sbc #7
        inx
        bra @div
@divd:  sta q0
        stx j0
        ldy #1                          ; rowbase = y * STRIDE
        lda (ptr1),y
        tax
        lda #0
        cpx #0
        beq @rb
@mul:   clc
        adc #STRIDE
        dex
        bne @mul
@rb:    sta rowbase
@row:   lda rowbase
        clc
        adc j0
        tay
        lda q0
        sta q
        lda rw
        sta cnt
@px:    ldx q
        lda _spr_buf,y
        and mlo,x
        ora lo,x
        sta _spr_buf,y
        cpx #4
        bcc @adv
        lda _spr_buf+1,y
        and mhi,x
        ora hi,x
        sta _spr_buf+1,y
@adv:   txa
        clc
        adc #4
        cmp #7
        bcc @same
        sbc #7
        iny
@same:  sta q
        dec cnt
        bne @px
        lda rowbase
        clc
        adc #STRIDE
        sta rowbase
        dec rh
        bne @row
        lda ptr1
        clc
        adc #5
        sta ptr1
        bcc @n
        inc ptr1+1
@n:     dec _spr_n
        bra @rect
