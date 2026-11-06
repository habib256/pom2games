; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; rope.s -- ROPE: a pinned Verlet rope with a weight, a floor to drop it on
; ============================================================================
; The dev/lib/physics rope toy (Apple II+ 48 KB, DOS 3.3, HGR). The physics
; is tools/rope.py transcribed in phys.inc (tests/test_rope.py: bit for
; bit); this file is the toy around it: input, drawing, the text lines.
;
; Screen: rows 0-7 the keys, 8-15 the mode, 16-191 the view (the world is
; the screen: y 8.8 rows). The floor is drawn once on both pages; each
; tick draws the hidden page: what hgr_plot_hist.asm lit two ticks ago
; there goes out (the floor under it comes back as it was), the rope and the
; pin (its fast lines) and the weight (a preshifted 5 x 5 sprite) go in, and
; the page is shown in the vertical blank (vapor.asm: the beam found
; through the floating bus, a marker on row 191 of both pages; nothing is
; drawn below row 190), a tick every TICK_FRAMES video frames (20 a
; second: vapor_pace, given an estimate of the tick's cycles); without a
; floating bus (//c, IIgs) it runs unpaced.
; Keys: J / <- and L / -> move the pin (a press moves it MV_HOLD ticks: the
; II+ keyboard has no key-up, its repeat keeps it going), M swing / floor,
; space cuts the weight off or puts it back, R resets, ESC quits. A
; joystick (found at start): X places the pin, button 0 cuts.
; ============================================================================

.include "apple2.inc"
MUL_TABLES = $1000                      ; LOWBSS: 2 KB, page aligned
PL_HIST    = $1800                      ; hgr_plot_hist.asm's histories: 1.5 KB
HGR_PLOT_HIST_FAST = 1                  ; lines stepped by byte, pl_sprite
MUL_ACC    = 1
mul_y = mul_s1l                 ; operand is also the first table pointer low byte
.include "math.inc"
.include "ropeconst.inc"
.include "physdefs.inc"
.include "hgr_pages.inc"
HGR_LINE_DIV7 = hgr_div7                ; (hgr_div7_ram.asm)
HGR_LINE_MOD7 = hgr_mod7
HGR_TEXT8_HGR_ORDER = 1

MV_HOLD   = 6                           ; ticks a key moves the pin
VIEW_LAST = 190                         ; the last row drawn (191: the vapor marker;
                                        ; the rope's points stay above the floor, <= 186)
JOY_DEAD  = 13                          ; read_stick_x counts (PREAD: 0..255;
                                        ; 4 on the former read_stick_fast)

.segment "ZEROPAGE"
pidx:   .res 1                          ; page drawn this frame: 0 = 1, 1 = 2
t0:     .res 1
gk:     .res 1

.segment "BSS"
frames:   .res 2                        ; frames drawn (tests)
msg_pg:   .res 2                        ; status shown on each page ($FF: none)
mv_hold:  .res 1
joy_ok:   .res 1
joy_cx:   .res 1                        ; the stick's rest position
btn_was:  .res 1
pace_ok:  .res 1                        ; a floating bus: vapor_pace

.segment "CODE"
        JMP     start
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
        STA     btn_was
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
        JSR     phys_reset
        LDA     #0
        STA     mv_hold
        STA     in_mv
        STA     in_mode
        STA     in_cut
        STA     pl_n
        STA     pl_n+1
        JSR     clear_pages
        LDA     #1
        STA     t0
:       LDA     t0                      ; both pages: floor, keys
        JSR     set_page
        JSR     draw_floor
        LDA     #0
        STA     ht_col
        STA     ht_sl
        LDA     #<m_keys
        STA     ht_src_lo
        LDA     #>m_keys
        STA     ht_src_hi
        JSR     hgr_puts8
        LDX     t0
        LDA     #$FF
        STA     msg_pg,X
        DEC     t0
        BPL     :-

main:   JSR     input                   ; (R: back to restart, ESC: quit)
        JSR     phys_tick
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
; TICK_FRAMES and the tick's estimate (by rp_mode); unpaced without a
; floating bus
; ---------------------------------------------------------------------------
pace:   LDA     pace_ok
        BEQ     @rts
        LDX     rp_mode
        LDY     est_hi,X
        LDA     est_lo,X
        TAX
        LDA     #TICK_FRAMES
        JMP     vapor_pace
@rts:   RTS

EST_SWING = 34000                       ; a tick's cycles (main to pace):
EST_FLOOR = 41000                       ; swinging 33,500, floor 39,900-45,700
est_lo:   .byte <(EST_SWING / 13), <(EST_FLOOR / 13)
est_hi:   .byte >(EST_SWING / 13), >(EST_FLOOR / 13)

; ---------------------------------------------------------------------------
; input -- keys and joystick -> in_mv, in_mode, in_cut
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
        CMP     #'M'
        BEQ     @mode
        CMP     #' '
        BEQ     @cut
        CMP     #'R'
        BEQ     @again
        CMP     #KC_ESC
        BEQ     quit
        BNE     @hold
@left:  LDA     #<-MV_HOLD
        BNE     @mv
@right: LDA     #MV_HOLD
@mv:    STA     mv_hold
        JMP     @hold
@mode:  LDA     in_mode
        EOR     #1
        STA     in_mode
        JMP     @hold
@cut:   LDA     in_cut
        EOR     #1
        STA     in_cut
        JMP     @hold
@again: PLA                             ; (called from main)
        PLA
        JMP     restart
@hold:  LDA     #0
        STA     in_mv
        LDA     mv_hold
        BEQ     @joy
        BMI     @nl
        DEC     mv_hold
        LDA     #1
        STA     in_mv
        BNE     @joy
@nl:    INC     mv_hold
        LDA     #$FF
        STA     in_mv
@joy:   LDA     joy_ok
        BEQ     @rts
        JSR     read_stick_x            ; deflected: the pin goes toward
        SEC                             ; 128 + (x - the rest position)
        LDA     joy_x                   ; (PREAD scale: 3.2 times the former
        SBC     joy_cx                  ; read_stick_fast counts, which went
        BVS     @btn                    ; x 3)
        STA     t0
        BPL     :+
        EOR     #$FF
        ADC     #1                      ; (C = 0)
:       CMP     #JOY_DEAD + 1
        BCC     @btn
        LDA     t0
        EOR     #$80                    ; + 128 (signed -> unsigned)
        CMP     #PIN_X0
        BCS     :+
        LDA     #PIN_X0
:       CMP     #PIN_X1
        BCC     :+
        LDA     #PIN_X1
:       SEC
        SBC     rp_px
        BEQ     @btn
        BCS     @jr
        LDA     #$FF
        STA     in_mv
        BNE     @btn
@jr:    LDA     #1
        STA     in_mv
@btn:   LDA     BUTN0                   ; button 0: a press cuts / puts back
        AND     #$80
        CMP     btn_was
        BEQ     @rts
        STA     btn_was
        TAX
        BEQ     @rts
        LDA     in_cut
        EOR     #1
        STA     in_cut
@rts:   RTS


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

; the floor: segments of 4 px, columns 0..255
draw_floor:
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
        BCS     @rts
        STA     gk
        BCC     @seg
@rts:   RTS

; ---------------------------------------------------------------------------
; render -- the hidden page: what was lit out, the rope in, the status
; ---------------------------------------------------------------------------
render: LDA     pidx
        JSR     set_page
        JSR     pl_erase
        LDX     #0                      ; the rope: points 0..7
@r:     STX     gk
        LDA     vl_xl,X
        STA     pl_x0
        LDA     vl_yh,X
        STA     pl_y0
        LDA     vl_xl+1,X
        STA     pl_x1
        LDA     vl_yh+1,X
        STA     pl_y1
        CPX     #7                      ; the last link, unless cut
        BNE     :+
        LDA     rp_cut
        BNE     @pin
:       JSR     pl_line
        LDX     gk
        INX
        CPX     #8
        BNE     @r
@pin:   LDA     vl_xl                   ; the pin: a bar of 7 px
        SEC
        SBC     #3
        STA     pl_x0
        CLC
        ADC     #6
        STA     pl_x1
        LDA     vl_yh
        SEC
        SBC     #1
        STA     pl_y0
        STA     pl_y1
        JSR     pl_line
        LDA     vl_xl+8                 ; the weight: a 5 x 5 square
        SEC                             ; (its left edge clipped at x 0)
        SBC     #2
        BCS     :+
        LDA     #0
:       STA     pl_x
        LDA     vl_yh+8
        SEC
        SBC     #2
        CMP     #VIEW_LAST - 4 + 1      ; (its 5 rows above row 191; the
        BCC     :+                      ; floor keeps it higher anyway)
        LDA     #VIEW_LAST - 4
:       STA     pl_y
        LDA     #<weight_desc
        STA     pl_sp
        LDA     #>weight_desc
        STA     pl_sp+1
        JSR     pl_sprite
        LDA     rp_mode                 ; the status line, when it changed
        ASL     A
        ORA     rp_cut
        LDX     pidx
        CMP     msg_pg,X
        BEQ     @rts
        STA     msg_pg,X
        TAX
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

.segment "RODATA"
m_keys:     .byte "J L:PIN  M:FLOOR  SPACE:CUT  R:RESET", 0
m_swing:    .byte "SWING                ", 0
m_swcut:    .byte "SWING - WEIGHT CUT   ", 0
m_floor:    .byte "FLOOR                ", 0
m_flcut:    .byte "FLOOR - WEIGHT CUT   ", 0
msg_lo:     .byte <m_swing, <m_swcut, <m_floor, <m_flcut
msg_hi:     .byte >m_swing, >m_swcut, >m_floor, >m_flcut
weight_desc: .byte 2, 5                 ; pl_sprite: 2 bytes x 5 rows
            .repeat 7, I
            .addr weight_spr + I * 10
            .endrepeat
weight_spr: .repeat 7, I                ; 5 pixels from bit I
            .repeat 5
            .byte ($1F << I) & $7F, ($1F << I) >> 7
            .endrepeat
            .endrepeat
.segment "CODE"

.include "hgr_plot_hist.asm"            ; the routines referenced above
.include "hgr_pages.asm"                ; after the last HGR_HI_SITE
.include "verlet_hmap.asm"              ; lib/physics (physdefs.inc: verlet.inc)
.include "verlet_con.asm"
.include "verlet.asm"
.include "mul.asm"
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
.include "vapor.asm"
.include "exit.asm"
.include "hgr_div7_ram.asm"
.segment "RODATA"
.include "bbfont.inc"
.include "hgr_scanline.inc"
