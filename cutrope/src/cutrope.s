; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; cutrope.s -- CUTROPE: cut the ropes, swing the candy into the frog
; ============================================================================
; A "Cut the Rope"-like for the Apple II+ 48 KB (DOS 3.3, HGR, assembly,
; dev/lib only). The physics and the rules are tools/cutrope.py transcribed
; in phys.inc (tests/test_cutrope.py: bit for bit); this file is the game
; around it: input, events and sounds, drawing, the text lines, the pace.
;
; Screen: rows 0-7 the counters (level, stars, total), 8-15 the message,
; 16-190 the field (the world is the screen). The platforms, the spikes,
; the cushions and the frog are drawn once on both pages at a level's start;
; the stars, the free bubble, the puffs, the ropes, the candy (in its
; bubble) and the cursor are drawn with hgr_plot_hist.asm, which records the
; bits each one lit, in a stack per page: the stars and the free bubble at
; the bottom (drawn again only when one changes), the puffs, the ropes, the
; candy, the cursor on top. Each tick draws the hidden page -- what it
; showed above the stars given back (EOR), the rest drawn again -- and shows
; it in the vertical blank (vapor.asm: the beam found through the floating
; bus, a marker on row 191 of both pages; nothing is drawn below row 190),
; a tick every TICK_FRAMES video frames (30 a second: vapor_pace, given an
; estimate of the tick's cycles); without a floating bus (//c, IIgs) it
; runs unpaced. Once the candy is in the frog or lost, both pages hold the
; last picture after two ticks: only the cursor is drawn again, and the
; jingle plays (tune.asm, a tick of it a game tick).
; The levels are on the disk (LEVELS: one a sector, read through RWTS when
; one is chosen, disk.inc); the menu (menu.inc) shows them with the stars
; won, kept in CUTSAVE (written when a better result is left).
; Keys: 1-3 cut rope 1-3, 4-5 puff cushion 1-2, 6 pops the bubble; I J K L
; (or the arrows) move the cursor, space holds the "button" a moment: a
; rope the cursor touches meanwhile is cut, a cushion under it puffs, the
; candy's bubble under it pops; R restarts the level, N goes to the next one
; after a win, ESC back to the menu. A joystick (found at start): both axes
; move the cursor, button 0 is the button.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
PL_HIST    = $1800                      ; hgr_plot_hist.asm's histories: 1.5 KB
HGR_PLOT_HIST_FAST = 1                  ; lines stepped by byte, pl_sprite
PL_SPRITE_YMIN = 16                     ; the field's first row
MUL_ACC    = 1
mul_y = mul_s1l                 ; operand is also the first table pointer low byte
.include "math.inc"
.include "cutconst.inc"
.include "physdefs.inc"
.include "hgr_pages.inc"
.import _mouse_init, _mouse_poll, _mouse_close             ; dev/lib/mouse (mouse.o)
.import _mouse_slot, _mouse_x, _mouse_y, _mouse_buttons
.exportzp ptr1
ptr1 = lvp                              ; (the driver's, at init only)
RWTS_SEI = 1                            ; the //c mouse runs with IRQs on
APPLE2_EXIT_HOOK = _mouse_close
HGR_LINE_DIV7 = hgr_div7                ; (hgr_div7_ram.asm)
HGR_LINE_MOD7 = hgr_mod7
HGR_TEXT8_HGR_ORDER = 1

MSG_PLAY  = 0
MSG_WON   = 1
MSG_LOST  = 2
VIEW_LAST = 190                         ; the last row drawn (191: the vapor marker)
CUR_SPEED = 3                           ; px a tick by a key (the stick: up to 3 too):
                                        ; under 2 CUT_R + 1, a sweep steps over no link
MV_HOLD   = 6                           ; ticks a key moves the cursor (no key-up on a II+)
BTN_HOLD  = 8                           ; ticks space holds the button
CUR_X0    = 3                           ; the cursor's centre: columns,
CUR_X1    = 252
CUR_Y0    = 19                          ; rows (its 7 x 7 cross in 16..190)
CUR_Y1    = 187
JOY_DEAD  = 8                           ; read_stick_fast counts: |d| < 8 still,
                                        ; then |d| / 8 px a tick, up to 3
KNIFE_MAX = 6                           ; the mouse with its button held: the cursor
                                        ; follows it CUR_SPEED px a step, up to
                                        ; KNIFE_MAX steps a tick, each step's point
                                        ; tested by the knife (near: no rope jumped)
TUNE_DELAY = 5                          ; ticks after the end before the jingle
TK_PHYS   = $01                         ; tkf: the physics ran (PLAY at its start),
TK_CUT    = $02                         ; a snip, a star's blip, the jingle's tick,
TK_STAR   = $04                         ; the frozen render (the cursor only),
TK_TUNE   = $08                         ; the stars drawn again, the message
TK_IDLE   = $10
TK_STARS  = $20
TK_MSG    = $40
TK_BUB    = $80                         ; the candy's bubble drawn

.segment "ZEROPAGE"
pidx:   .res 1                          ; page drawn this frame: 0 = 1, 1 = 2
t0:     .res 1
t1:     .res 1
t2:     .res 1
gk:     .res 1
tune_ptr: .res 2                        ; (tune.asm's, in zero page)

.segment "BSS"
frames:   .res 2                        ; ticks shown (tests)
level:    .res 1                        ; 0..NLEVEL-1 (BENCH_LEVEL: the tests')
total:    .res 1                        ; the stars won in all (disk.inc)
msg:      .res 1
msg_pg:   .res 2                        ; message shown on each page
hud_pg:   .res 6                        ; per page: level, stars, total shown
dirty:    .res 1                        ; bit p: page p draws its stars again
smark:    .res 2                        ; per page: the history under the ropes
dmark:    .res 2                        ; per page: ... under the cursor
frozen:   .res 1                        ; renders since the end (to 3)
tune_wt:  .res 1                        ; ticks before the jingle (0: none)
tune_lo:  .res 1
tune_hi:  .res 1
cur_x:    .res 1                        ; the cursor
cur_y:    .res 1
cur_vx:   .res 1                        ; a key's move (signed)
cur_vy:   .res 1
cur_hold: .res 1
btn_hold: .res 1
joy_ok:   .res 1
joy_rx:   .res 1                        ; the stick's rest position
joy_ry:   .res 1
pace_ok:  .res 1                        ; a floating bus: vapor_pace
ms_x:     .res 1                        ; the mouse: its last position,
ms_y:     .res 1
ms_tx:    .res 1                        ; the cursor's target (clamped),
ms_ty:    .res 1
chase:    .res 1                        ; the cursor goes there (not yet),
kn:       .res 1                        ; steps left this tick,
nknife:   .res 1                        ; knife tests this tick (pace)
nlink:    .res 1                        ; links drawn this tick (pace)
tkf:      .res 1                        ; what this tick did (TK_*: pace)
tkd:      .res 1                        ; digits it printed (pace)

.segment "CODE"
        JMP     start
.include "sound.asm"                    ; first: its loops never cross a page
.include "hgr_text8.asm"                ; (its zero page before the callers)
.include "hgr_line.asm"
.include "hgr_plot_hist.asm"            ; lib/hgr: its zero page (routines at the end)
.include "phys.inc"
.include "disk.inc"
.include "menu.inc"

start:  APPLE2_PREAMBLE
        JSR     apple2_zp_save
        JSR     mul_init
        JSR     hgr_div7_init
        JSR     hgr_pages_init
        LDA     #0
        STA     ht_page
        STA     ht_cbit
        STA     ht_left
        STA     pidx
        STA     joy_ok
        STA     pace_ok
        LDA     #$7F                    ; white text
        STA     ht_cm_ev
        STA     ht_cm_od
        LDA     #<bbfont
        STA     ht_font_lo
        LDA     #>bbfont
        STA     ht_font_hi
        LDA     #40
        STA     ht_wrap
        LDA     #128
        STA     cur_x
        LDA     #100
        STA     cur_y
        JSR     tune_stop
        JSR     read_stick_fast         ; a joystick: both timers run out
        BCS     :+
        LDA     joy_x
        STA     joy_rx
        LDA     joy_y
        STA     joy_ry
        INC     joy_ok
:       JSR     _mouse_init             ; an AppleMouse (before HGR: its init
        JSR     _mouse_poll             ; selects TEXT): where it is
        LDA     _mouse_x
        STA     ms_x
        LDA     _mouse_y
        STA     ms_y
        LDA     #0
        STA     chase
        JSR     clear_pages             ; (and the vapor marker)
        JSR     hgr_init
        JSR     vapor_pace_init         ; a floating bus?
        BCS     :+
        INC     pace_ok
:       JSR     save_load               ; the stars won (DOS still whole)
        LDA     #$FF                    ; (the menu: the first level not won)
        STA     level

to_menu:
        JSR     menu                    ; A = the level chosen
        STA     level
restart:
        JSR     level_load              ; (from the disk when it changed)
        JSR     phys_load
        LDA     #0
        STA     in_cut
        STA     in_btn
        STA     cur_hold
        STA     btn_hold
        STA     frozen
        STA     tune_wt
        STA     nlink
        STA     pl_n
        STA     pl_n+1
        LDA     #MSG_PLAY
        STA     msg
        JSR     tune_stop
        JSR     clear_pages
        LDA     #1
        STA     t0
:       LDA     t0                      ; both pages: scenery, frog, labels
        JSR     set_page
        JSR     scenery
        PUTS8_AT m_label, 0, 0
        LDX     t0
        STX     pidx
        LDA     #$FF
        STA     msg_pg,X
        LDA     #0
        STA     pl_n,X                  ; (the frog stays: no history)
        TXA
        ASL     A
        ADC     t0                      ; (C = 0)
        TAX
        LDA     #$FF
        STA     hud_pg,X
        STA     hud_pg+1,X
        STA     hud_pg+2,X
        JSR     draw_text               ; (here: not in a tick's time)
        DEC     t0
        BPL     :-
        LDA     #3                      ; both pages draw their stars first
        STA     dirty
        BIT     LOWSCR                  ; (the menu showed page 1)
        LDA     #0
        STA     pidx

main:   LDA     #0
        STA     tkf
        STA     tkd
        STA     nknife
        JSR     input                   ; (R, N: back to restart, ESC: quit)
        LDA     cr_state
        BNE     :+
        LDA     #TK_PHYS
        STA     tkf
:       JSR     phys_tick
        LDA     #0
        STA     in_cut
        JSR     events
        LDA     pidx                    ; draw the hidden page, show it
        EOR     #1
        STA     pidx
        JSR     render
        JSR     pace                    ; the tick's last video frame
flip:   LDA     pidx
        BNE     :+
        BIT     LOWSCR
        JMP     :++
:       BIT     HISCR
:       INC     frames
        BNE     :+
        INC     frames+1
:       JMP     main

quit:   JMP     apple2_exit

; ---------------------------------------------------------------------------
; input -- keys and joystick -> in_cut, the cursor (in_cx, in_cy), in_btn
; ---------------------------------------------------------------------------
input:  JSR     poll_key
        BNE     :+
        JMP     @move
:       CMP     #'1'
        BCC     :+
        CMP     #'1' + 6                ; 1-3 ropes, 4-5 cushions, 6 the bubble
        BCS     :+
        SBC     #'1' - 1                ; (C = 0)
        TAX
        LDA     bit_tab,X
        ORA     in_cut
        STA     in_cut
        JMP     @move
:       LDX     #0
        LDY     #<-CUR_SPEED
        CMP     #'J'
        BEQ     @key
        CMP     #KC_LEFT
        BEQ     @key
        LDY     #CUR_SPEED
        CMP     #'L'
        BEQ     @key
        CMP     #KC_RIGHT
        BEQ     @key
        LDX     #<-CUR_SPEED
        LDY     #0
        CMP     #'I'
        BEQ     @key
        CMP     #KC_UP
        BEQ     @key
        LDX     #CUR_SPEED
        CMP     #'K'
        BEQ     @key
        CMP     #KC_DOWN
        BEQ     @key
        CMP     #' '
        BEQ     @btn
        CMP     #'R'
        BEQ     @again
        CMP     #'N'
        BEQ     @next
        CMP     #KC_ESC
        BNE     @move
        PLA                             ; (called from main)
        PLA
        JSR     save_due                ; a better result: on the disk
        JMP     to_menu
@key:   STY     cur_vx
        STX     cur_vy
        LDA     #0
        STA     chase
        LDA     #MV_HOLD
        STA     cur_hold
        BNE     @move
@btn:   LDA     #BTN_HOLD
        STA     btn_hold
        BNE     @move
@next:  LDA     cr_state
        CMP     #WON
        BNE     @move
        PLA                             ; (called from main)
        PLA
        JSR     save_due
        LDX     level
        INX
        CPX     #NLEVEL
        BCC     :+
        JMP     to_menu                 ; (after the last one)
:       STX     level
        JMP     restart
@again: PLA
        PLA
        JSR     save_due
        JMP     restart
@move:  LDA     cur_hold                ; a key's move
        BEQ     @joy
        DEC     cur_hold
        LDA     cur_vx
        LDY     cur_vy
        JSR     move
@joy:   LDA     joy_ok
        BEQ     @out
        JSR     read_stick_fast
        LDA     joy_x
        LDY     joy_rx
        JSR     stick_v
        PHA
        LDA     joy_y
        LDY     joy_ry
        JSR     stick_v
        TAY
        PLA
        STA     t0
        TYA
        ORA     t0
        BEQ     @mouse
        LDA     #0                      ; (a push: the stick has the cursor)
        STA     chase
        LDA     t0
        JSR     move
@mouse: LDA     _mouse_slot
        BEQ     @out
        JSR     mouse_in
@out:   LDA     #0                      ; the button: space a moment, button 0,
                                        ; the mouse's
        LDX     btn_hold
        BEQ     :+
        DEC     btn_hold
        LDA     #1
:       LDX     joy_ok
        BEQ     :+
        BIT     BUTN0
        BPL     :+
        LDA     #1
:       LDX     _mouse_slot
        BEQ     :+
        BIT     _mouse_buttons
        BPL     :+
        LDA     #1
:       STA     in_btn
        LDA     cur_x
        STA     in_cx
        LDA     cur_y
        STA     in_cy
        RTS

; the mouse: when it moved, the cursor goes where it is (clamped to its box):
; at once, or with the button held CUR_SPEED px a step on each axis, up to
; KNIFE_MAX steps a tick, the knife tried on each step's point but the last
; (phys_tick tries that one): a rope near it is cut (in_cut), as by its key
mouse_in:
        JSR     _mouse_poll
        LDA     _mouse_x
        CMP     ms_x
        BNE     :+
        LDA     _mouse_y
        CMP     ms_y
        BEQ     @go
:       LDA     _mouse_x
        STA     ms_x
        CMP     #CUR_X0
        BCS     :+
        LDA     #CUR_X0
:       STA     ms_tx
        LDA     _mouse_y
        STA     ms_y
        STA     ms_ty                   ; (the driver clamps y to CUR_Y0..CUR_Y1)
        LDA     #1
        STA     chase
@go:    LDA     chase
        BEQ     @rts
        BIT     _mouse_buttons
        BMI     @knife
        LDA     ms_tx                   ; no knife: at once
        STA     cur_x
        LDA     ms_ty
        STA     cur_y
        JMP     @done
@knife: LDA     #KNIFE_MAX
        STA     kn
@step:  LDA     cur_x
        LDY     ms_tx
        JSR     toward
        STA     cur_x
        LDA     cur_y
        LDY     ms_ty
        JSR     toward
        STA     cur_y
        CMP     ms_ty
        BNE     :+
        LDA     cur_x
        CMP     ms_tx
        BEQ     @done
:       DEC     kn
        BEQ     @rts                    ; (the rest next tick)
        JSR     knife
        JMP     @step
@done:  LDA     #0
        STA     chase
@rts:   RTS

; A = a coordinate, Y = its target: A moved towards it by CUR_SPEED at most
toward: STY     t2
        CMP     t2
        BEQ     @rts
        BCS     @dn
        ADC     #CUR_SPEED              ; (C = 0)
        BCS     @t
        CMP     t2
        BCC     @rts
@t:     LDA     t2
@rts:   RTS
@dn:    SBC     #CUR_SPEED              ; (C = 1)
        BCC     @t
        CMP     t2
        BCC     @t
        RTS

; the knife at the cursor (in play): each rope on that near() finds -> in_cut
knife:  LDA     cr_state
        BNE     @rts
        INC     nknife
        LDA     cur_x
        STA     in_cx
        LDA     cur_y
        STA     in_cy
        LDX     #0
@r:     CPX     cr_nrope
        BCS     @rts
        LDA     bit_tab,X
        AND     cr_on
        BEQ     @n
        AND     in_cut
        BNE     @n
        STX     cr_r
        JSR     near
        LDX     cr_r
        BCC     @n
        LDA     bit_tab,X
        ORA     in_cut
        STA     in_cut
@n:     INX
        BNE     @r
@rts:   RTS

; A = vx, Y = vy (signed, |v| <= 6): the cursor moves, kept in its box
move:   STY     t1
        LDX     #CUR_X0
        STX     t0
        LDX     #CUR_X1
        STX     t2
        LDX     cur_x
        JSR     addc
        STA     cur_x
        LDA     #CUR_Y0
        STA     t0
        LDA     #CUR_Y1
        STA     t2
        LDA     t1
        LDX     cur_y
        JSR     addc
        STA     cur_y
        RTS

; A = v (signed), X = pos: A = pos + v clamped to t0..t2 (no wrap)
addc:   STX     gk
        CMP     #$80
        BCS     @neg
        ADC     gk                      ; (C = 0)
        BCS     @hi
        CMP     t2
        BCC     @ok
        BEQ     @ok
@hi:    LDA     t2
@ok:    RTS
@neg:   CLC
        ADC     gk                      ; C = 0: below 0
        BCC     @lo
        CMP     t0
        BCS     @ok
@lo:    LDA     t0
        RTS

; A = a stick count, Y = its rest: the cursor's speed on that axis
; (|d| < JOY_DEAD: 0, else |d| / 8 up to 3, d's sign)
stick_v:
        STY     t2
        SEC
        SBC     t2
        BMI     @neg
        CMP     #JOY_DEAD
        BCC     @zero
        LSR     A
        LSR     A
        LSR     A
        CMP     #4
        BCC     :+
        LDA     #3
:       RTS
@neg:   EOR     #$FF
        ADC     #1                      ; (C = 0)
        CMP     #JOY_DEAD
        BCC     @zero
        LSR     A
        LSR     A
        LSR     A
        CMP     #4
        BCC     :+
        LDA     #3
:       EOR     #$FF
        ADC     #0                      ; (C = 1: -A)
        RTS
@zero:  LDA     #0
        RTS

; ---------------------------------------------------------------------------
; events -- the sounds of a cut and a star, the message and the jingle at
; the end (TUNE_DELAY ticks after it: both pages hold the last picture
; first), a candy fewer when it is lost
; ---------------------------------------------------------------------------
events: LDA     cr_ev                   ; one sound a tick (the pace counts
        AND     #EV_STAR                ; one): a star's blip, the bubble
        BEQ     :+                      ; catching, its pop, a snip, a puff
        LDA     #12                     ; a blip: ~1,600 cycles
        LDX     #$18
        BNE     @blip
:       LDA     cr_ev
        AND     #EV_CATCH
        BEQ     :+
        LDA     #10
        LDX     #$20
@blip:  JSR     tone
        LDA     #TK_STAR
        BNE     @snd
:       LDA     cr_ev
        AND     #EV_POP
        BEQ     :+
        LDA     #3                      ; ~1,000 cycles, low
        LDX     #$40
        BNE     @snip
:       LDA     cr_ev
        AND     #EV_CUT
        BEQ     :+
        LDA     #4                      ; a snip: ~1,000 cycles
        LDX     #$30
        BNE     @snip
:       LDA     cr_ev
        AND     #EV_BOING
        BEQ     :+
        LDA     #3                      ; a trampoline: ~1,000 cycles, low
        LDX     #$50
        BNE     @snip
:       LDA     cr_ev
        AND     #EV_PUFF
        BEQ     @dirty
        LDA     #8                      ; a puff: ~1,050 cycles, high
        LDX     #$18
@snip:  JSR     tone
        LDA     #TK_CUT
@snd:   ORA     tkf
        STA     tkf
@dirty: LDA     cr_ev                   ; a star taken, the bubble caught or
        AND     #EV_STAR | EV_CATCH | EV_POP    ; popped: both pages draw the
        BEQ     :+                      ; stars and the free bubble again
        LDA     #3
        STA     dirty
:       LDA     cr_ev
        AND     #EV_WON
        BEQ     :+
        JSR     won                     ; (disk.inc: the best result kept)
        LDA     #MSG_WON
        STA     msg
        LDA     #<tune_won
        LDX     #>tune_won
        BNE     @tune
:       LDA     cr_ev
        AND     #EV_LOST
        BEQ     @play
        LDA     #MSG_LOST
        STA     msg
        LDA     #<tune_lost
        LDX     #>tune_lost
@tune:  STA     tune_lo
        STX     tune_hi
        LDA     #TUNE_DELAY
        STA     tune_wt
        RTS
@play:  LDA     tune_wt                 ; the jingle, once
        BEQ     @tick
        DEC     tune_wt
        BNE     @rts
        LDA     tune_lo
        LDY     tune_hi
        JSR     tune_start
        LDA     #0
        STA     tune_loop+1
@tick:  LDA     tune_ptr+1
        BEQ     @rts
        LDA     #TK_TUNE
        ORA     tkf
        STA     tkf
        JMP     tune_tick               ; ~17,000 cycles: a tone of 1/60 s
@rts:   RTS

; ---------------------------------------------------------------------------
; pace -- wait for line 191 of the tick's last video frame: vapor_pace with
; TICK_FRAMES and the tick's estimate, a sum of what it did: EST_BASE,
; EST_LINK a link (or a puff) drawn (its share of the physics too),
; EST_DIGIT a digit printed, a term per tkf flag (est_lo / est_hi: the
; physics, a snip, a blip, the jingle's tick, the frozen render, the stars,
; the message, the candy's bubble), a
; least-squares fit on the levels' ticks in a2run; unpaced without a
; floating bus
; ---------------------------------------------------------------------------
pace:   LDA     pace_ok
        BEQ     @rts
        LDA     #<(EST_BASE / 13)
        STA     t0
        LDA     #>(EST_BASE / 13)
        STA     t1
        LDX     nlink
        BEQ     @dg
@l:     CLC
        LDA     t0
        ADC     #<(EST_LINK / 13)
        STA     t0
        BCC     :+
        INC     t1
:       DEX
        BNE     @l
@dg:    LDA     nknife                  ; (+ the knife's tests, the mouse's:
        BEQ     @dg2                    ; each EST_KNIFE + EST_KNIFE_LINK a link)
@k:     CLC
        LDA     t0
        ADC     #<(EST_KNIFE / 13)
        STA     t0
        BCC     :+
        INC     t1
:       LDX     nlink
        BEQ     @kn
:       CLC
        LDA     t0
        ADC     #<(EST_KNIFE_LINK / 13)
        STA     t0
        BCC     :+
        INC     t1
:       DEX
        BNE     :--
@kn:    DEC     nknife
        BNE     @k
@dg2:   LDX     tkd
        BEQ     @fl
@d:     CLC
        LDA     t0
        ADC     #<(EST_DIGIT / 13)
        STA     t0
        BCC     :+
        INC     t1
:       DEX
        BNE     @d
@fl:    LDA     tkf
        LDX     #0
@f:     LSR     A
        BCC     :+
        PHA
        CLC
        LDA     t0
        ADC     est_lo,X
        STA     t0
        LDA     t1
        ADC     est_hi,X
        STA     t1
        PLA
:       INX
        CPX     #8
        BNE     @f
        LDX     t0
        LDY     t1
        LDA     #TICK_FRAMES
        JMP     vapor_pace
@rts:   RTS

; a tick's cycles (main to pace), fitted (tests/test_cutrope_disk.py --fit)
EST_BASE  = 5100
EST_LINK  = 2900
EST_DIGIT = 150
EST_PHYS  = 2200                        ; TK_PHYS .. TK_MSG
EST_CUT   = 2150
EST_STAR  = 1700
EST_TUNE  = 16750
EST_IDLE  = 0
EST_STARS = 2150
EST_MSG   = 21050
EST_BUB   = 3150
EST_KNIFE = 150                         ; a knife test (near over the ropes on),
EST_KNIFE_LINK = 210                    ; + a link (measured: 4 links 930, 8 1,850)
.assert EST_LINK / 13 < 256 .and EST_DIGIT / 13 < 256 .and EST_KNIFE / 13 < 256 .and EST_KNIFE_LINK / 13 < 256, error, "pace: EST_LINK, EST_DIGIT < 3,328"
est_lo:   .byte <(EST_PHYS / 13), <(EST_CUT / 13), <(EST_STAR / 13), <(EST_TUNE / 13)
          .byte <(EST_IDLE / 13), <(EST_STARS / 13), <(EST_MSG / 13), <(EST_BUB / 13)
est_hi:   .byte >(EST_PHYS / 13), >(EST_CUT / 13), >(EST_STAR / 13), >(EST_TUNE / 13)
          .byte >(EST_IDLE / 13), >(EST_STARS / 13), >(EST_MSG / 13), >(EST_BUB / 13)

; A = 0 / 1: the page for hgr_line8 (sites), hgr_text8 (ht_page), pl_page
set_page:
        PHA
        JSR     pl_page
        PLA
        PHA
        JSR     hgr_select_page
        PLA
        BEQ     :+
        LDA     #$60
:       STA     ht_page
        RTS

; the level's platforms (two rows), trampolines (a platform on two legs),
; spikes (teeth every 6 px on a base SPIKE_H under their line), the frog (pl_sprite: its history is dropped
; by the caller, it stays)
scenery:
        LDX     #0
@s:     CPX     cr_nseg
        BCC     :+
        JMP     @frog
:       STX     gk
        LDA     seg_kind,X
        BEQ     @plat
        CMP     #SEG_TRAMP
        BNE     @spk
        LDA     seg_y0,X                ; a trampoline: two legs, then the
        STA     hl_ln_y0                ; platform's two lines
        CLC
        ADC     #6
        STA     hl_ln_y1
        LDA     seg_x0,X
        STA     hl_ln_x0
        STA     hl_ln_x1
        JSR     hgr_line8
        LDX     gk
        LDA     seg_x1,X
        STA     hl_ln_x0
        STA     hl_ln_x1
        JSR     hgr_line8
        LDX     gk
@plat:  LDA     seg_x0,X
        STA     hl_ln_x0
        LDA     seg_y0,X
        STA     hl_ln_y0
        LDA     seg_x1,X
        STA     hl_ln_x1
        LDA     seg_y1,X
        STA     hl_ln_y1
        JSR     hgr_line8
        LDX     gk
        LDA     seg_x0,X
        STA     hl_ln_x0
        LDA     seg_x1,X
        STA     hl_ln_x1
        LDY     seg_y0,X
        INY
        STY     hl_ln_y0
        LDY     seg_y1,X
        INY
        STY     hl_ln_y1
        JSR     hgr_line8
        JMP     @nx
@spk:   LDA     seg_y0,X                ; the base
        CLC
        ADC     #SPIKE_H
        STA     t1
        STA     hl_ln_y0
        STA     hl_ln_y1
        LDA     seg_x0,X
        STA     hl_ln_x0
        STA     t2
        LDA     seg_x1,X
        STA     hl_ln_x1
        JSR     hgr_line8
@t:     LDX     gk                      ; a tooth while x + 6 <= x1
        LDA     t2
        CLC
        ADC     #6
        BCS     @nx
        CMP     seg_x1,X
        BEQ     :+
        BCS     @nx
:       LDA     t2
        STA     hl_ln_x0
        ADC     #3                      ; (C = 0)
        STA     hl_ln_x1
        LDA     t1
        STA     hl_ln_y0
        LDA     seg_y0,X
        STA     hl_ln_y1
        JSR     hgr_line8
        LDX     gk
        LDA     t2
        CLC
        ADC     #3
        STA     hl_ln_x0
        ADC     #3
        STA     hl_ln_x1
        LDA     seg_y0,X
        STA     hl_ln_y0
        LDA     t1
        STA     hl_ln_y1
        JSR     hgr_line8
        LDA     t2
        CLC
        ADC     #6
        STA     t2
        JMP     @t
@nx:    LDX     gk
        INX
        JMP     @s
@frog:  JSR     cushions
        LDA     frog_x
        STA     pl_x
        LDA     frog_y
        STA     pl_y
        LDA     #<frog_desc
        STA     pl_sp
        LDA     #>frog_desc
        STA     pl_sp+1
        JMP     pl_sprite

; the cushions (hgr_line8: CUSH_NL lines a direction, cush_lines)
cushions:
        LDX     #0
@c:     CPX     cr_ncush
        BCS     @rts
        STX     gk
        LDA     cu_dir,X                ; the direction's lines: 4 * CUSH_NL each
        ASL     A
        ASL     A
        ASL     A
        ASL     A
        ASL     A
.assert CUSH_NL = 8, error, "cushions: dir * 4 * CUSH_NL"
        TAY
        LDA     #CUSH_NL
        STA     t1
@l:     LDX     gk
        LDA     cu_x,X
        CLC
        ADC     cush_lines,Y
        STA     hl_ln_x0
        LDA     cu_y,X
        CLC
        ADC     cush_lines+1,Y
        STA     hl_ln_y0
        LDA     cu_x,X
        CLC
        ADC     cush_lines+2,Y
        STA     hl_ln_x1
        LDA     cu_y,X
        CLC
        ADC     cush_lines+3,Y
        STA     hl_ln_y1
        STY     t2
        JSR     hgr_line8
        LDA     t2
        CLC
        ADC     #4
        TAY
        DEC     t1
        BNE     @l
        LDX     gk
        INX
        BNE     @c
@rts:   RTS

; ---------------------------------------------------------------------------
; render -- the hidden page: given back above the stars (all of it, and the
; stars drawn again, when one was taken), the ropes, the candy, the cursor;
; once the end is on both pages, only the cursor
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        LDA     #0
        STA     nlink
        LDA     cr_state
        BEQ     @full
        LDA     frozen                  ; renders since the end
        CMP     #3
        BCS     :+
        INC     frozen
:       LDA     frozen
        CMP     #3
        BCC     @full
        LDX     pidx
        LDA     dirty
        AND     bit_tab,X
        BNE     @full
        LDA     #TK_IDLE
        ORA     tkf
        STA     tkf
        LDA     dmark,X                 ; the last picture: the cursor only
        JSR     pl_erase_to
        JSR     draw_text
        JMP     draw_cursor
@full:  LDX     pidx
        LDA     dirty
        AND     bit_tab,X
        BEQ     @keep
        LDA     bit_tab,X
        EOR     #$FF
        AND     dirty
        STA     dirty
        LDA     #TK_STARS
        ORA     tkf
        STA     tkf
        JSR     pl_erase
        JSR     draw_stars
        JSR     free_bubble
        LDX     pidx
        LDA     pl_n,X
        STA     smark,X
        JMP     @dyn
@keep:  LDA     smark,X
        JSR     pl_erase_to
@dyn:   JSR     draw_text
        JSR     draw_puffs
        JSR     draw_ropes
        JSR     draw_candy
        JSR     draw_bubble
        LDX     pidx
        LDA     pl_n,X
        STA     dmark,X
        ; (falls into draw_cursor)

draw_cursor:
        LDA     cur_x
        SEC
        SBC     #3
        STA     pl_x
        LDA     cur_y
        SEC
        SBC     #3
        STA     pl_y
        LDA     #<cursor_desc
        STA     pl_sp
        LDA     #>cursor_desc
        STA     pl_sp+1
        JMP     pl_sprite

; the stars not taken yet (5 x 5, centred)
draw_stars:
        LDX     #2
@s:     STX     gk
        LDA     bit_tab,X
        AND     cr_stars
        BNE     @n
        LDA     star_x,X
        SEC
        SBC     #2
        STA     pl_x
        LDA     star_y,X
        SEC
        SBC     #2
        STA     pl_y
        LDA     #<star_desc
        STA     pl_sp
        LDA     #>star_desc
        STA     pl_sp+1
        JSR     pl_sprite
@n:     LDX     gk
        DEX
        BPL     @s
        RTS

; the bubble not taken yet (11 x 11, centred)
free_bubble:
        LDA     cr_bub
        CMP     #BUB_FREE
        BNE     bub_rts
        LDA     bub_x
        LDY     bub_y
bub_at: SEC                             ; A, Y = the centre (pl_x >= 0,
        SBC     #5                      ; pl_y <= VIEW_LAST - 10)
        BCS     :+
        LDA     #0
:       STA     pl_x
        TYA
        SEC
        SBC     #5
        CMP     #VIEW_LAST - 10 + 1
        BCC     :+
        LDA     #VIEW_LAST - 10
:       STA     pl_y
        LDA     #<bubble_desc
        STA     pl_sp
        LDA     #>bubble_desc
        STA     pl_sp+1
        JMP     pl_sprite
bub_rts:
        RTS

; the bubble round the candy while it holds it (in play)
draw_bubble:
        LDA     cr_state
        BNE     bub_rts
        LDA     cr_bub
        CMP     #BUB_CAUGHT
        BNE     bub_rts
        LDA     #TK_BUB
        ORA     tkf
        STA     tkf
        LDY     #0
        JSR     pt_xy
        TAY
        LDA     t2
        JMP     bub_at

; the puffs: PUFF_SHOW ticks from a cushion's puff, PUFF_NL lines (counted
; as a link each for the pace)
draw_puffs:
        LDX     #0
@c:     CPX     cr_ncush
        BCS     @rts
        LDA     cr_cool,X
        CMP     #PUFF_COOL - PUFF_SHOW + 1
        BCC     @n
        STX     gk
        INC     nlink
        LDA     cu_dir,X                ; 4 * PUFF_NL bytes a direction
        ASL     A
        ASL     A
        STA     t0
        ASL     A
        ADC     t0                      ; dir * 12 (C = 0)
.assert PUFF_NL = 3, error, "draw_puffs: dir * 4 * PUFF_NL"
        TAY
        LDA     #PUFF_NL
        STA     t1
@l:     LDX     gk
        LDA     cu_x,X
        CLC
        ADC     puff_lines,Y
        STA     pl_x0
        LDA     cu_y,X
        CLC
        ADC     puff_lines+1,Y
        STA     pl_y0
        LDA     cu_x,X
        CLC
        ADC     puff_lines+2,Y
        STA     pl_x1
        LDA     cu_y,X
        CLC
        ADC     puff_lines+3,Y
        STA     pl_y1
        STY     t2
        JSR     pl_line
        LDA     t2
        CLC
        ADC     #4
        TAY
        DEC     t1
        BNE     @l
        LDX     gk
@n:     INX
        BNE     @c
@rts:   RTS

; each link of the ropes still on: a line (nlink counts them)
draw_ropes:
        LDX     #0
@r:     CPX     cr_nrope
        BCS     @rts
        LDA     bit_tab,X
        AND     cr_on
        BEQ     @nx
        STX     t1
        LDA     rope_l0,X
        STA     gk
        CLC
        ADC     rope_n,X
        STA     t0
@l:     LDX     gk
        LDY     vl_con_a,X
        JSR     pt_xy
        STA     pl_y0
        LDA     t2
        STA     pl_x0
        LDX     gk
        LDY     vl_con_b,X
        JSR     pt_xy
        STA     pl_y1
        LDA     t2
        STA     pl_x1
        JSR     pl_line
        INC     nlink
        INC     gk
        LDA     gk
        CMP     t0
        BNE     @l
        LDX     t1
@nx:    INX
        BNE     @r
@rts:   RTS

; the candy (7 x 7, centred): not once in the frog, nor lost off the field
draw_candy:
        LDA     cr_state
        CMP     #WON
        BEQ     @rts
        CMP     #LOST
        BNE     @go
        LDA     vl_gnd
        BEQ     @rts
@go:    LDY     #0
        JSR     pt_xy
        SEC
        SBC     #3
        CMP     #VIEW_LAST - 6 + 1
        BCC     :+
        LDA     #VIEW_LAST - 6
:       STA     pl_y
        LDA     t2
        SEC
        SBC     #3
        BCS     :+
        LDA     #0
:       STA     pl_x
        LDA     #<candy_desc
        STA     pl_sp
        LDA     #>candy_desc
        STA     pl_sp+1
        JMP     pl_sprite
@rts:   RTS

; Y = point: t2 = its column (0 / 255 beyond the screen's ends), A = its row
; (VIEW_LAST at most: the ceiling keeps it below the text lines)
pt_xy:  LDA     vl_xh,Y
        BEQ     @x
        BMI     :+
        LDA     #255
        BNE     @sx
:       LDA     #0
        BEQ     @sx
@x:     LDA     vl_xl,Y
@sx:    STA     t2
        LDA     vl_yh,Y
        CMP     #VIEW_LAST + 1
        BCC     :+
        LDA     #VIEW_LAST
:       RTS

; the counters and the message that changed on this page
draw_text:
        LDA     #0
        STA     ht_sl
        LDA     pidx
        ASL     A
        ADC     pidx                    ; (C = 0)
        STA     t1
        TAX                             ; the level
        LDA     level
        CLC
        ADC     #1
        CMP     hud_pg,X
        BEQ     :+
        STA     hud_pg,X
        LDY     #15
        JSR     put2
:       LDX     t1                      ; the stars
        LDA     cr_nstar
        CMP     hud_pg+1,X
        BEQ     :+
        STA     hud_pg+1,X
        LDY     #25
        JSR     put1
:       LDX     t1                      ; the stars won in all
        LDA     total
        CMP     hud_pg+2,X
        BEQ     :+
        STA     hud_pg+2,X
        LDY     #36
        JSR     put2
:       LDA     cr_state                ; the message: in play (a restart),
        BEQ     :+                      ; or once frozen (19,000 cycles: not
        LDA     frozen                  ; with the physics)
        CMP     #3
        BCC     @rts
:       LDX     pidx
        LDA     msg
        CMP     msg_pg,X
        BEQ     @rts
        STA     msg_pg,X
        TAX
        LDA     #TK_MSG
        ORA     tkf
        STA     tkf
        LDA     #0
        STA     ht_col
        LDA     #8
        STA     ht_sl
        LDA     msg_lo,X
        STA     ht_src_lo
        LDA     msg_hi,X
        STA     ht_src_hi
        JMP     hgr_puts8
@rts:   RTS

; A (0..99) as two digits at column Y, row ht_sl (a space for a 0 ten)
put2:   STY     ht_col
        LDX     #0
:       CMP     #10
        BCC     :+
        SBC     #10                     ; (C = 1)
        INX
        BNE     :-
:       PHA
        TXA
        BEQ     :+
        ORA     #'0' - ' '
:       ORA     #' '
        INC     tkd
        JSR     hgr_putc8
        PLA
        LDY     ht_col
        ; (falls into put1)

; A (0..9) as a digit at column Y, row ht_sl
put1:   STY     ht_col
        INC     tkd
        ORA     #'0'
        JMP     hgr_putc8

.segment "RODATA"
m_label:    .byte "CUTROPE  LEVEL     STARS  /3  TOTAL   ", 0
m_play:     .byte "1-3 CUT 4-5 PUFF 6 POP  SPACE+IJKL R ESC", 0
m_won:      .byte "YUM!  N: NEXT LEVEL  R: AGAIN  ESC: MENU", 0
m_lost:     .byte "CANDY LOST!    R: TRY AGAIN    ESC: MENU", 0
msg_lo:     .byte <m_play, <m_won, <m_lost
msg_hi:     .byte >m_play, >m_won, >m_lost
.segment "CODE"

.include "hgr_text8.asm"                ; hgr_puts8_at (after its callers)
.include "hgr_plot_hist.asm"            ; the routines referenced above
.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
.include "verlet_seg.asm"               ; lib/physics (physdefs.inc: verlet.inc)
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
.include "kbd.asm"
.include "joy.asm"
.include "tune.asm"
.include "rwts.asm"
.include "hgr.asm"

; both HGR pages black ($2000-$5FFF): the HGR_CLEAR_LOOP macro over 8 groups,
; ~92,000 cycles (after the include that defines the macro)
clear_pages:
        LDA     #0
        LDX     #>HGR1
        HGR_CLEAR_LOOP 8
        JMP     vapor_mark_both         ; the marker on row 191 of both
.include "exit.asm"
.include "hgr_div7_ram.asm"
.include "vapor.asm"                    ; (here: its poll loop within a page)
.segment "RODATA"
.include "bbfont.inc"
.include "hgr_scanline.inc"
