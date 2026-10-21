; ============================================================================
; DIRTBIKE -- side-view motocross time trial for the Apple II+ (48 KB, HGR)
; ============================================================================
; Inspired by Brad Quick's Dirt Bike (Macintosh) and by the PHYSICS demo:
; a bike made of three Verlet points rides a height-map track. Lean to land
; your jumps, keep the rider's head off the ground, beat the clock.
;
; Menu (menu.inc): 30 tracks from very easy to very hard, loaded from the
; disk when chosen (loader.inc). Once started, the game keeps only DOS's
; disk driver: Ctrl-RESET and ESC come back to the menu, not to DOS.
;
; Frame: read_input, one physics tick (physics.inc), draw the hidden page
; (render.inc), show it. Race time counts ticks (30 per second), so it does
; not depend on how long a frame takes to draw.
;
; Controls (input.inc): joystick X = lean, up = throttle, down / button 0 =
; brake. Keyboard: A/Z or up/down = throttle level, left/right or J/L =
; lean, SPACE = brake, R = restart, ESC = menu.
; ============================================================================

.include "apple2.inc"
.include "zp.inc"
MUL_TABLES = $0800              ; HELLO area (dirtbike.cfg)
MUL_ACC    = 1
.include "math.inc"
.include "hgr_pages.inc"
.include "physconst.inc"
.include "sprites.inc"
.include "music.inc"

TRACK_LEN = 4096
NTRACKS   = 30                  ; = tools/tracks.py
START_X   = 48
GROUND    = $7F                 ; solid ground byte (white)
CRASH_FRAMES = 50
COUNT_STEP   = 20               ; frames per countdown number

ST_RUN    = 0
ST_CRASH  = 1
ST_FINISH = 2                   ; >= ST_FINISH: finished
ST_RECORD = 3                   ; finished with a new record

.segment "ZEROPAGE"
state:  .res 1
stimer: .res 1
t_tick: .res 1                  ; tick in the tenth (0-2)
t_hun:  .res 1                  ; race clock, BCD: hundredths, seconds,
t_sec:  .res 1                  ; minutes (binary, 0-9)
t_min:  .res 1
frames: .res 2                  ; frames drawn (profiling, tests)

; library zero page used before the libraries are included (at the end)
.globalzp ht_col, ht_sl, ht_left, ht_wrap, ht_font_lo, ht_font_hi
.globalzp ht_cm_ev, ht_cm_od, ht_cbit, ht_page, ht_src_lo, ht_src_hi

.segment "CODE"
        JMP     start                   ; BRUN entry: the first byte
.include "input.inc"
.include "physics.inc"
.include "tricks.inc"
.include "render.inc"
.include "loader.inc"
.include "menu.inc"
.include "hof.inc"
.include "title.inc"

.segment "CODE"
start:
        LDA     #<reset                 ; Ctrl-RESET: back to the menu
        STA     SOFTEV
        LDA     #>reset
        STA     SOFTEV+1
        EOR     #$A5
        STA     SOFTEV+2
        JSR     hgr_init
        LDA     #$20                    ; both pages black
        STA     rptr+1
        LDY     #0
        STY     rptr
        TYA
@clr:   STA     (rptr),Y
        INY
        BNE     @clr
        INC     rptr+1
        LDX     rptr+1
        CPX     #$60
        BNE     @clr
        LDA     #0
        STA     ht_page
        STA     ht_cbit
        STA     sel
        LDA     #$7F
        STA     ht_cm_ev
        STA     ht_cm_od
        LDA     #<bbfont
        STA     ht_font_lo
        LDA     #>bbfont
        STA     ht_font_hi
        LDA     #0
        STA     ht_left
        LDA     #40
        STA     ht_wrap
        JSR     mul_init
        JSR     render_init
        JSR     input_init
        JSR     hof_load                ; (first RWTS call: DOS still whole)
        JMP     attract

to_menu:
        JSR     music_stop
        LDA     #0
        STA     demo
        JSR     menu                    ; A = the chosen track, C = 1: ESC
        BCC     @race
        JMP     attract
@race:
        LDA     #<msg_load
        LDY     #>msg_load
        LDX     #2
        STX     ht_col
        LDX     #MENU_INFO
        JSR     puts_at
        LDA     sel
        JSR     load_track
        BCC     new_race
        LDA     #<msg_derr
        LDY     #>msg_derr
        LDX     #2
        STX     ht_col
        LDX     #MENU_INFO
        JSR     puts_at
        BIT     KBDSTRB
@key:   LDA     KBD
        BPL     @key
        BIT     KBDSTRB
        JMP     to_menu

reset:  LDX     #$FF                    ; Ctrl-RESET: the title
        TXS
        CLD
        JSR     hgr_init
        JMP     attract

; leave_race -- after the finish: the initials if it was a record, the menu
leave_race:
        LDA     state
        CMP     #ST_RECORD
        BNE     @menu
        JSR     hof_entry
@menu:  JMP     to_menu

new_race:
        LDA     #1                      ; page 1 shown: draw page 2 first
        STA     pidx
        LDA     #START_X
        JSR     phys_reset
        JSR     render_reset
        LDX     #0
        JSR     hud_forget
        LDX     #1
        JSR     hud_forget
        LDA     #0
        STA     jphase                  ; the stick on even frames of the race:
        STA     state                   ; the same ride from every start
        STA     t_hun
        STA     t_tick
        STA     t_sec
        STA     t_min
        STA     kb_throttle
        STA     safe_x+1                ; the restart point: the start
        STA     safe_laps
        LDA     #START_X
        STA     safe_x
        LDA     #COUNT_STEP*3+1         ; 3, 2, 1, GO!
        STA     count_t
        JSR     trick_reset

main_loop:
        LDA     demo
        BEQ     @player
        LDA     count_t                 ; a demo: the ride's inputs, from GO
        BEQ     @dstep
        LDA     KBD
        BPL     @nokey
        BIT     KBDSTRB
        JMP     to_menu
@dstep: JSR     demo_step
        BCC     @nokey
        JMP     to_menu                 ; a key: stop it
@player:
        JSR     read_input
        BCC     @nokey
        CMP     #KC_ESC
        BEQ     @menu
        CMP     #'S'                    ; sound on / off
        BNE     @nos
        LDA     snd_on
        EOR     #1
        STA     snd_on
        JMP     @nokey
@nos:   CMP     #'R'
        BNE     @nor
        JMP     new_race
@nor:
        LDX     state
        CPX     #ST_FINISH              ; a key after the finish: the menu
        BCC     @nokey
@menu:  JMP     leave_race
@nokey: LDA     state
        BEQ     @run
        CMP     #ST_CRASH
        BNE     @fin
        LDA     #0                      ; crashed: the bike tumbles, no input
        STA     in_throttle
        STA     in_brake
        STA     in_lean
        JSR     phys_tick
        JSR     follow_wrap
        JSR     clock_tick              ; the fall costs time
        DEC     stimer
        BEQ     :+
        JMP     @draw
:
        LDA     demo
        BEQ     @again
        JMP     demo_end
@again: JSR     respawn                 ; back on the wheels where it was safe
        JMP     main_loop
@fin:   LDA     #0                      ; past the line: braking to a stop
        STA     in_throttle
        STA     in_lean
        LDA     #1
        STA     in_brake
        JSR     phys_tick
        JSR     follow_wrap
        LDA     demo                    ; a demo: a pause, then the hall of fame
        BEQ     @finp
        DEC     stimer
        BNE     @draw
        JMP     demo_end
@finp:  LDA     BUTN0                   ; finished: button 0 too
        BPL     @draw
@rel:   LDA     BUTN0
        BMI     @rel
        JMP     leave_race
@run:   LDA     count_t
        BEQ     @go
        JSR     countdown               ; frozen until GO
        JMP     @draw
@go:    LDA     tr_air
        STA     air_before
        JSR     phys_tick
        JSR     follow_wrap
        JSR     trick_tick
        JSR     trick_sounds
        JSR     clock_tick
        LDA     crashed
        BEQ     @nocr
        LDA     #ST_CRASH
        STA     state
        LDA     #CRASH_FRAMES
        STA     stimer
        LDA     #40                     ; a crash: two low thuds
        LDX     #$FF
        JSR     beep
        LDA     #30
        LDX     #$E0
        JSR     beep
        JMP     @draw
@nocr:  JSR     note_safe
        LDA     laps                    ; last lap, rear wheel past the line?
        CMP     #LAPS-1
        BCC     @draw
        LDA     pt_xl
        CMP     finish_x
        LDA     pt_xh
        SBC     finish_x+1
        BCC     @draw
        JSR     finished
@draw:  JSR     camera
        JSR     render_begin            ; pidx: the hidden page
        JSR     render_ground
        JSR     draw_bike
        JSR     draw_hud
        LDA     pidx                    ; show it, draw the other next
        BEQ     @s1
        LDA     HISCR
        LDA     #0
        BEQ     @s2
@s1:    LDA     LOWSCR
        LDA     #1
@s2:    STA     pidx
        INC     frames
        BNE     @nf
        INC     frames+1
@nf:    JMP     main_loop

; ---------------------------------------------------------------------------
; follow_wrap -- the bike moved back a lap (phys_wrap): so do the camera and
; what each page shows (no repaint: the padding repeats the start); a lap
; message while racing
; ---------------------------------------------------------------------------
follow_wrap:
        LDA     wrapped
        BEQ     @rts
        LDA     #0
        STA     wrapped
        SEC
        LDA     camx
        SBC     lap_len
        STA     camx
        LDA     camx+1
        SBC     lap_len+1
        STA     camx+1
        SEC
        LDA     camc
        SBC     lap_c
        STA     camc
        LDA     camc+1
        SBC     lap_c+1
        STA     camc+1
        LDX     #2                      ; pages 1 and 2, unless unknown
@pg:    LDA     pg_camx+1,X
        CMP     #$FF
        BEQ     @nx
        SEC
        LDA     pg_camx,X
        SBC     lap_len
        STA     pg_camx,X
        LDA     pg_camx+1,X
        SBC     lap_len+1
        STA     pg_camx+1,X
@nx:    DEX
        DEX
        BPL     @pg
        LDA     state
        BNE     @rts
        LDA     #<msg_final             ; "FINAL LAP" or "LAP n"
        LDY     #>msg_final
        LDX     laps
        CPX     #LAPS-1
        BEQ     @msg
        BCS     @rts
        TXA
        CLC
        ADC     #'1'
        STA     msg_lapn+4
        LDA     #<msg_lapn
        LDY     #>msg_lapn
@msg:   JSR     show_msg
        LDA     #40                     ; two beeps
        LDX     #$50
        JSR     beep
        LDA     #40
        LDX     #$50
        JMP     beep
@rts:   RTS

; show_msg -- A/Y = message (lo/hi): shown under the HUD, 11 wide. (A trick
; bank sets TR_MSG_FRAMES, this one frame less: trick_sounds tells them apart.)
show_msg:
        STA     ht_src_lo
        STY     ht_src_hi
        LDY     #0
@cp:    LDA     (ht_src_lo),Y
        BEQ     @pad
        STA     tr_msg,Y
        INY
        BNE     @cp
@pad:   LDA     #' '
        STA     tr_msg,Y
        INY
        CPY     #11
        BCC     @pad
        LDA     #0
        STA     tr_msg,Y
        LDA     #TR_MSG_FRAMES-1
        STA     tr_msgt
        RTS

; countdown -- before GO (and after a restart): 3, 2, 1 with beeps, GO!
countdown:
        LDA     t_min                   ; a restart: the clock runs on
        ORA     t_sec
        ORA     t_hun
        BEQ     @c
        JSR     clock_tick
@c:     DEC     count_t
        LDA     count_t
        BEQ     @go
        LDX     #2
@f:     CMP     cd_at,X
        BEQ     @show
        DEX
        BPL     @f
        RTS
@show:  LDA     cd_lo,X
        LDY     cd_hi,X
        JSR     show_msg
        LDA     #24
        LDX     #$A0
        JMP     beep
@go:    LDA     #<msg_go
        LDY     #>msg_go
        JSR     show_msg
        LDA     #60
        LDX     #$50
        JMP     beep

; note_safe -- both wheels down and the bike level: the restart point
note_safe:
        LDA     wheel_gnd
        AND     wheel_gnd+1
        BEQ     @rts
        SEC
        LDA     pt_yh+1
        SBC     pt_yh
        BPL     @abs
        EOR     #$FF
        CLC
        ADC     #1
@abs:   CMP     #3
        BCS     @rts
        LDA     pt_xl
        STA     safe_x
        LDA     pt_xh
        STA     safe_x+1
        LDA     laps
        STA     safe_laps
@rts:   RTS

; respawn -- after a crash: at rest at the restart point, a short count
respawn:
        LDA     safe_x
        STA     hxl
        LDA     safe_x+1
        STA     hxh
        JSR     phys_place
        LDA     safe_laps
        STA     laps
        LDA     #0
        STA     wrapped
        STA     state
        STA     pend
        STA     pend+1
        STA     tr_flips
        STA     tr_air
        STA     tr_rot
        STA     tr_sec
        STA     tr_safe
        JSR     render_reset            ; repaint, the camera finds the bike
        LDX     #0
        JSR     hud_forget
        LDX     #1
        JSR     hud_forget
        LDA     #COUNT_STEP+1           ; "1", GO!
        STA     count_t
        RTS

; trick_sounds -- a thud on landing a jump, a blip / an arpeggio on a bank
trick_sounds:
        LDA     crashed
        BNE     @rts
        LDA     air_before
        CMP     #AIR_MIN
        BCC     @bank
        LDA     tr_air
        BNE     @bank
        LDA     #10
        LDX     #$FF
        JSR     beep
@bank:  LDA     tr_msgt
        CMP     #TR_MSG_FRAMES
        BNE     @rts
        LDA     tr_msg
        CMP     #'F'
        BEQ     @flip
        LDA     #40
        LDX     #$40
        JMP     beep
@flip:  LDA     #30
        LDX     #$60
        JSR     beep
        LDA     #36
        LDX     #$48
        JSR     beep
        LDA     #60
        LDX     #$30
        JMP     beep
@rts:   RTS

; beep -- tone (A flips, X half period) unless muted or in a demo
beep:   LDY     snd_on
        BEQ     @no
        LDY     demo
        BNE     @no
        JMP     tone
@no:    RTS

; ---------------------------------------------------------------------------
; finished -- the finish line: keep the time if it beats the record
; ---------------------------------------------------------------------------
finished:
        JSR     trick_bank              ; the last jump counts
        LDA     #ST_FINISH
        STA     state
        LDA     demo
        BEQ     @player
        LDA     #DEMO_END_FRAMES
        STA     stimer
        RTS
@player:
        LDA     #<jingle
        LDY     #>jingle
        JSR     play_tune
        LDA     #0
        STA     hof_new
        JSR     @points
        LDX     sel
        LDA     t_min                   ; time < record ? (min, sec, hun)
        CMP     rec_min,X
        BCC     @new
        BNE     @old
        LDA     t_sec
        CMP     rec_sec,X
        BCC     @new
        BNE     @old
        LDA     t_hun
        CMP     rec_hun,X
        BCS     @old
@new:   LDA     t_min
        STA     rec_min,X
        LDA     t_sec
        STA     rec_sec,X
        LDA     t_hun
        STA     rec_hun,X
        LDA     hof_new
        ORA     #1
        STA     hof_new
@old:   LDA     hof_new
        BEQ     @rts
        LDA     #ST_RECORD
        STA     state
        LDA     #<jingle_rec            ; a record: the tail
        LDY     #>jingle_rec
        JMP     play_tune
@rts:   RTS
@points:                                ; score > best points ? (BCD, high first)
        LDA     sel
        STA     msel
        ASL     A
        ADC     msel
        TAY
        LDA     score+2
        CMP     rec_pts+2,Y
        BCC     @prts
        BNE     @pnew
        LDA     score+1
        CMP     rec_pts+1,Y
        BCC     @prts
        BNE     @pnew
        LDA     score
        CMP     rec_pts,Y
        BCC     @prts
        BEQ     @prts
@pnew:  LDA     score
        STA     rec_pts,Y
        LDA     score+1
        STA     rec_pts+1,Y
        LDA     score+2
        STA     rec_pts+2,Y
        LDA     #2
        STA     hof_new
@prts:  RTS

; ---------------------------------------------------------------------------
; clock_tick -- 30 ticks per second: 3, 3 then 4 hundredths
; ---------------------------------------------------------------------------
clock_tick:
        LDX     t_tick
        INX
        CPX     #3
        BCC     @t
        LDX     #0
@t:     STX     t_tick
        SED
        CLC
        LDA     t_hun
        ADC     hun_step,X
        STA     t_hun
        LDA     t_sec
        ADC     #0
        CLD
        CMP     #$60
        BCC     @sec
        LDA     t_min
        CMP     #9
        BCS     @done                   ; 9:59.9 is the slowest time shown
        INC     t_min
        LDA     #0
@sec:   STA     t_sec
@done:  RTS

; ---------------------------------------------------------------------------
; draw_hud -- clock top left, throttle top right; only the characters that
; differ from what this page shows (hud_sh, $FF = unknown) are drawn.
; CRASH / FINISH in the middle.
; ---------------------------------------------------------------------------
HUD_N = 16                      ; clock, throttle, score, lap (<= 16)

draw_hud:
        LDA     t_min
        ORA     #'0'
        STA     hud_new
        LDA     t_sec
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        ORA     #'0'
        STA     hud_new+2
        LDA     t_sec
        AND     #$0F
        ORA     #'0'
        STA     hud_new+3
        LDA     t_hun
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        ORA     #'0'
        STA     hud_new+5
        LDA     in_throttle
        ORA     #'0'
        STA     hud_new+7
        LDX     #2                      ; score: 6 BCD digits
        LDY     #8
@sc:    LDA     score,X
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        ORA     #'0'
        STA     hud_new,Y
        INY
        LDA     score,X
        AND     #$0F
        ORA     #'0'
        STA     hud_new,Y
        INY
        DEX
        BPL     @sc
        LDX     laps                    ; lap 1..LAPS
        CPX     #LAPS
        BCC     @lap
        LDX     #LAPS-1
@lap:   TXA
        CLC
        ADC     #'1'
        STA     hud_new+15
        LDA     #0
        STA     ht_sl
        LDA     pidx
        ASL     A
        ASL     A
        ASL     A
        ASL     A
        TAX                             ; X = pidx * 16 + k
        LDY     #0
@k:     LDA     hud_new,Y
        CMP     hud_sh,X
        BEQ     @same
        STA     hud_sh,X
        PHA
        LDA     hud_cols,Y
        STA     ht_col
        PLA
        JSR     hgr_putc8               ; keeps A, X, Y
@same:  INX
        INY
        CPY     #HUD_N
        BNE     @k
        LDA     demo                    ; (sky rows: only the bike can spoil
        BEQ     @nodemo                 ;  them, so 2 frames in 8 are enough)
        LDA     frames
        AND     #6
        BNE     @nodemo
        LDA     #<msg_demo
        LDY     #>msg_demo
        LDX     #18
        STX     ht_col
        LDX     #16
        JSR     puts_at
@nodemo:
        LDA     state
        BNE     @state
        LDA     tr_msgt                 ; a message: on both pages at first,
        BEQ     @done                   ; then 2 frames in 8; erased on both
        DEC     tr_msgt                 ; pages in the last two frames
        CMP     #3
        BCC     @put
        CMP     #TR_MSG_FRAMES-2
        BCS     @put
        LDA     frames
        AND     #6
        BEQ     @put
        RTS
@put:   LDA     tr_msgt
        CMP     #2
        LDX     #<tr_msg
        LDY     #>tr_msg
        BCS     @msg2
        LDX     #<msg_blank12
        LDY     #>msg_blank12
@msg2:  STX     ht_src_lo
        STY     ht_src_hi
        LDA     #14
        STA     ht_col
        LDA     #32
        STA     ht_sl
        JMP     hgr_puts8
@state: LDX     #<msg_crash
        LDY     #>msg_crash
        CMP     #ST_CRASH
        BEQ     @msg
        LDX     #<msg_finish
        LDY     #>msg_finish
        CMP     #ST_FINISH
        BEQ     @msg
        LDX     #<msg_record
        LDY     #>msg_record
@msg:   STX     ht_src_lo
        STY     ht_src_hi
        LDA     #15
        STA     ht_col
        LDA     #32
        STA     ht_sl
        JSR     hgr_puts8
@done:  RTS

; hud_forget -- page X (0/1): its HUD is unknown, redraw it all
hud_forget:
        TXA
        ASL     A
        ASL     A
        ASL     A
        ASL     A
        TAX
        LDY     #HUD_N
        LDA     #$FF
@f:     STA     hud_sh,X
        INX
        DEY
        BNE     @f
        RTS

.segment "DATA"
hud_new:  .byte "0:00.0T0000000L1"
msg_lapn: .byte "LAP 2", 0          ; (the digit is written in)
snd_on:   .byte 1                       ; S: sound on / off
.segment "BSS"
safe_x:     .res 2                      ; the restart point after a crash
safe_laps:  .res 1
count_t:    .res 1                      ; countdown frames (0: racing)
air_before: .res 1
.segment "DATA"
.segment "BSS"
hud_sh:   .res 32                 ; per page: 16 (pidx * 16 + k)
.segment "RODATA"
hud_cols: .byte 1, 2, 3, 4, 5, 6, 34, 35, 17, 18, 19, 20, 21, 22, 27, 28

.segment "RODATA"
hun_step:   .byte $03, $03, $04
msg_crash:  .byte " CRASH ! ", 0
msg_blank12: .byte "            ", 0
msg_finish: .byte " FINISH !", 0
msg_final:  .byte "FINAL LAP", 0
msg_go:     .byte "    GO!", 0
msg_c3:     .byte "     3", 0
msg_c2:     .byte "     2", 0
msg_c1:     .byte "     1", 0
cd_at:      .byte COUNT_STEP, COUNT_STEP*2, COUNT_STEP*3
cd_lo:      .byte <msg_c1, <msg_c2, <msg_c3
cd_hi:      .byte >msg_c1, >msg_c2, >msg_c3
msg_record: .byte " RECORD !", 0


; libraries after their callers (.ifref)
.include "hgr.asm"
.include "kbd.asm"
.include "sound.asm"
.include "joy.asm"                      ; read_stick_fast (joy_* in zero page)
.include "mul.asm"
HGR_LINE_DIV7 = div7
HGR_LINE_MOD7 = mod7
.include "hgr_line.asm"
.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
HGR_TEXT8_HGR_ORDER = 1
.include "hgr_text8.asm"

.segment "RODATA"
.include "hgr_scanline.inc"

.segment "RODATA"
BBFONT_FIRST = $20
BBFONT_LAST  = $5F
.include "bbfont.inc"
.include "lz4fh.asm"
.segment "CODE"
.include "rwts.asm"
.include "menu_data.inc"
