; Gameplay shared in spirit with ChromaBreak, NMOS 6502 / 48K.
.code
; Native pixel-to-cell lookups avoid repeated 21/12 divisions for every
; ball corner and substep, particularly with three balls at Expert speed.
build_collision_tables:
        lda #255
        ldx #0
@empty: sta collision_row,x
        sta collision_col,x
        inx
        bne @empty
        ldx #0
        ldy #24
@row:   txa
.repeat 8,I
        sta collision_row+I,y
.endrepeat
        tya
        clc
        adc #12
        tay
        txa
        clc
        adc #12
        tax
        cpx #96
        bcc @row
        ldx #0
        ldy #1
@col:   txa
.repeat 18,I
        sta collision_col+I,y
.endrepeat
        tya
        clc
        adc #21
        tay
        inx
        cpx #12
        bcc @col
        rts

mark_dirty:
        lda dirty1,x
        bne :+
        inc dirty_counts
:       lda dirty2,x
        bne :+
        inc dirty_counts+1
:       lda #1
        sta dirty1,x
        sta dirty2,x
        rts
unpack_cell:
        cmp #15
        bne :+
        lda #255
:       sta bricks,x
        cmp #0
        beq @mark
        cmp #255
        beq @mark
        inc remaining
@mark:  lda #1
        sta dirty1,x
        sta dirty2,x
        inx
        rts

fetch_level:
        lda level
        ldx #0
@decade:
        cmp #10
        bcc @found
        sec
        sbc #10
        inx
        bne @decade
@found: sta pack_offset
        stx pack_number
        cpx current_pack
        beq @address
        txa
        clc
        adc #'1'
        sta pack_command+12
        jsr dos_cmd_new
        lda #<pack_command
        ldy #>pack_command
        jsr dos_cmd_add
        jsr dos_cmd_run
        lda pack_number
        sta current_pack
@address:
        lda #<level_pack
        sta level_ptr
        lda #>level_pack
        sta level_ptr+1
        ldx pack_offset
        beq @name
@offset:
        lda level_ptr
        clc
        adc #58
        sta level_ptr
        bcc :+
        inc level_ptr+1
:       dex
        bne @offset
@name:  ldy #48
        ldx #0
@letter:
        lda (level_ptr),y
        sta level_name,x
        iny
        inx
        cpx #10
        bne @letter
        lda #0
        sta level_name+10
        rts

; Paddle never enters a brick, including horizontal sweeps and growing width.
; At y>=128 it is wholly below the grid; this is the cheap usual path.
clamp_height:
        lda pad_y
        cmp #100
        bcs :+
        lda #100
:       cmp #176
        bcc :+
        lda #175
:       sta pad_y
        cmp #128
        bcs @done
        ; Walk the swept horizontal interval under the bottom tile row.
        lda pad_x
        cmp previous_x
        bcc :+
        lda previous_x
:       sta cx
        lda pad_x
        cmp previous_x
        bcs :+
        lda previous_x
:       clc
        adc pad_width
        sta pending_edge
@probe: ldx cx
        lda collision_col,x
        cmp #255
        beq @gap
        lda pad_y
        sec
        sbc #5
        sta cy
        jsr point_hit
        bcs @blocked
        lda pad_y
        clc
        adc #2
        sta cy
        jsr point_hit
        bcs @blocked
        ; Every pixel of this brick column has the same collision result.
        ; Probe the next solid column rather than walking the paddle pixel by pixel.
        ldx cx
        lda collision_col,x
        tax
        lda col21,x
        clc
        adc #22
        sta cx
        jmp @range
@gap:   inc cx
@range: lda cx
        cmp pending_edge
        bcc @probe
@done:  rts
@blocked:
        ; Stay beneath the lowest tile; no path through bricks or walls.
        lda #128
        sta pad_y
        rts

paddle_contact:
        lda ball_live
        beq @done
        lda ball_diry
        bne @done
        lda ball_y
        clc
        adc #3
        cmp pad_y
        bcc @done
        lda previous_y
        cmp pad_y
        bcs :+
        lda pad_y
:       clc
        adc #4
        cmp ball_y
        bcc @done
        lda ball_x
        clc
        adc #2
        cmp pad_x
        bcc @done
        lda pad_x
        clc
        adc pad_width
        cmp ball_x
        bcc @done
        beq @done
        lda #1
        sta ball_diry
        sta multiplier
        lda #0
        sta combo
        lda pad_y
        sec
        sbc #3
        sta ball_y
        jsr paddle_angle
        lda #2
        sta pending
        lda effect
        cmp #3
        bne @hud
        lda ball_x
        sec
        sbc pad_x
        bcs :+
        lda #0
:       sta catch_offset
        lda #0
        sta ball_live
@hud:   jmp hud_dirty
@done:  rts

; Swap nine contiguous bytes; ball_step always uses the same working record.
swap_ball:
        ldx ball_id
        lda ball_offsets,x
        tay
        ldx #0
@byte:  lda ball_x,x
        pha
        lda extra_balls,y
        sta ball_x,x
        pla
        sta extra_balls,y
        iny
        inx
        cpx #9
        bne @byte
        rts
advance_balls:
        lda ball_live
        bne @main
        lda extra_balls+2
        bne @promote0
        lda extra_balls+11
        beq @attached
        lda #1
        bne @promote
@promote0:
        lda #0
@promote:
        sta ball_id
        jsr swap_ball
@main:  lda speed
        sta steps_left
@main_step:
        jsr ball_step
        lda remaining
        beq @done
        lda ball_live
        beq @extras
        dec steps_left
        bne @main_step
@extras:
        lda #0
        sta ball_id
@extra:
        jsr swap_ball
        lda ball_live
        beq @swap_back
        jsr paddle_contact
        lda speed
        sta steps_left
@extra_step:
        jsr ball_step
        lda remaining
        beq @swap_back
        lda ball_live
        beq @swap_back
        dec steps_left
        bne @extra_step
@swap_back:
        jsr swap_ball
        inc ball_id
        lda ball_id
        cmp #2
        bcc @extra
        lda ball_live
        ora extra_balls+2
        ora extra_balls+11
        bne @done
        lda ball_y
        cmp #180
        bcc @attached
        dec lives
        jsr hud_dirty
        lda lives
        beq @dead
        jsr reset_ball
@attached:
        jsr attach_ball
@done:  rts
@dead:  lda #2
        sta state
        jsr ending
        rts

apply_effect:
        lda #0
        sta shot_live
        sta shot_live+1
        sta laser_cooldown
        lda normal_speed
        sta speed
        lda effect
        cmp #2
        bne :+
        lda #2
        sta speed
:       lda effect
        cmp #3
        bne @multi
        lda #0
        sta extra_balls+2
        sta extra_balls+11
@multi: cmp #4
        bne @done
        lda enemy_live
        beq :+
        lda #10
        jsr award
:       lda enemy_live+1
        beq :+
        lda #10
        jsr award
:       lda #0
        sta enemy_live
        sta enemy_live+1
        sta ball_id
        lda #1
        sta ball_live
        sta ball_diry
        lda #0
        sta ball_dirx
        lda #32
        sta ball_speed
        lda #224
        sta ball_yspeed
@copy:  jsr swap_ball
        ; Working record contains the former extra; replace with primary.
        ldx #8
@record:
        lda extra_balls,x
        sta ball_x,x
        dex
        bpl @record
        lda #104
        sta ball_speed
        lda #208
        sta ball_yspeed
        lda ball_id
        eor #1
        sta ball_dirx
        jsr swap_ball
        inc ball_id
        lda ball_id
        cmp #2
        bcc @copy
@done:  rts

fire_lasers:
        lda effect
        cmp #5
        bne @done
        lda laser_cooldown
        ora shot_live
        ora shot_live+1
        bne @done
        lda #1
        sta shot_live
        sta shot_live+1
        lda pad_x
        clc
        adc #2
        sta shot_x
        lda pad_x
        clc
        adc pad_width
        sec
        sbc #3
        sta shot_x+1
        lda pad_y
        sec
        sbc #4
        sta shot_y
        sta shot_y+1
        lda #8
        sta laser_cooldown
@done:  rts
lasers_step:
        lda laser_cooldown
        beq :+
        dec laser_cooldown
:       lda #0
        sta object_id
@shot:  ldx object_id
        lda shot_live,x
        beq @next
        lda #4
        sta laser_steps
@sub:   ldx object_id
        dec shot_y,x
        lda shot_y,x
        cmp #18
        bcc @erase
        sta cy
        lda shot_x,x
        sta cx
        jsr point_hit
        bcc @continue
        jsr damage
@erase: ldx object_id
        lda #0
        sta shot_live,x
        beq @next
@continue:
        dec laser_steps
        bne @sub
@next:  inc object_id
        lda object_id
        cmp #2
        bcc @shot
        rts

; Two different silhouettes, drifting through the tile gaps, 100 points each.
enemies_step:
        lda extra_balls+2
        ora extra_balls+11
        jne @done
        lda ball_live
        beq @move
        lda enemy_hold
        bne @move
        dec enemy_timer
        bne @move
        ldx difficulty
        lda enemy_periods,x
        sta enemy_timer
        ldx #0
        lda enemy_live
        beq @spawn
        inx
        lda enemy_live+1
        bne @move
@spawn: lda #1
        sta enemy_live,x
        sta enemy_dx,x
        inc enemy_gate
        lda enemy_gate
        and #3
        tay
        lda gate_x,y
        sta enemy_x,x
        lda gate_y,y
        sta enemy_y,x
        tya
        and #1
        beq @move
        lda #255
        sta enemy_dx,x
@move:  lda #0
        sta enemy_id
@enemy: ldx enemy_id
        lda enemy_live,x
        jeq @next
        lda enemy_x,x
        clc
        adc enemy_dx,x
        sta cx
        cmp #2
        bcc @turn
        cmp #245
        bcs @turn
        lda enemy_y,x
        sta cy
        jsr enemy_blocked
        bcs @turn
        ldx enemy_id
        lda cx
        sta enemy_x,x
        jmp @vertical
@turn:  ldx enemy_id
        lda enemy_dx,x
        eor #255
        clc
        adc #1
        sta enemy_dx,x
@vertical:
        ldx enemy_id
        lda enemy_x,x
        sta cx
        lda #1
        sta enemy_drift
        lda enemy_y,x
        cmp #129
        bcc @fall
        lda frames
        cpx #1
        beq @weave
        and #31
        cmp #24
        bcc @fall
        bcs @rise
@weave: lsr
        lsr
        and #7
        cmp #5
        bcc @fall
@rise:  lda #255
        sta enemy_drift
@fall:  lda enemy_y,x
        clc
        adc enemy_drift
        sta cy
        cmp #176
        jcs @leave
        jsr enemy_blocked
        bcs @hits
        ldx enemy_id
        lda cy
        sta enemy_y,x
@hits:  ldx enemy_id
        lda enemy_x,x
        sta cx
        lda enemy_y,x
        sta cy
        lda ball_live
        beq @paddle
        lda ball_x
        clc
        adc #2
        cmp cx
        bcc @paddle
        lda cx
        clc
        adc #7
        cmp ball_x
        bcc @paddle
        lda ball_y
        clc
        adc #2
        cmp cy
        bcc @paddle
        lda cy
        clc
        adc #6
        cmp ball_y
        bcc @paddle
        lda ball_diry
        eor #1
        sta ball_diry
        jmp @kill
@paddle:
        lda cx
        clc
        adc #7
        cmp pad_x
        bcc @shots
        lda pad_x
        clc
        adc pad_width
        cmp cx
        bcc @shots
        lda cy
        clc
        adc #6
        cmp pad_y
        bcc @shots
        lda pad_y
        clc
        adc #3
        cmp cy
        bcs @kill
@shots: ldy #1
@laser: lda shot_live,y
        beq @laser_next
        lda shot_x,y
        cmp cx
        bcc @laser_next
        lda cx
        clc
        adc #7
        cmp shot_x,y
        bcc @laser_next
        lda shot_y,y
        clc
        adc #3
        cmp cy
        bcc @laser_next
        lda cy
        clc
        adc #6
        cmp shot_y,y
        bcc @laser_next
        lda #0
        sta shot_live,y
        jmp @kill
@laser_next:
        dey
        bpl @laser
        jmp @next
@kill:  lda #10
        jsr award
        lda #1
        sta pending
@leave: ldx enemy_id
        lda #0
        sta enemy_live,x
@next:  inc enemy_id
        lda enemy_id
        cmp #2
        jcc @enemy
@done:  rts

; Probe 8x6 corners without destroying the caller's cx/cy.
enemy_blocked:
        lda cx
        pha
        lda cy
        pha
        jsr point_hit
        bcs @hit
        lda cx
        clc
        adc #7
        sta cx
        jsr point_hit
        bcs @hit
        lda cy
        clc
        adc #5
        sta cy
        jsr point_hit
        bcs @hit
        lda cx
        sec
        sbc #7
        sta cx
        jsr point_hit
        bcs @hit
        pla
        sta cy
        pla
        sta cx
        clc
        rts
@hit:   pla
        sta cy
        pla
        sta cx
        sec
        rts

; Per-page snapshot: two extra balls, two shots, two enemies. XOR order is
; immaterial; erase every sprite before redrawing any dirty tile.
erase_sprites:
        lda page_index
        asl
        asl
        asl
        asl
        asl
        sta history_offset
        lda #0
        sta object_id
@object:
        ldx history_offset
        lda sprite_history+2,x
        beq @next
        sta sprite_kind
        lda sprite_history,x
        sta rx
        lda sprite_history+1,x
        sta ry
        jsr small_sprite
@next:  inc history_offset
        inc history_offset
        inc history_offset
        inc object_id
        lda object_id
        cmp #6
        bcc @object
        rts
new_sprites:
        lda page_index
        asl
        asl
        asl
        asl
        asl
        sta history_offset
        lda #0
        sta object_id
@object:
        ldx object_id
        lda new_kind,x
        sta sprite_kind
        cpx #2
        bcc @ball
        cpx #4
        bcc @shot
        txa
        sec
        sbc #4
        tax
        lda enemy_x,x
        sta rx
        lda enemy_y,x
        sta ry
        lda enemy_live,x
        jmp @store
@ball:  lda ball_offsets,x
        tay
        lda extra_balls,y
        sta rx
        lda extra_balls+1,y
        sta ry
        lda extra_balls+2,y
        jmp @store
@shot:  dex
        dex
        lda shot_x,x
        sta rx
        lda shot_y,x
        sta ry
        lda shot_live,x
@store: beq :+
        lda sprite_kind
:       ldx history_offset
        sta sprite_history+2,x
        cmp #0
        beq @next
        lda rx
        sta sprite_history,x
        lda ry
        sta sprite_history+1,x
        jsr small_sprite
@next:  inc history_offset
        inc history_offset
        inc history_offset
        inc object_id
        lda object_id
        cmp #6
        bcc @object
        rts
small_sprite:
        lda sprite_kind
        cmp #2
        bcc @ball
        beq @shot
        sec
        sbc #3
        asl
        tay
        lda enemy_assets,y
        sta asset_ptr
        lda enemy_assets+1,y
        sta asset_ptr+1
        jmp glyph_sprite
@shot:  lda #1
        sta rw
        lda #4
        bne @height
@ball:  lda #3
        sta rw
@height:sta rh
        jmp rectangle

.bss
pending_edge: .res 1
laser_steps: .res 1
enemy_gate: .res 1
enemy_drift: .res 1
.rodata
ball_offsets: .byte 0,9
new_kind: .byte 1,1,2,2,3,4
enemy_periods: .byte 180,135,90
gate_x: .byte 63,189,4,240
gate_y: .byte 18,18,128,128
; Mutable command is in RAM even though grouped with constants.
pack_command: .asciiz "BLOAD LEVELS1,A$1800"
