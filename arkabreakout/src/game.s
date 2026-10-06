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
asset_ptr: .res 2

.segment "LOWBSS"
bricks: .res 96
dirty1: .res 96
dirty2: .res 96
paddle_map: .res 256

.segment "BSS"
; Exported symbols are also used by deterministic emulator tests.
.export state, ball_x, ball_y, ball_live, ball_dirx, ball_diry, ball_speed
.export ball_yspeed, ball_frac, ball_yfrac, best_score, reward_hits, ramp_hits
.export loop, hit_count
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
level: .res 1             ; 0..11
remaining: .res 1
score: .res 5             ; ASCII decimal, 10 points per hit
capsule: .res 1           ; 0 absent; 1 wide, 2 slow, 3 catch
cap_x: .res 1
cap_y: .res 1
cap_next: .res 1
hit_count: .res 1
ramp_hits: .res 1
reward_hits: .res 1
best_score: .res 5
speed: .res 1             ; substeps/frame (2..5)
effect: .res 1
paused: .res 1
frames: .res 2
mode: .res 1              ; 0 keyboard, 1 paddle
button_old: .res 1
hud1: .res 1
hud2: .res 1
old_valid: .res 2
old_pad: .res 2
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

.code
        jmp main
HGR_TEXT8_HGR_ORDER = 1           ; bbfont is HGR bit order: no rev7_tab
.include "hgr_text8.asm"

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
        cpx #(pending-state+1)
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
        ldx #4
@best:  sta best_score,x
        dex
        bpl @best
        lda #112
        sta paddle_max
        lda #5
        sta key_speed
        jsr build_paddle_map
        jsr title
menu_loop:
        jsr poll_key
        cmp #KC_ESC
        jeq apple2_exit
        cmp #'C'
        bne @paddle
        jsr calibrate
        jsr title
        jmp menu_loop
@paddle: cmp #'J'
        bne @keyboard
        lda #1
        sta mode
        jmp start_game
@keyboard:
        cmp #KC_SPACE
        bne menu_loop
        lda #0
        sta mode
start_game:
        lda #0
        sta level
        sta reward_hits
        sta frames
        sta frames+1
        lda #'0'
        ldx #4
@score: sta score,x
        dex
        bpl @score
        lda #3
        sta lives
        lda #1
        sta state
        jsr load_level
loop:
        jsr input
        lda state
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
        jsr update_capsule
        lda ball_live
        bne @active
        jsr attach_ball
        jmp @render
@active:
        lda speed
        sta steps_left
@step:  jsr ball_step
        lda state
        cmp #1
        jne menu_loop
        lda ball_live
        beq @render
        lda remaining
        beq @next
        dec steps_left
        bne @step
@render:
        jsr render
@pace:  jsr beep
        ; Compensate for the ~6ms paddle read to keep control modes comparable.
        ; II+ has no readable VBL; this remains a CPU delay, not video sync.
        lda mode
        beq @keyboard_delay
        lda #88
        bne @wait
@keyboard_delay:
        lda #100
@wait:  jsr WAIT
        jmp loop
@next:  inc level
        lda level
        cmp #12
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

; Text is white x1. Screen transitions initialize both pages while text shows.
clear_pages:
        bit TXTSET
        lda #0
        tax
@clear:
.repeat 64, I
        sta $2000+I*$100,x
.endrepeat
        inx
        jne @clear
        sta page
        sta ht_page
        sta page_index
        sta old_valid
        sta old_valid+1
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
        text menu1, 5, 96
        text menu2, 5, 108
        text menu3, 5, 120
        text menu4, 5, 132
        text menu5, 5, 144
        text calibration_text, 5, 156
        text menu6, 5, 168
        text best_text, 11, 184
        lda #24
        sta ht_col
        ldx #0
@best:  lda best_score,x
        jsr hgr_putc8
        inx
        cpx #5
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
        lda asset_ptr
        clc
        adc #24
        sta asset_ptr
        bcc :+
        inc asset_ptr+1
:       inc row
        lda row
        cmp #52
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
        cpx #5
        bne @compare
        rts
@copy:  ldx #4
@digit: lda score,x
        sta best_score,x
        dex
        bpl @digit
@done:  rts

ending:
        jsr update_best
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
        cpx #5
        bne @digits
        text best_text, 11, 104
        lda #24
        sta ht_col
        ldx #0
@best:  lda best_score,x
        jsr hgr_putc8
        inx
        cpx #5
        bne @best
        text restart_text, 5, 128
        text menu6, 5, 152
        jmp show_graphics

load_level:
        lda level
        asl
        tax
        lda levels,x
        sta level_ptr
        lda levels+1,x
        sta level_ptr+1
        lda #0
        sta remaining
        sta paused
        sta movement
        sta capsule
        sta effect
        sta hit_count
        sta ramp_hits
        sta pending
        lda #1
        sta cap_next
        lda #28
        sta pad_width
        lda level
        lsr
        lsr
        clc
        adc #2
        sta speed
        ldy #0
@cells: lda (level_ptr),y
        sta bricks,y
        beq @skip
        cmp #255
        beq @skip
        inc remaining
@skip:  lda #1
        sta dirty1,y
        sta dirty2,y
        iny
        cpy #96
        bne @cells
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
        lda #28
        sta pad_width
        lda level
        lsr
        lsr
        clc
        adc #2
        sta speed
        lda #112
        sta pad_x
        lda #1
        sta ball_diry
        lda #0
        sta ball_dirx
        lda #128
        sta ball_speed
        lda #224
        sta ball_yspeed
attach_ball:
        lda pad_width
        lsr
        clc
        adc pad_x
        sec
        sbc #1
        sta ball_x
        lda #170
        sta ball_y
        rts
input:
        jsr poll_key
        cmp #KC_ESC
        jeq apple2_exit
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
        beq @left
        cmp #KC_LEFT
        beq @left
        cmp #'D'
        beq @right
        cmp #KC_RIGHT
        beq @right
        cmp #'S'
        beq @stop
        cmp #KC_SPACE
        beq @launch
        lda mode
        beq @done
        lda BUTN0
        and #$80
        cmp button_old
        sta button_old
        beq @done
        cmp #0
        bne @launch
@done:  rts
@left:  lda #1
        sta movement
        rts
@right: lda #2
        sta movement
        rts
@stop:  lda #0
        sta movement
        rts
@launch:
        lda paused
        bne @done
        lda ball_live
        bne @done
        lda #1
        sta ball_live
        sta ball_diry
        jmp hud_dirty
move_pad:
        lda mode
        beq @keys
        jsr read_stick
        ldx joy_x
        lda paddle_map,x
        sta pad_x
        jmp clamp_pad
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
        jmp clamp_pad
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
        lda save_x
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
        cmp #172
        bne @bottom
        ; paddle collision, including the ball's full 3 pixel extent
        lda ball_x
        clc
        adc #2
        cmp pad_x
        bcc @bottom
        lda pad_x
        clc
        adc pad_width
        cmp ball_x
        bcc @bottom
        beq @bottom
        lda #1
        sta ball_diry
        jsr paddle_angle
        lda #2
        sta pending
        lda effect
        cmp #3
        bne @done
        lda #0
        sta ball_live
        jsr hud_dirty
        rts
@bottom:
        lda ball_y
        cmp #180
        bcc @ybrick
        dec lives
        jsr hud_dirty
        lda lives
        beq @dead
        jsr reset_ball
        rts
@dead:  lda #2
        sta state
        jsr ending
        ; Caller checks state before rendering the cleared ending screen.
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
        lda save_y
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
@zone:  lda angle_x,x
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
        lda cy
        sec
        sbc #24
        bcc @miss
        cmp #96
        bcs @miss
        ldx #0
@row:   cmp #12
        bcc @rowfound
        sbc #12
        inx
        bne @row
@rowfound:
        cmp #8
        bcs @miss
        lda row12,x
        sta idx
        lda cx
        ldx #0
@col:   cmp #21
        bcc @colfound
        sbc #21
        inx
        bne @col
@colfound:
        cmp #1
        bcc @miss
        cmp #19
        bcs @miss
        cpx #12
        bcs @miss
        txa
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
        lda bricks,x
        cmp #255
        jeq wall_sound
        dec bricks,x
        stx brick_index
        lda #1
        sta dirty1,x
        sta dirty2,x
        sta pending
        jsr add_score
        ldx brick_index
        lda bricks,x
        bne @done
        dec remaining
        inc ramp_hits
        lda ramp_hits
        cmp #12
        bcc @capsule
        lda #0
        sta ramp_hits
        lda speed
        cmp #5
        bcs @capsule
        inc speed
@capsule:
        inc hit_count
        lda hit_count
        cmp #5
        bcc @done
        lda #0
        sta hit_count
        lda capsule
        bne @done
        lda cap_next
        sta capsule
        inc cap_next
        lda cap_next
        cmp #4
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
        ldx #3               ; increment tens, last digit stays zero
@digit: inc score,x
        lda score,x
        cmp #':'
        bcc @reward
        lda #'0'
        sta score,x
        dex
        bpl @digit
@reward:
        inc reward_hits
        lda reward_hits
        cmp #100
        bcc hud_dirty
        lda #0
        sta reward_hits
        lda lives
        cmp #5
        bcs hud_dirty
        inc lives
        lda #4
        sta pending
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
        cmp #170
        bne @miss
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
        lda #42
        jsr set_pad_width
        jmp @caught
@slow:  lda #28
        jsr set_pad_width
        lda effect
        cmp #2
        bne @caught
        lda #2
        sta speed
@caught:
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
        lda pending
        beq @done
        tax
        lda pitches,x
        tax
        lda #8               ; bounded: no blocking long tune during play
        jsr tone
        lda #0
        sta pending
@done:  rts

; XOR rectangles: byte masks, arbitrary pixel alignment, 3 rows per object.
; Erase ALL old objects on a hidden page before applying its dirty bricks.
rectangle:
        ldx rx
        lda div7,x
        sta first
        lda mod7,x
        tax
        lda left_masks,x
        sta lm
        lda rx
        clc
        adc rw
        sec
        sbc #1
        tax
        lda div7,x
        sta last
        lda mod7,x
        tax
        lda right_masks,x
        sta rm
        lda ry
        sta row
@line:  ldx row
        lda hgr_lo,x
        sta ptr
        lda hgr_hi,x
        eor page
        sta ptr+1
        ldy first
@byte:  lda #$7f
        cpy first
        bne :+
        and lm
:       cpy last
        bne :+
        and rm
:       eor (ptr),y
        sta (ptr),y
        cpy last
        beq @line_end
        iny
        bne @byte
@line_end:
        inc row
        dec rh
        bne @line
        rts
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
@dirty: lda #0
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
        ldx page_index
        lda pad_x
        sta old_pad,x
        lda pad_width
        sta old_width,x
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
        lda #175
        sta ry
        lda #3
        sta rh
        jsr rectangle
        ldx page_index
        lda old_bx,x
        sta rx
        lda old_by,x
        sta ry
        lda #3
        sta rw
        sta rh
        jsr rectangle
        ldx page_index
        lda old_cap,x
        beq @done
        lda old_cx,x
        sta rx
        lda old_cy,x
        sta ry
        jsr capsule_sprite
@done:  rts

; Pre-shifted white W/S/C glyphs; XOR preserves the coloured background.
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
        ldx rx
        lda div7,x
        sta col
        lda mod7,x
        asl
        asl
        asl
        asl
        clc
        adc asset_ptr
        sta asset_ptr
        bcc :+
        inc asset_ptr+1
:       lda ry
        sta row
        lda #0
        sta idx
@line:  ldx row
        lda hgr_lo,x
        sta ptr
        lda hgr_hi,x
        eor page
        sta ptr+1
        ldy idx
        lda (asset_ptr),y
        ldy col
        eor (ptr),y
        sta (ptr),y
        inc idx
        ldy idx
        lda (asset_ptr),y
        ldy col
        iny
        eor (ptr),y
        sta (ptr),y
        inc idx
        inc row
        lda idx
        cmp #16
        bne @line
        rts

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
        ; Column zero shares its first bit with the side wall.
        cpy #0
        bne :+
        ora #1
:       sta (ptr),y
        iny
        jsr paint_byte
        sta (ptr),y
        iny
        jsr paint_byte
        and #$9f              ; leave 2-pixel horizontal gap
        sta (ptr),y
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
        lda page
        sta ht_page
        text hud_text, 1, 4
        lda #7
        sta ht_col
        ldx #0
@score: lda score,x
        jsr hgr_putc8
        inx
        cpx #5
        bne @score
        lda #21
        sta ht_col
        lda lives
        clc
        adc #'0'
        jsr hgr_putc8
        lda #33
        sta ht_col
        lda level
        clc
        adc #1
        cmp #10
        bcc @single
        lda #'1'
        jsr hgr_putc8
        lda level
        sec
        sbc #9
        jmp @units
@single:
        pha
        lda #'0'
        jsr hgr_putc8
        pla
@units: clc
        adc #'0'
        jsr hgr_putc8
        lda mode
        beq @keyboard
        text paddle_footer, 1, 184
        jmp @effect
@keyboard:
        text footer, 1, 184
@effect:
        lda effect
        asl
        tax
        lda effect_strings,x
        sta ht_src_lo
        lda effect_strings+1,x
        sta ht_src_hi
        lda #28
        sta ht_col
        jsr hgr_puts8
        lda paused
        bne @pause
        lda ball_live
        beq @ready
        text playing_text, 34, 184
        rts
@pause: text pause_text, 34, 184
        rts
@ready: text ready_text, 34, 184
        rts

.include "hgr.asm"
.include "kbd.asm"
.include "joy.asm"
.include "sound.asm"
.include "exit.asm"

.rodata
best_text: .asciiz "SESSION BEST"
subtitle: .asciiz "12 SECTORS TO CLEAR"
menu1: .asciiz "SPACE : PLAY WITH KEYBOARD"
menu2: .asciiz "J     : PLAY WITH PADDLE"
menu3: .asciiz "A/D OR ARROWS : MOVE"
menu4: .asciiz "S : STOP   SPACE : LAUNCH"
menu5: .asciiz "W WIDE / S SLOW / C CATCH"
calibration_text: .asciiz "C : CALIBRATE   +/- : SPEED"
cal_left: .asciiz "PADDLE LEFT, THEN PRESS A KEY"
cal_right: .asciiz "PADDLE RIGHT, THEN PRESS A KEY"
menu6: .asciiz "P : PAUSE   ESC : QUIT"
lost_text: .asciiz "GAME OVER"
won_text: .asciiz "ALL SECTORS CLEARED!"
final_text: .asciiz "FINAL SCORE"
restart_text: .asciiz "SPACE : REPLAY   J : PADDLE"
hud_text: .asciiz "SCORE         LIVES      SECTOR"
footer: .asciiz "A/D MOVE S STOP SPACE FIRE"
paddle_footer: .asciiz "PADDLE MOVE   BUTTON FIRE "
effect_strings: .word no_effect, wide_text, slow_text, catch_text
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
hp2_masks: .byte $1f,$1f,$7f
hp3_masks: .byte $4f,$73,$7c
colors: .byte $2a,$55,$aa,$d5
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
.include "levels.inc"
.include "capsules.inc"
.include "title.inc"
