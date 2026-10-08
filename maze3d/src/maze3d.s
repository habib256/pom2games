; =============================================
; maze3d.s -- Wizardry-style 3D line maze for the Apple II+ (HGR, DOS 3.3)
; VERHILLE Arnaud - 2026   Original: HGR_Maze3D.asm (POM1, Apple-1 + GEN2)
; Licence: GPL v3 (same as the upstream sketch)
; =============================================
; Apple II port of POM1's sketchs/gen2/game_maze3d, itself the GEN2 HGR port
; of the TMS9918 dungeon crawler. The GEN2 card IS the Apple II video
; subsystem moved onto the Apple-1 bus, so the whole HGR primitive layer,
; the 3D renderer, the map, HUD and combat screens run unchanged. What
; changed for the Apple II:
;
;   - keyboard: the latch at $C000 is cleared through $C010 (the Apple-1
;     PIA cleared itself on read); key_fold folds lower case and maps the
;     arrow keys onto the IJKL movement keys
;   - soft switches $C050-$C057 instead of the GEN2's $C250-$C257
;   - DOUBLE BUFFERING: every full screen (3D view, map, combat, title,
;     help, win/lose) is drawn on the hidden HGR page and shown with one
;     page flip -- no more black blanking page during the redraw, the old
;     picture stays up until the new one is complete (set_draw_page,
;     vdp_display_off/on)
;   - ESC opens configuration; Q exits: zero page is saved at start and
;     restored on the way out (dev/lib/apple2/exit.asm) -- the Apple II
;     zero page belongs to the Monitor, DOS and Applesoft
;   - one binary BRUN at $6000, zero page at $50, maze state at $1000
;     (maze3d.cfg)
;
; Controls: I / up = forward, K / down = backward, J / left = turn left,
; L / right = turn right, M map, H help, A attack, F flee, ESC configuration.
; =============================================
; Original header (POM1):
; =============================================
; =============================================
; GEN2 HGR port — HGR_Maze3D, ported from sketchs/tms9918/game_maze3d/
; TMS_Maze3D.asm (the CodeTank bank build). The game logic — DFS maze,
; pseudo-3D wireframe renderer, map view, HUD, turn-based combat — is
; carried over verbatim; only the Graphics II bitmap PRIMITIVES
; (plot/line/hline/vline/char/x2-text/sprite-blit/clears) are swapped
; for HGR equivalents with the same contracts. Single-region image at
; $6000 on the "GEN2 HGR Color" 48 KB machine (chess model), state in
; low RAM ($0E00 segments), 6000R boots it.
;
; Pixel-space mapping: the TMS 256x192 bitmap becomes 32 HGR byte
; columns (4..35, centred in the 40-byte row). Each 8-px TMS byte
; column lands on one 7-px HGR byte column: bytes go through rev7_tab
; (bit 7 = leftmost -> bit 0 = leftmost, rightmost pixel dropped);
; per-pixel plots clamp x%8 == 7 onto bit 6 so wall edges on those
; columns still render. Text cells / sprite tiles stay 8-aligned in
; TMS coordinates and byte-aligned in HGR — no shifting anywhere.
; The Graphics II per-tile colour table has no HGR counterpart:
; color_rect / fill_color_white are stubs (monochrome; the depth cues
; survive via the stipple fills).
; =============================================
; HGR MAZE 3D - Wizardry-style line maze
; Uncle Bernie's GEN2 HGR Color Card - POM1 / Apple 1
; VERHILLE Arnaud - 2026
;
; A 1976-style first-person dungeon crawler with monsters.
; Backtracker-DFS maze (11x7 cells), pseudo-3D wireframe with
; depth shading (stipple/hatching), top-down map toggle and
; turn-based combat against three regular archetypes and a final dragon.
;
; Controls (IJKL — same physical keys on QWERTY and AZERTY):
;   I = forward          J = turn left
;   K = backward         L = turn right
;   M = toggle map / 3D view
;   A = attack (combat)  F = flee  (combat)
;   ESC = configuration / quit
;
; =============================================
; Assemble: `make` in this directory (ca65 + sprites libs + ld65 with
; apple1_maze3d_hgr.cfg -> "software/Graphic HGR"/HGR_Maze3D.{bin,txt}).
;
; Run in POM1: --preset 11 --load 6000:"software/Graphic HGR/HGR_Maze3D.bin"
; --run 6000, or File > Load the .txt (auto-enables the GEN2 card) then
; 6000R from Wozmon.
; =============================================

; ---- Apple 1 I/O ----
        ; HGR port: tms9918_pad12 / vdp_display_off / vdp_display_on are
        ; local no-op stubs (next to the clear routines) — the GEN2 card
        ; has no VDP bus timing and no display-enable bit.
        ; SCROLL-O-SPRITES 16x16 monster patterns (src/sprites_trollkind.asm and
        ; src/sprites_characters.asm, linked by the Makefile) — drawn as BITMAPS into the
        ; Graphics II pattern table by draw_sprite16_x2/_x4, NOT as hardware
        ; sprites. Layout: 32 bytes = left column rows 0..15, right column
        ; rows 0..15; bit 7 = leftmost (same bit order as the bitmap).
        ; Re-cast juillet 2026 after the community-name audit (the old picks,
        ; made under the pre-audit labels, were actually a Golem, a Hobgoblin
        ; and a FEMALE ARCHER): now the archetypes wear their true faces.
        ; Monster assets are packed at build time; see packed_sprites.inc.
.include "apple2.inc"

; The TMS build VBlank-gated a couple of rebuild bursts; no such
; concept on the framebuffer card.
.macro WAIT_VBLANK_SAFE
.endmacro

; ---- Keys (Apple 1 ASCII | $80, upper-cased by the keyboard) ----
KEY_ESC   = $9B
KEY_FWD   = $C9       ; 'I' forward
KEY_BACK  = $CB       ; 'K' backward
KEY_LEFT  = $CA       ; 'J' turn left
KEY_RIGHT = $CC       ; 'L' turn right
KEY_M     = $CD       ; toggle map / 3D
KEY_H     = $C8       ; help screen (in game)
KEY_A     = $C1       ; attack
KEY_F     = $C6       ; flee
KEY_G     = $C7       ; guard
KEY_P     = $D0       ; drink potion
KEY_SPACE = $A0
KEY_RET   = $8D

; ---- Maze geometry ----
NCOLS   = 11
NROWS   = 7
NCELLS  = 77

NORTH_BIT = $01       ; bit 0 of cell = north passage open
EAST_BIT  = $02       ; bit 1 = east passage open
VISITED   = $80       ; bit 7 = DFS visited flag
SEEN_MOB  = $40       ; bit 6 = a live monster was seen from the corridor
CHEST_BIT = $04
RELIC_BIT = $08
ROOM_BIT  = $10

; ---- Direction codes ----
DIR_N = 0
DIR_E = 1
DIR_S = 2
DIR_W = 3

; ---- Game states ----
ST_TITLE  = 0
ST_HELP   = 1
ST_PLAY3D = 2
ST_PLAYMAP= 3
ST_COMBAT = 4
ST_WIN    = 5
ST_LOSE   = 6
ST_QUIT   = $FF

; ---- Double buffering ----
HUD_BOTH  = 2         ; hud_dirty value: rebuild the HUD on each HGR page
PAGE2_EOR = $60       ; hgr_hi EOR value that moves a line from $2xxx to $4xxx

; ---- Combat ----
NUM_MOBS  = 8
MOB_DEAD  = $FF
MAX_DEPTH = 10

; ---- Player tuning ----
PLAYER_MAX_HP = 20
LAST_FLOOR = 3
SCORE_BASE = $1F00       ; preloaded MAZESCORE: "MZ3", version, best, seed, check

; =============================================
; Off-board RAM (bss, not in output binary)
; =============================================
.segment "GRIDSEG"
grid:       .res NCELLS

.segment "STKSEG"
dfs_stk:    .res NCELLS

.segment "MOBSEG"
mob_col:    .res NUM_MOBS
mob_row:    .res NUM_MOBS
mob_type:   .res NUM_MOBS    ; 0=goblin 1=orc 2=mage 3=dragon ; $FF dead
mob_hp:     .res NUM_MOBS

; =============================================
; Zero page
; =============================================
.zeropage
; --- generic scratch ---
tmp:        .res 1     ; $00
tmp2:       .res 1     ; $01
ptr_lo:     .res 1     ; $02
ptr_hi:     .res 1     ; $03
str_lo:     .res 1     ; $04
str_hi:     .res 1     ; $05

; --- PRNG (Galois LFSR + entropy) ---
prng_lo:    .res 1     ; $06
prng_hi:    .res 1     ; $07

; --- VDP helpers ---
vdp_addr_lo:.res 1     ; $08
vdp_addr_hi:.res 1     ; $09

; --- pixel-plot scratch ---
pix_x:      .res 1     ; $0A
pix_y:      .res 1     ; $0B
pix_byte:   .res 1     ; $0C  cached byte under cursor
pix_mask:   .res 1     ; $0D
pix_addr_lo:.res 1     ; $0E
pix_addr_hi:.res 1     ; $0F

; --- monster-bitmap blit scratch (draw_sprite16_x2/_x4) ---
; sp_ptr / sp_x / sp_y + the blit scratch now live in
; dev/lib/hgr/hgr_sprite_packed.asm supplies the packed blitter scratch and colour
; attributes (sp_cm_ev / sp_cm_od / sp_cbit). Sprite rows are packed at build
; time by tools/pack_sprites.py.
; --- monster cluster (draw_mob_indicator): up to 3 mobs on one cell ---
mob_depth:  .res 1     ; depth 1..10 of the cell currently being drawn
mob_scan_d: .res 1     ; corridor-scan depth cursor (check_front_wall-proof)
mob_cnt:    .res 1     ; monsters found on that cell (0..3)
mob_base:   .res 1     ; (mob_depth-1)*3 — cluster table row
mob_slot_i: .res 1     ; cluster draw loop counter
mob_slot0:  .res 1     ; mob indices on the cell (slot0/1/2 CONTIGUOUS)
mob_slot1:  .res 1
mob_slot2:  .res 1
mob_sz:     .res 1     ; current monster magnify 1/2/4
mob_cur:    .res 1     ; current monster index (for archetype colour)
mob_step:   .res 1     ; row pitch (monster width px = sz*16)
mob_spy:    .res 1     ; shared sp_y for the whole row (same height)
mob_curx:   .res 1     ; running x while laying out the row

; --- double-size text (title "MAZE 3D") ---
x2_src:     .res 1     ; source glyph row (0 or 4)
x2_nib:     .res 1     ; 0=high nibble (left tile), 1=low (right tile)
x2_cx:      .res 1     ; dest cell col/row
x2_cy:      .res 1
x2_row:     .res 1     ; loop cursors
x2_cnt:     .res 1
x2_byte:    .res 1     ; doubled byte (written twice = vertical double)
last_mob_depth: .res 1 ; depth coloured last frame (0=none) -> reset target
; --- colour-table fill (color_rect) ---
cr_x:       .res 1     ; rect origin/size (pixels, multiples of 8)
cr_y:       .res 1
cr_w:       .res 1
cr_h:       .res 1
cr_col:     .res 1     ; colour byte (fg<<4 | bg)
cr_cx:      .res 1     ; color_rect loop cursors
cr_cy:      .res 1

; --- line / Bresenham ---
ln_x0:      .res 1     ; $10
ln_y0:      .res 1
ln_x1:      .res 1
ln_y1:      .res 1
ln_dx:      .res 1     ; $14
ln_dy:      .res 1
ln_sx:      .res 1
ln_sy:      .res 1
ln_err:     .res 1     ; $18  (signed, 16-bit since the GAME6 fix)
ln_err_hi:  .res 1     ;      high byte — 2*err overflows 8 bits for
                       ;      any |dy| > 63 (see line_xy bug note)

; --- DFS gen state ---
cur_row:    .res 1     ; $19
cur_col:    .res 1
stkp:       .res 1
num_dirs:   .res 1
cell_idx:   .res 1     ; $1D
dir_buf:    .res 4     ; $1E-$21

; --- Player state ---
p_col:      .res 1     ; $22
p_row:      .res 1
p_face:     .res 1     ; 0=N 1=E 2=S 3=W
p_hp:       .res 1     ; $25
p_atk:      .res 1
p_def:      .res 1
p_lvl:      .res 1
p_xp:       .res 1     ; $29
p_gold:     .res 1     ; loot collected from slain monsters (0..99 for HUD)
xp_next:    .res 1     ; total-XP threshold for the next level-up
p_floor:    .res 1
dead_type:  .res 1     ; killed foe's type, saved before MOB_DEAD replaces it
p_relic:    .res 1
p_potions:  .res 1
p_chests:   .res 1
p_turns:    .res 1
old_col:    .res 1
old_row:    .res 1
room_idx:   .res 1
p_guard:    .res 1
p_focus:    .res 1
mob_phase:  .res 1
p_seed_lo:  .res 1
p_seed_hi:  .res 1
score_run:  .res 1

; --- Event message shown at the top of the 3D view ---
msg_lo:     .res 1     ; pointer to the current message string (ZP indirect)
msg_hi:     .res 1

; --- Game state ---
gstate:     .res 1     ; $2A
prev_state: .res 1     ; previous gameplay state for combat return
quit_flag:  .res 1
view_mode:  .res 1     ; 0=3D, 1=MAP
hud_dirty:  .res 1     ; >0 = HUD rebuilds left (HUD_BOTH = one per page) (stats/facing
                       ; changed, or we just entered the 3D view); 0 = it
                       ; persists (clear_viewport spares the HUD zone), so
                       ; plain forward/back moves skip it entirely.

; --- Combat scratch ---
cur_mob:    .res 1     ; $2E   index of current foe ($FF=none)
ev_dmg:     .res 1

; --- Render scratch ---
rd_depth:   .res 1     ; $32
rd_col:     .res 1
rd_row:     .res 1
rd_dx:      .res 1
rd_dy:      .res 1     ; $36
rd_face:    .res 1
rd_cell:    .res 1     ; cached cell byte
rd_blocked: .res 1     ; non-zero once front blocked

; --- write_char scratch ---
ch_cx:      .res 1     ; $3A    column 0..31
ch_cy:      .res 1     ; $3B    row    0..23
ch_code:    .res 1     ; $3C
ch_idx:     .res 1     ; $3D

; --- movement scratch ---
mv_dir:     .res 1     ; try_move's direction. MUST NOT live in tmp:
                       ; cell_index_xy does STX tmp and would clobber it
                       ; (the historical game-breaking movement bug)

; --- wait_key timeout counter (bits 16-23) ---
wk_hi:      .res 1

; --- scratch for fill / map ---
fl_y0:      .res 1     ; $3E
fl_y1:      .res 1
fl_x0:      .res 1
fl_x1:      .res 1     ; $41

; --- fast vline scratch (batched 8-row read-modify-write) ---
vl_mask:    .res 1     ; column bit mask
vl_cnt:     .res 1     ; rows in current pattern group (1..8)
vbuf:       .res 8     ; staging buffer (unused on HGR; kept for layout)

; ---- HGR port ZP ----
pix_col:    .res 1     ; dest byte column (4 + pix_x/8) from calc_pix_addr
front_page: .res 1     ; displayed HGR page: 0 = page 1, PAGE2_EOR = page 2
hgr_front_page = front_page   ; dev/lib/hgr/hgr_flip.asm keeps it here (ZP)
hsp_col = mob_curx
; Forward ZP references into hgr_sprite_packed.asm: tell ca65 these live
; in zero page so the packed sprite blitter gets short addressing.
.globalzp sp_ptr, sp_cm_ev, sp_cm_od, sp_cbit
.globalzp sp_wout, sp_yy, sp_lin_lo, sp_lin_hi
.globalzp ht_col, ht_sl, ht_left, ht_wrap, ht_font_lo, ht_font_hi, ht_rev
.globalzp ht_cm_ev, ht_cm_od, ht_cbit, ht_page

.code

; Seed editor state stays outside the crowded zero page.
.segment "BSS"
seed_digits: .res 4
seed_count:  .res 1
seed_value_lo: .res 1
seed_value_hi: .res 1
visible_depth: .res NUM_MOBS
configured_depth: .res 1
sound_enabled: .res 1
config_front: .res 1
active_profile: .res 1
profiles_ready: .res 1
preferences_dirty: .res 1
save_available: .res 1
active_game: .res 1
combat_resuming: .res 1
.code

; =============================================
; main entry
; =============================================
main:
        APPLE2_PREAMBLE
        JSR apple2_zp_save      ; ZP is shared with DOS/BASIC: restored on quit
        JSR score_validate
        ; PRNG seed is a CONSTANT and wait_key mixes in KEY VALUES only
        ; (never a polling counter — see the entropy contract at wait_key),
        ; so a scripted --paste-at-cycle session is fully deterministic
        ; regardless of host-load paste jitter (noise-invariance gate).
        ; Real hardware gets variety the TMS_Snake way: title/help accept
        ; ANY key, each distinct keycode seeds a different dungeon.
        LDA #$5A
        STA prng_lo
        LDA #$3C
        STA prng_hi
        LDA #MAX_DEPTH
        STA configured_depth
        LDA #1
        STA sound_enabled
        STA active_profile
        LDA #0
        STA profiles_ready
        STA preferences_dirty
        STA active_game
        STA combat_resuming
        STA quit_flag
        STA view_mode
        ; MUST zero before the first render: color_reset_last reads
        ; last_mob_depth, and a garbage value indexes the reset_* tables
        ; out of bounds -> color_rect with wild bounds that can write into
        ; the NAME TABLE ($3800+), which is built once at init and never
        ; rebuilt -> PERMANENT corruption (missing wall spans + HUD on a
        ; warm/noisy boot; headless zeroes RAM, so it hid in tests).
        STA last_mob_depth
        ; GEN2 init: park the display on TEXT, wipe HGR page 1 (power-on
        ; SRAM is junk and the card has no display-enable bit), then flip
        ; GRAPHICS + HIRES + PAGE1 + MIXOFF.
        JSR hgr_init_clear
        ; Double buffering: page 1 on screen, drawing goes to page 1 until
        ; the first vdp_display_off picks the hidden page.
        LDA #0
        STA front_page
        JSR set_draw_page
        ; hgr_text8 setup: the game's own font (TMS bit order -> ht_rev=1);
        ; write_char positions every glyph explicitly, so no wrap (40).
        LDA #<font_base
        STA ht_font_lo
        LDA #>font_base
        STA ht_font_hi
        LDA #1
        STA ht_rev
        LDA #4
        STA ht_left
        LDA #40
        STA ht_wrap
        LDA #$7F                ; text colour: white (pass-through)
        STA ht_cm_ev
        STA ht_cm_od
        LDA #0
        STA ht_cbit
        STA ht_page             ; 0: hgr_text8 follows hgr_hi, which
                                ; set_draw_page already points at a page
        ; Zero HGR page 2 -- the first hidden page, shown by the first flip.
        LDA #$40
        STA pix_addr_hi
        LDA #0
        STA pix_addr_lo
        TAY
@zp2:   STA (pix_addr_lo),Y
        INY
        BNE @zp2
        INC pix_addr_hi
        LDX pix_addr_hi
        CPX #$60
        BNE @zp2
        ; drain stale keystrokes left over from Woz Monitor / paste buffer
        JSR drain_kb

main_loop:
        LDA quit_flag
        BEQ @cont
        ; ESC quit: blank the display (R1=$80 idiom) and hand control back
        ; to the Woz Monitor. We were launched with JMP (runv) by the GAME6
        ; menu — there is NO caller frame, so the old bare RTS here popped
        ; stale stack bytes and jumped into the weeds on real hardware.
        JMP apple2_exit         ; restore ZP + text screen, back to DOS
@cont:
        ; ONE intro screen (juillet 2026): the title only. The controls +
        ; objective page is no longer forced here -- it moved behind the
        ; in-game H key (see play_input), and the title points to it.
        JSR show_title
        PHA
        LDA quit_flag
        BEQ @title_ok
        PLA
        JMP main_loop
@title_ok:
        PLA

        CMP #$C3                ; C: continue the selected profile
        BNE @new
        JSR resume_game
        JMP main_loop
@new:   CMP #$D2                ; R: replay the best run's maze seed
        BNE @seed_ready
        LDA SCORE_BASE+4
        BEQ @seed_ready
        LDA SCORE_BASE+5
        STA prng_lo
        LDA SCORE_BASE+6
        STA prng_hi
@seed_ready:
        LDA prng_lo
        STA p_seed_lo
        LDA prng_hi
        STA p_seed_hi

        JSR new_game
        LDA quit_flag
        BNE main_loop

        ; on victory or defeat we fall back to title
        JMP main_loop

; =============================================
; drain_kb: read & ignore any pending keystroke until KBDCR is clear,
; then loop a few thousand cycles to let new keys settle.
; =============================================
drain_kb:
        LDX #0
@lp:    LDA KBD
        BPL @nokey
        BIT KBDSTRB             ; Apple II: clear the strobe explicitly
@nokey: INX
        BNE @lp
        RTS

; =============================================
; new_game - generate maze, init player, place mobs, run gameplay loop
; =============================================
new_game:
        JSR prepare_text
        LDA #1
        STA active_game
        LDA #1
        STA p_floor
        JSR start_floor
        LDA #PLAYER_MAX_HP
        STA p_hp
        LDA #4
        STA p_atk
        LDA #2
        STA p_def
        LDA #1
        STA p_lvl
        LDA #0
        STA p_xp
        STA p_gold
        STA p_chests
        STA p_turns
        LDA #1
        STA p_potions
        LDA #10
        STA xp_next
        LDA #MSG_IDLE
        LDX #MSG_POOL
        JSR msg_rand
        JMP play_loop

; Generate a fresh floor while preserving the hero's stats and gold.
start_floor:
        JSR generate_maze
        JSR decorate_maze
        JSR place_mobs
        LDA #0
        STA p_col
        STA p_row
        STA p_relic
        ; DFS has marked every cell. Reuse bit 7 for exploration.
        LDX #0
@fog:   LDA grid,X
        AND #$7F
        STA grid,X
        INX
        CPX #NCELLS
        BNE @fog
        LDA grid
        ORA #VISITED
        STA grid
        LDA #DIR_E
        STA p_face
        LDA #0
        STA view_mode
        STA last_mob_depth      ; fresh maze: nothing coloured yet
        JSR fill_color_white    ; wipe the title screen's colours
        LDA #HUD_BOTH
        STA hud_dirty           ; first 3D frame must build the HUD
        LDA #ST_PLAY3D
        STA gstate
        RTS

; Between floors, spend loot. C continues; ESC opens configuration.
floor_shop:
@redraw:
        JSR vdp_display_off
        JSR clear_bitmap
        LDA #8
        STA ch_cx
        LDA #2
        STA ch_cy
        LDA #<str_shop_title
        LDX #>str_shop_title
        JSR print_str_ax
        LDA #5
        STA ch_cx
        LDA #6
        STA ch_cy
        LDA #<str_shop_gold
        LDX #>str_shop_gold
        JSR print_str_ax
        LDA #12
        STA ch_cx
        LDA #6
        STA ch_cy
        LDA p_gold
        JSR write_decimal_2d
        LDA #4
        STA ch_cx
        LDA #9
        STA ch_cy
        LDA #<str_shop_heal
        LDX #>str_shop_heal
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #11
        STA ch_cy
        LDA #<str_shop_atk
        LDX #>str_shop_atk
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #13
        STA ch_cy
        LDA #<str_shop_def
        LDX #>str_shop_def
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #15
        STA ch_cy
        LDA #<str_shop_potion
        LDX #>str_shop_potion
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #18
        STA ch_cy
        LDA #<str_shop_next
        LDX #>str_shop_next
        JSR print_str_ax
        JSR vdp_display_on
@key:   JSR wait_key_real
        CMP #KEY_ESC
        BNE @not_escape
        INC quit_flag
        RTS
@not_escape:
        CMP #$C3                ; C: continue
        BNE @not_continue
        RTS
@not_continue:
        CMP #KEY_H
        BNE @not_heal
        LDA p_hp
        CMP #30
        BCS @fail
        LDA #8
        JSR shop_pay
        BCC @fail
        LDA p_hp
        CLC
        ADC #10
        CMP #31
        BCC @store_hp
        LDA #30
@store_hp:
        STA p_hp
        JMP @bought
@not_heal:
        CMP #KEY_A
        BNE @not_atk
        LDA #12
        JSR shop_pay
        BCC @fail
        INC p_atk
        JMP @bought
@not_atk:
        CMP #$C4                ; D: defense
        BNE @not_def
        LDA #12
        JSR shop_pay
        BCC @fail
        INC p_def
        JMP @bought
@not_def:
        CMP #KEY_P
        BNE @key
        LDA p_potions
        CMP #9
        BCS @fail
        LDA #6
        JSR shop_pay
        BCC @fail
        INC p_potions
@bought:
        JSR sound_level
        JMP @redraw
@fail:  JSR sound_wall
        JMP @key

; A=price. Carry set when paid; gold is held to the HUD's two digits.
shop_pay:
        STA tmp2
        LDA p_gold
        CMP tmp2
        BCC @no
        SEC
        SBC tmp2
        STA p_gold
        SEC
        RTS
@no:    CLC
        RTS

score_validate:
        LDA SCORE_BASE
        CMP #'M'
        BNE @reset
        LDA SCORE_BASE+1
        CMP #'Z'
        BNE @reset
        LDA SCORE_BASE+2
        CMP #'3'
        BNE @reset
        LDA SCORE_BASE+3
        CMP #1
        BNE @reset
        LDA SCORE_BASE+4
        EOR SCORE_BASE+5
        EOR SCORE_BASE+6
        EOR #$A5
        CMP SCORE_BASE+7
        BEQ @valid
@reset: LDX #0
@copy:  LDA score_initial,X
        STA SCORE_BASE,X
        INX
        CPX #8
        BNE @copy
@valid: RTS

; Only a completed run can set a record. Score rewards found caches and
; experience, then subtracts one point per four moves.
score_finish:
        LDA #100
        STA score_run
        LDX p_chests
@cache: CPX #0
        BEQ @level
        LDA score_run
        CLC
        ADC #10
        STA score_run
        DEX
        JMP @cache
@level: LDX p_lvl
@level_loop:
        CPX #0
        BEQ @turns
        LDA score_run
        CLC
        ADC #5
        STA score_run
        DEX
        JMP @level_loop
@turns: LDA p_turns
        LSR
        LSR
        STA tmp
        LDA score_run
        SEC
        SBC tmp
        BCS @score_ok
        LDA #0
@score_ok:
        STA score_run
        CMP SCORE_BASE+4
        BCC @done
        BEQ @done
        STA SCORE_BASE+4
        LDA p_seed_lo
        STA SCORE_BASE+5
        LDA p_seed_hi
        STA SCORE_BASE+6
        LDA score_run
        EOR p_seed_lo
        EOR p_seed_hi
        EOR #$A5
        STA SCORE_BASE+7
        JSR disk_protected
        BCS @done
        JSR dos_cmd_new
        LDA #<str_score_save
        LDY #>str_score_save
        JSR dos_cmd_add
        JSR dos_cmd_run
@done:  RTS

score_initial:
        .byte 'M','Z','3',1,0,0,0,$A5
str_score_save:
        .byte "BSAVE MAZESCORE,A$1F00,L$0008",0

sound_wall:
        LDA #$18
        LDX #$E0
        JMP tone
sound_attack:
        LDA #$18
        LDX #$48
        JMP tone
sound_hurt:
        LDA #$28
        LDX #$B0
        JMP tone
sound_level:
        LDA #$24
        LDX #$90
        JSR tone
        LDA #$28
        LDX #$60
        JMP tone
sound_stairs:
        LDA #$30
        LDX #$B0
        JSR tone
        LDA #$30
        LDX #$78
        JMP tone
sound_victory:
        JSR sound_level
        LDA #$50
        LDX #$48
        JMP tone
sound_death:
        LDA #$30
        LDX #$70
        JSR tone
        LDA #$48
        LDX #$D0
        JMP tone

play_loop:
        LDA quit_flag
        BEQ @go
        RTS
@go:
        LDA gstate
        CMP #ST_PLAY3D
        BNE @c1
        JSR render_3d
        JSR play_input
        JMP play_loop
@c1:    CMP #ST_PLAYMAP
        BNE @c2
        JSR render_map
        JSR play_input
        JMP play_loop
@c2:    CMP #ST_COMBAT
        BNE @c3
        JSR run_combat
        JMP play_loop
@c3:    CMP #ST_WIN
        BNE @c4
        JSR show_win
        RTS
@c4:    CMP #ST_LOSE
        BNE @done
        JSR show_lose
        RTS
@done:
        RTS

; =============================================
; play_input - read one key, update state
; =============================================
play_input:
        JSR wait_key
        CMP #KEY_ESC
        BNE @n1
        INC quit_flag
        RTS
@n1:    CMP #KEY_M
        BNE @n2
        ; toggle view. Wipe colours ONCE here (not in the per-frame
        ; render_map/render_3d): otherwise the 3D monster/HUD tint would
        ; bleed onto the map grid and vice-versa.
        JSR fill_color_white
        LDA #HUD_BOTH
        STA hud_dirty           ; the map full-clears the HUD zone; rebuild
                                ; it when we return to 3D
        LDA view_mode
        EOR #$01
        STA view_mode
        BNE @ismap
        LDA #ST_PLAY3D
        STA gstate
        RTS
@ismap:
        LDA #ST_PLAYMAP
        STA gstate
        RTS
@n2:    CMP #KEY_LEFT
        BNE @n3
        ; turn left
        LDA p_face
        SEC
        SBC #1
        AND #$03
        STA p_face
        JSR hush_narrator       ; turning in place silences the narrator
        RTS
@n3:    CMP #KEY_RIGHT
        BNE @n4
        ; turn right
        LDA p_face
        CLC
        ADC #1
        AND #$03
        STA p_face
        JSR hush_narrator
        RTS
@n4:    CMP #KEY_FWD
        BNE @n5
        ; forward. Fresh narrator patter as we advance (a fight, if it is
        ; triggered, overrides it with a WIN/PERIL line afterwards).
        JSR narrate_step
        LDA p_face
        JSR try_move
        RTS
@n5:    CMP #KEY_BACK
        BNE @n6
        ; backward = move opposite of facing
        JSR narrate_step
        LDA p_face
        CLC
        ADC #2
        AND #$03
        JSR try_move
        RTS
@n6:    CMP #KEY_H
        BNE @other
        ; help screen on demand; when it returns, play_loop redraws the
        ; current view (gstate unchanged).
        JSR show_help
        LDA #HUD_BOTH           ; Apple II port fix: the help page wiped the HUD
        STA hud_dirty           ; zone too, so rebuild it (upstream left the
        RTS                     ; "PRESS ANY KEY..." line on screen)
@other: CMP #KEY_P
        BNE @unknown
        JSR drink_potion
        RTS
@unknown:
        JMP play_input          ; unknown key, or wait_key's synthetic
                                ; timeout SPACE: wait again WITHOUT
                                ; returning — the old fall-through RTS made
                                ; play_loop rebuild the whole frame every
                                ; ~0.7 s even with no input, so the screen
                                ; was mid-repaint most of the time
                                ; (half-drawn-frame bug).

; =============================================
; try_move: attempt to move in direction A.
; If blocked by wall, ignore. After move, check exit + mob spawn.
; BUG HISTORY (juillet 2026): the direction used to be saved in tmp —
; but cell_index_xy does STX tmp, so the direction was silently replaced
; by p_col before the very first compare. Every move key thus moved in
; the direction equal to the player's COLUMN NUMBER (usually blocked
; north at col 0): the game was never walkable. Direction now lives in
; the dedicated mv_dir.
; =============================================
try_move:
        STA mv_dir              ; save direction (cell_index_xy-proof)
        LDA p_col
        STA old_col
        LDA p_row
        STA old_row
        JMP @check
@blocked:
        JSR sound_wall
        RTS
@check:
        LDX p_col
        LDY p_row
        JSR cell_index_xy       ; A = idx (clobbers tmp!)
        TAX
        LDA grid,X
        STA tmp2                ; current cell flags
        LDA mv_dir
        CMP #DIR_N
        BNE @ne
        LDA tmp2
        AND #NORTH_BIT
        BEQ @blocked
        DEC p_row
        JMP @arrive
@ne:    CMP #DIR_E
        BNE @ns
        LDA tmp2
        AND #EAST_BIT
        BEQ @blocked
        INC p_col
        JMP @arrive
@ns:    CMP #DIR_S
        BNE @nw
        ; SOUTH: south neighbor's NORTH passage
        LDA p_row
        CMP #(NROWS-1)
        BCS @blocked
        LDX p_col
        LDY p_row
        INY
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #NORTH_BIT
        BEQ @blocked
        INC p_row
        JMP @arrive
@nw:    ; WEST: west neighbor's EAST passage
        LDA p_col
        BEQ @blocked
        LDX p_col
        DEX
        LDY p_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #EAST_BIT
        BEQ @blocked
        DEC p_col
@arrive:
        LDA p_turns
        CMP #$FF
        BEQ @turn_counted
        INC p_turns
@turn_counted:
        LDX p_col
        LDY p_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        ORA #VISITED
        STA grid,X
        JSR collect_cell
        ; reached exit?
        LDA p_col
        CMP #(NCOLS-1)
        BNE @nowin
        LDA p_row
        CMP #(NROWS-1)
        BNE @nowin
        LDA p_relic
        BNE @has_relic
        LDA #<str_relic_blocks
        STA msg_lo
        LDA #>str_relic_blocks
        STA msg_hi
        LDA #HUD_BOTH
        STA hud_dirty
        JSR sound_wall
        RTS
@has_relic:
        LDA p_floor
        CMP #LAST_FLOOR
        BNE @next_floor
        ; The final exit opens only after the dragon has fallen.
        LDA mob_type+NUM_MOBS-1
        CMP #MOB_DEAD
        BNE @dragon_alive
        LDA #ST_WIN
        STA gstate
        JSR score_finish
        JSR sound_victory
        RTS
@dragon_alive:
        LDA #<str_dragon_blocks
        STA msg_lo
        LDA #>str_dragon_blocks
        STA msg_hi
        RTS
@next_floor:
        JSR floor_shop
        LDA quit_flag
        BNE @leave
        INC p_floor
        JSR start_floor
        JSR sound_stairs
@leave: RTS
@nowin:
        ; mob on this cell?
        JSR find_mob_here
        BMI @no_mob              ; A=$FF -> no mob
        STA cur_mob
        LDA gstate
        STA prev_state
        LDA #ST_COMBAT
        STA gstate
@no_mob:
        RTS

; X = destination cell. Picking up a cache or relic happens once.
collect_cell:
        LDA grid,X
        AND #RELIC_BIT
        BEQ @chest
        LDA grid,X
        AND #($FF-RELIC_BIT)
        STA grid,X
        LDA #1
        STA p_relic
        LDA #<str_relic_found
        STA msg_lo
        LDA #>str_relic_found
        STA msg_hi
        LDA #HUD_BOTH
        STA hud_dirty
        JSR sound_level
        RTS
@chest:
        LDA grid,X
        AND #CHEST_BIT
        BEQ @done
        LDA grid,X
        AND #($FF-CHEST_BIT)
        STA grid,X
        INC p_chests
        LDA p_gold
        CLC
        ADC #6
        CMP #100
        BCC @store_gold
        LDA #99
@store_gold:
        STA p_gold
        JSR random
        AND #1
        BEQ @no_potion
        LDA p_potions
        CMP #9
        BCS @no_potion
        INC p_potions
@no_potion:
        LDA #<str_cache_found
        STA msg_lo
        LDA #>str_cache_found
        STA msg_hi
        LDA #HUD_BOTH
        STA hud_dirty
        JSR sound_level
@done:  RTS

; Spend one potion to restore 10 HP, up to 30. Carry signals success.
drink_potion:
        LDA p_potions
        BEQ @no
        LDA p_hp
        CMP #30
        BCS @no
        DEC p_potions
        CLC
        ADC #10
        CMP #31
        BCC @store
        LDA #30
@store: STA p_hp
        LDA #HUD_BOTH
        STA hud_dirty
        JSR sound_level
        SEC
        RTS
@no:    CLC
        RTS

; =============================================
; cell_index_xy: X=col, Y=row -> A = row*NCOLS + col
; =============================================
cell_index_xy:
        LDA row_offset,Y
        STX tmp
        CLC
        ADC tmp
        RTS

; =============================================
; find_mob_here: returns A = mob index or $FF if none
; =============================================
find_mob_here:
        LDX #0
@lp:    LDA mob_type,X
        CMP #MOB_DEAD
        BEQ @next
        LDA mob_col,X
        CMP p_col
        BNE @next
        LDA mob_row,X
        CMP p_row
        BNE @next
        TXA
        RTS
@next:  INX
        CPX #NUM_MOBS
        BNE @lp
        LDA #$FF
        RTS

; =============================================
; place_mobs - random monster placement on free cells
; (avoids start (0,0) and exit (NCOLS-1, NROWS-1))
; =============================================
place_mobs:
        LDX #0
@lp:    JSR random
        ; pick column 1..NCOLS-1
        AND #$0F
        CMP #NCOLS
        BCC @okc
        SBC #NCOLS
@okc:   STA mob_col,X
        JSR random
        AND #$07
        CMP #NROWS
        BCC @okr
        SBC #NROWS
@okr:   STA mob_row,X
        ; reject start
        LDA mob_col,X
        ORA mob_row,X
        BNE @not_start
        JMP @retry
@not_start:
        ; reject exit
        LDA mob_col,X
        CMP #(NCOLS-1)
        BNE @keep
        LDA mob_row,X
        CMP #(NROWS-1)
        BNE @keep
        JMP @retry
@keep:
        STX ch_idx
        LDY mob_row,X
        LDA mob_col,X
        TAX
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #(CHEST_BIT|RELIC_BIT)
        BEQ @free_cell
        LDX ch_idx
        JMP @retry
@free_cell:
        LDX #0
        LDA #0
        STA tmp2
@stack: CPX ch_idx
        BEQ @stack_ok
        LDY ch_idx
        LDA mob_col,X
        CMP mob_col,Y
        BNE @stack_next
        LDA mob_row,X
        CMP mob_row,Y
        BNE @stack_next
        INC tmp2
@stack_next:
        INX
        BNE @stack
@stack_ok:
        LDX ch_idx
        LDA tmp2
        CMP #3
        BCC @available
        JMP @retry
@available:
        ; assign type round-robin: 0,1,2,0,1,2,...
        TXA
        STA tmp
        LDY #0
@modlp: LDA tmp
        CMP #3
        BCC @okmod
        SBC #3
        STA tmp
        JMP @modlp
@okmod:
        ; Floors two and three have tougher regular foes. Slot 7 on the
        ; last floor is the unique dragon, irrespective of this rotation.
        STA tmp
        LDA p_floor
        CMP #1
        BEQ @type
        LDA tmp
        CMP #2
        BCS @floor_type_done
        CLC
        ADC #1
        STA tmp
@floor_type_done:
        LDA p_floor
        CMP #LAST_FLOOR
        BNE @type
        CPX #(NUM_MOBS-1)
        BNE @type
        LDA #3
        STA tmp
@type:
        LDA tmp
        STA mob_type,X
        ; HP = 4 + 3*type + floor bonus + 1d4
        ASL                    ; type * 2
        CLC
        ADC tmp                ; +type -> 3*type
        CLC
        ADC #4
        CLC
        ADC p_floor
        SEC
        SBC #1
        STA tmp2
        JSR random
        AND #$03
        CLC
        ADC tmp2
        STA mob_hp,X
        INX
        CPX #NUM_MOBS
        BEQ @done
        JMP @lp
@done:
        RTS
@retry:
        ; reroll without advancing X
        JMP @lp

; =============================================
; generate_maze: recursive backtracker DFS
; (port of Maze2_Backtracker.asm to 11x7)
; =============================================
generate_maze:
        LDX #0
        TXA
@cl:    STA grid,X
        INX
        CPX #NCELLS
        BNE @cl

        LDA #0
        STA cur_row
        STA cur_col
        STA stkp
        STA cell_idx
        LDA #VISITED
        STA grid

dfs_loop:
        LDY #0
        LDA cur_row
        BEQ @sn
        LDA cell_idx
        SEC
        SBC #NCOLS
        TAX
        LDA grid,X
        BMI @sn
        LDA #DIR_N
        STA dir_buf,Y
        INY
@sn:    LDA cur_col
        CMP #(NCOLS-1)
        BCS @se
        LDX cell_idx
        INX
        LDA grid,X
        BMI @se
        LDA #DIR_E
        STA dir_buf,Y
        INY
@se:    LDA cur_row
        CMP #(NROWS-1)
        BCS @ss
        LDA cell_idx
        CLC
        ADC #NCOLS
        TAX
        LDA grid,X
        BMI @ss
        LDA #DIR_S
        STA dir_buf,Y
        INY
@ss:    LDA cur_col
        BEQ @sw
        LDX cell_idx
        DEX
        LDA grid,X
        BMI @sw
        LDA #DIR_W
        STA dir_buf,Y
        INY
@sw:    STY num_dirs
        CPY #0
        BEQ @bt
        ; pick random direction modulo num_dirs
        JSR random
        AND #$03
@mod:   CMP num_dirs
        BCC @okm
        SEC
        SBC num_dirs
        JMP @mod
@okm:   TAX
        LDA dir_buf,X
        PHA
        LDX stkp
        LDA cell_idx
        STA dfs_stk,X
        INC stkp
        PLA
        CMP #DIR_E
        BEQ @ge
        CMP #DIR_S
        BEQ @gs
        CMP #DIR_W
        BEQ @gw
        ; NORTH
        LDX cell_idx
        LDA grid,X
        ORA #NORTH_BIT
        STA grid,X
        DEC cur_row
        JMP @mark
@ge:    LDX cell_idx
        LDA grid,X
        ORA #EAST_BIT
        STA grid,X
        INC cur_col
        JMP @mark
@gs:    LDA cell_idx
        CLC
        ADC #NCOLS
        TAX
        LDA grid,X
        ORA #NORTH_BIT
        STA grid,X
        INC cur_row
        JMP @mark
@gw:    LDX cell_idx
        DEX
        LDA grid,X
        ORA #EAST_BIT
        STA grid,X
        DEC cur_col
@mark:  LDX cur_row
        LDA row_offset,X
        CLC
        ADC cur_col
        STA cell_idx
        TAX
        LDA grid,X
        ORA #VISITED
        STA grid,X
        JMP dfs_loop
@bt:    LDA stkp
        BEQ @done
        DEC stkp
        LDX stkp
        LDA dfs_stk,X
        ; recover row,col by div/mod NCOLS
        LDX #0
@dv:    CMP #NCOLS
        BCC @dvd
        SEC
        SBC #NCOLS
        INX
        JMP @dv
@dvd:   STA cur_col
        STX cur_row
        LDX cur_row
        LDA row_offset,X
        CLC
        ADC cur_col
        STA cell_idx
        JMP dfs_loop
@done:  RTS

; Add a recognizable 2x2 chamber, three extra links, and three caches.
; All passages from DFS remain open, so every new floor stays connected.
decorate_maze:
        JSR random
        AND #$07
        CMP #6
        BCC @room_col
        SEC
        SBC #6
@room_col:
        CLC
        ADC #3                  ; chamber x = 3..8
        STA cur_col
        JSR random
        AND #$03
        CLC
        ADC #2                  ; chamber y = 2..5
        STA cur_row
        LDY cur_row
        LDX cur_col
        JSR cell_index_xy
        STA room_idx
        TAX
        LDA grid,X
        ORA #(EAST_BIT|ROOM_BIT)
        STA grid,X
        INX
        LDA grid,X
        ORA #ROOM_BIT
        STA grid,X
        LDX room_idx
        TXA
        CLC
        ADC #NCOLS
        TAX
        LDA grid,X
        ORA #(NORTH_BIT|EAST_BIT|ROOM_BIT)
        STA grid,X
        INX
        LDA grid,X
        ORA #(NORTH_BIT|ROOM_BIT|RELIC_BIT)
        STA grid,X

        LDA #3
        STA num_dirs
@extra:
        JSR random
        AND #$0F
        CMP #(NCOLS-1)
        BCS @extra
        STA cur_col
        JSR random
        AND #$07
        CMP #NROWS
        BCS @extra
        TAY
        LDX cur_col
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #EAST_BIT
        BNE @extra
        LDA grid,X
        ORA #EAST_BIT
        STA grid,X
        DEC num_dirs
        BNE @extra

        LDA #3
        STA num_dirs
@cache:
        JSR random
        AND #$7F
        BEQ @cache
        CMP #(NCELLS-1)
        BCS @cache
        TAX
        LDA grid,X
        AND #(CHEST_BIT|RELIC_BIT)
        BNE @cache
        LDA grid,X
        ORA #CHEST_BIT
        STA grid,X
        DEC num_dirs
        BNE @cache
        RTS

; =============================================
; random: 16-bit Galois LFSR
; =============================================
random:
        LDA prng_lo
        ASL
        ROL prng_hi
        BCC @nf
        EOR #$2D
@nf:    STA prng_lo
        ; mix prng_hi a bit so place_mobs doesn't loop
        LDA prng_hi
        ASL
        ADC prng_lo
        STA prng_hi
        LDA prng_lo
        RTS

; =============================================
; wait_key: spin until key, stir entropy with the KEY VALUE (only).
; Reads KBD only once (a second read clears the strobe and would
; consume a fresh queued character if any).
;
; ENTROPY CONTRACT (juillet 2026, Snake idiom): the polling loop must
; NOT touch the PRNG. An older revision INC'd prng_lo every iteration
; ("raw timer" seeding) — under POM1's --paste-at-cycle a few thousand
; cycles of host-load slice jitter in key delivery then produced a
; COMPLETELY different maze per run, breaking the noise-invariance /
; determinism gate. Mixing only the key VALUE is paste-jitter-proof:
; the dungeon depends solely on WHICH keys were pressed before
; generation. On real hardware variety comes from the same place as
; TMS_Snake's: the title/help screens accept ANY key, so each distinct
; key press seeds a different dungeon, and in-game combat rolls keep
; consuming draws state-dependently.
;
; A 24-bit polling counter gives the loop a hard stop after ~3 s of
; CPU time; if it fires we return $A0 (a synthetic SPACE) so the
; title / help / win / lose screens can never wedge the game on a
; sticky keyboard / focus issue (and double as a slow attract mode).
; In normal use a real keypress trips the KBDCR test long before the
; counter saturates. In gameplay/combat the synthetic SPACE is ignored
; WITHOUT a repaint (see play_input / run_combat).
; =============================================
wait_key:
        LDA #0
        STA vdp_addr_lo         ; wkey bits 0-7
        STA vdp_addr_hi         ; wkey bits 8-15
        STA wk_hi               ; wkey bits 16-23
@spin:
        LDA KBD
        BPL @nokey
        BIT KBDSTRB
        JSR key_fold
        CMP #KEY_ESC
        BNE @entropy
        JSR configuration_menu
        LDA quit_flag
        BNE @quit
        JMP wait_key
@quit:  LDA #KEY_ESC
        RTS
@entropy:
        PHA
        EOR prng_lo
        STA prng_lo
        PLA
        RTS
@nokey:
        INC vdp_addr_lo
        BNE @spin
        INC vdp_addr_hi
        LDA vdp_addr_hi
        BNE @spin
        INC wk_hi
        LDA wk_hi
        CMP #3                  ; 3 * 65536 iters * ~15c = ~2.9 s at 1 MHz
        BCC @spin
        ; timeout: synthetic SPACE so screens still advance
        LDA #$A0
        RTS

; wait_key_real: block until a REAL key -- no timeout. The menu screens
; (title/help/win/lose) use this so they actually WAIT for the player
; instead of auto-advancing on wait_key's ~3 s synthetic SPACE. Mixing
; the key VALUE into the PRNG also seeds the maze from WHICH key was
; pressed (real-hardware variety, the wait_key entropy contract).
wait_key_real:
@spin:  LDA KBD
        BPL @spin
        BIT KBDSTRB
        JSR key_fold
        CMP #KEY_ESC
        BNE @entropy
        JSR configuration_menu
        LDA quit_flag
        BNE @quit
        JMP wait_key_real
@quit:  LDA #KEY_ESC
        RTS
@entropy:
        PHA
        EOR prng_lo
        STA prng_lo
        PLA
        RTS

; key_fold: Apple II keyboard -> the Apple-1 key codes the game compares
; against. A = raw KBD byte (bit 7 set). Lower case folds to upper case (a
; //e or a host keyboard sends it) and the arrows alias the movement keys:
; left = J (turn left), right = L, up = I (forward), down = K (backward).
key_fold:
        CMP #$E1                ; 'a' | $80
        BCC @arrows
        CMP #$FB                ; past 'z' | $80
        BCS @done
        AND #$DF
        RTS
@arrows:
        CMP #KC_LEFT | $80
        BNE @r
        LDA #KEY_LEFT
        RTS
@r:     CMP #KC_RIGHT | $80
        BNE @u
        LDA #KEY_RIGHT
        RTS
@u:     CMP #KC_UP | $80
        BNE @d
        LDA #KEY_FWD
        RTS
@d:     CMP #KC_DOWN | $80
        BNE @done
        LDA #KEY_BACK
@done:  RTS

; ESC pauses every input context. Draw the menu on the hidden page once;
; update its values in place, preserving the previous screen for resume.
configuration_menu:
        LDA front_page
        STA config_front
        JSR vdp_display_off
        JSR clear_bitmap
        LDA #<str_config
        LDX #>str_config
        LDY #4
        JSR draw_str_centered
        LDA #4
        STA ch_cx
        LDA #8
        STA ch_cy
        LDA #<str_config_sound
        LDX #>str_config_sound
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #10
        STA ch_cy
        LDA #<str_config_depth
        LDX #>str_config_depth
        JSR print_str_ax
        LDA #<str_config_resume
        LDX #>str_config_resume
        LDY #14
        JSR draw_str_centered
        LDA #<str_config_save
        LDX #>str_config_save
        LDY #16
        JSR draw_str_centered
        LDA #<str_config_quit
        LDX #>str_config_quit
        LDY #18
        JSR draw_str_centered
        JSR configuration_values
        JSR vdp_display_on
@wait:  LDA KBD
        BPL @wait
        BIT KBDSTRB
        JSR key_fold
        CMP #KEY_ESC
        BEQ @resume
        CMP #KEY_RET
        BEQ @resume
        CMP #$D2                ; R resume
        BEQ @resume
        CMP #$D1                ; Q quit to DOS
        BEQ @quit
        CMP #$D7                ; W explicitly saves the current game
        BNE @sound
        JSR manual_save
        BCC @save_failed
        LDA #<str_config_saved
        LDX #>str_config_saved
        JMP @save_status
@save_failed:
        LDA #<str_config_no_save
        LDX #>str_config_no_save
@save_status:
        LDY #20
        JSR draw_str_centered
        JMP @wait
@sound: CMP #$D3                ; S sound on/off
        BNE @depth
        LDA sound_enabled
        EOR #1
        STA sound_enabled
        JMP @update
@depth: CMP #$C4                ; D cycles 4,6,8,10 visible cells
        BNE @wait
        LDA configured_depth
        CLC
        ADC #2
        CMP #11
        BCC @store
        LDA #4
@store: STA configured_depth
@update:
        LDA #1
        STA preferences_dirty
        JSR configuration_values
        JMP @wait
@quit:  LDA #1
        STA quit_flag
@resume:
        JSR preferences_save
        LDA config_front
        JSR set_draw_page
        JSR vdp_display_on
        LDA #HUD_BOTH
        STA hud_dirty
        RTS

configuration_values:
        LDA #22
        STA ch_cx
        LDA #8
        STA ch_cy
        LDA sound_enabled
        BEQ @off
        LDA #<str_on
        LDX #>str_on
        JMP @sound
@off:   LDA #<str_off
        LDX #>str_off
@sound: JSR print_str_ax
        LDA #22
        STA ch_cx
        LDA #10
        STA ch_cy
        LDA configured_depth
        JMP write_decimal_2d

; =============================================
; init_vdp_g2 - Graphics II (bitmap) mode
;   pattern  $0000-$17FF (6144 B)
;   color    $2000-$37FF (6144 B)
;   name     $3800-$3AFF (768 B, linear: cell N -> pattern N within third)
;   sprite attr $3B00, sprite gen $1800
;
; R0=$02 M3=1, R1=$C0 16K+screen on,
; R2=$0E -> $3800 name table
; R3=$FF color table at $2000 (6K)
; R4=$03 pattern table at $0000 (6K)
; R5=$76 sprite attr at $3B00
; R6=$03 sprite gen at $1800
; R7=$F1 fg=white bg=black
; =============================================
; TMS9918 compatibility stubs — the pad JSRs sprinkled through the kept
; game code and the display-blank pair become no-ops on the GEN2 card.
; =============================================
tms9918_pad12:
        RTS

; vdp_display_off / _on: the TMS build blanked the display (R1 bit 6)
; around every full redraw so the player never watched the frame being
; drawn; the GEN2 port showed a black page 2 meanwhile. This Apple II port
; DOUBLE-BUFFERS instead:
;   vdp_display_off  draw target := the hidden page (nothing changes on
;                    screen: the previous picture stays up)
;   vdp_display_on   show the page just drawn (one soft-switch read). It is
;                    now the front page AND still the draw target, so the
;                    small in-place updates that follow a full screen
;                    (combat_update_hp) land on the visible page.
; Everything the game writes goes through hgr_hi (clear_span,
; calc_pix_addr, vline, x2_put, hgr_text8, hgr_sprite16), so switching the
; draw page is one pass over that table -- see set_draw_page.
; The three routines and draw_page are dev/lib/hgr/hgr_flip.asm (included at
; the end of this file); front_page above is its hgr_front_page.
vdp_display_off = hgr_draw_hidden
vdp_display_on  = hgr_show_draw
set_draw_page   = hgr_set_draw_page
draw_page       = hgr_draw_page

; hgr_bitmask: pixel (x & 7) -> HGR bit mask (bit 0 = leftmost pixel,
; 7 px/byte, bit 7 = palette group kept clear). The TMS bitmap byte is
; 8 px wide; HGR shows 7 — pixel 7 of each source byte column CLAMPS
; onto bit 6 instead of vanishing, so a wall edge sitting on an
; x = 7 (mod 8) column still renders (merged with column 6).
hgr_bitmask:
        .byte $01, $02, $04, $08, $10, $20, $40, $40

; (rev7_tab — TMS bit order -> HGR — comes from dev/lib/hgr/rev7.inc;
; write_char and x2_tile below use it for their 8-px-grid glyphs.)

; =============================================
; clear_viewport / clear_bitmap / clear_hud — zero a scanline band of
; the HGR framebuffer (full 40-byte rows; the never-drawn side margins
; are black anyway). Same row semantics as the TMS versions:
;   clear_viewport  y 0..159  (3D corridor; HUD zone spared)
;   clear_bitmap    y 0..191  (map / combat / menus)
;   clear_hud       y 160..191
; cr_cx / cr_cy are free outside color_rect (a stub here) and serve as
; end/current scanline scratch. Clobbers A, X, Y.
; =============================================
clear_viewport = hgr_clear_viewport160
clear_bitmap = hgr_clear_visible
clear_hud = hgr_clear_hud32
clear_span = hgr_clear_rows
; =============================================
; calc_pix_addr  (input pix_x, pix_y)
; HGR port: pix_addr_lo/hi = hgr scanline base for pix_y (interleaved
; layout via the hgr_lo/hi tables), pix_col = dest byte column
; 4 + pix_x/8 — each 8-px TMS byte column maps onto one 7-px HGR byte
; column, the whole 256-px TMS screen centred as byte columns 4..35.
; =============================================
calc_pix_addr:
        LDY pix_y
        LDA hgr_lo,Y
        STA pix_addr_lo
        LDA hgr_hi,Y
        STA pix_addr_hi
        LDA pix_x
        LSR
        LSR
        LSR
        CLC
        ADC #4
        STA pix_col
        RTS

; =============================================
; plot_set  (pix_x, pix_y) — OR one pixel into the framebuffer.
; =============================================
plot_set:
        ; bounds check (Y only; X is unsigned 0..255 always in range)
        LDA pix_y
        CMP #192
        BCS plot_done
        JSR calc_pix_addr
        LDA pix_x
        AND #$07
        TAX
        LDA hgr_bitmask,X
        LDY pix_col
        ORA (pix_addr_lo),Y
        STA (pix_addr_lo),Y
plot_done:
        RTS

; =============================================
; line_xy: convert virtual TMS endpoints, then use the native HGR kernel.
; Endpoints and renderer scratch are modified. All endpoints must be on-screen.
; =============================================
line_xy:
        ; Targeted fdraw adaptation (Andy McFadden, Apache-2.0): dominant
        ; axis loops, X = scanline, Y = byte column, incremental bit mask.
        ; Work in native HGR pixels AFTER converting the virtual endpoints.
        ; Unlike the old loop, no 16-bit error tests / division per pixel.
        LDX ln_x0
        LDA native_x,X
        STA ln_x0
        LDX ln_x1
        LDA native_x,X
        STA ln_x1
        JMP hgr_line8

native_x:
.repeat 256, I
    .if (I .mod 8) = 7
        .byte 28 + (I / 8) * 7 + 6
    .else
        .byte 28 + (I / 8) * 7 + (I .mod 8)
    .endif
.endrepeat

; =============================================
; hline: horizontal line from (fl_x0,fl_y0) to (fl_x1,fl_y0), x0 <= x1.
; Byte-oriented: an 8-aligned full span stores one $7F byte (7 lit px —
; the 8th source pixel falls in the dropped column); edge pixels go
; through plot_set.
; =============================================
hline:
        ; fdraw-style byte spans: two masked ends and direct full-byte stores.
        LDY fl_y0
        LDA hgr_lo,Y
        STA pix_addr_lo
        LDA hgr_hi,Y
        STA pix_addr_hi
        LDA fl_x1
        AND #7
        TAX
        LDA span_right,X
        STA tmp2
        LDA fl_x1
        LSR
        LSR
        LSR
        CLC
        ADC #4
        STA pix_col
        LDA fl_x0
        AND #7
        TAX
        LDA span_left,X
        STA tmp
        LDA fl_x0
        LSR
        LSR
        LSR
        CLC
        ADC #4
        TAY
        JMP hgr_hspan
span_left:  .byte $7F,$7E,$7C,$78,$70,$60,$40,$40
span_right: .byte $01,$03,$07,$0F,$1F,$3F,$7F,$7F

vline:
        ; Keep the scanline in X and byte column in Y throughout the loop.
        LDA fl_y1
        CMP #192
        BCC @valid
        LDA #191
@valid: CLC
        ADC #1
        STA tmp2
        LDA fl_x0
        AND #7
        TAX
        LDA hgr_bitmask,X
        STA tmp
        LDA fl_x0
        LSR
        LSR
        LSR
        CLC
        ADC #4
        TAY
        LDX fl_y0
        LDA tmp2
        JMP hgr_vspan

; =============================================
; write_char: place 8x8 glyph at cell (ch_cx, ch_cy); ch_code = ASCII.
; Thin wrapper over hgr_putc8 (dev/lib/hgr/hgr_text8.asm): byte column
; 4 + cx, top scanline cy*8; the game font is TMS bit order, so main:
; arms ht_rev = 1 once at boot (glyph rows pass through rev7_tab).
; =============================================
write_char:
        LDA ch_cx
        CLC
        ADC #4
        STA ht_col
        LDA ch_cy
        ASL
        ASL
        ASL
        STA ht_sl
        LDA ch_code
        JMP hgr_putc8

; =============================================
; draw_str_x2: print the NUL-terminated string (str_lo/hi) at DOUBLE size
; starting at cell (ch_cx, ch_cy). Each glyph becomes 16x16 (a 2x2 cell
; block); the cursor advances 2 cells per character. Used for the big
; "MAZE 3D" title. ch_cy is preserved; ch_cx is advanced.
; =============================================
write_str:
        LDA #0
        STA ch_idx
@lp:    LDY ch_idx
        LDA (str_lo),Y
        BEQ @done
        STA ch_code
        JSR write_char
        INC ch_cx
        INC ch_idx
        BNE @lp
@done:  RTS

; helper: print string (ax pointer) at (ch_cx, ch_cy)
print_str_ax:
        STA str_lo
        STX str_hi
        JMP write_str

; set_msg: A=lo, X=hi -> current event message pointer (shown on row 23).
set_msg:
        STA msg_lo
        STX msg_hi
        RTS

; Narrator pools (index into msg_ptr_lo/hi): base + count.
MSG_IDLE  = 0
MSG_WIN   = 32
MSG_PERIL = 64
MSG_POOL  = 32

; msg_rand: A = pool base index, X = pool count. Picks a random line from
; the pool and points the narrator (msg_lo/hi) at it. Clobbers A/X/Y, tmp.
msg_rand:
        STA tmp                 ; base
        STX tmp2                ; count
        JSR random
@mod:   CMP tmp2                ; A mod count (count is small)
        BCC @have
        SEC
        SBC tmp2
        JMP @mod
@have:  CLC
        ADC tmp                 ; base + (rand mod count)
        TAX
        LDA msg_ptr_lo,X
        STA msg_lo
        LDA msg_ptr_hi,X
        STA msg_hi
        RTS

; narrate_step: a fresh IDLE line as the hero advances, and mark the HUD
; dirty so row 23 is rebuilt (a plain move otherwise leaves it untouched).
narrate_step:
        LDA #MSG_IDLE
        LDX #MSG_POOL
        JSR msg_rand
        LDA #HUD_BOTH
        STA hud_dirty
        RTS

; hush_narrator: blank row 23 (turning in place says nothing) and mark the
; HUD dirty so the DIR change + the now-empty message are redrawn. The
; narrator speaks again on the next actual step (narrate_step).
hush_narrator:
        LDA #<str_empty
        STA msg_lo
        LDA #>str_empty
        STA msg_hi
        LDA #HUD_BOTH
        STA hud_dirty
        RTS

; draw_str_centered: print the NUL-terminated string at (A=lo, X=hi) centered
; on char row Y. Clobbers A/X/Y, str_lo/hi, tmp. Used for the top-centre
; direction word and the row-23 message.
draw_str_centered:
        STA str_lo
        STX str_hi
        STY tmp                 ; target row
        LDY #0
@len:   LDA (str_lo),Y
        BEQ @lend
        INY
        BNE @len
@lend:  TYA                     ; A = length
        LSR                     ; length/2
        STA tmp2
        LDA #16                 ; 32/2 = centre column
        SEC
        SBC tmp2
        STA ch_cx
        LDA tmp
        STA ch_cy
        LDA str_lo
        LDX str_hi
        JMP print_str_ax

; draw_direction: the compass heading spelled out (NORTH/EAST/SOUTH/WEST),
; centred on row 1 at the top, tinted cyan. Redrawn every 3D frame (it
; lives in the cleared viewport).
draw_direction:
        LDA #2
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA #<str_floor
        LDX #>str_floor
        JSR print_str_ax
        LDA #8
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA p_floor
        JSR write_decimal_2d
        LDA #23
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA #'R'
        STA ch_code
        JSR write_char
        LDA #24
        STA ch_cx
        LDA p_relic
        CLC
        ADC #'0'
        STA ch_code
        JSR write_char
        LDA #27
        STA ch_cx
        LDA #'P'
        STA ch_code
        JSR write_char
        LDA #28
        STA ch_cx
        LDA p_potions
        CLC
        ADC #'0'
        STA ch_code
        JSR write_char
        LDX p_face
        LDA dir_word_lo,X
        PHA
        LDA dir_word_hi,X
        TAX                     ; X = hi
        PLA                     ; A = lo
        LDY #1                  ; row 1
        JSR draw_str_centered
        LDA #48                 ; tint the centre band cyan (avoids the
        STA cr_x                ; ceiling diagonals at the row's edges)
        LDA #8                  ; row 1 -> y=8
        STA cr_y
        LDA #160
        STA cr_w
        LDA #8
        STA cr_h
        LDA #$71                ; cyan
        STA cr_col
        JMP color_rect

; =============================================
; show_title: title screen on bitmap
; =============================================
show_title:
        JSR vdp_display_off
        ; Read the original A2FC HGR artwork into the hidden page. The
        ; picture occupies disk sectors, not scarce permanent 48K RAM.
        JSR dos_cmd_new
        LDA #<str_title_load
        LDY #>str_title_load
        JSR dos_cmd_add
        JSR dos_cmd_run
        LDA #0
        STA in_src
        STA in_dst
        LDA #$11
        STA in_src+1
        LDX draw_page
        LDA #$20
        CPX #0
        BEQ @destination
        LDA #$40
@destination:
        STA in_dst+1
        JSR unpack_title
        JSR dos_cmd_new
        LDA #<str_state_load
        LDY #>str_state_load
        JSR dos_cmd_add
        JSR dos_cmd_run
        JSR profiles_init
        JSR profile_load
        ; A compact footer leaves the illustration and title unobstructed.
        LDA #168
        LDX #192
        JSR clear_span
        JSR title_footer
        JSR vdp_display_on
@title_wait:
        JSR wait_key_real
        CMP #$B1
        BCC @action
        CMP #$B4
        BCS @action
        AND #$7F
        SEC
        SBC #'0'
        STA active_profile
        LDA #1
        STA preferences_dirty
        JSR preferences_save
        JSR profile_load
        JSR title_footer
        JMP @title_wait
@action:
        CMP #$C3
        BNE @start
        LDX save_available
        BEQ @title_wait
        RTS
@start:
        CMP #$D3
        BNE @exit
        JSR enter_seed
        LDA quit_flag
        BNE @ok
        BCC show_title_again
        LDA #$D3
        RTS
@exit:  CMP #KEY_ESC
        BNE @ok
        INC quit_flag
@ok:    RTS
title_footer:
        LDA #2
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA #<str_profile
        LDX #>str_profile
        JSR print_str_ax
        LDA #10
        STA ch_cx
        LDA active_profile
        CLC
        ADC #'0'
        STA ch_code
        JSR write_char
        LDA #13
        STA ch_cx
        LDA #<str_best
        LDX #>str_best
        JSR print_str_ax
        LDA #18
        STA ch_cx
        LDA SCORE_BASE+4
        JSR write_decimal_3d
        LDA #24
        STA ch_cx
        LDA save_available
        BEQ @empty
        LDA #<str_saved
        LDX #>str_saved
        JMP @status
@empty: LDA #<str_empty_save
        LDX #>str_empty_save
@status:
        JSR print_str_ax
        LDA #<str_profile_keys
        LDX #>str_profile_keys
        LDY #22
        JSR draw_str_centered
        LDA #<str_title_keys
        LDX #>str_title_keys
        LDY #23
        JMP draw_str_centered

show_title_again:
        JMP show_title

; Four hex digits, confirmed by RETURN. No entropy mixing while editing:
; spelling, corrections and time spent typing cannot change the dungeon.
; Carry set = accepted, clear = configuration requested quit.
enter_seed:
        LDA #0
        STA seed_count
@draw:
        JSR vdp_display_off
        JSR clear_bitmap
        LDA #<str_seed_title
        LDX #>str_seed_title
        LDY #5
        JSR draw_str_centered
        LDA #<str_seed_range
        LDX #>str_seed_range
        LDY #8
        JSR draw_str_centered
        LDA #14
        STA ch_cx
        LDA #11
        STA ch_cy
        LDA #0
        STA seed_value_lo       ; temporary drawing index (write_char clobbers X)
@digit:
        LDX seed_value_lo
        LDA #'_'
        CPX seed_count
        BCS @put
        LDA seed_digits,X
@put:   STA ch_code
        JSR write_char
        INC ch_cx
        INC seed_value_lo
        LDA seed_value_lo
        CMP #4
        BCC @digit
        LDA #<str_seed_keys
        LDX #>str_seed_keys
        LDY #15
        JSR draw_str_centered
        LDA #<str_seed_cancel
        LDX #>str_seed_cancel
        LDY #18
        JSR draw_str_centered
        JSR vdp_display_on
@wait:  LDA KBD
        BPL @wait
        BIT KBDSTRB
        CMP #KEY_ESC
        BNE @editing
        JSR configuration_menu
        LDA quit_flag
        BNE @cancel
        JMP @draw
@editing:
        CMP #$88                ; backspace / Apple II left arrow
        BEQ @erase
        CMP #$FF                ; DELETE on a //e or host keyboard
        BEQ @erase
        CMP #KEY_RET
        BEQ @confirm
        AND #$7F
        CMP #'a'
        BCC @hex
        CMP #'g'
        BCS @wait
        AND #$DF
@hex:   CMP #'0'
        BCC @wait
        CMP #('9'+1)
        BCC @store
        CMP #'A'
        BCC @wait
        CMP #('F'+1)
        BCS @wait
@store: LDX seed_count
        CPX #4
        BCS @wait
        STA seed_digits,X
        INC seed_count
        JMP @draw
@erase: LDA seed_count
        BEQ @wait
        DEC seed_count
        JMP @draw
@cancel:
        CLC
        RTS
@confirm:
        LDA seed_count
        CMP #4
        BNE @wait
        LDA #0
        STA seed_value_lo
        STA seed_value_hi
        LDX #0
@parse: LDA seed_digits,X
        SEC
        SBC #'0'
        CMP #10
        BCC @nibble
        SBC #7                  ; carry set: A-F -> 10-15
@nibble:
        LDY #4
@shift: ASL seed_value_lo
        ROL seed_value_hi
        DEY
        BNE @shift
        ORA seed_value_lo
        STA seed_value_lo
        INX
        CPX #4
        BCC @parse
        LDA seed_value_lo
        ORA seed_value_hi
        BNE @accept
        JMP @wait               ; zero locks the PRNG; remain in the editor
@accept:
        LDA seed_value_lo
        STA prng_lo
        LDA seed_value_hi
        STA prng_hi
        SEC
        RTS

; =============================================
; show_help: instructions screen
; =============================================
show_help:
        JSR vdp_display_off     ; hide the redraw
        JSR fill_color_white   ; wipe colours from the game/previous screen
        JSR clear_bitmap

        LDA #8
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA #<str_help_h1
        LDX #>str_help_h1
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        JSR print_str_ax

        LDA #1
        STA ch_cx
        LDA #4
        STA ch_cy
        LDA #<str_help_l1
        LDX #>str_help_l1
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #5
        STA ch_cy
        LDA #<str_help_l2
        LDX #>str_help_l2
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #6
        STA ch_cy
        LDA #<str_help_l3
        LDX #>str_help_l3
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #7
        STA ch_cy
        LDA #<str_help_l4
        LDX #>str_help_l4
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #8
        STA ch_cy
        LDA #<str_help_l5
        LDX #>str_help_l5
        JSR print_str_ax

        LDA #1
        STA ch_cx
        LDA #11
        STA ch_cy
        LDA #<str_help_l6
        LDX #>str_help_l6
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #12
        STA ch_cy
        LDA #<str_help_l7
        LDX #>str_help_l7
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #13
        STA ch_cy
        LDA #<str_help_l8
        LDX #>str_help_l8
        JSR print_str_ax

        LDA #1
        STA ch_cx
        LDA #16
        STA ch_cy
        LDA #<str_help_l9
        LDX #>str_help_l9
        JSR print_str_ax
        LDA #1
        STA ch_cx
        LDA #17
        STA ch_cy
        LDA #<str_help_l10
        LDX #>str_help_l10
        JSR print_str_ax

        LDA #4
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA #<str_press_any
        LDX #>str_press_any
        JSR print_str_ax

        JSR vdp_display_on      ; reveal the finished screen
        JSR wait_key_real
        CMP #KEY_ESC
        BNE @ok
        INC quit_flag
@ok:    RTS

; =============================================
; show_win
; =============================================
show_win:
        JSR finish_game
        JSR vdp_display_off     ; hide the redraw
        JSR fill_color_white   ; wipe colours from the game/previous screen
        JSR clear_bitmap
        LDA #6
        STA ch_cx
        LDA #6
        STA ch_cy
        LDA #<str_win1
        LDX #>str_win1
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #9
        STA ch_cy
        LDA #<str_win2
        LDX #>str_win2
        JSR print_str_ax
        LDA #6
        STA ch_cx
        LDA #12
        STA ch_cy
        LDA #<str_win3
        LDX #>str_win3
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #15
        STA ch_cy
        LDA #<str_score
        LDX #>str_score
        JSR print_str_ax
        LDA #11
        STA ch_cx
        LDA #15
        STA ch_cy
        LDA score_run
        JSR write_decimal_3d
        LDA #4
        STA ch_cx
        LDA #17
        STA ch_cy
        LDA #<str_best
        LDX #>str_best
        JSR print_str_ax
        LDA #11
        STA ch_cx
        LDA #17
        STA ch_cy
        LDA SCORE_BASE+4
        JSR write_decimal_3d
        LDA #4
        STA ch_cx
        LDA #19
        STA ch_cy
        LDA #<str_seed
        LDX #>str_seed
        JSR print_str_ax
        LDA #11
        STA ch_cx
        LDA #19
        STA ch_cy
        LDA p_seed_hi
        JSR write_hex_byte
        LDA p_seed_lo
        JSR write_hex_byte
        LDA #4
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA #<str_press_any
        LDX #>str_press_any
        JSR print_str_ax
        JSR vdp_display_on      ; reveal the finished screen
        JSR wait_key_real
        CMP #KEY_ESC
        BNE @ok
        INC quit_flag
@ok:    RTS

; =============================================
; show_lose
; =============================================
show_lose:
        JSR finish_game
        JSR vdp_display_off     ; hide the redraw
        JSR fill_color_white   ; wipe colours from the game/previous screen
        JSR clear_bitmap
        LDA #6
        STA ch_cx
        LDA #8
        STA ch_cy
        LDA #<str_lose1
        LDX #>str_lose1
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        JSR print_str_ax
        LDA #6
        STA ch_cx
        LDA #11
        STA ch_cy
        LDA #<str_lose2
        LDX #>str_lose2
        JSR print_str_ax
        LDA #4
        STA ch_cx
        LDA #20
        STA ch_cy
        LDA #<str_press_any
        LDX #>str_press_any
        JSR print_str_ax
        JSR vdp_display_on      ; reveal the finished screen
        JSR wait_key_real
        CMP #KEY_ESC
        BNE @ok
        INC quit_flag
@ok:    RTS

; =============================================
; render_3d - main scene
; =============================================
render_3d:
        ; Sync to VBlank before the full 3D-scene rebuild burst.
        WAIT_VBLANK_SAFE
        ; Draw the whole frame on the hidden page; vdp_display_on flips
        ; it in, so the player never sees a frame being drawn.
        JSR vdp_display_off
        JSR clear_viewport      ; only rows 0..19; HUD zone persists (per page)

        ; (No full-width horizon lines here: they crossed every wall and
        ; passage without occlusion and turned the scene to mush — the
        ; nested frame geometry alone carries the perspective, Wizardry
        ; style. Fixed juillet 2026 together with the front-wall frame
        ; off-by-one below.)

        ; precompute facing -> dx,dy (rd_dx, rd_dy)
        JSR setup_face_deltas

        ; iterate depth from 0..MAX_DEPTH-1
        LDA #0
        STA rd_depth
        STA rd_blocked
        LDA p_col
        STA rd_col
        LDA p_row
        STA rd_row

@dloop:
        LDA rd_blocked
        BNE @after_depth
        ; check OOB
        JSR check_oob
        BNE @oob_block
        ; draw side walls at this depth
        JSR draw_left_wall
        JSR draw_right_wall
        ; check front
        JSR check_front_wall
        BEQ @no_front
        ; front blocked: the wall sits on the FAR edge of cell d, so the
        ; closing rectangle lives at frame d+1 — drawing it at frame d
        ; (the old off-by-one) painted a rectangle one whole cell too
        ; near (full-screen when d=0!) across the side walls just drawn.
        ; rd_depth <= MAX_DEPTH-1 here, so d+1 stays inside the 11-entry
        ; frame tables. rd_blocked stops all further drawing, so the
        ; stale rd_depth value after this is never used for geometry.
        INC rd_depth
        JSR draw_front_wall
        LDA #1
        STA rd_blocked
        JMP @after_depth
@oob_block:
        JSR draw_front_wall
        LDA #1
        STA rd_blocked
        JMP @after_depth
@no_front:
        ; advance to next cell
        JSR step_forward
@after_depth:
        INC rd_depth
        LDA rd_depth
        CMP configured_depth
        BCC @dloop

        ; corridor still open at max view depth: close the perspective
        ; with the vanishing rectangle (frame entry MAX_DEPTH) so a long
        ; corridor reads as depth instead of trailing off into nothing
        LDA rd_blocked
        BNE @closed
        LDA configured_depth
        STA rd_depth
        JSR draw_front_wall
@closed:
        ; compass heading spelled out, top-centre
        JSR draw_direction
        ; HUD: HP, ATK, DEF, LVL, XP, GOLD + event message
        JSR draw_hud_3d
        ; monsters visible in the corridor ahead (up to 3, on the floor)
        JSR draw_mob_indicator

        JSR vdp_display_on      ; reveal the finished frame in one go
        RTS

; =============================================
; setup_face_deltas: based on p_face, set rd_dx, rd_dy
; =============================================
setup_face_deltas:
        LDA p_face
        STA rd_face
        CMP #DIR_N
        BNE @ne
        LDA #0
        STA rd_dx
        LDA #$FF
        STA rd_dy
        RTS
@ne:    CMP #DIR_E
        BNE @ns
        LDA #1
        STA rd_dx
        LDA #0
        STA rd_dy
        RTS
@ns:    CMP #DIR_S
        BNE @nw
        LDA #0
        STA rd_dx
        LDA #1
        STA rd_dy
        RTS
@nw:    LDA #$FF
        STA rd_dx
        LDA #0
        STA rd_dy
        RTS

; =============================================
; check_oob: A!=0 if (rd_col, rd_row) is out of maze
; =============================================
check_oob:
        LDA rd_col
        BMI @oob
        CMP #NCOLS
        BCS @oob
        LDA rd_row
        BMI @oob
        CMP #NROWS
        BCS @oob
        LDA #0
        RTS
@oob:   LDA #1
        RTS

; =============================================
; step_forward: rd_col += rd_dx, rd_row += rd_dy
; =============================================
step_forward:
        CLC
        LDA rd_col
        ADC rd_dx
        STA rd_col
        CLC
        LDA rd_row
        ADC rd_dy
        STA rd_row
        RTS

; =============================================
; check_front_wall: returns A!=0 if wall blocks forward
; based on rd_col, rd_row, p_face. Uses cell flags.
; OOB outside is treated as wall (caller handles).
; Wall check rules:
;   facing N: wall = !(cell.NORTH passage open)  with cell at rd_row, rd_col
;             -> need to check: from current cell heading N, the wall is THIS cell's NORTH
;   facing E: wall = !(cell.EAST)
;   facing S: wall = !(south neighbor.NORTH) but easier: cell.SOUTH = south_neighbor.NORTH
;   facing W: wall = !(west neighbor.EAST)
; =============================================
check_front_wall:
        ; load current cell at (rd_col, rd_row)
        LDX rd_col
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        STA rd_cell
        LDA p_face
        CMP #DIR_N
        BNE @ne
        LDA rd_cell
        AND #NORTH_BIT
        BEQ @blk
        LDA #0
        RTS
@ne:    CMP #DIR_E
        BNE @ns
        LDA rd_cell
        AND #EAST_BIT
        BEQ @blk
        LDA #0
        RTS
@ns:    CMP #DIR_S
        BNE @nw
        ; south neighbor's NORTH passage
        LDA rd_row
        CMP #(NROWS-1)
        BCS @blk
        LDX rd_col
        LDY rd_row
        INY
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #NORTH_BIT
        BEQ @blk
        LDA #0
        RTS
@nw:    ; west neighbor's EAST passage
        LDA rd_col
        BEQ @blk
        LDX rd_col
        DEX
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #EAST_BIT
        BEQ @blk
        LDA #0
        RTS
@blk:   LDA #1
        RTS

; =============================================
; check_left_wall: A!=0 if wall on player's LEFT at (rd_col, rd_row)
; facing N: left=W; facing E: left=N; facing S: left=E; facing W: left=S
; =============================================
check_left_wall:
        LDX rd_col
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        STA rd_cell
        LDA p_face
        CMP #DIR_N
        BNE @ne
        ; left=W: west neighbor's EAST
        LDA rd_col
        BEQ @blk
        LDX rd_col
        DEX
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #EAST_BIT
        BEQ @blk
        LDA #0
        RTS
@ne:    CMP #DIR_E
        BNE @ns
        ; left=N: cell.NORTH
        LDA rd_cell
        AND #NORTH_BIT
        BEQ @blk
        LDA #0
        RTS
@ns:    CMP #DIR_S
        BNE @nw
        ; left=E: cell.EAST
        LDA rd_cell
        AND #EAST_BIT
        BEQ @blk
        LDA #0
        RTS
@nw:    ; left=S: south neighbor's NORTH
        LDA rd_row
        CMP #(NROWS-1)
        BCS @blk
        LDX rd_col
        LDY rd_row
        INY
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #NORTH_BIT
        BEQ @blk
        LDA #0
        RTS
@blk:   LDA #1
        RTS

; =============================================
; check_right_wall: mirror of left
; facing N: right=E; facing E: right=S; facing S: right=W; facing W: right=N
; =============================================
check_right_wall:
        LDX rd_col
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        STA rd_cell
        LDA p_face
        CMP #DIR_N
        BNE @ne
        LDA rd_cell
        AND #EAST_BIT
        BEQ @blk
        LDA #0
        RTS
@ne:    CMP #DIR_E
        BNE @ns
        ; right=S
        LDA rd_row
        CMP #(NROWS-1)
        BCS @blk
        LDX rd_col
        LDY rd_row
        INY
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #NORTH_BIT
        BEQ @blk
        LDA #0
        RTS
@ns:    CMP #DIR_S
        BNE @nw
        ; right=W
        LDA rd_col
        BEQ @blk
        LDX rd_col
        DEX
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #EAST_BIT
        BEQ @blk
        LDA #0
        RTS
@nw:    LDA rd_cell
        AND #NORTH_BIT
        BEQ @blk
        LDA #0
        RTS
@blk:   LDA #1
        RTS

; =============================================
; draw_left_wall: if wall on left at depth d, draw outline of the
; trapezoid d..d+1 (no inner fill - keep it Wizardry-clean).
; If OPEN, draw the side passage instead (juillet 2026 coherence fix):
; the far plane of the crossing corridor — ceiling and floor edges at
; depth d+1 height spanning the gap, plus the near vertical corner.
; The old code drew NOTHING for an open side, so openings were
; indistinguishable from unrendered space.
; =============================================
draw_left_wall:
        JSR check_left_wall
        BNE @wall
        ; open: side-passage far plane
        LDX rd_depth
        LDA frame_lx,X
        STA fl_x0
        LDA frame_lx+1,X
        STA fl_x1
        LDA frame_ty+1,X
        STA fl_y0
        JSR hline
        LDX rd_depth
        LDA frame_lx,X
        STA fl_x0
        LDA frame_lx+1,X
        STA fl_x1
        LDA frame_by+1,X
        STA fl_y0
        JSR hline
        LDX rd_depth
        LDA frame_lx,X
        STA fl_x0
        LDA frame_ty+1,X
        STA fl_y0
        LDA frame_by+1,X
        STA fl_y1
        JSR vline
        ; far vertical corner of the opening (at lx[d+1]) — without it the
        ; passage box stayed open-ended whenever the NEXT depth had no wall
        ; to supply that edge (its near vertical coincides when it does;
        ; the double draw is a harmless OR).
        LDX rd_depth
        LDA frame_lx+1,X
        STA fl_x0
        LDA frame_ty+1,X
        STA fl_y0
        LDA frame_by+1,X
        STA fl_y1
        JSR vline
        RTS
@wall:
        LDX rd_depth
        LDA frame_lx,X
        STA ln_x0
        LDA frame_ty,X
        STA ln_y0
        INX
        LDA frame_lx,X
        STA ln_x1
        LDA frame_ty,X
        STA ln_y1
        JSR line_xy

        LDX rd_depth
        LDA frame_lx,X
        STA ln_x0
        LDA frame_by,X
        STA ln_y0
        INX
        LDA frame_lx,X
        STA ln_x1
        LDA frame_by,X
        STA ln_y1
        JSR line_xy

        LDX rd_depth
        LDA frame_lx,X
        STA fl_x0
        LDA frame_ty,X
        STA fl_y0
        LDA frame_by,X
        STA fl_y1
        JSR vline
        LDX rd_depth
        INX
        LDA frame_lx,X
        STA fl_x0
        LDA frame_ty,X
        STA fl_y0
        LDA frame_by,X
        STA fl_y1
        JSR vline
@open:  RTS

; =============================================
; draw_right_wall (mirror of draw_left_wall, incl. the open-side
; passage geometry — see the coherence note there)
; =============================================
draw_right_wall:
        JSR check_right_wall
        BNE @wall
        ; open: side-passage far plane
        LDX rd_depth
        LDA frame_rx+1,X
        STA fl_x0
        LDA frame_rx,X
        STA fl_x1
        LDA frame_ty+1,X
        STA fl_y0
        JSR hline
        LDX rd_depth
        LDA frame_rx+1,X
        STA fl_x0
        LDA frame_rx,X
        STA fl_x1
        LDA frame_by+1,X
        STA fl_y0
        JSR hline
        LDX rd_depth
        LDA frame_rx,X
        STA fl_x0
        LDA frame_ty+1,X
        STA fl_y0
        LDA frame_by+1,X
        STA fl_y1
        JSR vline
        ; far vertical corner of the opening (at rx[d+1]) — mirror of the
        ; left-side fix; see the note there.
        LDX rd_depth
        LDA frame_rx+1,X
        STA fl_x0
        LDA frame_ty+1,X
        STA fl_y0
        LDA frame_by+1,X
        STA fl_y1
        JSR vline
        RTS
@wall:
        LDX rd_depth
        LDA frame_rx,X
        STA ln_x0
        LDA frame_ty,X
        STA ln_y0
        INX
        LDA frame_rx,X
        STA ln_x1
        LDA frame_ty,X
        STA ln_y1
        JSR line_xy

        LDX rd_depth
        LDA frame_rx,X
        STA ln_x0
        LDA frame_by,X
        STA ln_y0
        INX
        LDA frame_rx,X
        STA ln_x1
        LDA frame_by,X
        STA ln_y1
        JSR line_xy

        LDX rd_depth
        LDA frame_rx,X
        STA fl_x0
        LDA frame_ty,X
        STA fl_y0
        LDA frame_by,X
        STA fl_y1
        JSR vline
        LDX rd_depth
        INX
        LDA frame_rx,X
        STA fl_x0
        LDA frame_ty,X
        STA fl_y0
        LDA frame_by,X
        STA fl_y1
        JSR vline
@open:  RTS

; =============================================
; draw_front_wall: closing rectangle at depth d using frame_*
; with two simple horizontal seams to suggest stone courses.
; =============================================
draw_front_wall:
        ; hline/vline CLOBBER X (their 8-px batching loops: TAX/INX) — every
        ; frame_*,X load below reloads X from rd_depth after a JSR. The old
        ; code reused X across the calls: the bottom hline picked a random
        ; frame_by and the right edge landed at frame_rx[vl_cnt] (a phantom
        ; vertical at x=183 in every blocked scene — the juillet 2026 render
        ; mess, together with the frame off-by-one fixed in render_3d).
        LDX rd_depth
        LDA frame_lx,X
        STA fl_x0
        LDA frame_rx,X
        STA fl_x1
        LDA frame_ty,X
        STA fl_y0
        JSR hline
        LDX rd_depth
        LDA frame_by,X
        STA fl_y0
        JSR hline
        LDX rd_depth
        LDA frame_lx,X
        STA fl_x0
        LDA frame_ty,X
        STA fl_y0
        LDA frame_by,X
        STA fl_y1
        JSR vline
        LDX rd_depth
        LDA frame_rx,X
        STA fl_x0
        JSR vline
        ; (No mortar seam: the mid-height line across the closing wall read
        ; as clutter, not texture — removed juillet 2026 on request.)
        RTS

; =============================================
; draw_hud_3d - small status under the floor area
; =============================================
draw_hud_3d:
        ; Status panel in the 4-line text zone (rows 20-23, y 160..191):
        ;   y=159      full-width floor line closing the 3D viewport
        ;   row 20     (blank -- 8px of air so the text is not glued
        ;              to the floor line; juillet 2026 request)
        ;   row 21     HP nn    ATK n    DEF n     (combat stats)
        ;   row 22     LVL n    XP nn    DIR X     (progression + facing)
        ;   row 23     free for game messages.
        ; Three aligned columns at cx 1 / 11 / 21, values 2 cells after
        ; their label (write_decimal_2d blanks a leading zero tens digit).
        ; Floor line (y159) closes the viewport -- it lives in the cleared
        ; region (rows 0..19), so it is redrawn EVERY frame.
        LDA #0
        STA fl_x0
        LDA #255
        STA fl_x1
        LDA #159
        STA fl_y0
        JSR hline

        ; The text panel (rows 20..23) is NOT cleared by clear_viewport, so
        ; it persists across plain moves. Rebuild it only when dirty (a
        ; stat/facing change, or a fresh entry into the 3D view).
        LDA hud_dirty
        BNE @rebuild
        RTS
@rebuild:
        ; Double buffering: each HGR page keeps its own copy of the panel,
        ; so a change is rebuilt twice -- once on each page (HUD_BOTH).
        DEC hud_dirty
        JSR clear_hud           ; wipe rows 20..23 -> no field-gap remnants

        ; --- row 21: HP / ATK / DEF ---
        LDA #1
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA #<str_hud_hp
        LDX #>str_hud_hp
        JSR print_str_ax
        LDA #5
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA p_hp
        JSR write_decimal_2d

        LDA #11
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA #<str_hud_atk
        LDX #>str_hud_atk
        JSR print_str_ax
        LDA #15
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA p_atk
        JSR write_decimal_2d

        LDA #21
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA #<str_hud_def
        LDX #>str_hud_def
        JSR print_str_ax
        LDA #25
        STA ch_cx
        LDA #21
        STA ch_cy
        LDA p_def
        JSR write_decimal_2d

        ; --- row 21: LVL / XP / DIR ---
        LDA #1
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA #<str_hud_lvl
        LDX #>str_hud_lvl
        JSR print_str_ax
        LDA #5
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA p_lvl
        JSR write_decimal_2d

        LDA #11
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA #<str_hud_xp
        LDX #>str_hud_xp
        JSR print_str_ax
        LDA #15
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA p_xp
        JSR write_decimal_2d

        ; GOLD (facing now lives spelled-out at the top, so the HUD slot
        ; that held DIR shows the loot total instead).
        LDA #21
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA #<str_hud_gold
        LDX #>str_hud_gold
        JSR print_str_ax
        LDA #26
        STA ch_cx
        LDA #22
        STA ch_cy
        LDA p_gold
        JSR write_decimal_2d

        ; Event message, centred on row 23 (yellow).
        LDA msg_lo
        LDX msg_hi
        LDY #23
        JSR draw_str_centered

        ; Colour the HUD rows: vitals (21) green, progression (22) cyan,
        ; message (23) yellow.
        LDA #8
        STA cr_x
        LDA #168                ; row 21 (HP / ATK / DEF)
        STA cr_y
        LDA #216
        STA cr_w
        LDA #8
        STA cr_h
        LDA #$31                ; light green
        STA cr_col
        JSR color_rect
        LDA #8
        STA cr_x
        LDA #176                ; row 22 (LVL / XP / GOLD)
        STA cr_y
        LDA #216
        STA cr_w
        LDA #8
        STA cr_h
        LDA #$71                ; cyan
        STA cr_col
        JSR color_rect
        LDA #0
        STA cr_x
        LDA #184                ; row 23 (message)
        STA cr_y
        LDA #248
        STA cr_w
        LDA #8
        STA cr_h
        LDA #$B1                ; yellow
        STA cr_col
        JSR color_rect
        RTS

face_chars:
        .byte 'N', 'E', 'S', 'W'

; =============================================
 ; draw_mob_indicator: scan up to configured_depth cells ahead, stop at a
; wall, remember the visible monsters and paint occupied cells far to near.
; Up to three monsters share a cell. Near groups retain separate sprites;
; at sub-byte distances the cell resolves to one small white silhouette.
; =============================================
draw_mob_indicator:
        ; Collect every occupied visible cell, then paint FAR TO NEAR so
        ; nearer opaque silhouettes hide monsters farther down the hall.
        LDA #0
        STA mob_depth
        LDX #NUM_MOBS-1
@reset: STA visible_depth,X
        DEX
        BPL @reset
        LDA p_col
        STA rd_col
        LDA p_row
        STA rd_row
        LDA #1
        STA mob_scan_d
@scan:  JSR check_front_wall
        BNE @paint
        JSR step_forward
        JSR count_mobs_rd
        BEQ @next
        LDX rd_col
        LDY rd_row
        JSR cell_index_xy
        TAX
        LDA grid,X
        ORA #SEEN_MOB
        STA grid,X
        LDY #0
@remember:
        LDX mob_slot0,Y
        LDA mob_scan_d
        STA visible_depth,X
        INY
        CPY mob_cnt
        BCC @remember
@next:  INC mob_scan_d
        LDA mob_scan_d
        CMP configured_depth
        BCC @scan
        BEQ @scan
@paint: LDA configured_depth
        STA mob_scan_d
@cell:  LDA #0
        STA mob_cnt
        LDX #0
@mob:   LDA visible_depth,X
        CMP mob_scan_d
        BNE @skip
        LDY mob_cnt
        TXA
        STA mob_slot0,Y
        INC mob_cnt
@skip:  INX
        CPX #NUM_MOBS
        BCC @mob
        LDA mob_cnt
        BEQ @closer
        LDA mob_scan_d
        STA mob_depth
        JSR draw_mob_cluster
@closer:
        DEC mob_scan_d
        BNE @cell
        JMP sprite_color_white

; count_mobs_rd: scan every mob; record up to 3 living ones standing on
; (rd_col, rd_row) into mob_slot0/1/2. Returns A = count (0..3).
count_mobs_rd:
        LDA #0
        STA mob_cnt
        LDX #0
@lp:    LDA mob_type,X
        CMP #MOB_DEAD
        BEQ @nx
        LDA mob_col,X
        CMP rd_col
        BNE @nx
        LDA mob_row,X
        CMP rd_row
        BNE @nx
        LDY mob_cnt
        CPY #3
        BCS @nx                 ; already have 3 -- ignore extras
        TXA
        STA mob_slot0,Y         ; slot0/1/2 contiguous
        INC mob_cnt
@nx:    INX
        CPX #NUM_MOBS
        BNE @lp
        LDA mob_cnt
        RTS

 ; draw_mob_cluster: native HGR byte spacing, centred row with a shared
; feet line. Packed sizes: 0=8, 1=16, 2=32, 3=64, 4=4, 5=2, 6=1 pixels.
; =============================================
draw_mob_cluster:
        LDA mob_depth
        CMP #6
        BCC @near
        LDA #1                 ; sub-byte distances resolve one cell silhouette
        STA mob_cnt
@near:  LDX mob_depth
        LDA mob_cnt
        CMP #2
        BCC @single
        LDA multi_sz-1,X
        JMP @size
@single:
        LDA base_sz-1,X
@size:  STA mob_sz              ; packed size index: 0=8, 1=16, 2=32, 3=64
        TAY
        LDA packed_height,Y
        STA tmp
        LDA feet_y-1,X
        SEC
        SBC tmp
        STA mob_spy
        ; Byte-column spacing is native HGR: a 32px sprite takes FIVE
        ; bytes, not four virtual 8px columns. This prevents truncation.
        LDA cluster_pitch-1,X
        STA mob_step
        LDA mob_sz
        CMP #3
        BNE @row
        LDA #10
        STA mob_step
@row:   LDX mob_cnt
        DEX
        LDA #0
@width: CPX #0
        BEQ @last
        CLC
        ADC mob_step
        DEX
        BNE @width
@last:  LDY mob_sz
        CLC
        ADC packed_width,Y
        LSR
        STA tmp
        LDA #20                ; centre of the 40-column HGR screen
        SEC
        SBC tmp
        STA mob_curx           ; native byte column, not virtual pixel x
        LDA #0
        STA mob_slot_i
@draw:  LDY mob_slot_i
        LDX mob_slot0,Y
        STX mob_cur
        JSR draw_packed_mob
        LDA mob_curx
        CLC
        ADC mob_step
        STA mob_curx
        INC mob_slot_i
        LDA mob_slot_i
        CMP mob_cnt
        BCC @draw
        RTS

; X = monster index, mob_sz = size index, mob_curx = native HGR byte,
; mob_spy = top scanline. Pack and tint once per SOURCE row, reuse it for
; vertical magnification. No per-pixel shifting in the runtime blitter.
draw_packed_mob:
        LDA mob_type,X
        STA tmp
        ASL
        ASL
        ASL
        SEC
        SBC tmp
        CLC
        ADC mob_sz
        TAY
        LDA packed_mob_lo,Y
        STA sp_ptr
        LDA packed_mob_hi,Y
        STA sp_ptr+1
        LDA mob_type,X
        TAY
        JSR set_sprite_color_y
        LDY mob_sz
        BEQ @white
        CPY #4
        BCC @color
@white:
        JSR sprite_color_white  ; tiny silhouettes retain all their pixels
        LDY mob_sz
@color: LDA packed_width,Y
        STA sp_wout
        LDA packed_source_rows,Y
        STA packed_rows
        LDA packed_vertical,Y
        STA packed_repeat
        LDA packed_last_mask,Y
        STA packed_tail
        LDA mob_spy
        STA sp_yy
        JMP hgr_sprite_packed

packed_width = packed_mob_width
packed_height = packed_mob_height
packed_source_rows = packed_mob_source_rows
packed_vertical = packed_mob_vertical
packed_last_mask = packed_mob_last_mask
cluster_pitch:     .byte 5,3,2,1,1,1,1,1,1,1

; color_current_mob: fill the colour table for the mob_sz*16-square block
; at (sp_x, sp_y) with mob_cur's archetype colour.
color_reset_last:
        RTS

color_rect:
        RTS

; fill_color_white: STUB on the GEN2 HGR port (no colour table).
fill_color_white:
        RTS

; Packed size indices and feet line, indexed by depth 1..10:
;   base_sz  = a LONE monster (imposing: adjacent = x4).
;   multi_sz = 2-3 monsters, all this size so they share size + height.
;   feet_y   = the floor line the monsters stand on (same for the whole row).
base_sz:  .byte 3,2,1,1,0,4,5,5,6,6
multi_sz: .byte 2,1,0,0,0,4,5,5,6,6
feet_y:   .byte 128,112,96,88,84,82,81,81,80,80

; ---- HGR artifact colour per archetype (goblin / orc / dark mage) ----
; The TMS tints ($31 lt-green / $91 lt-red / $D1 magenta) map onto the
; HSPR_* artifact-colour codes (hgr_sprite_color.inc).
mob_colors:     .byte $31,$91,$D1,$91
mob_hues:       .byte HSPR_GREEN, HSPR_ORANGE, HSPR_VIOLET, HSPR_ORANGE

; set_sprite_color_y: arm the blit colour attributes for archetype Y.
set_sprite_color_y:
        LDA mob_hues,Y
        JMP hgr_spr16_color_a

; sprite_color_white: full-density monochrome blit (both parities lit).
sprite_color_white:
        LDA #HSPR_WHITE
        JMP hgr_spr16_color_a

; =============================================
; write_decimal_2d: A=value, prints two decimal digits at
; (ch_cx, ch_cy); advances ch_cx by 2.
; BUG HISTORY (juillet 2026): the ones digit used to be kept in tmp
; across the tens digit's JSR write_char — but write_char clobbers
; tmp/tmp2 for its font-pointer math, so the ones digit came out as
; garbage (HP 20 printed as "2" + junk glyph; ATK 4 as " 0"; LVL 1 as
; " 0" — the broken-HUD bug). The ones digit now rides the stack.
; =============================================
write_decimal_2d:
        STA tmp
        ; tens
        LDX #0
@dv:    LDA tmp
        CMP #10
        BCC @dvd
        SEC
        SBC #10
        STA tmp
        INX
        JMP @dv
@dvd:   LDA tmp
        PHA                     ; ones digit — write_char-proof
        ; print tens (or space if 0)
        TXA
        BNE @nz
        LDA #' '
        JMP @stz
@nz:    CLC
        ADC #'0'
@stz:   STA ch_code
        JSR write_char
        INC ch_cx
        ; ones
        PLA
        CLC
        ADC #'0'
        STA ch_code
        JSR write_char
        INC ch_cx
        RTS

; A=0..255, three digits for scores.
write_decimal_3d:
        LDX #0
@hundreds:
        CMP #100
        BCC @remainder
        SEC
        SBC #100
        INX
        JMP @hundreds
@remainder:
        PHA
        TXA
        CLC
        ADC #'0'
        STA ch_code
        JSR write_char
        INC ch_cx
        PLA
        CMP #10
        BCS @two_digits
        PHA
        LDA #'0'
        STA ch_code
        JSR write_char
        INC ch_cx
        PLA
        CLC
        ADC #'0'
        STA ch_code
        JSR write_char
        INC ch_cx
        RTS
@two_digits:
        JMP write_decimal_2d

; Print one byte as two hexadecimal characters at the current text cell.
write_hex_byte:
        PHA
        LSR
        LSR
        LSR
        LSR
        JSR write_hex_nibble
        PLA
        AND #$0F
write_hex_nibble:
        CMP #10
        BCC @digit
        SEC
        SBC #10
        CLC
        ADC #'A'
        JMP @print
@digit:
        CLC
        ADC #'0'
@print: STA ch_code
        JSR write_char
        INC ch_cx
        RTS

; =============================================
; render_map - top-down view of the maze with player position
; Cell size 16x16 px; maze 11x7 -> 176x112. Origin (36,20) — NOT (40,24):
; with a 36/20 origin the central 8x8 glyph block of cell (c,r) is exactly
; char cell (5+2c, 3+2r), so the S/E/M/arrow markers sit centered with 4 px
; of air on every side instead of starting ON the left wall line (the
; "letters glued to the walls" report, juillet 2026).
; =============================================
render_map:
        ; Sync to VBlank before the top-down map rebuild burst.
        WAIT_VBLANK_SAFE
        JSR vdp_display_off     ; hide the redraw
        JSR clear_bitmap
        LDA #4
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA #<str_map_title
        LDX #>str_map_title
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        JSR print_str_ax
        LDA #23
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA #<str_floor
        LDX #>str_floor
        JSR print_str_ax
        LDA #29
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA p_floor
        JSR write_decimal_2d

        ; outer bounds
        LDA #(36)
        STA fl_x0
        LDA #(36+11*16)         ; 212
        STA fl_x1
        LDA #(20)
        STA fl_y0
        JSR hline
        LDA #(20+7*16)          ; 132
        STA fl_y0
        JSR hline

        LDA #36
        STA fl_x0
        LDA #(20)
        STA fl_y0
        LDA #(20+7*16)
        STA fl_y1
        JSR vline
        LDA #(36+11*16)
        STA fl_x0
        JSR vline

        ; walls between cells — loop indices live in rd_col/rd_row (free
        ; during map rendering). BUG HISTORY (juillet 2026): they used to
        ; live in tmp/tmp2, but cell_index_xy, calc_pix_addr and the line
        ; primitives all clobber tmp — after the first drawn wall the
        ; column index turned to garbage and the map came out empty but
        ; for a couple of random ticks.
        LDA #0
        STA rd_row
@yloop: LDA #0
        STA rd_col
@xloop: LDX rd_col
        LDY rd_row
        JSR cell_index_xy       ; A = row*NCOLS + col (clobbers tmp)
        TAX
        LDA grid,X
        STA rd_cell
        AND #VISITED
        BEQ @no_bot
        ; --- right wall: if EAST passage NOT set and col<NCOLS-1 ---
        LDA rd_col
        CMP #(NCOLS-1)
        BCS @no_right
        LDA rd_cell
        AND #EAST_BIT
        BNE @no_right
        ; vertical line at x = 36+(col+1)*16, y 20+row*16 .. 20+(row+1)*16
        LDA rd_col
        CLC
        ADC #1
        ASL
        ASL
        ASL
        ASL                     ; (col+1)*16
        CLC
        ADC #36
        STA fl_x0
        LDA rd_row
        ASL
        ASL
        ASL
        ASL
        CLC
        ADC #20
        STA fl_y0
        CLC
        ADC #16
        STA fl_y1
        JSR vline
@no_right:
        ; --- bottom wall: if SOUTH passage missing (south neighbor's
        ;     NORTH bit clear) and row<NROWS-1 ---
        LDA rd_row
        CMP #(NROWS-1)
        BCS @no_bot
        LDX rd_col
        LDY rd_row
        INY
        JSR cell_index_xy       ; south neighbor index
        TAX
        LDA grid,X
        AND #NORTH_BIT
        BNE @no_bot
        ; horizontal line at y = 20+(row+1)*16, x 36+col*16 .. +16
        LDA rd_col
        ASL
        ASL
        ASL
        ASL
        CLC
        ADC #36
        STA fl_x0
        CLC
        ADC #16
        STA fl_x1
        LDA rd_row
        CLC
        ADC #1
        ASL
        ASL
        ASL
        ASL
        CLC
        ADC #20
        STA fl_y0
        JSR hline
@no_bot:
        LDA rd_cell
        AND #(VISITED|ROOM_BIT)
        CMP #(VISITED|ROOM_BIT)
        BNE @no_room
        LDA rd_col
        ASL
        CLC
        ADC #5
        STA ch_cx
        LDA rd_row
        ASL
        CLC
        ADC #3
        STA ch_cy
        LDA #'R'
        STA ch_code
        JSR write_char
@no_room:
        ; Pickups are visible on the map to give each run a route-planning
        ; objective. collect_cell clears the bit when one is collected.
        LDA rd_cell
        AND #RELIC_BIT
        BEQ @not_relic
        LDA #'*'
        BNE @draw_pickup
@not_relic:
        LDA rd_cell
        AND #CHEST_BIT
        BEQ @no_pickup
        LDA #'$'
@draw_pickup:
        STA ch_code
        LDA rd_col
        ASL
        CLC
        ADC #5
        STA ch_cx
        LDA rd_row
        ASL
        CLC
        ADC #3
        STA ch_cy
        JSR write_char
@no_pickup:
        INC rd_col
        LDA rd_col
        CMP #NCOLS
        BCS @yend
        JMP @xloop
@yend:  INC rd_row
        LDA rd_row
        CMP #NROWS
        BCS @ydone
        JMP @yloop
@ydone:

        ; markers: S at (0,0), E at (NCOLS-1, NROWS-1), live mobs as 'M'
        ; (all markers: char cell (5+2c, 3+2r) = the centered 8x8 block)
        LDA #5
        STA ch_cx
        LDA #3
        STA ch_cy
        LDA #'S'
        STA ch_code
        JSR write_char

        ; Only reveal the exit once its cell has been explored.
        LDA grid+NCELLS-1
        AND #VISITED
        BEQ @hide_exit
        ; E in bottom-right cell: (5+2*10, 3+2*6) = (25, 15)
        LDA #25
        STA ch_cx
        LDA #15
        STA ch_cy
        LDA #'E'
        STA ch_code
        JSR write_char
@hide_exit:

        ; live mobs
        LDX #0
@mlp:   STX ch_idx
        LDA mob_type,X
        CMP #MOB_DEAD
        BEQ @mn
        LDA mob_row,X
        TAY
        LDA mob_col,X
        TAX
        JSR cell_index_xy
        TAX
        LDA grid,X
        AND #SEEN_MOB
        BEQ @mn
        LDX ch_idx
        ; cell coord -> char cell
        LDA mob_col,X
        ASL
        STA tmp                 ; col*2 (each cell ~16 px = 2 char cells)
        CLC
        ADC #5                  ; offset into map (40 px = char col 5)
        STA ch_cx
        LDA mob_row,X
        ASL
        CLC
        ADC #3
        STA ch_cy
        LDA #'M'
        STA ch_code
        JSR write_char
@mn:    LDX ch_idx
        INX
        CPX #NUM_MOBS
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        BNE @mlp

        ; Player arrow
        LDA p_col
        ASL
        CLC
        ADC #5
        STA ch_cx
        LDA p_row
        ASL
        CLC
        ADC #3
        STA ch_cy
        LDA p_face
        TAX
        LDA arrow_chars,X
        STA ch_code
        JSR write_char

        LDA #3
        STA ch_cx
        LDA #18
        STA ch_cy
        LDA #<str_seed
        LDX #>str_seed
        JSR print_str_ax
        LDA #10
        STA ch_cx
        LDA #18
        STA ch_cy
        LDA p_seed_hi
        JSR write_hex_byte
        LDA p_seed_lo
        JSR write_hex_byte

        ; HUD line
        LDA #0
        STA ch_cx
        LDA #20
        STA ch_cy
        LDA #<str_map_help
        LDX #>str_map_help
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        JSR print_str_ax
        JSR vdp_display_on      ; reveal the finished map
        RTS

arrow_chars:
        .byte '^', '>', 'V', '<'

; =============================================
; run_combat - turn-based against cur_mob
; =============================================
run_combat:
        LDA combat_resuming
        BEQ @fresh
        LDA #0
        STA combat_resuming
        JMP @portrait
@fresh: LDA #0
        STA p_guard
        STA p_focus
        STA mob_phase
@portrait:
        JSR draw_combat_screen
@wait:  JSR wait_key
        CMP #KEY_ESC
        BNE @n1
        INC quit_flag
        RTS
@n1:    CMP #KEY_F
        BNE @n2
        ; flee: 50% chance
        JSR random
        AND #$01
        BNE @flee_ok
        ; failed flee = monster gets free hit
        JMP @mob_alive
@flee_ok:
        ; Retreat to the cell from which combat was entered. Staying on
        ; the monster cell let a successful flee bypass every foe.
        LDA old_col
        STA p_col
        LDA old_row
        STA p_row
        LDA #HUD_BOTH
        STA hud_dirty           ; combat wiped the HUD zone + may have changed
                                ; HP; rebuild it on the 3D return
        LDA prev_state
        STA gstate
        RTS
@n2:    CMP #KEY_G
        BNE @n3
        LDA #1
        STA p_guard
        LDA #2
        STA p_focus             ; the next attack gains two points
        JMP @mob_alive
@n3:    CMP #KEY_P
        BNE @n4
        JSR drink_potion
        BCC @wait
        JMP @mob_alive
@n4:    CMP #KEY_A
        BEQ @attack
        ; unknown key / wait_key's synthetic timeout: keep waiting
        ; WITHOUT returning — an RTS here made play_loop rebuild the
        ; whole combat screen every ~0.7 s (same flicker bug as
        ; play_input's old fall-through)
        JMP @wait
@attack:
        JSR sound_attack
        ; player attacks
        LDX cur_mob
        LDA p_atk
        STA tmp
        ; small random variance 0..1
        JSR random
        AND #$01
        CLC
        ADC tmp
        CLC
        ADC p_focus
        STA tmp                 ; effective atk
        LDA #0
        STA p_focus
        ; mob defense by type: 0,1,2,2 (the dragon relies on HP)
        LDX cur_mob
        LDA mob_type,X
        CMP #3
        BCC @def_ready
        LDA #2
@def_ready:
        STA tmp2                ; type defense
        LDA tmp
        SEC
        SBC tmp2
        BPL @okd
        LDA #1
@okd:   CMP #1
        BCS @apply
        LDA #1
@apply: STA ev_dmg
        ; subtract from mob_hp
        LDX cur_mob
        SEC
        LDA mob_hp,X
        SBC ev_dmg
        BCS @ok
        LDA #0
@ok:    STA mob_hp,X
        BEQ @killed
        JMP @mob_alive
@killed:
        ; mob killed
        LDA mob_type,X
        STA dead_type
        LDA #MOB_DEAD
        STA mob_type,X
        ; --- loot: gold += (type+1)*2 + 1d4 (tougher foes drop more) ---
        LDA dead_type
        CLC
        ADC #1
        ASL                     ; (type+1)*2
        STA tmp
        JSR random
        AND #$03
        CLC
        ADC tmp
        CLC
        ADC p_gold
        CMP #100
        BCC @gold_ok
        LDA #99
@gold_ok:
        STA p_gold              ; keep the two-digit HUD and shop readable
        ; --- XP is a running TOTAL now (it only ever climbs, so a kill
        ; always visibly rewards). Level up each time it crosses xp_next. ---
        LDA p_xp
        CLC
        ADC #4
        STA p_xp
        LDA #0
        STA tmp2                ; leveled-up flag
@lvlchk:
        LDA p_xp
        CMP xp_next
        BCC @lvldone
        INC p_lvl
        INC p_atk
        ; level-up HEAL: +8 HP (capped at 30). Turns combat into a real
        ; risk/reward loop -- fighting weaker foes to level up lets you
        ; recover HP and take on the dangerous ones, instead of the
        ; "avoid everything and rush the exit" degenerate strategy.
        LDA p_hp
        CLC
        ADC #8
        CMP #31
        BCC @hpok
        LDA #30
@hpok:  STA p_hp
        LDA p_lvl
        AND #$01
        BNE @nodef
        INC p_def
@nodef:
        LDA xp_next
        CLC
        ADC #10                 ; next threshold
        STA xp_next
        LDA #1
        STA tmp2
        JSR sound_level
        JMP @lvlchk
@lvldone:
        ; narrator: if the fight left you battered, an ominous PERIL line;
        ; otherwise a triumphant WIN line. (The LVL bump + heal already
        ; signal the level-up on the HUD.)
        LDA p_hp
        CMP #7
        BCS @winmsg
        LDA #MSG_PERIL
        LDX #MSG_POOL
        JSR msg_rand
        JMP @nolvl
@winmsg:
        LDA #MSG_WIN
        LDX #MSG_POOL
        JSR msg_rand
@nolvl:
        ; A cell can hold up to 3 monsters ("the original idea"): if
        ; another is still standing on the player's cell, fight it too —
        ; stay in ST_COMBAT (cur_mob := next foe) so play_loop re-enters
        ; run_combat and redraws. Only when the cell is clear do we drop
        ; back to the previous state.
        JSR find_mob_here
        BMI @cell_clear
        STA cur_mob
        RTS
@cell_clear:
        LDA #HUD_BOTH
        STA hud_dirty           ; combat changed stats + wiped the HUD zone
        LDA prev_state
        STA gstate
        RTS
@mob_alive:
        ; monster's turn
        JSR mob_attacks
        LDA ev_dmg
        BEQ @quiet
        JSR sound_hurt
@quiet:
        LDA p_hp
        BEQ @die2
        ; HGR port: the round only moved the two HP values — repaint
        ; those four digit cells and loop for the next key. The full
        ; draw_combat_screen stays for entry and next-foe transitions
        ; (different name/portrait), where it is genuinely needed.
        JSR combat_update_hp
        JSR draw_combat_intent
        JMP @wait
@die2:  LDA #ST_LOSE
        STA gstate
        JSR sound_death
        RTS

; =============================================
; mob_attacks: mob hits player
; damage = (type+2) + (floor-1) - p_def + 0..1
; =============================================
mob_attacks:
        LDA #0
        STA ev_dmg
        LDX cur_mob
        LDA mob_type,X
        CMP #1
        BEQ @charger
        CMP #3
        BEQ @charger
        CMP #2
        BEQ @mage
        ; A goblin sometimes steals one coin instead of dealing damage.
        JSR random
        AND #$03
        BNE @normal
        LDA p_gold
        BEQ @normal
        DEC p_gold
        LDA #HUD_BOTH
        STA hud_dirty
        RTS
@charger:
        LDA mob_phase
        BEQ @windup
        LDA #0
        STA mob_phase
        LDA mob_type,X
        CLC
        ADC #4                  ; heavy blow after the visible windup
        JMP @floor_bonus
@windup:
        LDA #1
        STA mob_phase
        RTS
@mage:
        LDA p_floor
        ; Magic ignores armor, so its base damage must stay below the
        ; physical heavy hitters' damage on later floors.
        JMP @variance
@normal:
        LDA mob_type,X
        CLC
        ADC #2
@floor_bonus:
        STA tmp
        LDA p_floor
        SEC
        SBC #1
        CLC
        ADC tmp
        STA tmp
        JSR random
        AND #$01
        CLC
        ADC tmp
        SEC
        SBC p_def
        BCS @positive
        LDA #1
@positive:
        CMP #1
        BCS @guard
        LDA #1
        JMP @guard
@variance:
        STA tmp
        JSR random
        AND #$01
        CLC
        ADC tmp
@guard: LDY p_guard
        BEQ @apply
        LSR
        BNE @apply
        LDA #1
@apply: STA ev_dmg
        LDA #0
        STA p_guard
        LDA p_hp
        SEC
        SBC ev_dmg
        BCS @okhp
        LDA #0
@okhp:  STA p_hp
        RTS

; =============================================
; draw_combat_screen
; =============================================
draw_combat_screen:
        ; Wipe any monster tint the 3D view left in the colour table (its
        ; depth-1 region is larger than the portrait box, so leftover
        ; colour could tinge the combat text). The portrait gets its own
        ; tint below.
        JSR color_reset_last
        ; Sync to VBlank before the combat-scene rebuild burst.
        WAIT_VBLANK_SAFE
        JSR vdp_display_off     ; hide the redraw
        JSR clear_bitmap
        ; Title bar
        LDA #10
        STA ch_cx
        LDA #1
        STA ch_cy
        LDA #<str_combat_title
        LDX #>str_combat_title
        JSR     tms9918_pad12   ; +12c silicon-strict pad12-v3 (back-to-back VDP store)
        JSR print_str_ax

        ; Monster name. BUG HISTORY (juillet 2026): an ASL doubled the
        ; type before indexing, but mob_names_lo/hi are PARALLEL byte
        ; tables indexed by type directly — orcs displayed the mage's
        ; name and mages read past the table ("R 3 ?" garbage).
        LDX cur_mob
        LDA mob_type,X
        TAX
        LDA mob_names_lo,X
        STA str_lo
        LDA mob_names_hi,X
        STA str_hi
        LDA #11
        STA ch_cx
        LDA #4
        STA ch_cy
        JSR write_str

        ; Monster HP — value at cx 7..8: cx 11 would put the ones digit in
        ; cell 12 (x 96..103), exactly under the x4 portrait's first column
        ; (drawn LATER with pure stores), which wiped the digit.
        LDA #4
        STA ch_cx
        LDA #6
        STA ch_cy
        LDA #<str_mob_hp
        LDX #>str_mob_hp
        JSR print_str_ax
        LDA #7
        STA ch_cx
        LDA #6
        STA ch_cy
        LDX cur_mob
        LDA mob_hp,X
        JSR write_decimal_2d

        ; Player HP / ATK
        LDA #5
        STA ch_cx
        LDA #16
        STA ch_cy
        LDA #<str_p_hp
        LDX #>str_p_hp
        JSR print_str_ax
        LDA #11
        STA ch_cx
        LDA #16
        STA ch_cy
        LDA p_hp
        JSR write_decimal_2d

        LDA #16
        STA ch_cx
        LDA #16
        STA ch_cy
        LDA #<str_p_atk
        LDX #>str_p_atk
        JSR print_str_ax
        LDA #21
        STA ch_cx
        LDA #16
        STA ch_cy
        LDA p_atk
        JSR write_decimal_2d

        LDA #5
        STA ch_cx
        LDA #14
        STA ch_cy
        LDA #<str_hud_potions
        LDX #>str_hud_potions
        JSR print_str_ax
        LDA #14
        STA ch_cx
        LDA #14
        STA ch_cy
        LDA p_potions
        JSR write_decimal_2d

        ; Action prompt
        LDA #1
        STA ch_cx
        LDA #20
        STA ch_cy
        LDA #<str_combat_prompt
        LDX #>str_combat_prompt
        JSR print_str_ax

        ; Monster portrait: the archetype's SCROLL-O-SPRITES image blitted
        ; x4 (64x64) at x 96..159, y 48..111 — between the monster HP line
        ; (row 5) and the player stats line (row 16). Replaces the juillet
        ; 2026 vector portraits (draw_goblin/draw_orc/draw_mage).
        LDA #3
        STA mob_sz
        LDA #15
        STA mob_curx
        LDA #48
        STA mob_spy
        LDX cur_mob
        JSR draw_packed_mob
        JSR sprite_color_white
        ; tint the portrait with the foe's archetype colour (and wipe any
        ; stale colour left by the 3D view, whose monster region overlaps
        ; this 64x64 box). Reuse color_rect over the portrait rectangle.
        LDA #96
        STA cr_x
        LDA #48
        STA cr_y
        LDA #64
        STA cr_w
        STA cr_h
        LDX cur_mob
        LDA mob_type,X
        TAY
        LDA mob_colors,Y
        STA cr_col
        JSR color_rect
        JSR draw_combat_intent
        JSR vdp_display_on      ; reveal the finished combat screen
        RTS

; Row 18 tells the player when an orc or dragon has wound up a heavy hit.
draw_combat_intent:
        LDA #144
        LDX #152
        JSR clear_span
        LDA #3
        STA ch_cx
        LDA #18
        STA ch_cy
        LDX cur_mob
        LDA mob_type,X
        CMP #0
        BNE @not_goblin
        LDA #<str_intent_goblin
        LDX #>str_intent_goblin
        JMP print_str_ax
@not_goblin:
        CMP #2
        BNE @charger
        LDA #<str_intent_mage
        LDX #>str_intent_mage
        JMP print_str_ax
@charger:
        LDA mob_phase
        BEQ @calm
        LDA #<str_intent_strike
        LDX #>str_intent_strike
        JMP print_str_ax
@calm:  LDA #<str_intent_windup
        LDX #>str_intent_windup
        JMP print_str_ax

; combat_update_hp: repaint ONLY the two per-round fields of the combat
; screen — monster HP (cells 7-8 of row 6) and player HP (cells 11-12
; of row 16). write_decimal_2d STORE-overwrites both digit cells, so no
; clearing is needed and the ~1.5k-cycle update needs no display blank.
combat_update_hp:
        LDA #7
        STA ch_cx
        LDA #6
        STA ch_cy
        LDX cur_mob
        LDA mob_hp,X
        JSR write_decimal_2d
        LDA #11
        STA ch_cx
        LDA #16
        STA ch_cy
        LDA p_hp
        JSR write_decimal_2d
        LDA #14
        STA ch_cx
        LDA #14
        STA ch_cy
        LDA p_potions
        JSR write_decimal_2d
        RTS

; =============================================
; Monster patterns: tools/pack_sprites.py converts the original TMS-format
; 16x16 rows into native HGR sprites in seven sizes. Runtime colour comes
; from hgr_spr16_color_a in hgr_sprite_color.inc.
; =============================================

; archetype -> 16x16 pattern (Quale's three sprites, then original dragon)
; Original 16x16 winged dragon, in the sprite blitter's left/right format.
dragon_pat:
        .byte $00,$11,$3B,$7F,$FF,$EF,$6F,$3D
        .byte $1D,$1F,$3D,$79,$71,$61,$C1,$81
        .byte $C0,$E2,$F7,$FE,$FF,$F7,$F6,$BC
        .byte $B8,$F8,$BC,$9E,$8E,$86,$83,$81

; =============================================
; DATA TABLES
; =============================================

; row_offset[r] = r * NCOLS  (NCOLS=11)
row_offset:
        .byte 0, 11, 22, 33, 44, 55, 66

; depth frame coordinates (11 entries: depth 0..MAX_DEPTH).
; Vertical span 0..159 ONLY: rows 20-23 (y 160..191) are the 4-line text
; zone under the 3D view (HUD on row 20, rows 21-23 free for messages).
; Horizon = 79/80.
; depth 0 = whole viewport, 10 = distant vanishing rectangle
frame_lx:
        .byte 0,40,72,96,104,112,120,124,125,126,127
frame_rx:
        .byte 255,215,183,159,151,143,135,131,130,129,128
frame_ty:
        .byte 0,25,45,60,66,72,76,78,78,79,79
frame_by:
        .byte 159,134,114,99,93,87,83,81,81,80,80

; Monster names
mob_names_lo:
        .byte <str_mob_gob, <str_mob_orc, <str_mob_mage, <str_mob_dragon
mob_names_hi:
        .byte >str_mob_gob, >str_mob_orc, >str_mob_mage, >str_mob_dragon

; ---- Strings (null-terminated, ASCII < 128) ----
str_config: .byte "CONFIGURATION",0
str_config_sound: .byte "S  SOUND",0
str_config_depth: .byte "D  VIEW DEPTH",0
str_config_resume: .byte "R / RETURN / ESC  RESUME",0
str_config_save: .byte "W  SAVE GAME",0
str_config_saved: .byte "      GAME SAVED      ",0
str_config_no_save: .byte "   SAVE UNAVAILABLE   ",0
str_config_quit: .byte "Q  QUIT TO DOS",0
str_on: .byte "ON ",0
str_off: .byte "OFF",0
str_state_load: .byte "BLOAD MAZESTATE",0
str_profile: .byte "PROFILE",0
str_saved: .byte "SAVED",0
str_empty_save: .byte "EMPTY",0
str_profile_keys: .byte "1-3 PROFILE C CONTINUE N NEW",0
str_title_load: .byte "BLOAD MAZETITLE,A$1100",0
str_text_load: .byte "BLOAD MAZETEXT",0
str_title_keys: .byte "S=SEED R=REPLAY ESC=OPTIONS",0
str_title_start: .byte "ANY KEY STARTS",0
str_title1:   .byte "MAZE 3D",0
str_title2:   .byte "WIZARDRY-STYLE",0
str_title3:   .byte "DUNGEON CRAWLER",0
str_title4:   .byte "FOR THE APPLE II (HGR)",0
str_title_hint:.byte "S=ENTER SEED  H=HELP IN GAME",0
str_title_replay:.byte "R=REPLAY SEED",0
str_press_any:.byte "PRESS ANY KEY...",0
str_title_author:.byte "BY VERHILLE ARNAUD  2026",0

str_help_h1:  .byte "HOW TO PLAY",0
; 31 chars max: printed at ch_cx=1 on the 32-column grid — the old l2 was
; 32 chars, its final 'T' wrapped to the next row ("TK BACKWARD" glitch).
str_help_l1:  .byte "I   FORWARD       J  TURN LEFT",0
str_help_l2:  .byte "K   BACKWARD      L  TURN RIGHT",0
str_help_l3:  .byte "M MAP   P DRINK POTION",0
str_help_l4:  .byte "A HIT  G GUARD  F FLEE (FIGHT)",0
str_help_l5:  .byte "ESC  CONFIGURATION / QUIT",0

str_help_l6:  .byte "FIND RELIC IN THE R CHAMBER",0
str_help_l7:  .byte "E EXIT; DRAGON GUARDS FLOOR 3",0
str_help_l8:  .byte "CACHES GIVE GOLD AND POTIONS",0

str_help_l9:  .byte "G GUARD BOOSTS YOUR NEXT HIT",0
str_help_l10: .byte "TITLE: S SEED / R BEST SEED",0

str_win1:     .byte "YOU FOUND THE EXIT!",0
str_win2:     .byte "THE LIGHT OF DAY GREETS YOU.",0
str_win3:     .byte "VICTORY!",0

str_lose1:    .byte "YOU HAVE FALLEN.",0
str_lose2:    .byte "THE DUNGEON KEEPS YOU.",0

str_map_title:.byte "DUNGEON MAP",0
str_map_help: .byte "M=BACK TO 3D  ESC=OPTIONS",0
str_seed:     .byte "SEED",0
str_seed_title: .byte "ENTER DUNGEON SEED",0
str_seed_range: .byte "4 HEX DIGITS: 0001-FFFF",0
str_seed_keys: .byte "RETURN STARTS / LEFT ERASES",0
str_seed_cancel: .byte "ESC OPENS CONFIGURATION",0
str_score:    .byte "SCORE",0
str_best:     .byte "BEST",0
str_floor:    .byte "FLOOR",0
str_dragon_blocks: .byte "THE DRAGON GUARDS THE EXIT",0
str_relic_blocks: .byte "FIND THE CHAMBER RELIC",0
str_relic_found: .byte "THE RELIC IS YOURS!",0
str_cache_found: .byte "A HIDDEN CACHE! GOLD AND GEAR",0
str_shop_title: .byte "BETWEEN FLOORS",0
str_shop_gold:  .byte "GOLD:",0
str_shop_heal:  .byte "H: HEAL 10 HP        8 GOLD",0
str_shop_atk:   .byte "A: +1 ATTACK        12 GOLD",0
str_shop_def:   .byte "D: +1 DEFENSE       12 GOLD",0
str_shop_potion:.byte "P: +1 POTION         6 GOLD",0
str_shop_next:  .byte "C: DESCEND   ESC: OPTIONS",0

str_hud_hp:   .byte "HP",0
str_hud_atk:  .byte "ATK",0
str_hud_lvl:  .byte "LVL",0
str_hud_def:  .byte "DEF",0
str_hud_xp:   .byte "XP",0
str_hud_gold: .byte "GOLD",0
str_hud_potions:.byte "POTIONS",0

; Compass direction spelled out, shown top-centre in colour. Indexed by
; p_face (0=N 1=E 2=S 3=W) via dir_word_lo/hi.
str_dir_n:    .byte "NORTH",0
str_dir_e:    .byte "EAST",0
str_dir_s:    .byte "SOUTH",0
str_dir_w:    .byte "WEST",0
dir_word_lo:  .byte <str_dir_n, <str_dir_e, <str_dir_s, <str_dir_w
dir_word_hi:  .byte >str_dir_n, >str_dir_e, >str_dir_s, >str_dir_w

; ---------------------------------------------------------------------------
.include "narrator.asm"
.code


str_combat_title:   .byte "COMBAT!",0
str_mob_hp:   .byte "HP",0
str_p_hp:     .byte "HP",0
str_p_atk:    .byte "ATK",0
str_combat_prompt: .byte "A=HIT G=GUARD P=HEAL F=FLEE",0
str_intent_goblin: .byte "GOBLIN MAY STEAL GOLD",0
str_intent_mage:   .byte "MAGIC IGNORES YOUR ARMOR",0
str_intent_windup: .byte "FOE GATHERS ITS STRENGTH",0
str_intent_strike: .byte "HEAVY STRIKE NEXT TURN!",0

str_mob_gob:  .byte "GOBLIN",0
str_mob_orc:  .byte "ORC",0
str_mob_mage: .byte "DARK MAGE",0
str_mob_dragon: .byte "DRAGON",0

; =============================================
; FONT (8x8, ASCII $20..$5F = 64 glyphs * 8 = 512 bytes)
; Bit 7 = leftmost pixel.
; =============================================
font_base:
        ; $20 SPACE
        .byte $00,$00,$00,$00,$00,$00,$00,$00
        ; $21 !
        .byte $30,$30,$30,$30,$30,$00,$30,$00
        ; $22 "
        .byte $66,$66,$66,$00,$00,$00,$00,$00
        ; $23 #
        .byte $66,$66,$FF,$66,$FF,$66,$66,$00
        ; $24 $
        .byte $18,$3E,$60,$3C,$06,$7C,$18,$00
        ; $25 %
        .byte $62,$66,$0C,$18,$30,$66,$46,$00
        ; $26 &
        .byte $3C,$66,$3C,$38,$67,$66,$3F,$00
        ; $27 '
        .byte $30,$30,$60,$00,$00,$00,$00,$00
        ; $28 (
        .byte $0C,$18,$30,$30,$30,$18,$0C,$00
        ; $29 )
        .byte $30,$18,$0C,$0C,$0C,$18,$30,$00
        ; $2A *
        .byte $00,$66,$3C,$FF,$3C,$66,$00,$00
        ; $2B +
        .byte $00,$18,$18,$7E,$18,$18,$00,$00
        ; $2C ,
        .byte $00,$00,$00,$00,$00,$18,$18,$30
        ; $2D -
        .byte $00,$00,$00,$7E,$00,$00,$00,$00
        ; $2E .
        .byte $00,$00,$00,$00,$00,$18,$18,$00
        ; $2F /
        .byte $00,$03,$06,$0C,$18,$30,$60,$00
        ; $30 0
        .byte $3C,$66,$6E,$76,$66,$66,$3C,$00
        ; $31 1
        .byte $18,$18,$38,$18,$18,$18,$7E,$00
        ; $32 2
        .byte $3C,$66,$06,$0C,$30,$60,$7E,$00
        ; $33 3
        .byte $3C,$66,$06,$1C,$06,$66,$3C,$00
        ; $34 4
        .byte $06,$0E,$1E,$66,$7F,$06,$06,$00
        ; $35 5
        .byte $7E,$60,$7C,$06,$06,$66,$3C,$00
        ; $36 6
        .byte $3C,$60,$60,$7C,$66,$66,$3C,$00
        ; $37 7
        .byte $7E,$66,$0C,$18,$18,$18,$18,$00
        ; $38 8
        .byte $3C,$66,$66,$3C,$66,$66,$3C,$00
        ; $39 9
        .byte $3C,$66,$66,$3E,$06,$66,$3C,$00
        ; $3A :
        .byte $00,$18,$18,$00,$00,$18,$18,$00
        ; $3B ;
        .byte $00,$18,$18,$00,$00,$18,$18,$30
        ; $3C <
        .byte $0E,$18,$30,$60,$30,$18,$0E,$00
        ; $3D =
        .byte $00,$00,$7E,$00,$7E,$00,$00,$00
        ; $3E >
        .byte $70,$18,$0C,$06,$0C,$18,$70,$00
        ; $3F ?
        .byte $3C,$66,$06,$0C,$18,$00,$18,$00
        ; $40 @
        .byte $3C,$66,$6E,$6E,$60,$62,$3C,$00
        ; $41 A
        .byte $18,$3C,$66,$66,$7E,$66,$66,$00
        ; $42 B
        .byte $7C,$66,$66,$7C,$66,$66,$7C,$00
        ; $43 C
        .byte $3C,$66,$60,$60,$60,$66,$3C,$00
        ; $44 D
        .byte $78,$6C,$66,$66,$66,$6C,$78,$00
        ; $45 E
        .byte $7E,$60,$60,$78,$60,$60,$7E,$00
        ; $46 F
        .byte $7E,$60,$60,$78,$60,$60,$60,$00
        ; $47 G
        .byte $3C,$66,$60,$6E,$66,$66,$3C,$00
        ; $48 H
        .byte $66,$66,$66,$7E,$66,$66,$66,$00
        ; $49 I
        .byte $3C,$18,$18,$18,$18,$18,$3C,$00
        ; $4A J
        .byte $1E,$0C,$0C,$0C,$0C,$6C,$38,$00
        ; $4B K
        .byte $66,$6C,$78,$70,$78,$6C,$66,$00
        ; $4C L
        .byte $60,$60,$60,$60,$60,$60,$7E,$00
        ; $4D M
        .byte $63,$77,$7F,$6B,$63,$63,$63,$00
        ; $4E N
        .byte $66,$76,$7E,$7E,$6E,$66,$66,$00
        ; $4F O
        .byte $3C,$66,$66,$66,$66,$66,$3C,$00
        ; $50 P
        .byte $7C,$66,$66,$7C,$60,$60,$60,$00
        ; $51 Q
        .byte $3C,$66,$66,$66,$66,$3C,$0E,$00
        ; $52 R
        .byte $7C,$66,$66,$7C,$78,$6C,$66,$00
        ; $53 S
        .byte $3C,$66,$60,$3C,$06,$66,$3C,$00
        ; $54 T
        .byte $7E,$5A,$18,$18,$18,$18,$18,$00
        ; $55 U
        .byte $66,$66,$66,$66,$66,$66,$3C,$00
        ; $56 V
        .byte $66,$66,$66,$66,$66,$3C,$18,$00
        ; $57 W
        .byte $63,$63,$63,$6B,$7F,$77,$63,$00
        ; $58 X
        .byte $66,$66,$3C,$18,$3C,$66,$66,$00
        ; $59 Y
        .byte $66,$66,$66,$3C,$18,$18,$18,$00
        ; $5A Z
        .byte $7E,$06,$0C,$18,$30,$60,$7E,$00
        ; $5B [
        .byte $3C,$30,$30,$30,$30,$30,$3C,$00
        ; $5C backslash
        .byte $00,$60,$30,$18,$0C,$06,$03,$00
        ; $5D ]
        .byte $3C,$0C,$0C,$0C,$0C,$0C,$3C,$00
        ; $5E ^
        .byte $18,$3C,$66,$00,$00,$00,$00,$00
        ; $5F _
        .byte $00,$00,$00,$00,$00,$00,$00,$FF

; =============================================
; GEN2 lib modules (textual includes): hgr_lo/hgr_hi scanline tables +
; hgr_init_clear / hgr_text_restore.
; =============================================
.include "hgr_scanline.inc"
.include "hgr_flip.asm"          ; dev/lib/hgr: draw page by rewriting hgr_hi
.include "hgr_sprite_packed.asm"
.include "rev7.inc"
HGR_TEXT8_NO_PUTS = 1            ; write_char drives hgr_putc8 itself
.include "hgr_text8.asm"
.include "hgr.asm"               ; dev/lib/apple2: hgr_init_clear
; Keep the shared tone implementation, with a game-local mute gate.
.define tone speaker_tone
.include "sound.asm"
.undefine tone
tone:
        PHA
        LDA sound_enabled
        BEQ @muted
        PLA
        JMP speaker_tone
@muted: PLA
        RTS
.include "exit.asm"              ; dev/lib/apple2: apple2_zp_save / apple2_exit
DOS_ZP_START = $50
DOS_ZP_LEN = $B0
.include "dos.asm"               ; DOS score file, preserving the game's ZP

; Shared asset data and rendering modules.

.include "packed_sprites.inc"

lz4fh_src = $02FC
lz4fh_dst = $02FE
in_src = lz4fh_src
in_dst = lz4fh_dst
lz4fh_read = ptr_lo
lz4fh_write = pix_addr_lo
lz4fh_match = str_lo
lz4fh_token = tmp
lz4fh_length = tmp2
unpack_title = lz4fh_unpack
.include "lz4fh.asm"

.include "save.inc"

; Native renderer reuses game scratch without changing its ZP layout.
hl_ln_x0 = ln_x0
hl_ln_y0 = ln_y0
hl_ln_x1 = ln_x1
hl_ln_y1 = ln_y1
hl_ln_dx = ln_dx
hl_ln_dy = ln_dy
hl_ln_sx = ln_sx
hl_ln_err = ln_err
hl_pix_mask = pix_mask
hl_pix_addr_lo = pix_addr_lo
hl_pix_addr_hi = pix_addr_hi
.include "hgr_line.asm"

hc_row = cr_cy
hc_end = cr_cx
hc_ptr = pix_addr_lo
hc_ptr_hi = pix_addr_hi
.include "hgr_clear_rows.asm"

hs_ptr = pix_addr_lo
hs_end_col = pix_col
hs_left_mask = tmp
hs_right_mask = tmp2
.include "hgr_span.asm"
