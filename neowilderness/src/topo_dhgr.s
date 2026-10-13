; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; topo_dhgr.s -- TOPOGEN: the DHGR TOPO sheet computed from the resident map
; (lot 4, docs/TOPO_DHGR.md), and the snapshot of the view it overwrites.
; ============================================================================
; Module 0, copied by mem_fetch into the SIM window ($9600, like the
; simulation; sim_loaded is cleared by its caller). Its tables and row
; buffers (TOPOBSS) follow the code in the same window.
;
; topo_open  -- snapshot of the view (rows 0..159, both banks) in the
;               auxiliary language card, DHGR mixed mode, legend on text
;               rows 20..23, then the sheet, which wipes the view from the
;               top (tools/topo_dhgr_ref.Sheet6502, bit for bit).
; topo_close -- C clear: the view and its band are back (snapshot copied back,
;               0.2 s instead of a full redraw); C set: no snapshot, redraw.
;
; Sheet: rows 0..159, x 0..111 the map (one cell column per colour pixel),
; x 112..139 the legend strip. Row sy samples v = (159 - sy) * 166 / 159 half
; cells (DDA); each pixel gets a code K = band | woods ($20) or water ($40),
; compared with its east (kr) and north (KP) neighbours: equal -> FILL table
; (tint dither or woods texture), else the slow path draws contours, index
; contours and water rims (retro writes into the east / north colour
; buffers, idempotent). The north row is packed one row late.
; ============================================================================

TP_WATER = 2                    ; dark blue: open water
TP_SHORE = 6                    ; medium blue: water touching land
TP_WOODS = 4                    ; dark green
TP_INK   = 15                   ; strip ink
K_WOODS  = $20
K_WATER  = $40
TP_ROWS  = 160
TP_BAR_BOTTOM = 157

; Renderer scratch (the view is stopped while TOPO is shown).
tr0   = dx                      ; grid row j
tr1   = dy                      ; grid row j + 1
tptr  = rx                      ; patch / copy pointer
tcp   = ry                      ; colour row being flushed
tkr   = qlo                     ; K of the east neighbour
tkc   = qhi                     ; K of the pixel (slow path)
th1   = divisor
tf    = dz                      ; slow path flags: 1 line, 2 index, 4 rim
tnk   = eye                     ; K of a neighbour
tval  = n
tpar  = thr                     ; slow path: x & 1
ttmp  = thr+1
tq    = tinc                    ; q = v & 1
tj    = tinc+1                  ; j = v >> 1

.segment "TOPOBSS"
tp_fill:   .res 8*256           ; fill{r}{p}[K] on page 2r+p (K <= $40)
tp_ka:     .res 256             ; K rows, current / north (swapped)
tp_kb:     .res 256
tp_ca:     .res 256             ; colour rows, 140 pixels (packed one row late)
tp_cb:     .res 256
tp_wrow:   .res 112             ; K_WOODS where the nearest cell row is wooded
tp_mark:   .res 65              ; contour colour of K's band; [$40] = rim
tp_indexk: .res 64              ; index contour colour of K's band
tp_idxk:   .res 64              ; index levels at or below K's band
tp_ri:     .res 32              ; ramp entry of a band (10 = snow)
tp_wood:   .res 32              ; band under the timberline
tp_lrow:   .res 8               ; scale labels: first row, digits ($FF none)
tp_ltens:  .res 8
tp_lunits: .res 8
tp_nlab:   .res 1
tp_mk:     .res 3*8             ; markers: x, row, box x, box row, box, ink, glyph
tp_nmk:    .res 1
tp_v:      .res 1               ; DDA: half cells
tp_acc:    .res 1
tp_sy:     .res 1
tp_nb:     .res 1               ; nearest cell row
tp_fy:     .res 1               ; woods row of tp_wrow
tp_prime:  .res 1
tp_kcur:   .res 1               ; pages of the K / colour rows
tp_kprev:  .res 1
tp_ccur:   .res 1
tp_cprev:  .res 1
tp_base:   .res 1
tp_snow:   .res 1
tp_sb:     .res 1
tp_top:    .res 1               ; highest band
tp_timber: .res 1
tp_bartop: .res 1
tp_row:    .res 1               ; flush: screen row
tp_ov:     .res 1               ; flush: bar override colour (0: none)
tp_ovon:   .res 1
tp_b:      .res 1
tp_gb:     .res 1               ; pack: 2 * group
tp_b0:     .res 1
tp_b1:     .res 1
tp_b2:     .res 1
tp_valid:  .res 1               ; a snapshot of the view is stored

.segment "TOPOGEN"
; ----------------------------------------------------------------------------
topo_open:
        jsr     tp_save         ; the view, before anything is drawn
        jsr     text_mode80     ; from a 40-column menu too
        lda     #20
        sta     WNDTOP
        jsr     t_home
        jsr     show_dhgr       ; the sheet wipes the view from the top
        jsr     puts
        .byte   "TOPO  N UP  CONTOURS 400 FT, BOLD 2000|"
        .byte   "C CRASH  H CABIN  R RANGERS  SCALE KFT|"
        .byte   "MAP: PLAYER MAP|"
        .byte   "ESC/RETURN/SPACE: VIEW",0
        ; fall through
; ----------------------------------------------------------------------------
topo_sheet:
        jsr     tp_tables
        jsr     tp_sites
        lda     #166            ; v(0) = 83 cells
        sta     tp_v
        lda     #158
        sta     tp_acc
        lda     #$FF
        sta     tp_fy
        lda     #1
        sta     tp_prime
        lda     #0
        sta     tp_sy
        lda     #>tp_ka
        sta     tp_kcur
        lda     #>tp_kb
        sta     tp_kprev
        lda     #>tp_ca
        sta     tp_ccur
        lda     #>tp_cb
        sta     tp_cprev
@row:   lda     tp_v            ; j = v >> 1, q = v & 1, nearest = j + q
        lsr     a
        sta     tj
        lda     #0
        rol     a
        sta     tq
        clc
        adc     tj
        sta     tp_nb
        ldx     tj
        lda     grid_lo,x
        sta     tr0
        lda     grid_hi,x
        sta     tr0+1
        cpx     #GH-1
        bcs     :+
        inx
:       lda     grid_lo,x
        sta     tr1
        lda     grid_hi,x
        sta     tr1+1
        lda     tp_nb
        lsr     a
        cmp     tp_fy
        beq     :+
        sta     tp_fy
        jsr     tp_wrow_make
:       jsr     tp_patch
        lda     tp_prime        ; row 0 is its own north row
        beq     @seed
        lda     #0
        sta     tp_prime
        sta     tptr
        lda     tp_kprev
        sta     tptr+1
        ldy     #GW-1
:       jsr     tp_sample
        sta     (tptr),y
        dey
        bpl     :-
@seed:  ldy     #GW-1           ; the east neighbour of x = 111 is itself
        jsr     tp_sample
        sta     tkr
        lda     tq
        bne     @mid
        jsr     tp_loop_cell
        jmp     @flush
@mid:   jsr     tp_loop_mid
@flush: lda     tp_sy
        beq     @swap
        sec
        sbc     #1
        jsr     tp_flush
@swap:  ldx     tp_kcur
        lda     tp_kprev
        sta     tp_kcur
        stx     tp_kprev
        ldx     tp_ccur
        lda     tp_cprev
        sta     tp_ccur
        stx     tp_cprev
        jsr     tp_dda
        inc     tp_sy
        lda     tp_sy
        cmp     #TP_ROWS
        bcs     :+
        jmp     @row
:       lda     #TP_ROWS-1
        jmp     tp_flush

; tp_dda -- next row: acc += 7, v -= 1, and one more when acc reaches 159.
tp_dda: dec     tp_v
        lda     tp_acc
        clc
        adc     #7
        cmp     #159
        bcc     :+
        sbc     #159
        dec     tp_v
:       sta     tp_acc
        rts

; tp_sample -- Y = x: A = K of the pixel on the current row.
tp_sample:
        lda     tq
        bne     @mid
        lda     (tr0),y
        bmi     @water
        lsr     a
        lsr     a
        ora     tp_wrow,y
        rts
@water: lda     #K_WATER
        rts
@mid:   lda     (tr1),y
        bmi     @water
        sta     th1
        lda     (tr0),y
        and     #$7F
        clc
        adc     th1
        ror     a
        lsr     a
        lsr     a
        ora     tp_wrow,y
        rts

; ----------------------------------------------------------------------------
; Pixel loops: x = 111 (odd) .. 0, two pixels per pass; operands marked P
; are patched once per row (tp_patch).
.macro TP_PIXEL mid, kc, kp, fill, cc, slow
.local land, tail
  .if mid
        lda     (tr1),y
        bpl     land
        lda     #K_WATER
        bne     tail
land:   sta     th1
        lda     (tr0),y
        and     #$7F
        clc
        adc     th1
        ror     a
        lsr     a
        lsr     a
        ora     tp_wrow,y
  .else
        lda     (tr0),y
        bpl     land
        lda     #K_WATER
        bne     tail
land:   lsr     a
        lsr     a
        ora     tp_wrow,y
  .endif
tail:
kc:     sta     $FF00,y         ; P: K of this row
kp:     cmp     $FF00,y         ; P: north
        bne     slow
        cmp     tkr             ; east
        bne     slow
        tax
fill:   lda     $FF00,x         ; P: fill{row & 3}{x & 1}
cc:     sta     $FF00,y         ; P: colour of this row
.endmacro

.macro TP_LOOP mid, p
.local loop, odd_next, even_next, odd_slow, even_slow
        ldy     #GW-1
loop:
        TP_PIXEL mid, .ident(.concat(p, "_kc1")), .ident(.concat(p, "_kp1")), .ident(.concat(p, "_fo")), .ident(.concat(p, "_cc1")), odd_slow
odd_next:
        dey
        TP_PIXEL mid, .ident(.concat(p, "_kc0")), .ident(.concat(p, "_kp0")), .ident(.concat(p, "_fe")), .ident(.concat(p, "_cc0")), even_slow
even_next:
        dey
        bpl     loop
        rts
odd_slow:
        ldx     #1
        jsr     tp_slow
        jmp     odd_next
even_slow:
        ldx     #0
        jsr     tp_slow
        jmp     even_next
.endmacro

tp_loop_cell:
        TP_LOOP 0, "tpc"
tp_loop_mid:
        TP_LOOP 1, "tpm"

; tp_slow -- A = K of pixel Y, X = parity: compare with the north and east
; neighbours, write rims / index contours back into them, colour the pixel.
tp_slow:
        sta     tkc
        stx     tpar
        lda     #0
        sta     tf
tp_s_kp:
        lda     $FF00,y         ; P: north K
        cmp     tkc
        beq     tps_east
        sta     tnk
        eor     tkc
        tax
        and     #K_WATER
        beq     tps_nland
        lda     tkc             ; exactly one of the two is water
        cmp     #K_WATER
        bne     tps_nrim
        lda     #4
        ora     tf
        sta     tf
        bne     tps_east
tps_nrim:  lda     #TP_SHORE
tp_s_cp1:
        sta     $FF00,y         ; P: north colour (retro)
        jmp     tps_east
tps_nland: txa
        and     #$1F
        beq     tps_east           ; woods only
        lda     tf
        ora     #1
        sta     tf
        ldx     tnk
        lda     tp_idxk,x
        ldx     tkc
        cmp     tp_idxk,x
        beq     tps_east
        lda     tf
        ora     #2
        sta     tf
        ldx     tnk
        lda     tp_indexk,x
tp_s_cp2:
        sta     $FF00,y         ; P: north colour (retro)
tps_east:  lda     tkr
        cmp     tkc
        beq     tps_end
        sta     tnk
        eor     tkc
        tax
        and     #K_WATER
        beq     tps_eland
        lda     tkc
        cmp     #K_WATER
        bne     tps_erim
        lda     #4
        ora     tf
        sta     tf
        bne     tps_end
tps_erim:  lda     #TP_SHORE
tp_s_cc1:
        sta     $FF01,y         ; P: east colour, x + 1 (retro)
        jmp     tps_end
tps_eland: txa
        and     #$1F
        beq     tps_end
        lda     tf
        ora     #1
        sta     tf
        ldx     tnk
        lda     tp_idxk,x
        ldx     tkc
        cmp     tp_idxk,x
        beq     tps_end
        lda     tf
        ora     #2
        sta     tf
        ldx     tnk
        lda     tp_indexk,x
tp_s_cc2:
        sta     $FF01,y         ; P: east colour (retro)
tps_end:   ldx     tkc
        stx     tkr
        lda     tf
        beq     tps_fill
        and     #4
        bne     tps_mark
        lda     tf
        and     #2
        beq     tps_mark
        lda     tp_indexk,x
        jmp     tps_store
tps_mark:  lda     tp_mark,x
        jmp     tps_store
tps_fill:  lda     tpar
        bne     tps_odd
tp_s_fe:
        lda     $FF00,x         ; P: fill, even x
        jmp     tps_store
tps_odd:
tp_s_fo:
        lda     $FF00,x         ; P: fill, odd x
tps_store:
tp_s_cc:
        sta     $FF00,y         ; P: colour of this row
        rts

; tp_patch -- page operands of the row: K / colour buffers, fill tables
tp_patch:
        lda     tp_kcur
        sta     tpc_kc1+2
        sta     tpc_kc0+2
        sta     tpm_kc1+2
        sta     tpm_kc0+2
        lda     tp_kprev
        sta     tpc_kp1+2
        sta     tpc_kp0+2
        sta     tpm_kp1+2
        sta     tpm_kp0+2
        sta     tp_s_kp+2
        lda     tp_ccur
        sta     tpc_cc1+2
        sta     tpc_cc0+2
        sta     tpm_cc1+2
        sta     tpm_cc0+2
        sta     tp_s_cc+2
        sta     tp_s_cc1+2
        sta     tp_s_cc2+2
        lda     tp_cprev
        sta     tp_s_cp1+2
        sta     tp_s_cp2+2
        lda     tp_sy           ; fill{row & 3}{p}: page 2r + p
        and     #3
        asl     a
        adc     #>tp_fill
        sta     tpc_fe+2
        sta     tpm_fe+2
        sta     tp_s_fe+2
        adc     #1
        sta     tpc_fo+2
        sta     tpm_fo+2
        sta     tp_s_fo+2
        rts

; tp_wrow_make -- A = woods row (nearest >> 1): 112 bytes of K_WOODS / 0.
tp_wrow_make:
        tax
        lda     #<forest_bits
        sta     tptr
        lda     #>forest_bits
        sta     tptr+1
:       dex
        bmi     :+
        lda     tptr
        clc
        adc     #7
        sta     tptr
        bcc     :-
        inc     tptr+1
        bne     :-
:       ldy     #0
        ldx     #0
@byte:  sty     ttmp
        lda     (tptr),y
        ldy     #8
@bit:   lsr     a
        pha
        lda     #0
        bcc     :+
        lda     #K_WOODS
:       sta     tp_wrow,x
        sta     tp_wrow+1,x
        inx
        inx
        pla
        dey
        bne     @bit
        ldy     ttmp
        iny
        cpy     #7
        bcc     @byte
        rts

; ----------------------------------------------------------------------------
; tp_flush -- A = screen row: legend strip and markers into the north colour
; row, then its 20 byte groups, both banks.
tp_flush:
        sta     tp_row
        lda     #0
        sta     tcp
        lda     tp_cprev
        sta     tcp+1
        ldy     #COLS_TP-1
        lda     #0
:       sta     (tcp),y
        dey
        cpy     #GW
        bcs     :-
        ; scale bar
        lda     tp_row
        cmp     tp_bartop
        bcc     @nobar
        cmp     #TP_BAR_BOTTOM+1
        bcc     @inbar
@nobar: jmp     @labels
@inbar: lda     #TP_BAR_BOTTOM
        sec
        sbc     tp_row
        tax                     ; d
        lsr     a
        lsr     a
        sta     tp_b            ; band
        lda     #0
        sta     tp_ovon
        txa
        and     #3
        cmp     #3
        bne     @below
        ldx     tp_b            ; top row of the band, a band above
        cpx     tp_top
        bcs     @bar
        lda     tp_idxk+1,x
        cmp     tp_idxk,x
        bne     @index
        lda     tp_mark,x
        bne     @over           ; colours are never 0 here? (see below)
        beq     @over
@below: cmp     #0
        bne     @bar
        ldx     tp_b
        beq     @bar
        lda     tp_idxk-1,x
        cmp     tp_idxk,x
        beq     @bar
@index: ldx     tp_b
        lda     tp_indexk,x
@over:  sta     tp_ov
        inc     tp_ovon
@bar:   ldy     #115
@barx:  lda     tp_ovon
        beq     :+
        lda     tp_ov
        bne     @barput
        beq     @barput
:       lda     tp_row          ; fill{row & 3}{x & 1}[band]
        and     #3
        asl     a
        sta     tval
        tya
        and     #1
        ora     tval
        clc
        adc     #>tp_fill
        sta     tptr+1
        lda     tp_b
        sta     tptr
        sty     ttmp
        ldy     #0
        lda     (tptr),y
        ldy     ttmp
@barput:
        sta     (tcp),y
        iny
        cpy     #121
        bcc     @barx
@labels:
        ldx     tp_nlab
@lab:   dex
        bmi     @north
        lda     tp_row
        sec
        sbc     tp_lrow,x
        cmp     #5
        bcs     @lab
        sta     ttmp            ; glyph row
        cmp     #2
        bne     :+
        ldy     #121            ; tick
        lda     #TP_INK
        sta     (tcp),y
:       stx     tval
        ldy     #123
        lda     tp_ltens,x
        bmi     :+
        jsr     tp_glyph_row
        ldx     tval
        ldy     #127
:       lda     tp_lunits,x
        jsr     tp_glyph_row
        ldx     tval
        jmp     @lab
@north: lda     tp_row          ; N, rows 3..7
        sec
        sbc     #3
        cmp     #5
        bcs     @arrow
        sta     ttmp
        lda     #TPG_N
        ldy     #124
        jsr     tp_glyph_row
@arrow: lda     tp_row          ; arrow rows 10..25 at x 125
        sec
        sbc     #10
        cmp     #16
        bcs     @marks
        tax
        ldy     #125
        lda     #TP_INK
        sta     (tcp),y
        cpx     #4
        bcs     @marks
        lda     tp_arrow,x      ; half width of the head
        beq     @marks
        tax
@ar:    stx     th1
        txa
        clc
        adc     #125
        tay
        lda     #TP_INK
        sta     (tcp),y
        lda     #125
        sec
        sbc     th1
        tay
        lda     #TP_INK
        sta     (tcp),y
        dex
        bne     @ar
@marks: jsr     tp_markers
        ; pack the 140 pixels: 20 groups
        ldx     tp_row
        jsr     hgr_row
        lda     hp
        sta     tp_pm0+1
        sta     tp_pa0+1
        clc
        adc     #1
        sta     tp_pm1+1
        sta     tp_pa1+1
        lda     hp+1
        sta     tp_pm0+2
        sta     tp_pa0+2
        sta     tp_pm1+2
        sta     tp_pa1+2
        lda     tp_cprev
        ldx     #6
:       ldy     tp_ppat,x       ; high bytes of the CP+k operands
        sta     tp_pk0+2,y
        dex
        bpl     :-
        lda     #0
        sta     tp_gb
        tay
        php
        sei
tpk_g:
tp_pk0: ldx     $FF00,y
        lda     tp_t0,x
tp_pk1: ldx     $FF01,y
        ora     tp_t1a,x
        sta     tp_b0
        lda     tp_t1b,x
tp_pk2: ldx     $FF02,y
        ora     tp_t2,x
tp_pk3: ldx     $FF03,y
        ora     tp_t3a,x
        sta     tp_b1
        lda     tp_t3b,x
tp_pk4: ldx     $FF04,y
        ora     tp_t4,x
tp_pk5: ldx     $FF05,y
        ora     tp_t5a,x
        sta     tp_b2
        lda     tp_t5b,x
tp_pk6: ldx     $FF06,y
        ora     tp_t6,x
        ldx     tp_gb
tp_pm1: sta     $FFFF,x         ; main 2g + 1
        lda     tp_b1
tp_pm0: sta     $FFFF,x         ; main 2g
        sta     PAGE2_AUX
        lda     tp_b0
tp_pa0: sta     $FFFF,x         ; aux 2g
        lda     tp_b2
tp_pa1: sta     $FFFF,x         ; aux 2g + 1
        sta     PAGE2_MAIN
        inx
        inx
        stx     tp_gb
        tya
        clc
        adc     #7
        tay
        cpy     #COLS_TP
        bcc     tpk_g
        plp
        rts
COLS_TP = 140
tp_ppat: .byte  tp_pk0-tp_pk0, tp_pk1-tp_pk0, tp_pk2-tp_pk0, tp_pk3-tp_pk0
         .byte  tp_pk4-tp_pk0, tp_pk5-tp_pk0, tp_pk6-tp_pk0
tp_arrow:  .byte 0, 1, 1, 2     ; half width of the arrow head, rows 10..13

; tp_glyph_row -- A = glyph, ttmp = its row 0..4, Y = left x: ink pixels.
tp_glyph_row:
        sta     th1             ; 5 * glyph + row
        asl     a
        asl     a
        adc     th1
        adc     ttmp
        tax
        lda     tp_glyphs,x
        ldx     #3
@px:    asl     a               ; bit 2 (left pixel) first, into bit 3
        pha
        and     #8
        beq     :+
        lda     #TP_INK
        sta     (tcp),y
:       pla
        iny
        dex
        bne     @px
        rts

; tp_markers -- crash, cabin and rangers (drawn R, H, C) on row tp_row.
tp_markers:
        ldx     #0
@mk:    cpx     tp_nmk
        bcs     @done
        lda     tp_row
        cmp     tp_mk+1,x       ; site pixel
        bne     :+
        ldy     tp_mk,x
        lda     tp_mk+4,x
        sta     (tcp),y
:       lda     tp_row
        sec
        sbc     tp_mk+3,x       ; row in the box
        cmp     #7
        bcs     @next
        sta     ttmp
        stx     tval
        ldy     tp_mk+2,x       ; box x
        lda     tp_mk+4,x
        sta     (tcp),y         ; c = 0 and 4: box
        iny
        sta     tf              ; box colour
        lda     tp_mk+5,x
        sta     tnk             ; ink
        lda     #0
        ldx     ttmp
        beq     @bits
        cpx     #6
        bcs     @bits
        dec     ttmp
        ldx     tval
        lda     tp_mk+6,x
        asl     a
        asl     a
        adc     tp_mk+6,x       ; 5 * glyph
        adc     ttmp
        tax
        lda     tp_glyphs,x
@bits:  ldx     #3
@c:     asl     a
        pha
        and     #8
        beq     :+
        lda     tnk
        bne     :++
:       lda     tf
:       sta     (tcp),y
        pla
        iny
        dex
        bne     @c
        lda     tf
        sta     (tcp),y
        ldx     tval
@next:  txa
        clc
        adc     #8
        tax
        bne     @mk
@done:  rts

; 3 x 5 glyphs, bit 2 = left pixel (tools/topo_palette.GLYPHS).
TPG_N = 10
TPG_C = 11
TPG_H = 12
TPG_R = 13
tp_glyphs:
        .byte   7,5,5,5,7, 2,6,2,2,7, 7,1,7,4,7, 7,1,3,1,7, 5,5,7,1,1
        .byte   7,4,7,1,7, 7,4,7,5,7, 7,1,1,2,2, 7,5,7,5,7, 7,5,7,1,7
        .byte   5,7,7,7,5, 7,4,4,4,7, 5,5,7,5,5, 6,5,6,5,5

; Packing tables (tools/topo_palette.pack_tables), r = rot(c).
; (values of tools/topo_palette.pack_tables)
tp_t0: .byte $00,$08,$01,$09,$02,$0A,$03,$0B,$04,$0C,$05,$0D,$06,$0E,$07,$0F
tp_t1a: .byte $00,$00,$10,$10,$20,$20,$30,$30,$40,$40,$50,$50,$60,$60,$70,$70
tp_t1b: .byte $00,$01,$00,$01,$00,$01,$00,$01,$00,$01,$00,$01,$00,$01,$00,$01
tp_t2: .byte $00,$10,$02,$12,$04,$14,$06,$16,$08,$18,$0A,$1A,$0C,$1C,$0E,$1E
tp_t3a: .byte $00,$00,$20,$20,$40,$40,$60,$60,$00,$00,$20,$20,$40,$40,$60,$60
tp_t3b: .byte $00,$02,$00,$02,$00,$02,$00,$02,$01,$03,$01,$03,$01,$03,$01,$03
tp_t4: .byte $00,$20,$04,$24,$08,$28,$0C,$2C,$10,$30,$14,$34,$18,$38,$1C,$3C
tp_t5a: .byte $00,$00,$40,$40,$00,$00,$40,$40,$00,$00,$40,$40,$00,$00,$40,$40
tp_t5b: .byte $00,$04,$00,$04,$01,$05,$01,$05,$02,$06,$02,$06,$03,$07,$03,$07
tp_t6: .byte $00,$40,$08,$48,$10,$50,$18,$58,$20,$60,$28,$68,$30,$70,$38,$78

; ----------------------------------------------------------------------------
; tp_tables -- the byte tables of the sheet from the map header (oracle:
; tools/topo_palette.tables).
tp_tables:
        lda     MAP+10          ; base altitude, snow level, timberline
        bne     :+
        lda     #24
:       sta     tp_base
        lda     MAP+11
        bne     :+
        lda     #48
:       sta     tp_snow
        lda     MAP+27
        bne     :+
        lda     #110
:       sta     tp_timber
        lda     MAP+21          ; highest level + 1, or the grid maximum
        beq     @scan
        sec
        sbc     #1
        jmp     @top
@scan:  lda     #<GRID
        sta     tptr
        lda     #>GRID
        sta     tptr+1
        lda     #0
        sta     tval
        ldx     #0              ; 9408 cells: 36 pages and 192 bytes
        ldy     #0
@max:   lda     (tptr),y
        and     #$7F
        cmp     tval
        bcc     :+
        sta     tval
:       iny
        bne     :+
        inc     tptr+1
        inx
:       cpx     #>(GW*GH)
        bne     @max
        cpy     #<(GW*GH)
        bne     @max
        lda     tval
@top:   lsr     a
        lsr     a
        sta     tp_top
        lda     tp_snow         ; sb = ceil(snow / 4)
        clc
        adc     #3
        ror     a
        lsr     a
        sta     tp_sb
        ; per band b: ramp entry, index levels, woods allowed
        lda     tp_base         ; m = (base + 4b) mod 20
:       cmp     #20
        bcc     :+
        sbc     #20
        bcs     :-
:       sta     ttmp
        lda     #0
        sta     tval            ; index levels 4k, 1 <= k <= b
        ldx     #0
@band:  cpx     #0
        beq     @ramp
        lda     ttmp
        clc
        adc     #4
        cmp     #20
        bcc     :+
        sbc     #20
:       sta     ttmp
        bne     @ramp
        inc     tval
@ramp:  lda     tval
        sta     tp_idxk,x
        sta     tp_idxk+32,x
        lda     #10             ; snow
        cpx     tp_sb
        bcs     @ri
        stx     tf              ; b * 10 / sb (b * 10 < 320: 16 bits)
        txa
        asl     a
        asl     a
        adc     tf
        asl     a
        sta     tf
        lda     #0
        rol     a
        sta     tnk
        ldy     #0
@div:   lda     tf
        sec
        sbc     tp_sb
        sta     tf
        lda     tnk
        sbc     #0
        sta     tnk
        bcc     @quot
        iny
        bne     @div
@quot:  tya
        cmp     #10
        bcc     @ri
        lda     #9
@ri:    sta     tp_ri,x
        lda     #0              ; woods: 4b + base < timber
        sta     tf
        txa
        asl     a
        asl     a
        clc
        adc     tp_base
        bcs     :+
        cmp     tp_timber
        bcs     :+
        lda     #K_WOODS
        sta     tf
:       lda     tf
        sta     tp_wood,x
        inx
        cpx     #32
        bcc     @band
        ; per code K = 0..63: contour colours and the eight fill tables
        ldx     #63
@k:     txa
        and     #31
        tay
        lda     tp_wood,y
        sta     tf
        txa
        and     tf              ; K_WOODS: wooded code where woods may grow
        sta     tf
        lda     tp_ri,y
        tay
        lda     tp_line,y
        sta     tp_mark,x
        lda     tp_index,y
        sta     tp_indexk,x
        lda     tp_ramp,y
        sta     tnk             ; a << 4 | b
        stx     tval
        ldy     #7              ; table t = 2r + p
@t:     tya
        clc
        adc     #>tp_fill
        sta     tptr+1
        lda     #0
        sta     tptr
        lda     tnk
        ldx     tp_tpar,y       ; (r + p) & 1: 0 = a, 1 = b
        bne     :+
        lsr     a
        lsr     a
        lsr     a
        lsr     a
:       and     #15
        ldx     tf
        beq     :+
        ldx     tp_wdot,y       ; woods window
        beq     :+
        lda     #TP_WOODS
:       sty     ttmp
        ldy     tval
        sta     (tptr),y
        ldy     ttmp
        dey
        bpl     @t
        ldx     tval
        dex
        bpl     @k
        ldy     #7              ; water
@w:     tya
        clc
        adc     #>tp_fill
        sta     tptr+1
        lda     #0
        sta     tptr
        sty     ttmp
        ldy     #K_WATER
        lda     #TP_WATER
        sta     (tptr),y
        ldy     ttmp
        dey
        bpl     @w
        lda     #TP_SHORE
        sta     tp_mark+K_WATER
        ; scale: top row of the bar and the labels of the index contours
        lda     tp_top
        asl     a
        asl     a
        sta     tval
        lda     #TP_BAR_BOTTOM-3
        sec
        sbc     tval
        sta     tp_bartop       ; 157 - 4 (top + 1) + 1
        ldy     #0              ; labels
        lda     #1
        sta     tp_b
@lab:   ldx     tp_b
        cpx     tp_top
        beq     :+
        bcs     @labend
:       lda     tp_idxk,x
        cmp     tp_idxk-1,x
        beq     @labnext
        txa                     ; first row: 155 - 4b
        asl     a
        asl     a
        sta     tval
        lda     #TP_BAR_BOTTOM-2
        sec
        sbc     tval
        sta     tp_lrow,y
        txa                     ; q = (4b + base) / 10, 16-bit dividend
        asl     a
        asl     a
        clc
        adc     tp_base
        sta     tval
        lda     #0
        rol     a
        sta     tf
        lda     #0
        sta     tnk
@ten:   lda     tval
        sec
        sbc     #10
        sta     th1
        lda     tf
        sbc     #0
        bcc     @tend
        sta     tf
        lda     th1
        sta     tval
        inc     tnk
        bne     @ten
@tend:  lda     tnk             ; its digits
        ldx     #$FF
@d10:   inx
        sec
        sbc     #10
        bcs     @d10
        adc     #10
        sta     tp_lunits,y
        txa
        bne     :+
        lda     #$FF            ; one digit
:       sta     tp_ltens,y
        iny
@labnext:
        inc     tp_b
        lda     tp_b
        cmp     #32
        bcc     @lab
@labend:
        sty     tp_nlab
        rts
tp_ramp:  .byte $CC, $CD, $DD, $D9, $99, $98, $88, $85, $55, $5F, $FF
tp_line:  .byte 8, 8, 8, 8, 8, 8, 0, 0, 0, 0, 7
tp_index: .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5
tp_tpar:  .byte 0, 1, 1, 0, 0, 1, 1, 0      ; (r + p) & 1 for t = 2r + p
tp_wdot:  .byte 0, 1, 1, 1, 1, 0, 1, 1      ; woods_dot(p, r)

; ----------------------------------------------------------------------------
; tp_sites -- markers R, H (if any), C: site pixel, 5 x 7 box, letter.
tp_sites:
        ldx     #0
        lda     MAP+8
        sta     tval
        lda     MAP+9
        ldy     #0              ; R: purple box, white letter
        jsr     tp_marker
        lda     MAP+16
        beq     :+
        lda     MAP+17
        sta     tval
        lda     MAP+18
        ldy     #1              ; H: black box, yellow letter
        jsr     tp_marker
:       lda     MAP+3
        sta     tval
        lda     MAP+5
        ldy     #2              ; C: magenta box, white letter
        jsr     tp_marker
        stx     tp_nmk
        rts
; tp_marker -- tval = cell x, A = cell y, Y = kind, X = slot (+8 on return).
tp_marker:
        pha
        lda     tp_mbox,y
        sta     tp_mk+4,x
        lda     tp_mink,y
        sta     tp_mk+5,x
        lda     tp_mglyph,y
        sta     tp_mk+6,x
        lda     tval
        sta     tp_mk,x
        clc
        adc     #5
        cmp     #GW
        lda     tval
        bcs     :+
        adc     #1              ; carry clear
        bcc     :++
:       sbc     #5              ; carry set
:       sta     tp_mk+2,x
        pla
        jsr     tp_marker_row
        sta     tp_mk+1,x
        cmp     #7
        bcc     :+
        sbc     #7
        bcs     :++
:       adc     #1
:       sta     tp_mk+3,x
        txa
        clc
        adc     #8
        tax
        rts
tp_mbox:   .byte 3, 0, 1
tp_mink:   .byte 15, 13, 15
tp_mglyph: .byte TPG_R, TPG_H, TPG_C

; tp_marker_row -- A = cell row y: first sheet row whose nearest cell row is
; y (the DDA of topo_sheet). Preserves X.
tp_marker_row:
        sta     th1
        stx     tf
        lda     #166
        sta     tp_v
        lda     #158
        sta     tp_acc
        ldx     #0
@row:   lda     tp_v
        clc
        adc     #1
        lsr     a
        cmp     th1
        beq     @found
        jsr     tp_dda
        inx
        cpx     #TP_ROWS
        bcc     @row
@found: txa
        ldx     tf
        rts

; ----------------------------------------------------------------------------
; Snapshot of rows 0..159 (both banks, 80 bytes a row) in the auxiliary
; language card, reserved by tools/build_disk.py: rows 0..152 at $D000-$FFCF
; with bank 1 selected (bank 1 + common area), rows 153..159 at
; $DC00-$DE2F of bank 2. ALTZP selects the auxiliary card, and also the
; auxiliary zero page and stack (never used otherwise): the pointers are set
; after the switch.
TP_LC1 = $C08B                  ; RAM bank 1, read and write
TP_LC2 = $C083                  ; RAM bank 2, read and write
TP_SPLIT = 153
tp_save:
        lda     #0
        beq     tp_copy
topo_close:
        lda     tp_valid
        bne     :+
        sec                     ; no snapshot: the caller redraws
        rts
:       lda     #0
        sta     tp_valid
        lda     #1
tp_copy:
        sta     tp_dir+1
        php
        sei
        sta     ALTZPON
        lda     TP_LC1
        lda     TP_LC1
        lda     #<$D000
        sta     tptr
        lda     #>$D000
        sta     tptr+1
        ldx     #0
tpy_row:   cpx     #TP_SPLIT
        bne     :+
        lda     TP_LC2
        lda     TP_LC2
        lda     #<$DC00
        sta     tptr
        lda     #>$DC00
        sta     tptr+1
:       jsr     hgr_row         ; hp: main bytes 0..39 = snapshot 0..39
        sec
        lda     hp
        sbc     #40
        sta     tcp             ; tcp + 40..79 = the same row (aux bank)
        lda     hp+1
        sbc     #0
        sta     tcp+1
tp_dir: lda     #0
        bne     tpy_load
        ldy     #39
:       lda     (hp),y
        sta     (tptr),y
        dey
        bpl     :-
        sta     PAGE2_AUX
        ldy     #79
:       lda     (tcp),y
        sta     (tptr),y
        dey
        cpy     #40
        bcs     :-
        bcc     tpy_next
tpy_load:  ldy     #39
:       lda     (tptr),y
        sta     (hp),y
        dey
        bpl     :-
        sta     PAGE2_AUX
        ldy     #79
:       lda     (tptr),y
        sta     (tcp),y
        dey
        cpy     #40
        bcs     :-
tpy_next:  sta     PAGE2_MAIN
        clc
        lda     tptr
        adc     #80
        sta     tptr
        bcc     :+
        inc     tptr+1
:       inx
        cpx     #TP_ROWS
        bcc     tpy_row
        lda     LCROM
        sta     ALTZPOFF
        plp
        lda     tp_dir+1
        bne     :+
        lda     #1              ; saved
        sta     tp_valid
:       clc
        rts
.assert TP_SPLIT * 80 <= $FFFA - $D000, error, "snapshot overflows the language card"
