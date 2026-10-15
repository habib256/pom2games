; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; stars_test.s -- standalone IIe bench of the night-sky stars (lot 7)
; ============================================================================
; ProDOS boots NEOSTARS.SYSTEM (src/stars_boot.s), which loads this program
; (STARTEST, $4000-$7FFF, then the star module and its BSS at $8000) and
; SCENE (case records at $A000, tests/test_stars.py), then runs it. The bench links
; the real engine pieces: src/dhgr.s (dhgr_frame, select_mood, column_setup,
; dspan, clear_rows), src/stars_draw.s and the module src/stars.s at $8000;
; the sky-zone loop of render_sky and the scroll of a turn are copied from
; src/wild.s (no terrain: the ridge is a 140-byte top profile per case).
;
; Case record (CASE_SIZE bytes; flags 0 ends the list):
;   +0 flags: bit 0 set, bit 1 stars on (stars_frame + stars_column),
;      bits 2-3 mode (0 full view, 1 columns c1-1 down to c0, 2 turn right
;      by 35: view at heading - 35, scroll, columns 105..139), bit 4 demo
;      (no checkpoint, ridge painted dark blue, wait for a key), bits 5-6
;      the tilt of the view (LOOK UP 1, LOOK DOWN 3: tilt_frame)
;   +1/+2 day  +3/+4 minute  +5 latitude  +6 longitude  +7/+8 sky_bearing
;   +9 sky_y  +10 night  +11 view_dark  +12 weather_sky  +13 sun_alt8
;   +14 moon_alt8  +15 moon_phase  +16/+17 heading  +18 c0  +19 c1
;   +20..+159 top of columns 0..139 (first terrain row, 0..160)
; Per case: stars_compute, checkpoint (the harness reads the list), page
; clear, dhgr_frame, stars_frame, columns, checkpoint (both banks).
; ============================================================================
        .include "apple2.inc"
        .macpack longbranch

STARS_BENCH = 1
STARS_ZP  = $B0                 ; module temporaries: above the bench zero page
VIEW_ROWS = 160
HUD_ROWS  = 16
HORIZON   = 95
UNITS     = 560
FOV_HALF  = 70
CASES     = $A000
CASE_SIZE = 160
CASE_TOP  = 20

        .import _prodos_video_claim
        .exportzp tmp1, tmp2
        .export checkpoint, cp_resume, finished, dt_go

.segment "ZEROPAGE"
ang:     .res 2                 ; the view engine's names (src/wild.s)
col:     .res 1
top:     .res 1
sp_end:  .res 1
hp:      .res 2
hp2:     .res 2
tmp:     .res 1
tmp2:    .res 1
row:     .res 1
shift:   .res 1
tmp1:    .res 1                 ; dev/lib/prodos/video.s
cp:      .res 2                 ; current case
tp:      .res 2                 ; its top profile
dt_go:   .res 1
c1:      .res 1
toff:    .res 1                 ; top index = col - toff

.segment "GDATA"
; Engine state read by dhgr.s / stars (src/game.s, sky.s, weather.s names).
night:       .byte 0
view_dark:   .byte 0
weather_sky: .byte 0
scene_asset: .byte 0
sky_bearing: .word 0
sky_y:       .byte 255
heading:     .word 0
bench_flags: .byte 0
MAP:         .res 64            ; header: +12 latitude, +25 longitude
M_LAT = MAP + 12
line_pix:    .res 140           ; dhgr_pack (unused here)
WNDTOP = $22

.segment "RODATA"
        .include "tables.inc"   ; build/, tools/gentables.py: sin_lo
.segment "LOWTEXT"
sky_outer: .byte 3,5,6,7,7,8,7,7,6,5,3          ; src/sky.s

; Unused engine entries referenced by src/dhgr.s.
.segment "CODE"
sky_position_core:
hud_draw:
        rts
sky_up = MAP + 32               ; ROM float scratch of sky_position (unused)
sky_sample = MAP + 40

        .include "dhgr.s"
        .include "stars_draw.s"
        .include "stars.s"

.segment "STARTUP"
start:  cld
        sei                     ; no IRQ source is used by the bench
        lda     #0
        sta     dt_go
        lda     #1              ; discard /RAM: the bench owns aux memory
        jsr     _prodos_video_claim
        sta     TXTCLR
        sta     MIXCLR
        sta     HIRES
        sta     COL80ON
        sta     DHIRES_ON
        sta     STORE80ON
        sta     LOWSCR          ; display page 1, main selected
        jsr     page_clear
        lda     #<CASES
        sta     cp
        lda     #>CASES
        sta     cp+1

next_case:
        ldy     #0
        lda     (cp),y
        bne     :+
finished:
        jmp     finished
:       sta     bench_flags
        ldy     #1              ; inputs
        lda     (cp),y
        sta     st_day
        iny
        lda     (cp),y
        sta     st_day+1
        iny
        lda     (cp),y
        sta     st_min
        iny
        lda     (cp),y
        sta     st_min+1
        iny
        lda     (cp),y
        sta     M_LAT
        iny
        lda     (cp),y
        sta     MAP+25
        iny
        lda     (cp),y
        sta     sky_bearing
        iny
        lda     (cp),y
        sta     sky_bearing+1
        iny
        lda     (cp),y
        sta     sky_y
        iny
        lda     (cp),y
        sta     night
        iny
        lda     (cp),y
        sta     view_dark
        iny
        lda     (cp),y
        sta     weather_sky
        iny
        lda     (cp),y
        sta     sun_alt8
        iny
        lda     (cp),y
        sta     moon_alt8
        iny
        lda     (cp),y
        sta     moon_phase
        iny
        lda     (cp),y
        sta     heading
        iny
        lda     (cp),y
        sta     heading+1
        clc
        lda     cp
        adc     #CASE_TOP
        sta     tp
        lda     cp+1
        adc     #0
        sta     tp+1
        ldx     #0              ; the module's inputs (the game: st_inputs):
        lda     bench_flags     ; tilt 1 (bits 5-6) is LOOK UP
        and     #$60
        cmp     #$20
        bne     :+
        inx
:       stx     st_up
        lda     sky_bearing
        sta     st_mb
        lda     sky_bearing+1
        sta     st_mb+1
        lda     sky_y           ; a Moon drawn at level (the up cases have none)
        cpx     #0
        bne     @nomoon
        cmp     #96
        bcs     @nomoon
        cmp     #16
        bcs     :+
@nomoon:
        lda     #$80
:       sta     st_mrow
        jsr     stars_compute   ; the module, in its window
        jsr     checkpoint      ; list: st_a, st_row, st_bucket
        jsr     page_clear
        lda     bench_flags     ; bits 5-6: tilt (0 level, 1 up, 3 down):
        lsr     a               ; X = tilt + 1 (LOOK UP / DOWN, dhgr.s)
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        clc
        adc     #1
        and     #3
        tax
        jsr     tilt_frame
        jsr     dhgr_frame
        lda     #0
        sta     star_thr
        lda     bench_flags
        and     #2
        beq     :+
        jsr     stars_frame
:       jsr     frame_columns
        jsr     checkpoint      ; both banks
        lda     bench_flags
        and     #$10
        beq     @advance
        bit     KBDSTRB
:       bit     KBD
        bpl     :-
        bit     KBDSTRB
@advance:
        clc
        lda     cp
        adc     #CASE_SIZE
        sta     cp
        bcc     :+
        inc     cp+1
:       jmp     next_case

; The harness stops at checkpoint (the polling loop), pokes dt_go = 1 and
; runs to cp_resume, which differs from checkpoint.
; Demo records (wait for a key) skip it: nobody pokes dt_go in POM2.
checkpoint:
        lda     bench_flags
        and     #$10
        bne     cp_resume
@poll:  lda     dt_go
        beq     @poll
cp_resume:
        lda     #0
        sta     dt_go
        rts

; page_clear -- both banks of $2000-$3FFF to zero.
page_clear:
        lda     #0
        sta     hp
        ldx     #$20
        sta     PAGE2_AUX
        jsr     @fill
        sta     PAGE2_MAIN
        lda     #0
        ldx     #$20
@fill:  stx     hp+1
        ldy     #0
:       sta     (hp),y
        iny
        bne     :-
        inc     hp+1
        ldx     hp+1
        cpx     #$40
        bcc     :-
        rts

; frame_columns -- the columns of the case's mode.
frame_columns:
        lda     bench_flags
        and     #$0C
        beq     @full
        cmp     #$04
        beq     @back
        ; turn right by 35 (src/wild.s view_turn X = 1): the previous view at
        ; heading - 35 (its columns 35..139), the scroll, the new columns.
        lda     heading
        pha
        lda     heading+1
        pha
        sec
        lda     heading
        sbc     #35
        sta     ang
        lda     heading+1
        sbc     #0
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     heading
        lda     ang+1
        sta     heading+1
        lda     #35
        sta     toff
        sta     col
        lda     #140
        sta     c1
        jsr     render_forward
        pla
        sta     heading+1
        pla
        sta     heading
        lda     #10
        sta     shift
        sec                     ; turning right: the view moves left
        jsr     scroll
        lda     #30             ; render_frame: clear the new bytes
        sta     tmp
        lda     #40
        sta     tmp2
        jsr     clear_rows
        lda     #0
        sta     toff
        lda     #105
        sta     col
        jmp     render_forward
@full:  lda     #0
        sta     toff
        sta     col
        lda     #140
        sta     c1
        jmp     render_forward
@back:  lda     #0              ; c1 - 1 down to c0
        sta     toff
        ldy     #19
        lda     (cp),y
        sec
        sbc     #1
        sta     col
        dey
        lda     (cp),y
        sta     c1
@bcol:  jsr     render_column
        lda     col
        cmp     c1
        beq     @bdone
        dec     col
        jmp     @bcol
@bdone: rts

render_forward:
        jsr     render_column
        inc     col
        lda     col
        cmp     c1
        bcc     render_forward
        rts

; render_column -- the sky of column `col` above its top (render_sky of
; src/wild.s: five mood zones clipped to the terrain), then its stars.
render_column:
        clc                     ; ang = heading - 70 + col
        lda     heading
        adc     col
        sta     ang
        lda     heading+1
        adc     #0
        sta     ang+1
        sec
        lda     ang
        sbc     #FOV_HALF
        sta     ang
        lda     ang+1
        sbc     #0
        sta     ang+1
        jsr     wrap_ang
        sec
        lda     col
        sbc     toff
        tay
        lda     (tp),y
        sta     top
        jsr     column_setup
        ldx     #0
        ldy     #0
@zone:  stx     dzone
        lda     sky_zone_end,x
        cmp     top
        bcc     :+
        lda     top
:       sta     sp_end
        lda     cur_zone,x
        jsr     scene_span
        ldy     sp_end
        ldx     dzone
        inx
        cpy     top
        bcc     @zone
        lda     bench_flags
        and     #2
        beq     :+
        jsr     stars_column
:       lda     bench_flags     ; demo: the ridge, dark blue / black dither
        and     #$10
        beq     :+
        lda     #VIEW_ROWS
        sta     sp_end
        ldy     top
        lda     #$20
        jsr     dspan
:       rts

; No sprite in the bench: scene_span is dspan (src/sprites.s, scene_opaque 0).
scene_span = dspan

; wrap_ang -- signed 16-bit ang into 0..559 (src/wild.s)
wrap_ang:
        lda     ang+1
        bpl     @hi
        clc
        lda     ang
        adc     #<UNITS
        sta     ang
        lda     ang+1
        adc     #>UNITS
        sta     ang+1
        rts
@hi:    lda     ang
        cmp     #<UNITS
        lda     ang+1
        sbc     #>UNITS
        bcc     @ok
        sta     ang+1
        lda     ang
        sbc     #<UNITS
        sta     ang
@ok:    rts

; scroll -- copied from src/wild.s: rows 16..175 of both banks by `shift`
; bytes, left when carry is set.
scroll: lda     #0
        rol     a
        tay
        php
        sei
        lda     #40
        sec
        sbc     shift
        tax
        cpy     #0
        beq     @right
        stx     band_stop+1
        lda     shift
        sta     band_sadd
        lda     #0
        sta     band_dadd
        sta     scroll_x
        lda     #$E8            ; INX
        bne     @set
@right: dex
        stx     scroll_x
        lda     #$FF
        sta     band_stop+1
        lda     #0
        sta     band_sadd
        lda     shift
        sta     band_dadd
        lda     #$CA            ; DEX
@set:   sta     band_step
        ldx     #HUD_ROWS/8
@band:  jsr     band_base
        lda     band_lo
        clc
        adc     band_sadd
        sta     band_slo
        lda     band_lo
        clc
        adc     band_dadd
        sta     band_dlo
        ldy     #7*6
        lda     band_hi
        clc
        adc     #7*4
        tax
@patch: lda     band_slo
        sta     band_copy+1,y
        lda     band_dlo
        sta     band_copy+4,y
        txa
        sta     band_copy+2,y
        sta     band_copy+5,y
        sbc     #3
        tax
        tya
        sec
        sbc     #6
        tay
        clc
        bpl     @patch
        sta     PAGE2_AUX
        ldx     scroll_x
        jsr     band_copy
        sta     PAGE2_MAIN
        ldx     scroll_x
        jsr     band_copy
        ldx     band_index
        inx
        cpx     #(VIEW_ROWS+HUD_ROWS)/8
        bne     @band
        plp
        rts
band_copy:
.repeat 8
        lda     $2000,x
        sta     $2000,x
.endrep
band_step:
        inx
band_stop:
        cpx     #30
        bne     band_copy
        rts

