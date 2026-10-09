; ARKABREAKOUT — original Apple II+ 48K game. GPL-3.0.
; 6502 NMOS, no language card, no IIe video/VBL dependency.
.include "apple2.inc"
.macpack longbranch

.zeropage
ptr: .res 2
page: .res 1
rx: .res 1
ry: .res 1
rw: .res 1
rh: .res 1
first: .res 1
last: .res 1
lm: .res 1
rm: .res 1
row: .res 1
col: .res 1
idx: .res 1
paint: .res 1
cx: .res 1
cy: .res 1
save_x: .res 1
save_y: .res 1
steps_left: .res 1
scratch: .res 1
level_ptr: .res 2
.exportzp ptr1
ptr1 = level_ptr
asset_ptr: .res 2

.segment "LOWBSS"
bricks: .res 96
dirty1: .res 96
dirty2: .res 96
paddle_map: .res 256
extra_balls: .res 18             ; two records matching ball_x..ball_yfrac
sprite_history: .res 64         ; eight x/y/kind records on each HGR page
level_name: .res 11
.assert * <= $1300, lderror, "LOWBSS overlaps music player"
collision_row = $1C00
collision_col = $1D00
level_pack = $1800              ; ten interleaved 48-byte boards + 10-byte names


.segment "BSS"
; Exported symbols are also used by deterministic emulator tests.
.export state, ball_x, ball_y, ball_live, ball_dirx, ball_diry, ball_speed
.export ball_yspeed, ball_frac, ball_yfrac, best_score, reward_hits, ramp_hits
.export loop, hit_count, hud1, hud2, page, old_cap, wait_key, title_menu_key
.export pad_x, pad_width, movement, lives, level, remaining, bricks
.export score, capsule, cap_x, cap_y, effect, paused, frames, mode, speed
state: .res 1             ; 0 title, 1 game, 2 defeat, 3 victory
ball_x: .res 1            ; upper-left, x 2..248, 3x3 white sprite
ball_y: .res 1
ball_live: .res 1
ball_dirx: .res 1         ; 0 right, 1 left
ball_diry: .res 1         ; 0 down, 1 up
ball_speed: .res 1        ; unsigned horizontal fraction, vertical is 1/substep
ball_frac: .res 1
ball_yspeed: .res 1
ball_yfrac: .res 1
pad_x: .res 1
pad_width: .res 1
movement: .res 1          ; 0 stopped, 1 left, 2 right
lives: .res 1
level: .res 1             ; 0..59
remaining: .res 1
score: .res 6             ; ASCII decimal, points capped at 650000
capsule: .res 1           ; 0 absent; E/S/C/D/L/P = 1..6
cap_x: .res 1
cap_y: .res 1
cap_next: .res 1
hit_count: .res 1
ramp_hits: .res 1
reward_hits: .res 1
best_score: .res 6
speed: .res 1             ; substeps/frame (2..7)
effect: .res 1
paused: .res 1
frames: .res 2
mode: .res 1              ; 0 keyboard, 1 joystick/paddles, 2 AppleMouse II
button_old: .res 1
hud1: .res 1
hud2: .res 1
dirty_counts: .res 2
old_valid: .res 2
old_pad: .res 2
old_effect: .res 2
old_width: .res 2
old_bx: .res 2
old_by: .res 2
old_cap: .res 2
old_cx: .res 2
old_cy: .res 2
page_index: .res 1
brick_index: .res 1
brick_row: .res 1
brick_kind: .res 1
brick_col: .res 1
paddle_min: .res 1
paddle_max: .res 1
key_speed: .res 1
cal_old_min: .res 1
cal_old_max: .res 1
pending: .res 1            ; sound event; one short pulse train per frame
.export difficulty, combo, multiplier, pad_y, vertical, extra_balls
.export life_hits, enemy_dx, button_old, fire_lasers, laser_cooldown, furthest
.export normal_speed, cap_next, menu_sector, menu_input, menu_click
.export shot_live, shot_x, shot_y, enemy_live, enemy_x, enemy_y, enemy_hold
.export speed_limit, base_width, current_pack, level_name, sound_muted, menu_loop
pad_y: .res 1
vertical: .res 1
previous_x: .res 1
previous_y: .res 1
difficulty: .res 1
base_width: .res 1
speed_limit: .res 1
ramp_period: .res 1
reward_period: .res 1
normal_speed: .res 1
combo: .res 1
multiplier: .res 1
award_count: .res 1
life_hits: .res 2
current_pack: .res 1
pack_number: .res 1
pack_offset: .res 1
ball_id: .res 1
shot_live: .res 2
shot_x: .res 2
shot_y: .res 2
laser_cooldown: .res 1
object_id: .res 1
history_offset: .res 1
sprite_kind: .res 1
old_height: .res 2
catch_offset: .res 1
enemy_live: .res 2
enemy_x: .res 2
enemy_y: .res 2
enemy_dx: .res 2
enemy_timer: .res 1
enemy_hold: .res 1
enemy_id: .res 1
sound_muted: .res 1
furthest: .res 1
menu_sector: .res 1
menu_origin: .res 1
start_request: .res 1
idle: .res 2
demo: .res 1
reset_end:


.code
        jmp main
HGR_TEXT8_FILTER = hud_filter
HGR_TEXT8_HGR_ORDER = 1           ; bbfont is HGR bit order: no rev7_tab
.include "hgr_text8.asm"
HGR_XOR_DIV7 = div7
HGR_XOR_MOD7 = mod7
.include "hgr_xor.asm"

.code
main:
        APPLE2_PREAMBLE
        jsr apple2_zp_save
        lda #0
        ldx #0
@zp:    sta ptr,x
        inx
        cpx #25
        bne @zp
        ldx #0
@bss:   sta state,x
        inx
        cpx #(reset_end-state)
        bne @bss
        lda #<font
        sta ht_font_lo
        lda #>font
        sta ht_font_hi
        lda #$7f
        sta ht_cm_ev
        sta ht_cm_od
        lda #0
        sta ht_cbit
        sta ht_left
        lda #40
        sta ht_wrap
        lda #'0'
        ldx #5
@best:  sta best_score,x
        dex
        bpl @best
        lda #112
        sta paddle_max
        lda #5
        sta key_speed
        jsr build_paddle_map
        jsr build_collision_tables
        lda #255
        sta current_pack
        lda #1
        sta difficulty
        jsr records_load
        jsr music_load
        jsr mouse_start
        jsr title
        jsr music_title
menu_loop:
        lda start_request
        beq :+
        lda #0
        sta start_request
        jmp start_sector
:       jsr poll_key
        cmp #KC_ESC
        beq @menu
@dispatch:
        cmp #'H'
        beq @records
        cmp #'?'
        beq @help
        cmp #'1'
        bcc @control
        cmp #'4'
        bcs @control
        sec
        sbc #'1'
        sta difficulty
        jsr title
        jmp menu_loop
@menu:  jsr title_menu
        jmp @dispatch
@records:
        jsr records_show
        jsr title
        jmp menu_loop
@help:  jsr help
        jsr title
        jmp menu_loop
@control:
        cmp #'C'
        bne @paddle
        jsr calibrate
        jsr title
        jmp menu_loop
@paddle:
        cmp #'J'
        bne @mouse
        lda #1
        sta mode
        jmp start_game
@mouse: cmp #'M'
        bne @keyboard
        lda _mouse_slot
        beq menu_loop
        lda #2
        sta mode
        jmp start_game
@keyboard:
        cmp #'K'
        beq @keys
        cmp #KC_SPACE
        beq start_game
        cmp #$0D
        beq start_game
        lda _mouse_slot
        beq @idle
        jsr mouse_read
        lda _mouse_buttons
        and #$80
        cmp button_old
        sta button_old
        beq @idle
        cmp #0
        bne start_game
@idle:  inc idle
        bne :+
        inc idle+1
:       lda idle+1
        cmp #5
        bcc @wait
        lda #1
        sta demo
        jmp start_game
@wait:  lda #70
        jsr WAIT
        jmp menu_loop
@keys:  lda #0
        sta mode
start_game:
        lda #0
        sta level
start_sector:
        lda #0
        sta reward_hits
        sta frames
        sta frames+1
        sta life_hits
        sta life_hits+1
        lda #'0'
        ldx #5
@score: sta score,x
        dex
        bpl @score
        ldx difficulty
        lda starting_lives,x
        sta lives
        lda paddle_sizes,x
        sta base_width
        lda maximum_speeds,x
        sta speed_limit
        lda ramp_periods,x
        sta ramp_period
        lda reward_periods,x
        sta reward_period
        lda #1
        sta cap_next
        sta state
        jsr load_level
        lda #1
        sta ball_live
        jsr hud_dirty
loop:
        lda start_request
        beq :+
        lda #0
        sta start_request
        jmp start_sector
:       jsr input
        lda start_request
        beq :+
        jmp loop
:       lda state
        cmp #1
        jne menu_loop
        lda paused
        beq @simulate
        lda hud1
        ora hud2
        bne @render
        jmp @pace
@simulate:
        inc frames
        bne :+
        inc frames+1
:       jsr move_pad
        lda demo
        beq :+
        jsr autopilot
        lda state
        cmp #1
        jne menu_loop
:       jsr paddle_contact
        jsr update_capsule
        jsr lasers_step
        jsr enemies_step
        jsr advance_balls
        lda state
        cmp #1
        jne menu_loop
        lda remaining
        beq @next
@render:
        jsr render
@pace:  jsr beep
        ; Spend less of the frame waiting when controllers / extra balls
        ; already consumed CPU time. The II+ has no readable VBL.
        lda extra_balls+2
        ora extra_balls+11
        bne @multi_delay
        lda mode
        beq @keyboard_delay
        cmp #2
        beq @mouse_delay
        lda #68
        bne @wait
@mouse_delay:
        lda #40
        bne @wait
@keyboard_delay:
        lda #80
        bne @wait
@multi_delay:
        lda mode
        cmp #2
        bne :+
        lda #15
        bne @wait
:       lda #50
@wait:  jsr WAIT
        jmp loop
@next:  jsr music_jingle
        inc level
        lda level
        cmp #60
        bcc @load
        lda #3
        sta state
        jsr ending
        jmp menu_loop
@load:  jsr load_level
        jmp loop

.macro text label, column, line
        lda #column
        sta scratch
        lda #<label
        ldx #>label
        ldy #line
        jsr set_string
.endmacro

; Calibration is optional and retained across replay; invalid ranges fall back.
calibrate:
        lda paddle_min
        sta cal_old_min
        lda paddle_max
        sta cal_old_max
        jsr clear_pages
        text cal_left, 4, 72
        jsr show_graphics
        jsr wait_key
        cmp #KC_ESC
        beq @done
        jsr read_stick
        lda joy_x
        sta paddle_min
        jsr clear_pages
        text cal_right, 4, 72
        jsr show_graphics
        jsr wait_key
        cmp #KC_ESC
        beq @cancel
        jsr read_stick
        lda joy_x
        sec
        sbc paddle_min
        bcc @fallback
        cmp #16
        bcc @fallback
        lda joy_x
        sta paddle_max
        jmp build_paddle_map
@fallback:
        lda #0
        sta paddle_min
        lda #112
        sta paddle_max
        jsr build_paddle_map
        rts
@cancel:
        lda cal_old_min
        sta paddle_min
        lda cal_old_max
        sta paddle_max
@done:  rts
build_paddle_map:
        lda paddle_max
        sec
        sbc paddle_min
        sta rw                 ; denominator
        lda #0
        sta rx                 ; result
        sta ptr
        sta ptr+1              ; division remainder
        ldx #0
@value: cpx paddle_min
        bcc @zero
        beq @zero
        cpx paddle_max
        bcs @maximum
        lda ptr
        clc
        adc #224
        sta ptr
        bcc @divide
        inc ptr+1
@divide:
        lda ptr+1
        bne @subtract
        lda ptr
        cmp rw
        bcc @mapped
@subtract:
        lda ptr
        sec
        sbc rw
        sta ptr
        lda ptr+1
        sbc #0
        sta ptr+1
        inc rx
        jmp @divide
@mapped: lda rx
        jmp @store
@zero:  lda #0
        jmp @store
@maximum:
        lda #224
@store: sta paddle_map,x
        inx
        bne @value
        rts

; Text is white x1. Keep full-screen HGR active during every transition.
clear_pages:
        lda #0
        tax
        sta ptr
        lda #$20
        sta ptr+1
        ldy #0
        lda #0
@clear: sta (ptr),y
        iny
        bne @clear
        inc ptr+1
        ldx ptr+1
        cpx #$60
        bcc @clear
        sta page
        sta ht_page
        sta page_index
        sta old_valid
        sta old_valid+1
        sta hud_active
        sta hud_static
        sta hud_static+1
        ldx #0
@cache: sta hud_chars,x
        inx
        cpx #160
        bcc @cache
        rts
show_graphics:
        jsr hgr_init
        rts
set_string:              ; A/X string pointer; Y scanline; scratch byte column
        sta ht_src_lo
        stx ht_src_hi
        sty ht_sl
        lda scratch
        sta ht_col
        lda page
        sta ht_page
        jmp hgr_puts8


title:
        lda #0
        sta idle
        sta idle+1
        sta state
        jsr clear_pages
        jsr draw_large_title
        lda #0
        sta brick_index
@decor:
        ldx brick_index
        lda #1
        sta bricks,x
        jsr draw_brick
        inc brick_index
        lda brick_index
        cmp #12
        bne @decor
        lda #36
        sta brick_index
@lower:
        ldx brick_index
        lda #1
        sta bricks,x
        jsr draw_brick
        inc brick_index
        lda brick_index
        cmp #48
        bne @lower
        text subtitle, 11, 76
        text menu1, 10, 104
        text title_options, 14, 132
        text best_text, 11, 184
        lda #24
        sta ht_col
        ldx #0
@best:  lda best_score,x
        jsr hgr_putc8
        inx
        cpx #6
        bne @best
        jmp show_graphics

draw_large_title:
        lda #<title_bitmap
        sta asset_ptr
        lda #>title_bitmap
        sta asset_ptr+1
        lda #36
        sta row
@row:   ldx row
        lda hgr_lo,x
        clc
        adc #8
        sta ptr
        lda hgr_hi,x
        adc #0
        sta ptr+1
        ldy #23
@byte:  lda (asset_ptr),y
        sta (ptr),y
        dey
        bpl @byte
        lda row
        and #1
        beq @duplicate
        lda asset_ptr
        clc
        adc #24
        sta asset_ptr
        bcc :+
        inc asset_ptr+1
:
@duplicate:
        inc row
        lda row
        cmp #50
        bne @row
        rts

update_best:
        ldx #0
@compare:
        lda score,x
        cmp best_score,x
        bcc @done
        bne @copy
        inx
        cpx #6
        bne @compare
        rts
@copy:  ldx #5
@digit: lda score,x
        sta best_score,x
        dex
        bpl @digit
@done:  rts

ending:
        lda demo
        beq :+
        lda #0
        sta demo
        jmp title
:       lda state
        cmp #3
        bne :+
        jsr music_victory
:       jsr update_best
        jsr records_submit
        jsr clear_pages
        lda state
        cmp #3
        bne @lost
        text won_text, 9, 56
        jmp @score
@lost:  text lost_text, 14, 56
@score: text final_text, 11, 88
        lda #23
        sta ht_col
        ldx #0
@digits:
        lda score,x
        jsr hgr_putc8
        inx
        cpx #6
        bne @digits
        text best_text, 11, 104
        lda #24
        sta ht_col
        ldx #0
@best:  lda best_score,x
        jsr hgr_putc8
        inx
        cpx #6
        bne @best
        text restart_text, 5, 128
        text menu6, 5, 152
        lda save_status
        cmp #2
        bne :+
        text save_failed, 3, 176
:       jmp show_graphics

load_level:
        jsr fetch_level
        lda level
        cmp furthest
        bcc :+
        sta furthest
:        lda #0
        sta remaining
        sta paused
        sta movement
        sta capsule
        sta effect
        sta hit_count
        sta ramp_hits
        sta pending
        lda base_width
        sta pad_width
        ldx difficulty
        lda starting_speeds,x
        sta speed
        sta normal_speed
        ldy #0
        ldx #0
@cells: lda (level_ptr),y
        pha
        and #15
        jsr unpack_cell
        pla
        lsr
        lsr
        lsr
        lsr
        jsr unpack_cell
        iny
        cpy #48
        bne @cells
        lda #96
        sta dirty_counts
        sta dirty_counts+1
        jsr reset_ball
        jsr clear_pages
        ; Static side walls and ceiling, on both pages.
        jsr walls
        lda #$60
        sta page
        jsr walls
        lda #0
        sta page
        lda #1
        sta hud1
        sta hud2
        jsr render
        jsr render
        rts
reset_ball:
        lda #0
        sta ball_live
        sta ball_frac
        sta ball_yfrac
        sta ramp_hits
        sta effect
        sta capsule
        sta movement
        sta vertical
        sta combo
        sta shot_live
        sta shot_live+1
        sta laser_cooldown
        sta enemy_live
        sta enemy_live+1
        ldx #17
@extras: sta extra_balls,x
        dex
        bpl @extras
        lda #1
        sta multiplier
        ldx difficulty
        lda enemy_periods,x
        sta enemy_timer
        lda base_width
        sta pad_width
        ldx difficulty
        lda starting_speeds,x
        sta speed
        sta normal_speed
        lda #112
        sta pad_x
        lda #175
        sta pad_y
        sta previous_y
        lda base_width
        lsr
        sec
        sbc #1
        sta catch_offset
        lda #1
        sta ball_diry
        lda #0
        sta ball_dirx
        lda #128
        sta ball_speed
        lda #224
        sta ball_yspeed
attach_ball:
        lda catch_offset
        cmp pad_width
        bcc :+
        lda pad_width
        sec
        sbc #1
:       clc
        adc pad_x
        sta ball_x
        lda pad_y
        sec
        sbc #5
        sta ball_y
        rts
input:
        lda mode
        cmp #2
        bne :+
        jsr mouse_read
:       jsr poll_key
        pha
        lda demo
        beq @normal_input
        pla
        beq @nothing
        lda #0
        sta demo
        jsr title
        rts
@nothing:
        lda mode
        beq @no_demo_button
        cmp #2
        bne @demo_stick
        lda _mouse_buttons
        jmp @demo_button
@demo_stick:
        lda BUTN0
        ora BUTN1
@demo_button:
        and #$80
        beq @no_demo_button
        lda #0
        sta demo
        jsr title
@no_demo_button:
        lda #0
        rts
@normal_input:
        pla
        cmp #KC_ESC
        bne :+
        jsr escape_menu
        rts
:       cmp #'M'
        bne :+
        lda _mouse_slot
        jeq @done
        lda #2
        jmp select_control
:       cmp #'K'
        bne :+
        lda #0
        jmp select_control
:       cmp #'J'
        bne :+
        lda #1
        jmp select_control
:       cmp #'W'
        jeq @up
        cmp #KC_UP
        jeq @up
        cmp #'X'
        jeq @down
        cmp #KC_DOWN
        jeq @down
        cmp #'P'
        bne @other
        lda paused
        eor #1
        sta paused
        jsr hud_dirty
        rts
@other: cmp #'+'
        bne @minus
        lda key_speed
        cmp #8
        jcs @done
        inc key_speed
        rts
@minus: cmp #'-'
        bne @direction
        lda key_speed
        cmp #2
        jcc @done
        dec key_speed
        rts
@direction: cmp #'A'
        jeq @left
        cmp #KC_LEFT
        jeq @left
        cmp #'D'
        jeq @right
        cmp #KC_RIGHT
        jeq @right
        cmp #'S'
        beq @stop
        cmp #KC_SPACE
        beq @launch
        lda mode
        beq @done
        cmp #2
        bne @stick_button
        lda _mouse_buttons
        jmp @button
@stick_button:
        lda BUTN0
        ora BUTN1
@button: and #$80
        cmp button_old
        sta button_old
        bne @edge
        cmp #0
        beq @done
        lda paused
        bne @done
        lda effect
        cmp #5
        bne @done
        jmp fire_lasers
@edge:  cmp #0
        bne @launch
@done:  rts
@up:    lda #1
        sta vertical
        rts
@down:  lda #2
        sta vertical
        rts
@left:  lda #1
        sta movement
        rts
@right: lda #2
        sta movement
        rts
@stop:  lda #0
        sta vertical
        sta movement
        rts
@launch:
        lda paused
        bne @done
        lda ball_live
        beq :+
        jmp fire_lasers
:       lda extra_balls+2
        ora extra_balls+11
        bne @done                 ; another ball is flying, no attached ball to release
        lda #1
        sta ball_live
        sta ball_diry
        jmp hud_dirty
select_control:
        sta mode
        lda #0
        sta movement
        sta vertical
        jmp hud_dirty
move_pad:
        lda pad_x
        sta previous_x
        lda pad_y
        sta previous_y
        lda mode
        cmp #2
        beq @mouse
        cmp #1
        beq @stick
        lda vertical
        beq @horizontal
        cmp #1
        bne @down
        lda pad_y
        sec
        sbc #3
        sta pad_y
        jmp @horizontal
@down:  lda pad_y
        clc
        adc #3
        sta pad_y
@horizontal:
        jsr keyboard_pad
        jmp clamp_height
@mouse: ldx _mouse_x
        lda mouse_map,x
        sta pad_x
        lda _mouse_y
        sta pad_y
        jsr clamp_pad
        jmp clamp_height
@stick: jsr read_stick
        ldx joy_x
        lda paddle_map,x
        sta pad_x
        ; A standalone paddle 0 leaves timer 1 charged: stay on the floor.
        lda PADDL1
        bpl @two_axes
        lda #175
        sta pad_y
        jsr clamp_pad
        jmp clamp_height
@two_axes:
        ; Map the second timer 0..112 into height 100..175.
        lda joy_y
        cmp #112
        bcc :+
        lda #112
:       lsr
        sta scratch
        lsr
        clc
        adc scratch
        clc
        adc #100
        sta pad_y
        jsr clamp_pad
        jmp clamp_height
keyboard_pad:
@keys:  lda movement
        beq clamp_pad
        cmp #1
        bne @right
        lda pad_x
        sec
        sbc key_speed
        bcc @min
        cmp #2
        bcc @min
        sta pad_x
        jmp clamp_pad
@min:   lda #2
        sta pad_x
        rts
@right: lda pad_x
        clc
        adc key_speed
        sta pad_x
clamp_pad: lda #251
        sec
        sbc pad_width
        cmp pad_x
        bcs @done
        sta pad_x
@done:  lda pad_x
        cmp #2
        bcs :+
        lda #2
        sta pad_x
:       rts

set_pad_width:
        ; Keep the paddle centre steady when a capsule changes its width.
        sta scratch
        lda pad_width
        cmp scratch
        beq @done
        bcc @grow
        sec
        sbc scratch
        lsr
        clc
        adc pad_x
        sta pad_x
        jmp @width
@grow:  lda scratch
        sec
        sbc pad_width
        lsr
        sta rw
        lda pad_x
        sec
        sbc rw
        bcs :+
        lda #2
:       sta pad_x
@width: lda scratch
        sta pad_width
        lsr
        sec
        sbc #1
        sta catch_offset
        jsr clamp_pad
        jmp clamp_height
@done:  rts

ball_step:
        ; Normalized fractional velocity on both axes, at most 1 pixel/axis.
        ; Resolve axes separately; restore the coordinate on impact.
        lda ball_x
        sta save_x
        lda ball_y
        sta save_y
        lda ball_frac
        clc
        adc ball_speed
        sta ball_frac
        bcc @vertical
        lda ball_dirx
        bne @left
        inc ball_x
        lda ball_x
        cmp #249
        bcc @xbrick
        jmp @xbounce
@left:  dec ball_x
        lda ball_x
        cmp #2
        bcs @xbrick
@xbounce:
        lda ball_dirx
        eor #1
        sta ball_dirx
        lda save_x
        sta ball_x
        jsr wall_sound
        jmp @vertical
@xbrick:
        jsr collide
        bcc @vertical
        jsr damage
        lda effect
        cmp #6
        bne :+
        ldx brick_index
        lda bricks,x
        cmp #255
        bne @vertical
:       lda save_x
        sta ball_x
        lda ball_dirx
        eor #1
        sta ball_dirx
@vertical:
        lda ball_yfrac
        clc
        adc ball_yspeed
        sta ball_yfrac
        jcc @done
        lda ball_diry
        bne @up
        inc ball_y
        lda ball_y
        jsr paddle_contact
        lda ball_diry
        jne @done
@bottom:
        lda ball_y
        cmp #180
        bcc @ybrick
        lda #0
        sta ball_live
        rts
@up:    dec ball_y
        lda ball_y
        cmp #18
        bcs @ybrick
        lda save_y
        sta ball_y
        lda #0
        sta ball_diry
        jsr wall_sound
        rts
@ybrick:
        jsr collide
        bcc @done
        jsr damage
        lda effect
        cmp #6
        bne :+
        ldx brick_index
        lda bricks,x
        cmp #255
        bne @done
:       lda save_y
        sta ball_y
        lda ball_diry
        eor #1
        sta ball_diry
@done:  rts
paddle_angle:
        ; 8 equal impact zones, including when the paddle is wide.
        lda ball_x
        clc
        adc #1
        sec
        sbc pad_x
        bcs :+
        lda #0
:       cmp pad_width
        bcc :+
        lda pad_width
        sec
        sbc #1
:       sta cx
        lda #0
        sta cy
        ldx #3
@multiply:
        asl cx
        rol cy
        dex
        bne @multiply
        ldx #0
@divide:
        lda cy
        bne @subtract
        lda cx
        cmp pad_width
        bcc @zone
@subtract:
        lda cx
        sec
        sbc pad_width
        sta cx
        lda cy
        sbc #0
        sta cy
        inx
        bne @divide
@zone:
        ; Horizontal paddle motion biases the rebound by one impact zone.
        lda pad_x
        cmp previous_x
        beq @angle
        bcc @spin_left
        cpx #7
        bcs @angle
        inx
        bne @angle
@spin_left:
        cpx #0
        beq @angle
        dex
@angle: lda angle_x,x
        sta ball_speed
        lda angle_y,x
        sta ball_yspeed
        lda #0
        sta ball_frac
        sta ball_yfrac
        cpx #4
        bcs :+
        lda #1
:       sta ball_dirx
        rts

; Check four corners against geometry (21x12 cells, solid 18x8).
collide:
        lda ball_x
        sta cx
        lda ball_y
        sta cy
        jsr point_hit
        bcs @hit
        lda ball_x
        clc
        adc #2
        sta cx
        jsr point_hit
        bcs @hit
        lda ball_y
        clc
        adc #2
        sta cy
        jsr point_hit
        bcs @hit
        lda ball_x
        sta cx
        jmp point_hit
@hit:   rts
point_hit:
        ldy cy
        lda collision_row,y
        cmp #255
        beq @miss
        sta idx
        ldy cx
        lda collision_col,y
        cmp #255
        beq @miss
        clc
        adc idx
        tax
        lda bricks,x
        beq @miss
        sec
        rts
@miss:  clc
        rts

damage:
        stx brick_index
        lda bricks,x
        cmp #255
        jeq wall_sound
        lda effect
        cmp #6
        bne :+
        lda #1
        sta bricks,x
:       dec bricks,x
        jsr mark_dirty
        lda #1
        sta pending
        lda bricks,x
        bne @single
        lda combo
        cmp #21
        bcs :+
        inc combo
:       lda combo
        ldx #0
@third: cmp #3
        bcc @combo
        sec
        sbc #3
        inx
        bne @third
@combo: txa
        clc
        adc #1
        sta multiplier
        lda multiplier
        jmp @award
@single: lda #1
@award: jsr award
        ldx brick_index
        lda bricks,x
        bne @done
        dec remaining
        inc ramp_hits
        lda ramp_hits
        cmp ramp_period
        bcc @capsule
        lda #0
        sta ramp_hits
        lda normal_speed
        cmp speed_limit
        bcs @capsule
        inc normal_speed
        lda effect
        cmp #2
        beq @capsule
        lda normal_speed
        sta speed
@capsule:
        inc hit_count
        lda hit_count
        cmp reward_period
        bcc @done
        lda #0
        sta hit_count
        lda capsule
        bne @done
        lda cap_next
        sta capsule
        inc cap_next
        lda cap_next
        cmp #7
        bcc :+
        lda #1
        sta cap_next
:       lda brick_index
        ldx #0
@row:   cmp #12
        bcc @col
        sec
        sbc #12
        inx
        bne @row
@col:   tay
        lda col21,y
        clc
        adc #7
        sta cap_x
        lda row_y,x
        clc
        adc #4
        sta cap_y
@done:  rts
wall_sound:
        lda #3
        sta pending
        rts
add_score:
        lda #1
award:  sta award_count
@again: lda score
        cmp #'6'
        bcc @add
        bne @capped
        lda score+1
        cmp #'5'
        bcs @capped
@add:   ldx #4                ; six digits; units always zero
@digit: inc score,x
        lda score,x
        cmp #':'
        bcc @reward
        lda #'0'
        sta score,x
        dex
        bpl @digit
@reward:
        inc life_hits
        bne :+
        inc life_hits+1
:       lda life_hits+1
        cmp #1
        bne @capped
        lda life_hits
        cmp #244              ; 500 tens = 5000 points
        bcc @capped
        lda #0
        sta life_hits
        sta life_hits+1
        lda lives
        cmp #5
        bcs @capped
        inc lives
        lda #4
        sta pending
@capped:
        dec award_count
        bne @again
        jmp hud_dirty
hud_dirty:
        lda #1
        sta hud1
        sta hud2
        rts
update_capsule:
        lda capsule
        beq @done
        inc cap_y
        lda cap_y
        clc
        adc #7
        cmp pad_y
        bcc @miss
        lda cap_y
        cmp previous_y
        bcs @miss
        lda cap_x
        clc
        adc #6
        cmp pad_x
        bcc @miss
        lda pad_x
        clc
        adc pad_width
        cmp cap_x
        bcc @miss
        beq @miss
        lda capsule
        sta effect
        cmp #1
        bne @slow
        lda base_width
        clc
        adc #14
        jsr set_pad_width
        jmp @caught
@slow:  lda base_width
        jsr set_pad_width
        lda effect
        cmp #2
        bne @caught
        lda #2
        sta speed
@caught:
        jsr apply_effect
        lda #0
        sta capsule
        lda #2
        sta pending
        jsr add_score
        jmp hud_dirty
@miss:  lda cap_y
        cmp #176
        bcc @done
        lda #0
        sta capsule
@done:  rts
beep:
        lda sound_muted
        ora demo
        bne @silent
        lda pending
        beq @done
        tax
        lda pitches,x
        tax
        lda #8               ; bounded: no blocking long tune during play
        jsr tone
        lda #0
        sta pending
@silent: lda #0
        sta pending
@done:  rts

; XOR rectangles: byte masks, arbitrary pixel alignment, 3 rows per object.
; Erase ALL old objects on a hidden page before applying its dirty bricks.
rectangle:
        lda rx
        sta hx_x
        lda ry
        sta hx_y
        lda rw
        sta hx_w
        lda rh
        sta hx_h
        lda page
        sta hx_page
        jmp hgr_xor_rect
walls:
        lda #0
        sta rx
        lda #17
        sta ry
        lda #253
        sta rw
        lda #1
        sta rh
        jsr rectangle
        lda #0
        sta rx
        lda #18
        sta ry
        lda #1
        sta rw
        lda #164
        sta rh
        jsr rectangle
        lda #252
        sta rx
        lda #18
        sta ry
        lda #1
        sta rw
        lda #164
        sta rh
        jmp rectangle

render:
        lda page
        beq @p1
        lda #1
@p1:    sta page_index
        tax
        lda old_valid,x
        beq @dirty
        jsr old_objects
        jsr erase_sprites
@dirty: ldx page_index
        lda dirty_counts,x
        beq @objects
        lda #0
        sta dirty_counts,x
        sta brick_index
@brick: ldx brick_index
        lda page_index
        beq @d1
        lda dirty2,x
        beq @skip
        lda #0
        sta dirty2,x
        jmp @draw
@d1:    lda dirty1,x
        beq @skip
        lda #0
        sta dirty1,x
@draw:  jsr draw_brick
@skip:  inc brick_index
        lda brick_index
        cmp #96
        bne @brick
@objects:
        ldx page_index
        lda effect
        sta old_effect,x
        lda pad_x
        sta old_pad,x
        lda pad_width
        sta old_width,x
        lda pad_y
        sta old_height,x
        lda ball_x
        sta old_bx,x
        lda ball_y
        sta old_by,x
        lda capsule
        sta old_cap,x
        lda cap_x
        sta old_cx,x
        lda cap_y
        sta old_cy,x
        lda #1
        sta old_valid,x
        jsr old_objects
        jsr new_sprites
        lda page_index
        beq @h1
        lda hud2
        beq @present
        lda #0
        sta hud2
        jmp @hud
@h1:    lda hud1
        beq @present
        lda #0
        sta hud1
@hud:   jsr draw_hud
@present:
        lda page
        beq @show1
        bit HISCR
        jmp @flip
@show1: bit LOWSCR
@flip:  bit TXTCLR
        bit HIRES
        bit MIXCLR
        lda page
        eor #$60
        sta page
        rts
old_objects:
        ldx page_index
        lda old_pad,x
        sta rx
        lda old_width,x
        sta rw
        lda old_height,x
        sta ry
        lda #3
        sta rh
        jsr rectangle
        ldx page_index
        lda old_effect,x
        cmp #5
        bne @ball
        ; Two three-pixel barrels, aligned with the shot origins.
        lda old_pad,x
        clc
        adc #1
        sta rx
        lda old_height,x
        sec
        sbc #4
        sta ry
        lda #3
        sta rw
        lda #4
        sta rh
        jsr rectangle
        ldx page_index
        lda old_pad,x
        clc
        adc old_width,x
        sec
        sbc #4
        sta rx
        lda #4
        sta rh
        jsr rectangle
@ball:  ldx page_index
        lda old_bx,x
        sta rx
        lda old_by,x
        sta ry
        lda #3
        sta rw
        sta rh
        jsr rectangle
        ldx page_index
        lda old_effect,x
        cmp #6
        bne @capsule
        ; Pierce is an outlined ball; keep its 3x3 collision footprint.
        inc rx
        inc ry
        lda #1
        sta rw
        sta rh
        jsr rectangle
@capsule:
        ldx page_index
        lda old_cap,x
        beq @done
        lda old_cx,x
        sta rx
        lda old_cy,x
        sta ry
        jsr capsule_sprite
@done:  rts

; Pre-shifted white E/S/C/D/L/P glyphs; XOR preserves the coloured background.
capsule_sprite:
        lda old_cap,x
        sec
        sbc #1
        asl
        tay
        lda cap_assets,y
        sta asset_ptr
        lda cap_assets+1,y
        sta asset_ptr+1
glyph_sprite:
        ldx rx
        lda mod7,x
        asl
        asl
        asl
        asl
        clc
        adc asset_ptr
        sta hx_data
        lda asset_ptr+1
        adc #0
        sta hx_data+1
        lda rx
        sta hx_x
        lda ry
        sta hx_y
        lda page
        sta hx_page
        jmp hgr_xor_sprite

draw_brick:
        lda brick_index
        ldx #0
@row:   cmp #12
        bcc @col
        sec
        sbc #12
        inx
        bne @row
@col:   tay
        lda col3,y
        sta brick_col
        lda state
        bne :+
        inc brick_col       ; centre the 252-pixel title bands in 280 pixels
        inc brick_col
:
        lda row_y,x
        sta brick_row
        ldx brick_index
        lda bricks,x
        sta brick_kind
        beq @empty
        cmp #255
        beq @steel
        cmp #1
        bne @hard
        lda brick_row
        lsr
        lsr
        and #3
        tax
        lda colors,x
        jmp @color
@hard:  lda #$7f
        bne @color
@steel: lda #$ff
@color: sta paint
        jmp @paint
@empty: lda #0
        sta paint
@paint: lda #8
        sta scratch
@line:  ldx brick_row
        lda hgr_lo,x
        sta ptr
        lda hgr_hi,x
        eor page
        sta ptr+1
        ldy brick_col
        jsr paint_byte
        and #$fe
        ldx brick_kind
        beq :+
        ora #$06            ; two bright left-edge pixels form the bevel
:       ; Column zero shares its first bit with the side wall.
        cpy #0
        bne :+
        ora #1
:       sta (ptr),y
        iny
        jsr paint_byte
        sta (ptr),y
        iny
        jsr paint_byte
        and #$8f              ; recessed right edge and three-pixel gap
        ldx state
        bne :+
        ora #$10            ; title frame reaches the symmetric right edge
:       sta (ptr),y
        inc brick_row
        dec scratch
        bne @line
        rts

paint_byte:
        lda brick_kind
        beq @empty
        cmp #2
        beq @resistant
        cmp #3
        bne @body
@resistant:
        lda scratch
        cmp #4
        beq @notches
        cmp #5
        bne @body
@notches:
        tya
        sec
        sbc brick_col
        tax
        lda brick_kind
        cmp #3
        beq @three
        lda hp2_masks,x
        rts
@three: lda hp3_masks,x
        rts
@body:
        lda scratch
        cmp #1
        beq @empty          ; black lower edge gives every brick relief
        cmp #8
        beq @highlight
        lda brick_kind
        cmp #255
        beq @metal
        lda paint
        jmp @parity
@highlight:
        lda #$7f
        rts
@metal: lda scratch
        and #1
        beq @highlight
        lda #$2a             ; alternating hatch, distinct even in monochrome
@parity:
        sta idx
        and #$7f
        cmp #$2a
        beq @pattern
        cmp #$55
        beq @pattern
        lda idx
        rts
@pattern:
        tya
        and #1
        beq @even
        lda idx
        eor #$7f
        rts
@even:  lda idx
        rts
@empty: lda #0
        rts

draw_hud:
        lda #1
        sta hud_active
        lda page
        sta ht_page
        ldx page_index
        lda hud_static,x
        bne @fields
        text hud_text, 1, 4
        text footer, 1, 184
        ldx page_index
        lda #1
        sta hud_static,x
@fields:
        lda #4
        sta ht_sl
        lda #3
        sta ht_col
        ldx #0
@score: lda score,x
        jsr hgr_putc8
        inx
        cpx #6
        bne @score
        lda #12
        sta ht_col
        lda lives
        clc
        adc #'0'
        jsr hgr_putc8
        lda #16
        sta ht_col
        lda multiplier
        clc
        adc #'0'
        jsr hgr_putc8
        lda #20
        sta ht_col
        lda level
        clc
        adc #1
        ldx #0
@tens: cmp #10
        bcc @digits
        sec
        sbc #10
        inx
        bne @tens
@digits:
        pha
        txa
        clc
        adc #'0'
        jsr hgr_putc8
        pla
        clc
        adc #'0'
        jsr hgr_putc8
        text level_name, 24, 4
        lda effect
        asl
        tax
        lda effect_strings,x
        sta ht_src_lo
        lda effect_strings+1,x
        sta ht_src_hi
        lda #184
        sta ht_sl
        lda #28
        sta ht_col
        jsr hgr_puts8
        lda paused
        bne @pause
        lda ball_live
        ora extra_balls+2
        ora extra_balls+11
        beq @ready
        text playing_text, 34, 184
        jmp hud_end
@pause: text pause_text, 34, 184
        jmp hud_end
@ready: text ready_text, 34, 184
        jmp hud_end

hud_end:
        lda #0
        sta hud_active
        rts

.include "hud_cache.inc"
.include "mechanics.inc"
.include "interface.inc"
.include "records.inc"
.include "music.inc"
.include "hgr.asm"
.include "kbd.asm"
.include "joy.asm"
.include "sound.asm"
APPLE2_EXIT_HOOK = mouse_shutdown
.include "exit.asm"
DOS_ZP_START = $50
DOS_ZP_LEN = $B0
.include "dos.asm"
.include "mouse_context.asm"

.rodata
best_text: .asciiz "BEST SCORE  "
subtitle: .asciiz "60 SECTORS TO CLEAR"
title_options: .asciiz "ESC : MENU"
menu1: .asciiz "SPACE / ENTER : PLAY"
menu2: .asciiz "K KEYBOARD  J PADDLE  M MOUSE"
menu3: .asciiz "A/D : MOVE    W/X : HEIGHT"
menu4: .asciiz "S : STOP   SPACE : LAUNCH"
menu5: .asciiz "1 RELAX / 2 ARCADE / 3 EXPERT"
calibration_text: .asciiz "C CALIBRATE  ? HELP  H RECORDS"
cal_left: .asciiz "PADDLE LEFT, THEN PRESS A KEY"
cal_right: .asciiz "PADDLE RIGHT, THEN PRESS A KEY"
menu6: .asciiz "P : PAUSE   ESC : MENU"
lost_text: .asciiz "GAME OVER"
won_text: .asciiz "ALL SECTORS CLEARED!"
final_text: .asciiz "FINAL SCORE"
restart_text: .asciiz "SPACE : REPLAY   J : PADDLE"
hud_text: .asciiz "S:       L:  X:  N:                  "
footer: .asciiz "SPACE/BUTTON FIRE ESC MENU "
effect_strings: .word no_effect, wide_text, slow_text, catch_text, multi_text, laser_text, pierce_text
multi_text: .asciiz "MULTI"
laser_text: .asciiz "LASER"
pierce_text: .asciiz "PIERC"
no_effect: .asciiz "     "
wide_text: .asciiz "WIDE "
slow_text: .asciiz "SLOW "
catch_text: .asciiz "CATCH"
playing_text: .asciiz "     "
pause_text: .asciiz "PAUSE"
ready_text: .asciiz "READY"
pitches: .byte 0, 22, 42, 70, 12
angle_x: .byte 240,208,160,64,64,160,208,240
angle_y: .byte 96,144,200,248,248,200,144,96
hp2_masks: .byte $67,$73,$7f
hp3_masks: .byte $4f,$73,$7c
colors: .byte $2a,$55,$aa,$d5
mouse_map:
.repeat 140,I
.byte (I*249)/139
.endrepeat
left_masks: .byte $7f,$7e,$7c,$78,$70,$60,$40
right_masks: .byte $01,$03,$07,$0f,$1f,$3f,$7f
row12: .byte 0,12,24,36,48,60,72,84
row_y: .byte 24,36,48,60,72,84,96,108
col21:
.repeat 12,I
.byte I*21
.endrepeat
col3:
.repeat 12,I
.byte I*3
.endrepeat
div7:
.repeat 256,I
.byte I/7
.endrepeat
mod7:
.repeat 256,I
.byte I .mod 7
.endrepeat
.include "hgr_scanline.inc"
font:
.include "bbfont.inc"           ; font = bbfont, ASCII $20-$5F
starting_lives: .byte 5,3,2
paddle_sizes: .byte 42,35,28
starting_speeds: .byte 2,3,4
maximum_speeds: .byte 4,6,7
ramp_periods: .byte 10,8,6
reward_periods: .byte 4,5,6
.include "capsules.inc"
.include "title.inc"
