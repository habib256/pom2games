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
; an edge selects the next one and both pages are drawn again.
; Two pages: each frame draws the hidden one and shows it. On that page
; the lander of two frames ago is wiped (its box of bytes cleared, then the
; ground segments under the box drawn again), the new one drawn (lines,
; hgr_line8), the HUD digits rewritten: only what changes.
; Keys: J / <- and L / -> turn, K / I / up the engine (a key press runs it
; THR_HOLD ticks: the II+ keyboard has no key-up, its repeat keeps it on),
; space cuts, R restarts, ESC quits. A joystick (found at start): X turns,
; button 0 is the engine.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
MUL_ACC    = 1
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
ROT_HOLD  = 8                           ; ticks a key turns
THR_HOLD  = 20                          ; ticks a key fires the engine
JOY_DEAD  = 12
.assert (ZONES - 1) * ZSTEP + VIEW_H = WORLD_H, error, "zones: cover the world exactly"

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
gptr:   .res 2
xa:     .res 1                          ; draw_ground: columns xa..xb
xb:     .res 1
gk:     .res 1
gy0:    .res 1
gy1:    .res 1
bx0:    .res 1                          ; the box of what draw_lander drew
bx1:    .res 1
by0:    .res 1
by1:    .res 1

.segment "BSS"
frames:   .res 2                        ; frames drawn (tests)
bb_r0:    .res 2                        ; per page: the lander's box, rows
bb_r1:    .res 2                        ; ($FF: nothing drawn) and byte
bb_c0:    .res 2                        ; columns
bb_c1:    .res 2
msg_pg:   .res 2                        ; message shown on each page
msg:      .res 1
thr_hold: .res 1
rot_hold: .res 1
joy_ok:   .res 1
joy_cx:   .res 1
burn:     .res 1                        ; the engine fired this tick
last_st:  .res 1
numbuf:   .res 6

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
        JSR     read_stick_fast
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
        LDA     #$40
        LDX     #$50
        JSR     tone
        LDA     #$60
        LDX     #$38
        JMP     tone
@crash: LDA     #MSG_CRASH
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
        JMP     new_screen
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
        JMP     new_screen
@rts:   RTS

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
; new_screen -- both pages: cleared, the ground, the HUD labels and the
; message (the HUD digits come with the next frames); no lander drawn yet
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
        JSR     draw_msg
        LDX     t3
        LDA     msg
        STA     msg_pg,X
        LDA     #$FF
        STA     bb_r0,X
        DEC     t3
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
; render -- the hidden page: the old lander out, the new one in, the HUD
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        LDX     pidx
        LDA     bb_r0,X
        CMP     #$FF
        BEQ     :+
        JSR     erase_box
:       JSR     draw_lander
        JSR     draw_hud
        LDX     pidx
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

; X = page: clear its lander box, then draw the ground under it again
erase_box:
        LDA     bb_c0,X
        STA     t0
        LDA     bb_c1,X
        STA     t1
        LDA     bb_r1,X
        STA     t2
        LDA     bb_r0,X
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
        JMP     draw_ground

mul7:   STA     t3
        ASL     A
        ASL     A
        ASL     A
        SEC
        SBC     t3
        RTS

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
        CPX     #192
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
        CPY     #192
        BCS     @off
        TYA
        RTS
@off:   LDA     #$FF
        RTS

; ---------------------------------------------------------------------------
; draw_lander -- the lander (or its debris) on the selected page; its box
; for erase_box two frames later
; ---------------------------------------------------------------------------
draw_lander:
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
        BEQ     @box
        JSR     flame
        LDX     #4
        LDY     #3
        JSR     line_ij
        JMP     @box
@debris:
        LDX     #2                      ; each point a small cross
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
@box:   LDX     pidx                    ; the box, in byte columns
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
        CMP     #192
        BCS     @off
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
        CMP     #192
        BCS     @rts
        STA     sy+3
@rts:   RTS

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
; draw_hud -- altitude (rows from the legs' discs to the ground under the
; middle),
; vertical speed (1/16 px a tick, + down), fuel
; ---------------------------------------------------------------------------
draw_hud:
        LDA     #0
        STA     ht_sl
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
:       LDA     #4
        STA     ht_col
        LDA     #<numbuf
        STA     dec_ptr
        LDA     #>numbuf
        STA     dec_ptr+1
        JSR     u16_to_dec              ; Y = digits
        LDA     #' '
:       CPY     #3
        BCS     :+
        JSR     hgr_putc8
        INY
        BNE     :-
:       LDX     #0
:       LDA     numbuf,X
        BEQ     :+
        JSR     hgr_putc8
        INX
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
:       STA     t0
        LDA     #12
        STA     ht_col
        TXA
        JSR     hgr_putc8
        LDA     t0
        JSR     byte_to_dec             ; Y tens, A units
        PHA
        TYA
        ORA     #'0'
        JSR     hgr_putc8
        PLA
        ORA     #'0'
        JSR     hgr_putc8
        LDA     #22                     ; fuel
        STA     ht_col
        LDA     lv_fuel
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
zone_lo:  .repeat ZONES, I
          .byte <(I * ZSTEP)
          .endrepeat
zone_hi:  .repeat ZONES, I
          .byte >(I * ZSTEP)
          .endrepeat
hud_label:  .byte "ALT      VS      FUEL", 0
m_help:     .byte "J L:TURN  K:ENGINE  SPACE:CUT  R:RESTART", 0
m_pad_a:    .byte "LANDED ON PAD A!          R:FLY AGAIN   ", 0
m_pad_b:    .byte "LANDED ON PAD B!          R:FLY AGAIN   ", 0
m_pad_c:    .byte "LANDED ON PAD C!          R:FLY AGAIN   ", 0
m_crash:    .byte "CRASHED!                  R:FLY AGAIN   ", 0
m_fuel:     .byte "OUT OF FUEL!                            ", 0
msg_lo:     .byte <m_help, <m_pad_a, <m_pad_b, <m_pad_c, <m_crash, <m_fuel
msg_hi:     .byte >m_help, >m_pad_a, >m_pad_b, >m_pad_c, >m_crash, >m_fuel
.segment "CODE"

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
.include "exit.asm"
.include "hgr_div7_ram.asm"
.segment "RODATA"
.include "bbfont.inc"
.include "hgr_scanline.inc"
