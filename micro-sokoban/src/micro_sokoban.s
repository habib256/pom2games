; =============================================================================
; MICRO-SOKOBAN — Apple II+ / DOS 3.3 port (HGR, keyboard + joystick)
; VERHILLE Arnaud - 2026            Original: HGR_Sokoban.asm (POM1, GEN2 card)
; Licence: GPL v3 (same as the upstream sketch)
; =============================================================================
; Assemble with cc65:   make          (see ../Makefile)
; Resident at $6000; the DOS bootstrap at $0800 loads/decompresses MICRODATA.
;
; Controls
;   Joystick  : stick = move (auto-repeats while held)
;               button 0 tapped = undo; button 0 held + stick left/right =
;               undo / redo (auto-repeat)
;               button 1 = menu
;   Keyboard  : I J K L or W A S D or arrows = move
;               U undo    Y redo    R restart (undoable: Y replays)
;               N next    P previous
;               ESC = menu   H = help    RETURN/SPACE = select in menu
;               in the menu: T tutorial, O options, F Hall of Fame, V profiles,
;               G level grid, C deadlock warning, Q quit to DOS
;               Ctrl-RESET also quits cleanly
;
; Playfield: 20 cols x 12 rows of 14x16 pixel tiles.
; Delta rendering: a move only redraws the 2-3 affected tiles, on the page
; on screen. Whole screens (level, title, help, success) are drawn on the
; hidden HGR page and shown with one page flip.
; HUD: 7-pixel glyphs in the four screen corners, 3 tiles each (moves top
; left, pushes top right, levels bottom left); levels keep those cells empty.
; Levels: Microban (David W. Skinner) -- every level that fits the screen,
; converted by tools/micro_sokoban_levels.py into packs of at most 2 KB (MB1A,
; MB1B, ...) read with RWTS (fast_disk.inc) into LOWBSS when play crosses into
; another pack. A
; level is (collection, index); the HUD shows the collection and the level's
; original number.
;
; History: every move is one byte (direction + "pushed a box") in a
; 1024-move ring. Undo walks it back, redo forward; restart (R)
; rewinds the whole level through it, so R can be redone with Y. Past 1024
; moves the oldest are forgotten, and R then reloads the level instead.
;
; Apple II+ specifics vs the Apple-1/GEN2 original:
;   - no V-blank signal on a II+ ($C019 is a //e thing) -> draws are immediate
;   - ../dev layout: code+data at $6000 above both HGR pages, the level pack
;     in LOWBSS ($1000), zero page at $50 (saved at start, restored on quit)
;   - the game port replaces the Apple-1 text-screen echo
; =============================================================================

.include "apple2.inc"            ; ../dev/lib/apple2: I/O equates, preamble
.include "levels.inc"            ; generated: collections, packs, numbers
.import __BSS_RUN__, __BOOTCODE_SIZE__

PAGE2_EOR = $60                 ; hgr_hi of page 1 ($20-$3F) EOR this = page 2

; --- Game constants ---
NCOLS      = 20
NROWS      = 12
STATE_GRID_LEN = 240
HIST_LEN   = 1024               ; moves kept for undo / redo (a power of two)

; --- Tile types ---
TILE_FLOOR         = 0
TILE_WALL          = 1
TILE_TARGET        = 2
TILE_BOX           = 3
TILE_BOX_TARGET    = 4
TILE_PLAYER        = 5
TILE_PLAYER_TARGET = 6
TILE_BOX_COLOR     = 7          ; how draw_tile shows BOX_TARGET in COLOR MODE

; --- Directions (history codes, bits 0-1; bit 2 = pushed a box) ---
DIR_UP     = 0
DIR_DOWN   = 1
DIR_LEFT   = 2
DIR_RIGHT  = 3
HIST_PUSH  = 4

; --- Input actions (get_input return codes) ---
ACT_NONE    = 0
ACT_UP      = 1
ACT_DOWN    = 2
ACT_LEFT    = 3
ACT_RIGHT   = 4
ACT_UNDO    = 5         ; U key / button 0
ACT_RESET   = 6         ; R key
ACT_NEXT    = 7         ; N key
ACT_PREV    = 8         ; P key
ACT_MENU    = 9         ; ESC key / button 1
ACT_SELECT  = 10        ; RETURN / SPACE
ACT_QUIT    = 11        ; Q key (acted on in the menu only)
ACT_REDO    = 12        ; Y key / button 0 held + stick right
ACT_DEADWARN = 13        ; C key (acted on in the menu only)
ACT_GOTO    = 14        ; G key: level selection
ACT_OTHER   = 15        ; any other key
ACT_OPTIONS = 17        ; O key in the help menu
ACT_TUTORIAL = 18       ; T key in the help menu
ACT_PROFILE = 19        ; V chooses a player profile
ACT_HELP    = 20        ; H opens HELP directly
ACT_HOF     = 16        ; F key in the help menu
ACT_SOLUTION = 21       ; X in the menu, only while cheat mode is on

; --- Joystick tuning ---
; read_stick (joy.asm) counts 24-cycle iterations while each paddle timer is
; charging: PDL 0 -> 0, PDL 127 (centered) -> ~60, PDL 255 -> ~120. JOY_LO /
; JOY_HI set the dead zone of stick_dir (joy.asm), defined here first.
JOY_LO     = 30         ; count below this  = left / up
JOY_HI     = 90         ; count above this  = right / down
JOY_REPEAT = 32         ; get_input calls (~6 ms each) between auto-repeats

; --- Menu entries: a compact block below the help controls ---
MENU_RESUME  = 0
MENU_BACK    = 255
MENU_TUTORIAL = 1
MENU_PROFILE = 2
MENU_RESET   = 3
MENU_GOTO    = 4
MENU_OPTIONS = 5
MENU_HOF     = 6
MENU_HELP    = 7
MENU_QUIT    = 8
MENU_SOLUTION = 9       ; drawn and reachable only while cheat mode is on
MENU_SL0     = 48       ; single menu below its heading and active profile
MENU_DY      = 12
MENU_CURSOR_COL = 64    ; pixel column of the compact green selection marker
MENU_TEXT_COL   = 84    ; pixel column of the compact entry labels
MENU_KEY_COL    = 208   ; aligned keyboard shortcuts

; --- HUD: 7-pixel glyphs, 8 lines centred in the top / bottom tile rows ---
HUD_TOP_SL = 4
HUD_BOT_SL = 11 * 16 + 4
HUD_LEFT   = 0          ; byte columns: 6 glyphs = 3 tiles per corner, 8 = 4
                        ; bottom left ("III:056", see micro_sokoban_levels.py)
HUD_RIGHT  = 34

; --- Save file MICROSAVE: "SOK2", collection and level last solved, one
; fingerprint per collection (coll_fp_lo/hi), then 4 bytes per level (best
; moves, best pushes; 0 = unsolved): SAVE_HDR + 4 * TOTAL_LEVELS = SAVE_LEN
; bytes, both from levels.inc. Records are kept by rank in the kept levels,
; so a collection whose levels changed (fingerprint) loses its records
; instead of passing them to other levels.
SAVE_FP    = 6          ; offset of the fingerprints in the file
HOF_COUNT  = 10
HOF_ENTRY  = 8          ; three ASCII initials, u24 score, u16 solved
HOF_HDR    = 7          ; "HOF1", then current initials
HOF_END    = HOF_HDR + HOF_COUNT * HOF_ENTRY
HOF_TUTORIAL = HOF_END
HOF_SOUND  = HOF_END+1  ; the OPT_* switches
OPT_GAME   = 1          ; game sounds
OPT_MENU   = 2          ; menu sounds and title music
OPT_DEMO   = 4          ; demo sounds
OPT_CHEAT  = 8          ; SOLUTION in the menu
OPT_COLOR  = 16         ; filled green boxes on targets (colour displays)
HOF_PROFILES = HOF_END+2 ; stable slots, three initials each; zero = unused
HOF_ACTIVE = HOF_PROFILES+30
HOF_LEN    = HOF_ACTIVE+1

; --- Title-screen demo. Times in poll_start calls, ~6.3 ms each (the
; stick read): 15 s on the title without a key or a button starts it.
TITLE_IDLE = 2385       ; ~15 s
DEMO_START = 120        ; ~0.8 s on the level before the first move
DEMO_STEP  = 22         ; ~0.15 s between two moves (plus the drawing)
DEMO_END   = 255        ; ~1.6 s on the solved level
TITLE_TICK = 256        ; ~1.6 s: byte countdown starts at zero, wraps on DEC

; --- Title screen: a full-width warehouse (tile rows 9-11). The player
; pushes a box along row 10, from the left wall to the target at the right.
TITLE_ROW  = 10
TITLE_COL  = 1
TITLE_TARGET_COL = NCOLS-2
TITLE_PUSHES = TITLE_TARGET_COL-TITLE_COL-1
TITLE_PHASES = TITLE_PUSHES+3  ; then hold the solved position for two ticks
TITLE_PRESS_COL = 88    ; pixel column, centred with 8-pixel character spacing
TITLE_PRESS_SL = 124    ; scanline of the blinking "KEY OR BUTTON"
STYLE_COMPACT = 3       ; native-size text is always white; only x2 may be tinted
COLOR_WHITE  = 0
COLOR_GREEN  = 1
COLOR_VIOLET = 2
COLOR_ORANGE = 3
COLOR_BLUE   = 4
HOF_TICK     = 154      ; calibrated on POM2: ten phases take about ten seconds

; --- Level selection: pages of 10 x 8 numbers, 4 byte columns each ---
SEL_COLS   = 10
SEL_PAGE   = 80
SEL_SL0    = 24         ; scanline of the first row of numbers
SEL_DY     = 18         ; scanlines from one row to the next

; =============================================================================
; Zero page ($50+, see apple2_micro_sokoban.cfg)
; =============================================================================
.zeropage
temp:            .res 1
temp2:           .res 1
watching:        .res 1          ; 1 = solution playback skips history and records
sol_ts_track:    .res 1          ; MICROSOL track/sector list
sol_ts_sector:   .res 1
sol_left:        .res 1          ; sol_read: bytes still to copy
sol_more:        .res 1
ptr_lo:          .res 1  ; HGR destination pointer
ptr_hi:          .res 1
src_lo:          .res 1  ; bitmap / font source pointer
src_hi:          .res 1
sptr_lo:         .res 1  ; scratch pointer (level data, strings)
sptr_hi:         .res 1
tbl_lo:          .res 1  ; screen-table pointer
tbl_hi:          .res 1
hptr_lo:         .res 1  ; history ring pointer
hptr_hi:         .res 1
cur_coll:        .res 1  ; collection being played
cur_lvl:         .res 1  ; level in it, 0-based (index in the kept levels)
player_row:      .res 1
player_col:      .res 1
lvl_w:           .res 1
lvl_h:           .res 1
row_offset:      .res 1
col_offset:      .res 1
parse_row:       .res 1  ; init_level decoder position
parse_col:       .res 1
run_len:         .res 1
new_row:         .res 1
new_col:         .res 1
box_row:         .res 1
box_col:         .res 1
dir_code:        .res 1  ; DIR_* of the move being played / undone
dir_dy:          .res 1  ; signed: -1, 0, 1
dir_dx:          .res 1
draw_row:        .res 1
draw_col:        .res 1
had_push:        .res 1  ; 1 = the move pushed a box
on_target:       .res 1  ; 1 = that box landed on a target
dead_square:     .res 1  ; 1 = that box landed on a dead square (dead_tbl)
moves_lo:        .res 1  ; move / push counters, 16 bits
moves_hi:        .res 1
pushes_lo:       .res 1
pushes_hi:       .res 1
boxes_left:      .res 1  ; boxes not on a target: 0 = solved
hist_pos_lo:     .res 1  ; next history slot, 0..HIST_LEN-1
hist_pos_hi:     .res 1
undo_n_lo:       .res 1  ; moves that can be undone (<= HIST_LEN)
undo_n_hi:       .res 1
redo_n_lo:       .res 1  ; moves that can be redone
redo_n_hi:       .res 1
quiet:           .res 1  ; 1 = no drawing, no sound (restart rewind)
replaying:       .res 1  ; 1 = execute_move is a redo (history not rewritten)
num_lo:          .res 1  ; print_num argument
num_hi:          .res 1
sel_coll:        .res 1  ; level selection: collection, level, first of page
sel_idx:         .res 1
sel_first:       .res 1
demo_src_lo:     .res 1  ; run_demo: next byte of the moves
demo_src_hi:     .res 1
DOS_CMD_MAX = 32
DOS_CMD_WORKBSS = 1
DOS_ZP_START = $50
DOS_ZP_LEN = * - temp

; =============================================================================
; LOWBSS ($1000-$1FFF, not in the file)
; =============================================================================
.segment "LOWBSS"
pack_buf:        .res PACK_MAX   ; the level pack in use, BLOADed at PACK_ADDR
boot_code = pack_buf             ; and before the first one, the BOOT segment
save_buf:        .res SAVE_LEN   ; active profile, isolated from the level pack
.assert save_buf + SAVE_LEN <= $2000, error, "profile save runs into HGR"

; =============================================================================
; Work RAM ($0840-$0FFF, not part of the BRUN file)
; =============================================================================
.segment "WORKBSS"
hist:            .res HIST_LEN   ; move history ring
STATE_GRID:      .res 240        ; 20x12 playfield, one tile code per cell
dead_tbl:        .res 240        ; 1 = a box here can never reach a target
dead_q:          .res 240        ; find_dead: cells to look around (queue)
rank_hi:        .res 1
rankings_old:   .res 1
resume_pending: .res 1
game_active:    .res 1
position_dirty: .res 1
autosave_lo:    .res 1
autosave_hi:    .res 1
loaded_pack:     .res 1          ; pack in pack_buf, $FF = none
title_ix:        .res 1
title_glyph:     .res 1
title_col_start: .res 1
title_scanline:  .res 1
big_byte0:       .res 1
big_byte1:       .res 1
num_col:         .res 1          ; text cursor column (pixels when num_step = 8)
num_sl:          .res 1
num_step:        .res 1
num_pow:         .res 1          ; print_num power index
str_ix:          .res 1
dq_head:         .res 1
dq_tail:         .res 1
dq_cell:         .res 1
dq_to:           .res 1
demo_i:          .res 1          ; run_demo: demo level being played
demo_left_lo:    .res 1          ; moves left
demo_left_hi:    .res 1
demo_byte:       .res 1          ; packed moves, low bits first
demo_nbits:      .res 1          ; moves left in demo_byte
demo_wait:       .res 1          ; demo_pause countdown
demo_sv_coll:    .res 1          ; the level to resume after the demo
demo_sv_lvl:     .res 1
idle_lo:         .res 1          ; title_wait countdown
title_tick:      .res 1          ; title_wait: polls left before the next title_step
title_phase:     .res 1          ; pushes made in the title animation, then a hold
title_player_col:.res 1          ; clamped player column for the current phase
title_blink:     .res 1          ; 1 = "KEY OR BUTTON" shown
big_color:       .res 1          ; COLOR_* for doubled glyphs
glyph_color:     .res 1          ; raster tint scratch
glyph_mask_index:.res 1
demo_active:     .res 1
tutorial_on:     .res 1
tutorial_idx:    .res 1
option_sel:      .res 1
all_solved_lo:   .res 1          ; draw_title_info: levels with a record, all collections
all_solved_hi:   .res 1
idle_hi:         .res 1
fp_coll:         .res 1          ; load_save: collection being checked
fp_n:            .res 1          ; levels left to wipe
new_record:      .res 1          ; 1 = the level just solved beat its record
best_lo:         .res 1          ; the record before that
best_hi:         .res 1
tot_moves_lo:    .res 1          ; end screen totals
tot_moves_hi:    .res 1
tot_pushes_lo:   .res 1
tot_pushes_hi:   .res 1
tot_solved:      .res 1
sel_prev:        .res 1
tot_i:           .res 1
sel_c:           .res 1          ; draw_select: column, scanline, level
sel_sl:          .res 1
sel_lvl:         .res 1
dirty_n:         .res 1          ; dirty-tile queue (max 3 per move)
dirty_row:       .res 4
dirty_col:       .res 4
flush_ix:        .res 1
in_src:          .res 1          ; 0 = last action came from keyboard, 1 = joystick
joy_hold:        .res 1          ; auto-repeat countdown while the stick is held
btn0_prev:       .res 1          ; button edge detection
btn1_prev:       .res 1
b0_used:         .res 1          ; 1 = the stick moved while button 0 was held,
                                 ; until it is centred with the button up
menu_sel:        .res 1
menu_prev:       .res 1
front_page:      .res 1          ; page on screen: 0 = page 1, PAGE2_EOR = page 2
hgr_front_page = front_page      ; (dev/lib/hgr/hgr_flip.asm)
deadwarn_on:      .res 1          ; 1 = warn when a box goes onto a dead square
score_total:     .res 4          ; exact sum of best moves, at most 454 * 65535
score_solved:    .res 2
score_work:      .res 4          ; decimal print scratch
score_level:     .res 2          ; points of one solved level
score_left:      .res 2          ; records left to scan
score_digit:     .res 1
hof_row:         .res 1
hof_offset:      .res 1
hof_index:       .res 1
hof_initials:    .res 3          ; initials editing scratch (ASCII)
hof_blink_tick:  .res 1
hof_blink_state: .res 1
hof_blink_color: .res 1
hof_cycles:      .res 1          ; timed attract ranking: ten one-second phases
profile_sel:     .res 1

; =============================================================================
; Pages 2 and 3 ($0200-$03CF, see apple2_micro_sokoban.cfg): buffers moved out
; of the full resident. exit.asm restores DOS's zero page from apple2_zp_buf
; before DOS types LOAD HELLO into page 2.
; =============================================================================
.segment "PAGE2BSS"
apple2_zp_buf:   .res 256        ; DOS's zero page while the game runs
.segment "PAGE3BSS"
hof_buf:         .res HOF_LEN

; =============================================================================
.code

; The loader enters at $6000. The title music's speaker loop comes first: it
; counts cycles, and here no later change can push it across a page boundary.
        JMP main
.include "title_music.inc"

; =============================================================================
; MAIN — entry point
; =============================================================================
main:
        APPLE2_PREAMBLE
        LDX #$00                        ; the start-only code came in behind the
@boot:  LDA __BSS_RUN__,X               ; resident, where BSS is: down to
        STA boot_code,X                 ; pack_buf with it, free until the
        LDA __BSS_RUN__+$100,X          ; first level pack
        STA boot_code+$100,X
        LDA __BSS_RUN__+$200,X
        STA boot_code+$200,X
        INX
        BNE @boot
        JSR apple2_zp_save              ; ZP is DOS/Applesoft's: restored on quit
        JSR init_disk_cache
        LDA #$00
        STA btn0_prev
        STA btn1_prev
        STA joy_hold
        STA cur_coll
        STA cur_lvl
        STA quiet
        STA moves_lo
        STA moves_hi
        STA demo_active
        STA resume_pending
        STA rankings_old
        STA game_active
        STA position_dirty
        STA hof_cycles
        STA tutorial_on
        STA tutorial_idx
        STA replaying
        STA watching
        STA front_page                  ; page 1 on screen, drawing on page 1
        JSR set_draw_page
        LDA #$01
        STA deadwarn_on
        LDA #$FF
        STA loaded_pack

        ; Blank-first: page 1 is cleared while the display still shows text,
        ; then the title is drawn on page 2 and flipped in.
        JSR hgr_init_clear
        JSR begin_screen
        JSR draw_title
        JSR show_screen
        JSR load_hof
        JSR migrate_rankings
        JSR set_profile_save
        JSR load_save                   ; the active profile's records
        JSR restore_tutorial
        JSR calculate_score
        JSR update_hof
        JSR first_unsolved              ; where to resume,
        JSR select_resume
        JSR find_level                  ; and that level's pack;
        LDA #<str_blank7                ; (wipe "LOADING")
        LDY #>str_blank7
        JSR show_status
        JSR draw_title_warehouse        ; LOADING shared the lower wall's pixels
        JSR draw_title_info             ; then progress and resume level
title_loop:
        JSR title_wait                  ; any key / any button starts,
        BNE title_start
        JSR run_hof_attract             ; ten seconds of profile rankings
        BCS return_title
        JSR run_demo                    ; ~15 s without one: the demo,
        JSR find_level                  ; (the resume level's pack again)
return_title:
        JSR begin_screen                ; then the title again
        JSR draw_title
        JSR draw_title_info
        JSR show_screen
        JMP title_loop
title_start:
        CMP #ACT_PROFILE
        BNE @tutorial
        JSR run_profiles
        JMP return_title
@tutorial:
        CMP #ACT_TUTORIAL
        BNE @goto
        LDA #MENU_TUTORIAL
        JMP menu_result
@goto:
        CMP #ACT_GOTO                   ; G goes to the level grid first
        BNE @play
        LDA #MENU_GOTO
        JMP @action
@play:  CMP #ACT_HELP
        BEQ @help
        CMP #ACT_MENU
        BEQ @menu
        BNE first_play                  ; (always)
@help:
        JSR run_help
@menu:
        JSR run_menu
        CMP #MENU_BACK
        BNE @action
        JMP return_title
@action:
        CMP #MENU_PROFILE
        BEQ return_title
        CMP #MENU_GOTO
        BNE @resume
        JSR run_select
        BCS game_loop
        JMP return_title                ; cancellation never starts a game
@resume:
        CMP #MENU_RESUME
        BEQ @play
        CMP #MENU_RESET                ; restart must bypass the saved position
        BNE @other
        LDA #0
        STA resume_pending
        BEQ game_loop
@other: JMP menu_result

; first_play: play as the active profile, from the title or after changing
; profile in the menu. One without a lesson flag, a record or a saved
; position has never played: the lessons come first.
first_play:
        LDA hof_buf+HOF_TUTORIAL
        AND #1
        ORA score_solved
        ORA score_solved+1
        ORA resume_pending
        BNE game_loop
        INC tutorial_on
game_loop:
        JSR start_level
        LDA #1
        STA game_active
        STA position_dirty
        JSR restore_position
        LDA #0
        STA autosave_lo
        STA autosave_hi
redraw_level:
        JSR draw_level

move_loop:
        JSR idle_save
        JSR get_input
        BEQ move_loop                   ; ACT_NONE
        PHA
        LDA #0
        STA autosave_lo
        STA autosave_hi
        PLA
        CMP #ACT_RIGHT+1
        BCS @not_dir
        JMP key_dir                     ; ACT_UP..ACT_RIGHT
@not_dir:
        CMP #ACT_UNDO
        BEQ key_undo
        CMP #ACT_REDO
        BEQ key_redo
        CMP #ACT_RESET
        BNE @not_reset
        JMP key_reset
@not_reset:
        CMP #ACT_NEXT
        BNE @prev_check
        JMP key_next
@prev_check:
        CMP #ACT_PREV
        BNE @menu_check
        JMP key_prev
@menu_check:
        CMP #ACT_HELP
        BEQ key_help
        CMP #ACT_MENU
        BEQ key_menu
        CMP #ACT_GOTO
        BEQ key_goto
        JMP move_loop                   ; ignore the rest

key_goto:
        JSR run_select                  ; C = 1: cur_coll / cur_lvl chosen
        BCC @back
        LDA #0
        STA tutorial_on                 ; cancel must retain the lesson and its HUD
        JMP game_loop
@back:  JMP redraw_level

key_undo:
        JSR execute_undo
        JMP move_loop

key_redo:
        JSR execute_redo
        JMP check_done                  ; a redo can finish the level

key_help:
        JSR save_position
        JSR run_help
key_menu:
        JSR save_position
        JSR run_menu                    ; returns A = MENU_* choice
menu_result:
        CMP #MENU_PROFILE
        BNE @tutorial
        JMP first_play                  ; another profile: its own first game?
@tutorial:
        CMP #MENU_TUTORIAL
        BNE @actions
        LDA #0
        STA tutorial_idx
        LDA #1
        STA tutorial_on
        JMP game_loop
@actions:
        CMP #MENU_SOLUTION
        BNE @reset
        JSR play_solution
        LDA game_active
        BEQ @solved_title
        JSR select_resume               ; the position saved as the menu opened
        LDA tutorial_on                 ; (a lesson has none: it starts again)
        BNE @again
        LDA resume_pending
        BEQ @again
        JSR restore_position            ; goes back onto the level, which is
        JMP redraw_level                ; still decoded; the history was kept
@again: JMP game_loop
@solved_title:
        JMP return_title
@reset:
        CMP #MENU_RESET
        BEQ key_reset
        CMP #MENU_GOTO
        BEQ key_goto
        CMP #MENU_QUIT
        BNE @resume
        JMP apple2_exit                 ; ZP + text screen back, DOS prompt
@resume:
        JMP redraw_level                ; MENU_RESUME: repaint and carry on

key_dir:
        SEC                             ; ACT_UP..ACT_RIGHT -> DIR_UP..DIR_RIGHT
        SBC #ACT_UP
        STA dir_code
        JSR execute_move
        JMP check_done

; key_reset: rewind the level through the history, silently, so the whole
; restart can be redone. If the ring has forgotten the first moves, the
; counters do not reach 0: reload the level instead (history lost).
key_reset:
        LDA #$01
        STA quiet
@rew:   JSR execute_undo
        BNE @rew                        ; A = 1 while something was undone
        LDA #$00
        STA quiet
        LDA moves_lo
        ORA moves_hi
        BEQ @redraw
        JMP game_loop
@redraw:
        JMP redraw_level

key_next:
        LDA tutorial_on
        BEQ @normal
        JMP tutorial_next
@normal:
        JMP advance_level

; key_prev: previous level; before the first, the last of the previous
; collection.
key_prev:
        LDA tutorial_on
        BEQ @normal
        LDA tutorial_idx
        BEQ @same
        DEC tutorial_idx
@same:  JMP game_loop
@normal:
        LDA cur_lvl
        BNE @dec
        LDX cur_coll
        DEX
        BPL @coll
        LDX #NUM_COLLS-1
@coll:  STX cur_coll
        LDA coll_count,X
@dec:   SEC
        SBC #$01
        STA cur_lvl
        JMP game_loop

check_done:
        LDA boxes_left
        BNE move_loop_j                 ; not solved yet
        LDA tutorial_on
        BEQ @record
        JSR begin_screen
        JSR draw_success
        JSR show_screen
        JSR play_fanfare
        JSR wait_any
        JMP tutorial_next
@record:

        ; Level complete: record, success screen, save, then the end screen
        ; if it was the last level of the collection
        LDA #0
        STA snapshot
        STA position_dirty
        LDA save_mask
        ORA #$80
        STA save_mask
        JSR record_solution
        JSR calculate_score
        JSR begin_screen
        JSR draw_success
        JSR show_screen
        JSR play_fanfare
        JSR write_save
        JSR update_hof
        JSR write_hof
        JSR wait_any
        LDX cur_coll
        LDA cur_lvl
        CLC
        ADC #$01
        CMP coll_count,X
        BCC advance_level
        JSR end_screen

; advance_level: next level; after the last, the next collection.
advance_level:
        INC cur_lvl
        LDX cur_coll
        LDA cur_lvl
        CMP coll_count,X
        BCC game_loop_j
        LDA #$00
        STA cur_lvl
        INX
        CPX #NUM_COLLS
        BCC @coll
        LDX #$00
@coll:  STX cur_coll
game_loop_j:
        JMP game_loop
move_loop_j:
        JMP move_loop

; =============================================================================
; INPUT
; =============================================================================
; get_input: non-blocking poll of keyboard then joystick.
; Returns A = ACT_* (0 = nothing), Z set on 0. in_src = 0 keyboard / 1 joystick.
; Button 1 fires on press. Button 0 fires ACT_UNDO on release, unless the
; stick was pushed while it was held: then stick left / right are undo / redo
; (auto-repeat), and once the button is released the stick must come back to
; the centre before it moves the player again. The stick alone moves,
; auto-repeating every JOY_REPEAT calls.
; Without a stick the paddle timers never run out (nothing charges them) and
; the button inputs float: a timer still running after read_stick, ~6 ms
; after PTRIG and twice the longest a real paddle takes, means no stick, and
; nothing is taken from the game port.
; Clobbers A, X, Y.
; =============================================================================
get_input:
        LDA #$00
        STA in_src
        JSR poll_key                    ; kbd.asm: A = key, upper-cased, or 0
        BEQ get_stick
        LDX #$00
@ml:    LDY key_tbl,X
        BEQ @other                      ; end of table
        CMP key_tbl,X
        BEQ @found
        INX
        INX
        BNE @ml
@found: LDA key_tbl+1,X
        RTS
@other: LDA #ACT_OTHER
        RTS

; Joystick-only entry: initials read the keyboard themselves. Polling it a
; second time here could consume a letter or RETURN between the two polls.
get_stick:
        LDA #$01
        STA in_src
        JSR read_stick
        LDA PADDL0                      ; a timer still running: no stick
        ORA PADDL1
        BMI @centre
        ; --- button 1 (press edge) ---
        LDA BUTN1
        BMI @b1_down
        LDA #$00
        STA btn1_prev
        BEQ @b0
@b1_down:
        LDA btn1_prev
        BNE @b0
        LDA #$01
        STA btn1_prev
        LDA #ACT_MENU
        RTS
@b0:    ; --- button 0 ---
        LDA BUTN0
        BMI @b0_down
        LDA btn0_prev
        BEQ @axes                       ; not held before either
        LDA #$00                        ; released
        STA btn0_prev
        LDA b0_used
        BNE @axes                       ; it was a tape shuttle, not a tap
        LDA #ACT_UNDO
        RTS
@b0_down:
        LDA btn0_prev
        BNE @shuttle
        LDA #$01                        ; just pressed
        STA btn0_prev
        LDA #$00
        STA b0_used
        STA joy_hold
@shuttle:
        LDA joy_x
        CMP #JOY_LO
        BCC @sh_undo
        CMP #JOY_HI+1
        BCS @sh_redo
@centre:
        LDA #$00                        ; centred: nothing, rearm the repeat
        STA joy_hold
        RTS
@sh_undo:
        LDA #ACT_UNDO
        BNE @sh
@sh_redo:
        LDA #ACT_REDO
@sh:    LDX #$01
        STX b0_used
        BNE @dir

@axes:  JSR stick_dir                   ; JOY_UP..JOY_RIGHT = ACT_UP..ACT_RIGHT
        BNE @moved
        STA joy_hold                    ; centered: A = 0, rearm the repeat
        STA b0_used                     ; and a shuttle is over: the stick moves
        RTS
@moved: LDX b0_used                     ; still where the shuttle left it:
        BNE @wait                       ; no move before it has been centred
@dir:   LDX joy_hold
        BEQ @fire
        DEC joy_hold
@wait:  LDA #$00
        RTS
@fire:  LDX #JOY_REPEAT
        STX joy_hold
        CMP #$00                        ; Z clear: an action
        RTS

; Keyboard map: (ASCII, action) pairs, 0-terminated.
key_tbl:
        .byte 'I', ACT_UP,   'K', ACT_DOWN, 'J', ACT_LEFT, 'L', ACT_RIGHT
        .byte 'W', ACT_UP,   'S', ACT_DOWN, 'A', ACT_LEFT, 'D', ACT_RIGHT
        .byte $0B, ACT_UP,   $0A, ACT_DOWN, $08, ACT_LEFT, $15, ACT_RIGHT
        .byte 'U', ACT_UNDO, 'Y', ACT_REDO, 'R', ACT_RESET
        .byte 'N', ACT_NEXT, 'P', ACT_PREV
        .byte 'H', ACT_HELP, $1B, ACT_MENU, 'Q', ACT_QUIT, 'C', ACT_DEADWARN
        .byte 'G', ACT_GOTO
        .byte 'F', ACT_HOF, 'O', ACT_OPTIONS, 'T', ACT_TUTORIAL
        .byte 'V', ACT_PROFILE
        .byte $0D, ACT_SELECT, ' ', ACT_SELECT
        .byte 0

; -----------------------------------------------------------------------------
; wait_any: block until a key (any) or a joystick button press. The keyboard
; must first stay quiet for WAIT_QUIET polls (~0.25 s, several auto-repeat
; periods of a //e): a key typed ahead, or still repeating from the winning
; move, is thrown away instead of skipping the screen. A button counts at
; once. Stick deflections are ignored so a stick still held from the winning
; push does not skip the screen.
; -----------------------------------------------------------------------------
WAIT_QUIET = 40
wait_any:
        LDX #WAIT_QUIET
@quiet: STX temp2                       ; (no poll uses temp2)
        JSR poll_start
        BEQ @none
        LDX in_src
        BEQ wait_any                    ; a key too soon: quiet starts again
        RTS
@none:  LDX temp2
        DEX
        BNE @quiet
@lp:    JSR poll_start
        BEQ @lp
        RTS

; poll_start: one look at the keyboard and the buttons. A = the action, Z
; clear, or A = 0. Any key counts; on the joystick only the buttons do (a
; stick resting off centre must not start anything). ~6.3 ms without a key.
poll_start:
        JSR get_input
        BEQ @none
        LDX in_src
        BEQ @yes                        ; keyboard: anything goes
        CMP #ACT_UNDO                   ; joystick: buttons only
        BEQ @yes
        CMP #ACT_MENU
        BEQ @yes
@none:  LDA #$00
        RTS
@yes:   ORA #$00                        ; Z clear (actions are not 0)
        RTS

; title_wait: wait_any for at most TITLE_IDLE polls (~15 s). A = the
; action (Z clear), or A = 0 (Z set) when nobody pressed anything.
title_wait:
        JSR title_music_reset
        LDA #<TITLE_IDLE
        STA idle_lo
        LDA #>TITLE_IDLE
        STA idle_hi
        LDA #<TITLE_TICK
        STA title_tick
@lp:    JSR poll_start
        BNE @done
        JSR title_music
        DEC title_tick                  ; every ~1.6 s: animation, blink
        BNE @idle
        LDA #<TITLE_TICK
        STA title_tick
        JSR title_animate
@idle:  LDA idle_lo
        ORA idle_hi
        BNE @countdown
        LDA title_phase
        CMP #TITLE_PUSHES
        BCC @lp                         ; finish placing the box before attract
        LDA #0
        RTS
@countdown:
        LDA idle_lo
        BNE @dec
        DEC idle_hi
@dec:   DEC idle_lo
        JMP @lp
@done:  RTS

; start_level: decode (cur_coll, cur_lvl), fresh counters and history.
; watch_level: the same, history kept (SOLUTION plays over the game).
start_level:
        LDA #$00
        STA hist_pos_lo
        STA hist_pos_hi
        STA undo_n_lo
        STA undo_n_hi
        STA redo_n_lo
        STA redo_n_hi
watch_level:
        JSR init_level
        LDA #$00
        STA moves_lo
        STA moves_hi
        STA pushes_lo
        STA pushes_hi
        RTS

; draw_level: the whole level and its HUD, drawn hidden then shown.
draw_level:
        JSR begin_screen
        JSR render_all
        JSR draw_hud
        LDA tutorial_on
        BEQ @show
        JSR draw_tutorial_info
@show:
        JMP show_screen

; =============================================================================
; run_demo: the title-screen demo. Plays the demo levels (levels.inc,
; demo_*: from levels/solutions.txt) one after the other with their stored
; solutions, at a watchable pace, then returns; a key or a button returns
; at once. Nothing is recorded or saved; cur_coll / cur_lvl are put back.
; =============================================================================
run_demo:
        LDA #1
        STA demo_active
        LDA cur_coll
        STA demo_sv_coll
        LDA cur_lvl
        STA demo_sv_lvl
        LDA #$00
        STA demo_i
@level: LDX demo_i
        LDA demo_coll,X
        STA cur_coll
        LDA demo_lvl,X
        STA cur_lvl
        LDA demo_ptr_lo,X
        STA demo_src_lo
        LDA demo_ptr_hi,X
        STA demo_src_hi
        LDA demo_len_lo,X
        STA demo_left_lo
        LDA demo_len_hi,X
        STA demo_left_hi
        LDA #$00
        STA demo_nbits
        JSR start_level
        JSR draw_level
        LDA #DEMO_START
        JSR demo_pause
        BCS @stop
@move:  LDA demo_left_lo
        ORA demo_left_hi
        BEQ @solved
        JSR demo_next
        STA dir_code
        JSR execute_move
        LDA demo_left_lo
        BNE @dl
        DEC demo_left_hi
@dl:    DEC demo_left_lo
        LDA #DEMO_STEP
        JSR demo_pause
        BCC @move
        BCS @stop
@solved:
        JSR play_fanfare
        LDA #DEMO_END
        JSR demo_pause
        BCS @stop
        INC demo_i
        LDA demo_i
        CMP #DEMO_COUNT
        BCC @level
@stop:  LDA demo_sv_coll
        STA cur_coll
        LDA demo_sv_lvl
        STA cur_lvl
        LDA #0
        STA demo_active
        RTS

; demo_pause: A polls (~6.3 ms each) unless a key or a button comes first:
; then C = 1.
demo_pause:
        STA demo_wait
@lp:    JSR poll_start
        BNE @hit
        DEC demo_wait
        BNE @lp
        CLC
        RTS
@hit:   SEC
        RTS

; demo_next: A = the next DIR_* of the demo solution (four a byte, low
; bits first).
demo_next:
        LDA demo_nbits
        BNE @have
        LDY #$00
        LDA (demo_src_lo),Y
        STA demo_byte
        INC demo_src_lo
        BNE @nc
        INC demo_src_hi
@nc:    LDA #4
        STA demo_nbits
@have:  DEC demo_nbits
        LDA demo_byte
        LSR demo_byte
        LSR demo_byte
        AND #$03
        RTS

; =============================================================================
; MENU — help text + cursor-driven choice. Returns A = MENU_*.
; =============================================================================
run_menu:
        LDA #MENU_RESUME
        STA menu_sel
@paint:
        JSR @screen
@loop:  JSR get_input
        BEQ @loop
        CMP #ACT_UP
        BNE @down_check
        JMP @up
@down_check:
        CMP #ACT_DOWN
        BNE @reset_check
        JMP @down
@reset_check:
        CMP #ACT_RESET
        BEQ @reset
        CMP #ACT_QUIT
        BEQ @quit
        CMP #ACT_DEADWARN
        BEQ @options
        CMP #ACT_OPTIONS
        BEQ @options
        CMP #ACT_TUTORIAL
        BEQ @tutorial
        CMP #ACT_GOTO
        BEQ @goto
        CMP #ACT_HOF
        BEQ @hof
        CMP #ACT_PROFILE
        BEQ @profiles
        CMP #ACT_SELECT
        BEQ @select
        CMP #ACT_MENU
        BEQ @resume
        CMP #ACT_HELP
        BEQ @help
        CMP #ACT_LEFT                   ; J / stick left: stay on the line
        BEQ @loop
        CMP #ACT_RIGHT
        BEQ @loop
        LDX in_src
        BEQ @resume                     ; any other KEY resumes
        CMP #ACT_UNDO                   ; button 0 selects; button 1 returns
        BEQ @select
        JMP @loop
@reset: LDA #MENU_RESET
        RTS
@quit:  LDA #MENU_QUIT
        RTS
@goto:  LDA #MENU_GOTO
        RTS
@tutorial:
        LDA #MENU_TUTORIAL
        RTS
@resume:
        LDA #MENU_BACK
        RTS
@select:
        LDA menu_sel
        CMP #MENU_OPTIONS
        BEQ @options
        CMP #MENU_HOF
        BEQ @hof
        CMP #MENU_PROFILE
        BEQ @profiles
        CMP #MENU_HELP
        BEQ @help
        RTS
@profiles:
        JSR run_profiles
        BCC @paint_profiles
        LDA #MENU_PROFILE
        RTS
@paint_profiles:
        JMP @paint
@help:  JSR run_help
        JMP @paint
@hof:   JSR run_hof
        JMP @paint
@options:
        JSR run_options
        LDA #MENU_OPTIONS               ; SOLUTION may have disappeared while in OPTIONS
        STA menu_sel
        JMP @paint
@up:    LDA menu_sel
        STA menu_prev
        BEQ @wrap_last
        DEC menu_sel
        JMP @moved
@wrap_last:
        JSR menu_last
        STA menu_sel
        JMP @moved
@down:  LDA menu_sel
        STA menu_prev
        INC menu_sel
        JSR menu_last
        CMP menu_sel
        BCS @moved
        LDA #$00
        STA menu_sel
@moved: ; erase only the old marker, then draw the new one
        LDA menu_prev
        JSR menu_cursor_position
        LDA #G_SPACE
        JSR put_glyph
        JSR menu_draw_cursor
        JSR menu_sound
        JMP @loop

@screen:
        JSR begin_screen
        JSR draw_menu
        JSR show_screen                 ; the cursor is drawn on the page shown
        JSR menu_draw_cursor
        RTS

run_help:
        JSR begin_screen
        JSR draw_help
        JSR show_screen
        JMP wait_any

menu_draw_cursor:
        LDA menu_sel
        JSR menu_cursor_position
        LDA #G_PLUS
        JMP put_glyph

menu_last:
        JSR cheat_on
        BEQ @quit
        LDA #MENU_SOLUTION
        RTS
@quit:  LDA #MENU_QUIT
        RTS

menu_cursor_position:
        ASL A
        ASL A                           ; 4 * index
        STA temp
        ASL A                           ; 8 * index
        CLC
        ADC temp                        ; 12 * index
        CLC
        ADC #MENU_SL0
        STA num_sl
        LDA #MENU_CURSOR_COL
        STA num_col
        LDA #8
        STA num_step
        RTS

; =============================================================================
; SOUND
; =============================================================================
; play_fanfare: three rising notes on level completion.
play_fanfare:
        JSR sound_enabled
        BEQ @done
        JMP @play
@done:  RTS
@play:
        LDA #$60
        LDX #$C0
        JSR tone
        LDA #$80
        LDX #$90
        JSR tone
        LDA #$C0
        LDX #$60
        JMP tone

; move_sounds: after a move. A click per step; a bright blip when a box lands
; on a target; two low notes when it lands on a dead square (if enabled).
move_sounds:
        JSR sound_enabled
        BEQ @done
        LDA quiet
        BNE @done
        LDA SPKR
        LDA on_target
        BEQ @corner
        LDA #$30
        LDX #$28
        JMP tone
@corner:
        LDA dead_square
        BEQ @done
        LDA deadwarn_on
        BEQ @done
        LDA #$20
        LDX #$C0
        JSR tone
        LDA #$18
        LDX #$F0
        JMP tone
@done:  RTS

; bump_sound: a short dull thud when a move is blocked.
bump_sound:
        JSR sound_enabled
        BEQ @done
        LDA quiet
        BNE @done
        LDA #$06
        LDX #$FF
        JMP tone
@done:  RTS

; =============================================================================
; init_level: decode level (cur_coll, cur_lvl) into STATE_GRID, loading its
; pack first if needed; find the player, count the boxes off target, then
; the dead squares (find_dead).
; A level record is w, h, row, col, then runs: tile << 5 | (length - 1), in
; row-major order over the w x h box (tools/micro_sokoban_levels.py).
; =============================================================================
init_level:
        LDA tutorial_on
        BEQ @normal
        LDX tutorial_idx
        LDA tutorial_ptr_lo,X
        STA sptr_lo
        LDA tutorial_ptr_hi,X
        STA sptr_hi
        JMP decode_level
@normal:
        JSR find_level                  ; sptr -> the record, pack loaded
decode_level:
        LDY #$00
        TYA
@clr:   STA STATE_GRID,Y
        INY
        CPY #STATE_GRID_LEN
        BNE @clr
        STA boxes_left
        STA parse_row
        STA parse_col

        TAY                             ; Y = 0: the record header
        LDA (sptr_lo),Y
        STA lvl_w
        INY
        LDA (sptr_lo),Y
        STA lvl_h
        INY
        LDA (sptr_lo),Y
        STA row_offset
        INY
        LDA (sptr_lo),Y
        STA col_offset
        INY
@run:   LDA (sptr_lo),Y
        INY
        STY temp                        ; record offset (levels < 256 bytes)
        PHA
        AND #$1F
        STA run_len
        INC run_len                     ; length 1..32
        PLA
        LSR A
        LSR A
        LSR A
        LSR A
        LSR A
        STA temp2                       ; tile
@cell:  LDA parse_row                   ; STATE_GRID[(row+r0)*20 + col+c0]
        CLC
        ADC row_offset
        TAY
        LDA row_x20,Y
        CLC
        ADC parse_col
        CLC
        ADC col_offset
        TAX
        LDA temp2
        STA STATE_GRID,X
        CMP #TILE_BOX
        BNE @nobox
        INC boxes_left
@nobox: CMP #TILE_PLAYER
        BEQ @player
        CMP #TILE_PLAYER_TARGET
        BNE @next
@player:
        LDA parse_row
        CLC
        ADC row_offset
        STA player_row
        LDA parse_col
        CLC
        ADC col_offset
        STA player_col
@next:  INC parse_col
        LDA parse_col
        CMP lvl_w
        BCC @same_row
        LDA #$00
        STA parse_col
        INC parse_row
        LDA parse_row
        CMP lvl_h
        BCS @done
@same_row:
        DEC run_len
        BNE @cell
        LDY temp
        JMP @run
@done:  JMP find_dead                   ; the dead squares of this level

; find_level: sptr := record of level (cur_coll, cur_lvl) in pack_buf,
; BLOADing its pack if another one is loaded.
find_level:
        LDX cur_coll
        LDA coll_first_pack,X
        STA temp                        ; candidate pack
        LDA coll_npacks,X
        STA temp2                       ; packs left to try
@find:  LDX temp
        LDA cur_lvl
        SEC
        SBC pack_first,X
        CMP pack_count,X
        BCC @found                      ; A = index in the pack
        INC temp
        DEC temp2
        BNE @find
        LDA #$00                        ; (not reached: the tables cover it)
@found: PHA
        CPX loaded_pack
        BEQ @ready
        STX loaded_pack
        JSR load_pack
@ready: PLA
        TAX                             ; sptr = pack_buf + offset[index]
        LDA pack_buf+1,X                ; offset low (pack_buf is page aligned)
        STA sptr_lo
        TXA
        CLC
        ADC pack_buf                    ; + n: the high bytes follow the lows
        TAX
        LDA pack_buf+1,X
        CLC
        ADC #>pack_buf
        STA sptr_hi
        RTS

; load_pack: "BLOAD <name>,A$1000" for pack loaded_pack. A 4 KB pack takes
; a few seconds: "LOADING" shows bottom right of the screen meanwhile.
load_pack:
        LDA #<str_loading
        LDY #>str_loading
        JSR show_status
        LDX loaded_pack
        STX io_id
        LDA pack_name_lo,X
        STA io_name
        LDA pack_name_hi,X
        STA io_name+1
        LDA #<pack_buf
        STA io_dest
        LDA #>pack_buf
        STA io_dest+1
        LDA #<PACK_MAX
        STA io_limit
        LDA #>PACK_MAX
        STA io_limit+1
        JMP fast_read

; show_status: the glyph string at A/Y (lo/hi) bottom right of the screen on
; show, packed (7-pixel glyphs), inset 14 pixels from the right edge.
show_status:
        STA sptr_lo
        STY sptr_hi
        LDA #1
        STA num_step
        LDA #HUD_RIGHT-3
        STA num_col
        LDA #HUD_BOT_SL
        STA num_sl
        JMP draw_str

profile_file_name: .byte "MICROSAVE", 0 ; final E replaced for profile 1..9
save_magic:    .byte "SOK2"

; =============================================================================
; Save file. load_save BLOADs MICROSAVE into save_buf: a foreign content (an
; older "SOK1" too) is wiped, and so is a file that cannot be read or has an
; impossible length; a file shorter than save_buf leaves the rest empty. Then
; each collection whose fingerprint differs from this build's loses its
; records and gets the new fingerprint.
; write_save BSAVEs it, unless the disk is write protected (DOS would stop
; the game with WRITE PROTECTED).
; =============================================================================
load_save:
        JSR wipe_save                   ; what the file does not bring is empty
        JSR profile_file
        JSR fast_read                   ; (unreadable: it brings nothing)
        LDA #0
        LDX io_limit+1
        CPX #>SAVE_LEN
        BNE @short
        LDX io_limit
        CPX #<SAVE_LEN
        BEQ @mask
@short: LDA #$FF
@mask:  STA save_mask
        LDX #3
@magic: LDA save_buf,X
        CMP save_magic,X
        BNE @wipe
        DEX
        BPL @magic
        BMI @colls                      ; (always)
@wipe:  JSR wipe_save
        LDX #3
@m:     LDA save_magic,X
        STA save_buf,X
        DEX
        BPL @m
        ; fingerprints: 0 after the wipe, so every collection gets its own
@colls: LDX #$00
@coll:  STX fp_coll
        TXA
        ASL A
        TAY                             ; Y = 2 * collection
        LDA save_buf+SAVE_FP,Y
        CMP coll_fp_lo,X
        BNE @reset
        LDA save_buf+SAVE_FP+1,Y
        CMP coll_fp_hi,X
        BEQ @next
@reset: LDA #$FF
        STA save_mask
        LDA coll_fp_lo,X
        STA save_buf+SAVE_FP,Y
        LDA coll_fp_hi,X
        STA save_buf+SAVE_FP+1,Y
        LDA coll_count,X
        STA fp_n
        LDA #$00
        JSR slot_ptr                    ; sptr -> its first record
@lvl:   LDY #3
        LDA #$00
@clr:   STA (sptr_lo),Y
        DEY
        BPL @clr
        LDA sptr_lo
        CLC
        ADC #4
        STA sptr_lo
        BCC @nc
        INC sptr_hi
@nc:    DEC fp_n
        BNE @lvl
        LDX fp_coll
@next:  INX
        CPX #NUM_COLLS
        BCC @coll
        RTS

; wipe_save: save_buf := zeroes (no magic, no record, no position).
wipe_save:
        LDA #<save_buf
        STA sptr_lo
        LDA #>save_buf
        STA sptr_hi
        LDX #>SAVE_LEN                  ; whole pages, then the rest
        LDY #$00
        TYA
@page:  CPX #$00
        BEQ @rest
@pg:    STA (sptr_lo),Y
        INY
        BNE @pg
        INC sptr_hi
        DEX
        JMP @page
@rest:  CPY #<SAVE_LEN
        BEQ @done
        STA (sptr_lo),Y
        INY
        BNE @rest
@done:  RTS

; write_save: C = 1 if nothing could be written (protected disk, or a disk
; error: "IO ERR" then stays in the status corner and the sectors stay due).
write_save:
        LDA save_mask
        BEQ @done
        JSR disk_protected
        BCS @done
        LDA #<str_saving
        LDY #>str_saving
        JSR show_status
        JSR profile_file
        LDA save_mask
        STA io_mask
        JSR fast_write
        BCS @done
        LDA #0
        STA save_mask
        LDA #<str_blank7                ; wipe "SAVING"
        LDY #>str_blank7
        JSR show_status
        CLC
@done:  RTS

; first_unsolved: cur_coll / cur_lvl := the first level without a record
; (the very first if every level is solved).
first_unsolved:
        LDA #$00
        STA cur_coll
        STA cur_lvl
@lp:    JSR slot_cur
        LDY #$00
        LDA (sptr_lo),Y
        INY
        ORA (sptr_lo),Y
        BEQ @done
        INC cur_lvl
        LDX cur_coll
        LDA cur_lvl
        CMP coll_count,X
        BCC @lp
        LDA #$00
        STA cur_lvl
        INC cur_coll
        LDA cur_coll
        CMP #NUM_COLLS
        BCC @lp
        LDA #$00
        STA cur_coll
@done:  RTS

; slot_ptr: sptr := save slot of level A of collection X; slot_cur: of the
; level being played. Clobbers A.
slot_cur:
        LDX cur_coll
        LDA cur_lvl
slot_ptr:
        CLC
        ADC coll_base_lo,X
        STA sptr_lo
        LDA coll_base_hi,X
        ADC #$00
        STA sptr_hi
        ASL sptr_lo
        ROL sptr_hi
        ASL sptr_lo
        ROL sptr_hi
        LDA sptr_lo
        CLC
        ADC #<(save_buf + SAVE_HDR)
        STA sptr_lo
        LDA sptr_hi
        ADC #>(save_buf + SAVE_HDR)
        STA sptr_hi
        RTS

; record_solution: the level is solved with moves / pushes. Keep it if the
; slot is empty or it takes fewer moves (fewer pushes on a tie). new_record,
; best_lo/hi (the previous best moves) tell the success screen.
record_solution:
        LDA save_mask
        ORA #1
        STA save_mask
        LDA save_buf+4
        AND #$80
        ORA cur_coll
        STA save_buf+4
        LDA cur_lvl
        STA save_buf+5
        JSR slot_cur
        LDA #$00
        STA new_record
        LDY #$00
        LDA (sptr_lo),Y
        STA best_lo
        INY
        LDA (sptr_lo),Y
        STA best_hi
        ORA best_lo
        BEQ @new                        ; first time solved
        LDA moves_hi                    ; moves < best?
        CMP best_hi
        BCC @new
        BNE @keep
        LDA moves_lo
        CMP best_lo
        BCC @new
        BNE @keep
        LDY #3                          ; same moves: pushes < best pushes?
        LDA pushes_hi
        CMP (sptr_lo),Y
        BCC @new
        BNE @keep
        DEY
        LDA pushes_lo
        CMP (sptr_lo),Y
        BCS @keep
@new:   LDA sptr_lo
        CLC
        ADC #4                          ; DOS binary header precedes payload
        PHA
        LDA sptr_hi
        ADC #0
        SEC
        SBC #>save_buf
        TAX
        LDA sector_bits,X
        ORA save_mask
        STA save_mask
        PLA
        CMP #253                        ; four-byte record straddles a sector
        BCC @marked
        INX
        LDA sector_bits,X
        ORA save_mask
        STA save_mask
@marked:
        LDA #$01
        STA new_record
        LDY #$00
        LDA moves_lo
        STA (sptr_lo),Y
        INY
        LDA moves_hi
        STA (sptr_lo),Y
        INY
        LDA pushes_lo
        STA (sptr_lo),Y
        INY
        LDA pushes_hi
        STA (sptr_lo),Y
@keep:  RTS

; =============================================================================
; render_all: draw the 240 cells on a freshly cleared draw page. Floor is
; all black, so floor cells are skipped (most of the grid).
; =============================================================================
render_all:
        LDA #$00
        STA draw_row
@rowlp: LDA #$00
        STA draw_col
@collp:
        LDX draw_row
        LDA row_x20,X
        CLC
        ADC draw_col
        TAX
        LDA STATE_GRID,X
        BEQ @skip                       ; TILE_FLOOR: already black
        JSR draw_tile
@skip:  INC draw_col
        LDA draw_col
        CMP #NCOLS
        BCC @collp
        INC draw_row
        LDA draw_row
        CMP #NROWS
        BCC @rowlp
        RTS

; =============================================================================
; Dirty-tile queue: a move records the cells it touches, flush_dirty then
; redraws them all from their final state. Nothing is queued while quiet.
; =============================================================================
queue_tile:
        LDA quiet
        BNE @done
        LDX dirty_n
        LDA draw_row
        STA dirty_row,X
        LDA draw_col
        STA dirty_col,X
        INC dirty_n
@done:  RTS

flush_dirty:
        LDA dirty_n
        BEQ @done
        LDA #$00
        STA flush_ix
@lp:
        LDX flush_ix
        LDA dirty_row,X
        STA draw_row
        LDA dirty_col,X
        STA draw_col
        LDX draw_row
        LDA row_x20,X
        CLC
        ADC draw_col
        TAX
        LDA STATE_GRID,X
        JSR draw_tile
        INC flush_ix
        LDA flush_ix
        CMP dirty_n
        BCC @lp
@done:
        LDA #$00
        STA dirty_n
        RTS

; =============================================================================
; draw_tile: draw one 14x16 tile at (draw_row, draw_col).
; Input: A = tile type (0-6)
; =============================================================================
draw_tile:
        CMP #TILE_BOX_TARGET
        BNE @src
        LDA hof_buf+HOF_SOUND
        AND #OPT_COLOR
        BEQ @mono
        LDA #TILE_BOX_COLOR
        BNE @src
@mono:  LDA #TILE_BOX_TARGET
@src:   ASL A                           ; src = tile_bitmaps + A*32
        ASL A
        ASL A
        ASL A
        ASL A
        CLC
        ADC #<tile_bitmaps
        STA src_lo
        LDA #>tile_bitmaps
        ADC #$00
        STA src_hi

        LDA draw_col
        ASL A
        STA temp                        ; byte offset into the HGR line

        LDA draw_row
        ASL A
        ASL A
        ASL A
        ASL A
        STA temp2                       ; start scanline = row*16

        LDX #$00
@scan:
        TXA
        CLC
        ADC temp2
        TAY                             ; Y = scanline (0-191)
        LDA hgr_lo,Y
        CLC
        ADC temp
        STA ptr_lo
        LDA hgr_hi,Y
        ADC #$00
        STA ptr_hi

        LDY #$00
        LDA (src_lo),Y
        STA (ptr_lo),Y
        INY
        LDA (src_lo),Y
        STA (ptr_lo),Y

        CLC
        LDA src_lo
        ADC #$02
        STA src_lo
        BCC @no_sinc
        INC src_hi
@no_sinc:
        INX
        CPX #$10
        BCC @scan
        RTS

; =============================================================================
; Cell helpers. cell_index: A = row*20 + col for (Y = row, X = col).
; =============================================================================
cell_index:
        TXA
        CLC
        ADC row_x20,Y
        RTS

; =============================================================================
; execute_move: play direction dir_code (DIR_*). Returns A = 1 if the player
; moved, A = 0 if blocked (Z flag set accordingly). Updates STATE_GRID, the
; counters, boxes_left, the history (unless replaying) and the screen.
; =============================================================================
execute_move:
        LDX dir_code
        LDA dir_dy_tbl,X
        STA dir_dy
        LDA dir_dx_tbl,X
        STA dir_dx
        LDA #$00
        STA dirty_n
        STA had_push
        STA on_target
        STA dead_square

        LDA player_row
        CLC
        ADC dir_dy
        STA new_row
        LDA player_col
        CLC
        ADC dir_dx
        STA new_col

        LDA new_row                     ; bounds (unsigned wrap catches -1)
        CMP #NROWS
        BCS @blk_tr
        LDA new_col
        CMP #NCOLS
        BCS @blk_tr

        LDY new_row
        LDX new_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        CMP #TILE_WALL
        BEQ @blk_tr
        CMP #TILE_BOX
        BEQ @try_push
        CMP #TILE_BOX_TARGET
        BEQ @try_push
        JMP @step                       ; floor or target

@blk_tr:
        JMP @blocked

@try_push:
        LDA new_row
        CLC
        ADC dir_dy
        STA box_row
        LDA new_col
        CLC
        ADC dir_dx
        STA box_col

        LDA box_row
        CMP #NROWS
        BCS @blk_tr
        LDA box_col
        CMP #NCOLS
        BCS @blk_tr

        LDY box_row
        LDX box_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        CMP #TILE_TARGET
        BEQ @to_target
        CMP #TILE_FLOOR
        BNE @blk_tr
        ; box onto plain floor: off target now; a dead square?
        INC boxes_left
        LDA #TILE_BOX
        STA STATE_GRID,X
        LDA dead_tbl,X
        STA dead_square
        JMP @box_placed
@to_target:
        LDA #$01
        STA on_target
        LDA #TILE_BOX_TARGET
        STA STATE_GRID,X
@box_placed:
        LDA #$01
        STA had_push
        LDA box_row
        STA draw_row
        LDA box_col
        STA draw_col
        JSR queue_tile

        ; the box leaves new_row/new_col
        LDY new_row
        LDX new_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        CMP #TILE_BOX
        BNE @left_target
        DEC boxes_left                  ; an off-target box moved on
@left_target:
        JSR leave_tile
        STA STATE_GRID,X

@step:
        ; --- leave old player cell ---
        LDY player_row
        LDX player_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        JSR leave_tile
        STA STATE_GRID,X
        LDA player_row
        STA draw_row
        LDA player_col
        STA draw_col
        JSR queue_tile

        ; --- enter new player cell ---
        LDY new_row
        LDX new_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        JSR enter_player
        STA STATE_GRID,X
        LDA new_row
        STA player_row
        STA draw_row
        LDA new_col
        STA player_col
        STA draw_col
        JSR queue_tile

        ; --- counters: 16 bits, and they stay at 65535 (a wrap to 0 would
        ; make a record that reads as "unsolved") ---
        INC moves_lo
        BNE @m_ok
        INC moves_hi
        BNE @m_ok
        DEC moves_lo
        DEC moves_hi
@m_ok:  LDA had_push
        BEQ @p_ok
        INC pushes_lo
        BNE @p_ok
        INC pushes_hi
        BNE @p_ok
        DEC pushes_lo
        DEC pushes_hi
@p_ok:
        ; --- history ---
        LDA watching
        BNE @hist_done
        LDA replaying
        BNE @replay
        LDA had_push                    ; code = dir | HIST_PUSH if pushed
        ASL A
        ASL A
        ORA dir_code
        JSR hist_put
        LDA #$00                        ; a new move drops the redo branch
        STA redo_n_lo
        STA redo_n_hi
        JMP @hist_done
@replay:
        JSR hist_advance
        LDA redo_n_lo                   ; redo_n--
        BNE @r_lo
        DEC redo_n_hi
@r_lo:  DEC redo_n_lo
@hist_done:
        LDA #1
        STA position_dirty
        JSR flush_dirty
        JSR draw_hud
        JSR move_sounds
        LDA #$01
        RTS

@blocked:
        JSR bump_sound
        LDA #$00
        RTS

; =============================================================================
; find_dead: dead_tbl[c] := 1 for every cell from which a box can never reach
; a target, whatever the pushes: the rule of tools/solver.py (Level.live).
; A box is pulled backwards from every target, breadth first: from c it
; goes to c+d when c+d and c+2d are not walls (the player steps back to
; c+2d). Cells never reached are dead; walls and the outside are never asked
; for. A level's floor never touches the grid edge (walls enclose it), so
; c+d and c+2d stay inside the 240 cells. ~45 ms; once per init_level.
; Clobbers A, X, Y.
; =============================================================================
find_dead:
        LDY #$00                        ; queue length
        LDX #STATE_GRID_LEN-1
@init:  LDA #$01
        STA dead_tbl,X
        LDA STATE_GRID,X
        CMP #TILE_TARGET
        BEQ @goal
        CMP #TILE_BOX_TARGET
        BEQ @goal
        CMP #TILE_PLAYER_TARGET
        BNE @nxt
@goal:  LDA #$00                        ; targets are live: they start the queue
        STA dead_tbl,X
        TXA
        STA dead_q,Y
        INY
@nxt:   DEX
        CPX #$FF
        BNE @init
        STY dq_tail
        LDA #$00
        STA dq_head
@pop:   LDY dq_head
        CPY dq_tail
        BEQ @done
        LDA dead_q,Y
        STA dq_cell
        INC dq_head
        LDY #3                          ; four directions
@dir:   LDA dq_cell
        CLC
        ADC dead_off,Y                  ; to = c + d
        STA dq_to
        TAX
        LDA dead_tbl,X
        BEQ @skip                       ; live already
        LDA STATE_GRID,X
        CMP #TILE_WALL
        BEQ @skip
        TXA
        CLC
        ADC dead_off,Y                  ; room = c + 2d, for the player
        TAX
        LDA STATE_GRID,X
        CMP #TILE_WALL
        BEQ @skip
        LDX dq_to                       ; live: queue it
        LDA #$00
        STA dead_tbl,X
        TXA
        LDX dq_tail
        STA dead_q,X
        INC dq_tail
@skip:  DEY
        BPL @dir
        JMP @pop
@done:  RTS

dead_off:       .byte <-NCOLS, NCOLS, <-1, 1

; =============================================================================
; History ring: hist[hist_pos] is the next free slot; the undo_n moves
; before it can be undone, the redo_n moves from it on can be redone.
; =============================================================================
; hist_put: store A at hist_pos, then advance. Clobbers A, Y.
hist_put:
        PHA
        JSR hist_ptr
        PLA
        LDY #$00
        STA (hptr_lo),Y
        ; fall through
; hist_advance: hist_pos++ (mod HIST_LEN), undo_n++ (saturates at HIST_LEN:
; the oldest move is then forgotten).
hist_advance:
        INC hist_pos_lo
        BNE @pos_ok
        LDA hist_pos_hi
        CLC
        ADC #$01
        AND #>(HIST_LEN - 1)
        STA hist_pos_hi
@pos_ok:
        LDA undo_n_hi
        CMP #>HIST_LEN
        BEQ @full
        INC undo_n_lo
        BNE @full
        INC undo_n_hi
@full:  RTS

; hist_ptr: hptr = hist + hist_pos.
hist_ptr:
        LDA hist_pos_lo
        CLC
        ADC #<hist
        STA hptr_lo
        LDA hist_pos_hi
        ADC #>hist
        STA hptr_hi
        RTS

; =============================================================================
; execute_undo: take back the last move of the history. Returns A = 1 (Z
; clear) if a move was undone, A = 0 if there was nothing to undo.
; =============================================================================
execute_undo:
        LDA undo_n_lo
        ORA undo_n_hi
        BNE @go
        JSR bump_sound
        LDA #$00
        RTS
@go:
        ; hist_pos--, undo_n--, redo_n++
        LDA hist_pos_lo
        BNE @p_lo
        LDA hist_pos_hi
        SEC
        SBC #$01
        AND #>(HIST_LEN - 1)
        STA hist_pos_hi
@p_lo:  DEC hist_pos_lo
        LDA undo_n_lo
        BNE @u_lo
        DEC undo_n_hi
@u_lo:  DEC undo_n_lo
        INC redo_n_lo
        BNE @r_ok
        INC redo_n_hi
@r_ok:
        JSR hist_ptr
        LDY #$00
        LDA (hptr_lo),Y
        STA temp2                       ; history code
        AND #$03
        TAX
        LDA dir_dy_tbl,X
        STA dir_dy
        LDA dir_dx_tbl,X
        STA dir_dx
        LDA #$00
        STA dirty_n

        ; previous player cell = player - d
        LDA player_row
        SEC
        SBC dir_dy
        STA new_row
        LDA player_col
        SEC
        SBC dir_dx
        STA new_col

        LDA temp2
        AND #HIST_PUSH
        BEQ @no_box

        ; the box at player + d comes back onto the player's cell
        LDA player_row
        CLC
        ADC dir_dy
        STA box_row
        STA draw_row
        LDA player_col
        CLC
        ADC dir_dx
        STA box_col
        STA draw_col
        LDY box_row
        LDX box_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        CMP #TILE_BOX
        BNE @was_on
        DEC boxes_left
@was_on:
        JSR leave_tile
        STA STATE_GRID,X
        JSR queue_tile

        LDA pushes_lo
        BNE @pu_lo
        DEC pushes_hi
@pu_lo: DEC pushes_lo

@no_box:
        LDY player_row
        LDX player_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        JSR leave_tile
        STA STATE_GRID,X
        LDA temp2
        AND #HIST_PUSH
        BEQ @draw_cur
        LDA STATE_GRID,X
        JSR enter_as_box
        STA STATE_GRID,X
        CMP #TILE_BOX
        BNE @draw_cur
        INC boxes_left
@draw_cur:
        LDA player_row
        STA draw_row
        LDA player_col
        STA draw_col
        JSR queue_tile

        LDY new_row
        LDX new_col
        JSR cell_index
        TAX
        LDA STATE_GRID,X
        JSR enter_player
        STA STATE_GRID,X
        LDA new_row
        STA player_row
        STA draw_row
        LDA new_col
        STA player_col
        STA draw_col
        JSR queue_tile

        LDA moves_lo
        BNE @mv_lo
        DEC moves_hi
@mv_lo: DEC moves_lo

        LDA #1
        STA position_dirty
        JSR flush_dirty
        JSR draw_hud
        LDA quiet
        BNE @q
        JSR sound_enabled
        BEQ @q
        LDA SPKR
@q:     LDA #$01
        RTS

; =============================================================================
; execute_redo: replay the move at hist_pos. Returns A = 1 if replayed.
; =============================================================================
execute_redo:
        LDA redo_n_lo
        ORA redo_n_hi
        BNE @go
        JSR bump_sound
        LDA #$00
        RTS
@go:    JSR hist_ptr
        LDY #$00
        LDA (hptr_lo),Y
        AND #$03
        STA dir_code
        LDA #$01
        STA replaying
        JSR execute_move                ; cannot be blocked: it was played
        LDX #$00
        STX replaying
        RTS

dir_dy_tbl: .byte $FF, $01, $00, $00    ; DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT
dir_dx_tbl: .byte $00, $00, $FF, $01

; =============================================================================
; HUD: moves top left, pushes top right, levels bottom left, record bottom
; right (once solved). 7-pixel glyphs, one per byte column; nothing is drawn
; while quiet.
; =============================================================================
draw_hud:
        LDA quiet
        BEQ @draw
        RTS
@draw:
        LDA #1
        STA num_step
        LDA #0
        STA num_sl
        LDA #HUD_LEFT
        STA num_col
        LDA #<str_moves
        STA sptr_lo
        LDA #>str_moves
        STA sptr_hi
        JSR draw_str
        LDA #HUD_LEFT
        STA num_col
        LDA #8
        STA num_sl
        LDA moves_lo
        STA num_lo
        LDA moves_hi
        STA num_hi
        LDA #4
        JSR print_num

        LDA #HUD_RIGHT
        STA num_col
        LDA #0
        STA num_sl
        LDA #<str_pushes
        STA sptr_lo
        LDA #>str_pushes
        STA sptr_hi
        JSR draw_str
        LDA #HUD_RIGHT
        STA num_col
        LDA #8
        STA num_sl
        LDA pushes_lo
        STA num_lo
        LDA pushes_hi
        STA num_hi
        LDA #5
        JSR print_num

        LDA #176
        STA num_sl
        LDA #HUD_LEFT
        STA num_col
        LDA #<str_levels
        STA sptr_lo
        LDA #>str_levels
        STA sptr_hi
        JSR draw_str
        LDA #184                       ; "III:001": collection, original number
        STA num_sl
        LDA #HUD_LEFT
        STA num_col
        LDA tutorial_on
        BEQ @normal_level
        LDA #G_T
        JSR put_glyph
        LDA #G_COLON
        JSR put_glyph
        LDA tutorial_idx
        CLC
        ADC #1
        STA num_lo
        LDA #0
        STA num_hi
        LDA #3
        JMP print_num
@normal_level:
        LDX cur_coll
        LDA coll_hud_lo,X
        STA sptr_lo
        LDA coll_hud_hi,X
        STA sptr_hi
        JSR draw_str
        LDA #G_COLON
        JSR put_glyph
        JSR orig_number
        STA num_lo
        LDA #$00
        STA num_hi
        LDA #3
        JSR print_num

        JSR slot_cur                    ; "B:0033": best moves, if solved
        LDY #$00
        LDA (sptr_lo),Y
        STA num_lo
        INY
        LDA (sptr_lo),Y
        STA num_hi
        ORA num_lo
        BEQ @none
        LDA #HUD_BOT_SL
        STA num_sl
        LDA #HUD_RIGHT
        STA num_col
        LDA #G_B
        JSR put_glyph
        LDA #G_COLON
        JSR put_glyph
        LDA #4
        JMP print_num
@none:  RTS

; orig_number: A = original number of level (cur_coll, cur_lvl).
orig_number:
        LDX cur_coll
        LDY cur_lvl
; orig_of: A = original number of level Y of collection X.
orig_of:
        LDA coll_orig_lo,X
        STA sptr_lo
        LDA coll_orig_hi,X
        STA sptr_hi
        LDA (sptr_lo),Y
        RTS

; =============================================================================
; Text. Glyphs are 7x8, one byte column; the cursor is (num_col, num_sl) and
; num_step the advance: 1 = packed (HUD), 2 = the 14-pixel screen spacing,
; 8 = compact screen text (num_col is then a pixel column).
;   put_glyph   draw glyph A, advance
;   draw_str    the $FF-terminated glyph string at sptr
;   print_num   num_hi:num_lo as A digits (1..5, leading zeros; 4 digits
;               are capped at 9999). Clobbers num.
; TEXT col, sl, string: set the cursor and draw a string, at the current
; num_step.
; =============================================================================
.macro TEXT col, sl, str
        LDA #col
        STA num_col
        LDA #sl
        STA num_sl
        LDA #<str
        STA sptr_lo
        LDA #>str
        STA sptr_hi
        JSR draw_str
.endmacro

put_glyph:
        LDX num_col
        LDY num_sl
        PHA
        LDA num_step
        CMP #8
        BEQ @compact
        PLA
        JSR draw_title_glyph
        JMP @advance
@compact:
        PLA
        JSR draw_compact_glyph
@advance:
        LDA num_col
        CLC
        ADC num_step
        STA num_col
        RTS

draw_str:
        LDY #$00
        STY str_ix
@lp:    LDY str_ix
        LDA (sptr_lo),Y
        CMP #$FF
        BEQ @done
        JSR put_glyph
        INC str_ix
        BNE @lp
@done:  RTS

print_num:
        STA num_pow
        CMP #4
        BNE @index
        LDA num_hi                      ; 4 digits: cap at 9999 = $270F
        CMP #>10000
        BCC @index
        BNE @cap
        LDA num_lo
        CMP #<10000
        BCC @index
@cap:   LDA #<9999
        STA num_lo
        LDA #>9999
        STA num_hi
@index: LDA #5                          ; power index = 5 - digits (0 = 10000)
        SEC
        SBC num_pow
        STA num_pow
@digits:
        LDX num_pow
        CPX #$04
        BCS @last
        LDY #$00                        ; digit = how many times pow fits
@sub:   LDA num_lo
        SEC
        SBC pow10_lo,X
        STA temp2
        LDA num_hi
        SBC pow10_hi,X
        BCC @put
        STA num_hi
        LDA temp2
        STA num_lo
        INY
        BNE @sub
@put:   TYA                             ; digit glyphs are 0..9
        JSR put_glyph
        INC num_pow
        JMP @digits
@last:  LDA num_lo                      ; units
        JMP put_glyph

pow10_lo: .byte <10000, <1000, <100, <10
pow10_hi: .byte >10000, >1000, >100, >10

; --- HUD/title font (Beautiful Boot subset, bit 0 = left pixel) ---
.include "bbfont_subset.inc"
hud_font = HGR_MicroSokoban_bbfont

; --- 2x doubling tables for draw_big_glyph ---
double_lo:
        .byte $00, $03, $0C, $0F, $30, $33, $3C, $3F
        .byte $40, $43, $4C, $4F, $70, $73, $7C, $7F
double_hi:
        .byte $00, $01, $06, $07, $18, $19, $1E, $1F
        .byte $60, $61, $66, $67, $78, $79, $7E, $7F

; =============================================================================
; Title / help / success screens — table driven.
; Entry = str_lo, str_hi, column, scanline, style (0 small, 1 big white,
; 2 big orange, 3 compact white; only doubled text may be tinted).
; Column is in bytes except compact styles (pixels).
; $FFFF ends (a string address may legitimately end in $FF).
; =============================================================================
draw_title:
        LDA #<title_table
        STA tbl_lo
        LDA #>title_table
        STA tbl_hi
        JSR draw_from_table
        LDA #$00                        ; wall band along the top
        STA draw_row
        STA draw_col
@band:  LDA #TILE_WALL
        JSR draw_tile
        INC draw_col
        LDA draw_col
        CMP #NCOLS
        BCC @band
        JSR draw_screen_sides

; The loading status overlaps the full-width lower wall. Redraw this part
; after the initial disk loads have finished and the status has been erased.
draw_title_warehouse:
        LDX #$00                        ; full-width walls above and below the
@box:   STX draw_col                    ; corridor of row TITLE_ROW
        LDA #TITLE_ROW-1
        STA draw_row
        LDA #TILE_WALL
        JSR draw_tile
        LDA #TITLE_ROW+1
        STA draw_row
        LDA #TILE_WALL
        JSR draw_tile
        LDX draw_col
        INX
        CPX #NCOLS
        BCC @box
        LDA #TITLE_ROW
        STA draw_row
        LDA #$00
        STA draw_col
        LDA #TILE_WALL
        JSR draw_tile
        LDA #NCOLS-1
        STA draw_col
        LDA #TILE_WALL
        JSR draw_tile
        LDA #$00
        STA title_phase
        LDA #$01
        STA title_blink
        JMP draw_title_corridor

; title_step: next phase of the silent title animation; "KEY OR BUTTON"
; blinks. Both the title animation and the attract-mode levels are silent.
title_step:
        INC title_phase
        LDA title_phase
        CMP #TITLE_PHASES
        BCC @ph
        LDA #$00
        STA title_phase
@ph:    JSR draw_title_corridor
        LDA title_blink
        EOR #$01
        STA title_blink
        LDA #8
        STA num_step
        LDA title_blink
        BEQ @off
        TEXT TITLE_PRESS_COL, TITLE_PRESS_SL, title_press
        RTS
@off:   TEXT TITLE_PRESS_COL, TITLE_PRESS_SL, title_nopress
        RTS

; draw_title_corridor: the full-width corridor of phase title_phase. Clamp
; the final phases to the solved position; the next cycle starts at the left.
draw_title_corridor:
        LDA title_phase
        CMP #TITLE_PUSHES
        BCC @position
        LDA #TITLE_PUSHES
@position:
        CLC
        ADC #TITLE_COL
        STA title_player_col
        LDA #TITLE_ROW
        STA draw_row
        LDA #TITLE_COL
        STA draw_col
@cell:  LDA draw_col
        CMP title_player_col
        BEQ @player
        SEC
        SBC #1
        CMP title_player_col
        BEQ @box
        LDA draw_col
        CMP #TITLE_TARGET_COL
        BEQ @target
        LDA #TILE_FLOOR
        JMP @draw
@player:
        LDA #TILE_PLAYER
        BNE @draw
@box:   LDA draw_col
        CMP #TITLE_TARGET_COL
        BEQ @placed
        LDA #TILE_BOX
        BNE @draw
@placed:
        LDA #TILE_BOX_TARGET
        BNE @draw
@target:
        LDA #TILE_TARGET
@draw:
        JSR draw_tile
        INC draw_col
        LDA draw_col
        CMP #TITLE_TARGET_COL+1
        BCC @cell
        RTS


; draw_title_info: "SOLVED nnn/NNN" (levels with a record, all collections)
; and "CONTINUE III:056" (the level play resumes at), centred.
draw_title_info:
        LDA #$00
        STA all_solved_lo
        STA all_solved_hi
        STA title_ix
@coll:  LDA title_ix
        STA sel_coll
        JSR coll_totals
        LDA all_solved_lo
        CLC
        ADC tot_solved
        STA all_solved_lo
        BCC @nc
        INC all_solved_hi
@nc:    INC title_ix
        LDA title_ix
        CMP #NUM_COLLS
        BCC @coll
        LDA #8
        STA num_step
        TEXT 84, 62, str_solved         ; 14 compact glyphs, centred
        LDA all_solved_lo
        STA num_lo
        LDA all_solved_hi
        STA num_hi
        LDA #3
        JSR print_num
        LDA #G_SLASH
        JSR put_glyph
        LDA #<TOTAL_LEVELS
        STA num_lo
        LDA #>TOTAL_LEVELS
        STA num_hi
        LDA #3
        JSR print_num
        LDX cur_coll                    ; "CONTINUE " + name + ":NNN",
        LDA coll_hud_lo,X               ; 13 glyphs + the name: from
        STA sptr_lo                     ; pixel column 88 - 4 * name length
        LDA coll_hud_hi,X
        STA sptr_hi
        LDY #$FF
@len:   INY
        LDA (sptr_lo),Y
        CMP #$FF
        BNE @len
        TYA
        ASL A
        ASL A
        STA temp
        LDA #88
        SEC
        SBC temp
        STA num_col
        LDA #74
        STA num_sl
        LDA #<title_continue
        STA sptr_lo
        LDA #>title_continue
        STA sptr_hi
        JSR draw_str
        LDX cur_coll
        LDA coll_hud_lo,X
        STA sptr_lo
        LDA coll_hud_hi,X
        STA sptr_hi
        JSR draw_str
        LDA #G_COLON
        JSR put_glyph
        JSR orig_number
        STA num_lo
        LDA #$00
        STA num_hi
        LDA #3
        JSR print_num
        JMP draw_title_profile

; Blue bricks join the existing title bands along both screen edges.
draw_screen_sides:
        LDA #0
        STA draw_row
@row:   LDA #0
        STA draw_col
        LDA #TILE_WALL
        JSR draw_tile
        LDA #NCOLS-1
        STA draw_col
        LDA #TILE_WALL
        JSR draw_tile
        INC draw_row
        LDA draw_row
        CMP #NROWS
        BCC @row
        RTS

draw_menu:
        LDA #<menu_table
        STA tbl_lo
        LDA #>menu_table
        STA tbl_hi
        JSR draw_from_table
        JSR draw_screen_sides
        LDA #32
        JSR draw_profile_name
        JSR cheat_on
        BEQ @nosol
        LDA #8
        STA num_step
        TEXT MENU_TEXT_COL, MENU_SL0+MENU_SOLUTION*MENU_DY, menu_solution
@nosol: RTS

draw_help:
        LDA #<help_table
        STA tbl_lo
        LDA #>help_table
        STA tbl_hi
        JSR draw_from_table
        JMP draw_screen_sides

; Success card: compact statistics, best record and levels solved.
draw_success:
        LDA #<success_table
        STA tbl_lo
        LDA #>success_table
        STA tbl_hi
        JSR draw_from_table
        JSR draw_screen_sides
        LDA #184
        STA num_col
        LDA #72
        STA num_sl
        LDA moves_lo
        STA num_lo
        LDA moves_hi
        STA num_hi
        LDA #4
        JSR print_num
        LDA #184
        STA num_col
        LDA #92
        STA num_sl
        LDA pushes_lo
        STA num_lo
        LDA pushes_hi
        STA num_hi
        LDA #4
        JSR print_num
        LDA tutorial_on
        BNE @score
        LDA new_record
        BEQ @old
        TEXT 100, 116, str_new_record
        JMP @score
@old:   TEXT 64, 116, str_record
        LDA #184
        STA num_col
        LDA best_lo
        STA num_lo
        LDA best_hi
        STA num_hi
        LDA #4
        JSR print_num
@score: TEXT 64, 140, str_levels
        LDA #184
        STA num_col
        LDA score_solved
        STA num_lo
        LDA score_solved+1
        STA num_hi
        LDA #3
        JMP print_num

; =============================================================================
; end_screen: after the last level of a collection -- how many levels have
; a record, and the sum of the records (moves, pushes).
; =============================================================================
end_screen:
        LDA cur_coll
        STA sel_coll
        JSR coll_totals
        JSR begin_screen
        LDA #<end_table
        STA tbl_lo
        LDA #>end_table
        STA tbl_hi
        JSR draw_from_table
        LDA #2
        STA num_step
        LDA #56                         ; "MICROBAN" + collection
        STA num_sl
        LDA #26
        STA num_col
        LDX cur_coll
        LDA coll_hud_lo,X
        STA sptr_lo
        LDA coll_hud_hi,X
        STA sptr_hi
        JSR draw_str
        LDA #84                         ; solved / levels
        STA num_sl
        LDA #20
        STA num_col
        JSR print_solved
        LDA #100
        STA num_sl
        LDA #20
        STA num_col
        LDA tot_moves_lo
        STA num_lo
        LDA tot_moves_hi
        STA num_hi
        LDA #5
        JSR print_num
        LDA #116
        STA num_sl
        LDA #20
        STA num_col
        LDA tot_pushes_lo
        STA num_lo
        LDA tot_pushes_hi
        STA num_hi
        LDA #5
        JSR print_num
        JSR show_screen
        JSR play_fanfare
        JMP wait_any

; print_solved: "NNN/NNN", levels with a record / levels of sel_coll.
print_solved:
        LDA tot_solved
        STA num_lo
        LDA #$00
        STA num_hi
        LDA #3
        JSR print_num
        LDA #G_SLASH
        JSR put_glyph
        LDX sel_coll
        LDA coll_count,X
        STA num_lo
        LDA #$00
        STA num_hi
        LDA #3
        JMP print_num

; coll_totals: over collection sel_coll, tot_solved = levels with a record,
; tot_moves / tot_pushes = sums of the records (saturating at 65535).
coll_totals:
        LDA #$00
        STA tot_solved
        STA tot_moves_lo
        STA tot_moves_hi
        STA tot_pushes_lo
        STA tot_pushes_hi
        STA tot_i
@lp:    LDX sel_coll
        LDA tot_i
        JSR slot_ptr
        LDY #$00
        LDA (sptr_lo),Y
        INY
        ORA (sptr_lo),Y
        BEQ @next
        INC tot_solved
        LDY #$00
        CLC
        LDA tot_moves_lo
        ADC (sptr_lo),Y
        STA tot_moves_lo
        INY
        LDA tot_moves_hi
        ADC (sptr_lo),Y
        STA tot_moves_hi
        BCC @m_ok
        LDA #$FF
        STA tot_moves_lo
        STA tot_moves_hi
@m_ok:  INY
        CLC
        LDA tot_pushes_lo
        ADC (sptr_lo),Y
        STA tot_pushes_lo
        INY
        LDA tot_pushes_hi
        ADC (sptr_lo),Y
        STA tot_pushes_hi
        BCC @next
        LDA #$FF
        STA tot_pushes_lo
        STA tot_pushes_hi
@next:  INC tot_i
        LDX sel_coll
        LDA tot_i
        CMP coll_count,X
        BCC @lp
        RTS

; =============================================================================
; run_select: level selection. Pages of 10 x 8 original numbers, levels with
; a record underlined in green, the cursor in inverse video. Stick / IJKL
; move, N / P change collection, RETURN / button 0 plays, ESC / button 1
; goes back. Returns C = 1 with cur_coll / cur_lvl set, C = 0 on ESC.
; =============================================================================
run_select:
        LDA cur_coll
        STA sel_coll
        LDA cur_lvl
        STA sel_idx
@page:  LDA #$00                        ; sel_first = the page of sel_idx
        STA sel_first
@pf:    LDA sel_idx
        SEC
        SBC sel_first
        CMP #SEL_PAGE
        BCC @pf_ok
        LDA sel_first
        CLC
        ADC #SEL_PAGE
        STA sel_first
        BNE @pf
@pf_ok: JSR draw_select
@cur:   LDA sel_idx
        STA sel_prev
        JSR sel_cursor
@loop:  JSR get_input
        BEQ @loop
        CMP #ACT_SELECT
        BEQ @pick
        CMP #ACT_MENU
        BEQ @cancel
        CMP #ACT_UNDO
        BNE @keys
        LDX in_src                      ; button 0 picks, the U key does not
        BNE @pick
        BEQ @loop
@keys:  LDX sel_coll
        CMP #ACT_LEFT
        BEQ @left
        CMP #ACT_RIGHT
        BEQ @right
        CMP #ACT_UP
        BEQ @up
        CMP #ACT_DOWN
        BEQ @down
        CMP #ACT_NEXT
        BEQ @next_coll
        CMP #ACT_PREV
        BEQ @prev_coll
        JMP @loop
@pick:  LDA sel_coll
        STA cur_coll
        LDA sel_idx
        STA cur_lvl
        SEC
        RTS
@cancel:
        CLC
        RTS
@left:  LDA sel_idx
        BEQ @loop
        DEC sel_idx
        JMP @moved
@right: LDA sel_idx
        CLC
        ADC #$01
        CMP coll_count,X
        BCS @loop
        STA sel_idx
        JMP @moved
@up:    LDA sel_idx
        SEC
        SBC #SEL_COLS
        BCC @loop
        STA sel_idx
        JMP @moved
@down:  LDA sel_idx
        CLC
        ADC #SEL_COLS
        CMP coll_count,X
        BCS @loop
        STA sel_idx
        JMP @moved
@next_coll:
        INX
        CPX #NUM_COLLS
        BCC @coll
        LDX #$00
        BEQ @coll
@prev_coll:
        DEX
        BPL @coll
        LDX #NUM_COLLS-1
@coll:  STX sel_coll
        LDA #$00
        STA sel_idx
        JMP @page
@moved: LDA sel_idx                     ; still on this page?
        SEC
        SBC sel_first
        CMP #SEL_PAGE
        BCS @new_page                   ; (below sel_first wraps high too)
        LDA sel_prev                    ; erase the old cursor
        JSR sel_cursor_at
        JMP @cur
@new_page:
        JMP @page

; sel_cursor(_at): EOR the cell of level sel_idx (A) on the page on screen.
sel_cursor:
        LDA sel_idx
sel_cursor_at:
        SEC
        SBC sel_first
        LDX #$00                        ; X = row, A = column
@div:   CMP #SEL_COLS
        BCC @rc
        SBC #SEL_COLS
        INX
        BNE @div
@rc:    ASL A
        ASL A
        STA temp                        ; byte column = 4 * column
        LDA #SEL_SL0 - 1
@row:   DEX
        BMI @sl
        CLC
        ADC #SEL_DY
        BNE @row
@sl:    STA temp2
        LDA #10
        STA str_ix                      ; lines left
@ln:    LDY temp2
        LDA hgr_lo,Y
        CLC
        ADC temp
        STA ptr_lo
        LDA hgr_hi,Y
        ADC #$00
        STA ptr_hi
        LDY #$02
@b:     LDA (ptr_lo),Y
        EOR #$7F
        STA (ptr_lo),Y
        DEY
        BPL @b
        INC temp2
        DEC str_ix
        BNE @ln
        RTS

; draw_select: header (collection, levels solved), the page of numbers,
; help line; drawn on the hidden page, then shown.
draw_select:
        JSR begin_screen
        JSR coll_totals
        LDA #1
        STA num_step
        TEXT 0, 4, str_microban
        LDX sel_coll
        LDA coll_hud_lo,X
        STA sptr_lo
        LDA coll_hud_hi,X
        STA sptr_hi
        JSR draw_str
        TEXT 19, 4, str_solved
        JSR print_solved
        TEXT 0, HUD_BOT_SL, str_sel_help

        LDA #$00
        STA tot_i                       ; cell 0..79
        LDA #$00
        STA sel_c
        LDA #SEL_SL0
        STA sel_sl
@cell:  LDA sel_first
        CLC
        ADC tot_i
        LDX sel_coll
        CMP coll_count,X
        BCS @shown
        STA sel_lvl
        TAY
        JSR orig_of                     ; X = collection
        STA num_lo
        LDA #$00
        STA num_hi
        LDA sel_c
        ASL A
        ASL A
        STA num_col
        LDA sel_sl
        STA num_sl
        LDA #3
        JSR print_num
        LDX sel_coll                    ; solved: green line under the number
        LDA sel_lvl
        JSR slot_ptr
        LDY #$00
        LDA (sptr_lo),Y
        INY
        ORA (sptr_lo),Y
        BEQ @next
        LDA sel_sl
        CLC
        ADC #9
        JSR sel_bar
        LDA sel_sl
        CLC
        ADC #10
        JSR sel_bar
@next:  INC tot_i
        INC sel_c
        LDA sel_c
        CMP #SEL_COLS
        BCC @same
        LDA #$00
        STA sel_c
        LDA sel_sl
        CLC
        ADC #SEL_DY
        STA sel_sl
@same:  LDA tot_i
        CMP #SEL_PAGE
        BCC @cell
@shown: JMP show_screen

; sel_bar: a green line on scanline A under the number of column sel_c
; (green = odd pixels, bit 7 clear: $2A on an even byte column, $55 on an
; odd one).
sel_bar:
        TAY
        LDA sel_c
        ASL A
        ASL A
        CLC
        ADC hgr_lo,Y
        STA ptr_lo
        LDA hgr_hi,Y
        ADC #$00
        STA ptr_hi
        LDY #$00
        LDA #$2A
        STA (ptr_lo),Y
        INY
        LDA #$55
        STA (ptr_lo),Y
        INY
        LDA #$2A
        STA (ptr_lo),Y
        RTS

draw_from_table:
@entry:
        LDY #$00
        LDA (tbl_lo),Y
        CMP #$FF
        BNE @pointer
        INY
        LDA (tbl_lo),Y
        CMP #$FF
        BEQ @done
        DEY
        LDA (tbl_lo),Y
@pointer:
        STA sptr_lo
        INY
        LDA (tbl_lo),Y
        STA sptr_hi
        INY
        LDA (tbl_lo),Y
        STA title_col_start
        INY
        LDA (tbl_lo),Y
        STA title_scanline
        INY
        LDA (tbl_lo),Y
        CMP #STYLE_COMPACT
        BCS @compact
        CMP #$00
        BEQ @small
        SEC                             ; 1 = big white, 2 = big orange
        SBC #1
        BEQ @big
        LDA #COLOR_ORANGE
@big:
        STA big_color
        JSR draw_title_big_line
        JMP @next
@small:
        JSR draw_title_line
        JMP @next
@compact:
        LDA #8
        STA num_step
        LDA title_col_start
        STA num_col
        LDA title_scanline
        STA num_sl
        JSR draw_str
@next:
        LDA tbl_lo
        CLC
        ADC #$05
        STA tbl_lo
        BCC @entry
        INC tbl_hi
        JMP @entry
@done:
        RTS

; Title small lines: 8 px per glyph; pixel column = (280 - n * 8) / 2.
title_table:
        .byte <title_micro_sokoban,  >title_micro_sokoban,  $07, 20, $02     ; big, orange
        .byte <title_levels,   >title_levels,   60+LEVELS_TITLE_COL*4, 42, STYLE_COMPACT
        .byte <title_skinner,  >title_skinner,  64, 88, STYLE_COMPACT
        .byte <title_author,   >title_author,   80, 100, STYLE_COMPACT
        .byte <title_porter,   >title_porter,   84, 112, STYLE_COMPACT
        .byte <title_press,    >title_press,    TITLE_PRESS_COL, TITLE_PRESS_SL, STYLE_COMPACT
        .byte <title_h_help,   >title_h_help,   28, 136, STYLE_COMPACT
        .word $FFFF

; Help: controls in two columns, then a separate compact MENU block.
help_table:
        .byte <help_big_title, >help_big_title,16,8,2
        .byte <help_goal,>help_goal,44,40,STYLE_COMPACT
        .byte <help_movement,>help_movement,32,64,STYLE_COMPACT
        .byte <help_move,>help_move,32,80,STYLE_COMPACT
        .byte <help_move_keys,>help_move_keys,104,80,STYLE_COMPACT
        .byte <help_stick,>help_stick,104,92,STYLE_COMPACT
        .byte <help_history,>help_history,32,112,STYLE_COMPACT
        .byte <help_undo,>help_undo,32,128,STYLE_COMPACT
        .byte <help_undo_keys,>help_undo_keys,104,128,STYLE_COMPACT
        .byte <help_redo,>help_redo,32,140,STYLE_COMPACT
        .byte <help_redo_keys,>help_redo_keys,104,140,STYLE_COMPACT
        .byte <help_menu,>help_menu,32,160,STYLE_COMPACT
        .byte <help_menu_keys,>help_menu_keys,32,172,STYLE_COMPACT
        .byte <profiles_back,>profiles_back,96,184,STYLE_COMPACT
        .word $FFFF
menu_table:
        .byte <help_menu,>help_menu,16,8,2
        .byte <menu_tutorial,  >menu_tutorial,  MENU_TEXT_COL, MENU_SL0+MENU_TUTORIAL*MENU_DY, STYLE_COMPACT
        .byte <menu_key_tutorial,>menu_key_tutorial,MENU_KEY_COL,MENU_SL0+MENU_TUTORIAL*MENU_DY, STYLE_COMPACT
        .byte <menu_profiles, >menu_profiles,MENU_TEXT_COL,MENU_SL0+MENU_PROFILE*MENU_DY,STYLE_COMPACT
        .byte <menu_key_profiles,>menu_key_profiles,MENU_KEY_COL,MENU_SL0+MENU_PROFILE*MENU_DY,STYLE_COMPACT
        .byte <menu_resume,    >menu_resume,    MENU_TEXT_COL, MENU_SL0+MENU_RESUME*MENU_DY, STYLE_COMPACT
        .byte <menu_key_resume,>menu_key_resume,MENU_KEY_COL,  MENU_SL0+MENU_RESUME*MENU_DY, STYLE_COMPACT
        .byte <menu_reset,     >menu_reset,     MENU_TEXT_COL, MENU_SL0+MENU_RESET*MENU_DY, STYLE_COMPACT
        .byte <menu_key_reset, >menu_key_reset, MENU_KEY_COL,  MENU_SL0+MENU_RESET*MENU_DY, STYLE_COMPACT
        .byte <menu_goto,      >menu_goto,      MENU_TEXT_COL, MENU_SL0+MENU_GOTO*MENU_DY, STYLE_COMPACT
        .byte <menu_key_goto,  >menu_key_goto,  MENU_KEY_COL,  MENU_SL0+MENU_GOTO*MENU_DY, STYLE_COMPACT
        .byte <menu_options,   >menu_options,   MENU_TEXT_COL, MENU_SL0+MENU_OPTIONS*MENU_DY, STYLE_COMPACT
        .byte <menu_key_options,>menu_key_options,MENU_KEY_COL,MENU_SL0+MENU_OPTIONS*MENU_DY, STYLE_COMPACT
        .byte <menu_hof,       >menu_hof,       MENU_TEXT_COL, MENU_SL0+MENU_HOF*MENU_DY, STYLE_COMPACT
        .byte <menu_key_hof,   >menu_key_hof,   MENU_KEY_COL,  MENU_SL0+MENU_HOF*MENU_DY, STYLE_COMPACT
        .byte <help_big_title,>help_big_title,MENU_TEXT_COL,MENU_SL0+MENU_HELP*MENU_DY,STYLE_COMPACT
        .byte <menu_key_help,>menu_key_help,MENU_KEY_COL,MENU_SL0+MENU_HELP*MENU_DY,STYLE_COMPACT
        .byte <menu_quit,      >menu_quit,      MENU_TEXT_COL, MENU_SL0+MENU_QUIT*MENU_DY, STYLE_COMPACT
        .byte <menu_key_quit,  >menu_key_quit,  MENU_KEY_COL,  MENU_SL0+MENU_QUIT*MENU_DY, STYLE_COMPACT
        .byte <profiles_back,>profiles_back,96,180,STYLE_COMPACT
        .word $FFFF

success_table:
        .byte <title_success,  >title_success,  13, 28, 2
        .byte <str_moves,      >str_moves,      64, 72, STYLE_COMPACT
        .byte <str_pushes,     >str_pushes,     64, 92, STYLE_COMPACT
        .byte <title_press,    >title_press,    88,168, STYLE_COMPACT
        .word $FFFF

end_table:
        .byte <str_bravo,      >str_bravo,      $0F, 20, $01
        .byte <str_microban,   >str_microban,   $08, 56, $00
        .byte <str_solved,     >str_solved,     $04, 84, $00
        .byte <str_moves,      >str_moves,      $04, 100, $00
        .byte <str_pushes,     >str_pushes,     $04, 116, $00
        .byte <title_press,    >title_press,    $07, 160, $00
        .word $FFFF

; draw_title_line: small glyphs, byte_col = title_col_start + ix*2.
draw_title_line:
        LDA #$00
        STA title_ix
@lp:
        LDY title_ix
        LDA (sptr_lo),Y
        CMP #$FF
        BEQ @done
        STA title_glyph
        TYA
        ASL A
        CLC
        ADC title_col_start
        TAX
        LDA title_glyph
        LDY title_scanline
        JSR draw_title_glyph
        INC title_ix
        JMP @lp
@done:
        RTS

; draw_title_big_line: 2x glyphs, 2 bytes wide each, packed back-to-back.
draw_title_big_line:
        LDA #$00
        STA title_ix
@lp:
        LDY title_ix
        LDA (sptr_lo),Y
        CMP #$FF
        BEQ @done
        STA title_glyph
        TYA
        ASL A
        CLC
        ADC title_col_start
        TAX
        LDA title_glyph
        LDY title_scanline
        JSR draw_big_glyph
        INC title_ix
        JMP @lp
@done:
        RTS

; set_hud_font_ptr: src = hud_font + glyph*8 (16-bit). Input A = glyph.
set_hud_font_ptr:
        LDX #$00
        STX src_hi
        ASL A
        ROL src_hi
        ASL A
        ROL src_hi
        ASL A
        ROL src_hi
        CLC
        ADC #<hud_font
        STA src_lo
        LDA src_hi
        ADC #>hud_font
        STA src_hi
        RTS

; draw_big_glyph: glyph at 2x in both directions (14 px x 16 lines).
; Input: A = glyph, X = byte_col, Y = start scanline.
draw_big_glyph:
        STX temp
        STY temp2
        JSR set_hud_font_ptr
        LDY #$00
        STY title_glyph
@row:
        LDY title_glyph
        LDA (src_lo),Y
        PHA
        AND #$0F
        TAX
        LDA double_lo,X
        STA big_byte0
        PLA
        LSR A
        LSR A
        LSR A
        AND #$0F
        TAX
        LDA double_hi,X
        STA big_byte1
        LDA big_color
        JSR color_glyph_pair
        TYA
        ASL A
        CLC
        ADC temp2
        TAX                             ; X = scanline

        LDA hgr_lo,X
        CLC
        ADC temp
        STA ptr_lo
        LDA hgr_hi,X
        ADC #$00
        STA ptr_hi
        LDY #$00
        LDA big_byte0
        STA (ptr_lo),Y
        INY
        LDA big_byte1
        STA (ptr_lo),Y

        INX
        LDA hgr_lo,X
        CLC
        ADC temp
        STA ptr_lo
        LDA hgr_hi,X
        ADC #$00
        STA ptr_hi
        LDY #$00
        LDA big_byte0
        STA (ptr_lo),Y
        INY
        LDA big_byte1
        STA (ptr_lo),Y

        LDY title_glyph
        INY
        STY title_glyph
        CPY #$08
        BCS @end
        JMP @row
@end:   RTS

; Shared eight-pixel masked cell at an arbitrary pixel column.
draw_compact_glyph:
        .globalzp hg_x
        STX hg_x
        STY temp2
        LDX #0
        STX hg_x+1
        JSR set_hud_font_ptr
        JMP hgr_glyph8_cell

hg_src = src_lo
hg_ptr = ptr_lo
hg_col = temp
hg_y = temp2
hg_lo = big_byte0
hg_hi = big_byte1
HG_STORE_UNCLIPPED = 1            ; byte-aligned titles stay within the screen
.include "hgr_glyph8.asm"

; Tint two raster bytes using absolute pixel parity and HGR phase.
; Preserve Y (font row), temp (byte column) and temp2 (scanline).
color_glyph_pair:
        BEQ @done                       ; white keeps both adjacent pixels
        STA glyph_color
        AND #1
        ASL A
        STA glyph_mask_index
        LDA temp
        AND #1
        ORA glyph_mask_index
        TAX
        LDA big_byte0
        AND glyph_masks,X
        STA big_byte0
        TXA
        EOR #1
        TAX
        LDA big_byte1
        AND glyph_masks,X
        STA big_byte1
        LDA glyph_color
        CMP #COLOR_ORANGE
        BCC @done
        LDA big_byte0
        ORA #$80
        STA big_byte0
        LDA big_byte1
        ORA #$80
        STA big_byte1
@done:  RTS
glyph_masks: .byte $55, $2A, $2A, $55

; Shared byte-aligned white glyph.
draw_title_glyph:
        STX temp
        STY temp2
        JSR set_hud_font_ptr
        JMP hgr_glyph8_store

; --- Strings: glyph indices, $FF terminated (GSTR, see bbfont_subset.inc) ---
title_micro_sokoban:  GSTR "MICRO-SOKOBAN"
title_levels:   LEVELS_TITLE
title_skinner:  GSTR "BY DAVID W. SKINNER"
title_author:   GSTR "APPLE II PORT BY"
title_porter:   GSTR "VERHILLE ARNAUD"
title_press:    GSTR "KEY OR BUTTON"
title_nopress:  GSTR "             "
title_continue: GSTR "CONTINUE "
title_h_help:   GSTR "ESC MENU  H HELP  V PROFILES"
title_success:  GSTR "SUCCESS"
str_loading:    GSTR "LOADING"
str_saving:     GSTR " SAVING"
str_blank7:     GSTR "       "
str_moves:      GSTR "MOVES"
str_levels:     GSTR "LEVEL"
str_pushes:     GSTR "PUSHES"
str_record:     GSTR "RECORD"
str_new_record: GSTR "NEW RECORD"
str_bravo:      GSTR "BRAVO"
str_microban:   GSTR "MICROBAN "
str_solved:     GSTR "SOLVED "
str_score = str_moves           ; identical text, shared in the 48 KB resident
str_sel_help:   GSTR "RETURN PLAY   ESC BACK   N/P SET"

help_big_title: GSTR "HELP"
help_move:      GSTR "MOVE"
help_move_keys: GSTR "IJKL / WASD"
help_undo:      GSTR "UNDO"
help_undo_keys: GSTR "U / BUTTON 0"
help_redo:      GSTR "REDO"
help_redo_keys: GSTR "Y / B0 + RIGHT"
help_menu:      GSTR "MENU"
help_menu_keys: GSTR "ESC / BUTTON 1"
help_goal: GSTR "PUSH BOXES ON GREEN GOALS"
help_movement: GSTR "MOVEMENT"
help_history: GSTR "UNDO / REDO"
help_stick: GSTR "ARROWS / JOYSTICK"
menu_resume:    GSTR "PLAY / RESUME"
menu_reset:     GSTR "RESTART"
menu_goto:      GSTR "GO TO LEVEL"
menu_quit:      GSTR "QUIT TO DOS"
menu_hof:       GSTR "HALL OF FAME"
menu_key_resume:GSTR "(RET)"
menu_key_reset: GSTR "(R)"
menu_key_goto:  GSTR "(G)"
menu_key_options: GSTR "(O)"
menu_key_tutorial:GSTR "(T)"
menu_options:   GSTR "OPTIONS"
menu_tutorial:  GSTR "TUTORIAL (5)"
menu_profiles: GSTR "PROFILES"
menu_key_profiles: GSTR "(V)"
menu_key_help: GSTR "(H)"
menu_key_quit:  GSTR "(Q)"
menu_key_hof:   GSTR "(F)"
menu_solution:  GSTR "SOLUTION"

; =============================================================================
; Tile transitions
; =============================================================================
; leave_tile / enter_player / enter_as_box preserve X (cell index).
leave_tile:
        TAY
        LDA leave_tbl,Y
        RTS
enter_player:
        TAY
        LDA enter_player_tbl,Y
        RTS
enter_as_box:
        TAY
        LDA enter_box_tbl,Y
        RTS

leave_tbl:        .byte 0, 1, 2, 0, 2, 0, 2
enter_player_tbl: .byte 5, 0, 6, 0, 0, 0, 0
enter_box_tbl:    .byte 3, 0, 4, 0, 0, 0, 0

; =============================================================================
; Double buffering. All drawing goes through hgr_lo / hgr_hi, and hgr_hi is
; rewritten in place to address the draw page (set_draw_page), as Maze3D does.
;   begin_screen  draw page := the hidden page, cleared
;   show_screen   display the draw page; it stays the draw page, so the
;                 per-move tile updates land on the page on screen
; =============================================================================
; show_screen, set_draw_page and draw_page are dev/lib/hgr/hgr_flip.asm
; (hgr_show_draw, hgr_set_draw_page, hgr_draw_page, included below).
begin_screen:
        JSR hgr_draw_hidden
        JMP clear_draw_page

show_screen   = hgr_show_draw
set_draw_page = hgr_set_draw_page
draw_page     = hgr_draw_page

; clear_draw_page: zero the 8 KB of the draw page, using ptr_lo/ptr_hi (the
; compact loop: screens are cleared once per transition, bytes matter more).
clear_draw_page:
        LDA draw_page
        EOR #$20                        ; 0/$60 -> $20/$40
        STA ptr_hi
        LDA #$00
        STA ptr_lo
        TAY
        LDX #32
@page:  STA (ptr_lo),Y
        INY
        BNE @page
        INC ptr_hi
        DEX
        BNE @page
        RTS

; =============================================================================
; DATA
; =============================================================================
.data

; hgr_hi is rewritten by set_draw_page: it lives in DATA, not RODATA.
; HGR scanline address tables (Apple II interleave), page 1 at load time
.include "hgr_scanline.inc"      ; dev/lib/hgr: hgr_lo / hgr_hi
.include "hgr_flip.asm"          ; dev/lib/hgr: hgr_draw_hidden / hgr_show_draw /
                                 ; hgr_set_draw_page, draw page by rewriting hgr_hi

.rodata

row_x20:
        .byte   0,  20,  40,  60,  80, 100, 120, 140
        .byte 160, 180, 200, 220

; --- Tile bitmaps: 8 tiles x 16 scanlines x 2 bytes ---
; Colour on a real Apple II: tiles start on an even pixel column, so within a
; tile odd pixels are green (palette 0) / orange (bit 7 set), even pixels are
; violet / blue. A solid single colour is one bit in two; two adjacent bits
; make white.
;   byte 0 = pixels 0..6 (bit 0 leftmost), byte 1 = pixels 7..13.
;   odd-pixel colour (green/orange): byte0 bits 1,3,5 ($2A) byte1 bits 0,2,4,6 ($55)
tile_bitmaps:
; Tile 0: FLOOR (black)
        .byte $00,$00, $00,$00, $00,$00, $00,$00
        .byte $00,$00, $00,$00, $00,$00, $00,$00
        .byte $00,$00, $00,$00, $00,$00, $00,$00
        .byte $00,$00, $00,$00, $00,$00, $00,$00
; Tile 1: WALL — blue bricks (even pixels, bit 7 set), black mortar every
; 4th line. Blue keeps walls apart from the orange boxes.
        .byte $D5,$AA, $D5,$AA, $D5,$AA, $80,$80
        .byte $D5,$AA, $D5,$AA, $D5,$AA, $80,$80
        .byte $D5,$AA, $D5,$AA, $D5,$AA, $80,$80
        .byte $D5,$AA, $D5,$AA, $D5,$AA, $80,$80
; Tile 2: TARGET — small green square (pixels 3,5,7,9 on rows 5..10)
        .byte $00,$00, $00,$00, $00,$00, $00,$00
        .byte $00,$00, $28,$05, $28,$05, $28,$05
        .byte $28,$05, $28,$05, $28,$05, $00,$00
        .byte $00,$00, $00,$00, $00,$00, $00,$00
; Tile 3: BOX — white frame (rows 2,3,12,13; cols 2..11), orange body
        .byte $00,$00, $00,$00, $FC,$9F, $FC,$9F
        .byte $8C,$98, $A8,$95, $A8,$95, $A8,$95
        .byte $A8,$95, $A8,$95, $A8,$95, $8C,$98
        .byte $FC,$9F, $FC,$9F, $00,$00, $00,$00
; Tile 4: BOX ON TARGET — green frame, hollow body and white check mark.
; The hollow centre/check also distinguishes it from the filled BOX when
; bit 7 (orange versus green) carries no colour information on a mono display.
        .byte $00,$00, $00,$00, $28,$15, $28,$15
        .byte $08,$10, $08,$10, $08,$16, $08,$16
        .byte $38,$16, $68,$13, $48,$11, $08,$10
        .byte $28,$15, $28,$15, $00,$00, $00,$00
; Tile 5: PLAYER (white figure)
        .byte $70,$01, $78,$03, $18,$03, $78,$03
        .byte $70,$01, $7C,$07, $7E,$0F, $70,$01
        .byte $70,$01, $78,$03, $0C,$06, $0C,$06
        .byte $0C,$06, $0E,$0E, $00,$00, $00,$00
; Tile 6: PLAYER ON TARGET — the same white figure, with a green line
; below its feet (odd pixels, bit 7 clear).
        .byte $70,$01, $78,$03, $18,$03, $78,$03
        .byte $70,$01, $7C,$07, $7E,$0F, $70,$01
        .byte $70,$01, $78,$03, $0C,$06, $0C,$06
        .byte $0C,$06, $0E,$0E, $28,$15, $00,$00
; Tile 7: BOX ON TARGET in COLOR MODE — the BOX frame with a green body. On a
; mono display only bit 7 tells it from the BOX: hence the option.
        .byte $00,$00, $00,$00, $7C,$1F, $7C,$1F
        .byte $0C,$18, $28,$15, $28,$15, $28,$15
        .byte $28,$15, $28,$15, $28,$15, $0C,$18
        .byte $7C,$1F, $7C,$1F, $00,$00, $00,$00

.assert pack_buf = PACK_ADDR, error, "the packs are BLOADed at PACK_ADDR"
.assert __BSS_RUN__ + __BOOTCODE_SIZE__ <= $9AA0, lderror, "the start-only code runs into DOS's buffers"

.include "score_hof.inc"
.include "profiles.inc"
.include "resume.inc"
.include "fast_disk.inc"
.include "beginner.inc"
.include "solution.inc"

; =============================================================================
; ../dev/lib/apple2 modules (textual includes: they pick their own segments)
; =============================================================================
.include "kbd.asm"               ; poll_key
HGR_CLEAR_ROUTINE = clear_draw_page   ; hgr_init_clear clears through our loop
.include "hgr.asm"               ; hgr_init_clear

; The loader and work buffers overwrite Applesoft at $0801. After restoring
; DOS's zero page, LOAD HELLO restores both the program and BASIC pointers.
; Only resident code is used here: loading HELLO overwrites our work buffers.
restore_basic:
        LDA #0
        STA $0800                       ; Applesoft's sentinel before TXTTAB
        JSR $03EA                       ; reconnect DOS input/output hooks
        LDX #0
@char:  LDA basic_load_cmd,X
        ORA #$80
        STX @index+1
        JSR COUT
@index: LDX #0
        INX
        CPX #13
        BCC @char
        RTS
basic_load_cmd: .byte $0D, $04, "LOAD HELLO", $0D
.define APPLE2_EXIT_HOOK restore_basic
.include "exit.asm"              ; apple2_zp_save, apple2_exit
.include "sound.asm"             ; tone
.include "joy.asm"               ; read_stick, stick_dir (JOY_LO/HI above)
; Disk I/O lives in fast_disk.inc; DOS command parsing is only used by HELLO.


.assert ACT_UP = JOY_UP && ACT_DOWN = JOY_DOWN && ACT_LEFT = JOY_LEFT && ACT_RIGHT = JOY_RIGHT, error, "get_input passes stick_dir's result on as an action"
