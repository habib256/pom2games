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
; Two pages: each frame draws the hidden one and shows it. On that page
; the rider of two frames ago is wiped (its box of bytes cleared, then the
; pipe segments crossing the box drawn again), the new one drawn (lines,
; hgr_line8), the HUD digits rewritten when they changed: only what
; changes.
; Keys: K / I / up / space pump (a press pumps PUMP_HOLD ticks: the II+
; keyboard has no key-up, its repeat keeps it on), J / <- and L / -> lean
; (LEAN_HOLD ticks a press), R restarts, ESC quits. A joystick (found at
; start): X leans, button 0 pumps. After a crash, a new run starts by
; itself after AGAIN_T ticks.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
MUL_ACC    = 1
.include "math.inc"
.include "pipeconst.inc"
.include "physdefs.inc"
.include "hgr_pages.inc"
HGR_LINE_DIV7 = hgr_div7                ; (hgr_div7_ram.asm)
HGR_LINE_MOD7 = hgr_mod7
HGR_TEXT8_HGR_ORDER = 1
BCD_PUT_OUT = hgr_putc8                 ; (bcd.asm: the score's digits)

HUD_ROWS  = 16                          ; the pipe starts at row 16
PUMP_HOLD = 16                          ; ticks a key pumps
LEAN_HOLD = 6                           ; ticks a key leans
AGAIN_T   = 110                         ; ticks after a crash: a new run
JOY_DEAD  = 12

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
gptr:   .res 2
xa:     .res 1                          ; draw_pipe: the box xa..xb, ya..yb
xb:     .res 1
ya:     .res 1
yb:     .res 1
gk:     .res 1
pg:     .res 1                          ; new_screen: the page
bx0:    .res 1                          ; the box of what draw_rider drew
bx1:    .res 1
by0:    .res 1
by1:    .res 1

.segment "BSS"
frames:    .res 2                       ; frames drawn (tests)
bb_r0:     .res 2                       ; per page: the rider's box, rows
bb_r1:     .res 2                       ; ($FF: nothing drawn) and byte
bb_c0:     .res 2                       ; columns
bb_c1:     .res 2
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

.segment "CODE"
        JMP     start
.include "sound.asm"                    ; first: its loops never cross a page
.include "hgr_text8.asm"                ; (its zero page before the callers)
.include "hgr_line.asm"
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
        JSR     new_screen

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
        LDA     pidx
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
        JSR     read_stick_fast
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
        LDA     #$30
        LDX     #$50
        JMP     tone

; ---------------------------------------------------------------------------
; new_screen -- both pages: cleared, the pipe, the HUD labels and the
; message (the HUD digits come with the next frames); no rider drawn yet
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
        STA     bb_r0,X
        DEC     pg
        BPL     @page
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

; ---------------------------------------------------------------------------
; render -- the hidden page: the old rider out, the new one in, the HUD
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        LDX     pidx
        LDA     bb_r0,X
        CMP     #$FF
        BEQ     :+
        JSR     erase_box
:       JSR     draw_rider
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

; A = 0 / 1: select the page for hgr_line8 (sites) and hgr_text8 (ht_page)
set_page:
        PHA
        JSR     hgr_select_page
        PLA
        BEQ     :+
        LDA     #$60
:       STA     ht_page
        RTS

; X = page: clear its rider box, then draw the pipe under it again
erase_box:
        LDA     bb_c0,X
        STA     t0
        LDA     bb_c1,X
        STA     t1
        LDA     bb_r1,X
        STA     t2
        STA     yb
        LDA     bb_r0,X
        STA     ya
        TAX
:       LDA     hgr_lo,X
        STA     gptr
        HGR_LDA_HI_X
        STA     gptr+1
        LDY     t0
        LDA     #0
:       STA     (gptr),Y
        INY
        CPY     t1
        BCC     :-
        BEQ     :-
        INX
        CPX     t2
        BCC     :--
        BEQ     :--
        LDA     t0                      ; columns 7 c0 .. 7 c1 + 6
        JSR     mul7
        STA     xa
        LDA     t1
        JSR     mul7
        CLC
        ADC     #6
        BCC     :+
        LDA     #255
:       STA     xb
        JMP     draw_pipe

mul7:   STA     t3
        ASL     A
        ASL     A
        ASL     A
        SEC
        SBC     t3
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
; draw_rider -- the rider (or its debris) on the selected page; its box for
; erase_box two frames later
; ---------------------------------------------------------------------------
draw_rider:
        LDA     #255
        STA     bx0
        STA     by0
        LDA     #0
        STA     bx1
        STA     by1
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
        STX     gk
        LDY     sx,X
        BEQ     @v
        CPY     #255
        BEQ     @v
        STA     hl_ln_y0
        STA     hl_ln_y1
        DEY
        STY     hl_ln_x0
        INY
        INY
        STY     hl_ln_x1
        JSR     seg
        LDX     gk
@v:     LDA     sy,X
        CMP     #HUD_ROWS + 1
        BCC     @dn1
        CMP     #191
        BCS     @dn1
        TAY
        DEY
        STY     hl_ln_y0
        INY
        INY
        STY     hl_ln_y1
        LDA     sx,X
        STA     hl_ln_x0
        STA     hl_ln_x1
        JSR     seg
@dn1:   LDX     gk
@dn:    DEX
        BPL     @d
        LDX     pidx                    ; the box, in byte columns
        LDA     bx1
        CMP     bx0
        BCS     :+
        LDA     #$FF                    ; nothing drawn
        STA     bb_r0,X
        RTS
:       LDA     by0
        STA     bb_r0,X
        LDA     by1
        STA     bb_r1,X
        LDY     bx0
        LDA     hgr_div7,Y
        STA     bb_c0,X
        LDY     bx1
        LDA     hgr_div7,Y
        STA     bb_c1,X
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
        CMP     #192
        BCS     @off
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
        STA     hl_ln_y0
        LDA     sy,Y
        CMP     #$FF
        BEQ     @rts
        STA     hl_ln_y1
        LDA     sx,X
        STA     hl_ln_x0
        LDA     sx,Y
        STA     hl_ln_x1
        JMP     seg
@rts:   RTS

; draw hl_ln_x0,y0 - x1,y1 and grow the box
seg:    LDA     hl_ln_x0
        JSR     ext_x
        LDA     hl_ln_x1
        JSR     ext_x
        LDA     hl_ln_y0
        JSR     ext_y
        LDA     hl_ln_y1
        JSR     ext_y
        JMP     hgr_line8
ext_x:  CMP     bx0
        BCS     :+
        STA     bx0
:       CMP     bx1
        BCC     :+
        STA     bx1
:       RTS
ext_y:  CMP     by0
        BCS     :+
        STA     by0
:       CMP     by1
        BCC     :+
        STA     by1
:       RTS

; ---------------------------------------------------------------------------
; draw_hud -- the score (6 BCD digits), the last landing's points (4), the
; air of the last jump (px above the lip)
; ---------------------------------------------------------------------------
draw_hud:
        LDA     #0
        STA     ht_sl
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
        LDA     #29
        STA     ht_col
        LDA     air_px
        JSR     byte_to_dec             ; X hundreds, Y tens, A units
        PHA
        TXA
        ORA     #'0'
        JSR     hgr_putc8
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
hud_label:  .byte "SCORE 000000  LAST 0000  AIR 000", 0
m_help:     .byte "K/SPACE:PUMP  J L:LEAN  R:RESTART       ", 0
m_air:      .byte "AIR!                                    ", 0
m_360:      .byte "360!                                    ", 0
m_720:      .byte "720!!                                   ", 0
m_1080:     .byte "1080!!!                                 ", 0
m_crash:    .byte "CRASHED!                    R:RIDE AGAIN", 0
msg_lo:     .byte <m_help, <m_air, <m_360, <m_720, <m_1080, <m_crash
msg_hi:     .byte >m_help, >m_air, >m_360, >m_720, >m_1080, >m_crash
.segment "CODE"

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
.include "exit.asm"
.include "hgr_div7_ram.asm"
.segment "RODATA"
.include "bbfont.inc"
.include "hgr_scanline.inc"
