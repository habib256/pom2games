.include "layout.inc"
; VERHILLE Arnaud — GPL-3.0. Two drifting 4x6 enemies, Arkanoid style
; (a spool that wanders, a TIE fighter that weaves).
; They never enter a tile: blocked sideways they turn back, blocked downward
; they slide along the tiles until a gap opens. Below the tile grid they
; wander, and they leave through the floor. A ball (which rebounds), a laser
; or the paddle destroys one: enemy_hit gets its bit for the C side to score.
.setcpu "65C02"
.macpack longbranch
.importzp _ball_x, _ball_y, _ball_live, _dy, _pad_y
.import _bricks, _cell_col, _cell_row, _extra_ball, _pad_x, _pad_width
.import _shot_live, _shot_x, _shot_y, _frames
.import _enemy_live, _enemy_x, _enemy_y, _enemy_dx, _enemy_dy, _enemy_color
.export _enemies_tick, _enemy_blocked, _enemy_hit, _enemy_probe_x, _enemy_probe_y
.zeropage
_enemy_probe_x: .res 1
_enemy_probe_y: .res 1
.bss
row_base: .res 1
ox: .res 1
ow: .res 1
oy: .res 1
oh: .res 1
ex4: .res 1
ey6: .res 1
far: .res 1
_enemy_hit: .res 1
seed: .res 1
.rodata
; Shimmering orb: the color turns every four game ticks (never ball white).
palette: .byte 9,13,12,14,7,3,11,1
phase: .byte 0,4
kill_bit: .byte 1,2
wander_dy: .byte 1,1,0,255
; Wave of the second enemy: 20 dots down, 12 up, every 32 ticks.
weave_dy: .byte 1,1,1,1,1,255,255,255
.code
; A=x, Y=y: tile value under that color pixel (0 when empty). Keeps X.
tile_at:
        pha
        lda _cell_row,y
        cmp #255
        beq @none
        sta row_base
        ply
        lda _cell_col,y
        cmp #255
        beq @empty
        clc
        adc row_base
        tay
        lda _bricks,y
        rts
@none:  pla
@empty: lda #0
        rts

; Nonzero when a 4x6 box at enemy_probe_x/y overlaps a tile. Corners
; suffice: every tile is wider and taller than an enemy. Keeps X.
_enemy_blocked:
        lda _enemy_probe_x
        ldy _enemy_probe_y
        jsr tile_at
        bne @done
        lda _enemy_probe_x
        clc
        adc #3
        ldy _enemy_probe_y
        jsr tile_at
        bne @done
        lda _enemy_probe_y
        clc
        adc #5
        sta far
        lda _enemy_probe_x
        ldy far
        jsr tile_at
        bne @done
        lda _enemy_probe_x
        clc
        adc #3
        ldy far
        jsr tile_at
@done:  ldx #0
        rts

; C=1 when box ox,oy (ow x oh) overlaps enemy X (ex4/ey6 precomputed).
overlap:
        lda ox
        cmp ex4
        bcs @no
        clc
        adc ow
        sta far
        lda _enemy_x,x
        cmp far
        bcs @no
        lda oy
        cmp ey6
        bcs @no
        clc
        adc oh
        sta far
        lda _enemy_y,x
        cmp far
        bcs @no
        sec
        rts
@no:    clc
        rts

_enemies_tick:
        stz _enemy_hit
        lda seed
        bne :+
        lda #$A5
:       asl
        bcc :+
        eor #$1D
:       sta seed
        ldx #1
enemy_loop:
        lda _enemy_live,x
        jeq enemy_next
        lda _frames
        lsr
        lsr
        clc
        adc phase,x
        and #7
        tay
        lda palette,y
        sta _enemy_color,x
        ; Horizontal step: walls and tiles turn it back.
        lda _enemy_x,x
        clc
        adc _enemy_dx,x
        sta _enemy_probe_x
        cmp #4
        bcc turn_x
        cmp #133
        bcs turn_x
        lda _enemy_y,x
        sta _enemy_probe_y
        phx
        jsr _enemy_blocked
        plx
        cmp #0
        bne turn_x
        lda _enemy_probe_x
        sta _enemy_x,x
        bra wander
turn_x:
        lda _enemy_dx,x
        eor #$FF
        inc
        sta _enemy_dx,x
wander:
        ; Below the grid, the first picks a new heading every sixteen ticks;
        ; the second weaves down in waves.
        lda _enemy_y,x
        cmp #CB_GRID_END+2
        bcc move_y
        cpx #1
        bne :+
        lda _frames
        lsr
        lsr
        and #7
        tay
        lda weave_dy,y
        sta _enemy_dy,x
        bra move_y
:       lda _frames
        and #15
        bne move_y
        lda seed
        and #3
        tay
        lda wander_dy,y
        sta _enemy_dy,x
        lda seed
        and #4
        beq move_y
        lda _enemy_dx,x
        eor #$FF
        inc
        sta _enemy_dx,x
move_y:
        lda _enemy_dy,x
        beq hits
        clc
        adc _enemy_y,x
        sta _enemy_probe_y
        lda _enemy_dy,x
        bmi moving_up
        lda _enemy_probe_y
        cmp #CB_LOST_Y-5
        bcc check_y
        stz _enemy_live,x
        jmp enemy_next
moving_up:
        lda _enemy_probe_y
        cmp #CB_FIELD_TOP+1
        bcc fall_back
        ; A wanderer stays below the grid.
        lda _enemy_y,x
        cmp #CB_GRID_END+2
        bcc check_y
        lda _enemy_probe_y
        cmp #CB_GRID_END+2
        bcc fall_back
check_y:
        lda _enemy_x,x
        sta _enemy_probe_x
        phx
        jsr _enemy_blocked
        plx
        cmp #0
        bne blocked_y
        lda _enemy_probe_y
        sta _enemy_y,x
        bra hits
blocked_y:
        ; Downward: wait here and keep sliding sideways along the tiles.
        lda _enemy_dy,x
        bpl hits
fall_back:
        lda #1
        sta _enemy_dy,x
hits:
        lda _enemy_x,x
        clc
        adc #4
        sta ex4
        lda _enemy_y,x
        clc
        adc #6
        sta ey6
        lda _pad_x
        sta ox
        lda _pad_width
        sta ow
        lda _pad_y
        sta oy
        lda #5
        sta oh
        jsr overlap
        bcs kill
        lda #3
        sta ow
        lda #6
        sta oh
        lda _ball_live
        beq extras
        lda _ball_x
        sta ox
        lda _ball_y
        sta oy
        jsr overlap
        bcc extras
        lda _dy
        eor #$FF
        inc
        sta _dy
        bra kill
extras:
        ldy #0
extra_ball:
        lda _extra_ball+2,y
        beq extra_next
        lda _extra_ball,y
        sta ox
        lda _extra_ball+1,y
        sta oy
        jsr overlap
        bcc extra_next
        lda _extra_ball+4,y
        eor #$FF
        inc
        sta _extra_ball+4,y
        bra kill
extra_next:
        cpy #9
        beq shots
        ldy #9
        bra extra_ball
shots:
        lda #1
        sta ow
        lda #4
        sta oh
        ldy #1
shot:
        lda _shot_live,y
        beq shot_next
        lda _shot_x,y
        sta ox
        lda _shot_y,y
        sta oy
        jsr overlap
        bcc shot_next
        lda #0
        sta _shot_live,y
        bra kill
shot_next:
        dey
        bpl shot
        bra enemy_next
kill:
        stz _enemy_live,x
        lda kill_bit,x
        tsb _enemy_hit
enemy_next:
        dex
        jpl enemy_loop
        rts
