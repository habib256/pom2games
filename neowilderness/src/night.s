; VERHILLE Arnaud — GPL-3.0. Night preparation is an inspection, never a queue.
.segment "GUIDANCE"
module_night:
        jsr     menu_gather
        lda     #0
        sta     night_cursor
        lda     camp_pending
        and     #$40
        beq     :+
        lda     camp_pending
        and     #7
        sta     night_cursor
:       jsr     night_duration
night_draw:
        jsr     text_mode80
        jsr     text_begin
        lda     #0
        sta     WNDTOP
        sta     night_row
@clear: lda     night_row
        jsr     guidance_at
        jsr     topo_pad
        inc     night_row
        lda     night_row
        cmp     #24
        bcc     @clear
        lda     #0
        jsr     guidance_at
        jsr     puts
        .byte "PREPARE NIGHT",0
        jsr     topo_pad
        lda     #2
        jsr     guidance_at
        jsr     puts
        .byte "REVIEW FIRST. EACH ACTION NEEDS YOUR CONFIRMATION.",0
        jsr     topo_pad
        lda     #4
        jsr     guidance_at
        jsr     puts
        .byte "SHELTER: ",0
        lda     shelter_inside
        beq     @outside
        jsr     puts
        .byte "READY: INSIDE. NATIVE REST RISKS APPLY.",0
        jmp     @body
@outside:
        jsr     puts
        .byte "MISSING: ENTER SHELTER / USE TENT IF AVAILABLE.",0
@body:  jsr     topo_pad
        lda     #6
        jsr     guidance_at
        jsr     puts
        .byte "BODY: ",0
        lda     thermal_mode
        ora     wet_mode
        beq     @comfortable
        jsr     puts
        .byte "MISSING: THERMAL / WETNESS PROTECTION.",0
        jmp     @bag
@comfortable:
        jsr     puts
        .byte "READY: COMFORTABLE NOW; WEATHER CAN CHANGE.",0
@bag:   jsr     topo_pad
        lda     #8
        jsr     guidance_at
        jsr     puts
        .byte "SLEEPING BAG: ",0
        lda     it_place+1
        cmp     #1
        beq     @worn
        ldx     #1
        jsr     have
        bcc     @missing
        jsr     puts
        .byte "UNAVAILABLE: NO NATIVE WEAR / USE ACTION.",0
        jmp     @meal
@worn:  jsr     puts
        .byte "READY: WORN NATIVE PROTECTION.",0
        jmp     @meal
@missing:
        jsr     puts
        .byte "UNAVAILABLE: NOT ACCESSIBLE HERE.",0
@meal:  jsr     topo_pad
        lda     #10
        jsr     guidance_at
        jsr     puts
        .byte "MEAL: ",0
        lda     #F_EAT
        sta     mn_t
        ldx     #23
@food_scan:
        jsr     item_ok
        bcs     @food_yes
        inx
        cpx     #38
        bcc     @food_scan
        cpx     #76
        bcs     :+
        ldx     #76
:       cpx     #87
        bcc     @food_scan
        jsr     puts
        .byte "UNAVAILABLE: FORAGE / HUNT OR LOWER FOOD.",0
        jmp     @water
@food_yes:
        jsr     puts
        .byte "READY: FOOD AVAILABLE; REVIEW TASTE / PORTION.",0
@water:
        jsr     topo_pad
        lda     #12
        jsr     guidance_at
        jsr     puts
        .byte "WATER: ",0
        lda     camp_untreated
        pha
        jsr     grid_water
        pla
        sta     camp_untreated
        bcs     @water_yes
        ldx     #N_WATER
        jsr     have
        bcs     @water_yes
        jsr     puts
        .byte "UNAVAILABLE: FIND A SOURCE OR MAKE WATER.",0
        jmp     @rest_line
@water_yes:
        jsr     puts
        .byte "READY: AVAILABLE. TASTE IS NO SAFETY TEST.",0
@rest_line:
        jsr     topo_pad
        lda     #14
        jsr     guidance_at
        jsr     puts
        .byte "REST: READY TO PROPOSE ",0
        lda     night_default
        sta     num
        lda     night_default+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " MIN (",0
        lda     night_default
        sta     num
        lda     night_default+1
        sta     num+1
        ldx     #0
@hours: sec
        lda     num
        sbc     #60
        tay
        lda     num+1
        sbc     #0
        bcc     @hh
        sta     num+1
        sty     num
        inx
        bne     @hours
@hh:    lda     num
        pha
        txa
        jsr     pdec
        jsr     puts
        .byte " H ",0
        pla
        jsr     pdec
        jsr     puts
        .byte " MIN). EDIT, THEN CONFIRM.",0
        jsr     topo_pad
        lda     #16
        jsr     guidance_at
        lda     night
        bne     @night_hint
        jsr     puts
        .byte "DAYLIGHT: SHORT REST BY ENERGY. NEXT DAWN IS A SEPARATE ACTION.",0
        jsr     topo_pad
        jmp     @after_hint
@night_hint:
        lda     night_margin
        beq     @after_hint
        lda     #16
        jsr     guidance_at
        jsr     puts
        .byte "PREDICTED NIGHT-END; +1 MIN MARGIN CROSSING MIDNIGHT.",0
        jsr     topo_pad
@after_hint:
        lda     #17
        jsr     guidance_at
        jsr     puts
        .byte "REST CAN STOP FOR AN ANIMAL OR ESC / SECOND BUTTON.",0
        jsr     topo_pad
        lda     #18
        jsr     guidance_at
        jsr     puts
        .byte "RESULT REPORTS ACTUAL / REQUESTED MINUTES AND WHY IT STOPPED.",0
        jsr     topo_pad
        lda     #20
        jsr     guidance_at
        jsr     puts
        .byte "ACTION: ",0
        ldx     night_cursor
        lda     night_lo,x
        sta     gp2
        lda     night_hi,x
        sta     gp2+1
        jsr     guidance_print
        jsr     topo_pad
        lda     #22
        jsr     guidance_at
        jsr     puts
        .byte "UP/DOWN CHOOSE  RETURN OPEN ACTION  ESC VIEW",0
        jsr     topo_pad
        jsr     text_release
        jsr     show_text
night_key:
        jsr     wait_key
        cmp     #KC_ESC
        beq     night_cancel
        cmp     #KC_RET
        beq     night_take
        cmp     #KC_UP
        beq     @up
        cmp     #KC_DOWN
        bne     night_key
        inc     night_cursor
        lda     night_cursor
        cmp     #7
        bcc     @draw
        lda     #0
        beq     @set
@up:    lda     night_cursor
        bne     :+
        lda     #7
:       sec
        sbc     #1
@set:   sta     night_cursor
@draw:  jmp     night_draw
night_cancel:
        lda     #0
        sta     camp_pending
        sta     dep_mask
        jmp     back_to_view_now
night_take:
        lda     journey_encounters
        sta     camp_encounter
        lda     night_cursor
        ora     #$40
        sta     camp_pending
        ldx     night_cursor
        cpx     #6
        beq     @next_night
        cpx     #1
        beq     @body
        cpx     #3
        beq     @meal
        cpx     #4
        beq     @water
        cpx     #5
        beq     @rest
        cpx     #2
        beq     @wear
        lda     #1              ; native local found-shelter predicate
        jsr     ctx_ok
        lda     #25             ; ENTER SHELTER
        bcs     @execute
        lda     #10             ; USE: tent / crafted shelter source list
        bne     @execute
@wear:  lda     #8               ; native WEAR garments; sleeping bag is not supported
        bne     @execute
@body:  lda     #3
        jmp     module_guidance
@meal:  lda     #0
        jmp     module_guidance
@water: lda     #1
        jmp     module_guidance
@next_night:
        jsr     night_until_dawn
        jmp     @rest
@rest:  lda     night_default
        sta     duration_proposal
        lda     night_default+1
        sta     duration_proposal+1
        lda     #1
        sta     duration_pending
        lda     #3
@execute:
        pha
        lda     #10
        jsr     overlay_load
        pla
        jmp     flows_execute

; Next native night-end is sunrise minus twilight, wrapping midnight.
; Round upward to the first whole native minute at or after night-end.
; A fractional final minute must not leave the player still in darkness.
; Only a confirmed REST request can advance native simulation.
night_duration:
        lda     night
        bne     night_until_dawn
        ; Same fatigue predicates as STATUS ENERGY: exhausted or tired need
        ; a full rest, moderate deficit a pause, otherwise a short break.
        lda     #0
        sta     night_margin
        fld     s_rest
        fop     FCOMP, f_16
        cmp     #1
        beq     @long
        fld     s_defr
        fop     FCOMP, f_12
        cmp     #1
        beq     @long
        fop     FCOMP, f_7
        cmp     #1
        beq     @medium
        lda     #<30
        ldx     #>30
        beq     @store
@medium:
        lda     #<120
        ldx     #>120
        beq     @store
@long: lda     #<480
        ldx     #>480
@store: sta     night_default
        stx     night_default+1
        rts
night_until_dawn:
        lda     #0
        sta     night_margin
        fld     f_twilight
        fop     FSUB, s_rise
        fop     FSUB, s_hour
        jsr     negate
        fop     FCOMP, f_zero
        cmp     #1
        beq     @positive
        inc     night_margin
        jsr     night_forecast
        fop     FSUB, f_twilight
        jsr     negate
        fop     FSUB, s_hour
        jsr     negate
        fop     FADD, f_24
@positive:
        fop     FMULT, f_60
        fst     night_fraction
        jsr     AYINT
        lda     $A1
        sta     night_default
        lda     $A0
        sta     night_default+1
        ldy     night_default
        jsr     GIVAYF
        fop     FCOMP, night_fraction
        cmp     #$FF
        bne     @minimum
        inc     night_default
        bne     @minimum
        inc     night_default+1
@minimum:
        lda     night_margin
        beq     :+
        inc     night_default
        bne     :+
        inc     night_default+1
:       lda     night_default+1
        ora     night_default
        bne     :+
        inc     night_default   ; native requests have a one-minute minimum
:       rts
night_cursor: .byte 0
night_row: .byte 0
night_default: .word 60
night_fraction: .res 5
night_margin: .byte 0
night_lo: .byte <night_shelter,<night_body,<night_bag,<night_meal,<night_water,<night_rest,<night_plan
night_hi: .byte >night_shelter,>night_body,>night_bag,>night_meal,>night_water,>night_rest,>night_plan
night_shelter: .byte "ENTER SHELTER / USE TENT",0
night_body: .byte "REVIEW THERMAL PROTECTION",0
night_bag: .byte "WEAR CLOTHES",0
night_meal: .byte "REVIEW FOOD / EAT",0
night_water: .byte "REVIEW WATER / DRINK",0
night_rest: .byte "CHOOSE REST DURATION",0
night_plan: .byte "PLAN NEXT DAWN REST (EDIT BEFORE CONFIRMING)",0

; Same sunrise algebra as module_env_day, evaluated at the next midnight.
; This inspection uses local scratch; native environment and RNG are untouched.
night_forecast:
        fld     s_hour
        fop     FSUB, f_24
        fop     FMULT, f_60
        fop     FMULT, f_inv_year
        fop     FADD, s_date
        fop     FCOMP, f_one
        cmp     #$FF
        beq     :+
        fop     FSUB, f_one
        jsr     negate
:       fst     night_date
        fld     night_date
        fop     FMULT, f_2pi
        fop     FSUB, f_1_378           ; 1.378 - 2 pi date
        jsr     negate
        jsr     FSIN
        fop     FMULT, f_0_398
        fst     night_t1                      ; sin(decl)
        fop     FMULT, night_t1
        fop     FSUB, f_one             ; cos^2
        jsr     FSQR
        fst     night_t2                      ; cos(decl)
        fld     night_t2
        fop     FDIV, night_t1                ; tan(decl) = sin / cos
        fst     night_t3
        ldy     M_LAT                   ; tan(lat): sin / cos
        lda     #0
        cpy     #$80
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FMULT, f_rad
        fst     night_t4                      ; lat in radians
        jsr     FSIN
        fst     night_t1
        fld     night_t4
        fop     FADD, f_half_pi         ; cos = sin(lat + pi/2)
        jsr     FSIN
        fop     FDIV, night_t1                ; tan(lat) = sin / cos
        fop     FMULT, night_t3               ; y = tan(lat) tan(decl)
        fst     night_t1                      ; asin(y) = atn(y / sqrt(1 - y^2))
        fop     FMULT, night_t1
        fop     FSUB, f_one
        jsr     FSQR
        fop     FDIV, night_t1                ; y / sqrt(1 - y^2)
        jsr     FATN
        fop     FMULT, f_12_pi          ; x (hours)
        fst     night_t1
        fop     FSUB, f_6               ; sunrise = 6 - x
        rts
night_date: .res 5
night_t1: .res 5
night_t2: .res 5
night_t3: .res 5
night_t4: .res 5
