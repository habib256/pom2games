; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; video_x2.asm -- ROGUE.DHGR's game view, the X2 way (POM1's ROGUE X2)
; ============================================================================
; Included by video_dhgr.asm. The playfield of the virtual TMS9918 screen
; (name rows 0..19 + the sprites above row 20) drawn at x2 in big colour
; cells: a 9 x 5 window of 14 x 32 cells (lines 0..159, colour pixels
; 7..132 = groups 1..18), CENTRE-LOCKED on the hero (cell 4, 2); the window
; hangs past the map edges (black cells there). tools/x2_dhgr.py: the art,
; the palette, the model (render_screen) the tests hold this code to.
;
;   x2_frame    the wanted frame from the virtual screen: the camera (sprite
;               0 when it is the hero: the hero's cell - (4, 2), else the
;               last one), then 45 keys (tile = top-left name / 4; front and
;               back sprite = name / 4 + 1, + $40 for a hit: colour 8, not
;               the boss), from the sprite entries on the 16-pixel grid above
;               row 20, the two first of each cell (entry 0 in front);
;   x2_idle     double buffering: the frame goes to the HIDDEN page (only
;               the cells whose key differs from what that page shows, then
;               its HUD rows by the text engine), then the page is shown at
;               the next vertical blank (//e: $C019; //c: at once). When the
;               page shown already has the frame (the core's second vid_idle
;               of a turn, from wait_key, after the sound), the hidden page
;               catches up instead, without a flip (stopped by a key: the
;               turn comes first): the next turn draws on a page one frame
;               old, i.e. only what this turn changed;
;   x2_cell     a cell: its tile picture, or the tile + its sprites composed
;               in x2_cbuf (b = b XOR ((b XOR ink) AND dots)), written to the
;               page: 8 byte columns x 32 lines, each source row twice
;               (x2_w: 16 x LDA / STA / STA, ~14 cycles a row), aux columns
;               then main ones, IRQs masked during the aux ones.
;
; A cell picture (x2_timg + 128 t, x2_cbuf) = 8 stream bytes x 16 rows,
; byte k of row r at 16 k + r (k even: aux byte k/2 of the cell's 4 a line,
; k odd: main); its 32 lines = rows 0,0,1,1 ... Every byte of the window is
; written at most once an update, with its final value.
; ============================================================================

X2_W     = 9                    ; window, cells
X2_H     = 5
X2_BOSS0 = 14                   ; the boss's first quarter (name 56 / 4)

.segment "ZEROPAGE"
x2_np:    .res 2                ; names row / tile picture pointer
x2_bp0:   .res 2                ; x2_overlay: left halves of the 16 rows
x2_bp1:   .res 2                ; right halves
x2_ink:   .res 4                ; the ink in bytes j = 0..3 of a group
x2_i:     .res 1                ; cell 0..44
x2_vr:    .res 1                ; its window row, column
x2_vc:    .res 1
x2_mc:    .res 1                ; map column / scratch
x2_n:     .res 1                ; counter
x2_pg:    .res 1                ; the page drawn
x2_cur:   .res 1                ; bit 7: the page shown has the frame
x2_x:     .res 1                ; screen byte of a cell's first column
x2_off:   .res 1                ; its picture: low byte (x2_src: high)
x2_src:   .res 1                ; the page x2_w's loads point at
x2_ko:    .res 1                ; 45 * page: its keys
x2_tv:    .res 1
x2_tw:    .res 1
x2_code:  .res 1

.segment "X2LOW"                ; page aligned, rogue_dhgr.cfg
x2_m:     .res 512              ; x2_m + 128 j + v: the dots of the 7-pixel
                                ; half v (bit 6 = left) in byte j of a group
x2_cbuf:  .res 128              ; a composed cell picture

.segment "X2IMG"                ; page aligned
x2_timg:  .res 8 * 128          ; the 8 tile pictures

.segment "BSS"
x2_kt:    .res 90               ; what each page shows: page p, cell i at
x2_ka:    .res 90               ; 45 p + i (tile, front sprite, back
x2_kb:    .res 90               ; sprite); $FF: unknown
x2_ft:    .res 45               ; the frame wanted
x2_fa:    .res 45
x2_fb:    .res 45
x2_camc:  .res 1                ; the window's map column, row (signed)
x2_camr:  .res 1

.segment "LCCODE"

; ----------------------------------------------------------------------------
; x2_init -- the half masks, the tile pictures; no cell known on either page.
; ----------------------------------------------------------------------------
x2_init:
        LDA     #0
        STA     x2_m
        STA     x2_m+128
        STA     x2_m+256
        STA     x2_m+384
        LDX     #1
@v:     STX     x2_tv           ; v = w + its lowest pixel
        TXA
        LDY     #6
@f:     LSR
        BCS     @got
        DEY
        BPL     @f
@got:   DEX                     ; Y = that pixel (bit 0 = pixel 6)
        TXA
        AND     x2_tv
        STA     x2_n            ; w = v AND (v - 1)
        .repeat 4, j
        LDX     x2_n
        LDA     x2_m+128*j,X
        ORA     x2_pm+7*j,Y
        LDX     x2_tv
        STA     x2_m+128*j,X
        .endrepeat
        INX
        BPL     @v
        LDA     #0              ; tile t: its bits in x2_cbuf, then copied
        STA     x2_n
@t:     JSR     x2_zero
        LDA     x2_n
        ASL
        ASL
        ASL
        ASL
        PHA
        CLC
        ADC     #<x2_tb0
        STA     x2_bp0
        LDA     #>x2_tb0
        ADC     #0
        STA     x2_bp0+1
        PLA
        CLC
        ADC     #<x2_tb1
        STA     x2_bp1
        LDA     #>x2_tb1
        ADC     #0
        STA     x2_bp1+1
        LDX     x2_n
        LDA     x2_tink,X
        JSR     x2_overlay
        LDA     x2_n
        LSR
        PHP
        CLC
        ADC     #>x2_timg
        STA     x2_np+1
        PLP
        LDA     #0
        ROR
        STA     x2_np
        LDY     #127
@c:     LDA     x2_cbuf,Y
        STA     (x2_np),Y
        DEY
        BPL     @c
        INC     x2_n
        LDA     x2_n
        CMP     #8
        BNE     @t
        LDX     #0
        JSR     x2_forget
        LDX     #1
        JSR     x2_forget
        LDA     #0
        STA     x2_camc
        STA     x2_camr
        LDA     #$FF
        STA     x2_src
        RTS

; x2_forget -- X = page: none of its cells known.
x2_forget:
        LDA     x2_p45,X
        TAX
        LDY     #45
        LDA     #$FF
:       STA     x2_kt,X
        INX
        DEY
        BNE     :-
        RTS

; ----------------------------------------------------------------------------
; x2_idle -- the game view: the frame on the hidden page, then shown; or the
; hidden page catching up with the one shown.
; ----------------------------------------------------------------------------
x2_idle:
        JSR     x2_frame
        LDA     dg_vis
        JSR     x2_current
        ROR     x2_cur          ; bit 7 = the page shown has it
        LDA     dg_vis
        EOR     #1
        STA     x2_pg
        BIT     x2_cur
        BPL     @draw
        LDA     x2_pg
        JSR     x2_current
        BCS     @rts            ; both pages have it
@draw:  LDA     x2_pg
        JSR     x2_draw_page
        BIT     x2_cur
        BMI     @rts            ; catching up: no flip
        JMP     x2_flip
@rts:   RTS

; x2_current -- A = page: C = 1 if it shows the frame (X2 view, the same
; 45 keys, its HUD rows and sprite list not written since).
x2_current:
        TAX
        LDA     dg_kindp,X
        BEQ     @no
        LDA     dg_satdp,X
        BNE     @no
        LDA     x2_p45,X
        STA     x2_ko
        TXA
        BNE     @p1
        LDA     dg_touch+20
        ORA     dg_touch+21
        ORA     dg_touch+22
        ORA     dg_touch+23
        BNE     @no
        BEQ     @keys
@p1:    LDA     dg_touch+DG_PD+20
        ORA     dg_touch+DG_PD+21
        ORA     dg_touch+DG_PD+22
        ORA     dg_touch+DG_PD+23
        BNE     @no
@keys:  LDY     #44
@k:     TYA
        CLC
        ADC     x2_ko
        TAX
        LDA     x2_ft,Y
        CMP     x2_kt,X
        BNE     @no
        LDA     x2_fa,Y
        CMP     x2_ka,X
        BNE     @no
        LDA     x2_fb,Y
        CMP     x2_kb,X
        BNE     @no
        DEY
        BPL     @k
        SEC
        RTS
@no:    CLC
        RTS

; x2_flip -- show page x2_pg in a vertical blank: at once if the beam is in
; one, else at the start of the next (//e; a stuck signal: after ~2 frames
; anyway), at once on the //c (no VBL register: a frame may tear).
x2_flip:
        LDA     dg_vbl
        BEQ     @now
        LDX     #0
        LDY     #12
@bl:    BIT     $C019           ; bit 7 clear: in the blank (now or at its start)
        BPL     @now
        DEX
        BNE     @bl
        DEY
        BNE     @bl
@now:   LDA     x2_pg
        STA     dg_vis
        BNE     :+
        BIT     LOWSCR
        RTS
:       BIT     HISCR
        RTS

; ----------------------------------------------------------------------------
; x2_frame -- the camera and the 45 keys of the frame (x2_ft / fa / fb).
; ----------------------------------------------------------------------------
x2_frame:
        LDA     dg_chg
        BNE     :+
        RTS                     ; the virtual screen as at the last frame
:       LDA     #0
        STA     dg_chg
        LDA     DG_SAT          ; sprite 0 the hero, on the grid, on the map?
        CMP     #160
        BCS     @tiles          ; (also $D0: no sprite)
        ORA     DG_SAT+1
        AND     #15
        BNE     @tiles
        LDA     DG_SAT+2
        BNE     @tiles
        LDA     DG_SAT+1
        LSR
        LSR
        LSR
        LSR
        SEC
        SBC     #4
        STA     x2_camc
        LDA     DG_SAT
        LSR
        LSR
        LSR
        LSR
        SEC
        SBC     #2
        STA     x2_camr
@tiles: LDX     #0
        STX     x2_vr
@row:   LDA     x2_camr
        CLC
        ADC     x2_vr
        CMP     #10
        BCS     @blank          ; off the map (or above it: "negative")
        STA     x2_mc
        LSR
        LSR
        CLC
        ADC     #>DG_VRAM
        STA     x2_np+1         ; names row 2 mr = $1800 + 64 mr
        LDA     x2_mc
        AND     #3
        LSR
        ROR
        ROR
        STA     x2_np
        LDA     x2_camc
        STA     x2_mc
        LDA     #X2_W
        STA     x2_n
@c:     LDA     #0
        LDY     x2_mc
        CPY     #16
        BCS     @st             ; off the map
        TYA
        ASL
        TAY
        LDA     (x2_np),Y       ; the cell's top-left name
        LSR
        LSR
@st:    STA     x2_ft,X
        INX
        INC     x2_mc
        DEC     x2_n
        BNE     @c
        BEQ     @nrow
@blank: LDA     #0
        LDY     #X2_W
:       STA     x2_ft,X
        INX
        DEY
        BNE     :-
@nrow:  INC     x2_vr
        LDA     x2_vr
        CMP     #X2_H
        BNE     @row
        ; the sprites, entry 0 first: front, then back of each cell
        LDA     #0
        LDX     #44
:       STA     x2_fa,X
        STA     x2_fb,X
        DEX
        BPL     :-
        LDX     #0
@e:     LDA     DG_SAT,X
        CMP     #$D0
        BEQ     @done
        CMP     #160
        BCS     @nx             ; the HUD's icons
        STA     x2_tv
        ORA     DG_SAT+1,X
        AND     #15
        BNE     @nx             ; off the grid
        LDA     DG_SAT+3,X
        AND     #15
        BEQ     @nx             ; transparent
        STA     x2_tw
        LDA     DG_SAT+2,X
        CMP     #72
        BCS     @nx             ; no such pattern
        LSR
        LSR
        STA     x2_code
        LDA     DG_SAT+1,X
        LSR
        LSR
        LSR
        LSR
        SEC
        SBC     x2_camc
        CMP     #X2_W
        BCS     @nx             ; off the window
        STA     x2_vc
        LDA     x2_tv
        LSR
        LSR
        LSR
        LSR
        SEC
        SBC     x2_camr
        CMP     #X2_H
        BCS     @nx
        TAY
        LDA     x2_m9,Y
        CLC
        ADC     x2_vc
        TAY                     ; the cell
        LDA     x2_code
        CMP     #X2_BOSS0
        BCS     @nf             ; the boss: no flash (its colour is 8)
        LDA     x2_tw
        CMP     #8
        BNE     @nf
        LDA     x2_code
        ORA     #$40
        STA     x2_code
@nf:    INC     x2_code         ; name / 4 + 1 (+ $40)
        LDA     x2_fa,Y
        BNE     :+
        LDA     x2_code
        STA     x2_fa,Y
        BNE     @nx             ; always
:       LDA     x2_fb,Y
        BNE     @nx             ; a third one: hidden
        LDA     x2_code
        STA     x2_fb,Y
@nx:    INX
        INX
        INX
        INX
        CPX     #128
        BEQ     @done
        JMP     @e
@done:  RTS

; ----------------------------------------------------------------------------
; x2_draw_page -- A = page: the frame on it (the cells that differ), then its
; HUD rows (20..23) by the text engine. When it only catches up (x2_cur bit
; 7), a key pressed stops it between two cells: the turn starts at once.
; ----------------------------------------------------------------------------
x2_draw_page:
        STA     x2_pg
        JSR     dg_use_page
        LDX     x2_pg
        LDA     dg_kindp,X
        BNE     @ok
        LDA     #1              ; a full page was there: margins black, every
        STA     dg_kindp,X      ; cell drawn, rows 0..19 unknown to the text
        LDA     #0              ; engine
        STA     dg_bannp,X
        JSR     x2_forget
        LDX     #0
        LDY     #19
        JSR     dg_unknown_rows
        JSR     x2_margins
@ok:    LDX     x2_pg
        LDA     x2_p45,X
        STA     x2_ko
        LDA     #0
        STA     x2_i
        STA     x2_vr
@vr:    LDA     #0
        STA     x2_vc
        STA     x2_mc           ; x2_lines not done for this row yet
@vc:    BIT     x2_cur          ; catching up and a key is there:
        BPL     :+              ; the rest later (what was drawn is
        BIT     KBD             ; noted in the keys)
        BPL     :+
        RTS
:       LDY     x2_i
        TYA
        CLC
        ADC     x2_ko
        TAX
        LDA     x2_ft,Y
        CMP     x2_kt,X
        BNE     @draw
        LDA     x2_fa,Y
        CMP     x2_ka,X
        BNE     @draw
        LDA     x2_fb,Y
        CMP     x2_kb,X
        BEQ     @next
@draw:  LDA     x2_ft,Y
        STA     x2_kt,X
        LDA     x2_fa,Y
        STA     x2_ka,X
        LDA     x2_fb,Y
        STA     x2_kb,X
        LDA     x2_mc
        BNE     :+
        JSR     x2_lines        ; this row's 32 lines into x2_w
        INC     x2_mc
:       JSR     x2_cell
@next:  INC     x2_i
        INC     x2_vc
        LDA     x2_vc
        CMP     #X2_W
        BNE     @vc
        INC     x2_vr
        LDA     x2_vr
        CMP     #X2_H
        BNE     @vr
        LDA     #20             ; the HUD
        STA     dg_rmin
        JMP     dg_text_update

; ----------------------------------------------------------------------------
; x2_cell -- cell x2_i (x2_vr, x2_vc) of the frame onto page dg_pgo (x2_w's
; lines already this row's).
; ----------------------------------------------------------------------------
x2_cell:
        LDY     x2_i
        LDA     x2_fa,Y
        BNE     @spr
        LDA     x2_ft,Y         ; the tile alone: x2_timg + 128 t
        LSR
        PHA
        LDA     #0
        ROR
        STA     x2_off
        PLA
        CLC
        ADC     #>x2_timg
        BNE     @write          ; always
@spr:   LDA     x2_ft,Y         ; the tile, then the sprites: x2_cbuf
        BNE     @tile
        JSR     x2_zero
        JMP     @ovl
@tile:  LSR
        PHA
        LDA     #0
        ROR
        STA     x2_np
        PLA
        CLC
        ADC     #>x2_timg
        STA     x2_np+1
        LDY     #127
:       LDA     (x2_np),Y
        STA     x2_cbuf,Y
        DEY
        BPL     :-
@ovl:   LDY     x2_i
        LDA     x2_fb,Y
        BEQ     :+
        JSR     x2_sprite
        LDY     x2_i
:       LDA     x2_fa,Y
        JSR     x2_sprite
        LDA     #<x2_cbuf
        STA     x2_off
        LDA     #>x2_cbuf
@write: CMP     x2_src          ; x2_w's 16 loads: the picture's page
        BEQ     :+
        STA     x2_src
        .repeat 16, r
        STA     x2_w+9*r+2
        .endrepeat
:       LDA     x2_vc
        ASL
        ASL
        ADC     #2              ; C = 0: the cell's first byte (groups 1+2vc)
        STA     x2_x
        TAX
        LDY     x2_off          ; k = 0, 2, 4, 6: aux bytes 0..3
        PHP
        SEI
        STA     DG_RAMWRT_AUX
        JSR     x2_w
        .repeat 3
        INX
        TYA
        CLC
        ADC     #32
        TAY
        JSR     x2_w
        .endrepeat
        STA     DG_RAMWRT_MAIN
        PLP
        LDX     x2_x            ; k = 1, 3, 5, 7: main bytes 0..3
        LDA     x2_off
        CLC
        ADC     #16
        TAY
        JSR     x2_w
        .repeat 3
        INX
        TYA
        CLC
        ADC     #32
        TAY
        JSR     x2_w
        .endrepeat
        RTS

; x2_w -- one byte column of a cell: picture bytes Y .. Y + 15 (rows) to
; screen byte X of its 32 lines, each row on two lines. Operands: the
; picture's page (x2_cell), the lines (x2_lines). Keeps X, Y.
x2_w:
        .repeat 16, r
        LDA     $1100+r,Y
        STA     $2000,X
        STA     $2000,X
        .endrepeat
        RTS

; x2_lines -- x2_w's 32 line addresses = window row x2_vr's, page dg_pgo
; (its 4 text rows of 8 lines: one row's base, then + $400 a line).
x2_lines:
        LDA     x2_vr
        ASL
        ASL
        TAY                     ; its first text row
        .repeat 4, q
        LDA     dg_rlo+q,Y
        .repeat 8, l
        STA     x2_w+9*(4*q+l/2)+4+3*(l .mod 2)
        .endrepeat
        LDA     dg_rhi+q,Y
        CLC
        ADC     dg_pgo
        .repeat 8, l
        STA     x2_w+9*(4*q+l/2)+5+3*(l .mod 2)
        .if l < 7
        ADC     #4
        .endif
        .endrepeat
        .endrepeat
        RTS

; x2_zero -- x2_cbuf = 0 (a black tile).
x2_zero:
        LDA     #0
        LDY     #15
:       .repeat 8, k
        STA     x2_cbuf+16*k,Y
        .endrepeat
        DEY
        BPL     :-
        RTS

; x2_sprite -- A = a sprite key (name / 4 + 1, + $40 for the flash): its art
; over x2_cbuf, in its ink.
x2_sprite:
        STA     x2_code
        AND     #$3F
        SEC
        SBC     #1
        TAX
        ASL
        ASL
        ASL
        ASL
        STA     x2_tv           ; 16 * art, carry = its bit 8
        LDA     #0
        ROL
        STA     x2_tw
        LDA     x2_tv
        CLC
        ADC     #<x2_sb0
        STA     x2_bp0
        LDA     x2_tw
        ADC     #>x2_sb0
        STA     x2_bp0+1
        LDA     x2_tv
        CLC
        ADC     #<x2_sb1
        STA     x2_bp1
        LDA     x2_tw
        ADC     #>x2_sb1
        STA     x2_bp1+1
        BIT     x2_code
        BVS     :+
        LDA     x2_sink,X
        JMP     x2_overlay
:       LDA     x2_sfl,X
        ; fall through
; x2_overlay -- A = an ink (DHGR pixel value), x2_bp0 / x2_bp1 = 16 rows of
; left / right 7-pixel halves: those pixels of x2_cbuf painted with it.
x2_overlay:
        ASL
        ASL
        ASL
        ASL
        TAX
        .repeat 4, j
        LDA     dg_cpat+j,X
        STA     x2_ink+j
        .endrepeat
        LDA     x2_bp0
        STA     @a+1
        LDA     x2_bp0+1
        STA     @a+2
        LDA     x2_bp1
        STA     @b+1
        LDA     x2_bp1+1
        STA     @b+2
        LDY     #15
@r:
@a:     LDX     $FFFF,Y
        BEQ     @b
        .repeat 4, j
        LDA     x2_cbuf+16*j,Y
        EOR     x2_ink+j
        AND     x2_m+128*j,X
        EOR     x2_cbuf+16*j,Y
        STA     x2_cbuf+16*j,Y
        .endrepeat
@b:     LDX     $FFFF,Y
        BEQ     @nx
        .repeat 4, j
        LDA     x2_cbuf+64+16*j,Y
        EOR     x2_ink+j
        AND     x2_m+128*j,X
        EOR     x2_cbuf+64+16*j,Y
        STA     x2_cbuf+64+16*j,Y
        .endrepeat
@nx:    DEY
        BPL     @r
        RTS

; x2_margins -- lines 0..159 of page dg_pgo: groups 0 and 19 black (a full
; page draws there; the window does not).
x2_margins:
        LDX     #0
@r:     LDA     dg_rlo,X
        STA     dg_ptr
        LDA     dg_rhi,X
        CLC
        ADC     dg_pgo
        STA     dg_ptr+1
        LDA     #8
        STA     x2_n
@l:     PHP
        SEI
        STA     DG_RAMWRT_AUX
        JSR     @four
        STA     DG_RAMWRT_MAIN
        PLP
        JSR     @four
        LDA     dg_ptr+1
        CLC
        ADC     #4
        STA     dg_ptr+1
        DEC     x2_n
        BNE     @l
        INX
        CPX     #20
        BNE     @r
        RTS
@four:  LDA     #0
        TAY
        STA     (dg_ptr),Y
        INY
        STA     (dg_ptr),Y
        LDY     #38
        STA     (dg_ptr),Y
        INY
        STA     (dg_ptr),Y
        RTS

; ----------------------------------------------------------------------------
; x2_banner -- the title's "ROGUE", big: lines 24..55 of page dg_pgo (whole
; lines, each byte once). 8 glyph rows of 12 groups (x2_ban), 4 lines each,
; one ink a row (x2_bink); composed in line 0 of dg_lb.
; ----------------------------------------------------------------------------
x2_banner:
        LDA     #0
        STA     x2_n            ; glyph row
        STA     x2_i            ; its first x2_ban byte
@gr:    LDA     #0
        LDX     #DG_LW - 1
:       STA     dg_lb,X
        DEX
        BPL     :-
        LDX     x2_n
        LDA     x2_bink,X
        ASL
        ASL
        ASL
        ASL
        TAX
        .repeat 4, j
        LDA     dg_cpat+j,X
        STA     x2_ink+j
        .endrepeat
        LDA     #16             ; stream byte of group 4
        STA     x2_x
        LDA     #12
        STA     x2_vc
@g:     LDY     x2_i
        LDX     x2_ban,Y
        BEQ     @gn
        LDY     x2_x
        .repeat 4, j
        LDA     x2_m+128*j,X
        AND     x2_ink+j
        STA     dg_lb+j,Y
        .endrepeat
@gn:    INC     x2_i
        LDA     x2_x
        CLC
        ADC     #4
        STA     x2_x
        DEC     x2_vc
        BNE     @g
        LDA     x2_n            ; its 4 lines: 24 + 4 row ..
        ASL
        ASL
        ADC     #24             ; C = 0
        STA     x2_vr
        LDA     #4
        STA     x2_vc
@ln:    LDA     x2_vr
        LSR
        LSR
        LSR
        TAX
        LDA     dg_rlo,X
        STA     dg_ptr
        LDA     x2_vr
        AND     #7
        ASL
        ASL
        CLC
        ADC     dg_rhi,X
        ADC     dg_pgo          ; C = 0
        STA     dg_ptr+1
        PHP
        SEI
        STA     DG_RAMWRT_AUX
        LDX     #0
        JSR     @half
        STA     DG_RAMWRT_MAIN
        PLP
        LDX     #1
        JSR     @half
        INC     x2_vr
        DEC     x2_vc
        BNE     @ln
        INC     x2_n
        LDA     x2_n
        CMP     #8
        BEQ     :+
        JMP     @gr
:       RTS
@half:  LDY     #0
:       LDA     dg_lb,X
        STA     (dg_ptr),Y
        INX
        INX
        INY
        CPY     #40
        BNE     :-
        RTS

.segment "LCDATA"
x2_m9:  .byte   0, 9, 18, 27, 36        ; first cell of a window row
x2_p45: .byte   0, 45                   ; first key of a page

.include "video_x2_data.inc"
