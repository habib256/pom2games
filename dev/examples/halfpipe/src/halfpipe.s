; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; halfpipe.s -- HALFPIPE: a skate / BMX half-pipe made of three Verlet points
; ============================================================================
; The dev/lib/physics segment-ground demo (Apple II+ 48 KB, DOS 3.3, HGR).
; The physics is tools/halfpipe.py transcribed in phys.inc
; (tests/test_halfpipe.py: bit for bit); this file is the game around it:
; input, events, drawing, HUD.
;
; Screen: rows 0-7 the HUD (score, the last landing's points, the air of
; the last scored jump in px above the lip), 8-15 the message line, 16-191 the
; pipe (one static screen: the world is the screen, x 0..255).
; Two pages: each tick draws the hidden one and shows it, in the vertical
; blank (vapor.asm: the beam found through the floating bus, a marker on
; row 191 of both pages; nothing is drawn below row 190), a tick every
; TICK_FRAMES video frames (30 a second: vapor_pace, given an estimate of
; the tick's cycles); without a floating bus (//c, IIgs) it runs unpaced.
; On that page
; the rider of two frames ago is given back (hgr_plot_hist.asm recorded the
; bits its lines and wheels lit: EOR, the pipe under it comes back as it
; was), the new one drawn (fast lines, each wheel a 3 x 3 sprite), and of
; the HUD and the message only the characters that differ from what the
; page shows are written.
; Keys: K / I / up / space pump (a press pumps PUMP_HOLD ticks: the II+
; keyboard has no key-up, its repeat keeps it on), J / <- and L / -> lean
; (LEAN_HOLD ticks a press), R restarts, ESC quits. A joystick (found at
; start): X leans, button 0 pumps. After a crash, a new run starts by
; itself after AGAIN_T ticks.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
PL_HIST    = $1800                      ; hgr_plot_hist.asm's histories: 1.5 KB
HGR_PLOT_HIST_FAST = 1                  ; lines stepped by byte, pl_sprite
PL_SPRITE_YMIN = 16                     ; the pipe's first row
MUL_ACC    = 1
mul_y = mul_s1l                 ; operand is also the first table pointer low byte
.include "math.inc"
.include "pipeconst.inc"
.include "physdefs.inc"
.include "hgr_pages.inc"
HGR_LINE_DIV7 = hgr_div7                ; (hgr_div7_ram.asm)
HGR_LINE_MOD7 = hgr_mod7
HGR_TEXT8_HGR_ORDER = 1
BCD_PUT_OUT = now_put                   ; (bcd.asm: the score's digits)

HUD_ROWS  = 16                          ; the pipe starts at row 16
VIEW_LAST = 190                         ; the last row drawn (191: the vapor marker)
; PUMP_HOLD, LEAN_HOLD, AGAIN_T (pipeconst.inc): ticks a key pumps, a key
; leans; ticks after a crash before a new run
JOY_DEAD  = 38                          ; read_stick_x counts (12 on the
                                        ; former read_stick_fast: x 35/11)

MSG_HELP   = 0
MSG_AIR    = 1                          ; a landing without a full turn
MSG_360    = 2                          ; + spins - 1 (up to MSG_1080)
MSG_1080   = 4
MSG_CRASH  = 5

.globalzp dec_lo, dec_hi, dec_ptr       ; (dec.asm, at the end)

.segment "ZEROPAGE"
pidx:   .res 1                          ; page drawn this frame: 0 = 1, 1 = 2
sx:     .res 3                          ; screen x, y of the points
sy:     .res 3                          ; ($FF = out of view)
t0:     .res 1
t1:     .res 1
t2:     .res 1
t3:     .res 1
xa:     .res 1                          ; draw_pipe: the box xa..xb, ya..yb
xb:     .res 1
ya:     .res 1
yb:     .res 1
gk:     .res 1
pg:     .res 1                          ; new_screen: the page
srcp:   .res 2                          ; diff_row: the text now,
shp:    .res 2                          ; what the page shows,
dend:   .res 1                          ; the column after the last
gp:     .res 2                          ; fast_put: the glyph,
fp_y:   .res 1                          ; Y kept

.segment "BSS"
frames:    .res 2                       ; frames drawn (tests)
sh0:       .res 2 * 40                  ; per page: the HUD row shown
sh8:       .res 2 * 40                  ; per page: the message row shown
now:       .res 40                      ; the HUD row (draw_hud)
msg_pg:    .res 2                       ; message shown on each page
hud_pg:    .res 2                       ; HUD version shown on each page
hud_ver:   .res 1                       ; + 1 when a HUD number changes
msg:       .res 1
pump_hold: .res 1
lean_hold: .res 1
joy_ok:    .res 1
joy_cx:    .res 1
last_st:   .res 1
last_sc:   .res 2                       ; hp_score's low bytes last frame
air_px:    .res 1                       ; px above the lip, the last scored jump
jump_px:   .res 1                       ; px above the lip, the jump in progress
pace_ok:   .res 1                       ; a floating bus: vapor_pace
pace_add:  .res 2                       ; this tick's extra polls (sounds)

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
        BCS     :+
        INC     pace_ok
:       JSR     new_screen

restart:
        JSR     phys_reset
        LDA     #0
        STA     pump_hold
        STA     lean_hold
        STA     last_st
        STA     last_sc
        STA     last_sc+1
        STA     air_px
        STA     jump_px
        INC     hud_ver                 ; (score 0)
        LDA     #MSG_HELP
        STA     msg

main:   JSR     input                   ; (R: back to restart, ESC: quit)
        JSR     phys_tick
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
:       LDA     hp_status               ; a crash: a new run after a while
        BEQ     main
        LDA     hp_timer
        CMP     #AGAIN_T
        BCC     main
        BCS     restart

quit:   JMP     apple2_exit

; ---------------------------------------------------------------------------
; pace -- wait for line 191 of the tick's last video frame: vapor_pace with
; TICK_FRAMES and the tick's estimate (EST_AIR or EST_GND + pace_add, the
; sounds it played); unpaced without a floating bus
; ---------------------------------------------------------------------------
pace:   LDA     pace_ok
        BEQ     @rts
        LDX     #0                      ; a point on the pipe: EST_GND more
        LDA     vl_gnd
        ORA     vl_gnd+1
        ORA     vl_gnd+2
        BEQ     :+
        INX
:       CLC
        LDA     est_lo,X
        ADC     pace_add
        PHA
        LDA     est_hi,X
        ADC     pace_add+1
        TAY
        PLA
        TAX
        LDA     #0
        STA     pace_add
        STA     pace_add+1
        LDA     #TICK_FRAMES
        JMP     vapor_pace
@rts:   RTS

EST_AIR  = 16500                        ; a tick's cycles (main to pace): in the
EST_GND  = 21000                        ; air 13,500-19,500, on the pipe 15,900-28,300
est_lo:  .byte <(EST_AIR / 13), <(EST_GND / 13)
est_hi:  .byte >(EST_AIR / 13), >(EST_GND / 13)
; PACE_ADD cycles: pace_add += cycles / 13 (a sound)
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
CHIME_C  = TONE_CYC($30, $40) + TONE_CYC($40, $30) + TONE_CYC($60, $24)
AIR_C    = TONE_CYC($30, $50)

; ---------------------------------------------------------------------------
; input -- keys and joystick -> in_pump, in_lean for this tick
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
        BEQ     @pump
        CMP     #'I'
        BEQ     @pump
        CMP     #KC_UP
        BEQ     @pump
        CMP     #' '
        BEQ     @pump
        CMP     #'R'
        BEQ     @again
        CMP     #KC_ESC
        BEQ     quit
        BNE     @hold
@left:  LDA     #<-LEAN_HOLD
        BNE     @lean
@right: LDA     #LEAN_HOLD
@lean:  STA     lean_hold
        JMP     @hold
@pump:  LDA     #PUMP_HOLD
        STA     pump_hold
        BNE     @hold
@again: PLA                             ; (called from main)
        PLA
        JMP     restart
@hold:  LDA     #0
        STA     in_pump
        STA     in_lean
        LDA     pump_hold
        BEQ     @np
        DEC     pump_hold
        INC     in_pump
@np:    LDA     lean_hold
        BEQ     @joy
        BMI     @nl
        DEC     lean_hold
        LDA     #1
        STA     in_lean
        BNE     @joy
@nl:    INC     lean_hold
        LDA     #$FF
        STA     in_lean
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
        STA     in_lean
        BNE     @btn
@jl:    CMP     #<(-JOY_DEAD + 1)
        BCS     @btn
        LDA     #$FF
        STA     in_lean
@btn:   LDA     BUTN0
        BPL     @rts
        LDA     #1
        STA     in_pump
@rts:   RTS

; ---------------------------------------------------------------------------
; events -- a crash (message, growl), a landing that scored (message, chime),
; the air of the jump in progress
; ---------------------------------------------------------------------------
events: LDA     hp_status
        CMP     last_st
        BEQ     @same
        STA     last_st                 ; (only RIDE -> CRASHED in a run)
        LDA     #MSG_CRASH
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
@same:  LDA     hp_status
        BNE     @rts
        LDA     hp_air                  ; in the air: px above the lip
        BEQ     @land
        CMP     #1
        BNE     :+
        LDA     #0                      ; a new jump
        STA     jump_px
:       SEC
        LDA     #LIP_Y
        SBC     hp_peak
        BCC     @rts
        CMP     jump_px
        BCC     @rts
        STA     jump_px
@rts:   RTS
@land:  LDA     hp_score                ; the score moved: a landing
        LDX     hp_score+1
        CMP     last_sc
        BNE     :+
        CPX     last_sc+1
        BEQ     @rts
:       STA     last_sc
        STX     last_sc+1
        LDA     jump_px
        STA     air_px
        INC     hud_ver
        LDX     hp_spins
        BEQ     @air
        CPX     #4
        BCC     :+
        LDX     #3
:       TXA
        CLC
        ADC     #MSG_360 - 1
        STA     msg
        PACE_ADD CHIME_C
        LDA     #$30
        LDX     #$40
        JSR     tone
        LDA     #$40
        LDX     #$30
        JSR     tone
        LDA     #$60
        LDX     #$24
        JMP     tone
@air:   LDA     #MSG_AIR
        STA     msg
        PACE_ADD AIR_C
        LDA     #$30
        LDX     #$50
        JMP     tone

; ---------------------------------------------------------------------------
; new_screen -- both pages: cleared, the pipe, the HUD labels (the HUD
; digits and the message come with the next frames); no rider drawn yet
; ---------------------------------------------------------------------------
new_screen:
        JSR     clear_pages
        LDA     #1
        STA     pg
@page:  LDA     pg
        JSR     set_page
        LDA     #0
        STA     xa
        STA     ya
        LDA     #255
        STA     xb
        STA     yb
        JSR     draw_pipe
        LDA     #0
        STA     ht_col
        STA     ht_sl
        LDA     #<hud_label
        STA     ht_src_lo
        LDA     #>hud_label
        STA     ht_src_hi
        JSR     hgr_puts8
        LDX     pg
        LDA     #$FF
        STA     msg_pg,X                ; (the message and the HUD numbers
        STA     hud_pg,X                ; come with a frame)
        LDA     #0
        STA     pl_n,X
        DEC     pg
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
; render -- the hidden page: the old rider given back, the new one in, the
; HUD and the message characters that changed
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        JSR     pl_erase
        JSR     draw_rider
        LDX     pidx                    ; the HUD numbers, if they changed
        LDA     hud_ver
        CMP     hud_pg,X
        BEQ     :+
        STA     hud_pg,X
        JSR     draw_hud
:       LDX     pidx
        LDA     msg
        CMP     msg_pg,X
        BEQ     :+
        STA     msg_pg,X
        JSR     draw_msg
:       RTS

; A = 0 / 1: select the page for hgr_line8 (sites), hgr_text8 (ht_page),
; hgr_plot_hist (pl_page)
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

; ---------------------------------------------------------------------------
; draw_pipe -- the pipe segments crossing the box xa..xb, ya..yb on the
; selected page
; ---------------------------------------------------------------------------
draw_pipe:
        LDA     #NDRAW - 1
        STA     gk
@seg:   LDX     gk
        LDA     pipe_x0,X               ; t0..t1 = the segment's columns,
        LDY     pipe_x1,X               ; t2..t3 its rows
        CMP     pipe_x1,X
        BCC     :+
        TAY
        LDA     pipe_x1,X
:       STA     t0
        STY     t1
        LDA     pipe_y0,X
        LDY     pipe_y1,X
        CMP     pipe_y1,X
        BCC     :+
        TAY
        LDA     pipe_y1,X
:       STA     t2
        STY     t3
        LDA     t1                      ; overlap: t1 >= xa, xb >= t0,
        CMP     xa                      ; t3 >= ya, yb >= t2
        BCC     @next
        LDA     xb
        CMP     t0
        BCC     @next
        LDA     t3
        CMP     ya
        BCC     @next
        LDA     yb
        CMP     t2
        BCC     @next
        LDA     pipe_x0,X
        STA     hl_ln_x0
        LDA     pipe_y0,X
        STA     hl_ln_y0
        LDA     pipe_x1,X
        STA     hl_ln_x1
        LDA     pipe_y1,X
        STA     hl_ln_y1
        JSR     hgr_line8
@next:  DEC     gk
        BPL     @seg
        RTS

; ---------------------------------------------------------------------------
; draw_rider -- the rider (or its debris) on the selected page, recorded in
; its history for pl_erase two frames later
; ---------------------------------------------------------------------------
draw_rider:
        LDX     #2
:       JSR     scr_point
        DEX
        BPL     :-
        LDA     hp_status
        BNE     @wheels                 ; crashed: the three crosses alone
        LDX     #0                      ; the board, the legs
        LDY     #1
        JSR     line_ij
        LDX     #0
        LDY     #2
        JSR     line_ij
        LDX     #1
        LDY     #2
        JSR     line_ij
        LDX     #1                      ; the wheels (and the debris): crosses
        BNE     @d
@wheels:
        LDX     #2
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
        RTS

; X = point -> sx,X = its column, sy,X = its row ($FF: out of view)
scr_point:
        LDA     vl_xl,X
        STA     sx,X
        LDA     vl_xh,X
        BNE     @off
        LDA     vl_yh,X
        CMP     #HUD_ROWS
        BCC     @off
        CMP     #VIEW_LAST              ; (<= 189: a wheel's cross reaches
        BCS     @off                    ; one row below)
        STA     sy,X
        RTS
@off:   LDA     #$FF
        STA     sy,X
        RTS

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
; draw_hud -- the score (6 BCD digits), the last landing's points (4), the
; air of the last jump (px above the lip): written in now, then the
; characters the page does not show yet
; ---------------------------------------------------------------------------
draw_hud:
        LDA     #6
        STA     ht_col
        LDA     #<hp_score
        LDY     #>hp_score
        LDX     #3
        JSR     bcd_put
        LDA     #19
        STA     ht_col
        LDA     #<hp_last
        LDY     #>hp_last
        LDX     #2
        JSR     bcd_put
        LDA     air_px
        JSR     byte_to_dec             ; X hundreds, Y tens, A units
        ORA     #'0'
        STA     now+31
        TYA
        ORA     #'0'
        STA     now+30
        TXA
        ORA     #'0'
        STA     now+29
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
        LDY     #6
        LDA     #32

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

; bcd_put's output: A into now at ht_col (keeps X)
now_put:
        LDY     ht_col
        STA     now,Y
        INC     ht_col
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
hud_label:  .byte "SCORE 000000  LAST 0000  AIR 000"
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
m_help:     .byte "K/SPACE:PUMP  J L:LEAN  R:RESTART       ", 0
m_air:      .byte "AIR!                                    ", 0
m_360:      .byte "360!                                    ", 0
m_720:      .byte "720!!                                   ", 0
m_1080:     .byte "1080!!!                                 ", 0
m_crash:    .byte "CRASHED!                    R:RIDE AGAIN", 0
msg_lo:     .byte <m_help, <m_air, <m_360, <m_720, <m_1080, <m_crash
msg_hi:     .byte >m_help, >m_air, >m_360, >m_720, >m_1080, >m_crash
.assert m_air - m_help = 41 .and m_360 - m_air = 41 .and m_720 - m_360 = 41 .and m_1080 - m_720 = 41 .and m_crash - m_1080 = 41 .and msg_lo - m_crash = 41, error, "messages: 40 characters"
.segment "CODE"

.include "hgr_plot_hist.asm"            ; the routines referenced above
.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
.include "verlet_seg.asm"               ; lib/physics (physdefs.inc: verlet.inc)
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "mul.asm"
.include "bcd.asm"
.include "dec.asm"
.include "kbd.asm"
.include "joy.asm"
.include "hgr.asm"

; both HGR pages black ($2000-$5FFF): the HGR_CLEAR_LOOP macro over 8 groups,
; ~92,000 cycles, 79 bytes (after the include that defines the macro)
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
