.segment "STATUS"
th_display10: .byte $84,$20,0,0,0
th_display95: .byte $80,$73,$33,$33,$33
; STATUS, 80 columns (docs/MENUS.md 5, 9; 15 October 2026: with MEDICAL's
; conditions and care; the provisions moved to OBJECTS, the rangers to
; MENU). Under the tab row, the halves of rows 2-14 are each written top to
; bottom so that every cell is written once (differential, no stale cell of
; another page), then the full rows 15-21. Left, with the row width set to
; 41 (a CR pads to it, vtab pads what it skips): CONDITION (the player's
; word; HEALTH, ENERGY, HUNGER, THIRST with their gauge and percent, BODY;
; rows 4-12, a blank row between two: 15 October 2026). Right, from column
; 41 (st_at pads the right half of the rows it passes): LOCAL (rows 2-10:
; date and time, air and felt temperature, sky and wind, altitude and
; ground, the situation on rows 7-9), CONDITIONS (rows 11-14: dehydration,
; starvation, exhaustion, hypo- or hyperthermia, two a row). Rows 15-20:
; MEDICAL, the thirteen conditions and altitude sickness in three columns
; (severity: 100 - the simulation's percent; care mark: ACTIVE, TREATED,
; PROTECTED). Care: DOWN puts the focus on the active conditions in turn
; (the name in inverse); row 23 then shows the treatment gestures of the
; condition (LEFT/RIGHT choose, RETURN types it, src/care.s; CUT BODY
; without a blade in use, the FRSTAID KIT in the dark, type USE KNIFE (AXE)
; or USE FLASHLIGHT first and leave the gesture to the grid's queue,
; src/grid.s). On NeoWildernessXL each block is a post-it (src/mt_pages.s):
; the same cells, framed.
ST_RIGHT = 41                   ; first column of the right-hand blocks
ST_FOOD  = 18                   ; CARRYING (OBJECTS): food, water columns
ST_WATER = 29
ST_VAL   = 50                   ; LOCAL: value, second label, value
ST_LBL2  = 62
ST_VAL2  = 69
ST_COND  = 11                   ; CONDITIONS' heading (right, under LOCAL)
ST_COL2  = 60                   ; its second column
ST_MED   = 15                   ; MEDICAL's first row
module_status:
        lda     pg_open
        bpl     :+
        inc     pg_open         ; $FF -> 0: UP resumes; typed STATUS stays explicit
        ldx     pg_cur
        jmp     page_dispatch
:
        lda     pg_open         ; the grid's CARE: on the first active
        beq     :+              ; condition (src/grid.s)
        jsr     sr_open
        bne     @apply
:       lda     pg_focus        ; a move of the care's focus: as is
        bne     status_care
@apply: jsr     goal_pct        ; brings journey_left up to date (as the
        jsr     medical_apply   ; reference's STATUS); MEDICAL ($5800): the
                                ; percentages of now
status_care:
        ldx     #0              ; the active conditions, in pg_act
        ldy     #0
@act:   lda     injury_active,x
        beq     :+
        txa
        sta     pg_act,y
        iny
:       inx
        cpx     #13
        bcc     @act
        sty     pg_levels       ; (PG_STATUS: 0)
        cpy     pg_focus        ; one healed under the focus: the last
        bcs     :+
        sty     pg_focus
:       lda     pg_focus        ; another condition: its first gesture
        cmp     pg_gf
        beq     :+
        sta     pg_gf
        lda     #0
        sta     pg_g
:       lda     #PG_STATUS
        jsr     page_top
        lda     #41             ; rows 2-14 left half: CR pads to column 40
        sta     WNDWDTH
        lda     #$3F
        sta     INVFLG
        jsr     puts
        .byte   " CONDITION: ", 0
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
        jsr     puts
        .byte   " ", 0
        lda     #$FF
        sta     INVFLG
        lda     #st_health_label
        jsr     st_gauge_text
        fld     f_hmax
        fop     FDIV, s_health
        fop     FMULT, f_100
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     st_pct
        jsr     st_cells        ; ten cells: (percent + 5) / 10
        jsr     bar
        lda     st_pct
        jsr     pdec
        lda     #st_energy_label
        jsr     st_gauge_text
        ; ENERGY: BEAT if 16 h without rest, TIRED over 12 h of rest deficit,
        ; OKAY over 7, else GREAT (deficit replaces the original's F1[24])
        lda     #0
        sta     st_lvl
        fld     s_rest
        fop     FCOMP, f_16
        cmp     #1
        beq     @enrg
        inc     st_lvl
        fld     s_defr
        fop     FCOMP, f_12
        cmp     #1
        beq     @enrg
        inc     st_lvl
        fop     FCOMP, f_7
        cmp     #1
        beq     @enrg
        inc     st_lvl
@enrg:  lda     st_lvl          ; BEAT: an empty gauge
        beq     :+
        lda     #<s_defr
        ldy     #>s_defr
        jsr     hours_fill
:
        jsr     gauge_bar
        ldx     st_lvl
        lda     #<w_enrg
        sta     gp2
        lda     #>w_enrg
        sta     gp2+1
        lda     #6
        jsr     word
        lda     #st_hunger_label
        jsr     st_gauge_text
        lda     #<s_eat         ; VERY over 12 h, SO-SO over 6 h
        ldy     #>s_eat
        jsr     hours_gauge
        lda     #st_thirst_label
        jsr     st_gauge_text
        lda     #<s_drink
        ldy     #>s_drink
        jsr     hours_gauge
        lda     #st_body_label
        jsr     st_gauge_text
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
        lda     thermal_mode
        beq     @thermal_done
        cmp     #1
        beq     @sweat
        lda     #st_shivering_hint
        jsr     om_bank_puts
        jmp     @thermal_done
@sweat: lda     #st_sweating_hint
        jsr     om_bank_puts
@thermal_done:
        lda     #ST_MED         ; the rest of the left half, down to row 14
        jsr     vtab
        lda     #80             ; right column: rows 2-14 from ST_RIGHT (st_at)
        sta     WNDWDTH
        lda     #2
        sta     CV
        jsr     st_at
        lda     #0
        jsr     st_heading
        lda     #3
        jsr     st_at
        jsr     puts
        .byte   "DATE", 0
        lda     #ST_VAL
        jsr     tab
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
        lda     #' '|$80
        jsr     COUT
        lda     g0
        jsr     pdec
        lda     #ST_LBL2
        jsr     tab
        jsr     puts
        .byte   "TIME", 0
        lda     #ST_VAL2
        jsr     tab
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
        jmp     @air
@noclock:
        lda     #<w_period
        sta     gp2
        lda     #>w_period
        sta     gp2+1
        ldx     period
        lda     #5
        jsr     word
@air:   lda     #4
        jsr     st_at
        jsr     puts
        .byte   "AIR", 0
        lda     #ST_VAL
        jsr     tab
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
        lda     #'F'|$80
        jsr     COUT
        jmp     @felt
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
@felt:  lda     #ST_LBL2
        jsr     tab
        lda     #st_feels_label
        jsr     st_gauge_text
        lda     #ST_VAL2
        jsr     tab
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
        lda     #'F'|$80
        jsr     COUT
        lda     #5
        jsr     st_at
        jsr     puts
        .byte   "SKY", 0
        lda     #ST_VAL
        jsr     tab
        lda     #<sky_words
        sta     gp2
        lda     #>sky_words
        sta     gp2+1
        ldx     weather_sky
        lda     #5
        jsr     word
        lda     #ST_LBL2
        jsr     tab
        jsr     puts
        .byte   "WIND", 0
        lda     #ST_VAL2
        jsr     tab
        lda     wind
        jsr     pdec
        lda     #st_mph_label
        jsr     st_gauge_text
        lda     #6
        jsr     st_at
        jsr     puts
        .byte   "ALT", 0
        lda     #ST_VAL
        jsr     tab
        jsr     level_here
        clc
        adc     M_BASE
        sta     g0
        ldx     #55             ; ALTIMETER
        jsr     have
        bcc     @aword
        lda     g0
        jsr     pdec
        lda     #st_feet_label
        jsr     st_gauge_text
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
@grnd:  lda     #ST_LBL2
        jsr     tab
        lda     #st_ground_label
        jsr     st_gauge_text
        lda     #ST_VAL2
        jsr     tab
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
        ; the situation, a row each from row 7
        lda     #6
        sta     st_srow
        lda     tree_in
        beq     :+
        jsr     st_next
        lda     #st_tree_hint
        jsr     om_bank_puts
:       lda     it_place+21
        cmp     #5
        bne     :+
        jsr     st_next
        lda     #st_hung_hint
        jsr     om_bank_puts
:       lda     shelter_inside
        beq     :+
        jsr     st_next
        lda     #st_inside_hint
        jsr     om_bank_puts
:       lda     wet_mode
        cmp     #2
        bne     :+
        jsr     st_next
        lda     #st_immersed_hint
        jsr     om_bank_puts
:       lda     st_srow
        cmp     #6
        bne     :+
        jsr     st_next
        lda     #st_open_hint
        jsr     om_bank_puts
:
        ; CONDITIONS (rows 11-14, under LOCAL; 15 October 2026): dehydration,
        ; starvation, exhaustion under 95 %, hypo- or hyperthermia, two a row
        ; (the injuries: MEDICAL below)
        lda     #ST_COND
        jsr     st_at
        lda     #33
        jsr     st_heading
        lda     #0
        sta     st_lvl
        ldx     #0
        jsr     cond
        ldx     #1
        jsr     cond
        ldx     #2
        jsr     cond
        fld     s_therm_factor
        fop     FCOMP, th_display95
        cmp     #$FF
        bne     @injuries
        jsr     item
        fld     s_body
        fop     FCOMP, f_body
        cmp     #$FF
        bne     @hyper
        lda     #st_hypo_label
        jsr     st_gauge_text
        jmp     @injuries
@hyper: lda     #st_hyper_label
        jsr     st_gauge_text
@injuries:
        lda     st_lvl
        bne     :+
        jsr     item
        jsr     puts
        .byte   "NONE", 0
:       lda     #ST_MED         ; the rest of the right half, down to row 14
        jsr     st_at
        lda     #ST_MED         ; MEDICAL: full rows from row 15
        ldx     #0
        jsr     st_at_x
        lda     #46
        jsr     st_heading
        ldx     #0              ; the legend: each mark and its word
@leg:   stx     st_i
        jsr     puts
        .byte   "  ", 0
        ldx     st_i
        lda     st_marks,x
        jsr     COUT
        lda     #' '|$80
        jsr     COUT
        ldx     st_i
        jsr     st_care_text
        ldx     st_i
        inx
        cpx     #3
        bcc     @leg
        ldx     #0              ; rows 16-20: conditions r, r + 5, r + 10
@row:   stx     st_i
        jsr     CROUT
        lda     #0
        jsr     med_cell
        lda     #27
        jsr     tab
        lda     st_i
        clc
        adc     #5
        tax
        lda     #27
        jsr     med_cell
        lda     #53
        jsr     tab
        lda     st_i
        clc
        adc     #10
        cmp     #14
        bcs     :+
        tax
        lda     #53
        jsr     med_cell
:       ldx     st_i
        inx
        cpx     #5
        bcc     @row
        lda     pg_focus        ; the care's focus: the gestures on row 23
        beq     :+
        lda     #19
        jsr     overlay_load
        jsr     med_foot
        jmp     status_key
:       lda     #<st_keys
        ldy     #>st_keys
        XL_ABS  XI_STATUS, page_foot_x, @x17
        jsr     page_foot
status_key:
@key:   jsr     wait_key
        jsr     page_keys
        ldy     pg_focus
        beq     @key
        ldx     pg_g            ; the gestures of the focused condition
        cmp     #KC_LEFT
        bne     :+
        dex
        bpl     @g
        ldx     pg_gn
        dex
        bpl     @g
:       cmp     #KC_RIGHT
        bne     :+
        inx
        cpx     pg_gn
        bcc     @g
        ldx     #0
@g:     stx     pg_g
        jmp     status_care
:       cmp     #KC_RET
        beq     :+
        cmp     #' '
        bne     @key
:       lda     #19             ; MEDVIEW: the gestures (src/care.s)
        jsr     overlay_load
        jmp     med_run

; med_cell -- condition X (13: altitude sickness) from column A (the cursor
; there): its name (in inverse under the focus), its percent at +18, its
; care mark at +23.
med_cell:
        sta     st_col
        stx     st_cx
        ldy     pg_focus        ; the focused condition: in inverse
        beq     :+
        txa
        cmp     pg_act-1,y
        bne     :+
        lda     #$3F
        sta     INVFLG
:       jsr     med_name_text
        lda     #$FF
        sta     INVFLG
        lda     st_col
        clc
        adc     #18
        jsr     tab
        ldx     st_cx
        lda     altitude_percent
        cpx     #13
        bcs     :+
        lda     injury_percent,x
:       eor     #$FF            ; shown as the severity: 100 - x (0%: none)
        clc
        adc     #101
        jsr     pdec
        lda     #'%'|$80
        jsr     COUT
        lda     st_col
        clc
        adc     #23
        jsr     tab
        ldx     st_cx
        cpx     #13
        bcs     @rts
        ldy     #1
        lda     injury_treated,x
        bne     @mark
        dey
        lda     injury_active,x
        bne     @mark
        ldy     #2
        lda     injury_prevented,x
        beq     @rts
@mark:  lda     st_marks,y
        jmp     COUT
@rts:   rts
; The care marks: ACTIVE (care needed), TREATED, PROTECTED (XL: MouseText,
; docs/MENUS.md 9: an inverse X, a check mark, a diamond).
st_marks: .byte $18, '+'|$80, '*'|$80
        XL_BYTE XI_STATUS, st_marks+1, MT_CHECK
        XL_BYTE XI_STATUS, st_marks+2, MT_DIAMOND
st_care_ids: .byte om_doses_label,om_doses_label,om_doses_label
st_care_offsets: .byte 19,38,58
st_col: .byte 0
st_cx:   .byte 0

; st_rangers -- (MENU) a new row: the distance to the rangers, the bearing
; with a compass.
st_rangers:
        jsr     CROUT
        lda     journey_left
        sta     num
        lda     journey_left+1
        sta     num+1
        jsr     print_u16
        lda     #st_cells_hint
        jsr     om_bank_puts
        ldx     #53             ; COMPASS
        jsr     have
        bcc     @situation
        jsr     bearing
@situation:
        rts
; st_cells -- A (0..100): the full cells of a gauge, (A + 5) / 10.
st_cells:
        clc
        adc     #5
        ldx     #$FF
        sec
:       inx
        sbc     #10
        bcs     :-
        txa
        rts

; st_next -- the next row of the situation.
st_next:
        inc     st_srow
        lda     st_srow
        jmp     st_at

; Helpers of the page (in the module: it runs in the SIM window, with room).
; st_at -- the cursor on row A (at or below CV), column ST_RIGHT: the rest
; of the current row and the right half of every skipped row are padded
; (differential), the left half is left alone. st_at_x: row A, column X,
; nothing padded.
st_at:  sta     st_tgt
@pad:   lda     CV
        cmp     st_tgt
        bcs     @set
        jsr     topo_pad
        inc     CV
        jsr     t_vtab
        lda     #ST_RIGHT
        sta     CH
        bne     @pad
@set:   lda     st_tgt
        ldx     #ST_RIGHT
st_at_x:
        sta     CV
        jsr     t_vtab
        stx     CH
        rts
; item -- the cursor on the next cell of the list of conditions (st_lvl:
; the cells used), two a row from row ST_COND+1: column ST_RIGHT, then ST_COL2.
; Four at most (dehydration, starvation, exhaustion, a thermal one).
item:   lda     st_lvl
        inc     st_lvl
        lsr     a
        bcs     @col2
        adc     #ST_COND+1      ; (C clear)
        jmp     st_at
@col2:  lda     #ST_COL2
        jmp     tab

; st_heading -- A = offset of a banked page heading, in inverse.
st_heading:
        pha
        lda     #$3F
        sta     INVFLG
        pla
        jsr     pg_heading_text
        lda     #$FF
        sta     INVFLG
        rts

; bar -- a gauge of ten cells, A of them full (inverse spaces), then two
; spaces.
bar:    XL_JMP  XI_STATUS, bar_x, @p06          ; (XL: MouseText cells)
        cmp     #11
        bcc     :+
        lda     #10
:       sta     st_fill
        lda     #$3F
        sta     INVFLG
        ldx     #0
@on:    cpx     st_fill
        bcs     @off
        lda     #' '|$80
        jsr     COUT
        inx
        bne     @on
@off:   lda     #$FF
        sta     INVFLG
@dot:   cpx     #10
        bcs     @end
        lda     #'.'|$80
        jsr     COUT
        inx
        bne     @dot
@end:   jsr     puts
        .byte   "  ", 0
        rts

st_fill: .byte  0
st_keys: .byte  "T TOPO", 0
        ; XL: the up arrow (UP on the tabs opens TOPO; T still does).
        XL_BYTE XI_STATUS, st_keys, MS_UP
; gauge_bar -- A = the full cells (0..10): the gauge, then their percent
; (ten a cell) and a space, before the gauge's word ("90% OKAY").
gauge_bar:
        pha
        jsr     bar
        pla
        asl     a
        sta     st_i
        asl     a
        asl     a
        adc     st_i            ; (C clear: 80 at most)
        jsr     pdec
        jsr     puts
        .byte   "% ", 0
        rts
; hours_gauge -- the gauge and the word of HUNGER or THIRST, hours at (A,Y).
hours_gauge:
        sta     st_ptr
        sty     st_ptr+1
        jsr     hours_fill
        jsr     gauge_bar
        lda     st_ptr
        ldy     st_ptr+1
        jmp     gauge
; hours_fill -- A = full cells of a gauge for the hours at (A,Y): one cell
; less every 1.5 hours (6 h: six cells, 12 h: two), 0..10.
hours_fill:
        jsr     MOVFM
        fop     FMULT, f_two_thirds
        jsr     AYINT
        lda     $A0
        bmi     @full
        bne     @empty
        lda     $A1
        cmp     #10
        bcs     @empty
        eor     #$FF            ; 10 - A
        sec
        adc     #10
        rts
@full:  lda     #10
        rts
@empty: lda     #0
        rts

; bearing -- ", NORTH-EAST" and so on: the direction of the goal cell (world
; Y grows north); a component under half of the other is dropped. Nothing
; on the goal cell itself.
bearing:
        lda     M_GOALX
        sec
        sbc     px+1
        sta     st_dx
        jsr     st_abs
        sta     st_ax
        lda     M_GOALY
        sec
        sbc     py+1
        sta     st_dy
        jsr     st_abs
        sta     st_ay
        ora     st_ax
        beq     @rts
        jsr     puts
        .byte   ", ", 0
        lda     st_ay           ; north or south unless |dy| < |dx| / 2
        asl     a
        cmp     st_ax
        bcc     @east
        lda     #<w_ns
        ldy     #>w_ns
        ldx     #0
        bit     st_dy
        bpl     :+
        inx
:       jsr     st_word         ; NORTH or SOUTH
        lda     st_ax           ; then "-" when east or west follows
        asl     a
        cmp     st_ay
        bcc     @rts
        lda     #'-'|$80
        jsr     COUT
@east:  lda     #<w_ew
        ldy     #>w_ew
        ldx     #0
        bit     st_dx
        bpl     st_word
        inx
        bne     st_word         ; always
@rts:   rts
; st_word -- word X (5 letters) of the table at (A,Y).
st_word:
        sta     gp2
        sty     gp2+1
        lda     #5
        jmp     word
st_abs: bpl     :+
        eor     #$FF
        clc
        adc     #1
:       rts

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
cond:   stx     st_cx           ; (not g1: STATUS leaves g0, g1 as the
        lda     cdef_lo,x       ; reference does, tests/test_reference_state.py)
        ldy     cdef_hi,x
        jsr     MOVFM
        fst     t1
        ldx     st_cx
        lda     ctol_lo,x
        ldy     ctol_hi,x
        jsr     MOVFM
        fop     FMULT, f_0_2236
        fop     FCOMP, t1
        cmp     #$FF
        bne     @no
        jsr     item
        ldx     st_cx
        lda     cname_offsets,x
        jsr     st_kind_suffix
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


; status_stock_line -- after its label, the food and water ounces of a row of
; PROVISIONS: carried (kind 0), here (1), within reach (2, as the original's
; FOOD and WATER). A split food contributes once to each of the first two.
status_stock_line:
        ldx     status_stock_kind
        jsr     st_kind_text
        lda     #ST_FOOD
        jsr     tab
        lda     #0
        sta     num
        sta     num+1
        ldx     #23
@sum:   jsr     status_stock_oz
        inx
        cpx     #38
        bcc     @sum
        jsr     print_u16
        lda     #om_unit_oz
        jsr     om_bank_puts
        lda     #ST_WATER
        jsr     tab
        lda     #0
        sta     num
        sta     num+1
        ldx     #N_WATER
        jsr     status_stock_oz
        jsr     print_u16
        lda     #om_unit_oz
        jsr     om_bank_puts
        rts
print_str_ay:
        pha
        tya
        tax
        pla
        jmp     print_str_ax
status_stock_oz:
        lda     status_stock_kind
        cmp     #2
        jeq     reach_oz
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
st_done:  .byte 0
st_pct:   .byte 0
st_lvl:   .byte 0
st_i:     .byte 0
st_srow:   .byte 0
st_tgt:    .byte 0
st_ptr:   .word 0
st_dx:    .byte 0
st_dy:    .byte 0
st_ax:    .byte 0
st_ay:    .byte 0

.segment "STATUS"
mdays:  .byte   31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30
cname_offsets: .byte 17,29,40
tlimits: .byte  32, 60, 80, 95
w_temp: .byte   "FREEZECOLD  NICE  WARM  HOT   "
w_alt:  .byte   "LOW   MEDIUMHIGH  "
w_grnd: .byte   "CLEARROCKYWOODSSCRUB"
f_two_thirds: .byte $80,$2A,$AA,$AA,$AB
w_ns:   .byte   "NORTHSOUTH"
w_ew:   .byte   "EAST WEST "
st_kind_ids: .byte om_carried_label,om_local_label,om_carried_label
st_kind_offsets: .byte 0,0,8


.segment "ENVIRON"
tree_effort: .byte $7B,$23,$D7,$0A,$3E ; native T12/S08 $5CBE, .02 * body weight

        .include "inventory.s"   ; INVENTORY, in the same module
        .include "pages.s"       ; the tab row, MEDICAL, MENU
        .include "mt_pages.s"    ; NeoWildernessXL: the MouseText pages (STATX)

.pushseg
.segment "STATUS"
; Several short gauge labels share one fetched text, with embedded NULs.
pg_tab_text:
        pha
        lda     #om_hung_label
        jmp     st_bank_suffix
st_kind_text:
        lda     st_kind_offsets,x
        pha
        lda     st_kind_ids,x
        jmp     st_bank_suffix
st_kind_suffix:
        pha
        lda     #om_carried_label
        jmp     st_bank_suffix
pg_heading_text:
        pha
        lda     #pg_heading_texts
        bne     st_bank_suffix
pg_line_text:
        pha
        lda     #pg_line_texts
        bne     st_bank_suffix
st_gauge_text:
        pha
        lda     #st_gauge_labels
st_bank_suffix:
        jsr     text_fetch
        pla
        clc
        adc     #<tb_buf
        ldx     #>tb_buf
        bcc     :+
        inx
:       jmp     print_str_ax
st_care_text:
        lda     st_care_offsets,x
        pha
        lda     st_care_ids,x
        jmp     st_bank_suffix
med_name_text:
        lda     med_name_offsets,x
        pha
        lda     med_name_ids,x
        jmp     st_bank_suffix
.popseg

.pushseg
.segment "STATX"
; Upper-mid binary search reuses the read-only transfer projection.
; At most 16 trials, even with a 65535-ounce source.
om_fit_search:
        lda     om_max
        sta     om_fit_upper
        lda     om_max+1
        sta     om_fit_upper+1
@loop:  lda     om_fit
        cmp     om_fit_upper
        lda     om_fit+1
        sbc     om_fit_upper+1
        bcs     @done
        sec
        lda     om_fit
        adc     om_fit_upper
        sta     om_qty
        lda     om_fit+1
        adc     om_fit_upper+1
        ror     a
        sta     om_qty+1
        ror     om_qty
        lda     om_action
        cmp     #7
        bne     @project
        lda     it_pack_hi+N_WATER
        ora     om_qty+1
        bne     @bad
        clc
        lda     it_pack_lo+N_WATER
        adc     om_qty
        bcs     @bad
        cmp     #65
        bcs     @bad
@project:
        jsr     om_project
        lda     om_bad
        bne     @bad
        ldy     #6
@check: lda     load_limits,y
        cmp     om_total,y
        lda     load_limits+1,y
        sbc     om_total+1,y
        bcc     @bad
        dey
        dey
        bpl     @check
        lda     om_qty
        sta     om_fit
        lda     om_qty+1
        sta     om_fit+1
        jmp     @loop
@bad:   lda     om_qty
        bne     :+
        dec     om_qty+1
:       sec
        sbc     #1
        sta     om_fit_upper
        lda     om_qty+1
        sta     om_fit_upper+1
        jmp     @loop
@done:  lda     om_max
        sta     om_qty
        lda     om_max+1
        sta     om_qty+1
        rts

.popseg

.pushseg
.segment "STATX"
om_detail_num:
        sta     num+1
        bcs     :+
        lda     #0
        sta     num
        sta     num+1
:       jmp     print_u16
.popseg

.pushseg
.segment "STATUS"
; Capture identity before the care overlay can be replaced by simulation.
sr_prepare:
        ldx     pg_focus
        stx     sr_focus
        lda     pg_act-1,x
        sta     sr_condition
        lda     pg_g
        sta     sr_gesture
        lda     #S_CARE_RETURN
        sta     mq_list
        sta     mq_list+1
        lda     #2
        sta     mq_n
        lsr     a
        sta     mq_i
        lda     journey_encounters
        sta     mq_enc
        rts
; CARE uses 1; a completed return uses bit 6 and its rebuilt active index.
sr_open:
        tax
        and     #$3F
        sta     pg_focus
        sta     pg_gf
        lda     #0
        sta     pg_open
        txa
        and     #$40
        beq     :+
        lda     sr_gesture
        sta     pg_g
:       lda     pg_focus
        rts
.popseg
.pushseg
.segment "BSS"
sr_condition: .res 1
sr_focus: .res 1
sr_gesture: .res 1
.popseg
