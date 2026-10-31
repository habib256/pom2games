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
; Controls (input.inc): joystick X or paddle 0 = lean (analog), button 0 = throttle,
; button 1 = brake. Keyboard: A/Z or up/down = throttle level, left/right
; or J/L = lean, SPACE = brake, R = restart, ESC = menu.
; ============================================================================

.include "apple2.inc"
.include "zp.inc"
MUL_TABLES = $0800              ; HELLO area (dirtbike.cfg)
MUL_ACC    = 1
MUL_INIT_BOOT = 1               ; mul_init in INIT (dirtbike.cfg)
.include "math.inc"
.include "hgr_pages.inc"
.include "physconst.inc"
.include "sprites.inc"
.include "music.inc"
.include "pages.inc"

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
.include "sound.asm"                    ; first: its delay loop never crosses a page
.import __TXTC5_LOAD__, __TXTC5_RUN__, __TXTC7_LOAD__, __TXTC7_RUN__
.import __TXTC5_SIZE__, __TXTC7_SIZE__, __TXTC4_LOAD__, __TXTC4_RUN__, __TXTC4_SIZE__
.assert __TXTC5_SIZE__ <= 120 .and __TXTC7_SIZE__ <= 120, lderror, "TXTC: 120 bytes a run"
.include "input.inc"
.include "physics.inc"
.include "tricks.inc"
.include "render.inc"
.include "loader.inc"
.include "menu.inc"
.include "hof.inc"
.include "title.inc"
.include "mainmenu.inc"

.segment "INIT"                 ; boot only: the pool overwrites it
start:
        JSR     hgr_scanline_init       ; hgr_lo / hgr_hi
        LDX     #0                      ; routines that run in the text page
@cpy:   LDA     __TXTC5_LOAD__,X
        STA     __TXTC5_RUN__,X
        LDA     __TXTC7_LOAD__,X
        STA     __TXTC7_RUN__,X
        INX
        CPX     #120                    ; (a run: the screen holes stay)
        BNE     @cpy
        LDX     #<__TXTC4_SIZE__        ; (after TXT4's variables: its size)
@cp4:   LDA     __TXTC4_LOAD__-1,X
        STA     __TXTC4_RUN__-1,X
        DEX
        BNE     @cp4
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
        JSR     inp_boot                ; the device it names
        JMP     attract

.segment "CODE"

to_menu:
        JSR     tune_stop
        LDA     #0
        STA     demo
        JSR     stick_calib
        JSR     menu                    ; A = the chosen track, C = 1: ESC
        BCC     race_sel
        JMP     attract
race_sel:                               ; load track sel, race
        JSR     hgr_puts8_at
        .byte   2, MENU_INFO
        .addr   msg_load
        LDA     sel
        JSR     load_track
        BCC     new_race
        JSR     hgr_puts8_at
        .byte   2, MENU_INFO
        .addr   msg_derr
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

; leave_race -- after the finish: the initials if it was a record, then the
; next track (a game runs through them in order); after the last one, the
; congratulations page; ESC: the main menu (mainmenu.inc)
leave_race:
        LDA     state
        CMP     #ST_FINISH
        BCC     @menu
        LDA     inkey                   ; ESC after the finish: the menu
        PHA
        LDA     state
        CMP     #ST_RECORD
        BNE     @nr
        JSR     stick_calib
        JSR     hof_entry
@nr:    PLA
        CMP     #KC_ESC
        BEQ     @menu
        LDX     sel
        INX
        CPX     #NTRACKS
        BCC     @on
        LDA     #<jingle_rec            ; all 30: the congratulations
        LDY     #>jingle_rec
        JSR     tune_play
        LDX     #1
        JSR     show_page
        JMP     to_menu
@on:    STX     sel
        JSR     page1_text
        JMP     race_sel
@menu:  JMP     esc_menu

new_race:
        BIT     KBDSTRB                 ; no key typed during the load
        LDA     #START_X
        JSR     phys_reset
        JSR     race_view
        LDA     #0
        STA     jphase                  ; the stick on even frames of the race:
        STA     state                   ; the same ride from every start
        STA     t_hun
        STA     t_tick
        STA     t_sec
        STA     t_min
        STA     kb_throttle
        STA     gas_tm
        STA     safe_x+1                ; the restart point: the start
        STA     safe_laps
        LDA     #$80                    ; a button down now (gas) is not a
        STA     bheld                   ; press for stick_button
        LDA     #1
        STA     on_flat
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
        LDX     state                   ; a key after the finish (R and S
        CPX     #ST_FINISH              ; too): leave_race, the initials of
        BCS     @menu                   ; a record first
        CMP     #KC_ESC
        BEQ     @menu
        CMP     #'S'                    ; sound on / off
        BNE     @nos
        LDA     snd_on
        EOR     #1
        STA     snd_on
        JMP     @nokey
@nos:   CMP     #'R'
        BNE     @nokey
        JMP     new_race
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
@finp:  JSR     stick_button            ; finished: the stick's button too
        BCC     @draw
        JMP     leave_race
@run:   LDA     count_t
        BEQ     @go
        JSR     countdown               ; frozen until GO; a frame as long as
        LDA     #79                     ; a race's (~2 video frames): the
        JSR     WAIT                    ; countdown's pace (older POM2s also
        JMP     @draw                   ; flickered on faster page flips)
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

; race_view -- both pages and their HUD unknown: the next frames draw them
; whole (page 1 shown: page 2 first); race_resume -- back to the race the
; main menu stopped (its TITLE file took the track's place): the track
; again, then a countdown while racing (the hands back on the controls)
.segment "TXTC7"                ; runs in the text page (copied at boot)
race_view:
        LDA     #1
        STA     pidx
        JSR     render_reset
        LDX     #0
        JSR     hud_forget
        LDX     #1
        JMP     hud_forget
.segment "CODE"
race_resume:
        LDA     sel
        JSR     load_track
        BCS     @err
        JSR     race_view
        LDA     state
        BNE     @go
        LDA     #COUNT_STEP*3+1
        STA     count_t
@go:    JMP     main_loop
@err:   JMP     to_menu

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

; show_msg -- A/Y = message (lo/hi): shown in the HUD's middle (draw_hud).
; (A trick bank sets TR_MSG_FRAMES, this one frame less: trick_sounds tells
; them apart.)
show_msg:
        STA     ht_src_lo
        STY     ht_src_hi
        LDY     #0
@cp:    LDA     (ht_src_lo),Y
        STA     tr_msg,Y
        BEQ     @end
        INY
        BNE     @cp
@end:
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

; note_safe -- the restart point: where the bike rolls onto flat ground
; (both wheels down, one ground row under it and a wheel radius around:
; rear x - SAFE_M .. front x + SAFE_M). The start of each flat stretch, so a
; restart at rest has all of it ahead for a run-up.
SAFE_M = 6
.assert <track_h = 0, error, "note_safe: track_h must be page aligned"

note_safe:
        LDA     wheel_gnd
        AND     wheel_gnd+1
        BEQ     @off
        SEC                             ; sptr = track_h + rear x - SAFE_M
        LDA     pt_xl
        SBC     #SAFE_M
        STA     sptr
        LDA     pt_xh
        SBC     #0
        CLC
        ADC     #>track_h
        STA     sptr+1
        LDY     #0
        LDA     (sptr),Y
        LDY     #WHEELBASE + 2 * SAFE_M
@f:     CMP     (sptr),Y
        BNE     @off
        DEY
        BNE     @f
        LDA     on_flat
        BNE     @rts                    ; still the same flat
        INC     on_flat
        LDA     pt_xl
        STA     safe_x
        LDA     pt_xh
        STA     safe_x+1
        LDA     laps
        STA     safe_laps
@rts:   RTS
@off:   LDA     #0
        STA     on_flat
        RTS

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
        JSR     tune_play
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
        JMP     tune_play
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
; draw_hud -- the top row: clock left, score right, the message in the
; middle (MSG_W wide, centred: a trick, a lap, the countdown, CRASH /
; FINISH / RECORD, DEMO). Only the characters that differ from what this
; page shows (hud_sh, $FF = unknown) are drawn: a shorter message blanks
; what is left of a longer one, on both pages.
; ---------------------------------------------------------------------------
HUD_N = 6 + 6 + MSG_W           ; clock, score, message
MSG_W = 14

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
        LDX     #2                      ; score: 6 BCD digits
        LDY     #6
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
        LDA     state                   ; the message: the race's state
        BEQ     @tm                     ; first (a trick's outlasted CRASH),
        LDX     #0                      ; the timed one dropped
        STX     tr_msgt
        BEQ     @st                     ; (always)
@tm:    LDX     #<tr_msg                ; then a timed one,
        LDY     #>tr_msg
        LDA     tr_msgt
        BEQ     @dm
        DEC     tr_msgt
        BNE     @src
        BEQ     @dm                     ; (always)
@st:    LDX     #<msg_crash
        LDY     #>msg_crash
        CMP     #ST_CRASH
        BEQ     @src
        LDX     #<msg_finish
        LDY     #>msg_finish
        CMP     #ST_FINISH
        BEQ     @src
        LDX     #<msg_record
        LDY     #>msg_record
        BNE     @src
@dm:    LDX     #<msg_demo              ; DEMO, or nothing
        LDY     #>msg_demo
        LDA     demo
        BNE     @src
        LDX     #<msg_none
        LDY     #>msg_none
@src:   STX     ht_src_lo
        STY     ht_src_hi
        LDX     #MSG_W - 1              ; blank, then the text centred
        LDA     #' '
@bl:    STA     hud_new+12,X
        DEX
        BPL     @bl
        LDY     #0
@len:   LDA     (ht_src_lo),Y
        BEQ     @cen
        INY
        CPY     #MSG_W
        BNE     @len
@cen:   STY     w0                      ; X = (MSG_W - length) / 2
        SEC
        LDA     #MSG_W
        SBC     w0
        LSR     A
        TAX
        LDY     #0
@cp:    CPY     w0
        BEQ     @draw
        LDA     (ht_src_lo),Y
        STA     hud_new+12,X
        INX
        INY
        BNE     @cp
@draw:  LDA     #0
        STA     ht_sl
        LDX     pidx                    ; X = this page's hud_sh
        LDA     hud_pg,X
        TAX
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
        RTS

; hud_forget -- page X (0/1): its HUD is unknown, redraw it all
hud_forget:
        LDA     hud_pg,X
        TAX
        LDY     #HUD_N
        LDA     #$FF
@f:     STA     hud_sh,X
        INX
        DEY
        BNE     @f
        RTS

.segment "DATA"
hud_new:  .byte "0:00.0000000", "              "
msg_lapn: .byte "LAP 2", 0          ; (the digit is written in)
snd_on:   .byte 1                       ; S: sound on / off
.segment "BSS"
safe_x:     .res 2                      ; the restart point after a crash
on_flat:    .res 1                      ; the bike is on the flat of safe_x
safe_laps:  .res 1
count_t:    .res 1                      ; countdown frames (0: racing)
air_before: .res 1
.segment "DATA"
.segment "TXT4"
hud_sh:   .res 2 * HUD_N          ; per page (hud_pg + k)
.segment "RODATA"
hud_pg:   .byte 0, HUD_N
hud_cols: .byte 1, 2, 3, 4, 5, 6, 33, 34, 35, 36, 37, 38
          .byte 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26
.assert * - hud_cols = HUD_N, error, "hud_cols"

.segment "RODATA"
hun_step:   .byte $03, $03, $04
msg_crash:  .byte "CRASH !", 0
msg_none:   .byte 0
msg_finish: .byte "FINISH !", 0
msg_final:  .byte "FINAL LAP", 0
msg_go:     .byte "GO!", 0
msg_c3:     .byte "3", 0
msg_c2:     .byte "2", 0
msg_c1:     .byte "1", 0
cd_at:      .byte COUNT_STEP, COUNT_STEP*2, COUNT_STEP*3
cd_lo:      .byte <msg_c1, <msg_c2, <msg_c3
cd_hi:      .byte >msg_c1, >msg_c2, >msg_c3
msg_record: .byte "RECORD !", 0


; libraries after their callers (.ifref)
.include "hgr.asm"
.include "kbd.asm"
.include "joy.asm"                      ; read_stick_fast (joy_* in zero page)
.include "verlet_hmap.asm"               ; lib/physics (physics.inc: verlet.inc)
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
HGR_LINE_DIV7 = div7
HGR_LINE_MOD7 = mod7
.include "hgr_line.asm"
.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
HGR_TEXT8_HGR_ORDER = 1
.include "hgr_text8.asm"
TUNE_MUTE = snd_on                      ; S: notes become rests, same tempo
.include "tune.asm"                     ; title tune, jingles (title.inc)
.include "initials.asm"                 ; ini_key (hof.inc)

.segment "RODATA"
.define HGR_SCANLINE_SEGMENT "SYSBSS"    ; hgr_lo / hgr_hi at $0200 (dirtbike.cfg)
.pushseg
.segment "INIT"
.include "hgr_scanline_ram.asm"
.popseg

.segment "RODATA"
BBFONT_FIRST = $20
BBFONT_LAST  = $5F
.include "bbfont.inc"
.include "lz4fh.asm"
.segment "CODE"
.include "rwts.asm"
.include "menu_data.inc"
