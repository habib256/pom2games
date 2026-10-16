; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; prepare.s -- NEOWILD.PRE: the journey preparation of the original (lot 1)
; ============================================================================
; docs/ORIGINAL_GAP.md P1 and P2, docs/SCENARIOS.md section 11. Linked at
; $2000 (segment PREPARE, build/wildpre.bin); NEOWILD.SYSTEM reads it into
; its staging buffer once the region pack is read, for every journey other
; than a scenario at level 4 (the original's first journey: the frozen state
; of the reference stays untouched), and calls `prepare` before the grid of
; the menu goes into the HGR rows. No resident byte: everything here is
; overwritten by the game.
;
; The formulas are those of GO1 ($5800), GO2 ($2000) and GO3 ($3000) of the
; Sierra Nevadas side, computed with the same ROM floating point operations
; in the same order (tools/prepare_ref.py documents them; tools/
; re_prepare_probe.py runs the original with an imposed RND;
; tests/test_prepare.py compares the bytes):
;   - P (ld_prep): the questions (date and time chosen or drawn, normal play
;     or research mode, sex, weight, frame, height, age, resting pulse, then
;     wildlife and storm frequencies) and the fitness verdict; the body
;     gives the weight, metabolism (w / 100), eating rate, Hmax, health, the
;     thermal surface Q and the overweight factor; research mode skips the
;     body questions (175 lb...) and the crash injury, and puts the compass,
;     watch, altimeter, flashlight and thermometer at the wreck;
;   - every journey here: start date and hour drawn around the season by
;     the level, temperature wave phase, crash injury (normal play), wreck
;     lot (nine groups, about (11 - L) / 10 of each), uses of consumables x
;     1 / sqrt(L), first weather front and wind; the introduction words.
; Not here (documented): the in-game effects of research mode, STATUS's
; level factor, the original score, the moon phase 60 - 18 L, the per-level
; maps and the container capacities.
; ============================================================================

PR_SNGFLT = $E301               ; FAC = Y (unsigned)
PR_FLOAT  = $EB93               ; FAC = A (signed)
PR_NEG    = $EED0               ; FAC = -FAC
PR_MUL10  = $EA39
PR_DIV10  = $EA55
PR_ADDH   = $E7A0               ; FAC += .5
PR_ARGRND = $EB63               ; ARG = FAC (rounded)
PR_POWER  = $EE94               ; FAC = ARG ^ (A,Y)
PR_HALF   = $EE64               ; ROM constants .5, 1, 10, 2 pi
PR_ONE    = $E913
PR_TEN    = $EA50
PR_TWOPI  = $F06B
PR_COUT   = $FDED
PR_HOME   = $FC58
PR_CROUT  = $FD8E
PR_BELL   = $FF3A
PR_CH     = $24
PR_CV     = $25
PR_WNDTOP = $22
PR_SIM    = 3                   ; module_dir entry patched (raw SIM image)
SIM_WINDOW = $9600

.import ld_region, ld_level, ld_free, ld_prep, ld_entropy, ld_print, ld_place
.import ld_hdr, ld_move_src, ld_menu_key
.export prepare, pr_fixed, pr_inj, pr_verdict, pr_freq, pr_storm, pr_wild

.segment "PREPARE"
prepare:
        lda     #0              ; SHIFT.SIGN.EXT: the ROM shifts it into
        sta     $A4             ; products (boot.s applesoft_hi has 0 too)
        lda     ld_entropy      ; RNG seed (never zero)
        ora     #1
        sta     pr_seed
        lda     ld_entropy+1
        sta     pr_seed+1
        ldy     ld_level        ; GO1 $593B: L as a float
        jsr     PR_SNGFLT
        fst     pr_lv
        lda     #$FF
        sta     pr_verdict
        fld     PR_ONE          ; storm and wildlife 1.0 unless asked
        fst     pr_storm
        fst     pr_wild
        lda     ld_prep
        beq     :+
        jsr     pr_ask_start    ; date Y/N (month, hour), play P/R
:       jsr     pr_date         ; GO1 $5A38 / $59D7, GO2 $285D
        jsr     pr_rnd          ; GO2 $298F: temperature wave phase
        fop     FMULT, PR_TWOPI
        fst     s_temp_phase
        lda     pr_research
        bne     :+
        jsr     pr_injury       ; GO2 $2024
:       lda     ld_prep
        beq     :+
        jsr     pr_ask_body     ; GO1 $5B2F-$5C2E, GO2 $2119, $2337
:       jsr     pr_wreck        ; GO2 $2565
        jsr     pr_uses         ; GO2 $26C2
        lda     ld_prep
        beq     :+
        jsr     pr_ask_freq     ; GO1 $5D96-$5E01
:       jsr     pr_front        ; GO2 $2A74, GO1 $5E0A-$5E79
        jsr     pr_summary
        lda     #0
        sta     PR_WNDTOP
        rts

; ----------------------------------------------------------------------------
; pr_rnd -- FAC = RND in [0, 1): the imposed value pr_fixed (tests), else a
; 16-bit xorshift scaled by 1/32768.
pr_rnd: lda     pr_fixed
        beq     :+
        fld     pr_fixed
        rts
:       lda     pr_seed+1
        lsr     a
        lda     pr_seed
        ror     a
        eor     pr_seed+1
        sta     pr_seed+1
        ror     a
        eor     pr_seed
        sta     pr_seed
        eor     pr_seed+1
        sta     pr_seed+1
        and     #$7F
        ldy     pr_seed
        jsr     GIVAYF
        fop     FMULT, pr_c32768
        rts

; ----------------------------------------------------------------------------
; pr_date -- s_date (fraction of the year) and s_hour.
pr_date:
        lda     pr_dated
        beq     @random
        lda     #0              ; GO1 $59D7: (month - 1) .085 + .065 RND
        ldy     pr_month
        jsr     GIVAYF
        fop     FSUB, PR_ONE
        jsr     PR_NEG
        fop     FMULT, pr_c085
        fst     pr_t1
        jsr     pr_rnd
        fop     FMULT, pr_c065
        fop     FADD, pr_t1
        fst     s_date
        ldy     pr_hour
        jsr     PR_SNGFLT
        fst     s_hour
        jmp     @clamp
@random:
        jsr     pr_rnd          ; GO1 $5A38: around the summer, wider with L
        fop     FCOMP, PR_HALF
        sta     g0
        fop     FMULT, pr_lv
        fop     FMULT, pr_c05
        fop     FADD, pr_c05
        lda     M_LAT
        bmi     @south
        fop     FADD, PR_HALF
        lda     g0
        cmp     #1
        beq     @store
        lda     #<pr_cm05
        ldy     #>pr_cm05
        bne     @offset
@south: lda     g0
        cmp     #1
        bne     :+
        fop     FADD, PR_ONE
        lda     #<pr_cm075
        ldy     #>pr_cm075
        bne     @offset
:       lda     #<pr_c025
        ldy     #>pr_c025
@offset:
        sta     gp1
        sty     gp1+1
        fst     pr_t1
        lda     gp1
        ldy     gp1+1
        jsr     MOVFM
        fop     FMULT, pr_lv
        fop     FADD, pr_t1
@store: fst     s_date
        jsr     pr_rnd          ; GO1 $5AA6: around noon, wider with L
        fop     FCOMP, PR_HALF
        sta     g0
        fop     FMULT, pr_lv
        fop     FMULT, pr_c1_2
        fop     FADD, pr_c12
        lda     g0
        cmp     #1
        beq     :+
        fst     pr_t1
        fld     pr_c1_2
        fop     FMULT, pr_lv
        fop     FSUB, pr_t1
:       fst     s_hour
@clamp: fld     pr_c997         ; GO2 $285D: at most .997
        fop     FCOMP, s_date
        cmp     #1
        beq     :+
        fst     s_date
:       rts

; ----------------------------------------------------------------------------
; pr_injury -- GO2 $2024: n = INT(.45 RND L - .3), 0..3 (cuts, arm, leg),
; condition n - 1 active at 90 % (the original's rec7 entry).
pr_injury:
        jsr     pr_rnd
        fop     FMULT, pr_c045
        fst     pr_t1
        ldy     ld_level
        jsr     PR_SNGFLT
        fop     FMULT, pr_t1
        fop     FSUB, pr_c03
        jsr     PR_NEG
        jsr     AYINT
        ldy     $A1
        ldx     $A0
        bpl     :+
        ldy     #0
:       cpy     #4
        bcc     :+
        ldy     #3
:       sty     pr_inj
        dey
        bmi     @none
        lda     #1
        sta     injury_active,y
        lda     #90
        sta     injury_percent,y
        lda     #0
        sta     injury_treated,y
@none:  rts

; ----------------------------------------------------------------------------
; pr_body -- GO2 $2119: ideal weight, overweight, metabolism, Hmax, surface.
pr_body:
        ldy     pr_height
        jsr     PR_SNGFLT
        fst     pr_t2
        fld     pr_c073
        fop     FMULT, pr_t2
        fop     FSUB, pr_c598
        jsr     PR_NEG
        fop     FMULT, pr_t2
        fop     FADD, pr_c223
        fst     pr_t2
        ldy     pr_sex
        jsr     PR_SNGFLT
        jsr     PR_MUL10
        fop     FSUB, pr_t2
        fst     pr_t2
        lda     pr_frame
        jsr     PR_FLOAT
        fop     FMULT, pr_c065
        fop     FADD, PR_ONE
        fop     FMULT, pr_t2
        fst     pr_t2           ; ideal weight W0
        jsr     pr_weight_fac
        fop     FSUB, pr_t2
        jsr     PR_NEG
        jsr     AYINT           ; overweight (floor)
        lda     $A1
        sta     pr_ow
        lda     $A0
        sta     pr_ow+1
        ldy     pr_pulse
        jsr     PR_SNGFLT
        fop     FMULT, pr_c022
        fst     pr_t3
        ldy     pr_age
        jsr     PR_SNGFLT
        fop     FMULT, pr_c033
        fst     pr_t4
        jsr     pr_weight_fac   ; metabolism w / 100 ($4C20 = $4C25)
        jsr     PR_DIV10
        jsr     PR_DIV10
        fst     f_rest_rate
        jsr     pr_weight_fac
        fst     pr_t1
        lda     pr_ow+1
        bmi     @under
        ora     pr_ow
        beq     @under
        fld     pr_t2
        fop     FDIV, pr_t1     ; w / W0
        jmp     @power
@under: fld     pr_t1
        fop     FDIV, pr_t2     ; W0 / w
@power: jsr     PR_ARGRND
        lda     #<pr_c1_5
        ldy     #>pr_c1_5
        jsr     PR_POWER
        fop     FMULT, pr_t3
        fop     FDIV, PR_TEN
        fst     pr_t3
        fld     pr_t4
        lda     pr_age
        cmp     #31
        bcs     @old
        jsr     FSQR
        fop     FMULT, pr_t3
        jmp     @hmax
@old:   fop     FDIV, pr_t3
@hmax:  fst     f_hmax
        fst     s_health
        ldy     pr_height       ; surface S = .00919928 sqrt(h w)
        jsr     PR_SNGFLT
        fst     pr_t1
        jsr     pr_weight_fac
        fop     FMULT, pr_t1
        jsr     FSQR
        fop     FMULT, pr_c0092
        fst     pr_t1
        fop     FMULT, pr_c1335
        jsr     AYINT
        lda     $A1             ; Q = 2 INT(1335 S) + INT(800 S) + 2630
        asl     a
        sta     pr_q
        lda     $A0
        rol     a
        sta     pr_q+1
        fld     pr_t1
        fop     FMULT, pr_c800
        jsr     AYINT
        clc
        lda     $A1
        adc     pr_q
        tay
        lda     $A0
        adc     pr_q+1
        tax
        clc
        tya
        adc     #<2630
        sta     pr_q
        txa
        adc     #>2630
        sta     pr_q+1
        ldy     pr_q            ; thermal.s th_surface and th_a = 1e-7 Q
        jsr     GIVAYF
        fst     pr_t1
        lda     #<(th_surface - SIM_WINDOW)
        ldy     #>(th_surface - SIM_WINDOW)
        jsr     pr_patch_sim
        fld     pr_t1
        fop     FMULT, pr_c1em7
        fst     pr_t1
        lda     #<(th_a - SIM_WINDOW)
        ldy     #>(th_a - SIM_WINDOW)
        jsr     pr_patch_sim
        lda     pr_ow+1         ; 1 - overweight / weight (native maps)
        ldy     pr_ow
        jsr     GIVAYF
        fst     pr_t1
        jsr     pr_weight_fac
        fop     FDIV, pr_t1
        fop     FSUB, PR_ONE
        fst     pr_t1
        lda     #<(th_native_composition - SIM_WINDOW)
        ldy     #>(th_native_composition - SIM_WINDOW)
        jsr     pr_patch_sim
        jsr     pr_weight_fac   ; eating: base + .004 w (T12 $5E33)
        fop     FMULT, pr_c004
        fop     FADD, f_rest_rate
        fst     f_eat_rate
        lda     pr_weight
        sta     body_weight
        lda     pr_weight+1
        sta     body_weight+1
        asl     pr_weight       ; GOLD (scenario 2): 2 w + 40 oz, w / 2 in3
        rol     pr_weight+1
        clc
        lda     pr_weight
        adc     #40
        sta     it_oz_lo+75
        lda     pr_weight+1
        adc     #0
        sta     it_oz_hi+75
        lda     body_weight+1
        lsr     a
        sta     it_vol_hi+75
        lda     body_weight
        ror     a
        sta     it_vol_lo+75
        lda     pr_research     ; GO2 $2337: normal play clamps and judges
        bne     @done
        fld     f_hmax
        fop     FCOMP, pr_c1_1
        cmp     #$FF
        bne     :+
        fld     pr_c1_1
        fst     f_hmax
        jmp     @verdict
:       fop     FCOMP, PR_TEN
        cmp     #1
        bne     @verdict
        fld     PR_TEN
        fst     f_hmax
@verdict:
        lda     #0
        sta     pr_verdict
        fld     f_hmax
        fop     FCOMP, pr_c1_7
        cmp     #$FF
        beq     @done
        inc     pr_verdict
        fop     FCOMP, pr_c3_5
        cmp     #$FF
        beq     @done
        inc     pr_verdict
        jsr     PR_ADDH
        jsr     AYINT
        lda     $A1
        cmp     #6
        bcc     @done
        inc     pr_verdict
        cmp     #8
        bcc     @done
        inc     pr_verdict
@done:  rts

pr_weight_fac:
        lda     pr_weight+1
        ldy     pr_weight
        jmp     GIVAYF

; Mutable body/weather constants live in resident RAM so SIM can be
; compressed. Keep the existing offset API; only its storage changes.
pr_patch_sim:
        clc
        adc     #<SIM_WINDOW
        sta     @put+1
        tya
        adc     #>SIM_WINDOW
        sta     @put+2
        ldy     #4
@copy:  lda     pr_t1,y
@put:   sta     $FFFF,y
        dey
        bpl     @copy
        rts

; ----------------------------------------------------------------------------
; pr_wreck -- GO2 $2565: B1 (it_place) of a new journey, then the food on
; the ground (Journey template T$21: W7 = W5, W8 = 0).
pr_wreck:
        ldx     #75
        lda     #$FF
:       sta     it_place,x
        dex
        bne     :-
        lda     #0
        sta     it_place+52     ; TOPO MAP (template)
        ldx     #7
:       ldy     pr_always,x
        sta     it_place,y
        dex
        bpl     :-
        sta     pr_base
        sta     pr_g
@group: ldx     pr_g
        lda     pr_sizes,x
        sta     pr_s
        tay                     ; a = INT(RND (s - 1) + .5) + 1
        dey
        jsr     PR_SNGFLT
        fst     pr_t1
        jsr     pr_rnd
        fop     FMULT, pr_t1
        jsr     PR_ADDH
        jsr     AYINT
        ldx     $A1
        inx
        stx     pr_a
        lda     pr_s            ; b = INT(RND (s - 2) + .5) + 1
        sec
        sbc     #2
        jsr     PR_FLOAT
        fst     pr_t1
        jsr     pr_rnd
        fop     FMULT, pr_t1
        jsr     PR_ADDH
        jsr     AYINT
        ldx     $A1
        inx
        stx     pr_b
        lda     pr_g            ; groups 1 and 3: strides prime to 21, 15
        beq     :+
        cmp     #2
        bne     @count
:       txa
        ldy     #5
:       cmp     pr_three,y
        beq     @dec
        dey
        bpl     :-
        bmi     @four
@dec:   dec     pr_b
@four:  lda     pr_b
        ldy     #3
:       cmp     pr_four,y
        beq     @set4
        dey
        bpl     :-
        bmi     @count
@set4:  lda     #4
        sta     pr_b
@count: lda     #11             ; k = INT((11 - L) s / 10 + .5)
        sec
        sbc     ld_level
        jsr     PR_FLOAT
        fst     pr_t1
        ldy     pr_s
        jsr     PR_SNGFLT
        fop     FMULT, pr_t1
        jsr     PR_DIV10
        jsr     PR_ADDH
        jsr     AYINT
        lda     $A1
        sta     pr_k
        beq     @next
        lda     #1
        sta     pr_count
@pick:  lda     pr_a
        sec
        sbc     pr_s
        bmi     :+
        beq     :+
        sta     pr_a
:       clc
        lda     pr_base
        adc     pr_a
        tay
        lda     #0
        sta     it_place,y
        lda     pr_count
        cmp     pr_k
        beq     @next
        inc     pr_count
        clc
        lda     pr_a
        adc     pr_b
        sta     pr_a
        jmp     @pick
@next:  clc
        lda     pr_base
        adc     pr_s
        sta     pr_base
        inc     pr_g
        lda     pr_g
        cmp     #9
        jne     @group
        lda     #1              ; worn: BOOTS, JERSEY, JEANS, COTTN SOCKS
        sta     it_place+5
        sta     it_place+14
        sta     it_place+15
        sta     it_place+18
        lda     #$FF            ; STAR CHART, BINOCULARS, GOLD
        sta     it_place+56
        sta     it_place+68
        sta     it_place+75
        lda     pr_research
        beq     @food
        lda     #0              ; research: COMPASS, WATCH, ALTIMETER,
        sta     it_place+53     ; FLASHLGHT, THERMOMETER
        sta     it_place+54
        sta     it_place+55
        sta     it_place+66
        sta     it_place+69
@food:  ldx     #37
:       lda     it_oz_lo,x
        sta     it_gnd_lo,x
        lda     it_oz_hi,x
        sta     it_gnd_hi,x
        lda     #0
        sta     it_pack_lo,x
        sta     it_pack_hi,x
        dex
        cpx     #N_WATER
        bcs     :-
        rts

; pr_uses -- GO2 $26C2: W8 of items 38..66 (template), W5 and W6 of FUEL,
; x 1 / sqrt(L), truncated.
pr_uses:
        ldy     ld_level
        jsr     PR_SNGFLT
        jsr     FSQR
        fop     FDIV, PR_ONE
        fst     pr_t4
        ldx     #0
@use:   stx     pr_count
        lda     #0
        ldy     pr_uses_t,x
        jsr     GIVAYF
        fop     FMULT, pr_t4
        jsr     AYINT
        lda     pr_count
        clc
        adc     #38
        tax
        lda     $A1
        sta     it_pack_lo,x
        lda     $A0
        sta     it_pack_hi,x
        ldx     pr_count
        inx
        cpx     #29
        bne     @use
        lda     #0
        ldy     #16             ; FUEL: 16 oz, 138 in3
        jsr     GIVAYF
        fop     FMULT, pr_t4
        jsr     AYINT
        lda     $A1
        sta     it_oz_lo+40
        lda     $A0
        sta     it_oz_hi+40
        lda     #0
        ldy     #138
        jsr     GIVAYF
        fop     FMULT, pr_t4
        jsr     AYINT
        lda     $A1
        sta     it_vol_lo+40
        lda     $A0
        sta     it_vol_hi+40
        rts

; ----------------------------------------------------------------------------
; pr_front -- precipitation of the start date (GO2 $2A74, Sierra header, the
; port's module_weather_daily with the storm multiplier), first front
; (GO1 $5E0A), its duration and the wind ($5E2D, $5E67).
pr_front:
        fld     s_date
        fop     FMULT, pr_c360
        fop     FADD, pr_c47
        fop     FMULT, pr_crad
        jsr     FSIN
        fop     FADD, PR_ONE
        fst     pr_t1
        fld     pr_c29
        fop     FMULT, pr_t1
        fst     pr_t1
        fld     pr_c2
        fop     FADD, pr_t1
        fop     FMULT, pr_c01
        fop     FMULT, pr_storm
        fop     FCOMP, pr_c01
        cmp     #$FF
        bne     :+
        fld     pr_c01
:       fst     pr_freq
        fst     weather_frequency
        fld     pr_lv           ; 3000 / (L F) + 20 (4-minute units)
        fop     FMULT, pr_freq
        fop     FDIV, pr_c3000
        fop     FADD, pr_c20
        fst     weather_start
        jsr     pr_rnd          ; INT(min(540, 20 + 10 L F RND))
        fop     FMULT, pr_lv
        fop     FMULT, pr_freq
        jsr     PR_MUL10
        fop     FADD, pr_c20
        fop     FCOMP, pr_c540
        cmp     #1
        bne     :+
        fld     pr_c540
:       jsr     AYINT
        lda     $A1
        sta     weather_duration
        lda     $A0
        sta     weather_duration+1
        jsr     pr_rnd          ; wind INT(16 RND) + 2 mph
        lda     FAC
        beq     :+
        clc
        adc     #4
        sta     FAC
:       jsr     AYINT
        ldx     $A1
        inx
        inx
        stx     wind
        lda     ld_prep         ; storm multiplier of the daily precipitation
        beq     :+
        fld     pr_storm
        fst     pr_t1
        lda     #<(wf_storm - SIM_WINDOW)
        ldy     #>(wf_storm - SIM_WINDOW)
        jsr     pr_patch_sim
        fld     pr_wild         ; NATURE: an integer 0..100
        jsr     PR_ADDH
        jsr     AYINT
        lda     $A1
        sta     nature_frequency
:       rts

; ----------------------------------------------------------------------------
; Questions (texts of GO3, renumbered: the lost city is not in this port).
pr_ask_start:
        lda     #0
        sta     PR_WNDTOP
        jsr     PR_HOME
        lda     #<pr_m_head
        ldy     #>pr_m_head
        jsr     ld_print
        lda     #3
        sta     PR_WNDTOP
        lda     #<pr_m_q1
        ldy     #>pr_m_q1
        ldx     #'N'|$80
        jsr     pr_yes_no       ; Y: 0
        eor     #1
        sta     pr_dated
        beq     @mode
        lda     #<pr_m_month
        ldy     #>pr_m_month
        ldx     #1
        stx     pr_min
        ldx     #12
        jsr     pr_ask_number
        sty     pr_month
        lda     #<pr_m_hour
        ldy     #>pr_m_hour
        ldx     #0
        stx     pr_min
        ldx     #24
        jsr     pr_ask_number
        sty     pr_hour
@mode:  lda     #<pr_m_q2
        ldy     #>pr_m_q2
        jsr     ld_print
        lda     #'P'|$80
        ldx     #'R'|$80
        jsr     pr_key2
        sta     pr_research
        rts

; pr_ask_body -- research: the original's fixed body; normal: questions.
pr_ask_body:
        lda     pr_research
        beq     @ask
        lda     #175
        sta     pr_weight
        lda     #73
        sta     pr_height
        lda     #25
        sta     pr_age
        lda     #42
        sta     pr_pulse
        jmp     pr_body         ; pr_sex, pr_frame 0, pr_weight+1 0
@ask:   lda     #<pr_m_q3
        ldy     #>pr_m_q3
        jsr     ld_print
        lda     #'M'|$80
        ldx     #'F'|$80
        jsr     pr_key2
        sta     pr_sex
        lda     #<pr_m_q4
        ldy     #>pr_m_q4
        jsr     ld_print
        jsr     pr_field
@weight:
        jsr     pr_line
        jsr     pr_parse
        bcs     @bad_weight
        lda     pr_num+1        ; 50..350
        bne     :+
        lda     pr_num
        cmp     #50
        bcs     @weight_ok
        bcc     @bad_weight
:       cmp     #2
        bcs     @bad_weight
        lda     pr_num
        cmp     #<351
        bcc     @weight_ok
@bad_weight:
        jsr     pr_retry
        jmp     @weight
@weight_ok:
        lda     pr_num
        sta     pr_weight
        lda     pr_num+1
        sta     pr_weight+1
        lda     #<pr_m_q5
        ldy     #>pr_m_q5
        jsr     ld_print
        jsr     pr_frame_key
        sta     pr_frame
        lda     #<pr_m_q6
        ldy     #>pr_m_q6
        ldx     #50
        stx     pr_min
        ldx     #85
        jsr     pr_ask_number
        sty     pr_height
        lda     #<pr_m_q7
        ldy     #>pr_m_q7
        ldx     #8
        stx     pr_min
        ldx     #100
        jsr     pr_ask_number
        sty     pr_age
        lda     #<pr_m_q8
        ldy     #>pr_m_q8
        ldx     #35
        stx     pr_min
        ldx     #180
        jsr     pr_ask_number
        sty     pr_pulse
        jsr     pr_body
        jsr     PR_CROUT        ; the verdict, as GO2 prints it
        jsr     PR_CROUT
        lda     #3
        sta     PR_CH
        ldx     pr_verdict
        lda     pr_verdict_lo,x
        ldy     pr_verdict_hi,x
        jmp     ld_print

pr_ask_freq:
        lda     #<pr_m_q9
        ldy     #>pr_m_q9
        jsr     pr_ask_decimal
        fst     pr_wild
        lda     #<pr_m_q10
        ldy     #>pr_m_q10
        jsr     pr_ask_decimal
        fst     pr_storm
        rts

; pr_yes_no -- A/Y question, X = second key: Y/N (Y: A = 0).
pr_yes_no:
        stx     g1
        jsr     ld_print
        lda     #'Y'|$80
        ldx     g1
; pr_key2 -- A = first key, X = second: wait for one, echo it, wait for
; RETURN. A = 0 (first) or 1.
pr_key2:
        sta     g1
        stx     g2
@key:   jsr     ld_menu_key
        ldx     #0
        cmp     g1
        beq     @echo
        inx
        cmp     g2
        beq     @echo
        jsr     PR_BELL
        jmp     @key
@echo:  stx     g0
        jsr     PR_COUT
        jsr     pr_return
        lda     g0
        rts

; pr_frame_key -- S, M or L: A = -1, 0, 1.
pr_frame_key:
        jsr     ld_menu_key
        ldx     #$FF
        cmp     #'S'|$80
        beq     @echo
        inx
        cmp     #'M'|$80
        beq     @echo
        inx
        cmp     #'L'|$80
        beq     @echo
        jsr     PR_BELL
        jmp     pr_frame_key
@echo:  stx     g0
        jsr     PR_COUT
        jsr     pr_return
        lda     g0
        rts

pr_return:
        jsr     ld_menu_key
        cmp     #$8D
        bne     pr_return
        rts

; pr_ask_number -- A/Y question, pr_min .. X: Y = the number.
pr_ask_number:
        stx     pr_max
        jsr     ld_print
        jsr     pr_field
@again: jsr     pr_line
        jsr     pr_parse
        bcs     @bad
        lda     pr_num+1
        bne     @bad
        lda     pr_num
        cmp     pr_min
        bcc     @bad
        lda     pr_max
        cmp     pr_num
        bcc     @bad
        ldy     pr_num
        rts
@bad:   jsr     pr_retry
        jmp     @again

; pr_ask_decimal -- A/Y question: a number > 0 (decimals allowed, four
; digits at most), at most 100 (GO1 $5DA3). FAC = the value.
pr_ask_decimal:
        jsr     ld_print
        jsr     pr_field
@again: inc     pr_dot
        jsr     pr_line
        dec     pr_dot
        jsr     pr_parse
        bcs     @bad
        lda     pr_num
        ora     pr_num+1
        beq     @bad
        lda     pr_num+1
        ldy     pr_num
        jsr     GIVAYF
        lda     pr_decimals
        beq     :++
        sta     g0
:       jsr     PR_DIV10
        dec     g0
        bne     :-
:       fop     FCOMP, pr_c100
        cmp     #1
        bne     :+
        fld     pr_c100
:       rts
@bad:   jsr     pr_retry
        jmp     @again

pr_field:
        lda     PR_CH
        sta     pr_col
        rts

; pr_retry -- bell, the typed field cleared.
pr_retry:
        jsr     PR_BELL
        lda     pr_col
        sta     PR_CH
        ldx     #5
        stx     g0
:       lda     #$A0
        jsr     PR_COUT
        dec     g0
        bne     :-
        lda     pr_col
        sta     PR_CH
        rts

; pr_line -- up to four digits (and one '.' when pr_dot), RETURN; the left
; arrow erases. pr_buf, pr_len.
pr_line:
        lda     #0
        sta     pr_len
@key:   jsr     ld_menu_key
        cmp     #$8D
        beq     @done
        cmp     #$88
        bne     @char
        ldx     pr_len
        beq     @key
        dec     pr_len
        dec     PR_CH
        lda     #$A0
        jsr     PR_COUT
        dec     PR_CH
        jmp     @key
@char:  ldx     pr_len
        cpx     #4
        bcs     @bad
        cmp     #'.'|$80
        bne     :+
        ldx     pr_dot
        bne     @put
        beq     @bad
:       cmp     #'0'|$80
        bcc     @bad
        cmp     #'9'|$80+1
        bcs     @bad
@put:   ldx     pr_len
        sta     pr_buf,x
        inc     pr_len
        jsr     PR_COUT
        jmp     @key
@bad:   jsr     PR_BELL
        jmp     @key
@done:  rts

; pr_parse -- pr_buf -> pr_num (all digits) and pr_decimals; C set when
; empty or with two points.
pr_parse:
        lda     #0
        sta     pr_num
        sta     pr_num+1
        sta     pr_decimals
        sta     g1              ; point seen
        ldx     pr_len
        beq     @bad
        ldx     #0
@digit: cpx     pr_len
        beq     @ok
        lda     pr_buf,x
        inx
        cmp     #'.'|$80
        bne     :+
        lda     g1
        bne     @bad
        inc     g1
        bne     @digit
:       and     #$0F
        sta     g2
        lda     g1
        beq     :+
        inc     pr_decimals
:       lda     pr_num          ; num = 10 num + digit
        sta     gp1
        lda     pr_num+1
        sta     gp1+1
        asl     pr_num
        rol     pr_num+1
        asl     pr_num
        rol     pr_num+1
        clc
        lda     pr_num
        adc     gp1
        sta     pr_num
        lda     pr_num+1
        adc     gp1+1
        sta     pr_num+1
        asl     pr_num
        rol     pr_num+1
        clc
        lda     pr_num
        adc     g2
        sta     pr_num
        bcc     @digit
        inc     pr_num+1
        bne     @digit
@ok:    clc
        rts
@bad:   sec
        rts

; ----------------------------------------------------------------------------
; pr_summary -- the introduction words (GO3 $31B0): terrain, difficulty,
; time and date, injury; P journeys clear the questions first and wait.
pr_summary:
        lda     #0
        sta     PR_WNDTOP
        lda     ld_prep
        beq     @words
        jsr     PR_HOME
        lda     #<pr_m_head
        ldy     #>pr_m_head
        jsr     ld_print
        lda     #0
        sta     g0
:       ldx     g0              ; the region (16 characters, zero padded)
        lda     region_name,x
        beq     :+
        ora     #$80
        jsr     PR_COUT
        inc     g0
        lda     g0
        cmp     #16
        bne     :-
:
        lda     #<pr_m_level
        ldy     #>pr_m_level
        jsr     ld_print
        ldx     ld_level
        lda     #0
        jsr     pr_dec
        jsr     PR_CROUT
@words: jsr     PR_CROUT
        lda     #<pr_m_terrain
        ldy     #>pr_m_terrain
        jsr     ld_print
        ldx     #0              ; GO2 $2B3E: L < 4, < 8, else
        lda     ld_level
        cmp     #4
        bcc     :+
        inx
        cmp     #8
        bcc     :+
        inx
:       lda     pr_terrain_lo,x
        ldy     pr_terrain_hi,x
        jsr     ld_print
        lda     #<pr_m_chosen
        ldy     #>pr_m_chosen
        jsr     ld_print
        ldx     #0              ; GO2 $2BAA: L < 2, < 4, < 6, < 8, else
        lda     ld_level
:       cmp     pr_bounds,x
        bcc     :+
        inx
        cpx     #4
        bne     :-
:       lda     pr_difficulty_lo,x
        ldy     pr_difficulty_hi,x
        jsr     ld_print
        lda     #<pr_m_time
        ldy     #>pr_m_time
        jsr     ld_print
        jsr     pr_clock
        lda     pr_research
        beq     :+
        lda     #<pr_m_research
        ldy     #>pr_m_research
        jsr     ld_print
        jmp     @end
:       lda     #<pr_m_you
        ldy     #>pr_m_you
        jsr     ld_print
        ldx     pr_inj
        lda     pr_injury_lo,x
        ldy     pr_injury_hi,x
        jsr     ld_print
        lda     #<pr_m_crash
        ldy     #>pr_m_crash
        jsr     ld_print
@end:   lda     ld_prep
        beq     :+
        lda     #<pr_m_begin
        ldy     #>pr_m_begin
        jsr     ld_print
        jsr     pr_return
        lda     #<pr_m_loading
        ldy     #>pr_m_loading
        jsr     ld_print
:       rts

; pr_clock -- "7:00AM ON MAY 16." (GO2 $2755, $280A).
pr_clock:
        fld     s_hour
        jsr     AYINT
        ldy     $A1
        sty     pr_h
        jsr     PR_SNGFLT
        fop     FSUB, s_hour
        fop     FMULT, pr_c60
        jsr     AYINT
        lda     $A1
        sta     pr_m
        ldy     #'A'|$80
        lda     pr_h
        cmp     #12
        bcc     @am
        ldy     #'P'|$80
        cmp     #12
        beq     @hour
        sbc     #12
        jmp     @hour
@am:    cmp     #0
        bne     @hour
        lda     #12
@hour:  sty     g2
        tax
        lda     #0
        jsr     pr_dec
        lda     #':'|$80
        jsr     PR_COUT
        lda     pr_m
        cmp     #10
        bcs     :+
        lda     #'0'|$80
        jsr     PR_COUT
:       ldx     pr_m
        lda     #0
        jsr     pr_dec
        lda     g2
        jsr     PR_COUT
        lda     #'M'|$80
        jsr     PR_COUT
        lda     #<pr_m_on
        ldy     #>pr_m_on
        jsr     ld_print
        fld     s_date          ; day of the year INT(365 date + 1)
        fop     FMULT, pr_c365
        fop     FADD, PR_ONE
        jsr     AYINT
        ldx     #11
@month: lda     pr_cum_lo,x     ; the last month starting before the day
        cmp     $A1
        lda     pr_cum_hi,x
        sbc     $A0
        bcc     @found
        dex
        bne     @month
@found: stx     g0
        txa                     ; three letters
        asl     a
        adc     g0
        tay
        ldx     #3
:       lda     pr_months,y
        ora     #$80
        jsr     PR_COUT
        iny
        dex
        bne     :-
        lda     #' '|$80
        jsr     PR_COUT
        ldx     g0
        sec
        lda     $A1
        sbc     pr_cum_lo,x
        tax
        lda     #0
        jsr     pr_dec
        lda     #'.'|$80
        jmp     PR_COUT

; pr_dec -- X = 0..255 in decimal (Applesoft's LINPRT needs BASIC's zero
; page and string pointers).
pr_dec: stx     g1
        lda     #0
        sta     g2              ; a digit printed
        ldy     #2
@pow:   ldx     #0
        lda     g1
@sub:   cmp     pr_pow10,y
        bcc     @out
        sbc     pr_pow10,y
        inx
        bne     @sub
@out:   sta     g1
        txa
        bne     @print
        lda     g2
        bne     @zero
        cpy     #0
        bne     @skip
@zero:  txa
@print: ora     #'0'|$80
        jsr     PR_COUT
        inc     g2
@skip:  dey
        bpl     @pow
        rts
pr_pow10: .byte 1, 10, 100

; ----------------------------------------------------------------------------
; Tables and texts.
pr_sizes:  .byte 21, 1, 15, 3, 11, 5, 3, 3, 13       ; GO2 $26B5
pr_always: .byte 2, 21, 22, 38, 52, 59, 64, 25        ; GO2 $26AC
pr_three:  .byte 3, 6, 9, 12, 15, 18
pr_four:   .byte 5, 7, 10, 14
pr_uses_t: .byte 48, 0, 16, 0, 0, 0, 14, 21, 24, 24, 24, 35, 28, 63, 0, 0, 0, 0
           .byte 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 12   ; W8 38..66, template T$21
pr_bounds: .byte 2, 4, 6, 8
pr_cum_lo: .byte <0, <31, <59, <90, <120, <151, <181, <212, <243, <273, <304, <334
pr_cum_hi: .byte >0, >31, >59, >90, >120, >151, >181, >212, >243, >273, >304, >334
pr_months: .byte "JANFEBMARAPRMAYJUNJULAUGSEPOCTNOVDEC"
; Constants, bytes of GO1 and GO2.
pr_c05:   .byte $7C, $4C, $CC, $CC, $CD           ; GO1 $5EB9  .05
pr_cm05:  .byte $7C, $CC, $CC, $CC, $CD           ; GO1 $5EBE -.05
pr_c025:  .byte $7B, $4C, $CC, $CC, $CD           ; GO1 $5EA5  .025
pr_cm075: .byte $7D, $99, $99, $99, $9A           ; GO1 $5EAF -.075
pr_c085:  .byte $7D, $2E, $14, $7A, $E2           ; GO1 $5EB4  .085
pr_c065:  .byte $7D, $05, $1E, $B8, $52           ; GO1 $5EAA, GO2 $23D3  .065
pr_c1_2:  .byte $81, $19, $99, $99, $9A           ; GO1 $5EC3  1.2
pr_c12:   .byte $84, $40, $00, $00, $00           ; GO1 $5ECD  12
pr_c20:   .byte $85, $20, $00, $00, $00           ; GO1 $5ED7  20
pr_c60:   .byte $86, $70, $00, $00, $00           ; GO2 $2853  60
pr_c100:  .byte $87, $48, $00, $00, $00           ; GO1 $5EE1  100
pr_c540:  .byte $8A, $07, $00, $00, $00           ; GO1 $5EEB  540
pr_c3000: .byte $8C, $3B, $80, $00, $00           ; GO1 $5EF0  3000
pr_c997:  .byte $80, $7F, $3B, $64, $5A           ; GO2 $29AA  .997
pr_c045:  .byte $7F, $66, $66, $66, $66           ; GO2 $2105  .45
pr_c03:   .byte $7F, $19, $99, $99, $9A           ; GO2 $29A5  .3
pr_c073:  .byte $7D, $15, $81, $06, $25           ; GO2 $23D8  .073
pr_c598:  .byte $83, $3F, $5C, $28, $F6           ; GO2 $23EC  5.98
pr_c223:  .byte $88, $5F, $00, $00, $00           ; GO2 $23F1  223
pr_c022:  .byte $7B, $34, $39, $58, $11           ; GO2 $23C9  .022
pr_c033:  .byte $7C, $07, $2B, $02, $0C           ; GO2 $23CE  .033
pr_c1_5:  .byte $81, $40, $00, $00, $00           ; GO2 $23E2  1.5
pr_c0092: .byte $7A, $16, $B8, $98, $C8           ; GO2 $23C4  .00919928
pr_c1335: .byte $8B, $26, $E0, $00, $00           ; GO2 $2400  1335
pr_c800:  .byte $8A, $48, $00, $00, $00           ; GO2 $23FB  800
pr_c1_1:  .byte $81, $0C, $CC, $CC, $CD           ; GO2 $23DD  1.1
pr_c1_7:  .byte $81, $59, $99, $99, $9A           ; GO2 $29AF  1.7
pr_c3_5:  .byte $82, $60, $00, $00, $00           ; GO2 $23E7  3.5
pr_c004:  .byte $79, $03, $12, $6E, $98           ; T12 (eating)  .004
pr_c1em7: .byte $69, $56, $BF, $94, $D6           ; 1e-7 (thermal Q)
pr_c360:  .byte $89, $34, $00, $00, $00           ; GO2 $2B39  360
pr_c47:   .byte $86, $3C, $00, $00, $00           ; Sierra $60B4  47
pr_crad:  .byte $7B, $0E, $FA, $39, $18           ; GO2 $2B2A  pi / 180
pr_c29:   .byte $85, $68, $00, $00, $00           ; Sierra ($60B2 - $60B0) / 2
pr_c2:    .byte $82, $00, $00, $00, $00           ; Sierra $60B0
pr_c01:   .byte $7D, $4C, $CC, $CC, $CD           ; GO2 $2B2F  .1
pr_c365:  .byte $89, $36, $80, $00, $00           ; GO2 $2858  365
pr_c32768: .byte $71, $00, $00, $00, $00          ; 1 / 32768

pr_terrain_lo:    .byte <pr_w_moderate, <pr_w_varied, <pr_w_punishing
pr_terrain_hi:    .byte >pr_w_moderate, >pr_w_varied, >pr_w_punishing
pr_difficulty_lo: .byte <pr_w_low, <pr_w_lenient, <pr_w_respectable, <pr_w_challenging, <pr_w_back
pr_difficulty_hi: .byte >pr_w_low, >pr_w_lenient, >pr_w_respectable, >pr_w_challenging, >pr_w_back
pr_injury_lo: .byte <pr_i0, <pr_i1, <pr_i2, <pr_i3
pr_injury_hi: .byte >pr_i0, >pr_i1, >pr_i2, >pr_i3
pr_verdict_lo: .byte <pr_v0, <pr_v1, <pr_v2, <pr_v3, <pr_v4
pr_verdict_hi: .byte >pr_v0, >pr_v1, >pr_v2, >pr_v3, >pr_v4
pr_w_moderate:    .byte "MODERATE.", 13, 0
pr_w_varied:      .byte "VARIED.", 13, 0
pr_w_punishing:   .byte "PUNISHING.", 13, 0
pr_w_low:         .byte "LOW", 0
pr_w_lenient:     .byte "LENIENT", 0
pr_w_respectable: .byte "RESPECTABLE", 0
pr_w_challenging: .byte "CHALLENGING", 0
pr_w_back:        .byte "BACK-BREAKING", 0
pr_i0: .byte "NOT BEEN INJURED", 0
pr_i1: .byte "RECEIVED SEVERAL BAD CUTS", 0
pr_i2: .byte "RECEIVED A BROKEN ARM", 0
pr_i3: .byte "RECEIVED A BROKEN LEG", 0
pr_v0: .byte "YOU SHOULD SEE A DOCTOR IMMEDIATELY!", 13, 0
pr_v1: .byte "YOUR PHYSICAL CONDITION IS TERRIBLE!", 13, 0
pr_v2: .byte "YOU COULD BENEFIT FROM A PHYSICAL", 13, "   FITNESS PROGRAM.", 13, 0
pr_v3: .byte "YOU ARE REALLY IN PRETTY GOOD SHAPE.", 13, 0
pr_v4: .byte "YOU ARE OLYMPIC ATHLETE MATERIAL!", 13, 0
pr_m_head:
        .byte   "          JOURNEY PREPARATION", 13
        .byte   "----------------------------------------", 0
pr_m_q1:
        .byte   13, 13, "1. DO YOU WANT TO CHOOSE THE STARTING", 13
        .byte   "   DATE AND TIME [Y/N] ? ", 0
pr_m_month: .byte 13, "   SELECT NUMBER OF MONTH [1-12]: ", 0
pr_m_hour:  .byte 13, "   SELECT HOUR [0-24] PAST MIDNIGHT: ", 0
pr_m_q2:
        .byte   13, 13, "2. DO YOU WANT NORMAL PLAY [P], OR", 13
        .byte   "   RESEARCH MODE [R] ? ", 0
pr_m_q3: .byte  13, 13, "3. ARE YOU MALE [M] OR FEMALE [F] ? ", 0
pr_m_q4: .byte  13, 13, "4. WHAT IS YOUR WEIGHT IN POUNDS? ", 0
pr_m_q5:
        .byte   13, 13, "5. DO YOU HAVE A SMALL [S], MEDIUM [M],", 13
        .byte   "   OR LARGE [L] BODY FRAME ? ", 0
pr_m_q6: .byte  13, 13, "6. HOW TALL ARE YOU IN INCHES ? ", 0
pr_m_q7: .byte  13, 13, "7. WHAT IS YOUR AGE IN YEARS ? ", 0
pr_m_q8:
        .byte   13, 13, "8. CHECK YOUR PULSE AND GIVE ME YOUR", 13
        .byte   "   RESTING HEART RATE IN BEATS/MIN: ", 0
pr_m_q9:
        .byte   13, 13, "9. SELECT WILDLIFE ENCOUNTER FREQUENCY", 13
        .byte   "   [1.0 IS NORMAL]: ", 0
pr_m_q10:
        .byte   13, 13, "10. SELECT WEATHER STORM FREQUENCY", 13
        .byte   "    [1.0 IS NORMAL]: ", 0
pr_m_level:   .byte ", LEVEL ", 0
pr_m_terrain: .byte "THE TERRAIN IS ", 0
pr_m_chosen:  .byte "LEVEL OF DIFFICULTY: ", 0
pr_m_time:    .byte ".", 13, "THE TIME IS ", 0
pr_m_on:      .byte " ON ", 0
pr_m_you:     .byte 13, "YOU HAVE ", 0
pr_m_crash:   .byte 13, "IN THE CRASH.", 0
pr_m_research: .byte 13, "RESEARCH MODE: INSTRUMENTS AT HAND.", 0
pr_m_begin:   .byte 13, 13, "PRESS RETURN TO BEGIN.", 0
pr_m_loading: .byte 13, 13, "LOADING...", 0

; Answers and work (in the file: zero at every load).
pr_fixed:   .res 5              ; imposed RND (tests/test_prepare.py), 0: none
pr_seed:    .res 2
pr_lv:      .res 5
pr_t1:      .res 5
pr_t2:      .res 5
pr_t3:      .res 5
pr_t4:      .res 5
pr_storm:   .res 5
pr_wild:    .res 5
pr_freq:    .res 5
pr_dated:   .res 1
pr_month:   .res 1
pr_hour:    .res 1
pr_research: .res 1
pr_sex:     .res 1
pr_weight:  .res 2
pr_frame:   .res 1
pr_height:  .res 1
pr_age:     .res 1
pr_pulse:   .res 1
pr_ow:      .res 2
pr_q:       .res 2
pr_inj:     .res 1
pr_verdict: .res 1
pr_base:    .res 1
pr_g:       .res 1
pr_s:       .res 1
pr_a:       .res 1
pr_b:       .res 1
pr_k:       .res 1
pr_count:   .res 1
pr_min:     .res 1
pr_max:     .res 1
pr_num:     .res 2
pr_decimals: .res 1
pr_dot:     .res 1
pr_len:     .res 1
pr_col:     .res 1
pr_buf:     .res 4
pr_h:       .res 1
pr_m:       .res 1
.assert th_surface >= $4000 && th_native_composition < $5780, error, "resident body constants"
.assert wf_storm >= $4000 && wf_storm < $5780, error, "resident storm constant"
