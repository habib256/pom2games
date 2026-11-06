; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; lander.s -- LANDER: a lunar lander made of three Verlet points
; ============================================================================
; The dev/lib/physics demo (Apple II+ 48 KB, DOS 3.3, HGR). The physics is
; tools/lander.py transcribed in phys.inc (tests/test_lander.py: bit for
; bit); this file is the game around it: input, camera, drawing, HUD.
;
; Screen: rows 0-7 the HUD (altitude, vertical speed, fuel), 8-15 the
; message line, 16-191 the view: VIEW_H rows of the WORLD_H-row world. The
; camera is a zone (a static screen): the view shows world rows ztop..ztop
; + VIEW_H - 1, ztop = zone * ZSTEP; the zones overlap, the lander nearing
; an edge selects the next one: each page then has its view (rows 16-191)
; cleared and its ground drawn again when it is next drawn (the HUD and
; the message stay), one page a frame.
; Two pages: each tick draws the hidden one and shows it, in the vertical
; blank (vapor.asm: the beam found through the floating bus, a marker on
; row 191 of both pages; nothing is drawn below row 190), a tick every
; TICK_FRAMES video frames (30 a second: vapor_pace, given an estimate of
; the tick's cycles); without a floating bus (//c, IIgs) it runs unpaced.
; On that page
; the lander of two frames ago is given back (hgr_plot_hist.asm recorded
; the bits its lines and debris lit: EOR, the ground under it comes back as
; it was), the new one drawn (fast lines, the debris a 3 x 3 sprite each),
; and of the HUD and the message only the characters that differ from what
; the page shows are written.
; Keys: J / <- and L / -> turn, K / I / up the engine (a key press runs it
; THR_HOLD ticks: the II+ keyboard has no key-up, its repeat keeps it on),
; space cuts, R restarts, ESC quits. A joystick (found at start): X turns,
; button 0 is the engine.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
PL_HIST    = $1800                      ; hgr_plot_hist.asm's histories: 1.5 KB
HGR_PLOT_HIST_FAST = 1                  ; lines stepped by byte, pl_sprite
PL_SPRITE_YMIN = 16                     ; the view's first row
MUL_ACC    = 1
mul_y = mul_s1l                 ; operand is also the first table pointer low byte
.include "math.inc"
.include "landconst.inc"
.include "physdefs.inc"
.include "hgr_pages.inc"
HGR_LINE_DIV7 = hgr_div7                ; (hgr_div7_ram.asm)
HGR_LINE_MOD7 = hgr_mod7
HGR_TEXT8_HGR_ORDER = 1

HUD_ROWS  = 16                          ; the view starts at row 16
VIEW_H    = 192 - HUD_ROWS
ZSTEP     = 120                         ; zone tops 0, 120, 240, 360
ZONES     = (WORLD_H - VIEW_H) / ZSTEP + 1
ZMARGIN   = 16                          ; rows from an edge: next zone
VIEW_LAST = 190                         ; the last row drawn (191: the vapor marker)
; ROT_HOLD, THR_HOLD (landconst.inc): ticks a key turns, fires the engine
JOY_DEAD  = 38                          ; read_stick_x counts (12 on the
                                        ; former read_stick_fast: x 35/11)
.assert (ZONES - 1) * ZSTEP + VIEW_H = WORLD_H, error, "zones: cover the world exactly"

; rows 16-191 of the HGR page at base black (A = 0): the three last 256 B
; pages of each 1 KB whole, then the first one but its two HUD rows
.macro CLEAR_VIEW base
        .local @full, @part
        LDX     #0
@full:  .repeat 8, K
        .repeat 3, J
        STA     base + K * $400 + (J + 1) * $100,X
        .endrepeat
        .endrepeat
        INX
        BNE     @full
        LDX     #$28
@part:  .repeat 8, K
        STA     base + K * $400,X       ; $x028-$x07F
        STA     base + K * $400 + $80,X ; $x0A8-$x0FF
        .endrepeat
        INX
        CPX     #$80
        BNE     @part
        RTS
.endmacro

MSG_HELP   = 0
MSG_LANDED = 1                          ; + pad - 1
MSG_CRASH  = 4
MSG_FUEL   = 5

.globalzp dec_lo, dec_hi, dec_ptr       ; (dec.asm, at the end)

.segment "ZEROPAGE"
pidx:   .res 1                          ; page drawn this frame: 0 = 1, 1 = 2
zone:   .res 1
ztop:   .res 2                          ; world row at the top of the view
sx:     .res 5                          ; screen x, y: points 0-2, flame tip,
sy:     .res 5                          ; flame root ($FF = out of view)
t0:     .res 1
t1:     .res 1
t2:     .res 1
t3:     .res 1
xa:     .res 1                          ; draw_ground: columns xa..xb
xb:     .res 1
gk:     .res 1
gy0:    .res 1
gy1:    .res 1
srcp:   .res 2                          ; diff_row: the text now,
shp:    .res 2                          ; what the page shows,
dend:   .res 1                          ; the column after the last
gp:     .res 2                          ; fast_put: the glyph,
fp_y:   .res 1                          ; Y kept

.segment "BSS"
frames:   .res 2                        ; frames drawn (tests)
dirty:    .res 2                        ; per page: its view to clear (zone)
sh0:      .res 2 * 40                   ; per page: the HUD row shown
sh8:      .res 2 * 40                   ; per page: the message row shown
now:      .res 40                       ; the HUD row this frame
msg_pg:   .res 2                        ; message shown on each page
msg:      .res 1
thr_hold: .res 1
rot_hold: .res 1
joy_ok:   .res 1
joy_cx:   .res 1
burn:     .res 1                        ; the engine fired this tick
pace_ok:  .res 1                        ; a floating bus: vapor_pace
pace_add: .res 2                        ; this tick's extra polls (sounds, clears)
last_st:  .res 1
numbuf:   .res 6

.segment "CODE"
        JMP     start
.include "sound.asm"                    ; first: its loops never cross a page
.include "hgr_text8.asm"                ; (its zero page before the callers)
.include "hgr_line.asm"
.include "hgr_plot_hist.asm"            ; lib/hgr: its zero page (routines at the end)
.include "phys.inc"

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
        STA     pace_add
        STA     pace_add+1
        LDA     #$7F                    ; white text
        STA     ht_cm_ev
        STA     ht_cm_od
        LDA     #<bbfont
        STA     ht_font_lo
        LDA     #>bbfont
        STA     ht_font_hi
        LDA     #40
        STA     ht_wrap
        JSR     read_stick_fast         ; a joystick: both timers run out
        BCS     :+
        JSR     read_stick_x            ; its X at rest (PREAD scale)
        LDA     joy_x
        STA     joy_cx
        INC     joy_ok
:       JSR     clear_pages             ; (and the vapor marker)
        JSR     hgr_init
        JSR     vapor_pace_init         ; a floating bus?
        BCS     restart
        INC     pace_ok

restart:
        LDA     #START_X
        STA     st_x
        LDA     #<START_Y
        STA     st_y
        LDA     #>START_Y
        STA     st_y+1
        LDA     #<START_VX
        STA     st_vx
        LDA     #>START_VX
        STA     st_vx+1
        LDA     #<START_VY
        STA     st_vy
        LDA     #>START_VY
        STA     st_vy+1
        JSR     phys_reset
        LDA     #0
        STA     thr_hold
        STA     rot_hold
        STA     burn
        STA     last_st
        STA     zone
        LDA     #MSG_HELP
        STA     msg
        JSR     fit_zone
        JSR     new_screen

main:   JSR     input                   ; (R: back to restart, ESC: quit)
        LDA     #0                      ; the engine fires this tick?
        STA     burn
        LDA     lv_status
        BNE     :+
        LDA     in_thr
        BEQ     :+
        LDA     lv_fuel
        BEQ     :+
        INC     burn
:       JSR     phys_tick
        JSR     events
        JSR     camera
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
; pace -- wait for line 191 of the tick's last video frame: vapor_pace with
; TICK_FRAMES and the tick's estimate (a base per state + pace_add, the
; sounds and the clears it did); unpaced without a floating bus
; ---------------------------------------------------------------------------
pace:   LDA     pace_ok
        BEQ     @rts
        LDX     lv_status
        CLC
        LDA     est_lo,X
        ADC     pace_add
        STA     pace_add
        LDA     est_hi,X
        ADC     pace_add+1
        TAY
        LDX     pace_add
        LDA     #0
        STA     pace_add
        STA     pace_add+1
        LDA     #TICK_FRAMES
        JMP     vapor_pace
@rts:   RTS

; the cycles of a tick (main to pace) by lv_status, in polls (13 cycles)
EST_FLY     = 15000                     ; coasting 13,300, engine 16,800
EST_LANDED  = 9000
EST_CRASHED = 9000                      ; debris 7,900 (17,700 with the message)
est_lo:   .byte <(EST_FLY / 13), <(EST_LANDED / 13), <(EST_CRASHED / 13)
est_hi:   .byte >(EST_FLY / 13), >(EST_LANDED / 13), >(EST_CRASHED / 13)

; PACE_ADD cycles: pace_add += cycles / 13 (a sound, a clear)
.macro PACE_ADD cyc
        CLC
        LDA     pace_add
        ADC     #<((cyc) / 13)
        STA     pace_add
        LDA     pace_add+1
        ADC     #>((cyc) / 13)
        STA     pace_add+1
.endmacro
TONE_C   = 12 + 30                      ; tone: its call, then A x (12 + 5 X)
.define  TONE_CYC(n, d) (TONE_C + (n) * (12 + 5 * (d)))
GROWL_N  = ($100 - $58 + 5) / 6         ; the growl: 6 flips from $58 by 6
GROWL_C  = GROWL_N * (TONE_CYC(6, 0) + 20) + 6 * 5 * (GROWL_N * $58 + 6 * GROWL_N * (GROWL_N - 1) / 2)
LANDED_C = TONE_CYC($40, $50) + TONE_CYC($60, $38)

; ---------------------------------------------------------------------------
; input -- keys and joystick -> in_thr, in_rot for this tick
; ---------------------------------------------------------------------------
input:  JSR     poll_key
        BEQ     @hold
        CMP     #'J'
        BEQ     @left
        CMP     #KC_LEFT
        BEQ     @left
        CMP     #'L'
        BEQ     @right
        CMP     #KC_RIGHT
        BEQ     @right
        CMP     #'K'
        BEQ     @thr
        CMP     #'I'
        BEQ     @thr
        CMP     #KC_UP
        BEQ     @thr
        CMP     #' '
        BEQ     @cut
        CMP     #'R'
        BEQ     @again
        CMP     #KC_ESC
        BEQ     quit
        BNE     @hold
@left:  LDA     #<-ROT_HOLD
        BNE     @rot
@right: LDA     #ROT_HOLD
@rot:   STA     rot_hold
        JMP     @hold
@thr:   LDA     #THR_HOLD
        STA     thr_hold
        BNE     @hold
@cut:   LDA     #0
        STA     thr_hold
        STA     rot_hold
        BEQ     @hold
@again: PLA                             ; (called from main)
        PLA
        JMP     restart
@hold:  LDA     #0
        STA     in_thr
        STA     in_rot
        LDA     thr_hold
        BEQ     @nt
        DEC     thr_hold
        INC     in_thr
@nt:    LDA     rot_hold
        BEQ     @joy
        BMI     @nl
        DEC     rot_hold
        LDA     #1
        STA     in_rot
        BNE     @joy
@nl:    INC     rot_hold
        LDA     #$FF
        STA     in_rot
@joy:   LDA     joy_ok
        BEQ     @rts
        JSR     read_stick_x            ; X alone (PREAD scale)
        SEC
        LDA     joy_x
        SBC     joy_cx
        BMI     @jl
        CMP     #JOY_DEAD
        BCC     @btn
        LDA     #1
        STA     in_rot
        BNE     @btn
@jl:    CMP     #<(-JOY_DEAD + 1)
        BCS     @btn
        LDA     #$FF
        STA     in_rot
@btn:   LDA     BUTN0
        BPL     @rts
        LDA     #1
        STA     in_thr
@rts:   RTS

; ---------------------------------------------------------------------------
; events -- the end of a flight (message, sound), the empty tank, the engine
; ---------------------------------------------------------------------------
events: LDA     lv_status
        CMP     last_st
        BEQ     @same
        STA     last_st
        CMP     #LANDED
        BNE     @crash
        CLC
        LDA     lv_pad
        ADC     #MSG_LANDED - 1
        STA     msg
        PACE_ADD LANDED_C
        LDA     #$40
        LDX     #$50
        JSR     tone
        LDA     #$60
        LDX     #$38
        JMP     tone
@crash: LDA     #MSG_CRASH
        STA     msg
        PACE_ADD GROWL_C
        LDA     #$58                    ; a falling growl
        STA     t0
:       LDA     #6
        LDX     t0
        JSR     tone
        CLC
        LDA     t0
        ADC     #6
        STA     t0
        BCC     :-
        RTS
@same:  LDA     lv_status
        BNE     @rts
        LDA     lv_fuel
        BNE     @burn
        LDA     #MSG_FUEL
        STA     msg
@burn:  LDA     burn                    ; the engine rumbles: a click a frame
        BEQ     @rts
        BIT     SPKR
@rts:   RTS

; ---------------------------------------------------------------------------
; camera -- the zone follows the lander (frozen after a crash: the debris
; would bounce it between two zones)
; ---------------------------------------------------------------------------
camera: LDA     lv_status
        CMP     #CRASHED
        BEQ     @rts
        JSR     rows_minmax
        LDA     zone                    ; lowest point near the bottom: down
        CMP     #ZONES - 1
        BCS     @up
        CLC
        LDA     ztop
        ADC     #<(VIEW_H - ZMARGIN)
        STA     gy0
        LDA     ztop+1
        ADC     #>(VIEW_H - ZMARGIN)
        STA     gy1
        LDA     gy0                     ; max row > ztop + VIEW_H - ZMARGIN ?
        CMP     t2
        LDA     gy1
        SBC     t3
        BCS     @up
        INC     zone
        JMP     new_zone
@up:    LDA     zone                    ; highest point near the top: up
        BEQ     @rts
        CLC
        LDA     ztop
        ADC     #ZMARGIN
        STA     gy0
        LDA     ztop+1
        ADC     #0
        STA     gy1
        LDA     t0                      ; min row < ztop + ZMARGIN ?
        CMP     gy0
        LDA     t1
        SBC     gy1
        BCS     @rts
        DEC     zone
        JMP     new_zone
@rts:   RTS

; the zone changed: both pages get their view again when next drawn
new_zone:
        LDX     zone
        LDA     zone_lo,X
        STA     ztop
        LDA     zone_hi,X
        STA     ztop+1
        LDA     #1
        STA     dirty
        STA     dirty+1
        RTS

; the zone of the lander at a (re)start: down while it is too low
fit_zone:
        JSR     rows_minmax
@z:     LDX     zone
        CPX     #ZONES - 1
        BCS     @rts
        LDA     zone_lo,X
        ADC     #<(VIEW_H - ZMARGIN)    ; (C = 0)
        STA     gy0
        LDA     zone_hi,X
        ADC     #>(VIEW_H - ZMARGIN)
        STA     gy1
        LDA     gy0
        CMP     t2
        LDA     gy1
        SBC     t3
        BCS     @rts
        INC     zone
        BNE     @z
@rts:   RTS

; t1:t0 = the highest row of the 3 points, t3:t2 the lowest (16 bits; in
; flight the ceiling keeps y >= 0)
rows_minmax:
        LDA     #$FF
        STA     t0
        STA     t1
        LDA     #0
        STA     t2
        STA     t3
        LDX     #2
@p:     LDA     vl_yh,X
        CMP     t0
        LDA     vl_yu,X
        SBC     t1
        BCS     :+
        LDA     vl_yh,X
        STA     t0
        LDA     vl_yu,X
        STA     t1
:       LDA     t2
        CMP     vl_yh,X
        LDA     t3
        SBC     vl_yu,X
        BCS     :+
        LDA     vl_yh,X
        STA     t2
        LDA     vl_yu,X
        STA     t3
:       DEX
        BPL     @p
        RTS

; ---------------------------------------------------------------------------
; new_screen -- both pages: cleared, the ground, the HUD labels (the HUD
; digits and the message come with the next frames); no lander drawn yet
; ---------------------------------------------------------------------------
new_screen:
        LDX     zone
        LDA     zone_lo,X
        STA     ztop
        LDA     zone_hi,X
        STA     ztop+1
        JSR     clear_pages
        LDA     #1
        STA     t3
@page:  LDA     t3
        JSR     set_page
        LDA     #0
        STA     xa
        LDA     #255
        STA     xb
        JSR     draw_ground
        LDA     #0
        STA     ht_col
        STA     ht_sl
        LDA     #<hud_label
        STA     ht_src_lo
        LDA     #>hud_label
        STA     ht_src_hi
        JSR     hgr_puts8
        LDX     t3
        LDA     #$FF
        STA     msg_pg,X
        LDA     #0
        STA     dirty,X
        STA     pl_n,X
        DEC     t3
        BPL     @page
        LDX     #2 * 40 - 1             ; what the pages show: the labels,
:       LDA     #' '                    ; a blank message line
        STA     sh8,X
        STA     sh0,X
        DEX
        BPL     :-
        LDX     #hud_label_end - hud_label - 1
:       LDA     hud_label,X
        STA     sh0,X
        STA     sh0+40,X
        STA     now,X
        DEX
        BPL     :-
        RTS


; ---------------------------------------------------------------------------
; render -- the hidden page: the old lander given back (or the view cleared
; and the ground drawn again after a zone change), the new one in, the HUD
; and the message characters that changed
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        LDX     pidx
        LDA     dirty,X
        BEQ     :+
        LDA     #0
        STA     dirty,X
        STA     pl_n,X                  ; (its history goes with the view)
        TXA
        JSR     clear_view
        JSR     vapor_mark_both         ; (row 191 cleared with the view)
        PACE_ADD CLEAR_C
        LDA     #0
        STA     xa
        LDA     #255
        STA     xb
        JSR     draw_ground
        JMP     :++
:       JSR     pl_erase
:       JSR     draw_lander
        JSR     draw_hud
        LDX     pidx
        LDA     msg
        CMP     msg_pg,X
        BEQ     :+
        STA     msg_pg,X
        JSR     draw_msg
:       RTS

; A = 0 / 1: select the page for hgr_line8 (sites), hgr_text8 (ht_page),
; hgr_plot_hist (pl_page); shp = its HUD row's shadow
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

; A = 0 / 1: the page's rows 16-191 black (rows 0-15, the HUD, kept):
; every byte but $x000-$x027 and $x080-$x0A7 of each 1 KB, ~39,000 cycles
; (CLEAR_C: with the ground drawn again after it, for vapor_pace)
CLEAR_C = 50000
clear_view:
        TAX
        LDA     #0
        CPX     #0
        BEQ     :+
        JMP     clear_view2
:       CLEAR_VIEW $2000
clear_view2:
        CLEAR_VIEW $4000

; ---------------------------------------------------------------------------
; draw_ground -- the ground of columns xa..xb (segments of 4 px) and the
; pads (a second line under them) on the selected page, in the view only
; ---------------------------------------------------------------------------
draw_ground:
        LDA     xa
        AND     #$FC
        STA     gk
@seg:   LDX     gk
        JSR     gy_at
        CMP     #$FF
        BEQ     @next
        STA     t2
        LDA     gk
        CLC
        ADC     #4
        BCC     :+
        LDA     #255
:       STA     hl_ln_x1
        TAX
        JSR     gy_at
        CMP     #$FF
        BEQ     @next
        STA     hl_ln_y1
        LDA     t2
        STA     hl_ln_y0
        LDA     gk
        STA     hl_ln_x0
        JSR     hgr_line8
@next:  LDA     gk
        CLC
        ADC     #4
        BCS     @pads
        STA     gk
        CMP     xb
        BCC     @seg
        BEQ     @seg
@pads:  LDY     #NPADS - 1
@p:     LDA     pad_x1,Y                ; the pad overlaps xa..xb?
        CMP     xa
        BCC     @np
        LDA     xb
        CMP     pad_x0,Y
        BCC     @np
        CLC                             ; its row + 1 in the view?
        LDA     pad_rl,Y
        ADC     #<(HUD_ROWS + 1)
        STA     gy0
        LDA     pad_rh,Y
        ADC     #>(HUD_ROWS + 1)
        STA     gy1
        SEC
        LDA     gy0
        SBC     ztop
        TAX
        LDA     gy1
        SBC     ztop+1
        BNE     @np
        CPX     #HUD_ROWS
        BCC     @np
        CPX     #VIEW_LAST + 1
        BCS     @np
        STX     hl_ln_y0
        STX     hl_ln_y1
        LDA     pad_x0,Y
        STA     hl_ln_x0
        LDA     pad_x1,Y
        STA     hl_ln_x1
        STY     gk
        JSR     hgr_line8
        LDY     gk
@np:    DEY
        BPL     @p
        RTS

; X = column -> A = the screen row of the ground there, $FF out of view.
; Clobbers Y.
gy_at:  CLC
        LDA     heights,X
        ADC     #<(GROUND_BASE + HUD_ROWS)
        STA     gy0
        LDA     #>(GROUND_BASE + HUD_ROWS)
        ADC     #0
        STA     gy1
        SEC
        LDA     gy0
        SBC     ztop
        TAY
        LDA     gy1
        SBC     ztop+1
        BNE     @off
        CPY     #HUD_ROWS
        BCC     @off
        CPY     #VIEW_LAST + 1
        BCS     @off
        TYA
        RTS
@off:   LDA     #$FF
        RTS

; ---------------------------------------------------------------------------
; draw_lander -- the lander (or its debris) on the selected page, recorded
; in its history for pl_erase two frames later
; ---------------------------------------------------------------------------
draw_lander:
        LDX     #2
:       JSR     scr_point
        DEX
        BPL     :-
        LDA     lv_status
        CMP     #CRASHED
        BEQ     @debris
        LDX     #0                      ; the legs to the top, the base
        LDY     #2
        JSR     line_ij
        LDX     #1
        LDY     #2
        JSR     line_ij
        LDX     #0
        LDY     #1
        JSR     line_ij
        LDA     burn
        BEQ     @rts
        JSR     flame
        LDX     #4
        LDY     #3
        JMP     line_ij
@debris:
        LDX     #2                      ; each point a small cross
@d:     LDA     sy,X
        CMP     #$FF
        BEQ     @dn
        SEC
        SBC     #1
        STA     pl_y                    ; (row 16: its top row clipped)
        LDA     sx,X
        SEC
        SBC     #1
        BCS     :+
        LDA     #0
:       STA     pl_x
        LDA     #<cross_desc
        STA     pl_sp
        LDA     #>cross_desc
        STA     pl_sp+1
        STX     gk
        JSR     pl_sprite
        LDX     gk
@dn:    DEX
        BPL     @d
@rts:   RTS

; X = point -> sx,X = its column, sy,X = its screen row ($FF: out of view)
scr_point:
        LDA     vl_xl,X
        STA     sx,X
        SEC
        LDA     vl_yh,X
        SBC     ztop
        STA     t0
        LDA     vl_yu,X
        SBC     ztop+1
        STA     t1
        CLC
        LDA     t0
        ADC     #HUD_ROWS
        STA     t0
        LDA     t1
        ADC     #0
        BNE     @off
        LDA     t0
        CMP     #HUD_ROWS
        BCC     @off
        CMP     #VIEW_LAST              ; (<= 189: a debris cross reaches
        BCS     @off                    ; one row below)
        STA     sy,X
        RTS
@off:   LDA     #$FF
        STA     sy,X
        RTS

; the flame: from the middle of the legs (4) away from the top (tip 3)
flame:  LDA     #$FF
        STA     sy+3
        STA     sy+4
        LDX     #2
:       LDA     sy,X
        CMP     #$FF
        BEQ     @rts
        DEX
        BPL     :-
        CLC
        LDA     sx
        ADC     sx+1
        ROR     A
        STA     sx+4
        CLC
        LDA     sy
        ADC     sy+1
        ROR     A
        STA     sy+4
        SEC                             ; tip = root + (root - top) / 2
        LDA     sx+4
        SBC     sx+2
        CMP     #$80
        ROR     A
        CLC
        ADC     sx+4
        STA     sx+3
        SEC
        LDA     sy+4
        SBC     sy+2
        CMP     #$80
        ROR     A
        STA     t0
        LDA     frames                  ; it flickers
        AND     #2
        CLC
        ADC     t0
        CLC
        ADC     sy+4
        CMP     #HUD_ROWS
        BCC     @rts
        CMP     #VIEW_LAST + 1
        BCS     @rts
        STA     sy+3
@rts:   RTS

; a line between screen points X and Y if both are in view
line_ij:
        LDA     sy,X
        CMP     #$FF
        BEQ     @rts
        STA     pl_y0
        LDA     sy,Y
        CMP     #$FF
        BEQ     @rts
        STA     pl_y1
        LDA     sx,X
        STA     pl_x0
        LDA     sx,Y
        STA     pl_x1
        JMP     pl_line
@rts:   RTS

; ---------------------------------------------------------------------------
; draw_hud -- altitude (rows from the legs' discs to the ground under the
; middle), vertical speed (1/16 px a tick, + down), fuel: written in now,
; then the characters the page does not show yet
; ---------------------------------------------------------------------------
draw_hud:
        CLC                             ; ground row under the middle
        LDA     vl_xl
        ADC     vl_xl+1
        ROR     A
        TAX
        CLC
        LDA     heights,X
        ADC     #<GROUND_BASE
        STA     dec_lo
        LDA     #>GROUND_BASE
        ADC     #0
        STA     dec_hi
        LDX     #0                      ; the lower leg
        LDA     vl_yh
        CMP     vl_yh+1
        LDA     vl_yu
        SBC     vl_yu+1
        BCS     :+
        INX
:       SEC                             ; - its row - the leg's radius
        LDA     dec_lo
        SBC     vl_yh,X
        STA     dec_lo
        LDA     dec_hi
        SBC     vl_yu,X
        STA     dec_hi
        BCC     :+
        LDA     dec_lo
        SBC     #>RADIUS + 1
        STA     dec_lo
        LDA     dec_hi
        SBC     #0
        STA     dec_hi
        BCS     :++
:       LDA     #0
        STA     dec_lo
        STA     dec_hi
:       LDA     #<numbuf
        STA     dec_ptr
        LDA     #>numbuf
        STA     dec_ptr+1
        JSR     u16_to_dec              ; Y = digits
        LDX     #4                      ; columns 4..: at least 3 wide
        LDA     #' '
        STA     now+7
:       CPY     #3
        BCS     :+
        STA     now,X
        INX
        INY
        BNE     :-
:       LDY     #0
:       LDA     numbuf,Y
        BEQ     :+
        STA     now,X
        INX
        INY
        BNE     :-
:       SEC                             ; vertical speed of the top >> 4
        LDA     vl_yf+2
        SBC     vl_oyf+2
        STA     t0
        LDA     vl_yh+2
        SBC     vl_oyh+2
        LDX     #4
:       CMP     #$80
        ROR     A
        ROR     t0
        DEX
        BNE     :-
        LDX     #'+'
        TAY
        BPL     :+
        LDX     #'-'
        SEC
        LDA     #0
        SBC     t0
        STA     t0
        TYA
        EOR     #$FF
        ADC     #0
:       BEQ     :+                      ; |v| > 255: 99
        LDA     #99
        STA     t0
:       LDA     t0
        CMP     #100
        BCC     :+
        LDA     #99
:       STX     now+12
        JSR     byte_to_dec             ; Y tens, A units
        ORA     #'0'
        STA     now+14
        TYA
        ORA     #'0'
        STA     now+13
        LDA     lv_fuel                 ; fuel
        JSR     byte_to_dec             ; X hundreds, Y tens, A units
        ORA     #'0'
        STA     now+24
        TYA
        ORA     #'0'
        STA     now+23
        TXA
        ORA     #'0'
        STA     now+22
        LDA     #<now                   ; what changed on this page
        STA     srcp
        LDA     #>now
        STA     srcp+1
        LDX     pidx
        LDA     sh_lo,X
        STA     shp
        LDA     sh_hi,X
        STA     shp+1
        LDA     #0
        STA     ht_sl
        LDY     #4
        LDA     #8
        JSR     diff_row
        LDY     #12
        LDA     #15
        JSR     diff_row
        LDY     #22
        LDA     #25

; (srcp),Y vs (shp),Y for Y = Y .. A - 1: the characters that differ
; written at row ht_sl and recorded in (shp). Clobbers A, Y.
diff_row:
        STA     dend
@l:     LDA     (srcp),Y
        CMP     (shp),Y
        BEQ     @n
        STA     (shp),Y
        JSR     fast_put
@n:     INY
        CPY     dend
        BNE     @l
        RTS

; A = char ($20-$5F), Y = column: its 8 glyph rows stored at text line
; ht_sl / 8 (0 or 1) of the draw page (ht_page), white: what hgr_putc8
; writes there, ~150 cycles instead of ~470 (a private 8-row STA loop,
; dev/lib/font). Keeps Y.
fast_put:
        STY     fp_y
        SEC
        SBC     #$20                    ; the glyph: bbfont + 8 (char - $20)
        LDX     #0
        STX     gp+1
        ASL     A
        ROL     gp+1
        ASL     A
        ROL     gp+1
        ASL     A
        ROL     gp+1                    ; (C = 0)
        ADC     #<bbfont
        STA     gp
        LDA     gp+1
        ADC     #>bbfont
        STA     gp+1
        TYA                             ; X = the column, + $80 on line 1
        LDX     ht_sl
        BEQ     :+
        ORA     #$80
:       TAX
        LDY     #0
        LDA     ht_page
        BNE     @p2
        .repeat 8, R
        LDA     (gp),Y
        STA     $2000 + R * $400,X
        .if R < 7
        INY
        .endif
        .endrepeat
        LDY     fp_y
        RTS
@p2:    .repeat 8, R
        LDA     (gp),Y
        STA     $4000 + R * $400,X
        .if R < 7
        INY
        .endif
        .endrepeat
        LDY     fp_y
        RTS

; the message line (row 8) on the selected page: its changed characters
draw_msg:
        LDX     msg
        LDA     msg_lo,X
        STA     srcp
        LDA     msg_hi,X
        STA     srcp+1
        LDX     pidx
        LDA     sh_lo+2,X
        STA     shp
        LDA     sh_hi+2,X
        STA     shp+1
        LDA     #8
        STA     ht_sl
        LDY     #0
        LDA     #40
        JMP     diff_row

.segment "RODATA"
zone_lo:  .repeat ZONES, I
          .byte <(I * ZSTEP)
          .endrepeat
zone_hi:  .repeat ZONES, I
          .byte >(I * ZSTEP)
          .endrepeat
hud_label:  .byte "ALT      VS      FUEL"
hud_label_end:
            .byte 0
sh_lo:      .byte <sh0, <(sh0 + 40), <sh8, <(sh8 + 40)
sh_hi:      .byte >sh0, >(sh0 + 40), >sh8, >(sh8 + 40)
cross_desc: .byte 2, 3                  ; pl_sprite: a 3 x 3 cross
            .repeat 7, I
            .addr cross_spr + I * 6
            .endrepeat
cross_spr:  .repeat 7, I
            .byte (2 << I) & $7F, (2 << I) >> 7
            .byte (7 << I) & $7F, (7 << I) >> 7
            .byte (2 << I) & $7F, (2 << I) >> 7
            .endrepeat
m_help:     .byte "J L:TURN  K:ENGINE  SPACE:CUT  R:RESTART", 0
m_pad_a:    .byte "LANDED ON PAD A!          R:FLY AGAIN   ", 0
m_pad_b:    .byte "LANDED ON PAD B!          R:FLY AGAIN   ", 0
m_pad_c:    .byte "LANDED ON PAD C!          R:FLY AGAIN   ", 0
m_crash:    .byte "CRASHED!                  R:FLY AGAIN   ", 0
m_fuel:     .byte "OUT OF FUEL!                            ", 0
msg_lo:     .byte <m_help, <m_pad_a, <m_pad_b, <m_pad_c, <m_crash, <m_fuel
msg_hi:     .byte >m_help, >m_pad_a, >m_pad_b, >m_pad_c, >m_crash, >m_fuel
.assert m_pad_a - m_help = 41 .and m_pad_b - m_pad_a = 41 .and m_pad_c - m_pad_b = 41 .and m_crash - m_pad_c = 41 .and m_fuel - m_crash = 41 .and msg_lo - m_fuel = 41, error, "messages: 40 characters"
.segment "CODE"

.include "hgr_plot_hist.asm"            ; the routines referenced above
.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
.include "verlet_hmap.asm"              ; lib/physics (physdefs.inc: verlet.inc)
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
.include "dec.asm"
.include "kbd.asm"
.include "joy.asm"
.include "hgr.asm"
.include "vapor.asm"                    ; keep the timed poll within one page

; both HGR pages black ($2000-$5FFF): the HGR_CLEAR_LOOP macro over 8 groups,
; ~92,000 cycles, 79 bytes (after the include that defines the macro)
clear_pages:
        LDA     #0
        LDX     #>HGR1
        HGR_CLEAR_LOOP 8
        JMP     vapor_mark_both         ; the marker on row 191 of both
.include "exit.asm"
.include "hgr_div7_ram.asm"
.segment "RODATA"
.include "bbfont.inc"
.include "hgr_scanline.inc"
