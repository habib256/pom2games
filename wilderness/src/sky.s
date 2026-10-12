; Solar geometry follows the original seasonal declination and solar clock.
; Lunar ephemerides are a dated port extension (1985), not an original rule.
; Both bearings are geographic. A full lunar disk reveals the landscape,
; sites and fauna while the night sky remains black.
.segment "SCRATCH"
view_dark: .res 1              ; visual darkness, independent of night physiology
.segment "GDATA"
sky_enabled: .byte 1
sky_bearing: .word 0
sky_y: .byte 95
sky_waxing: .byte 0
.segment "ZEROPAGE"
sky_index: .res 1
sky_half: .res 1
sky_end: .res 1

.segment "THERMAL"
; The original clock is apparent solar time (solar noon = 12).
sky_position:
        lda     night
        sta     view_dark
        ldy     M_LAT
        lda     #0
        cpy     #128
        bcc     :+
        lda     #255
:       jsr     GIVAYF
        fop     FMULT, f_rad
        fst     sky_lat
        jsr     FSIN
        fst     sky_sinlat
        fld     sky_lat
        fop     FADD, f_half_pi
        jsr     FSIN
        fst     sky_coslat
        fld     f_12
        fop     FSUB, s_hour
        fop     FMULT, sky_pi12
        fst     sky_hour
        lda     night
        bne     @moon
        ; Original seasonal declination, also used for sunrise/sunset.
        fld     s_date
        fop     FMULT, f_2pi
        fop     FSUB, f_1_378
        jsr     negate
        jsr     FSIN
        fop     FMULT, f_0_398
        fst     sky_sindec
        jmp     @horizontal
@moon:  jsr     sky_lunar
        fld     sky_ra
        fop     FSUB, sky_hour
        fst     sky_hour
@horizontal:
        fld     sky_sindec
        fop     FMULT, sky_sindec
        fop     FSUB, f_one
        jsr     FSQR
        fst     sky_cosdec
        fld     sky_hour
        jsr     FSIN
        fop     FMULT, sky_cosdec
        jsr     negate
        fst     sky_east
        fld     sky_hour
        fop     FADD, f_half_pi
        jsr     FSIN
        fop     FMULT, sky_cosdec
        fst     sky_meridian
        fop     FMULT, sky_sinlat
        fst     sky_north
        fld     sky_sindec
        fop     FMULT, sky_coslat
        fop     FSUB, sky_north
        jsr     negate
        fst     sky_north
        fld     sky_sindec
        fop     FMULT, sky_sinlat
        fst     sky_up
        fld     sky_meridian
        fop     FMULT, sky_coslat
        fop     FADD, sky_up
        fst     sky_up
        ; The apparent Moon is about one degree lower (parallax).
        lda     night
        beq     :+
        fld     sky_up
        fop     FMULT, sky_up
        fop     FSUB, f_one
        jsr     FSQR
        fop     FMULT, f_rad
        fop     FSUB, sky_up
        fst     sky_up
:       lda     sky_up+1
        jmi     sky_hidden
        lda     sky_up
        jeq     sky_hidden
        fld     sky_east
        fop     FMULT, sky_east
        fst     sky_lat
        fld     sky_north
        fop     FMULT, sky_north
        fop     FADD, sky_lat
        jsr     FSQR
        lda     FAC
        jeq     sky_hidden       ; zenith is outside the forward view
        fop     FDIV, sky_up
        fop     FMULT, sky_48     ; same vertical perspective as terrain
        jsr     AYINT
        lda     $A0
        jne     sky_hidden
        lda     $A1
        cmp     #HORIZON+1
        jcs     sky_hidden
        sta     sky_y
        sec
        lda     #HORIZON
        sbc     sky_y
        sta     sky_y
        ; atan2(east,north), clockwise from geographic north.
        fld     sky_north
        lda     FAC
        beq     @eastwest
        fop     FDIV, sky_east
        jsr     FATN
        fop     FMULT, sky_units
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     sky_bearing
        lda     $A0
        sta     sky_bearing+1
        lda     sky_north+1
        bpl     @wrap
        clc
        lda     sky_bearing
        adc     #<280
        sta     sky_bearing
        lda     sky_bearing+1
        adc     #>280
        sta     sky_bearing+1
@wrap:  lda     sky_bearing
        sta     ang
        lda     sky_bearing+1
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     sky_bearing
        lda     ang+1
        sta     sky_bearing+1
        rts
@eastwest:
        lda     #140
        ldx     #0
        ldy     sky_east+1
        bpl     :+
        lda     #<420
        ldx     #>420
:       sta     sky_bearing
        stx     sky_bearing+1
        rts
sky_hidden:
        lda     #255
        sta     sky_y
        rts

; Interpolate UT ephemerides over two days. The date's fractional day is
; seasonal state in the original, so take the civil day plus the clock.
sky_lunar:
        fld     s_date
        fop     FMULT, f_365
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        fst     sky_day
        fld     s_hour
        fop     FMULT, sky_inv24
        fop     FADD, sky_day
        fst     sky_day
        ldy     MAP+25           ; added longitude, east positive
        lda     #0
        cpy     #128
        bcc     :+
        lda     #255
:       jsr     GIVAYF
        fop     FMULT, sky_inv360
        fop     FSUB, sky_day
        fop     FMULT, f_half
        fst     sky_day
        jsr     AYINT
        lda     $A1
        sta     sky_sample
        tay
        lda     $A0
        jsr     GIVAYF
        fop     FSUB, sky_day
        fst     sky_fraction
        lda     sky_sample
        asl
        sta     gp1
        lda     #0
        rol
        sta     gp1+1
        clc
        lda     gp1
        adc     sky_sample
        sta     gp1
        lda     gp1+1
        adc     #0
        sta     gp1+1
        clc
        lda     gp1
        adc     #<sky_ephemeris
        sta     gp1
        lda     gp1+1
        adc     #>sky_ephemeris
        sta     gp1+1
        lda     #0
        sta     sky_field
@field: ldy     sky_field
        lda     (gp1),y
        sta     sky_first
        iny
        iny
        iny
        lda     (gp1),y
        sec
        sbc     sky_first         ; cyclic RA/phase difference, signed
        tay
        lda     #0
        cpy     #128
        bcc     :+
        lda     #255
:       jsr     GIVAYF
        fop     FMULT, sky_fraction
        fst     sky_lat
        ldy     sky_first
        lda     #0
        ldx     sky_field
        cpx     #1
        bne     :+
        cpy     #128
        bcc     :+
        lda     #255             ; declination is signed, RA/phase unsigned
:       jsr     GIVAYF
        fop     FADD, sky_lat
        ldx     sky_field
        beq     @ra
        dex
        beq     @dec
        ; Quantised phase art: subtract a shifted disk, mirror when waning.
        fop     FMULT, sky_tau256
        fop     FADD, f_half_pi
        jsr     FSIN
        fop     FSUB, f_one
        fop     FMULT, sky_5half
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     sky_sample
        cmp     #11             ; full disk in the phase artwork
        bne     :+
        lda     #0
        sta     view_dark
:
        ldy     #10
@shape: tya
        sec
        sbc     sky_sample
        tax
        lda     #255
        cpx     #11
        bcs     :+
        lda     sky_outer,x
:       sta     sky_inner,y
        dey
        bpl     @shape
        ; RA offset's sign relative to a half turn distinguishes waxing.
        fld     sky_ra
        fop     FCOMP, sky_pi
        cmp     #255
        lda     #0
        adc     #0
        sta     sky_waxing
        rts
@ra:    fop     FMULT, sky_tau256
        fst     sky_ra
        jmp     @next
@dec:   fop     FMULT, sky_quarter_rad
        jsr     FSIN
        fst     sky_sindec
@next:  inc     sky_field
        jmp     @field

; These values live only inside sky_position/sky_lunar, which never BLOAD.
; DOS has already restored its text backup before either routine starts.
; Reuse that buffer rather than storing temporary floats in the SIM image.
sky_lat      = overlay_text
sky_sinlat   = sky_lat+5
sky_coslat   = sky_sinlat+5
sky_sindec   = sky_coslat+5
sky_cosdec   = sky_sindec+5
sky_hour     = sky_cosdec+5
sky_meridian = sky_hour+5
sky_east     = sky_meridian+5
sky_north    = sky_east+5
sky_up       = sky_north+5
sky_ra       = sky_up+5
sky_fraction = sky_ra+5
sky_day      = sky_fraction+5
sky_sample   = sky_day+5
sky_first    = sky_sample+1
sky_field    = sky_first+1
.assert sky_field < overlay_text+160, error, "Sky scratch exceeds DOS text buffer"
sky_pi12: .byte $7F,$06,$0A,$91,$C1
sky_48: .byte $86,$40,0,0,0
sky_5half: .byte $83,$30,0,0,0
sky_units: .byte 135,50,64,231,193
sky_inv24: .byte 124,42,170,170,171
sky_inv360: .byte 120,54,11,96,182
sky_tau256: .byte 123,73,15,218,162
sky_quarter_rad: .byte 121,14,250,53,19
        .include "sky_ephemeris.inc"

.segment "TEXT"
sky_pi: .byte 130,73,15,218,162
; Called only for remaining sky, after foreground terrain/sprites.
sky_column:
        lda     sky_enabled
        beq     @done
        lda     weather_sky
        bne     @done
        lda     sky_y
        cmp     #HORIZON+1
        bcs     @done
        jsr     sky_difference
        bcs     @done
        stx     sky_index
        lda     sky_outer,x
        sta     sky_half
        clc
        adc     sky_y
        adc     #1
        sta     sky_end
        sec
        lda     sky_y
        sbc     sky_half
        bcs     :+
        lda     #0
:       tay
        lda     night
        beq     @disk
        jsr     sky_moon_half
        bmi     @disk
        ; Moon phase art: outer disk minus a disk shifted by illumination.
        sta     sky_half
        sec
        lda     sky_y
        sbc     sky_half
        jsr     sky_span
        clc
        lda     sky_y
        adc     sky_half
        adc     #1
        tay
@disk:  lda     sky_end
        jmp     sky_span
@done:  rts

.segment "CODE"
; A = end, Y = start. Clip to the terrain and preserve opaque sprites.
sky_span:
        cmp     top
        bcc     :+
        lda     top
:       sta     sp_end
        lda     #C_SNOW
        jmp     scene_span

.segment "LOWTEXT"
sky_outer: .byte 3,5,6,7,7,8,7,7,6,5,3
sky_inner: .byte 255,255,3,5,6,7,7,8,7,7,6

.segment "GCODE"
sky_difference:
        ; d = (ray - body + 5) modulo 560: seamless at geographic north.
        sec
        lda     ang
        sbc     sky_bearing
        sta     sky_half
        lda     ang+1
        sbc     sky_bearing+1
        sta     sky_index
        clc
        lda     sky_half
        adc     #5
        sta     sky_half
        lda     sky_index
        adc     #0
        sta     sky_index
        bpl     :+
        clc
        lda     sky_half
        adc     #<560
        sta     sky_half
        lda     sky_index
        adc     #>560
        jmp     @check
:       cmp     #2
        bcc     @check
        ldx     sky_half
        cpx     #<560
        bcc     @check
        sec
        lda     sky_half
        sbc     #<560
        sta     sky_half
        lda     #0
@check: cmp     #0
        bne     @off
        ldx     sky_half
        cpx     #11
        rts
@off:   sec
        rts
.segment "TEXT"
sky_moon_half:
        lda     sky_waxing
        beq     :+
        txa
        eor     #255
        clc
        adc     #11
        tax
:       lda     sky_inner,x
        rts
