; WARGALAGA II -- Meteor Storm (lot 8; Warblade's rules, lot 11): one logic
; step, in place of logic_step's game step, and what only the storm draws.
; Resident at $0800 (segment STORM, memory LOWM) and $0200 (STORM2, LOW2):
; copied from WG2.AUX at boot. Included by game.s. tools/model.py
; (storm_step) is its bit-exact reference.
;
; Rocks are aliens 0..M_ROCKS-1 in state ST_ROCK, drawn by render.s as
; flying aliens: slots 0-7 (formation row 0) a medium rock (cur_alien) or a
; big one (a_big: cur_big), slots 8-15 (row 1, row_base DESIGN2) a small one
; (cur_alien2); each falls a_hp rows a step faster than the field. Fire
; held: faster (m_speed + M_ACC), else slower (- M_DEC). The field falls
; m_dy rows a step (storm_dy): rocks, objects, and the stars on top of their
; own speed. A rock or an object every M_SPACING rows; M_DIST rows to fly.
; A rock hits: the ship explodes, no life lost, 500 points per 256 rows
; flown, the storm ends with the explosion. Through: the prize by the speed
; percentage (storm_pct), named for M_END steps.
;
; Drawn here (st_erase / st_draw, around render.s's ship): the speed gauge
; right of the ship (26 bars, 8 red then 18 green, STA like the ship) and
; the distance bar in the field's last byte column (35: rocks, objects and
; the ship stay left of it), filled from the bottom.

GAUGE_Y = 190                    ; the gauge's bottom bar; bar k at Y - 2k
GAUGE_N = 26
BAR_COL = 35
BAR_TOP = 32
BAR_H = 144                      ; rows: M_DIST >> 5
.assert M_DIST >> 5 = BAR_H, error, "the distance bar: a row per 32 rows flown"
STORM_PCT = 18                   ; Meteor Storm's row 0 (storm_template)
STORM_CREDITS = 33

.segment "STORM"
; The storm begins (level_step, at the end of a teleport).
storm_start:
        ldx #ROWS-1              ; rocks: medium/big in row 0, small in row 1
:       stz row_base,x
        dex
        bpl :-
        lda #DESIGN2
        sta row_base+1
        stz subgame
        lda #1
        sta storm
        stz m_speed
        stz m_acc
        stz m_time
        stz m_time+1
        stz m_held
        stz m_held+1
        stz m_crash
        stz m_end
        stz m_rel
        lda #<M_DIST
        sta m_dist
        lda #>M_DIST
        sta m_dist+1
        lda #M_WAIT
        sta m_wait
        lda ship_c               ; left of the gauge and the bar
        cmp #M_SHIP_MAX+1
        bcc :+
        lda #M_SHIP_MAX
        sta ship_c
:       ldx #M_ROCKS-1
:       stz a_big,x
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
        cmp #M_SHIP_MAX+1
        bcc ss_x
        lda #M_SHIP_MAX
        bra ss_x
:       lda ship_c
        clc
        sbc s_level
        bcs ss_x
        lda #0
ss_x:   sta ship_c
ss_speed:
        jsr ss_held              ; fire held: faster, else slower
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
ss_dy:  lda #M_DY0               ; rows the field falls: + 1 past a third,
        sta m_dy                 ; + 2 past two thirds, + 3/16 of the speed
        lda m_dist+1             ; past the red bars
        cmp #>(2 * M_DIST / 3)
        bcs :+
        inc m_dy
:       cmp #>(M_DIST / 3)
        bcs :+
        inc m_dy
:       lda m_speed
        sec
        sbc #M_WARM
        bcc :+
        sta tmp
        asl
        adc tmp                  ; (carry clear: 3 * 36 at most)
        lsr
        lsr
        lsr
        lsr
        clc
        adc m_dy
        sta m_dy
:       ldx #N_OBJ-1             ; objects fall with it
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
        clc
        adc a_hp,x
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
        lda m_end                ; through: the prize named, then the end
        beq ss_wait
        dec m_end
        jeq storm_end
        bra ss_hits
ss_wait:
        lda m_wait               ; METEOR STORM on screen: no rock yet
        beq :+
        dec m_wait
        bra ss_hits
:       lda m_acc                ; a rock or an object every M_SPACING rows
        clc
        adc m_dy
        cmp #M_SPACING
        bcc :+
        sbc #M_SPACING
        sta m_acc
        jsr storm_spawn
        bra :++
:       sta m_acc
:       lda m_time+1             ; steps flown, and with fire held, up to
        cmp #>M_TIME_MAX         ; M_TIME_MAX
        bne :+
        lda m_time
        cmp #<M_TIME_MAX
        beq ss_rel
:       inc m_time
        bne :+
        inc m_time+1
:       jsr ss_held
        beq ss_rel
        inc m_held
        bne ss_hits
        inc m_held+1
        bra ss_hits
ss_rel: jsr ss_held              ; fire let go (or no ship): no 101 %
        bne ss_hits
        lda #1
        sta m_rel
ss_hits:
        lda tmp2                 ; the ship against the rocks (first hit)
        ora m_end
        jne ss_timers
        lda invul_t
        ora shield_t
        ora shield_t+1
        bne ss_take
        ldx #0
ss_hit: cpx nfly
        beq ss_take
        jsr rock_box             ; tmp..: x0 x1 y0 y1 (a small rock: inset)
        lda r_h                  ; y1 >= first row, y0 <= last row
        cmp #SHIP_HIT_Y0
        bcc ss_miss
        lda r_row
        cmp #SHIP_HIT_Y1+1
        bcs ss_miss
        lda r_w                  ; x1 >= ship_c + 1
        clc
        adc #<-SHIP_HIT_X0
        cmp ship_c
        bcc ss_miss
        lda ship_c               ; x0 <= ship_c + 5
        clc
        adc #SHIP_HIT_X1
        cmp r_col
        bcc ss_miss
        ldy fly_list,x
        jsr explode
        lda #DEATH_T             ; no life lost: the storm ends with it
        sta ship_state
        lda #1
        sta m_crash
        lda #EV_DEATH
        tsb snd_ev
        jsr storm_crash
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
        stz m_dist               ; through: the prize
        jsr storm_prize
        bra ss_timers
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

; Z = 0 if fire is held and the ship alive (tmp2 = 0).
ss_held:
        lda tmp2
        bne :+
        lda fire_held
        rts
:       lda #0
        rts

; Back to a teleport (LEVEL n), then the shop or the next level.
storm_end:
        stz storm
        ldx #NALIENS-1
:       stz a_state,x
        stz a_big,x
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

; The box of flying entry X (fl_x0.. from fly_add) -> r_col x0, r_w x1,
; r_row y0, r_h y1; a small rock's drawing is a cell and a row inside.
rock_box:
        lda fl_x0,x
        sta r_col
        lda fl_x1,x
        sta r_w
        lda fl_y0,x
        sta r_row
        lda fl_y1,x
        sta r_h
        lda fly_list,x
        cmp #M_SMALL0
        bcc :+
        tay
        lda a_state,y
        cmp #ST_ROCK
        bne :+
        inc r_col
        dec r_w
        inc r_row
        dec r_h
:       rts

; A crash: M_CRASH_PTS points per 256 rows flown.
storm_crash:
        lda #<M_DIST
        cmp m_dist               ; (carry: the borrow of the low bytes)
        lda #>M_DIST
        sbc m_dist+1
        tay
        beq :++
:       lda #>M_CRASH_PTS_BCD
        sta pts_hi
        lda #<M_CRASH_PTS_BCD
        jsr add_points
        dey
        bne :-
:       rts

; Through: the prize of the percentage's tier (points with the multiplier,
; credits), its name for M_END steps.
storm_prize:
        jsr storm_pct
        ldx #0                   ; MEGA: fire never let go
        cmp #101
        beq :++
:       inx
        cmp m_tier_pct-1,x
        bcc :-
:       lda m_tier_top,x
        sta pts_top
        lda m_tier_hi,x
        sta pts_hi
        phx
        lda #0
        jsr add_points3
        plx
        lda m_tier_clo,x
        ldy m_tier_chi,x
        phx
        jsr credit
        pla
        clc
        adc #PM_MEGA
        sta pick_msg
        lda #M_END
        sta pick_t
        sta m_end
        lda #EV_ARMOUR
        tsb snd_ev
        rts

; A = the speed percentage: 0 before the first step, 101 while fire was
; never let go, else (100 * m_held + m_time / 2) / m_time.
storm_pct:
        lda m_time
        ora m_time+1
        beq sp_ret
        lda m_rel
        bne :+
        lda #101
sp_ret: rts
:       stz dst                  ; dst, dst+1, cnt: 100 * m_held (24 bits)
        stz dst+1
        stz cnt
        lda m_held
        sta ptr
        lda m_held+1
        sta ptr+1
        stz tmp
        lda #100
        sta tmp2
sp_mul: lsr tmp2
        bcc :+
        clc
        lda dst
        adc ptr
        sta dst
        lda dst+1
        adc ptr+1
        sta dst+1
        lda cnt
        adc tmp
        sta cnt
:       asl ptr
        rol ptr+1
        rol tmp
        lda tmp2
        bne sp_mul
        lda m_time+1             ; + m_time / 2
        lsr
        tay
        lda m_time
        ror
        clc
        adc dst
        sta dst
        tya
        adc dst+1
        sta dst+1
        bcc :+
        inc cnt
:       stz ptr                  ; / m_time: remainder ptr, quotient dst
        stz ptr+1
        ldy #24
sp_div: asl dst
        rol dst+1
        rol cnt
        rol ptr
        rol ptr+1
        lda ptr
        sec
        sbc m_time
        tax
        lda ptr+1
        sbc m_time+1
        bcc :+
        sta ptr+1
        stx ptr
        inc dst
:       dey
        bne sp_div
        lda dst
        rts

; A rock or an object every M_SPACING rows: an object (rand8 < M_PICK) in
; the last free object slot, at the top, or a rock of a size in the last
; free slot of its kind, above the screen.
storm_spawn:
        jsr rand8
        cmp #M_PICK
        bcs sp_rock
        jsr rand8
        and #7
        tay
        lda m_picks,y
        ldx #N_OBJ
:       dex
        bmi sp_done
        ldy obj_y,x
        bne :-
        sta obj_kind,x
        lda #FIELD_TOP
        sta obj_y,x
        jsr rand8
        and #15                  ; the 16 icon columns of the field, but
        cmp #15                  ; the last (byte 35: the distance bar)
        bne :+
        lda #7
:       sta obj_k,x
sp_done:
        rts
sp_rock:
        jsr rand8                ; the size
        sta tmp
        jsr rand8                ; the cell
        and #127
        cmp #M_XMAX+1
        bcc :+
        sbc #64                  ; (carry set)
:       clc
        adc #2
        pha
        ldx #M_ROCKS             ; small: slots M_SMALL0..M_ROCKS-1, else
        ldy #M_SMALL0            ; 0..M_SMALL0-1
        lda tmp
        cmp #M_MEDIUM
        bcs :+
        ldx #M_SMALL0
        ldy #0
:       sty cnt
:       cpx cnt
        beq sp_none
        dex
        ldy a_state,x
        bne :-
        pla
        sta a_x,x
        lda #ST_ROCK
        sta a_state,x
        lda #M_TOP
        sta a_y,x
        ldy #2                   ; small: 2 rows faster, medium 1, big 0
        lda tmp
        cmp #M_MEDIUM
        bcs :+
        dey
        stz a_big,x
        cmp #M_BIG
        bcs :+
        dey
        inc a_big,x
:       tya
        sta a_hp,x
        rts
sp_none:
        pla
        rts

; Lot 11, Warblade: the Meteor Storm icon ends the level at once (not a
; boss level: the storm waits for its end there).
tk_meteor:
        lda #1
        sta subgame
        lda lkind
        cmp #LK_BOSS
        beq :++
        ldx #NALIENS-1
:       stz a_state,x
        dex
        bpl :-
        lda #ROWS
        sta entry_w
        jmp ls_over
:       rts
tk_p1k: lda #$10                 ; Meteor Storm's point tabs
        bra :+
tk_p5k: lda #$50
        bra :+
tk_p10k:
        lda #$00
        ldx #$01
        stx pts_top
        bra :++
:       stz pts_top
:       sta pts_hi
        lda #0
        jmp add_points3

; pack_check in a storm: the small rock -> cur_alien2, the big one ->
; cur_big (WG2.AUX after the boss).
storm_fetch:
        lda #<cur_alien2
        ldy #>cur_alien2
        ldx #ALIEN_TABLE/8
        jsr sf_set
        lda #<STORM_AUX
        ldy #>STORM_AUX
        jsr aux_fetch
        lda #<cur_big
        ldy #>cur_big
        ldx #BIG_TABLE/8
        jsr sf_set
        lda #<(STORM_AUX+ALIEN_TABLE)
        ldy #>(STORM_AUX+ALIEN_TABLE)
        jmp aux_fetch
sf_set: sta af_dst
        sty af_dst+1
        stz af_len+1
        txa
        asl
        rol af_len+1
        asl
        rol af_len+1
        asl
        rol af_len+1
        sta af_len
        rts
.assert ALIEN_TABLE .mod 8 = 0 && BIG_TABLE .mod 8 = 0, error, "storm_fetch: tables of 8-byte multiples"

; ---------------------------------------------------------------------------
; HUD (render.s): hud_now+19 = the percentage; row 0 from storm_template.
storm_keys:
        jsr storm_pct
        sta hud_now+19
        rts
hf_storm:
        ldx #39
:       lda storm_template,x
        sta hud_buf,x
        dex
        bpl :-
        ldx #HUD_SCORE
        jsr hud_score
        lda hud_now+19           ; the percentage, no leading zero
        ldx #' '
        ldy #'0'-1
        cmp #100
        bcc :+
        sbc #100
        ldx #'1'
:       stx hud_buf+STORM_PCT
:       iny
        sec
        sbc #10
        bcs :-
        adc #10+'0'
        sta hud_buf+STORM_PCT+2
        tya
        cpy #'0'
        bne :+
        cpx #' '
        bne :+
        lda #' '
:       sta hud_buf+STORM_PCT+1
        ldx #STORM_CREDITS
        jmp hf_credits

; ---------------------------------------------------------------------------
; Drawing (render.s calls these in place of ship_erase / ship_draw).
; g_col: byte column of the gauge this page shows (0: none), g_n its lit
; bars; b_n: the distance bar's filled rows + 1 this page shows (0: none).
st_erase:
        jsr ship_erase
        jsr st_page
        ldy page
        lda g_col,y
        beq :+
        jsr gauge_want
        bcc se_clear             ; no gauge now
        cmp g_col,y
        beq :+                   ; same column: st_draw rewrites the bars
se_clear:
        lda g_col,y
        sta col
        lda #0
        sta g_col,y
        lda #0
        jsr gauge_put
:       rts

st_draw:
        jsr ship_draw
        jsr st_page
        ldy page
        jsr gauge_want
        bcc sd_bar
        sta col
        lda m_speed
        lsr
        cmp g_n,y
        bne :+
        lda col
        cmp g_col,y
        beq sd_bar
        lda m_speed
        lsr
:       sta g_n,y
        sta tmp2
        lda col
        sta g_col,y
        lda #1
        jsr gauge_put
sd_bar: ldy page
        lda storm
        beq sd_off
        lda b_n,y                ; the bar: its frame once, then the rows
        bne :+                   ; flown since this page's
        lda #<BAR_EMPTY
        ldx #BAR_TOP
        jsr bar_rows
        ldy page
        lda #1
        sta b_n,y
:       lda #<M_DIST             ; rows flown / 32 + 1
        sec
        sbc m_dist
        tax
        lda #>M_DIST
        sbc m_dist+1
        stx tmp
        ldx #5
:       lsr
        ror tmp
        dex
        bne :-
        inc tmp
        lda tmp
        cmp b_n,y
        beq sd_done
        tax                      ; rows b_n-1 .. tmp-2 from the bottom
        lda b_n,y
        sta tmp2
        txa
        sta b_n,y
        lda #BAR_COL
        sta col
:       lda #BAR_TOP+BAR_H
        sec
        sbc tmp2
        tax
        lda #BAR_FULL
        jsr vput
        inc tmp2
        lda tmp2
        cmp tmp
        bne :-
sd_done:
        rts
sd_off: lda b_n,y                ; the storm over: the column cleared
        beq sd_done
        lda #0
        sta b_n,y
        ldx #BAR_TOP
        ; fall through
; A = byte for BAR_H rows from row X, column BAR_COL.
bar_rows:
        sta tmp
        lda #BAR_COL
        sta col
        lda #BAR_H
        sta cnt
:       lda tmp
        jsr vput
        inx
        dec cnt
        bne :-
        rts

; C = 1 and A = the gauge's byte column if there is a gauge to show (a
; storm, the ship alive and not GAME OVER). Keeps Y.
gauge_want:
        clc
        lda storm
        beq :+
        lda ship_state
        bne :+
        phx
        ldx ship_c
        lda cell_byte,x
        plx
        clc
        adc #3
        sec
:       rts

; A = 0: zero the gauge's bars at col; 1: draw them, tmp2 lit (from the
; bottom; the first 8 red, then green).
gauge_put:
        sta cnt
        ldx #GAUGE_Y
        ldy #0
gp_bar: lda cnt
        beq gp_put
        lda col                  ; the column's parity picks the dots
        lsr
        lda #0
        rol
        sta tmp
        cpy tmp2
        bcs gp_dim
        cpy #8
        bcs :+
        ora #2                   ; red (orange)
:       phy
        tay
        lda gauge_lit,y
        ply
        bra gp_put
gp_dim: phy
        tay
        lda gauge_dim,y
        ply
gp_put: jsr vput
        dex
        dex
        iny
        cpy #GAUGE_N
        bne gp_bar
        rts

.segment "STORM2"
; Byte columns even / odd: green, then orange (lit); a dot (dim).
gauge_lit: .byte $2A, $55, $AA, $D5
gauge_dim: .byte $08, $04
BAR_EMPTY = $88                  ; (column 35: odd)
BAR_FULL = $D5
; Meteor Storm's objects (model.M_PICKS) and prizes: bonus.inc.

; A to row X, byte col, of the page being drawn. Keeps A, X, Y.
vput:   phy
        ldy hgr_lo,x
        sty vp_st+1
vp_hi:  ldy hgr_hi,x             ; (st_page: hgr_hi or hgr_hi2)
        sty vp_st+2
        ldy col
vp_st:  sta $FFFF,y
        ply
        rts
st_page:
        lda page
        clc
        adc #>hgr_hi
        sta vp_hi+2
        rts
.assert >hgr_hi2 = >hgr_hi + 1, error, "st_page: hgr_hi2 follows hgr_hi"

; render.s, a pickup's name: aux PICK_AUX + 12 * A -> msg_text.
pick_fetch:
        sta tmp
        stz tmp2
        asl                      ; * 12 = * 8 + * 4
        rol tmp2
        asl
        rol tmp2
        sta ptr
        lda tmp2
        sta ptr+1
        lda ptr
        asl
        rol tmp2
        clc
        adc ptr
        sta ptr
        lda tmp2
        adc ptr+1
        sta ptr+1
        lda #<msg_text
        ldy #>msg_text
        ldx #MSG_LEN
        stx af_len
        stz af_len+1
        sta af_dst
        sty af_dst+1
        lda ptr
        clc
        adc #<PICK_AUX
        pha
        lda ptr+1
        adc #>PICK_AUX
        tay
        pla
        jmp aux_fetch

.segment "STORM"
; Boot (game.s, after this code's copy): LOW2's code and data, WG2.AUX at
; LOW2_AUX -> $0200, for good (no interrupt yet: one AUXMOVE).
low_boot:
        lda #<LOW2_AUX
        sta $3C
        lda #>LOW2_AUX
        sta $3D
        lda #<(LOW2_AUX+LOW2_LEN-1)
        sta $3E
        lda #>(LOW2_AUX+LOW2_LEN-1)
        sta $3F
        lda #<__LOW2_START__
        sta $42
        lda #>__LOW2_START__
        sta $43
        clc                      ; aux -> main
        jmp $C311

storm_template:                  ; Meteor Storm's row 0 (lot 11)
        .byte "000000      SPEED   0%          $0000   "
.assert * - storm_template = 40, error, "storm HUD template: 40 characters"
.code
