; =============================================================================
; SOKOBAN — Apple II+ / DOS 3.3 port (HGR, keyboard + joystick)
; VERHILLE Arnaud - 2026            Original: HGR_Sokoban.asm (POM1, GEN2 card)
; Licence: GPL v3 (same as the upstream sketch)
; =============================================================================
; Assemble with cc65:   make          (see ../Makefile)
; Output: SOKOBAN, a DOS 3.3 binary file, BRUN at $6000 (../dev layout).
;
; Controls
;   Joystick  : stick = move (auto-repeats while held)
;               button 0 tapped = undo; button 0 held + stick left/right =
;               undo / redo (auto-repeat)
;               button 1 = menu
;   Keyboard  : I J K L or W A S D or arrows = move
;               U undo    Y redo    R restart (undoable: Y replays)
;               N next    P previous
;               H or ESC  = menu        RETURN/SPACE = select in menu
;               in the menu: C = dead-corner warning on/off, Q = quit to DOS
;               Ctrl-RESET also quits cleanly
;
; Playfield: 20 cols x 12 rows of 14x16 pixel tiles.
; Delta rendering: a move only redraws the 2-3 affected tiles, on the page
; on screen. Whole screens (level, title, help, success) are drawn on the
; hidden HGR page and shown with one page flip.
; HUD: 7-pixel glyphs in the four screen corners, 3 tiles each (moves top
; left, pushes top right, level bottom left); levels keep those cells empty.
; Levels: Microban (David W. Skinner) -- every level that fits the screen,
; converted by tools/sokoban_levels.py into packs of up to 4 KB (MB1A, MB1B,
; ...) that are BLOADed into LOWBSS when play crosses into another pack. A
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
ACT_MENU    = 9         ; H / ESC key / button 1
ACT_SELECT  = 10        ; RETURN / SPACE
ACT_QUIT    = 11        ; Q key (acted on in the menu only)
ACT_REDO    = 12        ; Y key / button 0 held + stick right
ACT_CORNERS = 13        ; C key (acted on in the menu only)
ACT_GOTO    = 14        ; G key: level selection
ACT_OTHER   = 15        ; any other key

; --- Joystick tuning ---
; read_stick (joy.asm) counts 24-cycle iterations while each paddle timer is
; charging: PDL 0 -> 0, PDL 127 (centered) -> ~60, PDL 255 -> ~120. JOY_LO /
; JOY_HI set the dead zone of stick_dir (joy.asm), defined here first.
JOY_LO     = 30         ; count below this  = left / up
JOY_HI     = 90         ; count above this  = right / down
JOY_REPEAT = 32         ; get_input calls (~6 ms each) between auto-repeats

; --- Menu entries (one per tile row from MENU_ROW0) ---
MENU_RESUME  = 0
MENU_RESET   = 1
MENU_NEXT    = 2
MENU_PREV    = 3
MENU_GOTO    = 4
MENU_CORNERS = 5        ; toggled in place, never returned
MENU_QUIT    = 6
MENU_COUNT   = 7
MENU_ROW0    = 5        ; tile row of the first menu entry (cursor = player tile)
MENU_CURSOR_COL = 4
MENU_TEXT_COL   = $0B   ; byte column of the entry texts

; --- HUD: 7-pixel glyphs, 8 lines centred in the top / bottom tile rows ---
HUD_TOP_SL = 4
HUD_BOT_SL = 11 * 16 + 4
HUD_LEFT   = 0          ; byte columns: 6 glyphs = 3 tiles per corner
HUD_RIGHT  = 34

; --- Save file SOKOSAVE: "SOK1", collection and level last solved, then 4
; bytes per level (best moves, best pushes; 0 = unsolved), SAVE_LEN in all.
SAVE_HDR   = 6

; --- Level selection: pages of 10 x 8 numbers, 4 byte columns each ---
SEL_COLS   = 10
SEL_PAGE   = 80
SEL_SL0    = 24         ; scanline of the first row of numbers
SEL_DY     = 18         ; scanlines from one row to the next

; =============================================================================
; Zero page ($50+, see ../dev/cc65/apple2_hgr.cfg)
; =============================================================================
.zeropage
temp:            .res 1
temp2:           .res 1
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
dead_corner:     .res 1  ; 1 = that box landed in a target-less corner
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

; =============================================================================
; LOWBSS ($1000-$1FFF, not in the file)
; =============================================================================
.segment "LOWBSS"
pack_buf:        .res PACK_MAX   ; the level pack in use, BLOADed at PACK_ADDR

; =============================================================================
; BSS (after the code, not part of the BRUN file)
; =============================================================================
.bss
hist:            .res HIST_LEN   ; move history ring
STATE_GRID:      .res 240        ; 20x12 playfield, one tile code per cell
loaded_pack:     .res 1          ; pack in pack_buf, $FF = none
title_ix:        .res 1
title_glyph:     .res 1
title_col_start: .res 1
title_scanline:  .res 1
big_byte0:       .res 1
big_byte1:       .res 1
num_col:         .res 1          ; text cursor: byte column, scanline, advance
num_sl:          .res 1
num_step:        .res 1
num_pow:         .res 1          ; print_num power index
str_ix:          .res 1
save_buf:        .res SAVE_LEN   ; SOKOSAVE, BLOADed at start
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
b0_used:         .res 1          ; 1 = the stick moved while button 0 was held
menu_sel:        .res 1
menu_prev:       .res 1
front_page:      .res 1          ; page on screen: 0 = page 1, PAGE2_EOR = page 2
corners_on:      .res 1          ; 1 = warn when a box goes into a dead corner

; =============================================================================
.code

; =============================================================================
; MAIN — entry point (BRUN)
; =============================================================================
main:
        APPLE2_PREAMBLE
        JSR apple2_zp_save              ; ZP is DOS/Applesoft's: restored on quit
        LDA #$00
        STA btn0_prev
        STA btn1_prev
        STA joy_hold
        STA cur_coll
        STA cur_lvl
        STA quiet
        STA replaying
        STA front_page                  ; page 1 on screen, drawing on page 1
        JSR set_draw_page
        LDA #$01
        STA corners_on
        LDA #$FF
        STA loaded_pack

        ; Blank-first: page 1 is cleared while the display still shows text,
        ; then the title is drawn on page 2 and flipped in.
        JSR hgr_init_clear
        JSR begin_screen
        JSR draw_title
        JSR show_screen
        JSR load_save                   ; under the title: the save file,
        JSR first_unsolved              ; where to resume,
        JSR find_level                  ; and that level's pack
        JSR wait_any                    ; any key / any button starts,
        CMP #ACT_GOTO                   ; G goes to the level grid first
        BNE game_loop
        JSR run_select                  ; (ESC: the resume level)

game_loop:
        JSR init_level
        LDA #$00                        ; fresh counters and history
        STA moves_lo
        STA moves_hi
        STA pushes_lo
        STA pushes_hi
        STA hist_pos_lo
        STA hist_pos_hi
        STA undo_n_lo
        STA undo_n_hi
        STA redo_n_lo
        STA redo_n_hi
redraw_level:
        JSR begin_screen
        JSR render_all
        JSR draw_hud
        JSR show_screen

move_loop:
        JSR get_input
        BEQ move_loop                   ; ACT_NONE
        CMP #ACT_RIGHT+1
        BCC key_dir                     ; ACT_UP..ACT_RIGHT
        CMP #ACT_UNDO
        BEQ key_undo
        CMP #ACT_REDO
        BEQ key_redo
        CMP #ACT_RESET
        BEQ key_reset
        CMP #ACT_NEXT
        BEQ key_next
        CMP #ACT_PREV
        BEQ key_prev
        CMP #ACT_MENU
        BEQ key_menu
        CMP #ACT_GOTO
        BEQ key_goto
        JMP move_loop                   ; ignore the rest

key_goto:
        JSR run_select                  ; C = 1: cur_coll / cur_lvl chosen
        BCC @back
        JMP game_loop
@back:  JMP redraw_level

key_undo:
        JSR execute_undo
        JMP move_loop

key_redo:
        JSR execute_redo
        JMP check_done                  ; a redo can finish the level

key_menu:
        JSR run_menu                    ; returns A = MENU_* choice
        CMP #MENU_RESET
        BEQ key_reset
        CMP #MENU_NEXT
        BEQ key_next
        CMP #MENU_PREV
        BEQ key_prev
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
        BNE game_loop_j
        JMP redraw_level

key_next:
        JMP advance_level

; key_prev: previous level; before the first, the last of the previous
; collection.
key_prev:
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

        ; Level complete: record, success screen, save, then the end screen
        ; if it was the last level of the collection
        JSR record_solution
        JSR begin_screen
        JSR draw_success
        JSR show_screen
        JSR play_fanfare
        JSR write_save
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
; (auto-repeat). The stick alone moves, auto-repeating every JOY_REPEAT calls.
; Clobbers A, X, Y.
; =============================================================================
get_input:
        LDA #$00
        STA in_src
        JSR poll_key                    ; kbd.asm: A = key, upper-cased, or 0
        BEQ @stick
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

@stick:
        LDA #$01
        STA in_src
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
        JSR read_stick
        LDA joy_x
        CMP #JOY_LO
        BCC @sh_undo
        CMP #JOY_HI+1
        BCS @sh_redo
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

@axes:  JSR read_stick
        JSR stick_dir                   ; JOY_UP..JOY_RIGHT = ACT_UP..ACT_RIGHT
        BNE @dir
        STA joy_hold                    ; centered: A = 0, rearm the repeat
        RTS
@dir:   LDX joy_hold
        BEQ @fire
        DEC joy_hold
        LDA #$00
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
        .byte 'H', ACT_MENU, $1B, ACT_MENU, 'Q', ACT_QUIT, 'C', ACT_CORNERS
        .byte 'G', ACT_GOTO
        .byte $0D, ACT_SELECT, ' ', ACT_SELECT
        .byte 0

; -----------------------------------------------------------------------------
; wait_any: block until a key (any) or a joystick button press. Stick
; deflections are ignored so a stick still held from the winning push
; does not skip the screen.
; -----------------------------------------------------------------------------
wait_any:
        JSR get_input
        BEQ wait_any
        LDX in_src
        BEQ @done                       ; keyboard: anything goes
        CMP #ACT_UNDO                   ; joystick: buttons only
        BEQ @done
        CMP #ACT_MENU
        BNE wait_any
@done:  RTS

; =============================================================================
; MENU — help text + cursor-driven choice. Returns A = MENU_*.
; =============================================================================
run_menu:
        JSR begin_screen
        JSR draw_help
        JSR draw_corners_entry
        JSR show_screen                 ; the cursor is drawn on the page shown
        LDA #MENU_RESUME
        STA menu_sel
        JSR menu_draw_cursor
@loop:  JSR get_input
        BEQ @loop
        CMP #ACT_UP
        BEQ @up
        CMP #ACT_DOWN
        BEQ @down
        CMP #ACT_RESET
        BEQ @reset
        CMP #ACT_NEXT
        BEQ @next
        CMP #ACT_PREV
        BEQ @prev
        CMP #ACT_QUIT
        BEQ @quit
        CMP #ACT_CORNERS
        BEQ @corners
        CMP #ACT_GOTO
        BEQ @goto
        CMP #ACT_SELECT
        BEQ @select
        LDX in_src
        BEQ @resume                     ; any other KEY resumes
        CMP #ACT_UNDO                   ; button 0 / button 1 select
        BEQ @select
        CMP #ACT_MENU
        BEQ @select
        JMP @loop                       ; (left/right: ignore)
@reset: LDA #MENU_RESET
        RTS
@next:  LDA #MENU_NEXT
        RTS
@prev:  LDA #MENU_PREV
        RTS
@quit:  LDA #MENU_QUIT
        RTS
@goto:  LDA #MENU_GOTO
        RTS
@resume:
        LDA #MENU_RESUME
        RTS
@select:
        LDA menu_sel
        CMP #MENU_CORNERS
        BEQ @corners
        RTS
@corners:
        LDA corners_on
        EOR #$01
        STA corners_on
        JSR draw_corners_entry
        JMP @loop
@up:    LDA menu_sel
        STA menu_prev
        BEQ @wrap_last
        DEC menu_sel
        JMP @moved
@wrap_last:
        LDA #MENU_COUNT-1
        STA menu_sel
        JMP @moved
@down:  LDA menu_sel
        STA menu_prev
        INC menu_sel
        LDA menu_sel
        CMP #MENU_COUNT
        BCC @moved
        LDA #$00
        STA menu_sel
@moved: ; erase old cursor (floor tile), draw new one (player tile)
        LDA menu_prev
        CLC
        ADC #MENU_ROW0
        STA draw_row
        LDA #MENU_CURSOR_COL
        STA draw_col
        LDA #TILE_FLOOR
        JSR draw_tile
        JSR menu_draw_cursor
        JMP @loop

menu_draw_cursor:
        LDA menu_sel
        CLC
        ADC #MENU_ROW0
        STA draw_row
        LDA #MENU_CURSOR_COL
        STA draw_col
        LDA #TILE_PLAYER
        JMP draw_tile

; draw_corners_entry: "CORNERS: ON (C)" / "CORNERS:OFF (C)", same width, so
; one draw over the other replaces it.
draw_corners_entry:
        LDX #<menu_corners_on
        LDY #>menu_corners_on
        LDA corners_on
        BNE @on
        LDX #<menu_corners_off
        LDY #>menu_corners_off
@on:    STX sptr_lo
        STY sptr_hi
        LDA #MENU_TEXT_COL
        STA title_col_start
        LDA #(MENU_ROW0 + MENU_CORNERS) * 16 + 4
        STA title_scanline
        JMP draw_title_line

; =============================================================================
; SOUND
; =============================================================================
; play_fanfare: three rising notes on level completion.
play_fanfare:
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
; on a target; two low notes when it lands in a dead corner (if enabled).
move_sounds:
        LDA quiet
        BNE @done
        LDA SPKR
        LDA on_target
        BEQ @corner
        LDA #$30
        LDX #$28
        JMP tone
@corner:
        LDA dead_corner
        BEQ @done
        LDA corners_on
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
        LDA quiet
        BNE @done
        LDA #$06
        LDX #$FF
        JMP tone
@done:  RTS

; =============================================================================
; init_level: decode level (cur_coll, cur_lvl) into STATE_GRID, loading its
; pack first if needed; find the player, count the boxes off target.
; A level record is w, h, row, col, then runs: tile << 5 | (length - 1), in
; row-major order over the w x h box (tools/sokoban_levels.py).
; =============================================================================
init_level:
        JSR find_level                  ; sptr -> the record, pack loaded

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
@done:  RTS

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
        JSR dos_cmd_new
        LDA #<bload_str
        LDY #>bload_str
        JSR dos_cmd_add
        LDX loaded_pack
        LDA pack_name_lo,X
        LDY pack_name_hi,X
        JSR dos_cmd_add
        LDA #<pack_at_str
        LDY #>pack_at_str
        JSR dos_cmd_add
        JMP dos_cmd_run

; show_status: the glyph string at A/Y (lo/hi) bottom right of the screen on
; show, packed (7-pixel glyphs), right-aligned on a 7-glyph field.
show_status:
        STA sptr_lo
        STY sptr_hi
        LDA #1
        STA num_step
        LDA #HUD_RIGHT-1
        STA num_col
        LDA #HUD_BOT_SL
        STA num_sl
        JMP draw_str

bload_str:   .byte "BLOAD ", 0
pack_at_str: .byte ",A$1000", 0
.assert PACK_ADDR = $1000, error, "pack_at_str must match PACK_ADDR"
save_load_str: .byte "BLOAD SOKOSAVE,A$", 0
save_save_str: .byte "BSAVE SOKOSAVE,A$", 0
len_str:       .byte ",L$", 0
save_magic:    .byte "SOK1"

; =============================================================================
; Save file. load_save BLOADs SOKOSAVE into save_buf (a missing or foreign
; content is wiped); write_save BSAVEs it, unless the disk is write
; protected (DOS would stop the game with WRITE PROTECTED).
; =============================================================================
load_save:
        JSR dos_cmd_new
        LDA #<save_load_str
        LDY #>save_load_str
        JSR dos_cmd_add
        LDA #>save_buf
        JSR dos_cmd_hex
        LDA #<save_buf
        JSR dos_cmd_hex
        JSR dos_cmd_run
        LDX #3
@magic: LDA save_buf,X
        CMP save_magic,X
        BNE @wipe
        DEX
        BPL @magic
        RTS
@wipe:  LDA #<save_buf
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
        BEQ @hdr
        STA (sptr_lo),Y
        INY
        BNE @rest
@hdr:   LDX #3
@m:     LDA save_magic,X
        STA save_buf,X
        DEX
        BPL @m
        RTS

write_save:
        LDA cur_coll                    ; header: the level just solved
        STA save_buf+4
        LDA cur_lvl
        STA save_buf+5
        JSR disk_protected
        BCS @done
        LDA #<str_saving
        LDY #>str_saving
        JSR show_status
        JSR dos_cmd_new
        LDA #<save_save_str
        LDY #>save_save_str
        JSR dos_cmd_add
        LDA #>save_buf
        JSR dos_cmd_hex
        LDA #<save_buf
        JSR dos_cmd_hex
        LDA #<len_str
        LDY #>len_str
        JSR dos_cmd_add
        LDA #>SAVE_LEN
        JSR dos_cmd_hex
        LDA #<SAVE_LEN
        JSR dos_cmd_hex
        JSR dos_cmd_run
        LDA #<str_blank7                ; wipe "SAVING"
        LDY #>str_blank7
        JSR show_status
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
@new:   LDA #$01
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
        ASL A                           ; src = tile_bitmaps + A*32
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
        STA dead_corner

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
        ; box onto plain floor: off target now; a dead corner?
        INC boxes_left
        LDA #TILE_BOX
        STA STATE_GRID,X
        JSR check_corner
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

        ; --- counters ---
        INC moves_lo                    ; 16 bits (65535 moves is plenty)
        BNE @m_ok
        INC moves_hi
@m_ok:  LDA had_push
        BEQ @p_ok
        INC pushes_lo
        BNE @p_ok
        INC pushes_hi
@p_ok:
        ; --- history ---
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
        JSR flush_dirty
        JSR draw_hud
        JSR move_sounds
        LDA #$01
        RTS

@blocked:
        JSR bump_sound
        LDA #$00
        RTS

; check_corner: X = cell of a box just put on plain floor. dead_corner := 1
; if a wall is above or below it AND left or right of it: it can never move
; again, and it is not on a target. Preserves X.
check_corner:
        LDA STATE_GRID-NCOLS,X
        CMP #TILE_WALL
        BEQ @vert
        LDA STATE_GRID+NCOLS,X
        CMP #TILE_WALL
        BNE @no
@vert:  LDA STATE_GRID-1,X
        CMP #TILE_WALL
        BEQ @dead
        LDA STATE_GRID+1,X
        CMP #TILE_WALL
        BNE @no
@dead:  LDA #$01
        STA dead_corner
@no:    RTS

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

        JSR flush_dirty
        JSR draw_hud
        LDA quiet
        BNE @q
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
; HUD: moves top left, pushes top right, level bottom left, record bottom
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
        LDA #HUD_TOP_SL
        STA num_sl
        LDA #HUD_LEFT
        STA num_col
        LDA #G_M
        JSR put_glyph
        LDA #G_COLON
        JSR put_glyph
        LDA moves_lo
        STA num_lo
        LDA moves_hi
        STA num_hi
        LDA #4
        JSR print_num

        LDA #HUD_RIGHT
        STA num_col
        LDA #G_P
        JSR put_glyph
        LDA #G_COLON
        JSR put_glyph
        LDA pushes_lo
        STA num_lo
        LDA pushes_hi
        STA num_hi
        LDA #4
        JSR print_num

        LDA #HUD_BOT_SL                 ; "I:001": collection, original number
        STA num_sl
        LDA #HUD_LEFT
        STA num_col
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
; num_step the advance: 1 = packed (HUD), 2 = the 14-pixel screen spacing.
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
        JSR draw_title_glyph
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
hud_font = HGR_Sokoban_bbfont

; --- 2x doubling tables for draw_big_glyph ---
double_lo:
        .byte $00, $03, $0C, $0F, $30, $33, $3C, $3F
        .byte $40, $43, $4C, $4F, $70, $73, $7C, $7F
double_hi:
        .byte $00, $01, $06, $07, $18, $19, $1E, $1F
        .byte $60, $61, $66, $67, $78, $79, $7E, $7F

; =============================================================================
; Title / help / success screens — table driven.
; Entry = str_lo, str_hi, byte_col, scanline, style (0 small, 1 big). $FF ends.
; =============================================================================
draw_title:
        LDA #<title_table
        STA tbl_lo
        LDA #>title_table
        STA tbl_hi
        JMP draw_from_table

draw_help:
        LDA #<help_table
        STA tbl_lo
        LDA #>help_table
        STA tbl_hi
        JMP draw_from_table

; draw_success: "SUCCESS", the moves and pushes of the solution, and
; "NEW RECORD" or the record it did not beat.
draw_success:
        LDA #<success_table
        STA tbl_lo
        LDA #>success_table
        STA tbl_hi
        JSR draw_from_table
        LDA #2
        STA num_step
        LDA #22
        STA num_col
        LDA #80
        STA num_sl
        LDA moves_lo
        STA num_lo
        LDA moves_hi
        STA num_hi
        LDA #4
        JSR print_num
        LDA #22
        STA num_col
        LDA #96
        STA num_sl
        LDA pushes_lo
        STA num_lo
        LDA pushes_hi
        STA num_hi
        LDA #4
        JSR print_num
        LDA new_record
        BEQ @old
        TEXT 10, 120, str_new_record
        RTS
@old:   TEXT 8, 120, str_record
        LDA #22
        STA num_col
        LDA best_lo
        STA num_lo
        LDA best_hi
        STA num_hi
        LDA #4
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
        BEQ @done
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
        BEQ @small
        JSR draw_title_big_line
        JMP @next
@small:
        JSR draw_title_line
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

; Small lines: 14 px per glyph, so <= 20 glyphs; byte_col = 20 - n centres.
title_table:
        .byte <title_sokoban,  >title_sokoban,  $0D, $08, $01    ; big
        .byte <title_apple,    >title_apple,    $0C, $30, $00    ; APPLE II
        .byte <title_levels,   >title_levels,   LEVELS_TITLE_COL, $40, $00
        .byte <title_skinner,  >title_skinner,  $01, $50, $00    ; BY DAVID W. SKINNER
        .byte <title_author,   >title_author,   $00, $68, $00    ; PORT VERHILLE ARNAUD
        .byte <title_ctrl,     >title_ctrl,     $04, $80, $00    ; JOYSTICK OR IJKL
        .byte <title_press,    >title_press,    $07, $98, $00    ; KEY OR BUTTON
        .byte <title_h_help,   >title_h_help,   $02, $AA, $00    ; H HELP   G LEVELS (clear of LOADING)
        .byte $FF

; Help: title, the controls, then the menu entries on tile rows
; MENU_ROW0.. (text 4 lines below the row top), cursor at column 4.
help_table:
        .byte <help_big_title, >help_big_title, $10,  2, $01    ; HELP (big)
        .byte <help_move,      >help_move,      $02, 22, $00
        .byte <help_undo,      >help_undo,      $02, 32, $00
        .byte <help_redo,      >help_redo,      $02, 42, $00
        .byte <help_menu,      >help_menu,      $02, 52, $00
        .byte <help_select,    >help_select,    $05, 64, $00
        .byte <menu_resume,    >menu_resume,    MENU_TEXT_COL, (MENU_ROW0+MENU_RESUME)*16+4, $00
        .byte <menu_reset,     >menu_reset,     MENU_TEXT_COL, (MENU_ROW0+MENU_RESET)*16+4, $00
        .byte <menu_next,      >menu_next,      MENU_TEXT_COL, (MENU_ROW0+MENU_NEXT)*16+4, $00
        .byte <menu_prev_str,  >menu_prev_str,  MENU_TEXT_COL, (MENU_ROW0+MENU_PREV)*16+4, $00
        .byte <menu_goto,      >menu_goto,      MENU_TEXT_COL, (MENU_ROW0+MENU_GOTO)*16+4, $00
        .byte <menu_quit,      >menu_quit,      MENU_TEXT_COL, (MENU_ROW0+MENU_QUIT)*16+4, $00
        .byte $FF

success_table:
        .byte <title_success,  >title_success,  $0D, 40, $01
        .byte <str_moves,      >str_moves,      $08, 80, $00
        .byte <str_pushes,     >str_pushes,     $08, 96, $00
        .byte <title_press,    >title_press,    $07, 160, $00
        .byte $FF

end_table:
        .byte <str_bravo,      >str_bravo,      $0F, 20, $01
        .byte <str_microban,   >str_microban,   $08, 56, $00
        .byte <str_solved,     >str_solved,     $04, 84, $00
        .byte <str_moves,      >str_moves,      $04, 100, $00
        .byte <str_pushes,     >str_pushes,     $04, 116, $00
        .byte <title_press,    >title_press,    $07, 160, $00
        .byte $FF

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
        BCC @row
        RTS

; draw_title_glyph: one 7x8 glyph. Input: A = glyph, X = byte_col, Y = scanline.
draw_title_glyph:
        STX temp
        STY temp2
        JSR set_hud_font_ptr
        LDY #$00
@sc:
        STY title_glyph
        LDA (src_lo),Y
        PHA
        LDY title_glyph
        TYA
        CLC
        ADC temp2
        TAX
        LDA hgr_lo,X
        CLC
        ADC temp
        STA ptr_lo
        LDA hgr_hi,X
        ADC #$00
        STA ptr_hi
        PLA
        LDY #$00
        STA (ptr_lo),Y
        LDY title_glyph
        INY
        STY title_glyph
        CPY #$08
        BCC @sc
        RTS

; --- Strings: glyph indices, $FF terminated (GSTR, see bbfont_subset.inc) ---
title_sokoban:  GSTR "SOKOBAN"
title_apple:    GSTR "APPLE II"
title_levels:   LEVELS_TITLE
title_skinner:  GSTR "BY DAVID W. SKINNER"
title_author:   GSTR "PORT VERHILLE ARNAUD"
title_ctrl:     GSTR "JOYSTICK OR IJKL"
title_press:    GSTR "KEY OR BUTTON"
title_h_help:   GSTR "H HELP    G LEVELS"
title_success:  GSTR "SUCCESS"
str_loading:    GSTR "LOADING"
str_saving:     GSTR " SAVING"
str_blank7:     GSTR "       "
str_moves:      GSTR "MOVES"
str_pushes:     GSTR "PUSHES"
str_record:     GSTR "RECORD"
str_new_record: GSTR "NEW RECORD"
str_bravo:      GSTR "BRAVO"
str_microban:   GSTR "MICROBAN "
str_solved:     GSTR "SOLVED "
str_sel_help:   GSTR "RETURN PLAY   ESC BACK   N/P SET"

help_big_title: GSTR "HELP"
help_move:      GSTR "MOVE STICK OR IJKL"
help_undo:      GSTR "UNDO BUTTON 0 OR U"
help_redo:      GSTR "REDO B0+RIGHT OR Y"
help_menu:      GSTR "MENU BUTTON 1 OR H"
help_select:    GSTR "BUTTON SELECTS"
menu_resume:    GSTR "RESUME"
menu_reset:     GSTR "RESTART (R)"
menu_next:      GSTR "NEXT LEVEL (N)"
menu_prev_str:  GSTR "PREV LEVEL (P)"
menu_goto:      GSTR "GO TO LEVEL (G)"
menu_corners_on:  GSTR "CORNERS: ON (C)"
menu_corners_off: GSTR "CORNERS:OFF (C)"
menu_quit:      GSTR "QUIT TO DOS (Q)"

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
begin_screen:
        LDA front_page
        EOR #PAGE2_EOR                  ; the page that is not on screen
        JSR set_draw_page
        JMP clear_draw_page

show_screen:
        LDA draw_page
        STA front_page
        BNE @p2
        LDA LOWSCR
        RTS
@p2:    LDA HISCR
        RTS

; set_draw_page: A = 0 (page 1) or PAGE2_EOR (page 2). Clobbers A, X.
set_draw_page:
        CMP draw_page
        BEQ @done
        STA draw_page
        LDX #191
@lp:    LDA hgr_hi,X
        EOR #PAGE2_EOR
        STA hgr_hi,X
        DEX
        CPX #$FF
        BNE @lp
@done:  RTS

; clear_draw_page: zero the 8 KB of the draw page. No zero page used.
clear_draw_page:
        LDA #$00
        TAX
        BIT draw_page
        BVS @clr2                       ; PAGE2_EOR has bit 6 set
@clr1:
.repeat 32, I
        STA HGR1 + (I * $100), X
.endrepeat
        INX
        BNE @clr1
        RTS
@clr2:
.repeat 32, I
        STA HGR2 + (I * $100), X
.endrepeat
        INX
        BNE @clr2
        RTS

; =============================================================================
; DATA
; =============================================================================
.data

draw_page:
        .byte 0                         ; 0 = hgr_hi addresses page 1, PAGE2_EOR = page 2

; hgr_hi is rewritten by set_draw_page: it lives in DATA, not RODATA.
; HGR scanline address tables (Apple II interleave), page 1 at load time
hgr_lo:
.repeat 192, I
        .byte <(HGR1 + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * $28)
.endrepeat
hgr_hi:
.repeat 192, I
        .byte >(HGR1 + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * $28)
.endrepeat

.rodata

row_x20:
        .byte   0,  20,  40,  60,  80, 100, 120, 140
        .byte 160, 180, 200, 220

; --- Tile bitmaps: 7 tiles x 16 scanlines x 2 bytes ---
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
; Tile 4: BOX ON TARGET — same frame, green body
        .byte $00,$00, $00,$00, $7C,$1F, $7C,$1F
        .byte $0C,$18, $28,$15, $28,$15, $28,$15
        .byte $28,$15, $28,$15, $28,$15, $0C,$18
        .byte $7C,$1F, $7C,$1F, $00,$00, $00,$00
; Tile 5: PLAYER (white figure)
        .byte $70,$01, $78,$03, $18,$03, $78,$03
        .byte $70,$01, $7C,$07, $7E,$0F, $70,$01
        .byte $70,$01, $78,$03, $0C,$06, $0C,$06
        .byte $0C,$06, $0E,$0E, $00,$00, $00,$00
; Tile 6: PLAYER ON TARGET — the figure in green. Green is odd pixels only
; (bit 7 clear), each dot two pixels wide on screen, so the figure is redrawn
; on that grid, symmetric about pixel 6 (the white one is centred on 5.5,
; which no odd-pixel grid can mirror): head 5,7 / arms 1..11 / legs 3 and 9.
        .byte $20,$01, $20,$01, $20,$01, $20,$01
        .byte $20,$01, $28,$05, $2A,$15, $20,$01
        .byte $20,$01, $28,$05, $08,$04, $08,$04
        .byte $08,$04, $0A,$14, $00,$00, $00,$00

.assert pack_buf = PACK_ADDR, error, "the packs are BLOADed at PACK_ADDR"

; =============================================================================
; ../dev/lib/apple2 modules (textual includes: they pick their own segments)
; =============================================================================
.include "kbd.asm"               ; poll_key
.include "hgr.asm"               ; hgr_init_clear
.include "exit.asm"              ; apple2_zp_save, apple2_exit
.include "sound.asm"             ; tone
.include "joy.asm"               ; read_stick, stick_dir (JOY_LO/HI above)
.include "dos.asm"               ; dos_cmd_*: BLOAD packs, B(LOAD|SAVE) SOKOSAVE
.assert ACT_UP = JOY_UP && ACT_DOWN = JOY_DOWN && ACT_LEFT = JOY_LEFT && ACT_RIGHT = JOY_RIGHT, error, "get_input passes stick_dir's result on as an action"
