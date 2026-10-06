.include "layout.inc"
; Bounded 65C02 motion for up to three balls, plus two fast laser bolts.
.setcpu "65C02"
.macpack longbranch
.importzp _ball_x,_ball_y,_ball_live,_dx,_dy,_vx,_vy,_fraction_x,_fraction_y
.importzp _effect, _pad_y
.import _bricks,_state,_refresh,_extra_ball
.import _collision_cached,_collision_cache_reset,_damage,_rebound,_sound_event
.import _shot_live,_shot_x,_shot_y,_cell_col,_cell_row
.export _ball_step,_ball_swap,_lasers_step
.bss
old_position: .res 1
brick_hit: .res 1
pad_line: .res 1
pad_bottom: .res 1
shot_index: .res 1
shot_steps: .res 1
shot_row: .res 1
.code
_ball_swap:
        tax
        asl
        asl
        asl
        cpx #0
        beq :+
        inc
:       tax
.macro swap variable,offset
        lda variable
        ldy _extra_ball+offset,x
        sta _extra_ball+offset,x
        sty variable
.endmacro
        swap _ball_x,0
        swap _ball_y,1
        swap _ball_live,2
        swap _dx,3
        swap _dy,4
        swap _vx,5
        swap _vy,6
        swap _fraction_x,7
        swap _fraction_y,8
        rts
_ball_step:
        lda _fraction_x
        clc
        adc _vx
        sta _fraction_x
        jcc vertical
        lda _ball_x
        sta old_position
        lda _dx
        bmi moving_left
        lda _ball_x
        cmp #133
        bcs reverse_x
        bra move_x
moving_left:
        lda _ball_x
        cmp #5
        bcs move_x
reverse_x:
        lda _dx
        eor #$FF
        inc
        sta _dx
        lda #1
        jsr _sound_event
move_x:
        lda _ball_x
        clc
        adc _dx
        sta _ball_x
        jsr _collision_cached
        cmp #255
        beq vertical
        sta brick_hit
        jsr pierce
        bcs damage_x
        lda old_position
        sta _ball_x
        lda _dx
        eor #$FF
        inc
        sta _dx
damage_x:
        lda brick_hit
        jsr _damage
        ; Only a damage callback can change state during horizontal motion.
        lda _refresh
        jne done
        lda _state
        cmp #1
        jne done
vertical:
        lda _fraction_y
        clc
        adc _vy
        sta _fraction_y
        jcc done
        lda _ball_y
        sta old_position
        lda _dy
        bpl move_y
        lda _ball_y
        cmp #CB_FIELD_TOP+1
        bcs move_y
        lda #1
        sta _dy
        jsr _sound_event
move_y:
        lda _ball_y
        clc
        adc _dy
        sta _ball_y
        lda _dy
        bmi hit_y
        lda _pad_y
        sec
        sbc #5
        sta pad_line
        lda _ball_y
        cmp #CB_LOST_Y
        bcs lost
        cmp pad_line
        bcc hit_y
        lda old_position
        cmp pad_line
        bcs hit_y
        ; Round ball spans x..x+2 and first crosses the paddle at pad_y-5.
        lda _ball_x
        clc
        adc #2
        cmp _pad_x
        bcc hit_y
        lda _pad_x
        clc
        adc _pad_width
        cmp _ball_x
        beq hit_y
        bcc hit_y
        jmp _rebound
hit_y:
        jsr _collision_cached
        cmp #255
        beq done
        sta brick_hit
        jsr pierce
        bcs damage_y
        lda old_position
        sta _ball_y
        lda _dy
        eor #$FF
        inc
        sta _dy
damage_y:
        lda brick_hit
        jmp _damage
lost:   stz _ball_live
done:   rts
.import _pad_x,_pad_width
; Piercing destroys a destructible brick in one hit and retains direction.
; Steel always reflects, scores nothing, and remains indestructible.
pierce:
        lda _effect
        cmp #6
        bne solid
        ldx brick_hit
        lda _bricks,x
        cmp #255
        beq solid
        lda #1
        sta _bricks,x
        sec
        rts
solid:  clc
        rts
_lasers_step:
        lda #1
        sta shot_index
next_shot:
        ldx shot_index
        lda _shot_live,x
        jeq shot_done
        lda _shot_y,x
        cmp #CB_GRID_END+8
        bcc scan_shot
        sec
        sbc #8
        sta _shot_y,x
        bra shot_done
scan_shot:
        lda #8
        sta shot_steps
shot_pixel:
        ldx shot_index
        dec _shot_y,x
        lda _shot_y,x
        cmp #CB_FIELD_TOP
        bcc absorb
        tay
        lda _cell_row,y
        cmp #255
        beq shot_empty
        sta shot_row
        lda _shot_x,x
        tay
        lda _cell_col,y
        cmp #255
        beq shot_empty
        clc
        adc shot_row
        tay
        lda _bricks,y
        beq shot_empty
        stz _shot_live,x
        tya
        jsr _damage
        lda _state
        cmp #1
        jne done
        lda _refresh
        jne done
        bra shot_done
shot_empty:
        dec shot_steps
        bne shot_pixel
        bra shot_done
absorb: stz _shot_live,x
shot_done:
        dec shot_index
        jpl next_shot
        rts

; Four bounded particles and four tracked flashes; no software-stack indexing.
.export _effects_tick
.import _particle_x, _particle_y, _particle_life, _particle_dx
.import _flash_slot, _flash_life, _mark_dirty
_effects_tick:
        ldx #3
@actor:
        ldy _flash_slot,x
        cpy #255
        beq @particle
        lda _flash_life,y
        beq @clear_flash
        dec
        sta _flash_life,y
        bne @particle
        phx
        tya
        jsr _mark_dirty
        plx
@clear_flash:
        lda #255
        sta _flash_slot,x
@particle:
        lda _particle_life,x
        beq @next
        dec
        sta _particle_life,x
        cmp #4
        bcc @down
        dec _particle_y,x
        bra @move
@down: inc _particle_y,x
@move: lda _particle_x,x
        clc
        adc _particle_dx,x
        sta _particle_x,x
        cmp #4
        bcc @expire
        cmp #136
        bcs @expire
        lda _particle_y,x
        cmp #CB_FIELD_TOP
        bcc @expire
        cmp #CB_PAD_Y
        bcc @next
@expire:
        stz _particle_life,x
@next: dex
        bpl @actor
        rts

; The paddle moves before the balls: one sliding under a falling ball, or
; rising into it, must still bounce it. A ball overlapping the paddle box
; rebounds when falling, and is lifted above the paddle when rising.
paddle_contact:
        lda _ball_live
        beq @no
        lda _pad_y
        sec
        sbc #5
        sta pad_line
        lda _ball_y
        cmp pad_line
        bcc @no
        lda _pad_y
        clc
        adc #5
        sta pad_bottom
        lda _ball_y
        cmp pad_bottom
        bcs @no
        lda _ball_x
        clc
        adc #2
        cmp _pad_x
        bcc @no
        lda _pad_x
        clc
        adc _pad_width
        cmp _ball_x
        beq @no
        bcc @no
        lda _dy
        bmi @lift
        jmp _rebound
@lift:  lda pad_line
        dec
        sta _ball_y
@no:    rts

; Retain every collision substep, dynamic speed changes and actor swap-back.
.export _advance_balls
.importzp _speed
.import _timing_scan
.zeropage
motion_actor: .res 1
motion_step: .res 1
.code
_advance_balls:
        stz motion_actor
@actor:
        lda _state
        cmp #1
        bne @done
        lda _refresh
        bne @done
        lda motion_actor
        beq @steps
        dec
        jsr _ball_swap
@steps:
        jsr paddle_contact
        jsr _collision_cache_reset
        stz motion_step
@step:
        lda motion_step
        cmp _speed
        bcs @swap_back
        lda _ball_live
        beq @swap_back
        lda _state
        cmp #1
        bne @swap_back
        lda _refresh
        bne @swap_back
        jsr _ball_step
        ; A substep is ~160 cycles: every fourth scan still sees each blank.
        lda motion_step
        and #3
        bne :+
        jsr _timing_scan
:       inc motion_step
        bra @step
@swap_back:
        lda motion_actor
        beq @next
        dec
        jsr _ball_swap
@next: inc motion_actor
        lda motion_actor
        cmp #3
        bcc @actor
@done: rts
