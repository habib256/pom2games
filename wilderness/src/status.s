.segment "STATUS"
th_display10: .byte $84,$20,0,0,0
th_display95: .byte $80,$73,$33,$33,$33
module_status:
        jsr     text_screen
        ; player
        jsr     puts
        .byte   "STATUS: ", 0
        fld     f_hmax          ; s = H / Hmax: MISERABLE < .2 <= POOR < .4 <=
        fop     FDIV, s_health  ; OKAY < .6 <= GOOD < .8 <= FANTASTIC
        fop     FMULT, f_5
        jsr     AYINT
        ldx     $A1
        cpx     #5
        bcc     :+
        ldx     #4
:       lda     #<w_player
        sta     gp2
        lda     #>w_player
        sta     gp2+1
        lda     #9
        jsr     word
        lda     #28
        jsr     tab
        jsr     puts
        .byte   "GOAL=", 0
        jsr     goal_pct
        jsr     pdec
        jsr     puts
        .byte   "%|", 0
        lda     #26
        jsr     tab
        jsr     puts
        .byte   "HEALTH=", 0
        fld     f_hmax
        fop     FDIV, s_health
        fop     FMULT, f_100
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        jsr     pdec
        jsr     puts
        .byte "%",0
        jsr     puts
        .byte   "|ILL  ", 0
        ; conditions under 95 %: dehydration, starvation, exhaustion
        lda     #0
        sta     g0
        ldx     #0
        jsr     cond
        ldx     #1
        jsr     cond
        ldx     #2
        jsr     cond
        fld     s_therm_factor
        fop     FCOMP, th_display95
        cmp     #$FF
        bne     @condition_done
        jsr     CROUT
        inc     g0
        fld     s_body
        fop     FCOMP, f_body
        cmp     #$FF
        bne     @hyper
        jsr     puts
        .byte "HYPOTHERMIA", 0
        jmp     @condition_done
@hyper: jsr     puts
        .byte "HYPERTHERMIA", 0
@condition_done:
        lda     g0
        bne     :+
        jsr     puts
        .byte   "NONE", 0
:       lda     thermal_mode
        beq     @thermal_done
        cmp     #1
        beq     @sweat
        jsr     puts
        .byte "|SHIVERING", 0
        jmp     @thermal_done
@sweat: jsr     puts
        .byte "|SWEATING", 0
@thermal_done:
        lda     tree_in
        beq     :+
        jsr     puts
        .byte "|IN A TREE",0
:       lda     it_place+21
        cmp     #5
        bne     :+
        jsr     puts
        .byte "|BACKPACK HUNG",0
:
        lda     shelter_inside
        beq     :+
        jsr     puts
        .byte "|INSIDE SHELTER", 0
:
        lda     wet_mode
        cmp     #2
        bne     :+
        jsr     puts
        .byte "|IMMERSED", 0
:
        jsr     puts
        .byte   "|ENRG ", 0
        ; ENRG: BEAT if 16 h without rest, TIRED over 12 h of rest deficit,
        ; OKAY over 7, else GREAT (deficit replaces the original's F1[24])
        lda     #0
        sta     g1
        fld     s_rest
        fop     FCOMP, f_16
        cmp     #1
        beq     @enrg
        inc     g1
        fld     s_defr
        fop     FCOMP, f_12
        cmp     #1
        beq     @enrg
        inc     g1
        fop     FCOMP, f_7
        cmp     #1
        beq     @enrg
        inc     g1
@enrg:  ldx     g1
        lda     #<w_enrg
        sta     gp2
        lda     #>w_enrg
        sta     gp2+1
        lda     #6
        jsr     word
        lda     #14
        jsr     tab
        jsr     puts
        .byte   "HNGR ", 0
        lda     #<s_eat         ; VERY over 12 h, SO-SO over 6 h
        ldy     #>s_eat
        jsr     gauge
        lda     #28
        jsr     tab
        jsr     puts
        .byte   "THRST ", 0
        lda     #<s_drink
        ldy     #>s_drink
        jsr     gauge
        jsr     puts
        .byte   "|TEMP ", 0
        fld     s_body
        fop     FMULT, th_display10
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     num
        lda     $A0
        sta     num+1
        ; Divide the unsigned tenths by 10, keeping the remainder in g1.
        lda     #0
        sta     g1
@temp10:
        sec
        lda     num
        sbc     #10
        tax
        lda     num+1
        sbc     #0
        bcc     @temp_digit
        sta     num+1
        stx     num
        inc     g1
        bne     @temp10
@temp_digit:
        lda     num
        pha
        lda     g1
        jsr     pdec
        lda     #'.'|$80
        jsr     COUT
        pla
        ora     #'0'|$80
        jsr     COUT
        lda     #'F'|$80
        jsr     COUT
        lda     #14
        jsr     tab
        jsr     puts
        .byte   "FOOD ", 0
        lda     #0              ; FOOD: ounces of food 23..37 within reach
        sta     num
        sta     num+1
        ldx     #23
@food:  jsr     reach_oz
        inx
        cpx     #38
        bcc     @food
        jsr     print_u16
        jsr     puts
        .byte   " OZ", 0
        lda     #28
        jsr     tab
        jsr     puts
        .byte   "WATER ", 0
        lda     #0
        sta     num
        sta     num+1
        ldx     #N_WATER
        jsr     reach_oz
        jsr     print_u16
        jsr     puts
        .byte " OZ",0
        lda     #0
        sta     status_stock_kind
        jsr     status_stock_line
        inc     status_stock_kind
        jsr     status_stock_line
        jsr     puts
        .byte   "||ENVIRONMENT:|DATE ", 0
        ; date: day of year = INT(date * 365 + 1)
        fld     s_date
        fop     FMULT, f_365
        fop     FADD, f_one
        jsr     AYINT
        lda     $A1
        sta     g0
        lda     $A0
        sta     g1
        ldx     #0              ; month: subtract month lengths
@mon:   lda     g1
        bne     @sub
        lda     g0
        cmp     mdays,x
        bcc     @mgot
        beq     @mgot
@sub:   sec
        lda     g0
        sbc     mdays,x
        sta     g0
        lda     g1
        sbc     #0
        sta     g1
        inx
        cpx     #11
        bcc     @mon
@mgot:  lda     #<w_months
        sta     gp2
        lda     #>w_months
        sta     gp2+1
        lda     #3
        jsr     word
        lda     g0
        jsr     pdec
        lda     #14
        jsr     tab
        jsr     puts
        .byte   "TIME ", 0
        ldx     #54             ; WATCH
        jsr     have
        bcc     @noclock
        display_clock g1, g0    ; h:mm A/P
        lda     g1
        cmp     #12
        bcc     :+
        sbc     #12
:       cmp     #0              ; CMP #12 left Z clear for midnight's hour zero
        bne     :+
        lda     #12
:       jsr     pdec
        lda     #':'|$80
        jsr     COUT
        lda     g0
        cmp     #10
        bcs     :+
        lda     #'0'|$80
        jsr     COUT
        lda     g0
:       jsr     pdec
        lda     #'A'|$80
        ldx     g1
        cpx     #12
        bcc     :+
        lda     #'P'|$80
:       jsr     COUT
        jmp     @temp
@noclock:
        lda     #<w_period
        sta     gp2
        lda     #>w_period
        sta     gp2+1
        ldx     period
        lda     #5
        jsr     word
@temp:  lda     #28
        jsr     tab
        jsr     puts
        .byte   "TEMP ", 0
        ldx     #69             ; THERMOMETER
        jsr     have
        bcc     @tword
        lda     airtemp
        bpl     :+
        lda     #'-'|$80
        jsr     COUT
        lda     airtemp
        eor     #$FF
        clc
        adc     #1
:       jsr     pdec
        jsr     puts
        .byte   "DEG", 0
        jmp     @sky
@tword: ldx     #0              ; FREEZE < 32 <= COLD < 60 <= NICE < 80 <= WARM < 95 <= HOT
        lda     airtemp
        bmi     @tw
@tl:    cmp     tlimits,x
        bcc     @tw
        inx
        cpx     #4
        bcc     @tl
@tw:    lda     #<w_temp
        sta     gp2
        lda     #>w_temp
        sta     gp2+1
        lda     #6
        jsr     word
@sky:   jsr     puts
        .byte   "|SKY  ", 0
        lda     #<sky_words
        sta     gp2
        lda     #>sky_words
        sta     gp2+1
        ldx     weather_sky
        lda     #5
        jsr     word
        lda     #14
        jsr     tab
        jsr     puts
        .byte   "WIND ", 0
        lda     wind
        jsr     pdec
        jsr     puts
        .byte   "MPH", 0
        lda     #28
        jsr     tab
        jsr     puts
        .byte "FEEL ", 0
        lda     felt_temp
        sta     num
        lda     felt_temp+1
        sta     num+1
        bpl     @felt_abs
        lda     #'-'|$80
        jsr     COUT
        sec
        lda     #0
        sbc     num
        sta     num
        lda     #0
        sbc     num+1
        sta     num+1
@felt_abs:
        jsr     print_u16
        jsr     puts
        .byte "F|ALT  ", 0
        jsr     level_here
        clc
        adc     M_BASE
        sta     g0
        ldx     #55             ; ALTIMETER
        jsr     have
        bcc     @aword
        lda     g0
        jsr     pdec
        jsr     puts
        .byte   "00FT", 0
        jmp     @grnd
@aword: ldx     #0              ; LOW < 30 <= MEDIUM < 101 <= HIGH
        lda     g0
        cmp     #30
        bcc     :+
        inx
        cmp     #101
        bcc     :+
        inx
:       lda     #<w_alt
        sta     gp2
        lda     #>w_alt
        sta     gp2+1
        lda     #6
        jsr     word
@grnd:  lda     #14
        jsr     tab
        jsr     puts
        .byte   "GRND ", 0
        jsr     level_here
        pha
        jsr     woods_here
        pla
        ldx     #0
        bcc     @bare
        clc
        adc     M_BASE
        ldx     MAP+27
        bne     :+
        ldx     #110            ; same timberline as forest drawing and climbing
:       stx     g1
        cmp     g1
        ldx     #2              ; woodland, then alpine scrub above treeline
        bcc     @ground_word
        inx
        bne     @ground_word
@bare:  cmp     #96
        bcc     @ground_word
        inx
@ground_word:
        lda     #<w_grnd
        sta     gp2
        lda     #>w_grnd
        sta     gp2+1
        lda     #5
        jsr     word
        lda     #22
        jsr     vtab
        jsr     puts
        .byte "M MEDICAL I INV T TOPO H HELP|ESC/RETURN/SPACE: VIEW",0
status_key:
@key:   jsr     wait_key
        cmp     #'I'
        jeq     scr_inventory
        cmp     #'T'
        jeq     scr_topo
        cmp     #'H'
        jeq     scr_help
        cmp     #'M'
        jeq     scr_medical
        cmp     #KC_ESC
        jeq     back_to_view_now
        cmp     #KC_RET
        jeq     back_to_view_now
        cmp     #' '
        jeq     back_to_view_now
        jmp     @key


; gauge -- hunger / thirst word from the hours at (A,Y): VERY over 12,
; SO-SO over 6, else OKAY
gauge:  jsr     MOVFM
        lda     #0              ; the index stays out of X: the ROM float
        sta     g1              ; routines do not keep it
        fop     FCOMP, f_12
        cmp     #1
        beq     @w
        inc     g1
        fop     FCOMP, f_6
        cmp     #1
        beq     @w
        inc     g1
@w:     ldx     g1
        lda     #<w_gauge
        sta     gp2
        lda     #>w_gauge
        sta     gp2+1
        lda     #6
        jmp     word

; cond -- X = 0 dehydration, 1 starvation, 2 exhaustion: print its name when
; its factor is under 95 %, i.e. deficit > 0.2236 x tolerance
cond:   stx     g1
        lda     cdef_lo,x
        ldy     cdef_hi,x
        jsr     MOVFM
        fst     t1
        ldx     g1
        lda     ctol_lo,x
        ldy     ctol_hi,x
        jsr     MOVFM
        fop     FMULT, f_0_2236
        fop     FCOMP, t1
        cmp     #$FF
        bne     @no
        lda     g0
        beq     :+
        lda     #','|$80
        jsr     COUT
:       inc     g0
        ldx     g1
        lda     cname_lo,x
        pha
        lda     cname_hi,x
        tax
        pla
        jsr     print_str_ax
@no:    rts

; reach_oz -- num += ounces of item X within reach (pack, plus the ground at
; the item's ground cell)
reach_oz:
        lda     it_place,x
        cmp     #$FF
        beq     @no
        cmp     #5
        beq     @ground
        clc
        lda     num
        adc     it_pack_lo,x
        sta     num
        lda     num+1
        adc     it_pack_hi,x
        sta     num+1
@ground:
        stx     g1
        jsr     at_ground
        ldx     g1
        bcc     @no
        clc
        lda     num
        adc     it_gnd_lo,x
        sta     num
        lda     num+1
        adc     it_gnd_hi,x
        sta     num+1
@no:    rts


; Explicit transported/here totals; a split food contributes once to each.
status_stock_line:
        jsr     puts
        .byte "|",0
        lda     status_stock_kind
        bne     @here
        jsr     puts
        .byte "CARRIED ",0
        jmp     @food
@here:  jsr     puts
        .byte "HERE ",0
@food:  jsr     puts
        .byte "FOOD ",0
        lda     #0
        sta     num
        sta     num+1
        ldx     #23
@sum:   jsr     status_stock_oz
        inx
        cpx     #38
        bcc     @sum
        jsr     print_u16
        jsr     puts
        .byte " OZ WATER ",0
        lda     #0
        sta     num
        sta     num+1
        ldx     #N_WATER
        jsr     status_stock_oz
        jsr     print_u16
        jsr     puts
        .byte " OZ",0
        rts
status_stock_oz:
        lda     it_place,x
        cmp     #255
        beq     @done
        lda     status_stock_kind
        bne     @ground
        lda     it_place,x
        beq     @done
        cmp     #5
        beq     @done
        clc
        lda     num
        adc     it_pack_lo,x
        sta     num
        lda     num+1
        adc     it_pack_hi,x
        sta     num+1
        rts
@ground:
        jsr     at_ground       ; preserves X; no separate saved item needed
        bcc     @done
        clc
        lda     num
        adc     it_gnd_lo,x
        sta     num
        lda     num+1
        adc     it_gnd_hi,x
        sta     num+1
@done:  rts
status_stock_kind: .byte 0

.segment "STATUS"
goal_pct:
        lda     s_elap          ; initial GOAL is 100: no simulation disk read
        bne     :+
        lda     #100
        rts
:
        lda     #3
        jsr     overlay_load
        jmp     module_goal_pct

mdays:  .byte   31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30
cname_lo: .byte <w_dehyd, <w_starv, <w_exhau
cname_hi: .byte >w_dehyd, >w_starv, >w_exhau
tlimits: .byte  32, 60, 80, 95
w_temp: .byte   "FREEZECOLD  NICE  WARM  HOT   "
w_alt:  .byte   "LOW   MEDIUMHIGH  "
w_grnd: .byte   "CLEARROCKYWOODSSCRUB"
w_dehyd: .byte  "DEHYDRATION", 0
w_starv: .byte  "STARVATION", 0
w_exhau: .byte  "EXHAUSTION", 0


.segment "ENVIRON"
module_goal_pct:
        fld     s_elap
        lda     FAC
        bne     :+
        lda     #100
        rts
:       jsr     dist_goal
        fop     FSUB, s_d0              ; D0 - d
        fop     FMULT, f_goal_v
        fst     t1
        fld     s_elap
        fop     FDIV, t1                ; v = 0.6 (D0 - d) / u
        fst     t1
        fld     s_d0
        fop     FDIV, s_elap            ; u / D0
        fop     FMULT, f_goal_k
        jsr     FEXP
        fst     t2                      ; e
        fld     f_one
        fop     FSUB, t2
        jsr     negate                  ; 1 - e ... (e - 1) negated
        fop     FMULT, t1
        fop     FADD, t2
        fop     FMULT, f_100
        jsr     clamp0
        fop     FCOMP, f_100
        cmp     #1
        bne     :+
        lda     #100
        rts
:       jsr     AYINT
        lda     $A1
        rts


tree_effort: .byte $7B,$23,$D7,$0A,$3E ; native T12/S08 $5CBE, .02 * body weight
