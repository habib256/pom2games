; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; fire.s -- the animated campfire of the view (docs/CAMP.md section 8).
;
; The original draws no fire. A fire burns on its own cell (camp.s fire_on,
; fire_pos): M5 forbids walking away from it, except when an animal shares
; the cell (camp_walk), so it is drawn only while the player stands on that
; cell, as a local sprite anchored in the world: at the bearing the player
; faced when lighting it (fire_bear), at the player's feet (physical rows
; FIRE_TOP..FIRE_TOP + 31 = 125..156), 28 x 32 colour pixels, at the screen column of that bearing
; relative to the heading (src/project.s project_center), clipped at the
; view's edges, absent when out of view. As in the original it burns until
; DOUSE: no lifetime, one art. Art and data: tools/genfire.py
; (build/fire.inc).
;
; It lives while the prompt waits for a key (menu.s idle), with the view on
; screen, and nowhere else:
;   fire_tick  each turn of the idle loop with no key waiting. No fire on
;              screen: if a fire burns on the player's cell, the view is
;              shown (graphics) and the player does not LOOK UP, the module
;              is read from NEOWILD.BLK (directory entry 18, both editions)
;              into the SIM window (free between two commands, menu.s
;              MENUSWAP), once per appearance, and draws frame 0 over the
;              saved background if the fire is in view (else nothing
;              until fire_hide). Fire on screen: a countdown; at its end
;              the next frame, rows that change only, bytes that differ from the
;              screen only. Nothing else runs in the idle loop: the module
;              stays in its window from one frame to the next.
;   fire_hide  before get_line returns (every command, every page, TOPO,
;              MAP) and before a turn of the view: the background comes back,
;              byte for byte, so every other code sees the view without fire.
; Nothing else knows about the fire: MAKE FIRE and DOUSE need no hook (the
; next prompt shows it or not), a redrawn view gets it at the next prompt.
;
; Keys. The read cannot be interrupted inside a block (the first one takes
; up to 1 s on a 5.25-inch disk: motor and seek; 0.01 s on a 3.5-inch one)
; and the keyboard latch keeps one key: the read starts only after a quiet
; keyboard (FIRE_SOON, about 1 s, after a prompt; 1.4 to 2.4 s after a
; key), and a key waiting between two blocks cuts it (disk_fetch, df_kbd):
; the key is read, the fire comes back after the next quiet spell.
;
; Resident: fire_tick, fire_hide, fire_dly, fire_st and in menu.s
; fire_idle, STA fire_dly+1 at each key and two JSR fire_hide (MENUCODE);
; fire_light, fire_fetch and sim_fetch (forage.s) in WILDGAME; the fire's
; place and bearing in GDATA (saved).
; ============================================================================
RDTEXT      = $C01A             ; bit 7: text shown (no view on screen)
FIRE_DIR    = 18                ; directory entry (the alias of 17 is
                                ; overlay_load's, which never fetches 18)
FIRE_RUN    = $9600             ; the module's jump table
FIRE_PERIOD = 14                ; frames: 14 x 256 idle turns (about 5 Hz)
FIRE_SOON   = 96                ; the read: 96 x 256 idle turns after the
                                ; prompt (about 1 s of quiet keyboard)
FB_BG       = $A000             ; saved background, row * 20 + k (640 bytes)

.segment "MENUCODE"
; fire_tick -- menu.s fire_idle: one turn of the idle loop, no key waiting.
; The fire appears after fire_dly turns of 256 without a key (FIRE_SOON at
; a prompt; a key sets the count to its code, 128 to 218: about 1.4 to 2.4
; s), so that the read of the module never meets a key typed in a burst.
fire_tick:
        lda     fire_st
        bne     @run
        lda     fire_on
        beq     @no
        dec     fire_dly
        bne     @no
        dec     fire_dly+1
        bne     @no
        lda     RDTEXT          ; a text page is shown: no view
        bmi     @later
        lda     tilt            ; LOOK UP: the player's feet are out of view
        cmp     #1
        beq     @later
        lda     px+1            ; the fire stays on its cell
        cmp     fire_cx
        bne     @later
        lda     py+1
        cmp     fire_cy
        bne     @later
        jsr     fire_fetch
        bcs     @later          ; a key cut the read
        jmp     FIRE_RUN        ; fm_show
@later: inc     fire_dly+1      ; look again in 256 turns
@no:    rts
@run:   jmp     FIRE_RUN+3      ; fm_tick
; fire_hide -- (get_line's end, a turn of the view) the view without the
; fire again; the next prompt shows it soon. Preserves X.
fire_hide:
        lda     #FIRE_SOON
        sta     fire_dly+1
        lda     fire_st
        beq     :+
        jmp     FIRE_RUN+6      ; fm_hide
:       rts
fire_dly: .byte 0, FIRE_SOON    ; idle turns before the fire appears
fire_st: .byte  0               ; 1: the module is in its window, fire drawn

.segment "GCODE"
; fire_light -- (camp.s make_fire) the fire's place: px, py and its bearing,
; the heading (fire_pos = a copy of px, py, heading).
fire_light:
        ldx     #5
:       lda     px,x
        sta     fire_pos,x
        dex
        bpl     :-
        rts
.assert py = px + 2 && heading = px + 4, error, "fire_light copies px, py, heading"

; fire_fetch -- the module from NEOWILD.BLK into the SIM window, a key
; waiting between two blocks cutting the read: C set then (incomplete).
fire_fetch:
        lda     #0
        sta     sim_loaded      ; the window holds the fire, whole or not
        lda     #$80
        sta     df_kbd
        ldx     #FIRE_DIR
        jsr     sim_fetch
        lsr     df_kbd
        lda     df_left         ; blocks not read
        cmp     #1
        rts

; ----------------------------------------------------------------------------
; The module: directory entry 18, run in the SIM window. The fire is a local
; sprite of the player's cell at a fixed bearing, fire_bear (the heading when
; it was lit), placed like the local art of src/project.s (project_center):
; ang = fire_bear - heading in (-280, 280], 560 units a turn, one colour
; pixel a unit, the 140 pixels of the view a quarter turn; its 28 columns
; start at pixel 56 + ang, drawn if one of them is in 0..139. The rectangle
; is the five byte groups (35 pixels) from that of the first column, clipped
; to groups 0..19 (fm_k0..fm_k1); a row of it is composed in fm_tmp (k =
; 0..19: k & 1 main bank, else aux; screen offset 2 g0 + k / 2) from the
; saved background and the layers of tools/genfire.py, then only its bytes
; that differ from the screen are written. Variables and the background
; live past the image (FB_*), in the free SIM window.
FM_VARS  = FB_BG + 32*20        ; $A280 (FIRE_ROWS rows of 20 bytes)
fm_r     = FM_VARS              ; fm_setrow's row
fm_rr    = FM_VARS+1            ; row being drawn
fm_lo    = FM_VARS+2            ; its screen address
fm_hi    = FM_VARS+3
fm_blo   = FM_VARS+4            ; FB_BG offset: row * 20
fm_bhi   = FM_VARS+5
fm_frame = FM_VARS+6
fm_cnt   = FM_VARS+7            ; 2 bytes: idle turns to the next frame
fm_mask  = FM_VARS+9            ; 4 bytes: rows to draw
fm_p     = FM_VARS+13           ; phase of the pixel (column mod 7)
fm_g     = FM_VARS+14           ; 4 * its byte group in the rectangle
fm_bits  = FM_VARS+15
fm_n     = FM_VARS+16
fm_nb    = FM_VARS+17
fm_c     = FM_VARS+18
fm_m     = FM_VARS+19
fm_v     = FM_VARS+20
fm_y     = FM_VARS+21
fm_night = FM_VARS+22           ; bit 7: the glow
fm_w     = FM_VARS+23           ; bytes a row of the layer
fm_dirty = FM_VARS+24           ; bit 7: a frame left unfinished (a key)
fm_vis   = FM_VARS+25           ; bit 7: in view, drawn
fm_ph    = FM_VARS+26           ; phase of the first column (0..6)
fm_g0    = FM_VARS+27           ; its byte group on screen (signed)
fm_y0    = FM_VARS+28           ; 2 * fm_g0: screen offset of k = 0
fm_k0    = FM_VARS+29           ; first k on screen (0, 4 ... 16)
fm_k1    = FM_VARS+30           ; last k on screen (3, 7 ... 19)
fm_ytop  = FM_VARS+31           ; screen offset of fm_k1
fm_tmp   = FM_VARS+40           ; 20 bytes
.export fm_frame, fm_cnt, fm_dirty, fm_vis, fm_g0, fm_ph   ; (tests/test_fire.py)
.assert fm_tmp + 20 <= $A300, error, "FIRE: the buffers reach the grid (GRIDM)"

.segment "FIRE"
fire_module:
        jmp     fm_show
        jmp     fm_tick
        jmp     fm_hide
        .include "fire.inc"             ; build/, tools/genfire.py: data

; fm_show -- the place; in view: save the background of the rectangle,
; draw frame 0. Out of view nothing is drawn until fire_hide.
fm_show:
        lda     #0
        sta     fm_frame
        sta     fm_dirty
        sta     fm_vis
        inc     fire_st         ; the module is in its window, drawn or not
        lda     #FIRE_PERIOD
        sta     fm_cnt+1
        jsr     fm_frameptr
        ; d = fire_bear - heading, 0..559; in view when ang = d (d < 280)
        ; or d - 560 is in -83..83. A = L = first column + 35 = 91 + ang.
        sec
        lda     fire_bear
        sbc     heading
        tax
        lda     fire_bear+1
        sbc     heading+1
        bpl     :+
        tay                     ; + 560
        txa
        clc
        adc     #<560
        tax
        tya
        adc     #>560
:       cmp     #0
        bne     @hi
        cpx     #84
        bcs     @off            ; 84..255: out of view on the right
        txa
        adc     #91             ; C clear
        bcc     @place
@hi:    cmp     #2
        beq     @h2
        cpx     #221            ; 477..511: d - 469 = lo - 213
        bcc     @off            ; 256..476: out of view
        txa
        sbc     #213            ; C set
        bcs     @place
@h2:    txa                     ; 512..559: d - 469 = lo + 43
        adc     #42             ; C set
        bcc     @place
@off:   rts
@place: ldx     #$FA            ; g0 = L / 7 - 5, phase = L mod 7
:       inx
        sec
        sbc     #7
        bcs     :-
        adc     #7              ; C clear
        sta     fm_ph
        stx     fm_g0
        txa
        asl     a
        sta     fm_y0
        lda     #0              ; k0: the groups left of the view skipped
        cpx     #$80
        bcc     :+
        txa
        eor     #$FF
        adc     #0              ; C set: -g0
        asl     a
        asl     a
:       sta     fm_k0
        lda     fm_ph           ; the last group: g0 + 3, + 4 with a phase,
        cmp     #1              ; at most 19
        txa
        adc     #3
        cmp     #20
        bcc     :+
        lda     #19
:       sec
        sbc     fm_g0
        asl     a
        asl     a
        ora     #3
        sta     fm_k1
        lsr     a
        clc
        adc     fm_y0
        sta     fm_ytop
        sec
        ror     fm_vis
        lda     sky_mood        ; civil twilight to night: the glow
        cmp     #FIRE_NIGHT
        ror     fm_night
        php
        sei
        lda     #FIRE_ROWS-1
@save:  sta     fm_rr
        jsr     fm_setrow
        lda     fm_lo
        sta     @rd+1
        lda     fm_hi
        sta     @rd+2
        lda     fm_blo
        sta     @sv+1
        lda     #>FB_BG
        adc     fm_bhi          ; C clear (fm_setrow)
        sta     @sv+2
        ldx     fm_k1
@byte:  txa                     ; Y = 2 g0 + k / 2, bank k & 1
        lsr     a
        bcs     :+
        sta     PAGE2_AUX
        bcc     @y
:       sta     PAGE2_MAIN
@y:     clc
        adc     fm_y0
        tay
@rd:    lda     $2000,y
@sv:    sta     FB_BG,x
        cpx     fm_k0
        beq     @next
        dex
        bpl     @byte
@next:  lda     fm_rr
        sec
        sbc     #1
        bpl     @save
        sta     PAGE2_MAIN
        plp
        lda     #$FF            ; every row, frame 0
        sta     fm_mask+3
        sta     fm_mask+2
        sta     fm_mask+1
        sta     fm_mask
        lda     #FIRE_ROWS
        jmp     fm_rows

; fm_tick -- countdown; at its end the next frame, its changed rows only.
fm_tick:
        bit     fm_vis
        bpl     fm_rts
        dec     fm_cnt
        bne     fm_rts
        dec     fm_cnt+1
        bne     fm_rts
        lda     #FIRE_PERIOD
        sta     fm_cnt+1
        lda     fm_frame
        clc
        adc     #1
        and     #3
        sta     fm_frame
        jsr     fm_frameptr
        asl     a
        asl     a
        tax
        ldy     #0
:       lda     fire_changed,x
        sta     fm_mask,y
        inx
        iny
        cpy     #4
        bne     :-
        lda     #FIRE_FLAME_ROWS
        bit     fm_dirty        ; a frame left unfinished: every row
        bpl     fm_rows
        ldx     #$FF
        stx     fm_mask
        stx     fm_mask+1
        stx     fm_mask+2
        stx     fm_mask+3
        inx
        stx     fm_dirty
        lda     #FIRE_ROWS
; fm_rows -- A = rows 0..A-1 whose bit is set in fm_mask.
fm_rows:
        sta     fm_nb
        php
        sei
        lda     #0
@row:   sta     fm_rr
        bit     KBD             ; a key waits: leave the rest for later
        bmi     fm_abort
        lsr     fm_mask+3
        ror     fm_mask+2
        ror     fm_mask+1
        ror     fm_mask
        bcc     :+
        jsr     fm_row
:       lda     fm_rr
        clc
        adc     #1
        cmp     fm_nb
        bcc     @row
        plp
fm_rts: rts
fm_abort:
        sec
        ror     fm_dirty
        plp
        rts

; fm_frameptr -- the flame layer 2: frame fm_frame. Returns A = frame.
fm_frameptr:
        lda     #<fire_frames
        sta     fl_lo+2
        lda     #>fire_frames
        sta     fl_hi+2
        ldy     fm_frame
        beq     @done
:       lda     fl_lo+2
        clc
        adc     #FIRE_FRAME_SIZE
        sta     fl_lo+2
        bcc     :+
        inc     fl_hi+2
:       dey
        bne     :--
@done:  lda     fm_frame
        rts

; fm_hide -- the saved background back on screen; preserves X.
fm_hide:
        txa
        pha
        bit     fm_vis
        bpl     @done
        php
        sei
        lda     #FIRE_ROWS-1
@row:   sta     fm_rr
        jsr     fm_setrow
        jsr     fm_load
        jsr     fm_put
        lda     fm_rr
        sec
        sbc     #1
        bpl     @row
        plp
@done:  lda     #0
        sta     fire_st
        sta     fm_vis
        pla
        tax
        rts

; fm_row -- row fm_rr: background, static layer, glow, flames (layer 2),
; then the bytes that differ from the screen.
fm_row:
        lda     fm_rr
        jsr     fm_setrow
        jsr     fm_load
        ldx     #0
        jsr     fm_layer
        bit     fm_night
        bpl     :+
        ldx     #1
        jsr     fm_layer
:       ldx     #2              ; the flames
        jsr     fm_layer
        ; falls into fm_put

; fm_put -- fm_tmp to the screen row (fm_setrow), where it differs, k from
; fm_k1 down to fm_k0: the aux bytes (k even), then the main ones.
fm_put:
        lda     fm_lo
        sta     @cmp+1
        sta     @st+1
        lda     fm_hi
        sta     @cmp+2
        sta     @st+2
        sta     PAGE2_AUX
        ldx     fm_k1
        dex
        lda     fm_k0
        jsr     @pass
        sta     PAGE2_MAIN
        ldx     fm_k1
        lda     fm_k0
        ora     #1
@pass:  sta     @stop+1
        ldy     fm_ytop
@byte:  lda     fm_tmp,x
@cmp:   cmp     $2000,y
        beq     @same
@st:    sta     $2000,y
@same:  dey
@stop:  cpx     #0
        beq     @rts
        dex
        dex
        bpl     @byte
@rts:   rts

; fm_layer -- X = layer: its codes on row fm_rr (tools/genfire.py).
fm_layer:
        lda     fm_rr
        sec
        sbc     fl_r0,x
        bcc     @rts
        cmp     fl_rows,x
        bcc     :+
@rts:   rts
:
        tay
        lda     fl_pl,x
        sta     @pal+1
        lda     fl_ph,x
        sta     @pal+2
        lda     #0
        sta     fm_g
        lda     fl_col,x        ; + the phase of the first column: the
        clc                     ; layer's first pixel, group 0, 1 or 2
        adc     fm_ph
@grp:   cmp     #7
        bcc     :+
        sbc     #7              ; C set
        sta     fm_p
        lda     fm_g
        adc     #3              ; C set: + 4
        sta     fm_g
        lda     fm_p
        bcc     @grp            ; always
:       sta     fm_p
        lda     fl_w,x
        sta     fm_w
        lda     fl_hi,x
        sta     @src+2
        lda     fl_lo,x
        iny
@mul:   dey                     ; + (row - first row) * bytes a row
        beq     @go
        clc
        adc     fl_w,x
        bcc     @mul
        inc     @src+2
        bcs     @mul
@go:    sta     @src+1
@byte:
@src:   lda     $FFFF,y
        beq     @zero           ; four transparent pixels
        sta     fm_bits
        lda     #4
        sta     fm_n
@px:    lda     fm_bits
        and     #3
        beq     @next
        tax
@pal:   lda     $FFFF,x
        sta     fm_c
        jsr     fm_pixel
@next:  lsr     fm_bits
        lsr     fm_bits
        inc     fm_p
        lda     fm_p
        cmp     #7
        bne     :+
        lda     #0
        sta     fm_p
        lda     fm_g
        adc     #3              ; C set: + 4
        sta     fm_g
:       dec     fm_n
        bne     @px
@nextb: iny
        cpy     fm_w
        bne     @byte
        rts
@zero:  lda     fm_p            ; four columns on
        clc
        adc     #4
        cmp     #7
        bcc     :+
        sbc     #7              ; C set
        tax
        lda     fm_g
        adc     #3              ; C set: + 4
        sta     fm_g
        txa
:       sta     fm_p
        jmp     @nextb

; fm_pixel -- colour fm_c into the pixel of phase fm_p, group fm_g of
; fm_tmp (part A, then part B for phases 1, 3, 5). Preserves Y.
fm_pixel:
        sty     fm_y
        ldx     fm_p
        lda     ph_bitsa,x
        ldy     fm_ja,x
        jsr     fm_or
        ldx     fm_p
        lda     ph_bitsb,x
        ldy     fm_jb,x
        bmi     :+
        jsr     fm_or
:       ldy     fm_y
        rts
; fm_or -- A = the pixel's bits in byte j = Y of the group (0 aux 2g,
; 1 main 2g, 2 aux 2g+1, 3 main 2g+1): they take the colour (dc_pat, TN #3).
fm_or:  sta     fm_m
        tya
        clc
        adc     fm_g
        tax
        tya
        asl     a
        asl     a
        asl     a
        asl     a
        ora     fm_c
        tay
        lda     dc_pat,y
        eor     fm_tmp,x
        and     fm_m
        eor     fm_tmp,x
        sta     fm_tmp,x
        rts

; fm_setrow -- A = row r: fm_lo/fm_hi = the screen address (offset 0) of
; row y = FIRE_TOP + r (tools/genfire.py TOP, any row: the fire may cross a
; third), $2000 + (y & 7) * $400 + ((y >> 3) & 7) * $80 + (y >> 6) * $28;
; fm_blo/fm_bhi = r * 20 (the background). Returns C clear.
fm_setrow:
        sta     fm_r
        clc
        adc     #FIRE_TOP       ; y (fm_blo holds it until the end)
        sta     fm_blo
        and     #7
        asl     a
        asl     a
        sta     fm_hi           ; (y & 7) * 4
        lda     fm_blo
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        and     #3              ; ((y >> 3) & 7) >> 1
        ora     fm_hi
        ora     #$20
        sta     fm_hi
        lda     fm_blo
        asl     a
        asl     a
        asl     a
        asl     a
        and     #$80            ; (y & 8) * 16
        bit     fm_blo          ; N: third 2, V: third 1
        bmi     @t2
        bvc     @t0
        ora     #$28
        bvs     @t0             ; always
@t2:    ora     #$50
@t0:    sta     fm_lo
        lda     #0
        sta     fm_bhi
        lda     fm_r
        asl     a
        asl     a               ; r * 4
        sta     fm_blo
        asl     a
        asl     a               ; r * 16, bit 8 in C
        rol     fm_bhi          ; (C clear again)
        adc     fm_blo
        sta     fm_blo
        bcc     :+
        inc     fm_bhi
        clc
:       rts

; fm_load -- the saved background of the row (fm_setrow) into fm_tmp.
fm_load:
        lda     #>FB_BG
        clc
        adc     fm_bhi
        sta     @ld+2
        lda     fm_blo
        sta     @ld+1
        ldx     #19
@ld:    lda     FB_BG,x
        sta     fm_tmp,x
        dex
        bpl     @ld
        rts

fm_ja:  .byte   0, 0, 1, 1, 2, 2, 3             ; byte j of part A, phase 0..6
fm_jb:  .byte   $FF, 1, $FF, 2, $FF, 3, $FF     ; part B (phases 1, 3, 5)
.assert * <= FB_BG, error, "FIRE: the module must end below its buffers"
