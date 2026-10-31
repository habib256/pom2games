; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; catapult.s -- CATAPULT: knock six balls off their boxes, three shots
; ============================================================================
; The dev/lib/physics circle-contact demo (Apple II+ 48 KB, DOS 3.3, HGR).
; The physics is tools/catapult.py transcribed in phys.inc (tests/
; test_catapult.py: bit for bit); this file is the game around it: input,
; drawing, the text lines.
;
; Screen: rows 0-7 the counters, 8-15 the message, 16-191 the view (the
; world is the screen). The hill, the boxes and the catapult's post are
; drawn once on both pages; each frame draws the hidden page: what plot.inc
; lit two frames ago there goes out (the scenery under it comes back as it
; was), the arm, the balls and the aim mark go in, then the page is shown.
; Keys: J / <- and L / -> power, I and K the angle, space fires (and starts
; a new round when it is over), R a new round, ESC quits. A joystick (found
; at start): X the power, button 0 fires.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
PL_HIST    = $1800                      ; plot.inc's histories: 1.5 KB
SQRT_SEED  = $1E00                      ; isqrt16's seeds (256 B)
MUL_ACC    = 1
.include "math.inc"
.include "catconst.inc"
.include "physdefs.inc"
.include "hgr_pages.inc"
HGR_LINE_DIV7 = hgr_div7                ; (hgr_div7_ram.asm)
HGR_LINE_MOD7 = hgr_mod7
HGR_TEXT8_HGR_ORDER = 1

MSG_HELP  = 0
MSG_OVER  = 1
MSG_ALL   = 2

.segment "ZEROPAGE"
pidx:   .res 1                          ; page drawn this frame: 0 = 1, 1 = 2
t0:     .res 1
t1:     .res 1
gk:     .res 1
cx:     .res 1                          ; a circle's centre
cy:     .res 1

.segment "BSS"
frames:   .res 2                        ; frames drawn (tests)
hud_pg:   .res 8                        ; per page: power, angle, shots, score shown
msg_pg:   .res 2                        ; message shown on each page
msg:      .res 1
joy_ok:   .res 1
joy_cx:   .res 1
btn_was:  .res 1
numbuf:   .res 4

.segment "CODE"
        JMP     start
.include "hgr_text8.asm"                ; (its zero page before the callers)
.include "hgr_line.asm"
.include "plot.inc"
.include "phys.inc"

start:  APPLE2_PREAMBLE
        JSR     apple2_zp_save
        JSR     mul_init
        JSR     sqrt_init
        JSR     hgr_div7_init
        JSR     hgr_pages_init
        LDA     #0
        STA     ht_page
        STA     ht_cbit
        STA     ht_left
        STA     pidx
        STA     joy_ok
        STA     btn_was
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
        LDA     joy_x
        STA     joy_cx
        INC     joy_ok
:       JSR     clear_pages
        JSR     hgr_init

restart:
        JSR     phys_reset
        LDA     #0
        STA     in_fire
        STA     in_power
        STA     pl_n
        STA     pl_n+1
        LDA     #2
        STA     in_stop
        LDA     #MSG_HELP
        STA     msg
        JSR     clear_pages
        LDA     #1
        STA     t0
:       LDA     t0                      ; both pages: the scenery, the labels
        JSR     set_page
        JSR     scenery
        LDA     #0
        STA     ht_col
        STA     ht_sl
        LDA     #<m_label
        STA     ht_src_lo
        LDA     #>m_label
        STA     ht_src_hi
        JSR     hgr_puts8
        LDA     t0
        ASL     A
        ASL     A
        TAX
        LDA     #$FF
        STA     hud_pg,X
        STA     hud_pg+1,X
        STA     hud_pg+2,X
        STA     hud_pg+3,X
        LDX     t0
        STA     msg_pg,X
        DEC     t0
        BPL     :-

main:   JSR     input                   ; (R: back to restart, ESC: quit)
        JSR     phys_tick
        LDA     #0
        STA     in_fire
        JSR     events
        LDA     pidx                    ; draw the hidden page, show it
        EOR     #1
        STA     pidx
        JSR     render
        LDA     pidx
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
; input -- keys and joystick -> in_power, in_stop, in_fire (a new round
; when it is over)
; ---------------------------------------------------------------------------
input:  JSR     poll_key
        BEQ     @joy
        CMP     #'J'
        BEQ     @less
        CMP     #KC_LEFT
        BEQ     @less
        CMP     #'L'
        BEQ     @more
        CMP     #KC_RIGHT
        BEQ     @more
        CMP     #'I'
        BEQ     @up
        CMP     #KC_UP
        BEQ     @up
        CMP     #'K'
        BEQ     @down
        CMP     #KC_DOWN
        BEQ     @down
        CMP     #' '
        BEQ     @fire
        CMP     #'R'
        BEQ     @again
        CMP     #KC_ESC
        BEQ     quit
        BNE     @joy
@less:  LDA     in_power
        BEQ     @joy
        DEC     in_power
        BPL     @joy
@more:  LDA     in_power
        CMP     #PMAX
        BCS     @joy
        INC     in_power
        BNE     @joy
@up:    LDA     in_stop
        CMP     #NSTOP - 1
        BCS     @joy
        INC     in_stop
        BNE     @joy
@down:  LDA     in_stop
        BEQ     @joy
        DEC     in_stop
        JMP     @joy
@fire:  LDA     cp_phase
        CMP     #OVER
        BEQ     @again
        LDA     #1
        STA     in_fire
        BNE     @joy
@again: PLA                             ; (called from main)
        PLA
        JMP     restart
@joy:   LDA     joy_ok
        BEQ     @rts
        JSR     read_stick_fast         ; X deflected: power = (x - rest) / 2 + 8
        SEC
        LDA     joy_x
        SBC     joy_cx
        BVS     @btn
        CMP     #$80
        ROR     A
        CLC
        ADC     #8
        BPL     :+
        LDA     #0
:       CMP     #PMAX + 1
        BCC     :+
        LDA     #PMAX
:       STA     t0
        SEC
        LDA     joy_x
        SBC     joy_cx
        BPL     :+
        EOR     #$FF
        ADC     #1                      ; (C = 0)
:       CMP     #5
        BCC     @btn
        LDA     t0
        STA     in_power
@btn:   LDA     BUTN0                   ; button 0: a press fires
        AND     #$80
        CMP     btn_was
        BEQ     @rts
        STA     btn_was
        TAX
        BEQ     @rts
        LDA     cp_phase
        CMP     #OVER
        BEQ     @again
        LDA     #1
        STA     in_fire
@rts:   RTS

; ---------------------------------------------------------------------------
; events -- a click a contact tick, the message at the end of a round
; ---------------------------------------------------------------------------
events: LDA     cp_phase
        CMP     #FLY
        BNE     :+
        LDA     vl_chits
        BEQ     :+
        BIT     SPKR
:       LDX     #MSG_HELP
        LDA     cp_phase
        CMP     #OVER
        BNE     :+
        LDX     #MSG_OVER
        LDA     cp_score
        CMP     #6
        BNE     :+
        LDX     #MSG_ALL
:       STX     msg
        RTS

; both HGR pages black: 64 unrolled stores, ~84,000 cycles (5 a byte)
clear_pages:
        LDA     #0
        TAY
:
.repeat 64, I
        STA     $2000 + I * $100,Y
.endrepeat
        INY
        BEQ     :+
        JMP     :-
:       RTS

; A = 0 / 1: the page for hgr_line8 (sites), hgr_text8 (ht_page), plot.inc
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

; the hill (segments of 4 px), the boxes (outlines), the catapult's post
scenery:
        LDA     #0
        STA     gk
@seg:   LDX     gk
        LDA     heights,X
        STA     hl_ln_y0
        STX     hl_ln_x0
        TXA
        CLC
        ADC     #4
        BCC     :+
        LDA     #255
:       STA     hl_ln_x1
        TAX
        LDA     heights,X
        STA     hl_ln_y1
        JSR     hgr_line8
        LDA     gk
        CLC
        ADC     #4
        BCS     @box
        STA     gk
        BCC     @seg
@box:   LDX     #NBOX - 1
@b:     STX     gk
        LDA     vl_box_x0,X             ; top, bottom
        STA     hl_ln_x0
        LDA     vl_box_x1,X
        STA     hl_ln_x1
        LDA     vl_box_y0,X
        STA     hl_ln_y0
        STA     hl_ln_y1
        JSR     hgr_line8
        LDX     gk
        LDA     vl_box_x0,X
        STA     hl_ln_x0
        LDA     vl_box_x1,X
        STA     hl_ln_x1
        LDA     vl_box_y1,X
        STA     hl_ln_y0
        STA     hl_ln_y1
        JSR     hgr_line8
        LDX     gk                      ; left, right
        LDA     vl_box_x0,X
        STA     hl_ln_x0
        STA     hl_ln_x1
        LDA     vl_box_y0,X
        STA     hl_ln_y0
        LDA     vl_box_y1,X
        STA     hl_ln_y1
        JSR     hgr_line8
        LDX     gk
        LDA     vl_box_x1,X
        STA     hl_ln_x0
        STA     hl_ln_x1
        LDA     vl_box_y0,X
        STA     hl_ln_y0
        LDA     vl_box_y1,X
        STA     hl_ln_y1
        JSR     hgr_line8
        LDX     gk
        DEX
        BPL     @b
        LDA     #BASE_X                 ; the post: base to the ground
        STA     hl_ln_x0
        STA     hl_ln_x1
        LDA     #BASE_Y + 2
        STA     hl_ln_y0
        LDX     #BASE_X
        LDA     heights,X
        STA     hl_ln_y1
        JMP     hgr_line8

; ---------------------------------------------------------------------------
; render -- the hidden page: what was lit out, the arm and the balls in,
; the counters and the message when they changed
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        JSR     pl_erase
        LDA     vl_xl+BASE              ; the arm
        STA     pl_x0
        LDA     vl_yh+BASE
        STA     pl_y0
        LDA     vl_xl+TIP
        STA     pl_x1
        LDA     vl_yh+TIP
        STA     pl_y1
        JSR     pl_line
        LDX     #VL_CIRC - 1            ; the balls (the projectile: in the
@c:     STX     gk                      ; cup while it is aimed)
        LDA     vl_xl,X
        STA     cx
        LDA     vl_yh,X
        STA     cy
        JSR     ring
        LDX     gk
        DEX
        BPL     @c
        LDA     cp_phase                ; aiming: the mark
        BNE     @hud
        LDX     cp_stop
        CLC
        LDA     vl_xl+PROJ
        STA     pl_x0
        ADC     aim_dx,X
        STA     pl_x1
        CLC
        LDA     vl_yh+PROJ
        STA     pl_y0
        ADC     aim_dy,X
        STA     pl_y1
        JSR     pl_line
@hud:   JSR     draw_hud
        LDX     pidx
        LDA     msg
        CMP     msg_pg,X
        BEQ     :+
        STA     msg_pg,X
        JSR     draw_msg
:       RTS

; a ring of radius RADPX round cx, cy (clipped to the view)
ring:   LDY     #NRING - 1
@p:     STY     t1
        CLC
        LDA     cx
        ADC     ring_dx,Y
        STA     pl_x
        CLC
        LDA     cy
        ADC     ring_dy,Y
        CMP     #16
        BCC     @n
        CMP     #192
        BCS     @n
        STA     pl_y
        JSR     pl_plot
@n:     LDY     t1
        DEY
        BPL     @p
        RTS

; the counters that changed on this page: power, angle, shots, down
draw_hud:
        LDA     #0
        STA     ht_sl
        LDA     pidx
        ASL     A
        ASL     A
        STA     t1
        LDX     t1                      ; power 0..15
        LDA     cp_power
        CMP     hud_pg,X
        BEQ     :+
        STA     hud_pg,X
        LDY     #6
        JSR     put2
:       LDX     t1                      ; angle (degrees)
        LDY     cp_stop
        LDA     stop_deg,Y
        CMP     hud_pg+1,X
        BEQ     :+
        STA     hud_pg+1,X
        LDY     #16
        JSR     put2
:       LDX     t1                      ; shots left
        LDA     cp_shots
        CMP     hud_pg+2,X
        BEQ     :+
        STA     hud_pg+2,X
        LDY     #26
        JSR     put2
:       LDX     t1                      ; down
        LDA     cp_score
        CMP     hud_pg+3,X
        BEQ     :+
        STA     hud_pg+3,X
        LDY     #35
        JSR     put2
:       RTS

; A (0..99) as two digits at column Y, row 0
put2:   STY     ht_col
        JSR     byte_to_dec             ; Y tens, A units
        PHA
        TYA
        ORA     #'0'
        JSR     hgr_putc8
        PLA
        ORA     #'0'
        JMP     hgr_putc8

; the message line (row 8) on the selected page
draw_msg:
        LDA     #0
        STA     ht_col
        LDA     #8
        STA     ht_sl
        LDX     msg
        LDA     msg_lo,X
        STA     ht_src_lo
        LDA     msg_hi,X
        STA     ht_src_hi
        JMP     hgr_puts8

.segment "RODATA"
m_label:    .byte "POWER     ANGLE     SHOTS     DOWN   /6", 0
m_help:     .byte "J L:POWER  I K:ANGLE  SPACE:FIRE  R:NEW ", 0
m_over:     .byte "ROUND OVER         SPACE:AGAIN          ", 0
m_all:      .byte "ALL SIX DOWN!      SPACE:AGAIN          ", 0
msg_lo:     .byte <m_help, <m_over, <m_all
msg_hi:     .byte >m_help, >m_over, >m_all
.segment "CODE"

.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
.include "verlet_circ.asm"              ; lib/physics (physdefs.inc: verlet.inc)
.include "verlet_hmap.asm"
.include "verlet_con.asm"
.include "verlet_rot.asm"
.include "verlet.asm"
.include "sqrt.asm"
.include "mul.asm"
.include "dec.asm"
.include "kbd.asm"
.include "joy.asm"
.include "hgr.asm"
.include "exit.asm"
.include "hgr_div7_ram.asm"
.segment "RODATA"
.include "bbfont.inc"
.include "hgr_scanline.inc"
