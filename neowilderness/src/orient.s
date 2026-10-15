; Orientation (fidelity lot 7, docs/ORIENTATION.md): LOOK SUN, LOOK STARS,
; LOOK MAP/CHART/COMPASS/WATCH/ALTIMETER, the "direction aid in use" rule of
; LOOK N/E/S/W/AZ (COMPASS, WATCH with the Sun, shadow stick), USE MAP,
; COMPASS, WATCH, ALTIMETER, CHART and SHADOW. Original: T$0F/S$0F (LOOK
; with an object), T$10/S$0C (LOOK with a direction), T$11/S$00 $5BF9 and
; $5DAC (USE), T$0A/S$05 $58C4 (time spent ends the watch and the shadow).
; Every rule and number below was measured on the ROM by
; tools/re_orientation_probe.py.
;
; Placement (memory reclaim after lots 7 and 13, docs/MEMORY.md 13): LOOK,
; with its texts, dialogs, the Sun's azimuth and the shadow error (they run
; with SIM loaded), in the ORIENT module (ID 26); USE MAP...CHART, USE
; SHADOW, LOOK MAP and LOOK CHART in the TREE module (ID 20); resident in
; WILDLO the gates, in TEXT orient_number (numbers through INPUT, then ORIENT
; again); orient_ask's key dialog is ORIENT's (docs/MEMORY.md 15).

ORIENT_MODULE = 26

.segment "GDATA"
; B2[53], B2[54] and $4B4A of the original: bit 0 COMPASS in use, bit 1 WATCH
; in use, bit 2 shadow stick planted. USE of a family-6 object clears bits
; 0-1; USE SHADOW keeps only bit 2; spent time keeps only bit 0.
orient_aid: .byte 0
orient_lcg: .byte $F5,$CA,$66,$1D       ; SURV3D $0D2A state $BC-$BF (first view)

.segment "LOWCODE"
; orient_look -- first call of module_tree_look: the nouns of T$0F/S$0F
; (52-56) and of T$10/S$0C (N E S W, SUN STARS AZ) run the ORIENT module
; (MAP and CHART: USE in the TREE module); L R B F U D return to the
; resident LOOK.
orient_look:
        lda     noun
        cmp     #52
        bcc     orient_no
        cmp     #57
        bcc     orient_take
        cmp     #145
        bcc     orient_no
        cmp     #149
        bcc     orient_take
        cmp     #153
        bcc     orient_no
        cmp     #156
        bcs     orient_no
orient_take:
        pla                     ; replace the caller: the module ends the command
        pla
        lda     verb
        cmp     #V_PAN          ; PAN N, PAN SUN...: T$15/S$0A answers msg 2
        bne     :+
        lda     #<orient_sense
        ldx     #>orient_sense
        jmp     message
:       lda     verb            ; USE, LOOK MAP and LOOK CHART: the TREE
        cmp     #V_USE          ; module (module_orient_use)
        beq     @use
        lda     noun
        cmp     #52             ; MAP
        beq     @use
        cmp     #56             ; CHART
        beq     @use
        lda     #ORIENT_MODULE
        jsr     overlay_load
        jmp     module_orient_look
@use:   lda     #20
        jsr     overlay_load
        jmp     module_orient_use
orient_no:
        rts

; orient_use -- first call of do_medical: USE MAP...CHART (52-56), USE SHADOW.
orient_use:
        lda     verb
        cmp     #V_USE
        bne     orient_no
        lda     noun
        cmp     #174            ; SHADOW
        beq     orient_take
        cmp     #52
        bcc     orient_no
        cmp     #57
        bcc     orient_take
        rts

.segment "ORIENT"
; orient_ask -- X = dialog (OA_*): its message, then two keys (here) or a
; number read by INPUT (orient_number, resident); ORIENT comes back for the
; caller (its image is restored: state stays resident). C set: cancelled; a
; choice returns A = 0/1 (Z from it), a number msgnum and input_unit. Only
; ORIENT asks: the key dialog moved here from TEXT (docs/MEMORY.md 15).
orient_ask:
        stx     orient_dialog
        cpx     #OA_DEG
        jcs     orient_number
        lda     oa_lo,x         ; a text of the bank
        ldx     #0
        jsr     message
        ldx     orient_dialog
        cpx     #OA_NORTH
        jcs     orient_number
        jsr     prompt          ; $4D39: only the two keys (or ESC) answer
@key:   jsr     wait_key
        jsr     kbd_upcase
        ldx     orient_dialog
        cmp     #KC_ESC
        beq     @esc
        ldy     #1
        cmp     oa_one,x
        beq     @answer
        dey
        cmp     oa_zero,x
        bne     @key
@answer:
        tya
        clc
        rts
@esc:   lda     #<orient_cancel
        ldx     #>orient_cancel
        jsr     message
        sec
        rts
oa_one:  .byte 'Y','W'
oa_zero: .byte 'N','E'

.segment "TEXT"                 ; resident (WILDLO is full: docs/MEMORY.md 13)
; orient_number -- (orient_ask) X = dialog: the number through INPUT, which
; replaces ORIENT in $5800, then ORIENT again; returns to orient_ask's caller
; in the restored image.
orient_number:
        ldy     #3              ; degrees (0 is north)
        cpx     #OA_HOURS
        beq     :+
        cpx     #OA_TIME
        bne     @mode
:       ldy     #1              ; hours or minutes
@mode:  sty     input_mode
        lda     #0
        sta     input_argument
        lda     #13
        jsr     overlay_load
        jsr     module_number
        php
        lda     #ORIENT_MODULE
        jsr     overlay_load
        plp
        rts

orient_dialog: .res 1
orient_base:  .res 2            ; heading of the requested direction (units)
orient_sun_az: .res 2           ; the Sun's azimuth (units)
orient_south: .res 1            ; sin(dec) >= sin(lat): 12 pointed at the Sun
orient_flip:  .res 1            ; shadow tip said to move west
orient_min:   .res 2            ; observation (minutes)
orient_deg:   .res 2            ; signed degrees added to orient_base

.segment "LOWTEXT"

OA_WATCH  = 0                   ; msg 189/190, Y (1) or N (0)
OA_SHADOW = 1                   ; msg 29/30, W (1) or E (0)
OA_NORTH  = 2                   ; msg 13/14, then a number of degrees
OA_SOUTH  = 3                   ; msg 201/202, then a number of degrees
OA_HOURS  = 4                   ; msg 48, then a duration
OA_DEG    = 5                   ; a number of degrees (message already shown)
OA_TIME   = 6                   ; a duration (message already shown)

.segment "ORIENT"
; LOOK with noun 52-56 (T$0F/S$0F) or a direction (T$10/S$0C).
module_orient_look:
        lda     noun
        cmp     #57
        jcs     @direction
        cmp     #53             ; (MAP and CHART: USE, orient_take)
        beq     @compass
        tax                     ; WATCH, ALTIMETER
        jsr     have
        jcc     ol_missing
        lda     #<ol_status_msg
        ldx     #>ol_status_msg
        jmp     message
@compass:                       ; msg 256: heading - declination, degrees
        tax
        jsr     have
        jcc     ol_missing
        ldy     heading
        lda     heading+1
        jsr     GIVAYF
        fop     FMULT, ol_9_14
        fop     FADD, f_half
        jsr     AYINT
        ldx     #0
        lda     M_MAG
        bpl     :+
        dex
:       stx     g0
        sec
        lda     $A1
        sbc     M_MAG
        sta     msgnum
        lda     $A0
        sbc     g0
        sta     msgnum+1
        bpl     @high
        clc                     ; negative: + 360
        lda     msgnum
        adc     #<360
        sta     msgnum
        lda     msgnum+1
        adc     #>360
        sta     msgnum+1
@high:  lda     msgnum          ; 360 and more: - 360
        cmp     #<360
        lda     msgnum+1
        sbc     #>360
        bcc     @deg
        sta     msgnum+1
        lda     msgnum
        sbc     #<360
        sta     msgnum
@deg:        lda     #<ol_heading_msg
        ldx     #>ol_heading_msg
        jmp     message
@direction:
        lda     shelter_inside
        beq     :+
        lda     #<ol_inside_msg
        ldx     #>ol_inside_msg
        jmp     message
:       lda     noun
        cmp     #153            ; SUN
        jeq     ol_sun
        cmp     #154            ; STARS
        jeq     ol_stars
        lda     orient_aid
        bne     :+
        ldx     #53             ; port (14 October 2026): a COMPASS at hand
        jsr     have            ; is put in use, as USE COMPASS does (in
        bcc     @no_aid         ; hand, bit 0): the grid's NORTH..WEST turn
        lda     #3
        sta     it_place+53
        jsr     load_totals
        lda     #1
        sta     orient_aid
        bne     :+
@no_aid:
        lda     #<ol_aid_msg    ; msg 42: no compass
        ldx     #>ol_aid_msg
        jmp     message
:       lda     #0
        sta     orient_base
        sta     orient_base+1
        lda     noun
        cmp     #155            ; AZ: msg 43
        bne     @card
        lda     #<ol_az_msg
        ldx     #>ol_az_msg
        jsr     message
        ldx     #OA_DEG
        jsr     ol_degrees
        jcs     ol_done
        lda     msgnum
        sta     orient_deg
        lda     msgnum+1
        sta     orient_deg+1
        jsr     ol_add_deg
        jmp     @aid
@card:  sec                     ; N E S W -> 0, 140, 280, 420
        sbc     #145
        tax
        lda     card_lo,x
        sta     orient_base
        lda     card_hi,x
        sta     orient_base+1
@aid:   lda     orient_aid
        lsr     a
        bcc     @watch
        lda     #<orient_magnetic ; msg 44, then the ported magnetic heading
        ldx     #>orient_magnetic
        jsr     message
        jsr     ol_heading
        jmp     tree_look_aim
@watch: lsr     a
        jcc     ol_shadow
        jsr     ol_sun_seen     ; msg 41 when hidden
        jcc     ol_done
        ldx     #OA_WATCH       ; msg 189/190
        jsr     orient_ask
        jcs     ol_done
        beq     :+
        lda     #<m_ok          ; Y: the player uses LOOK SUN himself
        ldx     #>m_ok
        jsr     message
        jmp     show_view       ; the Sun's computation may have hidden the view
:       ldx     #OA_NORTH       ; msg 13/14, or 201/202
        lda     orient_south
        beq     :+
        inx
:       jsr     ol_degrees
        bcs     ol_done
        ; T$10/S$0C $5A3C: h = hour on a 12-hour dial, a = 57.296 h,
        ; heading = base + Sun + INT(-+.262 a) (+180 when INT(a) >= 344) - estimate
        fld     s_hour
        fop     FCOMP, f_12
        cmp     #1
        bne     :+
        fop     FSUB, f_12
        jsr     negate
:       fop     FMULT, ol_57
        fst     t1
        fop     FMULT, ol_262
        lda     orient_south
        bne     :+
        jsr     negate
:       jsr     AYINT
        sec
        lda     $A1
        sbc     msgnum
        sta     orient_deg
        lda     $A0
        sbc     msgnum+1
        sta     orient_deg+1
        fld     t1
        jsr     AYINT
        lda     $A1
        cmp     #<344
        lda     $A0
        sbc     #>344
        bcc     :+
        jsr     ol_half_turn
:       clc
        lda     orient_base
        adc     orient_sun_az
        sta     orient_base
        lda     orient_base+1
        adc     orient_sun_az+1
        sta     orient_base+1
        jsr     ol_add_deg
ol_view:
        jsr     ol_heading
        jmp     show_view
ol_done:
        rts
ol_missing:
        lda     #<m_noitem
        ldx     #>m_noitem
        jmp     message

; Shadow stick ($4B4A): msg 29/30 E or W, msg 48 hours, then the
; observation's minutes pass (0 cancels here; the original takes 10).
ol_shadow:
        ldx     #OA_SHADOW
        jsr     orient_ask
        bcs     ol_done
        sta     orient_flip
        ldx     #OA_HOURS
@ask:   jsr     orient_ask
        bcs     ol_done
        lda     msgnum
        sta     orient_min
        lda     msgnum+1
        sta     orient_min+1
        lda     input_unit
        cmp     #2
        beq     :+
        jsr     ol_mul60        ; hours (at most 255)
:       lda     orient_min      ; the original refuses 25 hours and more
        cmp     #<1500
        lda     orient_min+1
        sbc     #>1500
        bcc     @time
        lda     #<ol_long_msg
        ldx     #>ol_long_msg
        jsr     message
        ldx     #OA_TIME
        bne     @ask
@time:  lda     #3
        jsr     overlay_load
        jsr     orient_shadow_error
        lda     orient_flip
        beq     :+
        jsr     ol_half_turn
:       jsr     ol_add_deg
        jsr     ol_heading
        ; the clock runs as WAIT (spend clears the watch and the stick)
        lda     orient_min
        sta     msgnum
        lda     orient_min+1
        sta     msgnum+1
        lda     #2
        sta     input_unit
        sta     input_argument
        lda     #V_WAIT
        sta     verb
        jmp     do_rest

; LOOK SUN: msg 41 when hidden, else the view turns to the Sun.
ol_sun: jsr     ol_sun_seen
        bcc     ol_done
        lda     orient_sun_az
        sta     orient_base
        lda     orient_sun_az+1
        sta     orient_base+1
        jmp     ol_view

; LOOK STARS: msg 52 unless the night is clear ($4B49 + $4B4C < 0: night
; and clear sky); then the celestial pole, INT(LCG/4) - 33 degrees from
; north, +180 south of the equator ($60A8 < 0).
ol_stars:
        lda     night
        beq     :+
        lda     weather_sky
        beq     @clear
:       lda     #<ol_stars_msg
        ldx     #>ol_stars_msg
        jmp     message
@clear: clc                     ; SURV3D $0D2A
        ldx     #3
        lda     orient_lcg,x
        dex
@add:   adc     orient_lcg,x
        sta     orient_lcg,x
        dex
        bpl     @add
        ldx     #3
@inc:   inc     orient_lcg,x
        bne     :+
        dex
        bpl     @inc
:       lda     orient_lcg
        lsr     a
        lsr     a
        clc
        sbc     #32
        sta     orient_deg
        lda     #0
        sbc     #0
        sta     orient_deg+1
        lda     M_LAT
        bpl     :+
        jsr     ol_half_turn
:       lda     #0
        sta     orient_base
        sta     orient_base+1
        jsr     ol_add_deg
        jmp     ol_view

; ol_sun_seen -- C set when the Sun shows ($E0 = 0 and the light range
; $E1 >= 44: visibility V with V*L/(V+L) >= 88, L = 240 by day, 192 at
; dawn and dusk, i.e. V >= 139 or V >= 163); then orient_sun_az and
; orient_south. Otherwise msg 41 and C clear.
ol_sun_seen:
        lda     night
        bne     @hidden
        ldx     #139
        lda     period
        cmp     #2
        bcc     :+
        cmp     #4
        bcc     @range
:       ldx     #163
@range: stx     g0
        lda     weather_visibility
        cmp     g0
        bcc     @hidden
        lda     #3
        jsr     overlay_load
        jsr     orient_sun_core
        sec
        rts
@hidden:
        lda     #<ol_sun_msg
        ldx     #>ol_sun_msg
        jsr     message
        clc
        rts

; ol_degrees -- dialog X, then msgnum = 0..359 (msg 46 asks again)
ol_degrees:
        jsr     orient_ask
        bcs     @out
        lda     msgnum+1
        beq     @ok
        lsr     a
        bne     @over
        lda     msgnum
        cmp     #104            ; 360 = $168
        bcc     @ok
@over:  lda     #<ol_az_max_msg
        ldx     #>ol_az_max_msg
        jsr     message
        ldx     #OA_DEG
        bne     ol_degrees
@ok:    clc
@out:   rts

; ol_heading -- heading = orient_base
ol_heading:
        lda     orient_base
        sta     heading
        lda     orient_base+1
        sta     heading+1
        rts

; ol_half_turn -- orient_deg += 180
ol_half_turn:
        clc
        lda     orient_deg
        adc     #180
        sta     orient_deg
        bcc     :+
        inc     orient_deg+1
:       rts

; ol_add_deg -- orient_base += signed degrees orient_deg (nearest unit), 0..559
ol_add_deg:
        ldy     orient_deg
        lda     orient_deg+1
        jsr     GIVAYF
        fop     FMULT, f_deg_heading
        fop     FADD, f_half
        jsr     AYINT
        clc
        lda     orient_base
        adc     $A1
        sta     ang
        lda     orient_base+1
        adc     $A0
        sta     ang+1
        ldx     #3              ; up to three turns either way
:       jsr     wrap_ang
        dex
        bne     :-
        lda     ang
        sta     orient_base
        lda     ang+1
        sta     orient_base+1
        rts

; ol_mul60 -- orient_min = orient_min (hours, < 256) * 60
ol_mul60:
        lda     orient_min
        sta     g0
        lda     #0
        sta     orient_min
        sta     orient_min+1
        ldx     #60
@add:   clc
        lda     orient_min
        adc     g0
        sta     orient_min
        bcc     :+
        inc     orient_min+1
:       dex
        bne     @add
        rts

ol_57:    .byte $86,$65,$2F,$1A,$A0     ; 57.296 (T$10/S$0C $5AE7)
ol_262:   .byte $7F,$06,$24,$DD,$2F     ; .262 ($5AD8)
ol_9_14:  .byte $80,$24,$92,$49,$25     ; 9/14: units to degrees

; orient_sun_core -- (SIM loaded) the Sun of this hour: orient_sun_az
; (atan2(east, north) as src/sky.s, which skips it for a Sun out of the
; drawn sky) and orient_south (sin(dec) - sin(lat) >= 0: msg 201/202).
orient_sun_core:
        jsr     sky_position
        fld     sky_sinlat
        fop     FSUB, sky_sindec
        ldx     #0
        lda     FAC
        beq     :+
        lda     FACSGN
        bmi     :++
:       inx
:       stx     orient_south
        fld     sky_north
        lda     FAC
        beq     @eastwest
        fop     FDIV, sky_east
        jsr     FATN
        fop     FMULT, sky_units
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     ang
        lda     $A0
        sta     ang+1
        lda     sky_north+1
        bpl     @wrap
        clc
        lda     ang
        adc     #<280
        sta     ang
        lda     ang+1
        adc     #>280
        sta     ang+1
@wrap:  jsr     wrap_ang
        lda     ang
        ldx     ang+1
        jmp     @store
@eastwest:
        lda     #140
        ldx     #0
        ldy     sky_east+1
        bpl     @store
        lda     #<420
        ldx     #>420
@store: sta     orient_sun_az
        stx     orient_sun_az+1
        rts

; orient_shadow_error -- (SIM loaded) T$10/S$0C $59C4:
; orient_deg = INT((RND - .5) * 481 * (1 + .33 |12 - (hour + min/120)|) / min)
orient_shadow_error:
        ldy     orient_min
        lda     orient_min+1
        jsr     GIVAYF
        fst     t2
        fop     FMULT, os_00833
        fop     FADD, s_hour
        fop     FSUB, f_12
        lda     #0
        sta     FACSGN          ; ABS
        fop     FMULT, os_033
        fop     FADD, f_one
        fop     FMULT, os_481
        fst     t1
        jsr     weather_random  ; the original's RND ($0321)
        fop     FSUB, f_half
        jsr     negate
        fop     FMULT, t1
        fst     t1
        fld     t2
        fop     FDIV, t1
        jsr     AYINT
        lda     $A1
        sta     orient_deg
        lda     $A0
        sta     orient_deg+1
        rts
os_00833: .byte $7A,$08,$7A,$8D,$65     ; .00833 (T$10/S$0C $5AD3)
os_033:   .byte $7F,$28,$F5,$C2,$8F     ; .33 ($5ADD)
os_481:   .byte $89,$70,$80,$00,$00     ; 481 ($5AEC)

; Texts and dialogs (orient_ask prints them while this module is loaded).

oa_lo: .byte <oa_watch, <oa_shadow, <oa_north, <oa_south, <oa_hours

.segment "TREE"
; USE (T$11/S$00 $5BF9 family 6, $5DAC SHADOW).
module_orient_use:
        lda     noun
        cmp     #174
        bne     @object
        ; USE SHADOW: day (AM/PM) and clear sky ($4B49 - $4B4C = 1), else msg 53
        lda     period
        cmp     #2
        bcc     ou_dark
        cmp     #4
        bcs     ou_dark
        lda     weather_sky
        bne     ou_dark
        lda     #4
        bne     @set
@object:
        tax
        jsr     have
        jcc     ou_missing
        lda     orient_aid      ; COMPASS and WATCH stop being in use
        and     #4
        sta     orient_aid
        lda     noun
        cmp     #53
        beq     @light          ; the compass needs no light
        jsr     ou_light
        bcc     ou_dark
@light: lda     noun
        cmp     #56             ; CHART: msg 1
        bne     :+
        lda     #<ol_chart_msg
        ldx     #>ol_chart_msg
        jmp     message
:       tax
        lda     #3              ; in hand
        sta     it_place,x
        jsr     load_totals
        lda     noun
        cmp     #52
        bne     :+
        jmp     scr_topo        ; USE MAP: the map ($0D5B = 4, TOPO)
:       ldx     #0
        cmp     #55
        beq     @ok             ; ALTIMETER: in hand only
        inx
        cmp     #53
        beq     :+
        inx                     ; WATCH: bit 1
:       txa
        ora     orient_aid
@set:   sta     orient_aid
@ok:    lda     #<m_ok
        ldx     #>m_ok
        jmp     message
ou_dark:
        lda     #<ou_dark_msg   ; msg 53
        ldx     #>ou_dark_msg
        jmp     message

; ou_light -- C set when there is light ($0D5D, T$0D/S$0A): AM or PM, or
; dawn/dusk under a clear sky. Lamps (MATCHES, FLASHLIGHT in use) are not
; in the port yet.
ou_light:
        lda     period
        beq     @no
        cmp     #2
        bcc     @twilight
        cmp     #4
        bcc     @yes
@twilight:
        lda     weather_sky
        bne     @no
@yes:   sec
        rts
@no:    clc
        rts
ou_missing:
        lda     #<m_noitem
        ldx     #>m_noitem
        jmp     message
