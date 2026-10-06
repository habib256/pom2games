.include "layout.inc"
; Exact round-ball collision using two row candidates.
; A three-color-pixel ball cannot bridge the two-pixel gap between bricks.
; If its central column is inside a brick, the full six-row center is solid.
; Otherwise only a side's middle four rows can touch that brick column.
.setcpu "65C02"
.macpack longbranch
.importzp _ball_x, _ball_y
.import _cell_col, _cell_row, _bricks
.importzp tmp1,tmp2,tmp3
.export _collision
.code
_collision:
        lda _ball_y
        cmp #CB_GRID_END
        bcs empty
        ldx _ball_x
        cpx #138
        bcs empty
        inx
        lda _cell_col,x
        cmp #255
        beq side
        sta tmp1
        lda #5
        sta tmp3
        ldy _ball_y
        bra first_row
side:   dex
        lda _cell_col,x
        cmp #255
        bne side_column
        inx
        inx
        lda _cell_col,x
        cmp #255
        beq empty
side_column:
        sta tmp1
        lda #3
        sta tmp3
        ldy _ball_y
        iny
first_row:
        lda _cell_row,y
        sta tmp2
        cmp #255
        beq second_row
        clc
        adc tmp1
        tax
        lda _bricks,x
        bne found
second_row:
        tya
        clc
        adc tmp3
        tay
        lda _cell_row,y
        cmp tmp2
        beq empty
        cmp #255
        beq empty
        clc
        adc tmp1
        tax
        lda _bricks,x
        bne found
empty:  lda #255
        ldx #0
        rts
found:  txa
        ldx #0
        rts

; A per-actor cache covers only full empty grid rows in one brick column.
; Reset before each actor: board edits between frames cannot retain a miss.
.export _collision_cached, _collision_cache_reset
.zeropage
cache_x: .res 1
cache_low: .res 1
cache_high: .res 1
cache_start: .res 1
.rodata
grid_row:
.repeat CB_GRID_END,I
.if I<CB_TILE_TOP
.byte 255
.else
.byte ((I-CB_TILE_TOP)/12)*12
.endif
.endrepeat
.code
_collision_cache_reset:
        lda #255
        sta cache_low
        rts
_collision_cached:
        lda _ball_y
        cmp #CB_GRID_END
        jcs cached_empty
        ldx _ball_x
        cpx #138
        jcs cached_empty
        cpx cache_x
        bne cache_rebuild
        cmp cache_low
        bcc cache_rebuild
        cmp cache_high
        jcc cached_empty
cache_rebuild:
        stx cache_x
        lda #255
        sta cache_low
        inx
        lda _cell_col,x
        cmp #255
        bne cache_column
        dex
        lda _cell_col,x
        cmp #255
        bne cache_column
        inx
        inx
        lda _cell_col,x
        cmp #255
        jeq cached_empty
cache_column:
        sta tmp1
        ldy _ball_y
        lda grid_row,y
        cmp #255
        beq cache_exact
        sta tmp2
        clc
        adc #CB_TILE_TOP
        sta cache_start
        lda tmp2
        clc
        adc tmp1
        tax
        lda _bricks,x
        bne cache_exact
        lda cache_start
        sta cache_low
        clc
        adc #7
        sta cache_high
        lda tmp2
        cmp #84
        bcs cache_two_rows
        txa
        clc
        adc #12
        tax
        lda _bricks,x
        bne cache_test_range
cache_two_rows:
        lda cache_high
        clc
        adc #12
        sta cache_high
cache_test_range:
        lda _ball_y
        cmp cache_high
        jcc cached_empty
cache_exact:
        jmp _collision
cached_empty:
        lda #255
        ldx #0
        rts
