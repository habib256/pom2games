; WARGALAGA II -- Apple //e enhanced / //c 128 KB, ProDOS 8, HGR double buffer.
; VERHILLE Arnaud -- GPL-3.0 (see LICENSE at repository root).
;
; The frame loop:
;   input -> logic steps (one per two refreshes elapsed, at most two)
;         -> draw the hidden page -> present it at the next deadline.
; logic.s holds the logic (tools/model.py is its bit-exact reference),
; render.s the drawing, which only rewrites what changed on a page since
; that page was last drawn (two frames ago).
.setcpu "65C02"
.macpack longbranch

.import _prodos_video_claim, _prodos_video_release
.import timing_init, timing_close, timing_present, _a2_vbl_scan
.import timing_refreshes, joy_x, joy_mode
.import __TRAMP_LOAD__, __TRAMP_RUN__, __TRAMP_SIZE__, __AUXM_LAST__
.export _main, _game_shutdown
; Test hooks (a2test reads them through build/game.lbl).
.export game_tick, frame_count, step_count, ship_c, shot_y, shot_c, star_y
.export star_col, move_dir, fire_req, logic_step, logic_done, quit, shot_limit
.export a_state, a_x, a_y, row_off, row_anim, prng_lo, render, render_done
.export a_timer, e_y, e_c, lives, armour, ship_state, invul_t, game_over, score, nohit
.export sound_frame, sound_done
.export msg_drawn, hud_seen, page, credits, fire_held, shot_dx, obj_y, obj_k, obj_kind
.export s_level, t_level, weapon, autofire_t, mult_t, shield_t, freeze_t, mult, auto_cnt
.export extra_bits, marks, mark_dark, subgame, pick_msg, pick_t
.export level, loop, phase, clear_t, level_t, lkind, bonus_kills, w_kills
.export dive_gap, max_divers, fire_gap, bomb_dy, kami_dy, start_level, cur_alien, pack_loaded
.export mus_ticks, shop, rank, noshop, shop_can, shop_buy, shop_exit, shop_screen, sh_cur
.import __SHOPM_LAST__, __LOWM_LAST__, __LOWHI_START__, __LOWHI_LAST__
.import __LOWBSS_RUN__, __LOWBSS_SIZE__, __AUXLV_START__, __AUXLV_LAST__
.import __LOW2_START__, __LOW2_LAST__, __AUXPK_LAST__
.export storm, station, m_speed, m_dist, m_acc, m_time, m_wait, m_crash, storm_step, storm_spawn
.export m_held, m_rel, m_end, storm_prize, storm_pct, st_draw, g_col, b_n
.export m_round, m_pairs, m_first, m_card, m_up, mem_screen, mem_loop, mem_deal, mem_turn
.export mem_sec, mem_cx, mem_cy, station_exit
.export mode, front_skip, front_run, front_main, fr_panel, fr_pos, fr_name, rec_buf, rec_state, rec_save, rec_err
.export demo, demo_input, demo_end, demo_script, over_wait
.import __DUET_LOAD__, __DUET_SIZE__
.export a_big, a_hp, cur_big, e_dx, boss_hp, boss_x, boss_dir, boss_boom, boss_gap, boss_t, boss_mv, hurry, h_x, h_dir, h_t, spk_period, audio_slot, sound_on, snd_ev
.export shots_erase, aliens_pass, form_draw, movers_draw, stars_draw, hud_draw
.export alien_sta, alien_sta_done, alien_eor, alien_eor_done, alien_clr, alien_clr_done

FIELD_TOP  = 8                  ; rows 0-7: HUD (lot 3)
FIELD_COL  = 4                  ; lot 10: walls of 4 bytes (14 cells) each side,
FIELD_CELLS = 140 - 2 * 14      ; the field between them, cell 0 at FIELD_COL
STAR_COLS  = 2 * FIELD_CELLS / 7 ; its byte columns
SHIP_Y     = 180                ; ship top row
SHIP_MAX   = FIELD_CELLS - 8    ; last cell of the ship: its 3rd byte stays
                                ; on byte 35 (at 105 it took the wall's 36)
SHIP_SPEED = 2                  ; cells (4 dots) per step: jauge S at start
MAX_SHOTS  = 10                 ; shot slots; shot_limit = jauge B
SHOT_LIMIT = 5                  ; jauge B at start
SHOT_DY    = 8
SHOT_Y0    = SHIP_Y - 6
NSTARS     = 16                 ; (24 until lot 6: ~1 100 cycles a frame back)

ROWS       = 5                  ; formation: 5 rows of 8
COLS       = 8
NALIENS    = ROWS * COLS
ALIEN_MAX  = FIELD_CELLS - 8    ; (3 bytes too: off the right wall)
FORM_X0    = 5                  ; cell of column 0 at sway 0
FORM_DX    = 12
ROW_SHIFT  = FORM_DX / 2        ; a staggered row (lot 10b)
DESIGN2    = 28                 ; the second species' first table entry
FORM_Y0    = 20
FORM_DY    = 14
SWAY_MAX   = 12
SWAY_EVERY = 3                  ; steps per row move (2 until lot 6: frame budget)
ST_DEAD    = 0                  ; alien states
ST_ENTER   = 1
ST_DIVE    = 2
ST_HOME    = 3
ST_FORM    = 4
ST_BOOM    = 5                  ; exploding (a_timer steps), then dead
BOOM_T     = 8
HOME_DX    = 2
HOME_DY    = 4
ENTRY_FIRST = 20                ; steps before the first pair
WAVE_GAP   = 60
LAUNCH_GAP = 6
DIVE_GAP   = 20
MAX_DIVERS = 6
OFF_TOP    = 240                ; row 240 = -16: above the screen
ESCAPE_Y   = 224                ; rows 192..223: out through the bottom
PATH_END   = $80
E_SHOTS    = 6                  ; enemy bombs
BOMB_DY    = 4
FIRE_GAP   = 12                 ; steps between two bomb attempts
FIRE_MAX_Y = 150                ; an alien lower than this does not fire
LIVES      = 3
DEATH_T    = 45                 ; steps from a hit to the respawn
RESPAWN_INVUL = 60
SHIELD_T   = 60                 ; after armour took a bomb
SHIP_HIT_X0 = 1                 ; cells of the ship that can be hit
SHIP_HIT_X1 = 5
SHIP_HIT_Y0 = SHIP_Y + 2
SHIP_HIT_Y1 = SHIP_Y + 9
OVER_WAIT  = 60                 ; frames of GAME OVER before fire counts
OVER_END   = 240                ; frames of GAME OVER: the title (lot 9)
HUD_KEYS   = 21                 ; bytes of state the HUD shows (render.s hud_keys)
HUD_N      = 128                ; HUD characters (tools/hud.py)
; Lot 5: falling objects, gauges, timed bonuses (tools/model.py).
N_OBJ      = 6
OBJ_DY     = 2
OBJ_H      = 13                 ; = ICON_H (tools/sprites.py)
DROP_RATE  = 40                 ; rand8 below: a kill drops something
S_MAX      = 5
B_MIN      = 5
B_MAX      = 10
T_MIN      = 3
T_MAX      = 9
AUTO_GAP   = 4                  ; autofire: a volley every 4 steps, held
EXTRA_ALL  = $1F
; Lot 6: levels (tools/model.py: level_kind, level_params).
ST_PASS    = 6                  ; flies past and escapes (bonus levels)
ST_KAMI    = 7                  ; dives at the ship (kamikaze levels)
ST_ROCK    = 8                  ; a Meteor Storm rock (lot 8)
MEM_CELLS  = 35                 ; Memory Station's largest grid (7 x 5)
LK_NORMAL  = 0
LK_BIG     = 1
LK_BONUS   = 2
LK_KAMI    = 3
LK_BOSS    = 4
HURRY_T    = 1800              ; steps before the hurry-up saucer (60 s)
HURRY_Y    = 10
HURRY_FIRE = 12
LEVELS     = 100
BIG_HP     = 2
BIG_CELLS  = 10                 ; box: cells x-2..x+7, rows y-8..y+7
BIG_H      = 16
BIG_HI     = FIELD_CELLS - 9    ; last cell of a big alien (box x-2.., 4 bytes)
BOSS_Y     = 24                 ; the boss (lot 10c): 24 cells x 28 rows,
BOSS_CORE0 = 9                  ; core 9..14, a cell every BOSS_STEP steps
BOSS_CORE1 = 14
BOSS_MAX_X = 80                  ; (cells 1..80: its STA margin, 9 bytes)
BOSS_X0    = BOSS_MAX_X / 2
BOSS_STEP  = 8
BOSS_AUX   = $AA00               ; its 7 shifts in WG2.AUX (tools/sprites.py)
BOSS_BOOM_T = 40
TELEPORT_T = 60
SEED       = $AD3C

KEY_ESC   = $1B
KEY_LEFT  = $08
KEY_RIGHT = $15
KEY_TAB   = $09

.zeropage
src:    .res 2
dst:    .res 2
ptr:    .res 2
col:    .res 1                  ; byte column of a sprite
page:   .res 1                  ; page being drawn: 0 = $2000, 1 = $4000
pg40:   .res 1                  ; page * NALIENS
pg10:   .res 1                  ; page * MAX_SHOTS
tmp:    .res 1
tmp2:   .res 1
cnt:    .res 1
r_row:  .res 1                  ; rectangle for the generic routines
r_col:  .res 1
r_w:    .res 1
r_h:    .res 1
prng_lo: .res 1                 ; dev/lib/math/random.asm state
prng_hi: .res 1

.segment "ROWS"                 ; page aligned (src/game.cfg)
hgr_lo:  .res 256
hgr_hi:  .res 256               ; page 1 row high bytes
hgr_hi2: .res 256               ; page 2: the same + $20

.bss
frame_count: .res 2
step_count:  .res 2
pairs:       .res 1             ; refreshes not yet turned into a step (0/1)
steps:       .res 1
quit:        .res 1
dir_key:     .res 1             ; last direction key: 0, 1 right, $FF left
move_dir:    .res 1
fire_req:    .res 1
button:      .res 1             ; open apple / button 0, previous state
; The game state from here to game_vars_end: zeroed by game_init.
game_vars:
ship_c:      .res 1
shot_limit:  .res 1
shot_y:      .res MAX_SHOTS     ; top row, 0 = free
shot_c:      .res MAX_SHOTS
star_y:      .res NSTARS
star_col:    .res NSTARS
; aliens
a_state:     .res NALIENS
a_x:         .res NALIENS       ; cell
a_y:         .res NALIENS       ; row (240-255: above the screen)
a_plo:       .res NALIENS       ; path pointer
a_phi:       .res NALIENS
a_mirror:    .res NALIENS
row_off:     .res ROWS          ; sway offset of each row
row_anim:    .res ROWS          ; animation frame of each row
entry_w:     .res 1             ; wave being launched (ROWS = done)
entry_k:     .res 1             ; pair in the wave
entry_t:     .res 1             ; steps to the next pair
form_off:    .res 1
form_dir:    .res 1             ; 1 or $FF
sway_row:    .res 1
sway_t:      .res 1             ; rows move on every other step
dive_t:      .res 1
a_timer:     .res NALIENS       ; explosion steps left
e_y:         .res E_SHOTS       ; bombs: top row, 0 = free
e_c:         .res E_SHOTS       ; cell
fire_t:      .res 1
lives:       .res 1
armour:      .res 1
ship_state:  .res 1             ; >0: exploding, steps to the respawn
invul_t:     .res 1             ; >0: nothing hurts the ship
game_over:   .res 1
score:       .res 3             ; BCD, low byte first
credits:     .res 2             ; BCD, 4 digits (coins)
fly_list:    .res NALIENS       ; visible flying aliens (this step)
shot_dx:     .res MAX_SHOTS     ; cells a step (triple weapon: -1 / +1)
obj_y:       .res N_OBJ         ; falling objects: top row, 0 = free
obj_k:       .res N_OBJ         ; column: cells 7k..7k+6, bytes 2k..2k+1
obj_kind:    .res N_OBJ
s_level:     .res 1             ; jauge S: speed = s_level + 1 cells
t_level:     .res 1             ; jauge T: timed bonuses last 10 * t s
weapon:      .res 1             ; 0 single, 1 double, 2 triple
autofire_t:  .res 2             ; timed bonuses, steps left
mult_t:      .res 2
shield_t:    .res 2
freeze_t:    .res 2
mult:        .res 1             ; score multiplier
lv_rec:      .res 14            ; the level's record (aux lv_recs, LV_REC)
row_sh:      .res ROWS          ; lot 10b: each row's stagger (cells)
row_base:    .res ROWS          ; and first table entry (0 or DESIGN2)
auto_cnt:    .res 1
extra_bits:  .res 1             ; letters E X T R A collected (bits 0-4)
marks:       .res 1             ; rank marks (lot 7)
mark_dark:   .res 1
pick_msg:    .res 1             ; what the last pickup did (model.PICK_TEXT)
pick_t:      .res 1             ; >0: named mid-field (render.s msg_draw)
shop:        .res 1             ; the shop is open (lot 7): logic waits
rank:        .res 1
perfects:    .res 1             ; bonus levels all shot (lot 10: GAME BONUSES)
subgame:     .res 1             ; sub-game icon caught: 1 meteor, 2 memory (lot 8)
pts_lo:      .res 1             ; add_points scratch
pts_hi:      .res 1
pts_top:     .res 1
fl_x0:       .res NALIENS       ; fly_list boxes: cells, rows
fl_x1:       .res NALIENS
fl_y0:       .res NALIENS
fl_y1:       .res NALIENS
level:       .res 1             ; 0..99
loop:        .res 1             ; times past level 100
phase:       .res 1             ; 0 playing, 1 teleporting to the next level
clear_t:     .res 1
level_t:     .res 2             ; steps into the level (hurry-up, lot 6)
lkind:       .res 1             ; LK_*
bonus_kills: .res 1
w_kills:     .res ROWS          ; kamikaze: kills per wave
dive_gap:    .res 1             ; this level's parameters (setup_level)
max_divers:  .res 1
fire_gap:    .res 1
bomb_dy:     .res 1
kami_dy:     .res 1
a_big:       .res NALIENS       ; big alien (level 3 of a pack)
a_hp:        .res NALIENS       ; hits left
e_dx:        .res E_SHOTS       ; bombs: cells a step sideways (the boss)
boss_hp:     .res 1             ; 0: no boss
boss_x:      .res 1
boss_dir:    .res 1             ; 1 or $FF
boss_boom:   .res 1             ; steps of its explosion left
boss_gap:    .res 1
boss_t:      .res 1
boss_mv:     .res 1             ; steps to the next leap
hurry:       .res 1             ; the hurry-up saucer is out
h_x:         .res 1
h_dir:       .res 1             ; 1 or $FF
h_t:         .res 1             ; steps to its next bomb
b_y:         .res 1             ; bomb arguments
b_c:         .res 1
b_dx:        .res 1
nfly:        .res 1
; Lot 8: the sub-games (tools/model.py).
storm:       .res 1             ; Meteor Storm on (storm.s)
station:     .res 1             ; Memory Station open: logic waits (memory.s)
m_speed:     .res 1             ; storm: 0..M_SPEED_MAX
m_dist:      .res 2             ; rows of field left
m_acc:       .res 1             ; rows since the last rock or coin
m_time:      .res 2             ; steps flown (the prize)
m_wait:      .res 1             ; steps of METEOR STORM before the rocks
m_crash:     .res 1             ; a rock hit: the end once the ship is out
m_held:      .res 2             ; steps flown with fire held (lot 11)
m_rel:       .res 1             ; fire let go once (no 101 %)
m_end:       .res 1             ; steps of the prize's name before the end
m_dy:        .res 1             ; this step's rows
m_round:     .res 1             ; station: grids cleared
m_pairs:     .res 1             ; pairs left
m_first:     .res 1             ; card turned first, MEM_NONE
m_miss:      .res 1             ; the first of a pair that missed
m_n:         .res 1             ; cards on the grid
m_card:      .res MEM_CELLS     ; kind of each card, row-major
m_up:        .res MEM_CELLS     ; face up
game_vars_end:
hi_score:    .res 3             ; HI (BCD): the best record, then the score
                                ; (not in game_vars: game_init would clear it)
over_wait:   .res 1             ; frames since GAME OVER
space_held:  .res 1
demo:        .res 1             ; the attract mode plays (demo.s, lot 9)
.data
pack_loaded: .byte $FF          ; WG2.AUX table in cur_alien ($FF: none)
.bss
aux_bitmap:  .res 4
aux_total:   .res 2
af_src:      .res 2             ; aux_fetch
af_dst:      .res 2
af_len:      .res 2
af_n:        .res 1
fire_held:   .res 1             ; input: fire held down (autofire)
nohit:       .res 1             ; tests: shots hit nothing (the bench)
noshop:      .res 1             ; tests: the shop closes at once
.data
start_level: .byte 0            ; tests and the pilot: the first level
front_skip:  .byte 0            ; tests: no title, the game at once (SEED)
mode:        .byte 0            ; model.MODES: $FF EASY, 0 NORMAL, 1 HARD, 2 ACE
                                ; (front.s: from HIGHSCORES; tests: NORMAL)
.bss

.rodata
.include "sprites.inc"           ; first: the sprite routines need the sizes
.assert ICON_H = OBJ_H, error, "OBJ_H: the icons' height (tools/sprites.py)"
.include "paths.inc"
.include "sound.inc"

.segment "IOBUF"
iobuf:       .res 1024          ; ProDOS file buffer (WG2.AUX, HIGHSCORES);
                                ; in a game (lot 10): the walls' tile, then
cur_alien2 = iobuf + WALL_TILE   ; the pack's second species (pack_check)
.assert WALL_TILE + ALIEN_TABLE <= 1024, error, "iobuf: the walls' tile and the second species"
.segment "LOWBSS"
cur_alien:   .res ALIEN_TABLE   ; the current pack's small alien (from aux)
cur_big:     .res BIG_TABLE     ; and its big one

.code
_main:
        lda $BF98                ; MACHID: bits 5-4 = 11 for 128 KB
        and #$30
        cmp #$30
        beq big
        ldx #msg_128k-messages
        jmp fail
big:    lda #1                   ; PD_VIDEO_DISCARD_RAM: aux memory is ours
        jsr _prodos_video_claim
        cmp #0
        beq claimed
        ldx #msg_ram-messages
        jmp fail
claimed:
        jsr aux_load             ; before HGR page 2 is cleared: its buffer
        jsr tramp_install
        jsr rows_init
        lda #$20
        jsr clear_page
        lda #$40
        jsr clear_page
        sta $C00C                ; 40 columns, no 80STORE: plain HGR
        sta $C000
        bit $C050
        bit $C052
        bit $C057
        bit $C054
        jsr game_init
        jsr render_init
        jsr sound_init           ; before the //c clock (Mockingboard 4c)
        jsr timing_init
        lda #1                   ; page 1 shown, page 2 drawn first
        jsr select_page
        lda #1
        sta steps
        lda front_skip
        bne game_tick
        lda #0                   ; the title first
        jsr front_run
        jcs done

game_tick:
        lda demo                 ; the demo: a key or a button stops it
        beq :+
        jsr demo_poll
        bra :++
:       jsr read_input
:       lda quit                 ; ESC: the title
        jne to_front
        lda game_over            ; GAME OVER: after a while, fire (or more
        beq playing              ; time) goes to the title; the demo's at once
        lda demo
        bne to_front
        lda over_wait
        cmp #OVER_END
        bcs to_front
        inc over_wait
        cmp #OVER_WAIT
        bcs :+
        stz fire_req
:       lda fire_req
        beq playing
        stz fire_req
to_front:
        stz quit
        lda demo                 ; a game (not the demo) ended: a record?
        eor #1
        jsr front_run
        bcs done
        jmp game_tick
playing:
        ldx steps
        beq render_frame
:       phx
        jsr logic_step
        plx
        dex
        bne :-
        lda shop                 ; the shop (lot 7) or Memory Station (lot 8)
        ora station
        beq render_frame
        jsr shop_run
render_frame:
        jsr pack_check
        jsr render
        lda page
        jsr timing_present
        jsr sound_frame
sound_done:
        inc frame_count
        bne :+
        inc frame_count+1
:       lda timing_refreshes     ; one logic step per two refreshes
        clc
        adc pairs
        tax
        and #1
        sta pairs
        txa
        lsr
        cmp #3
        bcc :+
        lda #2                   ; at most one step of catch-up
:       sta steps
        lda page
        eor #1
        jsr select_page
        jmp game_tick
done:   rts

; WG2.AUX -> aux memory at AUX_BASE (every small and big alien design x
; tint), 8 KB at a time through HGR page 2 (not shown yet). A failure: a
; message, back to ProDOS.
STORM_AUX = $B100               ; lot 11: the small and big rocks,
LOW2_AUX = $B900                ; (the pickup texts at $B600: game.cfg AUXPK)
LOW2_LEN = __LOW2_LAST__ - __LOW2_START__
AUX_ALL = LOW2_AUX + $200 - AUX_BASE
.assert BOSS_AUX + 7 * BOSS_SHIFT <= STORM_AUX, error, "the boss runs into the rocks"
.assert STORM_AUX + ALIEN_TABLE + BIG_TABLE <= PICK_AUX, error, "the rocks run into the texts"
.assert __AUXPK_LAST__ <= LOW2_AUX, error, "the texts run into LOW2"
.assert LOW2_LEN <= $200, error, "LOW2: WG2.AUX keeps $200 for it"
.assert WALL_AUX + 4 * WALL_TILE <= BOSS_AUX, error, "the walls run into the boss"
.assert LV_LEN <= $0600, error, "the level records run into the walls"
.assert HI_LEN <= $0400, error, "the resident data runs into the level records"
.assert LOW_LEN <= $0800, error, "the storm runs into the resident data"
.assert __LOWBSS_RUN__ + __LOWBSS_SIZE__ <= __LOWHI_START__, error, "LOWBSS runs into LOWHI"
.assert __AUXM_LAST__ <= SHOP_AUX, error, "the PT3 player runs into the shop"
.assert SHOP_AUX + OVL_LEN <= LOW_AUX, error, "the overlay runs into the storm"

.assert AUX_BASE + AUX_SIZE <= $6000, error, "the packs run into the PT3 player"
aux_load:
        jsr $BF00
        .byte $C8                ; OPEN
        .word aux_open
        jcs aux_fail
        lda aux_open+5
        sta aux_read+1
        sta aux_close+1
        stz aux_total
        stz aux_total+1
al_chunk:
        ldx #3                   ; READ writes only where the system bitmap
:       lda $BF60,x              ; says free: $4000-$5FFF for the read
        sta aux_bitmap,x         ; (crt0 marks it used; as CHROMABREAK)
        stz $BF60,x
        dex
        bpl :-
        jsr $BF00
        .byte $CA                ; READ
        .word aux_read
        tay                      ; (the error code; $4C = end of file)
        ldx #3
:       lda aux_bitmap,x
        sta $BF60,x
        dex
        bpl :-
        bcc :+
        cpy #$4C
        bne al_close             ; an error (C = 1)
        bra al_end
:       lda aux_read+6           ; got: main $4000.. -> aux ($42/$43 goes on)
        ora aux_read+7
        beq al_end
        ; Reject an oversized file BEFORE AUXMOVE can write past its
        ; reserved auxiliary range. aux_total is bounded by every chunk.
        lda aux_total
        clc
        adc aux_read+6
        tax
        lda aux_total+1
        adc aux_read+7
        bcs al_too_long
        cmp #>AUX_ALL
        bcc al_copy
        bne al_too_long
        cpx #<AUX_ALL
        bcc al_copy
        beq al_copy
al_too_long:
        sec
        bra al_close
al_copy:
        lda #<$4000
        sta $3C
        lda #>$4000
        sta $3D
        lda aux_read+6
        sec
        sbc #1
        sta $3E
        lda aux_read+7
        sbc #0
        clc
        adc #>$4000
        sta $3F
        lda aux_total            ; to AUX_BASE + what came before
        clc
        adc #<AUX_BASE
        sta $42
        lda aux_total+1
        adc #>AUX_BASE
        sta $43
        sec                      ; main -> aux
        jsr $C311                ; AUXMOVE
        lda aux_total
        clc
        adc aux_read+6
        sta aux_total
        lda aux_total+1
        adc aux_read+7
        sta aux_total+1
        lda aux_read+7           ; a full 8 KB: maybe more
        cmp #$20
        jeq al_chunk
al_end: clc
al_close:
        php
        jsr $BF00
        .byte $CC                ; CLOSE
        .word aux_close
        plp
        bcs aux_fail
        lda aux_total            ; the whole file? (the packs, padding, then
        cmp #<AUX_ALL            ; the PT3 player and song at aux $6000)
        bne aux_fail
        lda aux_total+1
        cmp #>AUX_ALL
        bne aux_fail
        lda #<LOW_AUX            ; Meteor Storm's code -> $0800, for good
        sta $3C                  ; (no interrupt yet: one AUXMOVE)
        lda #>LOW_AUX
        sta $3D
        lda #<(LOW_AUX+LOW_LEN-1)
        sta $3E
        lda #>(LOW_AUX+LOW_LEN-1)
        sta $3F
        lda #<$0800
        sta $42
        lda #>$0800
        sta $43
        clc                      ; aux -> main
        jsr $C311                ; AUXMOVE
        jsr low_boot             ; and $0200's (lot 11)
        lda #<HI_AUX             ; the resident data -> $1C40, for good
        sta $3C
        lda #>HI_AUX
        sta $3D
        lda #<(HI_AUX+HI_LEN-1)
        sta $3E
        lda #>(HI_AUX+HI_LEN-1)
        sta $3F
        lda #<__LOWHI_START__
        sta $42
        lda #>__LOWHI_START__
        sta $43
        clc
        jmp $C311
aux_fail:
        pla                      ; (out of _main)
        pla
        ldx #msg_aux-messages
        jmp fail

; The level's pack table aux -> cur_alien, when it changed (between two
; levels: no alien of the old pack is drawn any more).
pack_check:
        ldx level
        lda lv_combo,x
        ldy storm                ; Meteor Storm: the rock (lot 8)
        beq :+
        lda #NCOMBOS
:       ldy lkind                ; a boss level: + $40, so that the next
        cpy #LK_BOSS             ; level (the same pack) loads again what
        bne :+                   ; the boss's shifts overwrite (lot 10c)
        ora #$40
:       cmp pack_loaded
        jeq boss_check
        tay
        eor pack_loaded          ; only the boss's mark changed: cur_alien is
        cmp #$40                 ; still good (the boss used iobuf, cur_big)
        sty pack_loaded
        stz boss_loaded
        php
        tya
        and #$3F
        tax
        plp
        beq pc_second
        lda combo_lo,x
        ldy combo_hi,x
        ldx #<cur_alien
        stx af_dst
        ldx #>cur_alien
        stx af_dst+1
        ldx #<ALIEN_TABLE
        stx af_len
        ldx #>ALIEN_TABLE
        stx af_len+1
        jsr aux_fetch
pc_second:
        lda storm                ; (the rocks: storm.s)
        jne storm_fetch
        lda pack_loaded          ; (a boss level: its escorts alone)
        cmp #$40
        jcs boss_check
        tax                      ; lot 10b: the pack's second species
        lda combo2_of,x
        tax
        lda combo_lo,x
        ldy combo_hi,x
        ldx #<cur_alien2
        stx af_dst
        ldx #>cur_alien2
        stx af_dst+1
        ldx #<ALIEN_TABLE
        stx af_len
        ldx #>ALIEN_TABLE
        stx af_len+1
        jsr aux_fetch
        ldx level                ; and the pack's big alien
        lda lv_big,x
        tax
        lda big_aux_lo,x
        ldy big_aux_hi,x
        ldx #<cur_big
        stx af_dst
        ldx #>cur_big
        stx af_dst+1
        ldx #<BIG_TABLE
        stx af_len
        ldx #>BIG_TABLE
        stx af_len+1
        ; fall through
; Aux (A lo, Y hi) -> main af_dst, af_len bytes, through AUXMOVE: AF_CHUNK
; bytes at a time, IRQs off only while the bank is switched (the music
; interrupt), a VBL scan between two. (One AUXMOVE of the 1 232 bytes
; under SEI held the interrupts and the scans off for ~50 000 cycles: a
; music tick and //e VBL edges lost at every pack change, bug hunt 5.)
AF_CHUNK = 64                    ; ~2 300 cycles each
aux_fetch:
        sta af_src
        sty af_src+1
af_chunk:
        lda af_len+1
        bne :+
        lda af_len
        beq pc_done
        cmp #AF_CHUNK
        bcc :++
:       lda #AF_CHUNK
:       sta af_n
        lda af_src               ; A1 = src, A2 = src + n - 1, A4 = dst
        sta $3C
        clc
        adc af_n
        sta af_src
        lda af_src+1
        sta $3D
        adc #0
        sta af_src+1
        lda af_src
        sec
        sbc #1
        sta $3E
        lda af_src+1
        sbc #0
        sta $3F
        lda af_dst
        sta $42
        clc
        adc af_n
        sta af_dst
        lda af_dst+1
        sta $43
        adc #0
        sta af_dst+1
        lda af_len
        sec
        sbc af_n
        sta af_len
        bcs :+
        dec af_len+1
:       php
        sei
        clc                      ; aux -> main
        jsr $C311                ; AUXMOVE
        plp
        jsr _a2_vbl_scan
        bra af_chunk
pc_done:
        rts

; The shop or Memory Station: page 1 shown and cleared, the overlay aux ->
; page 2 ($4000; up to its speaker player: not the title's part), the
; screen, then the rules on leaving (logic.s); Memory Station may lead to
; the shop. Then a fresh game screen.
SHOP_AUX = $7000                 ; (WG2.AUX: packs, PT3 at $6000, the
SHOP_LEN = __DUET_LOAD__ + __DUET_SIZE__ - $4000 ; overlay, storm and demo
OVL_LEN  = __SHOPM_LAST__ - $4000 ; at $9000)
LOW_AUX  = $9000
LOW_LEN  = __LOWM_LAST__ - $0800
HI_AUX   = $9800
HI_LEN   = __LOWHI_LAST__ - __LOWHI_START__
LV_AUX   = __AUXLV_START__
LV_LEN   = __AUXLV_LAST__ - __AUXLV_START__
WALL_AUX = $A200                 ; the walls' textures (tools/walls.py)
WALL_TILE = 512                  ; WALL_H rows of 8 bytes, one a quarter
WALL_H   = 64
shop_run:
        ldx #<SHOP_LEN
        ldy #>SHOP_LEN
        jsr ovl_load
sr_screen:
        lda station
        beq :+
        jsr mem_screen
        jsr station_exit         ; (maybe the shop next)
        bra :++
:       jsr shop_screen
        jsr shop_exit
:       lda shop
        ora station
        beq :+
        lda #$20
        jsr clear_page
        bra sr_screen
:       lda #$20
        jsr clear_page
        lda #$40
        jsr clear_page
        jsr render_init
        lda page
        jmp select_page

; Page 1 cleared and shown, X (lo) Y (hi) bytes of the overlay aux -> $4000.
ovl_load:
        stx af_len
        sty af_len+1
        lda #$20
        jsr clear_page
        bit $C054
        lda #<$4000
        sta af_dst
        lda #>$4000
        sta af_dst+1
        lda #<SHOP_AUX
        ldy #>SHOP_AUX
        jmp aux_fetch

; The title screen (front.s, in the overlay); A = 1: a game just ended (a
; record?). Then a new game, or the demo: level 1, SEED, its script (demo.s),
; the shop and the station closed at once. C = 1: ESC, back to ProDOS.
front_run:
        pha
        ldx #<OVL_LEN
        ldy #>OVL_LEN
        jsr ovl_load
        pla
        jsr front_main
        pha
        ldx #2                   ; HI: the best record (entry 0's score)
:       lda rec_buf+6,x
        sta hi_score,x
        dex
        bpl :-
        pla
        cmp #$FF
        beq fr_exit
        sta demo
        sta noshop
        jsr new_game
        lda demo
        beq :+
        lda #<SEED
        sta prng_lo
        lda #>SEED
        sta prng_hi
        jsr demo_init
:       lda #1                   ; page 1 shown, page 2 drawn first
        jsr select_page
        clc
        rts
fr_exit:
        sec
        rts

; Clean screens and records, fresh state.
new_game:
        lda #$20
        jsr clear_page
        lda #$40
        jsr clear_page
        jsr game_init
        jsr joy_calib
        lda #$FF
        sta pack_loaded
        lda frame_count          ; a new seed: the time the player took
        sta prng_lo              ; (the first game keeps SEED: the tests)
        lda frame_count+1
        ora #$01                 ; never 0/0
        sta prng_hi
        jmp render_init

; Text message (X = offset in messages), a key, then back to ProDOS.
fail:   lda messages,x
        beq :+
        ora #$80
        jsr $FDED
        inx
        bne fail
:       bit $C000
        bpl :-
        bit $C010
        rts

; From the crt0 cleanup (ESC, Ctrl-RESET): clock off, text, /RAM rebuilt.
_game_shutdown:
        jsr sound_shutdown
        jsr timing_close
        bit $C051
        bit $C054
        jmp _prodos_video_release

; Fill the 8 KB page at A (high byte) with zeros.
clear_page:
        sta dst+1
        stz dst
        ldx #$20
        lda #0
        tay
:       sta (dst),y
        iny
        bne :-
        inc dst+1
        dex
        bne :-
        rts

; Zero X pages then Y bytes from dst, exactly: a block rounded up to whole
; pages wiped the timing, library and crt0 (saved zero page) variables after
; render_vars (bug hunt 2026-10-23). Clobbers A, X, Y, tmp, dst.
zero_block:
        sty tmp
        ldy #0
        tya
        cpx #0
        beq zb_rest
zb_page:
        sta (dst),y
        iny
        bne zb_page
        inc dst+1
        dex
        bne zb_page
zb_rest:
        ldy tmp
        beq zb_done
zb_byte:
        dey
        sta (dst),y
        bne zb_byte
zb_done:
        rts

; Row address tables: lo = (y/8 mod 2)*$80 + (y/64)*$28, hi = $20 +
; (y mod 8)*4 + (y/8 mod 8)/2; page 2 = hi + $20.
rows_init:
        ldx #0
:       txa
        and #7
        asl
        asl
        ora #$20
        sta hgr_hi,x
        txa
        lsr
        lsr
        lsr
        tay                      ; y/8
        and #7
        lsr                      ; C = (y/8) & 1
        ora hgr_hi,x
        sta hgr_hi,x
        lda #0
        ror
        sta hgr_lo,x
        tya
        lsr
        lsr
        lsr
        tay                      ; y/64
        lda hgr_lo,x
        clc
        adc thirds,y
        sta hgr_lo,x
        lda hgr_hi,x
        clc
        adc #$20
        sta hgr_hi2,x
        inx
        cpx #192
        bne :-
        rts
thirds: .byte $00, $28, $50

game_init:
        lda #<game_vars          ; zero the game state
        sta dst
        lda #>game_vars
        sta dst+1
        ldx #>(game_vars_end-game_vars)
        ldy #<(game_vars_end-game_vars)
        jsr zero_block
        stz over_wait
        lda #(SHIP_MAX/2)
        sta ship_c
        lda #SHOT_LIMIT
        sta shot_limit
        ldx #NSTARS-1
:       lda star_y0,x
        sta star_y,x
        lda star_col0,x
        sta star_col,x
        dex
        bpl :-
        lda #<SEED
        sta prng_lo
        lda #>SEED
        sta prng_hi
        lda #1
        sta form_dir
        lda start_level
        sta level
        jsr setup_level
        lda #LIVES
        sta lives
        lda #1
        sta s_level
        sta mult
        lda #T_MIN
        sta t_level
        rts

; ---------------------------------------------------------------------------
; Input, once per frame. Keyboard: a new key sets the direction or asks for
; a shot; the direction holds while any key is down ($C010 bit 7), so a
; shot fired with SPACE does not stop the ship. Open apple / button 0 fires
; on press. TAB switches keyboard / joystick (as J on the title).
read_input:
        lda $C000
        bpl no_key
        bit $C010
        and #$7F
        cmp #'a'
        bcc :+
        and #$DF                 ; upper case
:       cmp #KEY_ESC
        bne :+
        sta quit
        rts
:       stz space_held           ; another key: SPACE is no longer down
        cmp #KEY_LEFT
        beq left
        cmp #'J'
        beq left
        cmp #KEY_RIGHT
        beq right
        cmp #'L'
        beq right
        cmp #' '
        beq space
        cmp #'S'
        bne :+
        jsr sound_toggle
        bra buttons
:       cmp #KEY_TAB
        bne buttons
        lda joy_mode
        eor #1
        sta joy_mode
        jsr joy_calib
        bra buttons
left:   lda #$FF
        bra :+
right:  lda #1
:       sta dir_key
        bra buttons
space:  sta fire_req
        sta space_held
        bra buttons
no_key: bit $C010                ; any key still down?
        bmi buttons
        stz dir_key
        stz space_held
buttons:
        lda $C061
        and #$80
        tax
        eor button
        and $C061                ; newly pressed
        bpl :+
        sta fire_req
:       stx button
        txa                      ; fire held (autofire): open apple / button
        ora space_held           ; 0, or SPACE still down
        sta fire_held
        lda joy_mode
        beq keyboard
        lda #$FF                 ; stick: left / dead zone / right
        ldx joy_x                ; (0..165 count, timing.s)
        cpx joy_lo
        bcc :+
        lda #1
        cpx joy_hi
        bcs :+
        lda #0
:       sta move_dir
        rts
keyboard:
        lda dir_key
        sta move_dir
        rts

; The stick's centre is where it rests at the start of a game (or TAB): a
; ROM read (11 cycles a count, x 5/8 = the 17 of timing.s), kept 50..115,
; then JOY_DEAD each side moves nothing (2026-10-30: a stick off centre
; drifted with fixed thirds). In LOW2 (main RAM is full).
JOY_DEAD = 40
.pushseg
.segment "STORM2"
joy_calib:
        ldx #0
        jsr $FB1E                ; PREAD: Y = 0..255
        tya
        lsr
        lsr
        lsr
        sta joy_lo
        tya
        lsr
        adc joy_lo
        cmp #50
        bcs :+
        lda #50
:       cmp #116
        bcc :+
        lda #115
:       sec
        sbc #JOY_DEAD
        sta joy_lo
        adc #2*JOY_DEAD-1        ; (carry set)
        sta joy_hi
        rts
joy_lo: .byte 83-JOY_DEAD
joy_hi: .byte 83+JOY_DEAD
.popseg

.include "logic.s"
.include "render.s"
.include "sound.s"

.rodata
messages:
msg_128k: .byte "WARGALAGA II NEEDS 128K.", $0D, 0
msg_ram:  .byte "INVALID PRODOS STATE (/RAM).", $0D, 0
msg_aux:  .byte "WG2.AUX: LOAD ERROR.", $0D, 0
aux_open:  .byte 3
        .word aux_name, iobuf
        .byte 0
aux_read:  .byte 4, 0
        .word $4000, $2000, 0
aux_close: .byte 1, 0
aux_name:  .byte 7, "WG2.AUX"
; The boss's 7 shifts (lot 10c): aux BOSS_AUX -> iobuf (0-3) and cur_big
; (4-6), on a boss level, once (pack_check and render_init forget them:
; their loads and the walls' tile overwrite them).
boss_check:
        lda lkind
        cmp #LK_BOSS
        bne bc_done
        lda boss_loaded
        bne bc_done
        inc boss_loaded
        lda #<iobuf
        sta af_dst
        lda #>iobuf
        sta af_dst+1
        lda #<(4 * BOSS_SHIFT)
        sta af_len
        lda #>(4 * BOSS_SHIFT)
        sta af_len+1
        lda #<BOSS_AUX
        ldy #>BOSS_AUX
        jsr aux_fetch
        lda #<cur_big
        sta af_dst
        lda #>cur_big
        sta af_dst+1
        lda #<(3 * BOSS_SHIFT)
        sta af_len
        lda #>(3 * BOSS_SHIFT)
        sta af_len+1
        lda #<(BOSS_AUX + 4 * BOSS_SHIFT)
        ldy #>(BOSS_AUX + 4 * BOSS_SHIFT)
        jmp aux_fetch
bc_done:
        rts

; The second species of a pack (model.alien_combo2): design + 2, tint + 2.
combo2_of:
.repeat NCOMBOS, I
        .byte (I / 4 + 2) .mod 6 * 4 + (I .mod 4 + 2) .mod 4
.endrepeat
; WG2.AUX tables: aux address of each design x tint.
combo_lo:
.repeat NCOMBOS, I
        .byte <(AUX_BASE + ALIEN_TABLE * I)
.endrepeat
        .byte <AUX_ROCK          ; NCOMBOS: the Meteor Storm rock
combo_hi:
.repeat NCOMBOS, I
        .byte >(AUX_BASE + ALIEN_TABLE * I)
.endrepeat
        .byte >AUX_ROCK
big_aux_lo:
.repeat NBIG, I
        .byte <(AUX_BIG + BIG_TABLE * I)
.endrepeat
big_aux_hi:
.repeat NBIG, I
        .byte >(AUX_BIG + BIG_TABLE * I)
.endrepeat
; Stars: start row, byte column, dot (one dot: violet/green, blue/orange),
; speed 1..3 rows a step.
star_y0:
.repeat NSTARS, I
        .byte FIELD_TOP + (I * 97 + 13) .mod (192 - FIELD_TOP)
.endrepeat
star_col0:
.repeat NSTARS, I
        .byte (I * 23 + 5) .mod STAR_COLS
.endrepeat
star_val:
.repeat NSTARS, I
        .byte (1 << ((I * 3) .mod 7)) | ((I .mod 2) << 7)
.endrepeat
star_speed:
.repeat NSTARS, I
        .byte 1 + I .mod 3
.endrepeat
; Formation geometry: cell of column j at sway 0, row of each alien, its
; slot row; the formation row each screen row belongs to ($FF: none).
slot_dx:
.repeat COLS, J
        .byte FORM_X0 + FORM_DX * J
.endrepeat
alien_row:
.repeat NALIENS, I
        .byte I / COLS
.endrepeat
form_y:
.repeat ROWS, R
        .byte FORM_Y0 + FORM_DY * R
.endrepeat
frow:
.repeat 256, L
.if L >= FORM_Y0 && L < FORM_Y0 + ROWS * FORM_DY
        .byte (L - FORM_Y0) / FORM_DY
.else
        .byte $FF
.endif
.endrepeat
; Font: Beautiful Boot $20-$5F, then the HUD's own glyphs ($60-$63), so
; that glyph C is at bbfont + (C - $20) * 8 for all of them.
BBFONT_FIRST = $20
BBFONT_LAST  = $5F
.include "bbfont.inc"
GLYPH_SHIP  = $60
GLYPH_SHIELD = $61
GLYPH_FULL  = $62
GLYPH_EMPTY = $63
GLYPH_BAR2  = $64               ; the walls' bars (lot 10): two half segments,
GLYPH_BAR1  = $65               ; the left one, none (tools/hud.py)
GLYPH_BAR0  = $66
        .byte $08,$08,$1C,$3E,$7F,$5D,$14,$00   ; ship (lives)
        .byte $1C,$22,$41,$49,$41,$22,$1C,$00   ; shield (armour)
        .byte $00,$3E,$3E,$3E,$3E,$3E,$00,$00   ; bar segment, full
        .byte $00,$3E,$22,$22,$22,$3E,$00,$00   ; bar segment, empty
        .byte $00,$77,$77,$77,$77,$77,$00,$00   ; two half segments
        .byte $00,$07,$07,$07,$07,$77,$00,$00   ; the left one (dot pairs:
        .byte $00,$00,$00,$00,$00,$77,$00,$00   ; none           white)
.assert * = bbfont + ($67 - $20) * 8, error, "HUD glyphs follow bbfont"
; HUD (lot 10: row 0 and the walls): tools/hud.py.
.include "hud.inc"
msg_over: .byte " GAME OVER  "
extra_letters: .byte "EXTRA"
; Lot 5 tables. A kill's drop: drop_table[rand & 63] (weights: model.py).
.include "bonus.inc"
.assert LV_REC = 14, error, "lv_rec: 14 bytes a level record"
col_bit: .byte 1, 2, 4, 8, 16, 32, 64, 128
; Kamikaze prizes, BCD 2000 << wave (bytes 2 and 3; byte 1 is 0).
kami_hi:  .byte $20, $40, $80, $60, $20
kami_top: .byte $00, $00, $00, $01, $03
; Alien states that fly on their own: enter, dive, home, pass, kamikaze,
; rock.
is_flying: .byte 0, 1, 1, 1, 0, 0, 1, 1, 1
; Weapons: volleys of (cell offset, dx) (single, double, triple).
wpn_first: .byte 0, 1, 3
wpn_count: .byte 1, 2, 3
wpn_cell:  .byte 3,  1, 5,  3, 1, 5
wpn_dx:    .byte 0,  0, 0,  0, $FF, 1
k7:
.repeat 20, L
        .byte 7 * L
.endrepeat
div7:
.repeat 140, L
        .byte L / 7
.endrepeat
; Timed bonuses: 300 steps a T level (10 s at 30 steps a second).
dur_lo:
.repeat 10, L
        .byte <(300 * L)
.endrepeat
dur_hi:
.repeat 10, L
        .byte >(300 * L)
.endrepeat

; Collision tables. shot_frow: the formation row a shot whose top is at
; this row can touch (its rows y..y+5 meet the alien rows), $FF none.
; col_of: cell offset from column 0 -> column, $FF in the gap.
SHOT_BAND0 = FORM_Y0 - SHOT_H + 1
shot_frow:
.repeat 256, L
  .if L >= SHOT_BAND0 && (L - SHOT_BAND0) .mod FORM_DY < SHOT_H + ALIEN_H - 1 && (L - SHOT_BAND0) / FORM_DY < ROWS
        .byte (L - SHOT_BAND0) / FORM_DY
  .else
        .byte $FF
  .endif
.endrepeat
col_of:
.repeat COLS * FORM_DX, L
  .if L .mod FORM_DX < ALIEN_CELLS
        .byte L / FORM_DX
  .else
        .byte $FF
  .endif
.endrepeat

.code
.include "random.asm"
MB_FAST_WRITE = 1                ; ~55 cycles an AY write instead of ~110
.include "mockingboard.asm"

.include "shop.s"
.include "storm.s"
.include "demo.s"
