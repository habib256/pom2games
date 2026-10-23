; WARGALAGA II -- one logic step (1/30 s NTSC). Pure state, no drawing:
; tools/model.py is its bit-exact reference (tests/test_game.py compares the
; two step by step). Order: ship, shots, new shots (weapon, autofire),
; bombs, falling objects, stars, entry waves, formation sway, dive launcher,
; aliens (all frozen by the freeze bonus but for explosions), flying list,
; shots against aliens (and drops), the ship against bombs then aliens,
; pickups, enemy fire, ship and bonus timers. Included by game.s.

logic_step:
        inc step_count
        bne :+
        inc step_count+1
:       lda ship_state           ; exploding or game over: no move, no shot
        ora game_over
        sta tmp2
        bne ship_done
        lda move_dir
        beq ship_done
        bmi ship_left
        lda ship_c               ; speed: s_level + 1 cells
        sec
        adc s_level
        cmp #SHIP_MAX+1
        bcc :+
        lda #SHIP_MAX
:       sta ship_c
        bra ship_done
ship_left:
        lda ship_c
        clc                      ; - s_level - 1
        sbc s_level
        bcs :+
        lda #0
:       sta ship_c
ship_done:
        ldx #MAX_SHOTS-1         ; shots climb (and drift: dx); off = free
shots:  lda shot_y,x
        beq shot_next
        lda shot_c,x
        clc
        adc shot_dx,x
        sta shot_c,x
        cmp #140
        bcs shot_free
        lda shot_y,x
        sec
        sbc #SHOT_DY
        cmp #FIELD_TOP
        bcc shot_free
        sta shot_y,x
        bra shot_next
shot_free:
        stz shot_y,x
shot_next:
        dex
        bpl shots
        lda autofire_t           ; autofire: a volley every AUTO_GAP steps
        ora autofire_t+1         ; while fire is held
        beq :+
        lda fire_held
        beq :+
        lda auto_cnt
        bne :+
        lda #1
        sta fire_req
:       lda auto_cnt
        inc a
        and #AUTO_GAP-1
        sta auto_cnt
        lda fire_req
        beq bombs
        stz fire_req
        lda tmp2                 ; no shot while dead or teleporting
        ora phase
        bne bombs
        jsr volley
bombs:  ldx #E_SHOTS-1           ; bombs fall; off the bottom = free
bomb_fall:
        lda e_y,x
        beq bomb_next
        lda e_c,x                ; (the boss's drift sideways)
        clc
        adc e_dx,x
        sta e_c,x
        cmp #140
        bcs bomb_free
        lda e_y,x
        clc
        adc bomb_dy
        cmp #192-BOMB_H+1
        bcc :+
bomb_free:
        lda #0
:       sta e_y,x
bomb_next:
        dex
        bpl bomb_fall
        ldx #N_OBJ-1             ; objects fall; off the bottom = free
obj_fall:
        lda obj_y,x
        beq obj_next
        clc
        adc #OBJ_DY
        cmp #192-OBJ_H+1
        bcc :+
        lda #0
:       sta obj_y,x
obj_next:
        dex
        bpl obj_fall
stars:  ldx #NSTARS-1            ; three speeds; a star leaving the bottom
:       lda star_y,x             ; comes back at the top, 17 bytes further
        clc
        adc star_speed,x
        cmp #192
        bcc :++
        sbc #192-FIELD_TOP
        pha
        lda star_col,x
        adc #17-1                ; carry is set
        cmp #40
        bcc :+
        sbc #40
:       sta star_col,x
        pla
:       sta star_y,x
        dex
        bpl :---
        stz nfly                 ; the alien moves list the flying ones
        lda freeze_t
        ora freeze_t+1
        beq thawed
        ldx #NALIENS-1           ; frozen: explosions go on, nothing moves
frozen: lda a_state,x
        cmp #ST_BOOM
        bne :+
        jsr alien
        bra fz_next
:       cmp #ST_FORM             ; seated big ones are shot through the
        bne :+                   ; list, frozen too (bug hunt 6: shots went
        lda a_big,x              ; through them, the model hit them)
        beq fz_next
        bra fz_add
:       tay
        lda is_flying,y
        beq fz_next
fz_add: jsr fly_add
fz_next:
        dex
        bpl frozen
        bra moved_all
thawed: jsr launch
        jsr sway
        jsr dive
        ldx #NALIENS-1
th_alien:
        lda a_state,x            ; a small seated alien: nothing to do
        cmp #ST_FORM             ; (inline: most of them)
        bne :+
        lda a_big,x
        beq :++
:       jsr alien
:       dex
        bpl th_alien
        jsr boss_move
        jsr hurry_move
moved_all:
        lda boss_boom
        beq :+
        dec boss_boom
:
        lda nohit                ; test bench only: shots pass through
        bne :+++
        ldx #MAX_SHOTS-1
:       lda shot_y,x
        beq :+
        jsr shoot
:       dex
        bpl :--
:       lda ship_state           ; the ship: hits, then pickups (not
        ora game_over            ; while teleporting)
        ora phase
        bne fired
        lda invul_t
        ora shield_t
        ora shield_t+1
        bne :+
        jsr ship_hits
:       lda ship_state
        ora game_over
        bne fired
        jsr pickups
fired:  lda freeze_t
        ora freeze_t+1
        bne :+
        lda lkind                ; a bonus level's aliens never fire
        cmp #LK_BONUS
        beq :+
        jsr enemy_fire
:       lda ship_state           ; ship timers
        beq invul
        dec ship_state
        bne timers
        lda lives
        beq over
        lda #SHIP_MAX/2
        sta ship_c
        lda #RESPAWN_INVUL
        sta invul_t
        bra timers
over:   lda #1
        sta game_over
        lda #EV_OVER
        tsb snd_ev
        bra timers
invul:  lda invul_t
        beq timers
        dec invul_t
timers: ldx #autofire_t-autofire_t  ; the timed bonuses (consecutive words)
        jsr tick16
        ldx #mult_t-autofire_t
        jsr tick16
        bne :+
        bcc :+
        lda #1                   ; multiplier over
        sta mult
:       ldx #shield_t-autofire_t
        jsr tick16
        ldx #freeze_t-autofire_t
        jsr tick16
        jsr level_step
logic_done:
        rts

; The level: playing until every wave is in and every alien gone, then
; TELEPORT_T steps of teleport (no shots, bombs, objects), then the next.
level_step:
        lda game_over            ; (levels went on behind GAME OVER)
        jne ls_done
        lda phase
        beq ls_play
        dec clear_t
        jne ls_done
        stz phase
        inc level
        lda level
        cmp #LEVELS
        bne :+
        stz level
        lda loop                 ; saturates (255 + 1 was loop 0: easy again)
        inc a
        beq :+
        sta loop
:       jmp setup_level
ls_play:
        inc level_t              ; (saturates at $FFFF)
        bne :+
        inc level_t+1
        bne :+
        dec level_t
        dec level_t+1
:       lda hurry                ; a level that drags: the saucer
        bne ls_clear             ; (normal and big levels only)
        lda lkind
        cmp #LK_BONUS
        bcs ls_clear
        lda level_t
        cmp #<HURRY_T
        lda level_t+1
        sbc #>HURRY_T
        bcc ls_clear
        lda #1
        sta hurry
        sta h_dir
        stz h_x
        lda #HURRY_FIRE
        sta h_t
ls_clear:
        lda entry_w
        cmp #ROWS
        bne ls_done
        lda boss_hp              ; (the boss, down and burnt out)
        ora boss_boom
        bne ls_done
        ldx #N_OBJ-1             ; objects still falling hold the end (the
:       lda obj_y,x              ; boss's life and coin were wiped half-way
        bne ls_done              ; down, bug hunt 6)
        dex
        bpl :-
        ldx #NALIENS-1
:       lda a_state,x
        bne ls_done
        dex
        bpl :-
        lda lkind                ; a bonus level all shot: the prize
        cmp #LK_BONUS
        bne :+
        lda bonus_kills
        cmp #NALIENS
        bne :+
        stz pts_hi               ; BCD 10 000
        lda #1
        sta pts_top
        lda #0
        jsr add_points3
:       lda #1
        sta phase
        stz hurry
        lda #TELEPORT_T
        sta clear_t
        ldx #MAX_SHOTS-1
:       stz shot_y,x
        dex
        bpl :-
        ldx #E_SHOTS-1
:       stz e_y,x
        dex
        bpl :-
        ldx #N_OBJ-1
:       stz obj_y,x
        dex
        bpl :-
ls_done:
        rts

; The level's kind and parameters: loop-0 tables (tools/bonus.py), made
; harder once a loop (saturating; five loops reach every bound).
setup_level:
        ldx level
        lda lv_kind,x
        sta lkind
        lda lv_dive,x
        sta dive_gap
        lda lv_divers,x
        sta max_divers
        lda lv_fire,x
        sta fire_gap
        lda lv_bomb,x
        sta bomb_dy
        lda lv_kami,x
        sta kami_dy
        lda loop
        cmp #5
        bcc :+
        lda #5
:       tax
        beq sl_set
sl_loop:
        lda dive_gap             ; max(8, dive_gap - 4)
        sec
        sbc #4
        cmp #8
        bcs :+
        lda #8
:       sta dive_gap
        lda max_divers           ; min(7, max_divers + 2): more is past the
        clc                      ; frame budget
        adc #2
        cmp #8
        bcc :+
        lda #7
:       sta max_divers
        lda fire_gap             ; max(5, fire_gap - 3)
        sec
        sbc #3
        cmp #5
        bcs :+
        lda #5
:       sta fire_gap
        lda bomb_dy              ; min(7, bomb_dy + 1)
        cmp #7
        bcs :+
        inc bomb_dy
:       lda kami_dy
        cmp #7
        bcs :+
        inc kami_dy
:       dex
        bne sl_loop
sl_set: lda #0                   ; boss levels: only waves 3 and 4 (escorts)
        ldx lkind
        cpx #LK_BOSS
        bne :+
        lda #3
:       sta entry_w
        stz entry_k
        lda #ENTRY_FIRST
        sta entry_t
        lda dive_gap
        sta dive_t
        lda fire_gap
        sta fire_t
        stz level_t
        stz level_t+1
        stz bonus_kills
        stz hurry
        ldx #ROWS-1
:       stz w_kills,x
        dex
        bpl :-
        lda lkind
        cmp #LK_BOSS
        bne :+
        jmp boss_setup
:       rts

; ---------------------------------------------------------------------------
; The boss. n = level / 25 + 4 * loop (saturated at 22: every bound
; reached): hp = 30 + 10 n (at most 250), gap = max(16, 40 - 5 n).
boss_setup:
        lda loop
        cmp #6
        bcc :+
        lda #6
:       asl
        asl
        sta tmp
        lda level                ; + level / 25 (0..3)
        ldx #0
:       cmp #25
        bcc :+
        sbc #25
        inx
        bra :-
:       txa
        clc
        adc tmp
        cmp #22
        bcc :+
        lda #22
:       sta tmp                  ; n
        asl                      ; 10 n
        asl
        adc tmp
        asl
        adc #30
        sta boss_hp
        lda tmp                  ; 5 n
        asl
        asl
        adc tmp
        sta tmp
        lda #40
        sec
        sbc tmp
        bcc :+
        cmp #16
        bcs :++
:       lda #16
:       sta boss_gap
        sta boss_t
        lda #56                  ; (a multiple of 7)
        sta boss_x
        lda #1
        sta boss_dir
        stz boss_boom
        lda #BOSS_STEP
        sta boss_mv
        rts

; A leap of 7 cells every BOSS_STEP steps, bouncing at the edges; a
; rosette every boss_gap steps, an aimed bomb half-way.
boss_move:
        lda boss_hp
        beq bm_done
        dec boss_mv
        bne bm_fire
        lda #BOSS_STEP
        sta boss_mv
        jsr bm_leap
        cmp #BOSS_MAX_X+1        ; (also negative)
        bcc :+
        lda boss_dir
        eor #$FE                 ; 1 <-> $FF
        sta boss_dir
        jsr bm_leap
:       sta boss_x
bm_fire:
        lda boss_x
        clc
        adc #BOSS_CELLS/2
        sta b_c                  ; its middle
        lda #BOSS_Y+BOSS_H
        sta b_y
        dec boss_t
        bne bm_aim
        lda boss_gap
        sta boss_t
        lda #<-2                 ; the rosette: dx -2..2
:       sta b_dx
        phx
        jsr bomb
        plx
        lda b_dx
        inc a
        cmp #3
        bne :-
bm_done:
        rts
bm_aim: lda boss_gap
        lsr
        cmp boss_t
        bne bm_done
        ; fall through
; A bomb at (b_y, b_c) drifting one cell a step towards the ship's middle.
aim_bomb:
        lda ship_c               ; aimed: towards the ship's middle
        clc
        adc #3
        cmp b_c
        beq :+
        lda #1
        bcs :+                   ; (ship middle > boss middle: carry set)
        lda #$FF
:       bne :+
        lda #0
:       sta b_dx
        jmp bomb

; The hurry-up saucer: 2 cells a step along the top, bouncing, out of
; reach; an aimed bomb every HURRY_FIRE steps.
hurry_move:
        lda hurry
        beq hm_done
        jsr hm_next
        cmp #ALIEN_MAX+1         ; (also negative)
        bcc :+
        lda h_dir
        eor #$FE                 ; 1 <-> $FF
        sta h_dir
        jsr hm_next
:       sta h_x
        dec h_t
        bne hm_done
        lda #HURRY_FIRE
        sta h_t
        lda h_x
        clc
        adc #3
        sta b_c
        lda #HURRY_Y+ALIEN_H
        sta b_y
        bra aim_bomb
hm_next:                         ; A = h_x + 2 * h_dir
        lda h_dir
        asl
        clc
        adc h_x
hm_done:
        rts

; A = boss_x + 7 * boss_dir.
bm_leap:
        lda boss_dir
        bmi :+
        lda boss_x
        clc
        adc #7
        rts
:       lda boss_x
        sec
        sbc #7
        rts

; Shot down: 5000 points, its escorts explode, a life and a 200 coin.
boss_down:
        stz pts_hi               ; BCD 5000
        lda #$50
        sta pts_hi
        lda #$00
        jsr add_points
        lda #BOSS_BOOM_T
        sta boss_boom
        phx
        ldy #NALIENS-1
:       lda a_state,y
        beq :+
        cmp #ST_BOOM
        beq :+
        jsr explode
:       dey
        bpl :--
        lda #BOSS_Y+8            ; the drops, slots 0 and 1
        sta obj_y
        sta obj_y+1
        lda #K_LIFE
        sta obj_kind
        lda #K_C200
        sta obj_kind+1
        lda boss_x
        clc
        adc #8
        tay
        lda div7,y
        sta obj_k
        dec a
        sta obj_k+1
        plx
        rts

; A 16-bit timer at game_vars+X: one step less if not 0. C = 1 and Z = 1 if
; it has just reached 0.
tick16: lda autofire_t,x
        ora autofire_t+1,x
        beq :++
        lda autofire_t,x
        bne :+
        dec autofire_t+1,x
:       dec autofire_t,x
        lda autofire_t,x
        ora autofire_t+1,x
        sec
        rts
:       clc                      ; already 0 (Z = 1, C = 0)
        rts

; Fire a volley of the weapon: each of its shots takes the last free slot
; under the limit; none left, the rest of the volley is lost.
volley: lda weapon
        tay
        lda wpn_count,y
        sta cnt
        lda wpn_first,y
        tay
        stz tmp                  ; shots fired
vl_shot:
        ldx shot_limit
:       dex
        bmi vl_done
        lda shot_y,x
        bne :-
        lda #SHOT_Y0
        sta shot_y,x
        lda ship_c
        clc
        adc wpn_cell,y
        sta shot_c,x
        lda wpn_dx,y
        sta shot_dx,x
        inc tmp
        iny
        dec cnt
        bne vl_shot
vl_done:
        lda tmp                  ; a sound only for a shot fired
        beq :+
        lda #EV_SHOT             ; sound.s (not logic state)
        tsb snd_ev
:       rts

; ---------------------------------------------------------------------------
; Shot X against the aliens. Seated ones: the one formation row its rows can
; touch (shot_frow), then the column under its cell (col_of). Then the
; flying list. A hit frees the shot, explodes the alien, scores.
shoot:  lda boss_hp                ; the boss first
        beq sh_grid
        lda shot_c,x             ; boss_x <= c <= boss_x + 15
        cmp boss_x
        bcc sh_grid
        lda boss_x
        clc
        adc #BOSS_CELLS-1
        cmp shot_c,x
        bcc sh_grid
        lda shot_y,x             ; rows y..y+5 meet BOSS_Y..BOSS_Y+23
        cmp #BOSS_Y+BOSS_H
        bcs sh_grid
        cmp #BOSS_Y-SHOT_H+1
        bcc sh_grid
        stz shot_y,x             ; the wings swallow it, the core bleeds
        lda shot_c,x
        sec
        sbc boss_x
        cmp #BOSS_CORE0
        bcc :+
        cmp #BOSS_CORE1+1
        bcs :+
        dec boss_hp
        lda #$10                 ; BCD 10
        stz pts_hi
        jsr add_points
        lda #EV_ARMOUR
        tsb snd_ev
        lda boss_hp
        bne :+
        jmp boss_down
:       rts
sh_grid:
        ldy shot_y,x
        lda shot_frow,y
        bmi sh_fly
        sta tmp2                 ; row
        tay
        lda shot_c,x
        sec
        sbc #FORM_X0
        bcc sh_fly
        sec
        sbc row_off,y
        bcc sh_fly
        cmp #COLS*FORM_DX
        bcs sh_fly
        tay
        lda col_of,y
        bmi sh_fly
        sta tmp
        lda tmp2
        asl
        asl
        asl
        ora tmp
        tay                      ; alien
        lda a_state,y
        cmp #ST_FORM
        bne sh_fly
        lda a_big,y              ; (a big one: through the list)
        bne sh_fly
        stz shot_y,x
        jsr explode
        lda #$50                 ; BCD 50
        stz pts_hi
        jsr add_points
        jmp drop
sh_fly: ldy #0
fly_shot:
        cpy nfly
        jeq sh_done
        phy
        lda shot_c,x             ; fl_x0 <= c <= fl_x1 (Y = list position)
        cmp fl_x0,y
        jcc fly_miss
        lda fl_x1,y
        cmp shot_c,x
        jcc fly_miss
        lda fl_y1,y              ; y <= fl_y1, y + 5 >= fl_y0
        cmp shot_y,x
        jcc fly_miss
        lda shot_y,x
        clc
        adc #SHOT_H-1
        cmp fl_y0,y
        jcc fly_miss
        lda fly_list,y
        tay
        jsr is_target            ; still a target (not shot this step)?
        jcc fly_miss
        stz shot_y,x
        lda a_big,y
        beq fs_small
        lda a_hp,y               ; a big one: two hits
        dec a
        sta a_hp,y
        beq :+
        lda #EV_ARMOUR           ; dented (sound only)
        tsb snd_ev
        ply
        rts
:       jsr explode
        lda #$02                 ; BCD 200
        sta pts_hi
        lda #$00
        jsr add_points
        jsr drop_mark
        ply
        rts
fs_small:
        jsr explode
        lda #$01                 ; BCD 100
        sta pts_hi
        lda #$00
        jsr add_points
        lda lkind                ; bonus level: count; kamikaze: a wave
        cmp #LK_BONUS            ; shot down pays 2000 << wave
        bne :+
        inc bonus_kills
        bra :++
:       cmp #LK_KAMI
        bne :+
        phx
        tya
        lsr
        lsr
        lsr
        tax
        inc w_kills,x
        lda w_kills,x
        cmp #COLS
        bne fs_paid
        lda kami_hi,x
        sta pts_hi
        lda kami_top,x
        sta pts_top
        lda #0
        jsr add_points3
fs_paid:
        plx
:       jsr drop
        ply
        rts
fly_miss:
        ply
        iny
        jmp fly_shot
sh_done:
        rts

; Y = alien: C = 1 if it is a list target: flying (enter, dive, home,
; pass, kamikaze) or a seated big one. Keeps X, Y.
is_target:
        lda a_state,y
        beq :++
        cmp #ST_BOOM
        beq :++
        cmp #ST_FORM
        bne :+
        lda a_big,y
        beq :++
:       sec
        rts
:       clc
        rts

; X = alien: C = 1 if on screen (rows FIELD_TOP..191; big: from 16, its top
; not in the HUD). Keeps X, Y.
shown_x:
        lda a_y,x
        cmp #192
        bcs :++
        pha
        lda a_big,x
        beq :+
        pla
        cmp #16
        rts
:       pla
        cmp #FIELD_TOP
        rts
:       clc
        rts

; A big alien Y leaves the pack's rank mark (always, a slot free). Keeps X, Y.
drop_mark:
        lda a_y,y
        cmp #192-OBJ_H+1
        bcs dm_done
        phx
        ldx #N_OBJ
:       dex
        bmi dm_full
        lda obj_y,x
        bne :-
        lda a_y,y
        sta obj_y,x
        lda a_x,y
        clc
        adc #3
        phy
        tay
        lda div7,y
        sta obj_k,x
        ply
        lda level                ; mark0 + pack mod 6
        lsr
        lsr
:       cmp #6
        bcc :+
        sbc #6
        bra :-
:       clc
        adc #K_MARK0
        sta obj_kind,x
dm_full:
        plx
dm_done:
        rts

; Alien Y explodes. Keeps X, Y.
explode:
        lda #EV_KILL
        tsb snd_ev
        lda #ST_BOOM
        sta a_state,y
        lda #BOOM_T
        sta a_timer,y
        rts

; score += BCD (pts_hi A) * mult, six digits, wrapping; add_points3: plus
; pts_top in the third byte (prizes of 10 000 and more). Keeps X, Y.
add_points:
        stz pts_top
add_points3:
        sta pts_lo
        phx
        ldx mult
ap_add: sed
        clc
        lda score
        adc pts_lo
        sta score
        lda score+1
        adc pts_hi
        sta score+1
        lda score+2
        adc pts_top
        sta score+2
        bcc :+                   ; past 999 999: stays there (it wrapped)
        lda #$99
        sta score
        sta score+1
        sta score+2
:       cld
        dex
        bne ap_add
        plx
        rts

; A kill by alien Y may drop an object (DROP_RATE / 256), of a kind drawn
; from drop_table, in the last free slot, on the 14-dot column under the
; alien's middle. Keeps X, Y.
drop:   jsr rand8
        cmp #DROP_RATE
        bcs dr_done
        jsr rand8                ; the kind from the high byte: the low one
        lda prng_hi              ; is the first draw shifted (bug hunt:
        and #63                  ; only coins and S ever dropped)
        phy
        tay
        lda drop_table,y
        ply
        pha                      ; guard: an object from an alien below
        lda a_y,y                ; row 184 would be drawn past row 191 (into
        cmp #192-OBJ_H+1         ; the zero page); shots hit nothing so low
        pla
        bcs dr_done
        phx
        ldx #N_OBJ
:       dex
        bmi dr_full
        pha
        lda obj_y,x
        bne dr_busy
        pla
        sta obj_kind,x
        lda a_y,y
        sta obj_y,x
        lda a_x,y
        clc
        adc #3
        phy
        tay
        lda div7,y
        sta obj_k,x
        ply
        bra dr_full
dr_busy:
        pla
        bra :-
dr_full:
        plx
dr_done:
        rts

; The ship takes every object it touches (the order: slots down).
pickups:
        ldx #N_OBJ-1
pk_obj: lda obj_y,x
        beq pk_next
        cmp #SHIP_HIT_Y0-OBJ_H+1 ; rows y..y+7 meet the ship's
        bcc pk_next
        cmp #SHIP_HIT_Y1+1
        bcs pk_next
        ldy obj_k,x              ; cells 7k..7k+6 meet ship_c+1..ship_c+5
        lda k7,y
        clc
        adc #6-SHIP_HIT_X0
        cmp ship_c
        bcc pk_next
        lda ship_c
        clc
        adc #SHIP_HIT_X1
        cmp k7,y
        bcc pk_next
        stz obj_y,x
        lda obj_kind,x
        phx
        jsr take
        plx
pk_next:
        dex
        bpl pk_obj
        rts

; The effect of object kind A.
take:   asl
        tax
        jmp (take_tab,x)
take_tab:
        .addr tk_c10, tk_c50, tk_c100, tk_c200, tk_s, tk_b, tk_t, tk_w1, tk_w2, tk_w3
        .addr tk_auto, tk_armour, tk_life, tk_skull, tk_e, tk_x, tk_lt, tk_r, tk_a
        .addr tk_x2, tk_x5, tk_shield, tk_freeze, tk_mark, tk_mark, tk_mark, tk_mark
        .addr tk_mark, tk_mark, tk_dark, tk_meteor, tk_memory
.assert (* - take_tab) / 2 = NKIND, error, "one effect per kind"
tk_c10: lda #$10
        ldy #$00
        bra credit
tk_c50: lda #$50
        ldy #$00
        bra credit
tk_c100:
        lda #$00
        ldy #$01
        bra credit
tk_c200:
        lda #$00
        ldy #$02
credit: sed                      ; credits += BCD (Y A), at most 9999
        clc
        adc credits
        sta credits
        tya
        adc credits+1
        sta credits+1
        cld
        bcc :+
        lda #$99
        sta credits
        sta credits+1
:       rts
tk_s:   lda s_level
        cmp #S_MAX
        bcs gauge_full
        inc s_level
        rts
tk_b:   lda shot_limit
        cmp #B_MAX
        bcs gauge_full
        inc shot_limit
        rts
tk_t:   lda t_level
        cmp #T_MAX
        bcs gauge_full
        inc t_level
        rts
gauge_full:                      ; a gauge (or armour, lives) at its maximum
        lda #$05                 ; BCD 500
        sta pts_hi
        lda #$00
        jmp add_points
tk_w1:  lda #0
        bra :+
tk_w2:  lda #1
        bra :+
tk_w3:  lda #2
:       sta weapon
        rts
tk_auto:
        ldx #autofire_t-autofire_t
        bra timed
tk_x2:  lda #2
        bra :+
tk_x5:  lda #5
:       cmp mult                 ; the larger multiplier, timed anew
        bcc :+
        sta mult
:       ldx #mult_t-autofire_t
        bra timed
tk_shield:
        ldx #shield_t-autofire_t
        bra timed
tk_freeze:
        ldx #freeze_t-autofire_t
timed:  ldy t_level              ; a timed bonus: 10 * t_level seconds
        lda dur_lo,y
        sta autofire_t,x
        lda dur_hi,y
        sta autofire_t+1,x
        rts
tk_armour:
        lda armour
        cmp #2
        bcs gauge_full
        inc armour
        rts
tk_life:
        lda lives
        cmp #4
        bcs gauge_full
        inc lives
        rts
tk_skull:                        ; a malus, by chance
        jsr rand8
        and #3
        beq tk_w1
        cmp #2
        bcc sk_speed
        beq sk_shots
        ldx #7                   ; 3: every timed bonus ends
:       stz autofire_t,x
        dex
        bpl :-
        lda #1
        sta mult
        rts
sk_speed:
        lda s_level
        cmp #2
        bcc :+
        dec s_level
:       rts
sk_shots:
        lda shot_limit
        cmp #B_MIN+1
        bcc :+
        dec shot_limit
:       rts
tk_e:   lda #1
        bra letter
tk_x:   lda #2
        bra letter
tk_lt:  lda #4
        bra letter
tk_r:   lda #8
        bra letter
tk_a:   lda #16
letter: tsb extra_bits
        lda extra_bits
        cmp #EXTRA_ALL
        bne :+
        stz extra_bits           ; E X T R A: a life
        bra tk_life
:       rts
tk_mark:                         ; rank marks 0..5 (lot 7): kind - K_MARK0
        txa
        lsr
        sec
        sbc #K_MARK0
        tax
        lda bit_of,x
        tsb marks
        rts
bit_of: .byte 1, 2, 4, 8, 16, 32
tk_dark:
        lda #1
        sta mark_dark
        rts
tk_meteor:                       ; sub-games (lot 8)
        lda #1
        sta subgame
        rts
tk_memory:
        lda #2
        sta subgame
        rts

; The ship against the bombs, then against the flying aliens (first hit
; only). Armour takes a bomb and gives a shield; an alien kills anyway.
ship_hits:
        ldx #E_SHOTS-1
hit_bomb:
        lda e_y,x
        beq hb_next
        lda e_c,x                ; ship_c+1 <= c <= ship_c+5
        sec
        sbc ship_c
        sec
        sbc #SHIP_HIT_X0
        cmp #SHIP_HIT_X1-SHIP_HIT_X0+1
        bcs hb_next
        lda e_y,x                ; rows y..y+3 meet the ship's
        sec
        sbc #SHIP_HIT_Y0-BOMB_H+1
        cmp #SHIP_HIT_Y1-(SHIP_HIT_Y0-BOMB_H+1)+1
        bcs hb_next
        stz e_y,x
        lda armour
        beq kill
        dec armour
        lda #SHIELD_T
        sta invul_t
        lda #EV_ARMOUR
        tsb snd_ev
        rts
hb_next:
        dex
        bpl hit_bomb
        ldx #0
hit_alien:
        cpx nfly
        beq ha_done
        lda fl_y1,x              ; fl_y1 >= first row, fl_y0 <= last row
        cmp #SHIP_HIT_Y0
        bcc ha_next
        lda fl_y0,x
        cmp #SHIP_HIT_Y1+1
        bcs ha_next
        lda fl_x1,x              ; fl_x1 >= ship_c + 1
        clc
        adc #<-SHIP_HIT_X0
        cmp ship_c
        bcc ha_next
        lda ship_c               ; fl_x0 <= ship_c + 5
        clc
        adc #SHIP_HIT_X1
        cmp fl_x0,x
        bcc ha_next
        ldy fly_list,x
        jsr is_target
        bcc ha_next
        jsr explode
kill:   lda #DEATH_T
        sta ship_state
        dec lives
        lda #EV_DEATH
        tsb snd_ev
ha_done:
        rts
ha_next:
        inx
        bra hit_alien

; Every FIRE_GAP steps a random alien, seated or diving, visible and high
; enough, drops a bomb if a slot is free.
enemy_fire:
        dec fire_t
        bne ef_done
        lda fire_gap
        sta fire_t
        jsr rand8
        and #63
        cmp #NALIENS
        bcc :+
        sbc #NALIENS             ; carry is set
:       tax
        ldy #NALIENS
ef_seek:
        lda a_state,x
        cmp #ST_FORM
        beq :+
        cmp #ST_DIVE
        bne ef_next
:       jsr shown_x
        bcc ef_next
        lda a_y,x
        cmp #FIRE_MAX_Y
        bcc ef_found
ef_next:
        inx
        cpx #NALIENS
        bne :+
        ldx #0
:       dey
        bne ef_seek
ef_done:
        rts
ef_found:
        lda a_y,x
        clc
        adc #ALIEN_H
        sta b_y
        lda a_x,x
        clc
        adc #3
        sta b_c
        stz b_dx
        ; fall through
; A bomb at (b_y, b_c) drifting b_dx cells a step, in the last free slot.
; Keeps X.
bomb:   ldy #E_SHOTS
:       dey
        bmi :+
        lda e_y,y
        bne :-
        lda b_y
        sta e_y,y
        lda b_c
        sta e_c,y
        lda b_dx
        sta e_dx,y
:       rts

; Entry waves: wave w fills formation row w, a pair every LAUNCH_GAP steps
; from the middle out, the left alien on the entry path, the right one on
; its mirror.
launch:
        lda entry_w
        cmp #ROWS
        beq launched
        dec entry_t
        bne launched
        asl
        asl
        asl
        sta tmp2                 ; w * 8
        clc
        adc #3
        sec
        sbc entry_k
        tax
        ldy #0
        jsr enter
        lda tmp2
        clc
        adc #4
        adc entry_k
        tax
        ldy #1
        jsr enter
        inc entry_k
        lda entry_k
        cmp #4
        bne :+
        stz entry_k
        inc entry_w
        lda #WAVE_GAP
        bra :++
:       lda #LAUNCH_GAP
:       sta entry_t
launched:
        rts
; X = alien, Y = mirror flag (the right one of the pair), flipped after
; level 100. The way in and the state depend on the level kind: a bonus
; level's aliens fly past, a kamikaze level's dive at the ship.
enter:  lda lkind                 ; a big level's row 0: big aliens on the
        cmp #LK_BIG              ; even slots, none on the odd ones
        bne en_small
        lda entry_w
        bne en_small
        txa
        lsr
        bcc :+
        rts                      ; odd slot: not launched (left as it is)
:       lda #1
        sta a_big,x
        lda #BIG_HP
        sta a_hp,x
        bra en_flip
en_small:
        stz a_big,x
        lda #1
        sta a_hp,x
en_flip:
        lda loop
        and #1
        sta tmp
        tya
        eor tmp
        sta a_mirror,x
        beq :+
        lda #ALIEN_MAX-ENTRY_X0
        bra :++
:       lda #ENTRY_X0
:       sta a_x,x
        lda #ENTRY_Y0
        sta a_y,x
        lda #<entry
        sta a_plo,x
        lda #>entry
        sta a_phi,x
        lda lkind
        cmp #LK_BONUS
        bne :+
        lda #<flypast
        sta a_plo,x
        lda #>flypast
        sta a_phi,x
        lda #ST_PASS
        bra :+++
:       cmp #LK_KAMI
        bne :+
        lda #ST_KAMI
        bra :++
:       lda #ST_ENTER
:       sta a_state,x
        rts

; Every other step, one formation row takes the current sway offset and
; flips its animation frame; its seated aliens follow. When all ROWS have,
; the offset moves one cell, bouncing between 0 and SWAY_MAX. (One row a
; step would redraw 16 aliens a frame: each change is drawn on both pages.)
sway:   lda sway_t               ; one row every SWAY_EVERY steps
        inc a
        cmp #SWAY_EVERY
        bcc :+
        lda #0
:       sta sway_t
        bne swayed
        ldx sway_row
        lda form_off
        sta row_off,x
        lda row_anim,x
        eor #1
        sta row_anim,x
        txa
        asl
        asl
        asl
        tax
        lda #COLS
        sta cnt
:       lda a_state,x
        cmp #ST_FORM
        bne :+
        jsr slot_x
        sta a_x,x
:       inx
        dec cnt
        bne :--
        inc sway_row
        lda sway_row
        cmp #ROWS
        bne swayed
        stz sway_row
        lda form_off
        clc
        adc form_dir
        sta form_off
        beq :+
        cmp #SWAY_MAX
        bne swayed
:       lda form_dir
        eor #$FE                 ; 1 <-> $FF
        sta form_dir
swayed: rts

; Every dive_gap steps once all waves are in, a random seated alien dives,
; unless max_divers are already off their seats (the level's parameters).
dive:   lda entry_w
        cmp #ROWS
        bne dived
        lda lkind                ; no formation on bonus / kamikaze levels
        cmp #LK_BONUS
        bcc :+
        cmp #LK_BOSS
        bcc dived
:       dec dive_t
        bne dived
        lda dive_gap
        sta dive_t
        ldy #0
        ldx #NALIENS-1
:       lda a_state,x
        sec
        sbc #ST_ENTER
        cmp #ST_HOME-ST_ENTER+1
        bcs :+
        iny
:       dex
        bpl :--
        cpy max_divers
        bcs dived
        jsr rand8
        and #63
        cmp #NALIENS
        bcc :+
        sbc #NALIENS             ; carry is set
:       tax
        ldy #NALIENS
seek:   lda a_state,x
        cmp #ST_FORM
        beq found
        inx
        cpx #NALIENS
        bne :+
        ldx #0
:       dey
        bne seek
dived:  rts
found:  lda #ST_DIVE
        sta a_state,x
        jsr rand8
        and #NDIVES-1
        tay
        lda dive_lo,y
        sta a_plo,x
        lda dive_hi,y
        sta a_phi,x
        txa                      ; right half of the formation: mirrored
        and #COLS-1              ; (and all of it after level 100)
        cmp #COLS/2
        lda #0
        rol
        sta tmp
        lda loop
        and #1
        eor tmp
        sta a_mirror,x
        rts
.assert NDIVES = 4, error, "dive choice masks with NDIVES-1"

; Slot of alien X: A = cell (FORM_X0 + row offset + 14 * column).
; Keeps X, Y. Uses tmp.
slot_x: phy
        ldy alien_row,x
        lda row_off,y
        sta tmp
        txa
        and #COLS-1
        tay
        lda slot_dx,y
        clc
        adc tmp
        ply
        rts

; Move alien X. Keeps X.
alien:  lda a_state,x
        cmp #ST_FORM
        bne :+
        lda a_big,x              ; seated big ones are tested through the
        jne fly_add              ; list too
        rts
:
        cmp #ST_HOME
        jeq home
        cmp #ST_DEAD
        jeq moved
        cmp #ST_BOOM
        bne :+
        dec a_timer,x            ; exploding
        bne moved_near
        stz a_state,x
moved_near:
        rts
:       cmp #ST_KAMI
        bne a_path
        lda a_x,x                ; kamikaze: one cell a step towards the
        cmp ship_c               ; ship, kami_dy rows down; escaped below
        beq ka_y
        bcs :+
        inc a_x,x
        bra ka_y
:       dec a_x,x
ka_y:   lda a_y,x
        clc
        adc kami_dy
        sta a_y,x
        cmp #192                 ; escaped: rows 192..ESCAPE_Y-1 (it starts
        jcc fly_add              ; at 236, above: not there)
        cmp #ESCAPE_Y
        jcs fly_add
        stz a_state,x
        rts
a_path: lda a_plo,x              ; flying a path
        sta ptr
        lda a_phi,x
        sta ptr+1
        lda (ptr)
        cmp #PATH_END
        bne :+
        lda a_state,x            ; a path ends: home, or gone (flew past)
        cmp #ST_PASS
        beq pass_gone
        lda #ST_HOME
        sta a_state,x
        jmp fly_add
:       inc a_plo,x
        bne :+
        inc a_phi,x
:       sta tmp2                 ; the step byte
        lsr                      ; dx: high nibble, signed
        lsr
        lsr
        lsr
        cmp #8
        bcc :+
        ora #$F0
:       ldy a_mirror,x
        beq :+
        eor #$FF
        inc a
:       sta tmp
        clc
        adc a_x,x
        bit tmp
        bpl :+
        bcs xok                  ; negative step, no borrow
        lda #0
        bra xok
:       cmp #ALIEN_MAX+1
        bcc xok
        lda #ALIEN_MAX
xok:    ldy a_big,x              ; big: cells 2..132 (its box: x-2..x+7)
        beq :++
        cmp #2
        bcs :+
        lda #2
:       cmp #132+1
        bcc :+
        lda #132
:       sta a_x,x
        lda tmp2                 ; dy: low nibble, signed
        and #$0F
        cmp #8
        bcc :+
        ora #$F0
:       clc
        adc a_y,x
        sta a_y,x
        ldy a_state,x            ; a diver leaving the bottom goes home
        cpy #ST_PASS             ; from above its seat; one flying past is
        bne :+                   ; gone
        cmp #192
        bcc fly_add
        cmp #ESCAPE_Y
        bcs fly_add
pass_gone:
        stz a_state,x
        rts
:       cpy #ST_DIVE
        bne fly_add
        cmp #192
        bcc fly_add
        cmp #OFF_TOP
        bcs fly_add
        lda #ST_HOME
        sta a_state,x
        lda #OFF_TOP
        sta a_y,x
        jsr slot_x
        sta a_x,x
; A visible flying alien joins fly_list (built in the descending alien loop:
; the model's order).
fly_add:
        jsr shown_x
        bcc moved
        ldy nfly                 ; listed with its box (shots and the ship
        txa                      ; test against it: the aliens have moved)
        sta fly_list,y
        inc nfly
        lda a_big,x
        bne :+
        lda a_x,x
        sta fl_x0,y
        clc
        adc #ALIEN_CELLS-1
        sta fl_x1,y
        lda a_y,x
        sta fl_y0,y
        clc
        adc #ALIEN_H-1
        sta fl_y1,y
        rts
:       lda a_x,x
        sec
        sbc #2
        sta fl_x0,y
        clc
        adc #BIG_CELLS-1
        sta fl_x1,y
        lda a_y,x
        sec
        sbc #8
        sta fl_y0,y
        clc
        adc #BIG_H-1
        sta fl_y1,y
moved:  rts

; Homing: at most HOME_DX cells and HOME_DY rows a step towards the seat.
home:   jsr slot_x
        sta tmp                  ; seat cell
        sec
        sbc a_x,x
        bcc hx_neg
        cmp #HOME_DX+1
        bcc hx_add
        lda #HOME_DX
        bra hx_add
hx_neg: cmp #256-HOME_DX
        bcs hx_add
        lda #256-HOME_DX
hx_add: clc
        adc a_x,x
        sta a_x,x
        ldy alien_row,x          ; seat row; the row step wraps (signed)
        lda form_y,y
        sta tmp2
        sec
        sbc a_y,x
        bmi hy_neg
        cmp #HOME_DY+1
        bcc hy_add
        lda #HOME_DY
        bra hy_add
hy_neg: cmp #256-HOME_DY
        bcs hy_add
        lda #256-HOME_DY
hy_add: clc
        adc a_y,x
        sta a_y,x
        cmp tmp2
        bne :+
        lda a_x,x
        cmp tmp
        bne :+
        lda #ST_FORM
        sta a_state,x
        lda a_big,x              ; a big one seated this step is still a
        jne fly_add              ; target (bug hunt 6)
        rts
:       jmp fly_add
