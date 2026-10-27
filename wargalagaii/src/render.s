; WARGALAGA II -- drawing on the hidden page. Included by game.s.
;
; Each page keeps what was drawn on it (two frames ago): aliens (pd_*),
; shots (sd_*), the ship, the stars. Drawing order, then erasing order, the
; exact reverse, so that each erase finds the page as its drawing left it:
;   draw:  seated aliens (STA), message (STA), ship (STA), flying aliens
;          and explosions (EOR), shots and bombs (EOR), stars (only on a
;          black byte)
;   erase: stars (only if the byte is still the star), shots and bombs
;          (EOR), flying aliens (EOR, all of them, every frame), ship
;          (zeros, if it moved or changed), seated aliens that moved or
;          left (zeros)
; The HUD (rows 0-7) is apart: a character is rewritten on a page when it
; differs from what that page shows.
; Flying things are drawn with EOR, so erasing them restores what was under
; them (a seated alien, the ship) without redrawing it: only the formation
; rows that swayed are rewritten, one row every other step.
;
; Row tables: hgr_lo/hgr_hi/hgr_hi2 are page aligned, so the routines read
; hgr_hi+R,X for row R of a sprite whose top row is X, and select_page
; rewrites only the high byte of each such operand (HI_LDA sites).

HI_SITES .set 0
.macro HI_LDA r, reg
        .ident(.sprintf("hi_site%d", HI_SITES)) = *
HI_SITES .set HI_SITES + 1
.if .xmatch({reg}, x)
        lda hgr_hi+r,x
.else
        lda hgr_hi+r,y
.endif
.endmacro

; Unrolled sprite rows. X = top row, col = byte column, src = data (W bytes
; a row, rows in order). MODE 0: STA, 2: zeros (no src), 3: EOR. The carry
; stays clear: hgr_lo + col never passes 255. Clobbers A, Y.
.macro SPRITE_ROWS W, H, MODE
        clc
.repeat H, R
        lda hgr_lo+R,x
        adc col
        sta dst
        HI_LDA R, x
        sta dst+1
.if MODE = 2
        lda #0
        sta (dst)
  .repeat W-1, B
        ldy #B+1
        sta (dst),y
  .endrepeat
.else
  .repeat W, B
        ldy #W*R+B
        lda (src),y
    .if B = 0
      .if MODE = 3
        eor (dst)
      .endif
        sta (dst)
    .else
      .if R > 0
        ldy #B
      .endif
      .if MODE = 3
        eor (dst),y
      .endif
        sta (dst),y
    .endif
  .endrepeat
.endif
.endrepeat
.endmacro

; A one-byte column of H rows, all the same pattern (pat): EOR.
.macro COLUMN_ROWS H
        clc
.repeat H, R
        lda hgr_lo+R,x
        adc col
        sta dst
        HI_LDA R, x
        sta dst+1
        lda (dst)
        eor pat
        sta (dst)
.endrepeat
.endmacro

.zeropage
pat:      .res 1

.bss
render_vars:                    ; zeroed by render_init
pd_x:     .res NALIENS*2        ; alien drawn at, per page
pd_y:     .res NALIENS*2        ; 0 = not drawn
pd_f:     .res NALIENS*2        ; table entry drawn, + $80 if drawn seated
md_list:  .res NALIENS*2        ; slots drawn flying, per page
md_n:     .res 2
sd_y:     .res MAX_SHOTS*2      ; shot drawn at (top row, 0 = none), per page
sd_col:   .res MAX_SHOTS*2
sd_pat:   .res MAX_SHOTS*2
bd_y:     .res E_SHOTS*2        ; bomb drawn at, per page
bd_col:   .res E_SHOTS*2
bd_pat:   .res E_SHOTS*2
od_y:     .res N_OBJ*2          ; object drawn at, per page
od_k:     .res N_OBJ*2
od_kind:  .res N_OBJ*2
star_lo:  .res NSTARS*2         ; screen byte written per page, hi 0 = none
star_hi:  .res NSTARS*2
boss_drawn: .res 2              ; boss cell drawn on each page, $FF none
ufo_drawn: .res 2               ; saucer cell drawn on each page, $FF none
ship_drawn: .res 2              ; cell drawn on each page
ship_img: .res 2                ; image drawn: 0 ship, 1-2 explosion, $FF none
ship_want: .res 1
msg_drawn: .res 2               ; message id each page shows
msg_text: .res 12               ; MSG_LEN
mn:       .res 2                ; LEVEL n: the number
mn_t:     .res 2
mn_k:     .res 1
mn_d:     .res 1
mn_lead:  .res 1
hud_seen: .res 80               ; HUD characters each page shows
hud_key:  .res 2*HUD_KEYS       ; the state each page's HUD shows
hud_buf:  .res 40
hud_now:  .res HUD_KEYS
form_list: .res NALIENS
nform:    .res 1
move_list: .res NALIENS
nmove:    .res 1
cur_f:    .res 1                ; table entry wanted for the alien in hand
pr_off:   .res ROWS*2           ; row sway offset / frame each page was drawn with
pr_anim:  .res ROWS*2
row_dirty: .res ROWS
render_vars_end:

.code
render_init:
        lda #<render_vars        ; every record: nothing drawn
        sta dst
        lda #>render_vars
        sta dst+1
        ldx #>(render_vars_end-render_vars)
        ldy #<(render_vars_end-render_vars)
        jsr zero_block
        lda #$FF
        sta ship_img
        sta ship_img+1
        sta boss_drawn
        sta boss_drawn+1
        sta ufo_drawn
        sta ufo_drawn+1
        ldx #ROWS*2-1
:       sta pr_off,x
        dex
        bpl :-
        ldx #80-1
:       sta hud_seen,x
        dex
        bpl :-
        ldx #2*HUD_KEYS-1
:       sta hud_key,x
        dex
        bpl :-
        ldx #40-1
:       lda hud_template,x
        sta hud_buf,x
        dex
        bpl :-
        rts

render:
        jsr stars_erase
        jsr _a2_vbl_scan
        jsr shots_erase
        jsr _a2_vbl_scan
        jsr bombs_erase
        jsr objects_erase
        jsr movers_erase
        jsr boss_erase
        jsr ufo_erase
        jsr ship_choose
        jsr ship_erase
        jsr aliens_pass
        jsr form_draw
        jsr msg_draw
        jsr ship_draw
        jsr movers_draw
        jsr boss_draw
        jsr ufo_draw
        jsr shots_draw
        jsr _a2_vbl_scan
        jsr bombs_draw
        jsr objects_draw
        jsr _a2_vbl_scan
        jsr stars_draw
        jsr hud_draw
render_done:
        rts

; ---------------------------------------------------------------------------
; Shots: one byte wide, SHOT_H rows of the same pattern, EOR both ways.
shots_erase:
        ldx pg10
se_shot:
        lda sd_y,x
        beq se_next
        stz sd_y,x
        phx
        ldy sd_col,x
        sty col
        ldy sd_pat,x
        sty pat
        tax
        jsr shot_eor
        plx
se_next:
        inx
        txa
        sec
        sbc pg10
        cmp #MAX_SHOTS
        bne se_shot
        rts

shots_draw:
        ldx #MAX_SHOTS-1
sh_draw:
        lda shot_y,x
        beq sh_next
        phx
        ldy shot_c,x
        lda cell_byte,y
        sta col
        lda cell_shift,y
        tay
        lda shot_pat,y
        sta pat
        txa
        clc
        adc pg10
        tay
        lda col
        sta sd_col,y
        lda pat
        sta sd_pat,y
        lda shot_y,x
        sta sd_y,y
        tax
        jsr shot_eor
        plx
sh_next:
        dex
        bpl sh_draw
        rts

; Bombs: as shots, falling.
bombs_erase:
        lda page
        beq :+
        lda #E_SHOTS
:       sta tmp                  ; first slot of this page
        clc
        adc #E_SHOTS-1
        tax
be_bomb:
        lda bd_y,x
        beq be_next
        stz bd_y,x
        phx
        ldy bd_col,x
        sty col
        ldy bd_pat,x
        sty pat
        tax
        jsr bomb_eor
        plx
be_next:
        cpx tmp
        beq :+
        dex
        bra be_bomb
:       rts

; Falling objects: a 2-byte icon on an even byte column, EOR both ways.
objects_erase:
        lda page
        beq :+
        lda #N_OBJ
:       sta tmp                  ; first slot of this page
        clc
        adc #N_OBJ-1
        tax
oe_obj: lda od_y,x
        beq oe_next
        stz od_y,x
        phx
        pha
        lda od_kind,x
        jsr icon_src
        lda od_k,x
        asl
        sta col
        plx                      ; (the row)
        jsr obj_eor
        jsr _a2_vbl_scan          ; (6 objects + 6 bombs: longer than a blank)
        plx
oe_next:
        cpx tmp
        beq :+
        dex
        bra oe_obj
:       rts

objects_draw:
        ldx #N_OBJ-1
ob_draw:
        lda obj_y,x
        beq ob_next
        phx
        txa
        ldy page
        beq :+
        clc
        adc #N_OBJ
:       tay
        lda obj_y,x
        sta od_y,y
        lda obj_k,x
        sta od_k,y
        asl
        sta col
        lda obj_kind,x
        sta od_kind,y
        jsr icon_src
        lda obj_y,x
        tax
        jsr obj_eor
        plx
        jsr _a2_vbl_scan
ob_next:
        dex
        bpl ob_draw
        rts

; src = icon A (2 * OBJ_H bytes). Keeps X, Y.
icon_src:
        phy
        tay
        lda icon_lo,y
        sta src
        lda icon_hi,y
        sta src+1
        ply
        rts

bombs_draw:
        ldx #E_SHOTS-1
bo_draw:
        lda e_y,x
        beq bo_next
        phx
        ldy e_c,x
        lda cell_byte,y
        sta col
        lda cell_shift,y
        tay
        lda bomb_pat,y
        sta pat
        txa
        ldy page
        beq :+
        clc
        adc #E_SHOTS
:       tay
        lda col
        sta bd_col,y
        lda pat
        sta bd_pat,y
        lda e_y,x
        sta bd_y,y
        tax
        jsr bomb_eor
        plx
bo_next:
        dex
        bpl bo_draw
        rts

; ---------------------------------------------------------------------------
; Ship: 0 = the ship (blinking while nothing hurts it), 1-2 = its
; explosion frames for the first 24 steps of ship_state, $FF = nothing.
; Redrawn on a page when its cell or image changed since that page.
ship_choose:
        lda game_over
        bne sc_none
        lda ship_state
        beq sc_alive
        cmp #DEATH_T-24+1
        bcc sc_none
        lsr
        lsr
        and #1
        inc a
        bra sc_set
sc_alive:
        lda invul_t              ; blinks while nothing hurts it
        ora shield_t
        and #4
        bne sc_none
        lda #0
        bra sc_set
sc_none:
        lda #$FF
sc_set: sta ship_want
        rts

ship_erase:
        ldy page
        lda ship_img,y
        cmp #$FF
        beq :+
        cmp ship_want
        bne se_go
        lda ship_c
        cmp ship_drawn,y
        beq :+
se_go:  ldx ship_drawn,y
        lda cell_byte,x
        sta col
        lda #$FF
        sta ship_img,y
        ldx #SHIP_Y
        jsr ship_clr
:       rts

ship_draw:
        ldy page
        lda ship_want
        cmp #$FF
        beq :+
        lda ship_img,y           ; still there: erase kept it
        cmp #$FF
        bne :+
        lda ship_want
        sta ship_img,y
        lda ship_c
        sta ship_drawn,y
        tax
        lda cell_byte,x
        sta col
        ldy cell_shift,x
        lda ship_want
        bne sd_boom
        lda ship_lo,y
        sta src
        lda ship_hi,y
        sta src+1
        bra sd_go
sd_boom:
        dec a                    ; frame
        sta tmp
        tya
        asl
        ora tmp
        tay
        lda shipboom_lo,y
        sta src
        lda shipboom_hi,y
        sta src+1
sd_go:  ldx #SHIP_Y
        jmp ship_sta
:       rts
.assert SHIPBOOM_W = SHIP_W && SHIPBOOM_H = SHIP_H, error, "the ship explosion uses the ship routines"

; A message in the middle of the field: 1 GAME OVER, 2 LEVEL n (the level
; being teleported to), 3 METEOR STORM (its first steps), 5 + pick_msg
; (what a pickup did, PICK_T steps: bonus.inc pick_*), 4 DEMO (the
; attract mode, when there is no other), 0 none. Rewritten
; on a page when it differs from what that page shows (none: spaces).
; msg_drawn = what each page shows.
msg_draw:
        lda #1
        ldx game_over
        bne md_id
        lda #2
        ldx phase
        bne md_id
        lda storm                ; 3 while m_wait counts, in a storm
        beq md_demo
        lda m_wait
        beq md_demo
        lda #3
        bra md_id
md_demo:
        lda pick_t               ; 5 + pick_msg: what a pickup did
        beq :+
        lda pick_msg
        clc
        adc #5
        bra md_id
:       lda demo                 ; 4 DEMO (the attract mode), else 0
        beq md_id
        lda #4
md_id:  ldy page
        cmp msg_drawn,y
        jeq md_none
        sta msg_drawn,y
        cmp #5
        jcs md_pick
        tay
        ldx #MSG_LEN-1           ; the text in msg_text
md_char:
        lda #' '
        cpy #1
        bne :+
        lda msg_over,x
:       cpy #3
        bne :+
        lda msg_storm,x
:       cpy #4
        bne :+
        lda msg_demo,x
:       sta msg_text,x
        dex
        bpl md_char
        cpy #2
        jne md_put
        ldx #MSG_LEN-1           ; LEVEL n: (level + 2) + 100 * loop
:       lda msg_level,x
        sta msg_text,x
        dex
        bpl :-
        lda loop                 ; n = 100 * loop + level + 2 (16 bits: up
        sta mn_t                 ; to 25 601; the hundreds were loop mod 10,
        stz mn_t+1               ; wrong past level 1 000, bug hunt 6)
        stz mn
        stz mn+1
        lda #100
        sta mn_k
md_mul: lsr mn_k                 ; n += loop << bit, for each bit of 100
        bcc :+
        clc
        lda mn
        adc mn_t
        sta mn
        lda mn+1
        adc mn_t+1
        sta mn+1
:       asl mn_t
        rol mn_t+1
        lda mn_k
        bne md_mul
        lda level
        inc a
        ldx demo
        beq :+
        jsr demo_next             ; show the actual showcase destination
:       clc                      ; index -> displayed level number
        adc #1
        clc
        adc mn
        sta mn
        bcc :+
        inc mn+1
:       ldx #6                   ; the digits from column 6, no leading 0
        ldy #0
        stz mn_lead
md_pow: lda #'0'
        sta mn_d
:       lda mn                   ; subtract 10 000, 1 000, 100, 10
        sec
        sbc p10_lo,y
        pha
        lda mn+1
        sbc p10_hi,y
        bcc :+
        sta mn+1
        pla
        sta mn
        inc mn_d
        bra :-
:       pla
        lda mn_d
        cmp #'0'
        bne :+
        bit mn_lead
        bpl md_next
:       sta msg_text,x
        inx
        lda #$80
        sta mn_lead
md_next:
        iny
        cpy #4
        bne md_pow
        lda mn
        ora #'0'
        sta msg_text,x
        bra md_put
md_pick:
        sbc #5                   ; (carry set) the pickup's text, in LOWM
        tax
        lda pick_lo,x
        sta src
        lda pick_hi,x
        sta src+1
        ldy #MSG_LEN-1
:       lda (src),y
        sta msg_text,y
        dey
        bpl :-
md_put: ldx #0
:       phx
        lda msg_text,x
        pha
        txa
        clc
        adc #MSG_COL
        sta col
        pla
        ldx #MSG_ROW
        jsr glyph
        jsr _a2_vbl_scan
        plx
        inx
        cpx #MSG_LEN
        bne :-
md_none:
        rts
; A mod 10 (A < 256). Z set if 0.
p10_lo: .lobytes 10000, 1000, 100, 10
p10_hi: .hibytes 10000, 1000, 100, 10
msg_level: .byte "LEVEL       "
msg_storm: .byte "METEOR STORM"
msg_demo:  .byte "    DEMO    "
MSG_ROW = 96
MSG_LEN = 12                     ; LEVEL nnnnn, METEOR STORM (GAME OVER: as
                                 ; it was in 11)
MSG_COL = (40 - MSG_LEN) / 2

; ---------------------------------------------------------------------------
; HUD. hud_key gathers what it shows; when it differs from what this page
; shows, hud_buf is filled from the state and every character that differs
; from this page's is rewritten.
hud_draw:
        jsr hud_keys
        ldx page
        beq :+
        ldx #HUD_KEYS
:       ldy #0
        lda #0
        sta tmp2                 ; differs?
hk_cmp: lda hud_now,y
        cmp hud_key,x
        beq :+
        sta hud_key,x
        lda #1
        sta tmp2
:       inx
        iny
        cpy #HUD_KEYS
        bne hk_cmp
        lda tmp2
        bne :+
        rts
:       jsr hud_fill
        ldx #39
        ldy #39
        lda page
        beq hd_char
        ldy #79
hd_char:
        lda hud_buf,x
        cmp hud_seen,y
        beq hd_next
        sta hud_seen,y
        phx
        phy
        stx col
        ldx #0
        jsr glyph
        jsr _a2_vbl_scan
        ply
        plx
hd_next:
        dey
        dex
        bpl hd_char
        rts

hud_keys:
        jsr hk_game
        lda storm                ; Meteor Storm's HUD (lot 8): speed, distance
        beq :+
        lda #$FF                 ; (lives are never $FF)
        sta hud_now+3
        lda m_speed              ; speed: 1..8 segments
        lsr
        lsr
        lsr
        inc a
        sta hud_now+4
        lda m_dist               ; distance left: (m_dist + 511) / 512
        clc
        adc #<511
        lda m_dist+1
        adc #>511
        lsr
        sta hud_now+5
:       rts
hk_game:
        lda score
        sta hud_now
        lda score+1
        sta hud_now+1
        lda score+2
        sta hud_now+2
        lda lives
        sta hud_now+3
        lda armour
        sta hud_now+4
        lda shot_limit
        sta hud_now+5
        lda credits
        sta hud_now+6
        lda credits+1
        sta hud_now+7
        lda s_level
        sta hud_now+8
        lda t_level
        sta hud_now+9
        lda extra_bits
        sta hud_now+10
        rts

; The changing characters of hud_buf (the rest is hud_template).
HUD_SCORE = 0
HUD_LIVES = 8
HUD_ARMOUR = 11
HUD_SBAR = 14
HUD_BBAR = 21
HUD_TIME = 28
HUD_CREDITS = 31
HUD_EXTRA = 35
BAR_LEN = 5
STORM_SPEED = 12                 ; Meteor Storm's HUD (storm_template)
STORM_DIST = 25
STORM_CREDITS = 35
STORM_BAR = 8
hud_fill:
        ldx #39                  ; the fixed characters
        lda storm
        jne hf_storm
:       lda hud_template,x
        sta hud_buf,x
        dex
        bpl :-
        ldx #HUD_SCORE
        lda score+2
        jsr hud_bcd
        lda score+1
        jsr hud_bcd
        lda score
        jsr hud_bcd
        lda lives
        ora #'0'
        sta hud_buf+HUD_LIVES
        lda armour
        ora #'0'
        sta hud_buf+HUD_ARMOUR
        ldx #HUD_SBAR            ; S: speed level 1..5
        lda s_level
        jsr hud_bar
        ldx #HUD_BBAR            ; B: shots on screen beyond 5 (0..5)
        lda shot_limit
        sec
        sbc #B_MIN
        jsr hud_bar
        lda t_level              ; T: tens of seconds
        ora #'0'
        sta hud_buf+HUD_TIME
        ldx #0                   ; E X T R A: the letter, or '-'
        lda extra_bits
        sta tmp2
:       lda #'-'
        lsr tmp2
        bcc :+
        lda extra_letters,x
:       sta hud_buf+HUD_EXTRA,x
        inx
        cpx #5
        bne :--
        ldx #HUD_CREDITS
hf_credits:
        lda credits+1
        jsr hud_bcd
        lda credits
        ; fall through
; A = two BCD digits -> hud_buf,X and X+1; X += 2.
hud_bcd:
        pha
        lsr
        lsr
        lsr
        lsr
        ora #'0'
        sta hud_buf,x
        inx
        pla
        and #$0F
        ora #'0'
        sta hud_buf,x
        inx
        rts
; Meteor Storm: score, speed, distance left, credits.
hf_storm:
:       lda storm_template,x
        sta hud_buf,x
        dex
        bpl :-
        ldx #HUD_SCORE
        lda score+2
        jsr hud_bcd
        lda score+1
        jsr hud_bcd
        lda score
        jsr hud_bcd
        ldx #STORM_SPEED
        lda hud_now+4
        ldy #STORM_BAR
        jsr hud_barn
        ldx #STORM_DIST
        lda hud_now+5
        ldy #STORM_BAR
        jsr hud_barn
        ldx #STORM_CREDITS
        bra hf_credits
; A = full segments (0..BAR_LEN) -> BAR_LEN characters at hud_buf,X;
; hud_barn: Y characters.
hud_bar:
        ldy #BAR_LEN
hud_barn:
        sta tmp
:       lda #GLYPH_FULL
        dec tmp
        bpl :+
        lda #GLYPH_EMPTY
:       sta hud_buf,x
        inx
        dey
        bne :--
        rts

; A = character, X = top row, col: its 8 rows (STA). Clobbers A, X, Y, src.
glyph:  sec
        sbc #$20
        stz src+1
        asl
        rol src+1
        asl
        rol src+1
        asl
        rol src+1
        clc
        adc #<bbfont
        sta src
        lda src+1
        adc #>bbfont
        sta src+1
        jmp glyph_sta

; ---------------------------------------------------------------------------
; Flying aliens drawn on this page last time: EOR them away.
movers_erase:
        ldy page
        lda md_n,y
        beq me_done
        sta cnt
        lda #0
        sta md_n,y
        ldx pg40
me_alien:
        phx
        ldy md_list,x
        lda pd_f,y               ; the drawing it had (big: bit 6)
        bit #$40
        bne :+
        sta cur_f                ; small: inline
        tax
        lda fly_lo,x
        sta src
        lda fly_hi,x
        sta src+1
        ldx pd_x,y
        lda cell_byte,x
        sta col
        bra :++
:       jsr pose_src
        lda pd_x,y
        jsr pose_col
:
        lda pd_y,y
        tax
        lda #0
        sta pd_f,y
        sta pd_y,y
        txa
        jsr any_eor_clip
        jsr _a2_vbl_scan
        plx
        inx
        dec cnt
        bne me_alien
me_done:
        rts

; A = anchor row, src/col/cur_f set: EOR the alien (big: 16 rows from
; 8 above), clipped at the bottom edge.
any_eor_clip:
        bit cur_f
        bvc alien_eor_clip
        sec
        sbc #8                   ; big: its top
        cmp #192-BIG_H+1
        bcs :+
        tax
        jmp big_eor
:       sta r_row
        eor #$FF                 ; 192 - top rows, at most 16
        sec
        adc #192
        cmp #BIG_H
        bcc :+
        lda #BIG_H
:       sta r_h
        lda col
        sta r_col
        lda #BIG_W
        sta r_w
        jmp eor_rect

; A = cur_f-like entry (bit 6: big): src, cur_f. Keeps X, Y.
pose_src:
        sta cur_f
        phy
        and #$3F
        tay
        bit cur_f
        bvs :+
        lda fly_lo,y
        sta src
        lda fly_hi,y
        sta src+1
        ply
        rts
:       lda big_lo,y
        sta src
        lda big_hi,y
        sta src+1
        ply
        rts

; A = anchor cell, cur_f set: col (big: from 2 cells left). Keeps X, Y.
pose_col:
        bit cur_f
        bvc :+
        dec a
        dec a
:       phx
        tax
        lda cell_byte,x
        sta col
        plx
        rts

; A = top row, src/col set: EOR the alien, clipped at the bottom edge.
alien_eor_clip:
        cmp #192-ALIEN_H+1
        bcs :+
        tax
        jmp alien_eor
:       sta r_row
        eor #$FF                 ; 192 - y rows
        sec
        adc #192                 ; ~y + 1 + 192
        sta r_h
        lda col
        sta r_col
        lda #ALIEN_W
        sta r_w
        jmp eor_rect

; ---------------------------------------------------------------------------
; A pass over the 40 aliens: erase seated drawings that moved or left
; (zeros), queue seated aliens to draw in form_list, flying ones in
; move_list. A formation row whose sway offset and frame are those this
; page was last drawn with is clean: its seated aliens drawn seated are
; passed over at the cost of a few tests.
aliens_pass:
        ldx #ROWS-1
        ldy #ROWS-1
        lda page
        beq ar_row
        ldy #ROWS*2-1
ar_row: lda row_off,x
        cmp pr_off,y
        bne :+
        lda row_anim,x
        cmp pr_anim,y
        bne :+
        stz row_dirty,x
        bra :++
:       lda #1
        sta row_dirty,x
        lda row_off,x
        sta pr_off,y
        lda row_anim,x
        sta pr_anim,y
:       dey
        dex
        bpl ar_row
        ldx #NALIENS-1
ae_alien:
        lda a_state,x
        cmp #ST_FORM
        bne ae_slot
        ldy alien_row,x
        lda row_dirty,y
        bne ae_slot
        txa
        clc
        adc pg40
        tay
        lda pd_f,y
        jmi ae_next              ; seated, drawn seated, row clean
        bra ae_full
ae_slot:
        txa
        clc
        adc pg40
        tay                      ; Y = slot of this alien on this page
ae_full:
        lda a_state,x
        jeq ae_gone
        sta tmp2
        lda a_big,x              ; on screen as drawn? (small: inline)
        bne :+
        lda a_y,x
        cmp #FIELD_TOP
        jcc ae_gone
        cmp #192
        jcs ae_gone
        bra :++
:       jsr drawn_x
        jcc ae_gone
:       lda tmp2
        cmp #ST_FORM
        jne ae_mover
        jsr want_f               ; seated
        sta cur_f
        lda pd_y,y
        beq ae_queue             ; not drawn here
        cmp a_y,x
        bne ae_erase
        lda pd_x,y
        cmp a_x,x
        bne ae_span              ; swayed along its row
        lda pd_f,y
        cmp cur_f
        jeq ae_next              ; unchanged
        bra ae_queue             ; new frame only: STA covers the old one
ae_span:                         ; swayed one cell: STA covers the old
        phy                      ; drawing but for a column it left
        bit cur_f                ; (A = old anchor cell)
        bvc :+
        dec a                    ; big: its box starts 2 cells left
        dec a
:       tay
        lda cell_byte,y
        sta col                  ; old start byte
        ldy a_x,x
        bit cur_f
        bvc :+
        dey
        dey
:       sec
        sbc cell_byte,y          ; old - new
        beq sp_same
        cmp #$FF
        beq sp_right
        cmp #1
        bne sp_far
        lda col                  ; moved left: the old last byte
        clc
        adc #ALIEN_W-1
        bit cur_f
        bvc :+
        inc a                    ; (big: one byte wider)
:       sta col
sp_right:
        ply
        phx
        phy
        lda pd_y,y
        bit cur_f
        bvs :+
        tax
        jsr column_clr
        bra :++
:       sec
        sbc #8
        tax
        jsr column_clr16
:       jsr _a2_vbl_scan          ; a whole row may slide: keep counting VBL
        ply
        plx
        bra ae_queue
sp_far: ply
        bra ae_erase
sp_same:
        ply
        bra ae_queue
ae_erase:
        jsr erase_seat
ae_queue:
        txa
        phx
        ldx nform
        sta form_list,x
        inc nform
        plx
        bra ae_next
ae_mover:
        lda pd_y,y               ; drawn seated (a dive starts): erase
        beq :+
        jsr erase_seat
:       txa
        phx
        ldx nmove
        sta move_list,x
        inc nmove
        plx
        bra ae_next
ae_gone:
        lda pd_y,y
        beq ae_next
        jsr erase_seat
ae_next:
        dex
        bmi :++
        txa                      ; every 8 aliens: the pass alone can last
        and #7                   ; longer than a vertical blank
        bne :+
        jsr _a2_vbl_scan
:       jmp ae_alien
:       rts

; X = alien: C = 1 if it is on screen as it is drawn (big: from row 16;
; an explosion is drawn small). Keeps X, Y.
drawn_x:
        lda a_y,x
        cmp #192
        bcs :++
        pha
        lda a_big,x
        beq :+
        lda a_state,x
        cmp #ST_BOOM
        beq :+
        pla
        cmp #16
        rts
:       pla
        cmp #FIELD_TOP
        rts
:       clc
        rts

; Zero the seated drawing of slot Y (X = alien). Keeps X, Y.
erase_seat:
        phx
        phy
        lda pd_f,y
        sta cur_f
        lda pd_x,y
        jsr pose_col
        ldx pd_y,y
        lda #0
        sta pd_y,y
        sta pd_f,y
        bit cur_f
        bvs :+
        jsr alien_clr
        bra :++
:       txa                      ; big: 16 rows from 8 above
        sec
        sbc #8
        tax
        jsr big_clr
:       jsr _a2_vbl_scan
        ply
        plx
        rts

; A = the table entry alien X needs (shift*2 + frame), + $80 if seated.
; Keeps X, Y.
want_f: phy
        lda a_state,x
        cmp #ST_FORM
        beq wf_seat
        cmp #ST_BOOM
        beq wf_boom
        lda step_count           ; flying: flaps every 4 steps
        lsr
        lsr
        and #1
        bra wf_add
wf_boom:
        lda a_timer,x            ; explosion: frame by its timer
        lsr
        lsr
        and #1
        ora #BOOM_ENTRY
        bra wf_add
wf_seat:
        ldy alien_row,x          ; seated: the row's frame
        lda row_anim,y
        ora #$80
wf_add: ldy a_big,x              ; drawn big: not as an explosion
        bne wf_big
wf_small:
        ldy a_x,x
        clc
        adc cell_shift2,y
        ply
        rts
wf_big: ldy a_state,x
        cpy #ST_BOOM
        beq wf_small
        ldy a_x,x                ; big: the shift of its box (2 cells left)
        dey
        dey
        clc
        adc cell_shift2,y
        ora #$40
        ply
        rts

; Alien X about to be drawn: work out its table entry and byte column,
; record them as drawn in its slot. -> Y = slot. Keeps X.
alien_pose:
        jsr want_f
        bit #$40
        bne ap_big
        sta cur_f                ; small: inline
        and #$3F
        tay
        lda fly_lo,y
        sta src
        lda fly_hi,y
        sta src+1
        ldy a_x,x
        lda cell_byte,y
        sta col
        bra ap_rec
ap_big: jsr pose_src
        lda a_x,x
        jsr pose_col
ap_rec: txa
        clc
        adc pg40
        tay
        lda cur_f
        sta pd_f,y
        lda a_x,x
        sta pd_x,y
        lda a_y,x
        sta pd_y,y
        rts

; Seated aliens: STA at their seat.
form_draw:
        lda nform
        beq fd_done
fd_alien:
        dec nform
        ldx nform
        lda form_list,x
        tax
        jsr alien_pose
        lda a_y,x
        bit cur_f
        bvs :+
        tax
        jsr alien_sta
        bra :++
:       sec                      ; big: 16 rows from 8 above
        sbc #8
        tax
        jsr big_sta
:       jsr _a2_vbl_scan
        lda nform
        bne fd_alien
fd_done:
        rts

; Flying aliens: EOR, clipped at the bottom edge; listed for the erase.
movers_draw:
        lda nmove
        beq md_done
md_alien:
        dec nmove
        ldx nmove
        lda move_list,x
        tax
        jsr alien_pose           ; Y = slot
        sty tmp
        ldy page                 ; list the slot on this page
        lda md_n,y
        inc a
        sta md_n,y
        dec a
        clc
        adc pg40
        tay
        lda tmp
        sta md_list,y
        lda a_y,x
        jsr any_eor_clip
        jsr _a2_vbl_scan
        lda nmove
        bne md_alien
md_done:
        rts

; ---------------------------------------------------------------------------
; The boss: EOR both ways, like flying aliens, but only when it changed
; since this page drew it (it leaps every BOSS_STEP steps; it blinks while
; it explodes). In two halves of 12 rows with a VBL scan between.
boss_want:                       ; A = cell to show, $FF none
        lda boss_hp
        bne :+
        lda boss_boom
        and #4
        beq :++
:       lda boss_x
        rts
:       lda #$FF
        rts

boss_erase:
        jsr boss_want
        ldy page
        cmp boss_drawn,y
        beq :+                   ; as drawn: kept
        ldx boss_drawn,y
        cpx #$FF
        beq :+
        lda #$FF
        sta boss_drawn,y
        txa
        jmp boss_eor
:       rts

boss_draw:
        jsr boss_want
        cmp #$FF
        beq :+
        ldy page
        ldx boss_drawn,y
        cpx #$FF
        bne :+                   ; still there
        sta boss_drawn,y
        jmp boss_eor
:       rts

; A = boss cell (a multiple of 7): EOR its 24 rows. Clobbers A, X, Y.
boss_eor:
        tax
        lda cell_byte,x
        sta r_col
        lda #<boss_s0
        sta src
        lda #>boss_s0
        sta src+1
        lda #BOSS_W
        sta r_w
        lda #BOSS_Y
        sta r_row
        lda #BOSS_H/2
        sta r_h
        jsr eor_rect             ; (leaves src on the next row)
        jsr _a2_vbl_scan
        lda #BOSS_Y+BOSS_H/2
        sta r_row
        lda #BOSS_H/2
        sta r_h
        jsr eor_rect
        jmp _a2_vbl_scan

; The hurry-up saucer: it moves every step, so EOR off and on each frame.
ufo_erase:
        ldy page
        lda ufo_drawn,y
        cmp #$FF
        beq uf_done
        tax
        lda #$FF
        sta ufo_drawn,y
        bra ufo_eor
ufo_draw:
        lda hurry
        beq uf_done
        ldy page
        ldx h_x
        txa
        sta ufo_drawn,y
ufo_eor:                         ; X = cell
        lda cell_byte,x
        sta r_col
        ldy cell_shift,x
        lda ufo_lo,y
        sta src
        lda ufo_hi,y
        sta src+1
        lda #UFO_W
        sta r_w
        lda #HURRY_Y
        sta r_row
        lda #UFO_H
        sta r_h
        jmp eor_rect
uf_done:
        rts

; ---------------------------------------------------------------------------
; Unrolled sprite routines (X = top row, col, src / pat).
alien_sta:
        SPRITE_ROWS ALIEN_W, ALIEN_H, 0
alien_sta_done:
        rts
alien_eor:
        SPRITE_ROWS ALIEN_W, ALIEN_H, 3
alien_eor_done:
        rts
alien_clr:
        SPRITE_ROWS ALIEN_W, ALIEN_H, 2
alien_clr_done:
        rts
ship_sta:
        SPRITE_ROWS SHIP_W, SHIP_H, 0
        rts
ship_clr:
        SPRITE_ROWS SHIP_W, SHIP_H, 2
        rts
shot_eor:
        COLUMN_ROWS SHOT_H
        rts
big_sta:                         ; big aliens: X = top row (anchor - 8)
        SPRITE_ROWS BIG_W, BIG_H, 0
        rts
big_eor:
        SPRITE_ROWS BIG_W, BIG_H, 3
        rts
big_clr:
        SPRITE_ROWS BIG_W, BIG_H, 2
        rts
column_clr16:                    ; one byte column of a big alien: zeros
        clc
.repeat BIG_H, R
        lda hgr_lo+R,x
        adc col
        sta dst
        HI_LDA R, x
        sta dst+1
        lda #0
        sta (dst)
.endrepeat
        rts
bomb_eor:
        COLUMN_ROWS BOMB_H
        rts
obj_eor:
        SPRITE_ROWS 2, OBJ_H, 3
        rts
column_clr:                      ; one byte column of an alien: zeros
        clc
.repeat ALIEN_H, R
        lda hgr_lo+R,x
        adc col
        sta dst
        HI_LDA R, x
        sta dst+1
        lda #0
        sta (dst)
.endrepeat
        rts
glyph_sta:
        SPRITE_ROWS 1, 8, 0
        rts

; Generic: STA / zeros, r_h rows of r_w bytes (from src) at (r_row, byte
; r_col): big aliens. Clobbers A, X, Y, r_h, src.
rect_sta:
        ldx r_row
rs_row: lda hgr_lo,x
        clc
        adc r_col
        sta dst
        HI_LDA 0, x
        sta dst+1
        ldy r_w
        dey
:       lda (src),y
        sta (dst),y
        dey
        bpl :-
        lda src
        clc
        adc r_w
        sta src
        bcc :+
        inc src+1
:       inx
        dec r_h
        bne rs_row
        rts
rect_clr:
        ldx r_row
rc_row: lda hgr_lo,x
        clc
        adc r_col
        sta dst
        HI_LDA 0, x
        sta dst+1
        ldy r_w
        dey
        lda #0
:       sta (dst),y
        dey
        bpl :-
        inx
        dec r_h
        bne rc_row
        rts

; Generic, for clipped sprites: EOR r_h rows of r_w bytes from src at
; (r_row, byte r_col). Clobbers A, X, Y, r_h, src.
eor_rect:
        ldx r_row
er_row: lda hgr_lo,x
        clc
        adc r_col
        sta dst
        HI_LDA 0, x
        sta dst+1
        ldy r_w
        dey
er_byte:
        lda (src),y
        eor (dst),y
        sta (dst),y
        dey
        bpl er_byte
        lda src
        clc
        adc r_w
        sta src
        bcc :+
        inc src+1
:       inx
        dec r_h
        bne er_row
        rts

; ---------------------------------------------------------------------------
; Remove this page's stars: a byte still holding exactly its star is
; zeroed; one a sprite was drawn over (or erased) is left alone.
stars_erase:
        ldx #NSTARS-1            ; X = star, Y = its slot for this page
        ldy #NSTARS-1
        lda page
        beq se_star
        ldy #NSTARS*2-1
se_star:
        lda star_hi,y
        beq st_next
        sta dst+1
        lda star_lo,y
        sta dst
        lda (dst)
        cmp star_val,x
        bne st_next
        lda #0
        sta (dst)
st_next:
        dey
        dex
        bpl se_star
        rts

; Put each star on this page where the byte is black; record where.
stars_draw:
        ldx #NSTARS-1
        lda page
        beq :+
        lda #NSTARS
:       sta tmp                  ; first slot of this page
sd_star:
        ldy star_y,x
        lda hgr_lo,y
        clc
        adc star_col,x
        sta dst
        HI_LDA 0, y
        sta dst+1
        txa
        clc
        adc tmp
        tay
        lda (dst)
        beq sd_free
        lda #0                   ; occupied: not drawn
        sta star_hi,y
        bra sd_next
sd_free:
        lda star_val,x
        sta (dst)
        lda dst
        sta star_lo,y
        lda dst+1
        sta star_hi,y
sd_next:
        dex
        bpl sd_star
        rts

; ---------------------------------------------------------------------------
; Last: it patches every HI_LDA site above. A = page to draw (0/1).
select_page:
        sta page
        tax
        lda pg40_of,x
        sta pg40
        lda pg10_of,x
        sta pg10
        ldy #>hgr_hi
        cpx #0
        beq :+
        ldy #>hgr_hi2
:
.repeat HI_SITES, I
        sty .ident(.sprintf("hi_site%d", I)) + 2
.endrepeat
        rts
pg40_of: .byte 0, NALIENS
pg10_of: .byte 0, MAX_SHOTS
