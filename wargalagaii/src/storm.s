; WARGALAGA II -- Meteor Storm (lot 8): one logic step, in place of
; logic_step's game step. Resident at $0800 (segment STORM, memory LOWM:
; WG2.AUX at $8000, copied at boot; crt0 keeps $0800-$0FFF). Included by
; game.s. tools/model.py (storm_step) is its bit-exact reference.
;
; Rocks are aliens 0..M_ROCKS-1 in state ST_ROCK, drawn by render.s as
; flying aliens with the rock table in cur_alien (pack_check). Fire held:
; faster (m_speed + M_ACC), else slower (- M_DEC); the field falls
; M_DY0 + m_speed / 8 rows a step: rocks, coins (falling objects), and the
; stars on top of their own speed. A rock or a coin every M_SPACING rows;
; M_DIST rows to fly. A rock hits: the ship explodes, no life lost, the storm
; ends with the explosion. Through: a prize by the time taken.

.segment "STORM"
; The storm begins (level_step, at the end of a teleport).
storm_start:
        stz subgame
        lda #1
        sta storm
        stz m_speed
        stz m_acc
        stz m_time
        stz m_time+1
        stz m_crash
        lda #<M_DIST
        sta m_dist
        lda #>M_DIST
        sta m_dist+1
        lda #M_WAIT
        sta m_wait
        ldx #M_ROCKS-1
:       stz a_big,x
        lda #1
        sta a_hp,x
        dex
        bpl :-
        rts

storm_step:
        stz fire_req             ; (a press is not a shot)
        lda ship_state           ; the ship, as in the game
        sta tmp2                 ; (0: alive this step)
        bne ss_speed
        lda move_dir
        beq ss_speed
        bmi :+
        lda ship_c
        sec
        adc s_level
        cmp #SHIP_MAX+1
        bcc ss_x
        lda #SHIP_MAX
        bra ss_x
:       lda ship_c
        clc
        sbc s_level
        bcs ss_x
        lda #0
ss_x:   sta ship_c
ss_speed:
        lda tmp2                 ; fire held: faster, else slower
        bne ss_slow
        lda fire_held
        beq ss_slow
        lda m_speed
        cmp #M_SPEED_MAX
        bcs ss_dy
        adc #M_ACC
        sta m_speed
        bra ss_dy
ss_slow:
        lda m_speed
        sec
        sbc #M_DEC
        bcs :+
        lda #0
:       sta m_speed
ss_dy:  lda m_speed              ; rows the field falls
        lsr
        lsr
        lsr
        clc
        adc #M_DY0
        sta m_dy
        ldx #N_OBJ-1             ; coins fall with it
ss_obj: lda obj_y,x
        beq :++
        clc
        adc m_dy
        cmp #192-OBJ_H+1
        bcc :+
        lda #0
:       sta obj_y,x
:       dex
        bpl ss_obj
        lda m_dy                 ; stars: their speed + dy / 2
        lsr
        sta tmp
        ldx #NSTARS-1
ss_star:
        lda star_y,x
        clc
        adc star_speed,x
        adc tmp
        cmp #192
        bcc :++
        sbc #192-FIELD_TOP
        pha
        lda star_col,x
        adc #17-1                ; carry is set
        cmp #STAR_COLS
        bcc :+
        sbc #STAR_COLS
:       sta star_col,x
        pla
:       sta star_y,x
        dex
        bpl ss_star
        stz nfly                 ; rocks fall (rows 192..M_TOP-1: gone),
        ldx #NALIENS-1           ; explosions burn out
ss_rock:
        lda a_state,x
        cmp #ST_ROCK
        bne :++
        lda a_y,x
        clc
        adc m_dy
        sta a_y,x
        cmp #192
        bcc :+
        cmp #M_TOP
        bcs :+
        stz a_state,x
        bra ss_next
:       jsr fly_add
        bra ss_next
:       cmp #ST_BOOM
        bne ss_next
        jsr alien
ss_next:
        dex
        bpl ss_rock
        lda m_wait               ; METEOR STORM on screen: no rock yet
        beq :+
        dec m_wait
        bra ss_hits
:       lda m_acc                ; a rock or a coin every M_SPACING rows
        clc
        adc m_dy
        cmp #M_SPACING
        bcc :+
        sbc #M_SPACING
        sta m_acc
        jsr storm_spawn
        bra :++
:       sta m_acc
:       lda m_time+1             ; steps flown, up to M_TIME_MAX
        cmp #>M_TIME_MAX
        bne :+
        lda m_time
        cmp #<M_TIME_MAX
        beq ss_hits
:       inc m_time
        bne ss_hits
        inc m_time+1
ss_hits:
        lda tmp2                 ; the ship against the rocks (first hit)
        jne ss_timers
        lda invul_t
        ora shield_t
        ora shield_t+1
        bne ss_take
        ldx #0
ss_hit: cpx nfly
        beq ss_take
        lda fl_y1,x              ; fl_y1 >= first row, fl_y0 <= last row
        cmp #SHIP_HIT_Y0
        bcc ss_miss
        lda fl_y0,x
        cmp #SHIP_HIT_Y1+1
        bcs ss_miss
        lda fl_x1,x              ; fl_x1 >= ship_c + 1
        clc
        adc #<-SHIP_HIT_X0
        cmp ship_c
        bcc ss_miss
        lda ship_c               ; fl_x0 <= ship_c + 5
        clc
        adc #SHIP_HIT_X1
        cmp fl_x0,x
        bcc ss_miss
        ldy fly_list,x
        jsr explode
        lda #DEATH_T             ; no life lost: the storm ends with it
        sta ship_state
        lda #1
        sta m_crash
        lda #EV_DEATH
        tsb snd_ev
        bra ss_timers
ss_miss:
        inx
        bra ss_hit
ss_take:
        jsr pickups
        lda m_wait               ; the distance
        bne ss_timers
        lda m_dist+1
        bne ss_fly
        lda m_dy
        cmp m_dist
        bcc ss_fly
        stz m_dist               ; through: the prize by steps / 128
        lda m_time
        asl
        lda m_time+1
        rol
        tay
        lda m_prize_hi,y
        sta pts_hi
        lda m_prize_top,y
        sta pts_top
        lda #0
        jsr add_points3
        lda #EV_ARMOUR
        tsb snd_ev
        bra storm_end
ss_fly: lda m_dist
        sec
        sbc m_dy
        sta m_dist
        bcs ss_timers
        dec m_dist+1
ss_timers:
        jsr ship_timers
        lda m_crash              ; the explosion over: the end
        beq :+
        lda ship_state
        beq storm_end
:       rts

; Back to a teleport (LEVEL n), then the shop or the next level.
storm_end:
        stz storm
        ldx #NALIENS-1
:       stz a_state,x
        dex
        bpl :-
        ldx #N_OBJ-1
:       stz obj_y,x
        dex
        bpl :-
        lda #1
        sta phase
        lda #TELEPORT_T
        sta clear_t
        rts

; A coin (rand8 < M_COIN) in the last free object slot, at the top, or a
; rock in the last free rock slot, above the screen.
storm_spawn:
        jsr rand8
        cmp #M_COIN
        bcs sp_rock
        jsr rand8
        and #7
        tay
        lda m_coins,y
        ldx #N_OBJ
:       dex
        bmi sp_done
        ldy obj_y,x
        bne :-
        sta obj_kind,x
        lda #FIELD_TOP
        sta obj_y,x
        jsr rand8
        and #15                  ; the 16 icon columns of the field
        sta obj_k,x
sp_done:
        rts
sp_rock:
        jsr rand8
        and #127
        cmp #ALIEN_MAX+1
        bcc :+
        sbc #64                  ; (carry set)
:       ldx #M_ROCKS
:       dex
        bmi sp_done
        ldy a_state,x
        bne :-
        sta a_x,x
        lda #ST_ROCK
        sta a_state,x
        lda #M_TOP
        sta a_y,x
        rts
.code
