; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.segment "TRAVEL"

; T0A/S05 scans small game and fish even during meals and WAIT. REST/CAMP
; skip their probability rolls. These draws share SMALLDOS's Lehmer state
; with the wind and compass; omitting them desynchronizes later weather.
module_stationary_resources:
resource_scan:
        lda     #0
        sta     MAP+36          ; discoveries awaiting their native quantities
        lda     act
        cmp     #1
        bne     @stationary
        lda     #0
        sta     resource_seen
        ldx     #7
@clear: sta     MAP+26,x
        dex
        cpx     #1
        bne     @clear
        lda     MAP+37
        beq     :+
        lda     #0
        sta     MAP+16          ; the native found shelter belongs to this cell
:
        jsr     weather_random  ; T0A/S00 $599C: injury check, including zero risk
        lda     #0
        beq     @start
@stationary:
        jsr     resource_retention
        ldx     #3
@home:  lda     px,x
        cmp     M_STARTX,x
        bne     @away
        dex
        bpl     @home
        lda     #11             ; native $0A suppresses animals at the crash
        bne     @start
@away:  lda     #7              ; stationary T0A/S05 scans animals too elsewhere
@start: sta     resource_phase
@species:
        ldx     resource_phase
        lda     resource_order,x
        sta     resource_species
        tax
        lda     resource_offsets,x
        tax
        ldy     #0
@pair:  lda     fauna_env,y
        sec
        sbc     resource_ranges,x
        bcs     :+
        eor     #255
        clc
        adc     #1
:       sta     fauna_delta
        inx
        lda     resource_ranges,x
        bmi     @outside
        beq     @different
        cmp     fauna_delta
        jcc     @next
        bcs     @match
@outside:
        eor     #255
        clc
        adc     #1
        cmp     fauna_delta
        jcs     @next
        bcc     @match
@different:
        lda     fauna_delta
        jeq     @next
@match: inx
        iny
        cpy     #6
        bne     @pair
        ldy     MAP+22
        bne     :+
        ldy     #4
:       lda     #0
        jsr     GIVAYF
        jsr     FSQR
        fst     resource_threshold
        lda     resource_species
        cmp     #4
        bcc     @animal
        cmp     #12
        beq     @shelter
        lda     verb
        cmp     #V_REST
        jeq     @next
        cmp     #V_CAMP
        jeq     @next
        jsr     weather_random
        fop     FMULT, resource_tenth
        fst     t1
        fld     resource_threshold
        fop     FDIV, t1
        jmp     @roll
@shelter:
        lda     fauna_env+2
        cmp     #10             ; native clear terrain never finds a shelter
        jeq     @next
        fld     resource_threshold
        fop     FDIV, resource_shelter
        jmp     @roll
@animal:
        ldy     scene_minutes
        lda     #0
        jsr     GIVAYF
        fop     FMULT, resource_threshold
        fop     FMULT, resource_animal_k
        fst     t1
        ldx     resource_species
        ldy     resource_animal_rates,x
        lda     #0
        jsr     GIVAYF
        fop     FMULT, t1
@roll:  fst     resource_threshold
        jsr     weather_random
        fop     FCOMP, resource_threshold
        cmp     #$FF
        jne     @next
        ldx     resource_species
        cpx     #4
        bcs     @resource
        stx     fauna_species
        jsr     fauna_accept
        jmp     @next
@resource:
        lda     act
        cmp     #1
        bne     :+
        lda     #1
        sta     fauna_alert     ; native discoveries interrupt the current walk
:
        lda     resource_bits,x
        ora     resource_seen
        sta     resource_seen
        lda     resource_bits,x
        ora     MAP+36
        sta     MAP+36
        cpx     #12
        jne     @next
        lda     #1
        sta     MAP+16
        lda     px+1
        sta     MAP+17
        lda     py+1
        sta     MAP+18
        lda     px
        sta     MAP+34
        lda     py
        sta     MAP+35
        lda     heading
        sta     MAP+19
        lda     heading+1
        sta     MAP+20
@next:  inc     resource_phase
        lda     act
        cmp     #1
        bne     :+
        lda     resource_phase
        cmp     #7
        beq     @pause          ; wind/health precede the stationary animal scan
:
        lda     resource_phase
        cmp     #13
        jcc     @species
@done:  lda     #0
        sta     scene_minutes   ; a subsequent VIEW must not reroll the activity
        jmp     native_resource_results
@pause: rts
.export resource_scan_species := @species
module_stationary_resources_tail:
        lda     #7
        sta     resource_phase
        jmp     resource_scan_species
resource_order: .byte 6,7,8,9,10,11,12,0,1,2,3,4,5
resource_bits: .byte 0,0,0,0,1,2,4,8,16,32,64,128,0
resource_offsets: .byte 0,12,24,36,48,60,72,84,96,108,120,132,144
resource_ranges:
        .byte 50,34,11,252,15,6,55,25,25,25,30,20
        .byte 50,50,12,251,10,12,50,40,35,35,30,20
        .byte 58,25,12,6,5,6,40,40,30,30,30,20
        .byte 0,0,0,0,0,0,0,0,0,0,0,0
        .byte 55,37,13,9,15,6,55,55,30,30,75,65
        .byte 50,50,13,9,35,6,60,60,15,15,75,65
        .byte 55,37,14,9,20,25,50,50,45,45,75,65
        .byte 60,20,13,9,15,6,50,50,30,30,75,60
        .byte 50,50,12,12,10,11,50,50,35,35,7,7
        .byte 55,32,13,9,20,5,40,40,15,15,80,60
        .byte 55,32,12,12,15,6,55,55,30,30,75,60
        .byte 58,20,13,9,15,6,50,50,30,30,75,60
        .byte 50,50,13,9,10,11,120,120,45,45,70,70
resource_tenth: .byte $7D,$4C,$CC,$CC,$CD
resource_shelter: .byte $7C,$4C,$CC,$CC,$CD
resource_animal_rates: .byte 80,40,100,0
resource_animal_k: .byte $70,$27,$C5,$AC,$48
resource_phase: .byte 0
resource_species: .byte 0
resource_threshold: .res 5
.segment "TRAVEL"

; Native T08/S07: one injury-probability preparation roll, followed by
; 180 * (total pounds + abs(body adjustment)) / body pounds / speed.
; The Sierra starting character has a +2 lb body adjustment.
module_walk_prepare:
        lda     MAP+37
        beq     :+
        lda     animal_kind
        beq     :+
        lda     #0
        sta     scene_minutes   ; distinguishes preparation from a timed reaction
        jmp     animal_attack   ; resident loader: TRAVEL is replaced by OUTDOOR
:
        jsr     weather_random
        jsr     travel_pounds
        fop     FADD, trv_adjust
        fst     t1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FDIV, t1
        fop     FMULT, trv_180
        fst     t1
        fld     walk_speed
        lda     verb
        cmp     #V_RUN
        bne     :+
        fld     walk_run_speed
:       fop     FDIV, t1
        fst     walk_factor
        jmp     module_swim_prepare

; T09/S00: each original-unit raster step has its own terrain, weather,
; daylight and health cost. Positive rises also add a separate calorie cost.
module_walk_step:
        lda     #0
        sta     walk_rise
        lda     g0
        sec
        sbc     g1
        bcc     :+
        sta     walk_rise
:       lda     weather_sky
        clc
        adc     #5
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, walk_factor
        fst     walk_scale
        fld     s_health
        jsr     FSQR
        fst     t1
        ldy     #5
        lda     night
        bne     :+
        iny
:       lda     #0
        jsr     GIVAYF
        fop     FMULT, t1
        fop     FDIV, walk_scale
        fst     walk_scale
        fld     f_zero
        lda     walk_rise
        beq     @base
        tay
        lda     #0
        jsr     GIVAYF
        fst     walk_height
        fld     walk_slope_unit
        fop     FDIV, walk_height
        jsr     FATN
        fop     FMULT, f_2
        jsr     $EFEA
        fop     FMULT, walk_nine
        fop     FSUB, walk_eleven
        fst     t1
        jsr     travel_pounds
        fop     FADD, trv_adjust
        fst     t2
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FDIV, t2
        fop     FMULT, t1
        fop     FMULT, walk_height
        fop     FMULT, walk_rise_cost
@base:  lda     wdx
        ora     wdx+1
        beq     @straight
        lda     wdy
        ora     wdy+1
        beq     @straight
        fop     FADD, trv_diagonal
        jmp     @time
@straight:
        fop     FADD, trv_straight
@time:  fop     FMULT, walk_scale
        fop     FADD, f_half
        jsr     AYINT
        lda     $A0
        bne     @bad
        lda     $A1
        beq     @bad
        sta     stepmin
        clc
        rts
@bad:   sec
        rts

module_walk_climb:
        lda     walk_rise
        beq     @done
        tay
        lda     #0
        jsr     GIVAYF
        fst     t1
        jsr     travel_pounds
        fop     FMULT, t1
        fop     FMULT, walk_climb_energy
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        fop     FADD, s_spent
        fst     s_spent
@done:  rts

walk_speed: .byte $82,$40,0,0,0 ; 3 miles/hour
walk_run_speed: .byte $84,$10,0,0,0 ; 9
walk_nine: .byte $84,$10,0,0,0
walk_eleven: .byte $84,$30,0,0,0
walk_slope_unit: .byte $85,$4C,$3A,$FB,$7E ; native 25.5288
walk_rise_cost: .byte $7D,$19,$99,$99,$9A ; .075
walk_climb_energy: .byte $7E,$4C,$CC,$CC,$CD ; .2
walk_scale: .res 5
walk_height: .res 5
.segment "GDATA"
resource_seen: .byte 0
walk_factor: .res 5
walk_rise: .byte 0
.segment "TRAVEL"

; Original T08/S07 $5BFB-$5C94 prepares an integer major coordinate and
; a sine-driven minor accumulator; T09/S00 $5B35 rounds the minor each step.
module_swim_prepare:
        lda     heading+1
        ldy     heading
        jsr     GIVAYF
        fst     t1
        fld     f_deg_heading
        fop     FDIV, t1        ; map the 560 azimuths back to original degrees
        fop     FADD, f_half
        jsr     AYINT
        sec
        lda     #90
        sbc     $A1
        sta     num
        lda     #0
        sbc     $A0
        sta     num+1
        bpl     @angle
        clc
        lda     num
        adc     #<360
        sta     num
        lda     num+1
        adc     #>360
        sta     num+1
@angle: lda     #0
        sta     travel_axis
        sta     travel_sign
        lda     num+1
        beq     @low
        lda     num
        cmp     #59            ; angle < 315
        bcc     @yminus
        bcs     @slope
@low:   lda     num
        cmp     #46
        bcc     @slope
        cmp     #135
        bcc     @yplus
        cmp     #226
        bcs     @yminus
        lda     #$FF
        sta     travel_sign
        bne     @slope
@yminus:
        lda     #$FF
        sta     travel_sign
@yplus:
        inc     travel_axis
@slope: lda     num+1
        ldy     num
        jsr     GIVAYF
        fop     FMULT, trv_rad
        lda     travel_axis
        beq     :+
        fop     FSUB, trv_half_pi ; original cos = SIN(pi/2 - angle)
:       jsr     FSIN
        fst     travel_delta
        ; Original coordinates are integers in half-map-cell units.
        lda     px
        asl
        lda     px+1
        rol
        sta     g0
        lda     py
        asl
        lda     py+1
        rol
        sta     g1
        ldx     travel_axis
        lda     g0,x
        sta     travel_major
        txa
        eor     #1
        tax
        ldy     g0,x
        lda     #0
        jsr     GIVAYF
        fst     travel_accum
        rts

module_swim_next:
        lda     travel_sign
        bmi     @minus
        inc     travel_major
        jmp     @minor
@minus: dec     travel_major
@minor: fld     travel_accum
        fop     FADD, travel_delta
        fst     travel_accum
        fld     travel_accum
        fop     FADD, f_half
        jsr     AYINT
        ldx     travel_axis
        lda     travel_major
        sta     g0,x
        txa
        eor     #1
        tax
        lda     $A1
        sta     g0,x
        .repeat 2, I
        lda     g0+I
        lsr
        sta     nx+2*I+1
        lda     #0
        ror
        sta     nx+2*I
        sec
        sbc     px+2*I
        sta     wdx+2*I
        lda     nx+2*I+1
        sbc     px+2*I+1
        sta     wdx+2*I+1
        .endrepeat
        rts

trv_rad:     .byte $7B,$0E,$FA,$35,$37
trv_half_pi: .byte $81,$49,$0F,$DA,$D5

; A land destination is permitted when leaving water, or when the next
; raster half-step enters water. WALK stops a full cell before water, so
; rejecting the first land half-step would make SWIM impossible from shore.
; Probe without committing position, time, or the raster's next-step state.
module_swim_land:
        jsr     native_here
        bpl     @entry
        lda     #1
        sta     travel_shore
        sec
        rts
@entry: ldx     #3
@save:  lda     nx,x
        pha
        lda     wdx,x
        pha
        dex
        bpl     @save
        lda     travel_major
        pha
        ldx     #4
@float: lda     travel_accum,x
        pha
        dex
        bpl     @float
        jsr     module_swim_next
        lda     nx+1
        cmp     #2
        bcc     @no
        cmp     #GW-2
        bcs     @no
        lda     ny+1
        cmp     #2
        bcc     @no
        cmp     #GH-2
        bcs     @no
        jsr     native_next
        bpl     @no
        sec
        bcs     @restore
@no:    clc
@restore:
        php
        pla
        sta     trv_admitted
        ldx     #0
@unfloat:
        pla
        sta     travel_accum,x
        inx
        cpx     #5
        bne     @unfloat
        pla
        sta     travel_major
        ldx     #0
@unsave:
        pla
        sta     wdx,x
        pla
        sta     nx,x
        inx
        cpx     #4
        bne     @unsave
        lda     trv_admitted
        pha
        plp
        bcs     @done
        lda     #8
        sta     travel_reason
        clc
@done:  rts
trv_admitted: .byte 0

; Normal swimming, T08/S07 $5B51 and T09/S00 $5909-$59CC.
; Default original modifiers: $4BBE=2, $4B49=1, $4B4C=0.
; Terrain/equipment and illness changes to those modifiers remain to port.
module_swim_step:
        jsr     travel_pounds
        fop     FADD, trv_adjust
        fst     t1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FDIV, t1
        fop     FMULT, trv_180
        fst     t1
        fld     s_health
        jsr     FSQR
        fst     t2
        fld     trv_six
        fop     FMULT, t2
        fst     t2
        fld     trv_five
        fop     FMULT, t1
        fst     t1
        fld     t2
        fop     FDIV, t1
        fst     t1
        lda     wdx
        ora     wdx+1
        beq     @straight
        lda     wdy
        ora     wdy+1
        beq     @straight
        fld     trv_diagonal
        jmp     @duration
@straight:
        fld     trv_straight
@duration:
        fop     FMULT, t1
        fop     FADD, f_half
        jsr     AYINT
        lda     $A0
        bne     @unsupported    ; spend currently accepts only byte durations
        lda     $A1
        beq     @unsupported
        sta     stepmin
        clc
        rts
@unsupported:
        sec
        rts

; Original float encodings, including their final mantissa bits.
trv_adjust:   .byte $82,$00,$00,$00,$00 ; 2 ($4BBE initial modifier)
trv_180:      .byte $88,$34,$00,$00,$00
trv_five:     .byte $83,$20,$00,$00,$00
trv_six:      .byte $83,$40,$00,$00,$00
trv_straight: .byte $7F,$4C,$CC,$CC,$CD ; .4
trv_diagonal: .byte $80,$11,$26,$E9,$79 ; .567

; T08/S07 $5AE7/$5D3A: swimming costs .06 * total pounds + basal rate.
; $50A1 truncates carried ounces / 16 before adding body pounds.
 .segment "ENVIRON"
module_swim_metabolic:
        jsr     travel_pounds
        fop     FMULT, f_swim_k
        fop     FADD, f_rest_rate
        rts

module_land_metabolic:
        jsr     travel_pounds
        fop     FMULT, walk_metabolic_k
        fop     FADD, f_rest_rate
        rts
walk_metabolic_k: .byte $7B,$0B,$43,$95,$82 ; .017

travel_pounds:
        lda     load_used
        sta     num
        lda     load_used+1
        sta     num+1
        ldx     #4
@shift: lsr     num+1
        ror     num
        dex
        bne     @shift
        clc
        lda     num
        adc     body_weight
        tay
        lda     num+1
        adc     body_weight+1
        jsr     GIVAYF
        rts

.segment "GDATA"
resource_retention_due: .byte 0
.segment "TRAVEL"
; T0A/S05 initial activity pass: game/fish already sighted can leave with
; probability dt/128. Subsequent intervals in this activity skip this pass.
resource_retention:
        lda     resource_retention_due
        beq     @done
        lsr     resource_retention_due
        lda     #1
        sta     resource_phase
@loop: lda     resource_phase
        and     resource_seen
        beq     @next
        ldy     scene_minutes
        lda     #0
        jsr     GIVAYF
        lda     FAC
        sec
        sbc     #7
        sta     FAC             ; dt / 128
        fst     resource_threshold
        jsr     weather_random
        fop     FCOMP, resource_threshold
        cmp     #$FF
        bne     @next
        lda     resource_phase
        eor     #255
        and     resource_seen
        sta     resource_seen
@next: asl     resource_phase
        lda     resource_phase
        cmp     #4
        bcc     @loop
@done: rts
