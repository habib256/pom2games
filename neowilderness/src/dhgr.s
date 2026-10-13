; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; dhgr.s -- DHGR output of the view engine (lot 3, included by wild.s)
; ============================================================================
; One ray = one DHGR colour pixel column x = 0..139: the 4-bit cell
; 4 * (x mod 7) of byte group g = x / 7, i.e. the interleaved bytes aux 2g,
; main 2g, aux 2g+1, main 2g+1 (7 bits each, LSB first, bit 7 clear).
; Colour c (LORES numbering) is stored as rot(c) = (c >> 1 | c << 3) & 15
; (Apple IIe TN #3, tools/dhgr_palette.py). A column touches at most one
; byte per bank: one read-modify-write pass per bank and span.
;
; Bank convention (docs/DHGR.md): 80STORE and HIRES stay on during the game,
; PAGE2 selects the bank of $2000-$3FFF for the CPU ($C055 aux, $C054 main)
; without changing the displayed page. Every routine returns with main
; selected. render, scroll and hud_col mask IRQs around aux passes.
;
; Colours come from the mood (tools/gendhgr.py, docs/DHGR.md 3.2), chosen
; once per frame by dhgr_frame. An entry is a << 4 | b: a where
; (logical row + azimuth of the column) is even, b where odd (a checkerboard
; anchored to the world, so scrolled columns keep their phase; a = b solid).
; The unrolled rows OR dv0 into even rows and dv1 into odd rows, so a
; dithered span costs the same as a solid one.
;
; Logical view rows 0..15 are painted into physical rows 160..175 (hidden
; under the four text rows), the cache convention of the HGR engine; the
; compass and survival panels own physical rows 0..15 (src/hud.s, colour
; pixels drawn by hud_col with the phase tables and dc_pat below).
; ============================================================================

PAL_ZONE    = 0                 ; mood entries (tools/gendhgr.py): 5 sky zones
PAL_GROUND  = 5                 ; near, mid, far
PAL_SNOW    = 8
PAL_WATER   = 11
PAL_RIDGE   = 14
PAL_OUTLINE = 15
PAL_TRUNK   = 16
PAL_CROWN   = 17                ; odd, then even
PAL_SUN     = 19
PAL_SHADE   = 20

PAGE2_MAIN  = $C054
PAGE2_AUX   = $C055
OP_RTS      = $60
OP_LDAY     = $B9

.define DHGR_ROW(I) $2000 + ((I) .mod 8) * $400 + (((I) / 8) .mod 8) * $80 + ((I) / 64) * $28
; physical row of logical row I: 0..15 -> 160..175
.define DHGR_VIEW_ROW(I) DHGR_ROW((I) + ((I) < HUD_ROWS) * VIEW_ROWS)

.segment "GCODE"
        .include "dhgr_tables.inc"      ; build/, from tools/gendhgr.py

.segment "ZEROPAGE"
dm:      .res 1                 ; pass: kept bits
dv0:     .res 1                 ; pass: colour bits of even rows
dv1:     .res 1                 ; pass: colour bits of odd rows
dca:     .res 1                 ; span: colour a (rows with row + col even)
dcb:     .res 1                 ; span: colour b
dpa_off: .res 1                 ; column: physical byte of part A
dpa_and: .res 1                 ;         its kept bits, then its pixel bits
dpa_bits: .res 1
dpb_off: .res 1                 ; part B ($FF: the pixel fits in one byte)
dpb_and: .res 1
dpb_bits: .res 1
dj:      .res 2                 ; pass: entry row
dp:      .res 2                 ; pass: row that receives the RTS
dzone:   .res 1                 ; sky zone of render_sky

; ----------------------------------------------------------------------------
; Unrolled rows (WILDLO): logical row I = LDA row,Y / AND dm / ORA dv / STA
; row,Y, 10 bytes, 15 cycles. dspan plants an RTS on the end row; the extra
; entry VIEW_ROWS only ever holds a planted RTS. Not banked: one RTS serves
; the aux and the main pass.
.segment "LOWCODE"
drows:
.repeat VIEW_ROWS, I
        lda     DHGR_VIEW_ROW(I), y
        and     dm
.if I .mod 2
        ora     dv1
.else
        ora     dv0
.endif
        sta     DHGR_VIEW_ROW(I), y
.endrep
        .byte   OP_LDAY

.segment "CODE"
drow_lo:
.repeat VIEW_ROWS + 1, R
        .byte   <(drows + R * 10)
.endrep
drow_hi:
.repeat VIEW_ROWS + 1, R
        .byte   >(drows + R * 10)
.endrep

; dspan -- rows Y..sp_end-1 of the current column, mood entry A.
;          Clobbers A, X, Y; returns with main selected.
dspan:  cpy     sp_end
        bcs     dspan_rts
        tax
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     dca
        txa
        and     #15
        sta     dcb
        ldx     sp_end
        lda     drow_lo,x
        sta     dp
        lda     drow_hi,x
        sta     dp+1
        lda     drow_lo,y
        sta     dj
        lda     drow_hi,y
        sta     dj+1
        ldy     #0
        lda     #OP_RTS
        sta     (dp),y
dspan_ea0:
        ldx     dca             ; patched: even-row colour of this column
dspan_pa0:
        lda     dc_pat,x        ; patched: pattern row of part A
        and     dpa_bits
        sta     dv0
dspan_ea1:
        ldx     dcb             ; patched: odd-row colour
dspan_pa1:
        lda     dc_pat,x
        and     dpa_bits
        sta     dv1
        lda     dpa_and
        sta     dm
        ldy     dpa_off
dspan_ba:
        sta     PAGE2_MAIN      ; patched: bank of part A
        jsr     dspan_go
        ldy     dpb_off
        bmi     dspan_end
dspan_eb0:
        ldx     dca
dspan_pb0:
        lda     dc_pat,x
        and     dpb_bits
        sta     dv0
dspan_eb1:
        ldx     dcb
dspan_pb1:
        lda     dc_pat,x
        and     dpb_bits
        sta     dv1
        lda     dpb_and
        sta     dm
dspan_bb:
        sta     PAGE2_MAIN
        jsr     dspan_go
dspan_end:
        sta     PAGE2_MAIN
        ldy     #0
        lda     #OP_LDAY
        sta     (dp),y
dspan_rts:
        rts
dspan_go:
        jmp     (dj)

; column_setup -- per column: bytes, masks and banks of the pixel, and the
; dither order (column parity) patched into dspan.
column_setup:
        lda     col
        jsr     div7            ; X = group, A = phase
        tay
        txa
        asl     a
        tax                     ; X = 2g
        clc
        adc     ph_offa,y
        sta     dpa_off
        lda     ph_bitsa,y
        sta     dpa_bits
        eor     #$7F
        sta     dpa_and
        lda     ph_banka,y
        sta     dspan_ba+1
        lda     ph_pata,y
        sta     dspan_pa0+1
        sta     dspan_pa1+1
        lda     ph_offb,y
        bmi     @one            ; $FF: the pixel fits in one byte
        lda     ph_bitsb,y
        sta     dpb_bits
        eor     #$7F
        sta     dpb_and
        lda     ph_bankb,y
        sta     dspan_bb+1
        lda     ph_patb,y
        sta     dspan_pb0+1
        sta     dspan_pb1+1
        txa
        clc
        adc     ph_offb,y
@one:   sta     dpb_off
        lda     ang             ; dither anchored to the azimuth: a turn
        lsr     a               ; scrolls 35 columns without changing it
        lda     #<dca
        ldx     #<dcb
        bcc     :+
        lda     #<dcb
        ldx     #<dca
:       sta     dspan_ea0+1
        sta     dspan_eb0+1
        stx     dspan_ea1+1
        stx     dspan_eb1+1
        rts
.assert >dc_pat = >(dc_pat + 63), error, "dc_pat crosses a page"

sky_zone_end: .byte SKY_ROW0, SKY_ROW1, SKY_ROW2, SKY_ROW3, VIEW_ROWS

.segment "GCODE"
; TOPO (src/topo.s) draws rows 0..159 through these; the HUD uses hud_row.
; hgr_row -- X = screen row 0..191: hp = its address in $2000-$3FFF
; ($2000 + (y & 7) * $400 + (y >> 3 & 7) * $80 + (y >> 6) * $28).
; hgr_row2: the same in hp2 (hp clobbered). Preserve X and Y.
hgr_row2:
        jsr     hgr_row
        lda     hp
        sta     hp2
        lda     hp+1
        sta     hp2+1
        rts
hgr_row:
        txa
        and     #$C0
        lsr     a
        sta     hp
        lsr     a
        lsr     a
        adc     hp              ; 0, $28, $50 (carry clear)
        sta     hp
        txa
        and     #$08
        beq     :+
        lda     #$80
        ora     hp
        sta     hp
:       txa
        and     #$30
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     hp+1
        txa
        and     #7
        asl     a
        asl     a
        ora     #$20
        ora     hp+1
        sta     hp+1
        rts

.segment "CODE"
; div7 -- A = 0..255: X = A / 7, A = A mod 7.
div7:   ldx     #0
@sub:   cmp     #7
        bcc     @done
        sbc     #7
        inx
        bne     @sub
@done:  rts

; Phase k = x mod 7: part A byte j = (0,0,1,1,2,2,3), part B j = (-,1,-,2,-,3,-).
; j: 0 aux 2g, 1 main 2g, 2 aux 2g+1, 3 main 2g+1.
ph_offa:  .byte 0, 0, 0, 0, 1, 1, 1
ph_banka: .byte <PAGE2_AUX, <PAGE2_AUX, <PAGE2_MAIN, <PAGE2_MAIN, <PAGE2_AUX, <PAGE2_AUX, <PAGE2_MAIN
ph_pata:  .byte <dc_pat, <dc_pat, <dc_pat+16, <dc_pat+16, <dc_pat+32, <dc_pat+32, <dc_pat+48
ph_bitsa:
.repeat 7, K
        .byte   (($F << (4 * K)) >> (7 * ((4 * K) / 7))) & $7F
.endrep
ph_offb:  .byte $FF, 0, $FF, 1, $FF, 1, $FF
ph_bankb: .byte 0, <PAGE2_MAIN, 0, <PAGE2_AUX, 0, <PAGE2_MAIN, 0
ph_patb:  .byte 0, <dc_pat+16, 0, <dc_pat+32, 0, <dc_pat+48, 0
ph_bitsb:
.repeat 7, K
        .byte   (($F << (4 * K)) >> (7 * ((4 * K) / 7 + 1))) & $7F
.endrep
; Solid colour bytes dc_pat[j * 16 + c] (Apple IIe TN #3).
dc_pat:
.repeat 4, JJ
.repeat 16, CC
        .byte   ((((CC >> 1) | (CC << 3)) & 15) * $1111111 >> (7 * JJ)) & $7F
.endrep
.endrep

; ----------------------------------------------------------------------------
; Mood and palette of the frame
.segment "GDATA"
; Recomputed with the hour by sky_position (docs/DHGR.md 3.3). S8 units:
; round(128 * sin(altitude)), signed; $80 when not computed (the engine
; computes the sun by day, the Moon at night).
sun_alt8:   .byte $80
moon_alt8:  .byte $80
moon_phase: .byte 0             ; sky_lunar sample 0..11 (11 = full disk)
sky_mood:   .byte 0             ; tools/dhgr_palette.MOODS index of the last frame
.segment "BSS"
cur_pal:    .res MOOD_SIZE      ; entries of the current mood
cur_zone = cur_pal + PAL_ZONE   ; sky: zenith, dither, mid, dither, glow
spr_map:    .res 4              ; sprite code -> shaded solid entry
draw_dark:  .res 1              ; no sprite (view_dark, or a mood without light)
body_on:    .res 1              ; sun/Moon drawn
body_colour: .res 1

.segment "GCODE"
; dhgr_frame -- choose the mood and expand its entries for the renderer.
dhgr_frame:
        jsr     select_mood
        sta     sky_mood
        tax
        lda     #0
        clc
@mul:   dex
        bmi     @base
        adc     #MOOD_SIZE
        bcc     @mul
@base:  tax
        ldy     #0
@copy:  lda     dhgr_moods,x
        sta     cur_pal,y
        inx
        iny
        cpy     #MOOD_SIZE
        bne     @copy
        ; Sun of the mood by day, the Moon (white, pale yellow when low) at night.
        ldx     #1
        lda     night
        beq     @sun
        lda     moon_alt8
        eor     #$80
        cmp     #MOON_LOW+$80
        lda     #MOON_HIGH_COLOUR
        bcs     @body
        lda     #MOON_LOW_COLOUR
        bne     @body
@sun:   lda     cur_pal+PAL_SUN
        cmp     #$FF
        bne     @body
        dex
@body:  sta     body_colour
        stx     body_on
        ; Sprites: shade of the mood over the day colours of the asset.
        ldx     #1
        lda     cur_pal+PAL_SHADE
        bmi     @dark
        ldx     view_dark
@dark:  stx     draw_dark
        txa
        bne     @done
        lda     scene_asset
        sec
        sbc     #5
        cmp     #5
        bcs     @done
        asl     a
        asl     a
        sta     dzone
        lda     cur_pal+PAL_SHADE
        asl     a
        asl     a
        asl     a
        asl     a
        sta     dca
        ldy     #3
@code:  tya
        ora     dzone
        tax
        lda     dhgr_assets,x
        ora     dca
        tax
        lda     dhgr_shades,x
        sta     dcb
        asl     a
        asl     a
        asl     a
        asl     a
        ora     dcb
        sta     spr_map,y
        dey
        bpl     @code
@done:  rts

; select_mood -- A = mood (docs/DHGR.md 3.1), integer compares only.
; view_dark keeps the HGR rule (only a full lunar disk lights the night):
; game logic (scene preparation, "no light" message) depends on it. By
; day the engine has only the sun: below -12 degrees it stays nautical.
select_mood:
        lda     view_dark
        bne     @dark
        ldx     weather_sky
        lda     night
        bne     @night
        lda     sun_alt8        ; first threshold the sun reaches
        eor     #$80
        ldy     #0
@sun:   cmp     sun_steps,y
        bcs     @step
        iny
        bne     @sun
@step:  lda     sun_clear,y
        cpx     #0
        beq     @rts
        lda     sun_cloudy,y
@rts:   rts
@night: lda     moon_alt8       ; Moon below the horizon: no light
        beq     @dark
        bmi     @dark
        cmp     #MOON_LOW
        lda     moon_phase
        bcs     :+
        sbc     #1              ; carry clear: -2 when the Moon is low
:       cpx     #0
        beq     :+
        sec
        sbc     #3              ; under clouds
:       tay                     ; N = sign of the light
        bmi     @dark
        cmp     #LIGHT_DIM
        bcc     @dark
        cmp     #LIGHT_BRIGHT
        lda     #MOOD_NIGHT_DIM
        bcc     @rts
        lda     #MOOD_NIGHT_BRIGHT
        rts
@dark:  lda     #MOOD_NIGHT_DARK
        rts
; Daytime moods (signed S8 thresholds, biased by $80); below -13 degrees
; the sun stays nautical: the engine has no Moon by day.
sun_steps:  .byte SUN_DAY+$80, SUN_GOLDEN+$80, SUN_HORIZON+$80, SUN_CIVIL+$80, 0
sun_clear:  .byte MOOD_DAY, MOOD_GOLDEN, MOOD_SUNSET, MOOD_CIVIL, MOOD_NAUTICAL
sun_cloudy: .byte MOOD_OVERCAST, MOOD_OVERCAST_DUSK, MOOD_OVERCAST_DUSK, MOOD_NAUTICAL, MOOD_NAUTICAL

; ----------------------------------------------------------------------------
; Sun / Moon altitudes, at each sky_position (when the hour changes).
.segment "GCODE"
; sky_position -- the SIM routine, then the altitude of the body it
; computed (sky_up, a ROM float in the scratch buffer) in S8 units. Pure
; integer code: FAC, ARG and the ROM rounding byte stay untouched.
sky_position:
        jsr     sky_position_core
        lda     sky_up
        beq     @store          ; zero
        lda     #129
        sec
        sbc     sky_up          ; shifts = 129 - exponent
        beq     @max            ; |sin| = 1
        bcc     @max
        cmp     #9
        bcs     @zero
        tax
        lda     sky_up+1
        ora     #$80            ; mantissa 0.1xxxxxxx
@shift: dex
        beq     @round
        lsr     a
        bne     @shift          ; A >= 1 during the shifts
@round: lsr     a
        adc     #0              ; round half up
        bpl     @sign
@max:   lda     #127
@sign:  bit     sky_up+1
        bpl     @store
        eor     #$FF
        clc
        adc     #1
@store: ldx     night
        bne     @moon
        sta     sun_alt8
        lda     #$80
        sta     moon_alt8
        lda     #0
        beq     @phase
@moon:  sta     moon_alt8
        lda     #$80
        sta     sun_alt8
        lda     sky_sample
@phase: sta     moon_phase
        rts
@zero:  lda     #0
        beq     @store

; ----------------------------------------------------------------------------
; Clears and scrolls of the terrain rows 16..175, both banks.
.segment "LOWCODE"
; Rows 16..175 by bands of eight: rows 8b..8b+7 share their low address
; byte, their high bytes step by 4 ($400); the band routines patch eight
; absolute,X operands per band and run once per bank.
.segment "BSS"
band_index: .res 1              ; band 2..21
band_lo:    .res 1              ; address of row 8b
band_hi:    .res 1
band_slo:   .res 1              ; scroll: source and destination low bytes
band_dlo:   .res 1
band_sadd:  .res 1
band_dadd:  .res 1
scroll_x:   .res 1              ; scroll: first byte index
.segment "GCODE"
; band_base -- X = band: band_lo/band_hi = address of its first row.
band_base:
        stx     band_index
        txa
        lsr     a
        lsr     a
        lsr     a
        tay
        lda     band_third,y    ; (b >> 3) * $28
        sta     band_lo
        txa
        lsr     a               ; carry = b & 1: + $80
        and     #3
        ora     #>$2000
        sta     band_hi
        bcc     :+
        lda     band_lo
        ora     #$80
        sta     band_lo
:       rts
band_third: .byte 0, $28, $50
.segment "LOWCODE"

; clear_rows -- clear byte columns [tmp,tmp2) of both banks, rows 16..175
;               (tmp < tmp2); keep the HUD.
clear_rows:
        php
        sei
        ldx     #HUD_ROWS/8
@band:  jsr     band_base
        ldy     #7*3
        lda     band_hi
        clc
        adc     #7*4
@patch: sta     clear_band+2,y
        tax
        lda     band_lo
        sta     clear_band+1,y
        txa
        sec
        sbc     #4
        dey
        dey
        dey
        bpl     @patch
        sta     PAGE2_AUX
        jsr     clear_band_go
        sta     PAGE2_MAIN
        jsr     clear_band_go
        ldx     band_index
        inx
        cpx     #(VIEW_ROWS+HUD_ROWS)/8
        bne     @band
        plp
        rts
clear_band_go:
        ldx     tmp
        lda     #0
clear_band:
.repeat 8
        sta     $2000,x         ; patched: row 8b + k
.endrep
        inx
        cpx     tmp2
        bne     clear_band
        rts

; ----------------------------------------------------------------------------
; Video modes. The view: DHGR + four mixed text rows, which are 80-column
; text under DHGR. The game keeps its 40-column text page: each character
; is the odd 80-column cell (main), the even cells (aux) hold spaces. The
; Monitor's COUT/HOME/SCROLL/CLREOL switch to 80-column layout when 80COL is
; on, so the game uses its own 40-column text primitives (below).
.segment "GCODE"
show_dhgr:
        sta     STORE80ON
        sta     COL80ON
        bit     DHIRES_ON
        bit     HIRES
        bit     MIXSET
        php
        sei
        sta     PAGE2_AUX       ; 80STORE: aux text page
        ldx     #39
        lda     #' '|$80
@space: sta     $0650,x         ; text rows 20..23
        sta     $06D0,x
        sta     $0750,x
        sta     $07D0,x
        dex
        bpl     @space
        sta     PAGE2_MAIN
        plp
        bit     TXTCLR
        rts

; show_text -- 40-column text page 1 (menus, curtain, MAP).
show_text:
        sta     COL80OFF
        bit     TXTSET
        rts

; ----------------------------------------------------------------------------
.segment "CODE"
; 40-column text primitives (main text page only), used instead of the
; Monitor's: they never look at 80COL. Window $20-$23, CH/CV, BASL ($28).
WNDLFT  = $20
WNDWDTH = $21
WNDBTM  = $23
BASL    = $28
BAS2L   = $2A
INVFLG  = $32

; t_cout -- the CSW output routine: A = character. Preserves A, X, Y.
t_cout: pha
        sty     @y+1
        cmp     #$A0
        bcc     @low
        and     INVFLG
@put:   ldy     CH
        sta     (BASL),y
        inc     CH
        lda     CH
        cmp     WNDWDTH
        bcc     @y
@cr:    lda     #0
        sta     CH
@lf:    inc     CV
        lda     CV
        cmp     WNDBTM
        bcc     @vtab
        dec     CV
        jsr     t_scroll
@vtab:  jsr     t_vtab
@y:     ldy     #0
        pla
        rts
@low:   cmp     #$80
        bcc     @put            ; inverse / flashing: stored as is
        cmp     #$8D
        beq     @cr
        cmp     #$8A
        beq     @lf
        bne     @y              ; other controls are ignored

; t_vtab -- BASL = row CV. t_bascalc: A = row.
t_vtab: lda     CV
t_bascalc:
        pha
        lsr     a
        and     #3
        ora     #4
        sta     BASL+1
        pla
        and     #$18
        bcc     :+
        adc     #$7F
:       sta     BASL
        asl     a
        asl     a
        ora     BASL
        sta     BASL
        rts

; t_scroll -- rows WNDTOP..WNDBTM-1 up by one, the last one cleared.
t_scroll:
        ldx     WNDTOP
@row:   txa
        jsr     t_bascalc
        inx
        cpx     WNDBTM
        bcs     @last
        lda     BASL
        sta     BAS2L
        lda     BASL+1
        sta     BAS2L+1
        txa
        jsr     t_bascalc
        ldy     #39
@copy:  lda     (BASL),y
        sta     (BAS2L),y
        dey
        bpl     @copy
        bmi     @row
@last:  ldy     #0
        jmp     t_clreol_y

; t_home -- clear the window, cursor on its first row.
t_home: lda     #0
        sta     CH
        lda     WNDTOP
        sta     CV
        ldy     #0
        beq     t_clreop_row
; t_clreop -- clear from the cursor to the end of the window.
t_clreop:
        ldy     CH
        lda     CV
t_clreop_row:
        pha
        jsr     t_bascalc
        jsr     t_clreol_y
        ldy     #0
        pla
        clc
        adc     #1
        cmp     WNDBTM
        bcc     t_clreop_row
        jmp     t_vtab
; t_clreol -- clear from the cursor to the end of the row.
t_clreol:
        ldy     CH
t_clreol_y:
        lda     #' '|$80
@clear: cpy     WNDWDTH
        bcs     @done
        sta     (BASL),y
        iny
        bne     @clear
@done:  rts
