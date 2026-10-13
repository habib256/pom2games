; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; topo.s -- graphical TOPO in DHGR (lot 4, module 0, window $5800)
; ============================================================================
; Drawn at display time from the resident map ($7000) and the woodland mask
; ($0800); tools/topo_ref.py is the exact model (tests/test_graphical_topo.py
; compares both banks). Physical rows 0..159, mixed text below:
;   pixels 0..111   one colour pixel per cell, north up: screen row r shows
;                   map row j = 21 * (159 - r) / 40 (Bresenham, 1 or 2 rows)
;   pixels 112..139 legend: north arrow and N, one block per 800 ft tint
;                   present below the snow level, then a white snow block
; Cell colour, by priority: water blue; contour black (level >> 2 above the
; east or north neighbour's: 400 ft lines); woods dark green where x + y is
; odd (black on the dark green tint); snow white (level >= M_SNOW, when set); otherwise gt_tint[level >> 3].
; Markers C, R, H, P (3 x 5 glyphs on a black 5 x 7 box) are plotted last;
; P's box takes the colour of a site on the same cell.
;
; One map row is classified into gt_line (colour indices), then packed into
; 32 aux + 32 main bytes; the legend packs its 4 groups only when its row
; pattern changes. The map bytes go to both rows of a cell in one pass, the
; legend bytes row by row, both banks under SEI with PAGE2 (80STORE), main
; selected on return, like the other DHGR routines.
; Render scratch ($50-$A3) is free here: the view is redrawn on return.
; ============================================================================

GT_W     = 112                  ; map cells per row
GT_ROWS  = 160                  ; screen rows of the sheet
GT_LAST  = 83                   ; northmost map row
GT_LEG   = 120                  ; legend tint blocks: pixels 120..131
GT_LEGW  = 12
GT_NORTH = 122                  ; north arrow bitmap: pixels 122..128
GT_NROWS = 18                   ; arrow rows 0..17
GT_KEYBLACK = GT_NROWS          ; legend row keys: 0..17 arrow, 18 black,
GT_KEYTINT  = 32                ; 32 + k tint block k

C_BLACK  = 0
C_DGREEN = 4
C_GREY1  = 5
C_MBLUE  = 6
C_BROWN  = 8
C_ORANGE = 9
C_GREY2  = 10
C_PINK   = 11
C_GREEN  = 12
C_YELLOW = 13
C_WHITE  = 15

; Dry level -> colour (128 bytes) in main $0300-$037F, a page the game
; never uses (docs/MEMORY.md 2): the window has no room left for it.
gt_ctab = $0300

; Zero page: render scratch, dead while TOPO runs.
gt_b0  = dx
gt_b1  = dx+1
gt_b2  = dy
gt_o   = dy+1
gt_end = rx

.segment "TOPO"
module_graphical_topo:
        jsr     view_hide
        lda     #0              ; overlay_fetch left overlay_current = 0
        sta     sim_loaded
        sta     scene_drawn
        sta     shown
        lda     #1
        sta     ui_dirty
        jsr     gt_draw
        lda     #20
        sta     WNDTOP
        jsr     t_home
        jsr     puts
        .byte "TOPO  N UP  CONTOURS 400 FT|P YOU  C CRASH  H CABIN  R RANGERS|BLUE WATER  DOTS WOODS  KEY 800 FT|ESC/RETURN/SPACE: VIEW",0
        jsr     show_dhgr
graphical_topo_key:
        jsr     wait_key
        cmp     #KC_ESC
        beq     @done
        cmp     #KC_RET
        beq     @done
        cmp     #' '
        bne     graphical_topo_key
@done:  jsr     view_hide
        jsr     t_home
        jmp     show_view_hidden

; ----------------------------------------------------------------------------
gt_draw:
        ; Colour of a dry level: tint, or white at and above the snow level.
        ldx     #127
@tint:  txa
        lsr     a
        lsr     a
        lsr     a
        tay
        lda     gt_tint,y
        ldy     M_SNOW
        beq     :+
        cpx     M_SNOW
        bcc     :+
        lda     #C_WHITE
:       sta     gt_ctab,x
        dex
        bpl     @tint
        ; No north neighbour for the first row; east sentinel at index 112.
        ldx     #GT_W
        lda     #$FF
:       sta     gt_qa,x
        sta     gt_qb,x
        dex
        bpl     :-
        ; Markers C, R, H, P: cell and (later) top screen row.
        lda     MAP+3
        sta     gt_mx
        lda     MAP+5
        sta     gt_mj
        lda     M_GOALX
        sta     gt_mx+1
        lda     M_GOALY
        sta     gt_mj+1
        lda     MAP+17
        sta     gt_mx+2
        lda     MAP+18
        ldy     MAP+16
        bne     :+
        lda     #$FF            ; no cabin: never matched
:       sta     gt_mj+2
        lda     px+1
        sta     gt_mx+3
        lda     py+1
        sta     gt_mj+3
        ldx     #3
        lda     #$FF
:       sta     gt_mr,x
        dex
        bpl     :-
        sta     gt_key
        ; Legend: tints of the levels below the snow level up to the highest
        ; level (header +21 = highest + 1, zero: 125), then a snow block when
        ; the snow level is set and reached; 16-row blocks when at most 8.
        lda     MAP+21
        bne     :+
        lda     #126
:       sec
        sbc     #1
        sta     gt_top
        ldy     #0              ; snow block
        ldx     M_SNOW
        beq     @btop
        lda     gt_top
        cmp     M_SNOW
        bcc     :+
        iny
:       dex                     ; snow - 1
        txa
        cmp     gt_top
        bcc     @below
@btop:  lda     gt_top
@below: lsr     a
        lsr     a
        lsr     a
        clc
        adc     #1
        sta     gt_n
        sty     gt_nb
        adc     gt_nb           ; carry clear
        sta     gt_nb
        ldx     #4
        ldy     #15
        cmp     #9
        bcc     :+
        dex
        ldy     #7
:       stx     gt_shift
        sty     gt_hmask
        ; Rows: r = 0..159, map row j from 83 down, err = 21 * t mod 40.
        lda     #0
        sta     gt_r
        lda     #GT_LAST
        sta     gt_j
        lda     #(21 * 159) .mod 40
        sta     gt_err
        ; One map row: its top screen row gt_r, and gt_r + 1 when the next
        ; step keeps the row (err >= 21: no borrow).
@cell:  jsr     gt_cells
        ldx     #3
@mark:  lda     gt_mj,x
        cmp     gt_j
        bne     :+
        lda     gt_r
        sta     gt_mr,x
:       dex
        bpl     @mark
        ldx     #0
        ldy     #0
        lda     #GT_W
        jsr     gt_pack
        ldx     gt_r
        lda     gt_err
        cmp     #21
        bcc     :+
        inx
:       jsr     hgr_row2        ; hp2: last row of the cell
        ldx     gt_r
        jsr     hgr_row         ; hp: first row
        jsr     gt_store_map
@leg:   jsr     gt_legend
        jsr     gt_store_leg
        inc     gt_r
        lda     gt_err
        sec
        sbc     #21
        sta     gt_err
        bcc     @next
        lda     hp2             ; second row of the cell
        sta     hp
        lda     hp2+1
        sta     hp+1
        jmp     @leg
@next:  adc     #40
        sta     gt_err
        dec     gt_j
        lda     gt_r
        cmp     #GT_ROWS
        bcc     @cell
        ; fall through: markers

; gt_markers -- each shown marker: glyph on a black box, clamped in the map.
gt_markers:
        lda     #C_BLACK        ; P on a site: box of the site's colour
        sta     gt_pbg          ; (first of C, R, H)
        ldx     #2
@site:  lda     gt_mx,x
        cmp     gt_mx+3
        bne     :+
        lda     gt_mj,x
        cmp     gt_mj+3
        bne     :+
        lda     gt_mcol,x
        sta     gt_pbg
:       dex
        bpl     @site
        ldx     #0
@mk:    stx     gt_i
        lda     #C_BLACK
        cpx     #3
        bne     :+
        lda     gt_pbg
:       sta     gt_bg
        lda     gt_mr,x
        cmp     #$FF
        beq     @next
        cmp     #3
        bcs     :+
        lda     #3
:       cmp     #GT_ROWS-3
        bcc     :+
        lda     #GT_ROWS-4
:       sec
        sbc     #3
        sta     gt_row
        lda     gt_mx,x
        cmp     #2
        bcs     :+
        lda     #2
:       cmp     #GT_W-2
        bcc     :+
        lda     #GT_W-3
:       sec
        sbc     #2
        sta     gt_x0
        lda     gt_mcol,x
        sta     gt_col
        txa                     ; 7 rows per glyph
        asl     a
        asl     a
        asl     a
        sec
        sbc     gt_i
        sta     gt_g
        lda     #7
        sta     gt_dy
@grow:  ldx     gt_g
        lda     gt_glyphs,x
        sta     gt_bits
        inc     gt_g
        lda     gt_x0
        sta     gt_x
        lda     #5
        sta     gt_dx
@px:    asl     gt_bits
        lda     gt_bg
        bcc     :+
        lda     gt_col
:       ldx     gt_x
        ldy     gt_row
        jsr     gt_plot
        inc     gt_x
        dec     gt_dx
        bne     @px
        inc     gt_row
        dec     gt_dy
        bne     @grow
@next:  ldx     gt_i
        inx
        cpx     #4
        bcs     :+
        jmp     @mk
:       rts

; ----------------------------------------------------------------------------
; gt_cells -- classify map row gt_j into gt_line[0..111], east to west, then
; the woods, swap the level buffers and step the grid pointer south.
gt_cells:
        ldx     #GT_W-1
gt_c_cell:
gt_grid:
        
        lda     MAP+64+GT_LAST*GT_W,x   ; patched: row gt_j
        tay
        bmi     gt_c_water
        lsr     a
        lsr     a
gt_qa1:
        sta     gt_qa,x         ; patched: this row's levels >> 2
gt_qa2:
        cmp     gt_qa+1,x       ; east
        beq     :+
        bcs     gt_c_black
:
gt_qn:
        cmp     gt_qb,x         ; patched: north row
        beq     :+
        bcs     gt_c_black
:       lda     gt_ctab,y
gt_c_put:   sta     gt_line,x
        dex
        bpl     gt_c_cell
        bmi     gt_c_woods
gt_c_water: and     #$7F
        lsr     a
        lsr     a
gt_qa3:
        sta     gt_qa,x         ; patched
        lda     #C_MBLUE
        bne     gt_c_put
gt_c_black: lda     #C_BLACK
        beq     gt_c_put
.assert <forest_bits = 0, error, "woods mask must start a page"
gt_c_woods: lda     MAP+26
        beq     gt_c_swap
        ; mask row (j >> 1) * 7 at $0800: bit i of byte b = cells 16b + 2i,
        ; +1; the cell with x + j odd gets the dot.
        lda     gt_j
        lsr     a
        sta     gt_t
        asl     a
        sta     gp
        asl     a
        adc     gp              ; carry clear: j <= 83
        clc
        adc     gt_t
        sta     gp
        lda     #>forest_bits
        adc     #0
        sta     gp+1
        lda     gt_j
        and     #1
        eor     #1
        tax
        ldy     #0
        stx     gt_wx
gt_c_byte:  lda     (gp),y
        beq     gt_c_empty
        sta     gt_t
        ldx     gt_wx
gt_c_bit:   lsr     gt_t
        bcc     gt_c_nobit
        lda     gt_line,x
        beq     gt_c_nobit          ; contour
        cmp     #C_MBLUE
        beq     gt_c_nobit          ; water
        cmp     #C_DGREEN       ; black dots on the dark green tint
        beq     :+
        lda     #C_DGREEN
        bne     :++
:       lda     #C_BLACK
:       sta     gt_line,x
gt_c_nobit: inx
        inx
        lda     gt_t
        bne     gt_c_bit
gt_c_empty: lda     gt_wx
        clc
        adc     #16
        sta     gt_wx
        iny
        cpy     #7
        bne     gt_c_byte
gt_c_swap:  ldx     gt_qa1+1        ; this row becomes the north row
        lda     gt_qn+1
        stx     gt_qn+1
        sta     gt_qa1+1
        sta     gt_qa3+1
        ldx     gt_qa1+2
        lda     gt_qn+2
        stx     gt_qn+2
        sta     gt_qa1+2
        sta     gt_qa3+2
        lda     gt_qa1+1
        clc
        adc     #1
        sta     gt_qa2+1
        lda     gt_qa1+2
        adc     #0
        sta     gt_qa2+2
        lda     gt_grid+1
        sec
        sbc     #GT_W
        sta     gt_grid+1
        bcs     :+
        dec     gt_grid+2
:       rts

; ----------------------------------------------------------------------------
; gt_legend -- pixels 112..139 of row gt_r, packed when the pattern changes.
gt_legend:
        lda     gt_r
        cmp     #GT_NROWS
        bcc     @key
        lda     #159
        sec
        sbc     gt_r            ; d = 159 - r
        sta     gt_t
        and     gt_hmask
        cmp     gt_hmask
        beq     @black          ; top row of a block
        lda     gt_t
        ldx     gt_shift
:       lsr     a
        dex
        bne     :-
        cmp     gt_nb
        bcs     @black          ; above the last block
        ora     #GT_KEYTINT
        bne     @key
@black: lda     #GT_KEYBLACK
@key:   cmp     gt_key
        beq     @rts
        sta     gt_key
        ldx     #COLS_LEG-1
        lda     #C_BLACK
:       sta     gt_line+GT_W,x
        dex
        bpl     :-
        lda     gt_key
        cmp     #GT_NROWS
        bcs     @tint
        tax
        lda     gt_north,x
        sta     gt_t
        ldx     #GT_NORTH
@arrow: lsr     gt_t
        bcc     :+
        lda     #C_WHITE
        sta     gt_line,x
:       inx
        lda     gt_t
        bne     @arrow
        beq     @pack
@tint:  cmp     #GT_KEYTINT
        bcc     @pack
        and     #31             ; block k: tint k, then the snow block
        cmp     gt_n
        lda     #C_WHITE
        bcs     :+
        lda     gt_key
        and     #31
        tay
        lda     gt_tint,y
:
        ldx     #GT_LEGW-1
:       sta     gt_line+GT_LEG,x
        dex
        bpl     :-
@pack:  ldx     #GT_W
        ldy     #32
        lda     #GT_W+COLS_LEG
        jmp     gt_pack
@rts:   rts
COLS_LEG = 28

; ----------------------------------------------------------------------------
; gt_pack -- groups of 7 pixels of gt_line into gt_aux/gt_main.
;   X = first pixel (7g), A = end pixel, Y = first byte (2g).
gt_pack:
        sta     gt_end
        sty     gt_o
@grp:   ldy     gt_line,x
        lda     gt_k00,y
        ldy     gt_line+1,x
        ora     gt_k10,y
        sta     gt_b0
        lda     gt_k11,y
        ldy     gt_line+2,x
        ora     gt_k21,y
        ldy     gt_line+3,x
        ora     gt_k31,y
        sta     gt_b1
        lda     gt_k32,y
        ldy     gt_line+4,x
        ora     gt_k42,y
        ldy     gt_line+5,x
        ora     gt_k52,y
        sta     gt_b2
        lda     gt_k53,y
        ldy     gt_line+6,x
        ora     gt_k63,y
        ldy     gt_o
        sta     gt_main+1,y
        lda     gt_b2
        sta     gt_aux+1,y
        lda     gt_b1
        sta     gt_main,y
        lda     gt_b0
        sta     gt_aux,y
        iny
        iny
        sty     gt_o
        txa
        clc
        adc     #7
        tax
        cpx     gt_end
        bne     @grp
        rts

; gt_store_map -- map bytes 0..31 of both banks into rows hp and hp2.
gt_store_map:
        php
        sei
        sta     PAGE2_AUX
        ldy     #31
:       lda     gt_aux,y
        sta     (hp),y
        sta     (hp2),y
        dey
        bpl     :-
        sta     PAGE2_MAIN
        ldy     #31
:       lda     gt_main,y
        sta     (hp),y
        sta     (hp2),y
        dey
        bpl     :-
        plp
        rts

; gt_store_leg -- legend bytes 32..39 of both banks into row hp.
gt_store_leg:
        php
        sei
        sta     PAGE2_AUX
        ldy     #39
:       lda     gt_aux,y
        sta     (hp),y
        dey
        cpy     #32
        bcs     :-
        sta     PAGE2_MAIN
        ldy     #39
:       lda     gt_main,y
        sta     (hp),y
        dey
        cpy     #32
        bcs     :-
        plp
        rts

; gt_plot -- A = colour, X = pixel 0..139, Y = screen row: one pixel,
; read-modify-write of its one or two bytes (dhgr.s phase tables).
gt_plot:
        sta     gt_pc
        stx     gt_px
        tya
        tax
        jsr     hgr_row
        lda     gt_px
        jsr     div7            ; X = group, A = phase
        tay
        sty     gt_ph
        txa
        asl     a
        sta     gt_pg
        clc
        adc     ph_offa,y
        sta     gt_poff
        lda     ph_bitsa,y
        sta     gt_pbits
        lda     ph_banka,y
        ldx     ph_pata,y
        jsr     @part
        ldy     gt_ph
        lda     ph_offb,y
        bmi     @rts            ; $FF: one byte
        clc
        adc     gt_pg
        sta     gt_poff
        lda     ph_bitsb,y
        sta     gt_pbits
        lda     ph_bankb,y
        ldx     ph_patb,y
@part:  sta     @bank+1
        stx     @pat+1
        ldx     gt_pc
@pat:   lda     dc_pat,x        ; patched: pattern row of the byte
        and     gt_pbits
        sta     gt_pv
        lda     gt_pbits
        eor     #$7F
        sta     gt_pm
        ldy     gt_poff
        php
        sei
@bank:  sta     PAGE2_MAIN      ; patched: bank of the byte
        lda     (hp),y
        and     gt_pm
        ora     gt_pv
        sta     (hp),y
        sta     PAGE2_MAIN
        plp
@rts:   rts

; ----------------------------------------------------------------------------
; Tint of level >> 3 (800 ft steps), tools/topo_ref.TINT.
gt_tint:
        .byte   C_DGREEN, C_GREEN, C_YELLOW, C_ORANGE, C_BROWN, C_PINK, C_GREY1
        .res    9, C_WHITE
; Marker colours C, R, H, P and their glyphs: 7 rows, bits 7..3 = pixels
; x - 2 .. x + 2 (clear: black box).
gt_mcol: .byte  C_ORANGE, C_YELLOW, C_PINK, C_WHITE
gt_glyphs:
        .byte   0, %01110000, %01000000, %01000000, %01000000, %01110000, 0     ; C
        .byte   0, %01100000, %01010000, %01100000, %01010000, %01010000, 0     ; R
        .byte   0, %01010000, %01010000, %01110000, %01010000, %01010000, 0     ; H
        .byte   0, %01100000, %01010000, %01100000, %01000000, %01000000, 0     ; P
; North arrow and N, rows 0..17: bit i = pixel GT_NORTH + i.
gt_north:
        .byte   %0000000, %0001000, %0001000, %0011100, %0011100, %0111110, %0111110
        .byte   %0001000, %0001000, %0001000, %0000000, %0100010, %0100110, %0101010
        .byte   %0110010, %0100010, %0000000, %0000000
; Pixel K of a 7-pixel group, its part in byte J of the group (aux 2g,
; main 2g, aux 2g + 1, main 2g + 1), for colour C (Apple IIe TN #3).
.macro  gt_kpart K, J
.repeat 16, C
        .byte   ((((C >> 1) | (C << 3)) & 15) * $1111111 >> (7 * J)) & (($F << (4 * K)) >> (7 * J)) & $7F
.endrep
.endmacro
gt_k00: gt_kpart 0, 0
gt_k10: gt_kpart 1, 0
gt_k11: gt_kpart 1, 1
gt_k21: gt_kpart 2, 1
gt_k31: gt_kpart 3, 1
gt_k32: gt_kpart 3, 2
gt_k42: gt_kpart 4, 2
gt_k52: gt_kpart 5, 2
gt_k53: gt_kpart 5, 3
gt_k63: gt_kpart 6, 3

; ----------------------------------------------------------------------------
; Buffers: past the image in the window (not stored, not copied).
.segment "TOPOBSS"
gt_qa:   .res   GT_W+1          ; levels >> 2 of two map rows, east sentinel
gt_qb:   .res   GT_W+1
gt_line: .res   GT_W+COLS_LEG   ; colour of each pixel of the row
gt_aux:  .res   40              ; packed row
gt_main: .res   40
gt_mx:   .res   4               ; markers C, R, H, P
gt_mj:   .res   4
gt_mr:   .res   4               ; top screen row, $FF: not shown
gt_r:    .res   1
gt_j:    .res   1
gt_err:  .res   1
gt_wx:   .res   1
gt_top:  .res   1               ; legend: highest level
gt_n:    .res   1               ;         tint blocks
gt_nb:   .res   1               ;         all blocks
gt_shift: .res  1               ;         log2 of the block height
gt_hmask: .res  1               ;         block height - 1
gt_pbg:  .res   1               ; P's box colour
gt_bg:   .res   1               ; box colour of the marker drawn
gt_key:  .res   1
gt_t:    .res   1
gt_bits: .res   1
gt_i:    .res   1
gt_row:  .res   1
gt_x0:   .res   1
gt_x:    .res   1
gt_col:  .res   1
gt_g:    .res   1
gt_dx:   .res   1
gt_dy:   .res   1
gt_pc:   .res   1
gt_px:   .res   1
gt_ph:   .res   1
gt_pg:   .res   1
gt_poff: .res   1
gt_pbits: .res  1
gt_pv:   .res   1
gt_pm:   .res   1
.segment "GCODE"
