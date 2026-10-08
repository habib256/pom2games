; GPL-3.0. Packed 128-unit obstacle grid, independent of drawing/ball state.
.export _load_level, _opening
.import _level_maps, _level_counts, _level_length, _level_slots, _door_phase
.import _aperture_l, _aperture_r, _aperture_moving, _plane
.zeropage
level_ptr: .res 2
level_code: .res 1
.code
_load_level:
    tax
    lda _level_counts,x
    sta _level_slots
    lsr a
    sta _level_length+1
    lda #0
    sta _level_length
    lda level_offsets,x
    clc
    adc #<_level_maps
    sta level_ptr
    lda #>_level_maps
    adc #0
    sta level_ptr+1
    rts
level_offsets: .byte 0,24,48,72,96
opening_widths: .byte 48,40,44,36

; fastcall A=slot (0..23). plane=(slot+1)*128. Empty cells open the whole
; section. Moving doors have a separate phase offset; first two walls fixed.
_opening:
    tay
    lda (level_ptr),y
    sta level_code
    iny
    tya
    lsr a
    sta _plane+1
    lda #0
    ror a
    sta _plane
    lda #0
    sta _aperture_l
    sta _aperture_moving
    lda #127
    sta _aperture_r
    lda level_code
    beq @done
    lsr a
    lsr a
    lsr a
    lsr a
    and #3
    tax
    lda level_code
    bmi @moving
    and #64
    bne @left
    lda opening_widths,x
    sta _aperture_r
    rts
@left:
    lda #128
    sec
    sbc opening_widths,x
    sta _aperture_l
    rts
@moving:
    lda #1
    sta _aperture_moving
    lda level_code
    and #15
    asl a
    clc
    adc _door_phase
    and #31
    cmp #16
    bcc @position
    eor #31
@position:
    asl a
    asl a
    clc
    adc #8
    sta _aperture_l
    clc
    adc opening_widths,x
    sta _aperture_r
@done:
    rts
