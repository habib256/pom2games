; =============================================================================
; SOKOBAN — Apple II+ / DOS 3.3 port (HGR, keyboard + joystick)
; VERHILLE Arnaud - 2026            Original: HGR_Sokoban.asm (POM1, GEN2 card)
; Licence: GPL v3 (same as the upstream sketch)
; =============================================================================
; Assemble with cc65:   make          (see ../Makefile)
; Output: SOKOBAN, a DOS 3.3 binary file, BRUN at $4000.
;
; Controls
;   Joystick  : stick = move (auto-repeats while held)
;               button 0 = undo last move
;               button 1 = menu (resume / reset level / next / previous)
;   Keyboard  : I J K L or W A S D or arrows = move
;               U undo    R reset level    N next    P previous
;               H or ESC  = menu        RETURN/SPACE = select in menu
;
; Playfield: 20 cols x 12 rows of 14x16 pixel tiles on HGR page 1 ($2000).
; Delta rendering: a move only redraws the 2-3 affected tiles.
; Levels: Microban I (David W. Skinner), 72 levels, RLE compressed.
;
; Apple II+ specifics vs the Apple-1/GEN2 original:
;   - no V-blank signal on a II+ ($C019 is a //e thing) -> draws are immediate
;   - everything lives in one 48 KB bank: code+data at $4000, BSS after it
;   - zero page trimmed to $80-$9F (pointers + hot scalars); the rest is BSS
;   - the game port replaces the Apple-1 text-screen echo
; =============================================================================

; --- Apple II soft switches / I/O ---
KBD     = $C000         ; keyboard data, bit 7 = key ready
KBDSTRB = $C010         ; clear keyboard strobe
SPKR    = $C030         ; speaker toggle
TXTCLR  = $C050         ; graphics
TXTSET  = $C051         ; text
MIXCLR  = $C052         ; full screen
LOWSCR  = $C054         ; page 1
HIRES   = $C057         ; hi-res
BUTN0   = $C061         ; game port button 0 (bit 7)
BUTN1   = $C062         ; game port button 1 (bit 7)
PADDL0  = $C064         ; paddle 0 timer (bit 7 while charging)
PADDL1  = $C065         ; paddle 1 timer
PTRIG   = $C070         ; trigger the paddle timers

HGR_BASE = $2000

; --- Game constants ---
NCOLS      = 20
NROWS      = 12
NUM_LEVELS = 72
STATE_GRID_LEN = 240

; --- Tile types ---
TILE_FLOOR         = 0
TILE_WALL          = 1
TILE_TARGET        = 2
TILE_BOX           = 3
TILE_BOX_TARGET    = 4
TILE_PLAYER        = 5
TILE_PLAYER_TARGET = 6

; --- Input actions (get_input return codes) ---
ACT_NONE   = 0
ACT_UP     = 1
ACT_DOWN   = 2
ACT_LEFT   = 3
ACT_RIGHT  = 4
ACT_UNDO   = 5          ; U key / button 0
ACT_RESET  = 6          ; R key
ACT_NEXT   = 7          ; N key
ACT_PREV   = 8          ; P key
ACT_MENU   = 9          ; H / ESC key / button 1
ACT_SELECT = 10         ; RETURN / SPACE
ACT_OTHER  = 11         ; any other key

; --- Joystick tuning ---
; read_stick counts 24-cycle iterations while each paddle timer is charging:
; PDL 0 -> 0, PDL 127 (centered) -> ~60, PDL 255 -> ~120.
JOY_LO     = 30         ; count below this  = left / up
JOY_HI     = 90         ; count above this  = right / down
JOY_REPEAT = 32         ; get_input calls (~6 ms each) between auto-repeats

; --- Menu entries ---
MENU_RESUME = 0
MENU_RESET  = 1
MENU_NEXT   = 2
MENU_PREV   = 3
MENU_COUNT  = 4
MENU_ROW0   = 7         ; tile row of the first menu entry (cursor = player tile)
MENU_CURSOR_COL = 4

; =============================================================================
; Zero page ($80-$9F, 32 bytes)
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
level_idx:       .res 1
player_row:      .res 1
player_col:      .res 1
lvl_w:           .res 1
lvl_h:           .res 1
row_offset:      .res 1
col_offset:      .res 1
new_row:         .res 1
new_col:         .res 1
box_row:         .res 1
box_col:         .res 1
dir_dy:          .res 1  ; signed: -1, 0, 1
dir_dx:          .res 1
draw_row:        .res 1
draw_col:        .res 1
prev_player_row: .res 1  ; single-step undo state
prev_player_col: .res 1
undo_avail:      .res 1  ; 1 = execute_undo is valid
had_push:        .res 1  ; 1 = last move pushed a box
moves:           .res 1  ; move counter (saturates at 255)
str_lo:          .res 1  ; (unused pair kept for symmetry / future text)
str_hi:          .res 1

; =============================================================================
; BSS (after the code, not part of the BRUN file)
; =============================================================================
.bss
LEVEL_BUF:       .res 256        ; RLE-expanded level (max level 117 cells)
STATE_GRID:      .res 240        ; 20x12 playfield, one tile code per cell
title_ix:        .res 1
title_glyph:     .res 1
title_col_start: .res 1
title_scanline:  .res 1
big_byte0:       .res 1
big_byte1:       .res 1
hud_base_sl:     .res 1
dirty_n:         .res 1          ; dirty-tile queue (max 3 per move)
dirty_row:       .res 4
dirty_col:       .res 4
flush_ix:        .res 1
in_src:          .res 1          ; 0 = last action came from keyboard, 1 = joystick
joy_x:           .res 1          ; read_stick results (0..~120)
joy_y:           .res 1
joy_hold:        .res 1          ; auto-repeat countdown while the stick is held
btn0_prev:       .res 1          ; button edge detection
btn1_prev:       .res 1
stick_cnt:       .res 1
menu_sel:        .res 1
menu_prev:       .res 1
beep_len:        .res 1
beep_period:     .res 1

; =============================================================================
.code

; =============================================================================
; MAIN — entry point (BRUN)
; =============================================================================
main:
        CLD
        LDA #$00
        STA btn0_prev
        STA btn1_prev
        STA joy_hold
        STA level_idx

        ; Blank-first: clear the page while the display is still on text,
        ; then flip to full-screen HGR page 1.
        JSR clear_hgr
        LDA TXTCLR
        LDA HIRES
        LDA LOWSCR
        LDA MIXCLR

        JSR draw_title
        JSR wait_any                    ; any key / any button starts

game_loop:
        JSR init_level
        JSR clear_hgr
        JSR render_all
        LDA #$00                        ; reset undo + move counter
        STA undo_avail
        STA had_push
        STA moves
        JSR draw_hud

move_loop:
        JSR get_input
        BEQ move_loop                   ; ACT_NONE
        CMP #ACT_UP
        BEQ key_up
        CMP #ACT_DOWN
        BEQ key_down
        CMP #ACT_LEFT
        BEQ key_left
        CMP #ACT_RIGHT
        BEQ key_right
        CMP #ACT_UNDO
        BEQ key_undo
        CMP #ACT_RESET
        BEQ key_reset
        CMP #ACT_NEXT
        BEQ key_next
        CMP #ACT_PREV
        BEQ key_prev
        CMP #ACT_MENU
        BEQ key_menu
        JMP move_loop                   ; ignore the rest

key_undo:
        JSR execute_undo
        JMP move_loop

key_menu:
        JSR run_menu                    ; returns A = MENU_* choice
        CMP #MENU_RESET
        BEQ key_reset
        CMP #MENU_NEXT
        BEQ key_next
        CMP #MENU_PREV
        BEQ key_prev
        ; MENU_RESUME: repaint the playfield and carry on
        JSR clear_hgr
        JSR render_all
        JSR draw_hud
        JMP move_loop

key_up:
        LDA #$FF                        ; dy = -1
        STA dir_dy
        LDA #$00
        STA dir_dx
        JMP do_move
key_down:
        LDA #$01
        STA dir_dy
        LDA #$00
        STA dir_dx
        JMP do_move
key_left:
        LDA #$00
        STA dir_dy
        LDA #$FF                        ; dx = -1
        STA dir_dx
        JMP do_move
key_right:
        LDA #$00
        STA dir_dy
        LDA #$01
        STA dir_dx
        JMP do_move

key_reset:
        JMP game_loop

key_next:
        JMP advance_level

key_prev:
        LDA level_idx
        BNE @dec
        LDA #NUM_LEVELS
@dec:   SEC
        SBC #$01
        STA level_idx
        JMP game_loop

do_move:
        JSR execute_move
        CMP #$00
        BEQ move_loop_j                 ; blocked, no move
        LDA SPKR                        ; tiny click per step

        JSR check_win
        CMP #$00
        BEQ move_loop_j                 ; not won yet

        ; Level complete
        JSR draw_success
        JSR play_fanfare
        JSR wait_any

advance_level:
        INC level_idx
        LDA level_idx
        CMP #NUM_LEVELS
        BCC game_loop_j
        LDA #$00
        STA level_idx
game_loop_j:
        JMP game_loop
move_loop_j:
        JMP move_loop

; =============================================================================
; INPUT
; =============================================================================
; get_input: non-blocking poll of keyboard then joystick.
; Returns A = ACT_* (0 = nothing). in_src = 0 keyboard / 1 joystick.
; Joystick buttons are edge-triggered; the stick auto-repeats every
; JOY_REPEAT calls while held.
; Clobbers A, X, Y.
; =============================================================================
get_input:
        LDA #$00
        STA in_src
        LDA KBD
        BPL @stick
        BIT KBDSTRB                     ; clear the strobe
        AND #$7F
        CMP #'a'                        ; fold lowercase (a //e would send it)
        BCC @map
        CMP #'z'+1
        BCS @map
        AND #$DF
@map:   LDX #$00
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
        ; --- button 0 (edge) ---
        LDA BUTN0
        BMI @b0_down
        LDA #$00
        STA btn0_prev
        BEQ @b1
@b0_down:
        LDA btn0_prev
        BNE @b1                         ; still held from last time
        LDA #$01
        STA btn0_prev
        LDA #ACT_UNDO
        RTS
@b1:    ; --- button 1 (edge) ---
        LDA BUTN1
        BMI @b1_down
        LDA #$00
        STA btn1_prev
        BEQ @axes
@b1_down:
        LDA btn1_prev
        BNE @axes
        LDA #$01
        STA btn1_prev
        LDA #ACT_MENU
        RTS
@axes:  JSR read_stick
        LDA joy_y
        CMP #JOY_LO
        BCC @up
        CMP #JOY_HI+1
        BCS @down
        LDA joy_x
        CMP #JOY_LO
        BCC @left
        CMP #JOY_HI+1
        BCS @right
        ; centered
        LDA #$00
        STA joy_hold
        RTS
@up:    LDA #ACT_UP
        BNE @dir
@down:  LDA #ACT_DOWN
        BNE @dir
@left:  LDA #ACT_LEFT
        BNE @dir
@right: LDA #ACT_RIGHT
@dir:   LDX joy_hold
        BEQ @fire
        DEC joy_hold
        LDA #$00
        RTS
@fire:  LDX #JOY_REPEAT
        STX joy_hold
        RTS

; Keyboard map: (ASCII, action) pairs, 0-terminated.
key_tbl:
        .byte 'I', ACT_UP,   'K', ACT_DOWN, 'J', ACT_LEFT, 'L', ACT_RIGHT
        .byte 'W', ACT_UP,   'S', ACT_DOWN, 'A', ACT_LEFT, 'D', ACT_RIGHT
        .byte $0B, ACT_UP,   $0A, ACT_DOWN, $08, ACT_LEFT, $15, ACT_RIGHT
        .byte 'U', ACT_UNDO, 'R', ACT_RESET, 'N', ACT_NEXT, 'P', ACT_PREV
        .byte 'H', ACT_MENU, $1B, ACT_MENU
        .byte $0D, ACT_SELECT, ' ', ACT_SELECT
        .byte 0

; -----------------------------------------------------------------------------
; read_stick: sample both paddle timers in one fixed-length loop (256 x 24
; cycles = 6 ms, longer than the 2.8 ms a fully deflected paddle charges).
; Reading both every iteration sidesteps the classic "second paddle read too
; soon after the first" bug. joy_x / joy_y = iterations spent charging.
; Clobbers A, X, Y.
; -----------------------------------------------------------------------------
read_stick:
        LDX #$00
        LDY #$00
        STX stick_cnt
        LDA PTRIG
@lp:    LDA PADDL0
        BPL @xd
        INX
@xd:    LDA PADDL1
        BPL @yd
        INY
@yd:    DEC stick_cnt
        BNE @lp
        STX joy_x
        STY joy_y
        RTS

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
        JSR draw_help
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
@resume:
        LDA #MENU_RESUME
        RTS
@select:
        LDA menu_sel
        RTS
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

; =============================================================================
; SOUND
; =============================================================================
; beep: toggle the speaker beep_len times with beep_period delay. Clobbers A,X,Y.
beep:
        LDY beep_len
@t:     LDA SPKR
        LDX beep_period
@d:     DEX
        BNE @d
        DEY
        BNE @t
        RTS

; play_fanfare: three rising notes on level completion.
play_fanfare:
        LDA #$60
        STA beep_len
        LDA #$C0
        STA beep_period
        JSR beep
        LDA #$80
        STA beep_len
        LDA #$90
        STA beep_period
        JSR beep
        LDA #$C0
        STA beep_len
        LDA #$60
        STA beep_period
        JMP beep

; =============================================================================
; init_level: RLE-expand the level into STATE_GRID
; =============================================================================
init_level:
        JSR load_level                  ; fills LEVEL_BUF, sets lvl_w/h + offsets

        LDY #$00
        TYA
@clr:   STA STATE_GRID,Y
        INY
        CPY #240
        BNE @clr

        LDA #$00
        STA temp                        ; temp = parse_row
        STA sptr_lo                     ; reuse sptr_lo as flat LEVEL_BUF index
@rowlp:
        LDY #$00                        ; Y = parse_col
@collp:
        LDX sptr_lo
        LDA LEVEL_BUF,X
        JSR ascii_to_tile               ; A = tile type
        PHA

        CMP #TILE_PLAYER
        BEQ @save_player
        CMP #TILE_PLAYER_TARGET
        BNE @no_player
@save_player:
        TYA
        CLC
        ADC col_offset
        STA player_col
        LDA temp
        CLC
        ADC row_offset
        STA player_row
@no_player:
        ; cell_index = (temp+row_offset)*20 + (Y+col_offset)
        LDA temp
        CLC
        ADC row_offset
        TAX
        LDA row_x20,X
        STA temp2
        TYA
        CLC
        ADC col_offset
        CLC
        ADC temp2
        TAX
        PLA
        STA STATE_GRID,X

        INC sptr_lo
        INY
        CPY lvl_w
        BCC @collp

        INC temp
        LDA temp
        CMP lvl_h
        BCS @init_done
        JMP @rowlp
@init_done:
        RTS

; =============================================================================
; render_all: draw all 240 tiles
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
        JSR draw_tile
        INC draw_col
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
; redraws them all from their final state.
; =============================================================================
queue_tile:
        LDX dirty_n
        LDA draw_row
        STA dirty_row,X
        LDA draw_col
        STA dirty_col,X
        INC dirty_n
        RTS

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
; execute_move: try to move the player along (dir_dy, dir_dx).
; Returns A=0 blocked, A!=0 moved. Updates STATE_GRID + redraws the delta.
; =============================================================================
execute_move:
        LDA #$00
        STA dirty_n
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

        LDX new_row
        LDA row_x20,X
        CLC
        ADC new_col
        TAX
        LDA STATE_GRID,X

        CMP #TILE_WALL
        BEQ @blk_tr
        CMP #TILE_BOX
        BEQ @try_push
        CMP #TILE_BOX_TARGET
        BEQ @try_push
        LDA #$00
        STA had_push
        JMP @simple_move                ; floor or target

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

        LDX box_row
        LDA row_x20,X
        CLC
        ADC box_col
        TAX
        LDA STATE_GRID,X

        CMP #TILE_FLOOR
        BEQ @push_floor
        CMP #TILE_TARGET
        BEQ @push_target
        JMP @blocked

@push_floor:
        LDA #TILE_BOX
        STA STATE_GRID,X
        LDA #$01
        STA had_push
        JMP @box_done
@push_target:
        LDA #TILE_BOX_TARGET
        STA STATE_GRID,X
        LDA #$01
        STA had_push
@box_done:
        LDA box_row
        STA draw_row
        LDA box_col
        STA draw_col
        JSR queue_tile

@simple_move:
        ; --- leave old player cell ---
        LDX player_row
        LDA row_x20,X
        CLC
        ADC player_col
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
        LDX new_row
        LDA row_x20,X
        CLC
        ADC new_col
        TAX
        LDA STATE_GRID,X
        CMP #TILE_BOX
        BEQ @strip_floor
        CMP #TILE_BOX_TARGET
        BEQ @strip_target
        JMP @enter
@strip_floor:
        LDA #TILE_FLOOR
        STA STATE_GRID,X
        JMP @enter
@strip_target:
        LDA #TILE_TARGET
        STA STATE_GRID,X
@enter:
        LDA STATE_GRID,X
        JSR enter_player
        STA STATE_GRID,X
        LDA new_row
        STA draw_row
        LDA new_col
        STA draw_col
        JSR queue_tile

        LDA player_row                  ; undo state
        STA prev_player_row
        LDA player_col
        STA prev_player_col
        LDA #$01
        STA undo_avail

        LDA new_row
        STA player_row
        LDA new_col
        STA player_col

        INC moves                       ; saturate at 255
        BNE @no_sat
        LDA #$FF
        STA moves
@no_sat:
        JSR flush_dirty
        JSR draw_hud
        LDA #$01
        RTS

@blocked:
        LDA #$00
        RTS

; =============================================================================
; execute_undo: reverse the last successful move (single step).
; =============================================================================
execute_undo:
        LDA undo_avail
        BNE @do_undo
        RTS
@do_undo:
        LDA #$00
        STA dirty_n
        LDA had_push
        BEQ @skip_box

        ; box = 2*player - prev_player
        LDA player_row
        ASL A
        SEC
        SBC prev_player_row
        STA box_row
        LDA player_col
        ASL A
        SEC
        SBC prev_player_col
        STA box_col

        LDX box_row
        LDA row_x20,X
        CLC
        ADC box_col
        TAX
        LDA STATE_GRID,X
        JSR leave_tile
        STA STATE_GRID,X
        LDA box_row
        STA draw_row
        LDA box_col
        STA draw_col
        JSR queue_tile
@skip_box:
        LDX player_row
        LDA row_x20,X
        CLC
        ADC player_col
        TAX
        LDA STATE_GRID,X
        JSR leave_tile
        STA STATE_GRID,X

        LDA had_push
        BEQ @draw_cur
        LDA STATE_GRID,X
        JSR enter_as_box
        STA STATE_GRID,X
@draw_cur:
        LDA player_row
        STA draw_row
        LDA player_col
        STA draw_col
        JSR queue_tile

        LDX prev_player_row
        LDA row_x20,X
        CLC
        ADC prev_player_col
        TAX
        LDA STATE_GRID,X
        JSR enter_player
        STA STATE_GRID,X
        LDA prev_player_row
        STA draw_row
        LDA prev_player_col
        STA draw_col
        JSR queue_tile

        LDA prev_player_row
        STA player_row
        LDA prev_player_col
        STA player_col

        LDA moves
        BEQ @no_dec
        DEC moves
@no_dec:
        JSR flush_dirty
        JSR draw_hud
        LDA #$00
        STA undo_avail
        STA had_push
        RTS

; =============================================================================
; draw_hud: "MV:NNN" top-left (row 0) and "L:NN" bottom-right (row 11).
; =============================================================================
HUD_G_M  = 10
HUD_G_V  = 11
HUD_G_CL = 12
HUD_G_L  = 22

draw_hud:
        LDA #$00
        STA hud_base_sl
        LDA #HUD_G_M
        LDX #$00
        JSR draw_hud_cell
        LDA #HUD_G_V
        LDX #$01
        JSR draw_hud_cell
        LDA #HUD_G_CL
        LDX #$02
        JSR draw_hud_cell

        LDA moves                       ; hundreds
        LDX #$00
@h100:  CMP #100
        BCC @h100d
        SBC #100
        INX
        JMP @h100
@h100d: PHA
        TXA
        LDX #$03
        JSR draw_hud_cell
        PLA

        LDX #$00                        ; tens
@t10:   CMP #$0A
        BCC @t10d
        SBC #$0A
        INX
        JMP @t10
@t10d:  PHA
        TXA
        LDX #$04
        JSR draw_hud_cell
        PLA

        LDX #$05                        ; ones
        JSR draw_hud_cell

        LDA #176                        ; bottom-right: L:NN
        STA hud_base_sl
        LDA #HUD_G_L
        LDX #$10
        JSR draw_hud_cell
        LDA #HUD_G_CL
        LDX #$11
        JSR draw_hud_cell

        LDA level_idx                   ; 1-based, 2 digits
        CLC
        ADC #$01
        LDX #$00
@lt10:  CMP #$0A
        BCC @lt10d
        SBC #$0A
        INX
        JMP @lt10
@lt10d: PHA
        TXA
        LDX #$12
        JSR draw_hud_cell
        PLA
        LDX #$13
        JMP draw_hud_cell

; draw_hud_cell: one 14x16 cell, glyph in the left byte, rest blank.
; Input: A = glyph index, X = cell column (0..19)
draw_hud_cell:
        STX temp
        ASL A
        ASL A
        ASL A
        STA temp2                       ; glyph base offset (idx*8)
        LDX #$00
@sc:
        TXA
        CLC
        ADC hud_base_sl
        TAY
        LDA hgr_lo,Y
        STA ptr_lo
        LDA hgr_hi,Y
        STA ptr_hi

        CPX #$08
        BCS @blank
        TXA
        CLC
        ADC temp2
        TAY
        LDA hud_font,Y
        JMP @write
@blank:
        LDA #$00
@write:
        PHA
        LDA temp
        ASL A
        TAY
        PLA
        STA (ptr_lo),Y
        INY
        LDA #$00
        STA (ptr_lo),Y

        INX
        CPX #$10
        BCC @sc
        RTS

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
        JSR clear_hgr
        LDA #<help_table
        STA tbl_lo
        LDA #>help_table
        STA tbl_hi
        JMP draw_from_table

draw_success:
        JSR clear_hgr
        LDA #<success_table
        STA tbl_lo
        LDA #>success_table
        STA tbl_hi

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
        .byte <title_levels,   >title_levels,   $02, $40, $00    ; MICROBAN 72 LEVELS
        .byte <title_author,   >title_author,   $02, $50, $00    ; BY VERHILLE ARNAUD
        .byte <title_ctrl,     >title_ctrl,     $04, $70, $00    ; JOYSTICK OR IJKL
        .byte <title_press,    >title_press,    $07, $90, $00    ; KEY OR BUTTON
        .byte <title_h_help,   >title_h_help,   $0E, $B8, $00    ; H HELP
        .byte $FF

help_table:
        .byte <help_big_title, >help_big_title, $10, $04, $01    ; HELP (big)
        .byte <help_move,      >help_move,      $02, $28, $00    ; MOVE STICK OR IJKL
        .byte <help_undo,      >help_undo,      $02, $38, $00    ; UNDO BUTTON 0 OR U
        .byte <help_menu,      >help_menu,      $02, $48, $00    ; MENU BUTTON 1 OR H
        ; menu entries: tile rows 7..10 (scanlines 112..160), cursor at col 4
        .byte <menu_resume,    >menu_resume,    $0B, 112+4, $00
        .byte <menu_reset,     >menu_reset,     $0B, 128+4, $00
        .byte <menu_next,      >menu_next,      $0B, 144+4, $00
        .byte <menu_prev_str, >menu_prev_str,      $0B, 160+4, $00
        .byte <help_select,    >help_select,    $05, $B8, $00    ; BUTTON SELECTS
        .byte $FF

success_table:
        .byte <title_success,  >title_success,  $0D, 56, $01
        .byte <title_press,    >title_press,    $07, 96, $00
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

; --- Strings: glyph indices, $FF terminated ---
;   0..9 = '0'..'9'
;   10=M  11=V  12=:  13=S  14=O  15=K  16=B  17=A  18=N  19=P
;   20=R  21=E  22=L  23=space  24=G  25=H  26=T  27=D  28=Y  29=I
;   30=U  31=Q  32=W  33=Z  34=C  35=X  36=(  37=)  38=J
title_sokoban:  .byte 13,14,15,14,16,17,18, $FF                          ; SOKOBAN
title_apple:    .byte 17,19,19,22,21,23,29,29, $FF                       ; APPLE II
title_levels:   .byte 10,29,34,20,14,16,17,18,23,7,2,23,22,21,11,21,22,13, $FF ; MICROBAN 72 LEVELS
title_author:   .byte 16,28,23,11,21,20,25,29,22,22,21,23,17,20,18,17,30,27, $FF ; BY VERHILLE ARNAUD
title_ctrl:     .byte 38,14,28,13,26,29,34,15,23,14,20,23,29,38,15,22, $FF ; JOYSTICK OR IJKL
title_press:    .byte 15,21,28,23,14,20,23,16,30,26,26,14,18, $FF          ; KEY OR BUTTON
title_h_help:   .byte 25,23,25,21,22,19, $FF                             ; H HELP
title_success:  .byte 13,30,34,34,21,13,13, $FF                          ; SUCCESS

help_big_title: .byte 25,21,22,19, $FF                                   ; HELP
help_move:      .byte 10,14,11,21,23,13,26,29,34,15,23,14,20,23,29,38,15,22, $FF ; MOVE STICK OR IJKL
help_undo:      .byte 30,18,27,14,23,16,30,26,26,14,18,23,0,23,14,20,23,30, $FF  ; UNDO BUTTON 0 OR U
help_menu:      .byte 10,21,18,30,23,16,30,26,26,14,18,23,1,23,14,20,23,25, $FF  ; MENU BUTTON 1 OR H
menu_resume:    .byte 20,21,13,30,10,21, $FF                             ; RESUME
menu_reset:     .byte 20,21,13,21,26,23,22,21,11,21,22,23,36,20,37, $FF  ; RESET LEVEL (R)
menu_next:      .byte 18,21,35,26,23,22,21,11,21,22,23,36,18,37, $FF     ; NEXT LEVEL (N)
menu_prev_str:  .byte 19,20,21,11,23,22,21,11,21,22,23,36,19,37, $FF     ; PREV LEVEL (P)
help_select:    .byte 16,30,26,26,14,18,23,13,21,22,21,34,26,13, $FF     ; BUTTON SELECTS

; =============================================================================
; Shared Sokoban plumbing (from sokoban_common.inc, minus the Apple-1 I/O)
; =============================================================================
ascii_to_tile:
        CMP #'#'
        BEQ @wall
        CMP #'.'
        BEQ @target
        CMP #'$'
        BEQ @box
        CMP #'*'
        BEQ @box_t
        CMP #'@'
        BEQ @player
        CMP #'+'
        BEQ @player_t
        LDA #TILE_FLOOR
        RTS
@wall:     LDA #TILE_WALL
        RTS
@target:   LDA #TILE_TARGET
        RTS
@box:      LDA #TILE_BOX
        RTS
@box_t:    LDA #TILE_BOX_TARGET
        RTS
@player:   LDA #TILE_PLAYER
        RTS
@player_t: LDA #TILE_PLAYER_TARGET
        RTS

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

; check_win: A=1 if no target is left uncovered by a box.
check_win:
        LDY #$00
@loop:  LDA STATE_GRID,Y
        CMP #TILE_TARGET
        BEQ @no
        CMP #TILE_PLAYER_TARGET
        BEQ @no
        INY
        CPY #STATE_GRID_LEN
        BNE @loop
        LDA #$01
        RTS
@no:    LDA #$00
        RTS

; load_level: expand level level_idx (RLE) into LEVEL_BUF, set lvl_w/h + offsets.
; RLE: byte < $80 literal; byte >= $80 -> (byte & $7F) copies of the next byte.
load_level:
        LDX level_idx
        LDA level_ptrs_lo,X
        STA sptr_lo
        LDA level_ptrs_hi,X
        STA sptr_hi

        LDY #$00
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

        CLC
        LDA sptr_lo
        ADC #$04
        STA sptr_lo
        LDA sptr_hi
        ADC #$00
        STA sptr_hi

        LDA #$00                        ; temp = w*h
        STA temp
        LDY lvl_h
        BEQ @decode
@mul:
        CLC
        LDA temp
        ADC lvl_w
        STA temp
        DEY
        BNE @mul

@decode:
        LDY #$00
        LDX #$00
@main:
        LDA (sptr_lo),Y
        INY
        CMP #$80
        BCC @literal
        AND #$7F
        STA temp2
        LDA (sptr_lo),Y
        INY
@runlp:
        STA LEVEL_BUF,X
        INX
        DEC temp2
        BNE @runlp
        JMP @chk
@literal:
        STA LEVEL_BUF,X
        INX
@chk:
        CPX temp
        BCC @main
        RTS

leave_tbl:        .byte 0, 1, 2, 0, 2, 0, 2
enter_player_tbl: .byte 5, 0, 6, 0, 0, 0, 0
enter_box_tbl:    .byte 3, 0, 4, 0, 0, 0, 0

; =============================================================================
; clear_hgr: zero HGR page 1 ($2000-$3FFF). No zero page used.
; =============================================================================
clear_hgr:
        LDA #$00
        TAX
@clr:
.repeat 32, I
        STA HGR_BASE + (I * $100), X
.endrepeat
        INX
        BNE @clr
        RTS

; =============================================================================
; DATA
; =============================================================================
.rodata

row_x20:
        .byte   0,  20,  40,  60,  80, 100, 120, 140
        .byte 160, 180, 200, 220

; HGR page 1 scanline address tables (Apple II interleave)
hgr_lo:
.repeat 192, I
        .byte <(HGR_BASE + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * $28)
.endrepeat
hgr_hi:
.repeat 192, I
        .byte >(HGR_BASE + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * $28)
.endrepeat

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

; --- Level data (RLE compressed, Microban I) ---
.include "sokoban_levels.inc"
.include "sokoban_levels_ext.inc"

level_ptrs_lo:
.repeat NUM_LEVELS, I
        .byte <.ident(.sprintf("level%d", I+1))
.endrepeat
level_ptrs_hi:
.repeat NUM_LEVELS, I
        .byte >.ident(.sprintf("level%d", I+1))
.endrepeat
