; Four short fields around the compass, outside the command area: left
; panel, health then alert or hint; right panel, clock and journey day then
; the more pressing need (hunger or thirst). Lot 4: native DHGR colour, the
; 7-row font of tools/dhgr_font.py on black panels (byte groups 0..6 and
; 13..19, rows 0..15; the right panel starts UI_GAP pixels after the
; ribbon): labels grey, values aqua / yellow, warnings white on red, hints
; light blue. Ink colours have three or
; four dots per pixel (white, aqua, yellow, light blue, grey): on a
; composite display (and POM2) a 2-dot colour such as green draws thin,
; broken strokes. tools/dhgr_ui.py is the model.
UI_BLACK = 0
UI_WARN  = 1                    ; magenta (deep red) strip behind warnings
UI_CALM  = 10                   ; grey
UI_LABEL = 10                   ; grey
UI_GOOD  = 14                   ; aqua (3-dot colours stay full width)
UI_FAIR  = 13                   ; yellow
UI_HINT  = 7                    ; light blue
UI_WHITE = 15
UI_CHARS = 16                   ; characters per field (49 pixels hold 13)
UI_GAP   = 4                    ; pixels between the ribbon and the right panel
; Field buffer: one entry per character (free outside the ray loop).
f_lo  = overlay_text            ; glyph address
f_hi  = overlay_text + UI_CHARS
f_w   = overlay_text + UI_CHARS*2   ; width in pixels
f_ink = overlay_text + UI_CHARS*3
f_bg  = overlay_text + UI_CHARS*4
.assert f_bg + UI_CHARS <= line_pix, error, "field buffer overlaps line_pix"
.segment "GDATA"
ui_enabled: .byte 1
ui_dirty: .byte 1
ui_initialized: .byte 0
ui_previous: .res 6
ui_pending: .byte 0
ui_events: .byte 0
.segment "GCODE"
summary_prepare:
        lda     ui_enabled
        beq     @done
        lda     ui_dirty
        beq     @done
        lda     #15
        jsr     overlay_load
        jsr     module_summary
        lda     #0
        sta     ui_dirty
@done:  rts
; Item commands need a new hint/clock, but arrow turns reuse the header.
summary_refresh:
        bit     obj_keep        ; a transfer of OBJECTS: the page comes back
        bmi     @done           ; (the header waits: ui_dirty, at its exit)
        lda     ui_enabled
        beq     @done
        lda     ui_dirty
        beq     @done
        jsr     summary_prepare
        lda     scene_asset
        beq     @done
        cmp     #SITE_ASSET     ; a site sprite is not in the $5800 window
        bcs     @done
        jmp     overlay_load
@done:  rts

.segment "SUMMARY"
module_summary:
        lda     #0
        sta     summary_inverse
        sta     summary_n
        sta     summary_field   ; field 0: left panel, upper line: health
        lda     $36
        sta     summary_vector
        lda     $37
        sta     summary_vector+1
        lda     #<summary_output
        sta     $36
        lda     #>summary_output
        sta     $37
        lda     #UI_LABEL
        sta     summary_ink
        jsr     puts
        .byte "HEALTH ",0
        fld     f_hmax
        fop     FDIV, s_health
        fop     FMULT, f_100
        fop     FADD, f_half
        jsr     AYINT
        ldx     #UI_GOOD
        lda     $A1
        cmp     #70
        bcs     :+
        ldx     #UI_FAIR
        cmp     #40
        bcs     :+
        inc     summary_inverse ; poor health stays visible after its first alert
:       stx     summary_ink
        jsr     pdec
        jsr     puts
        .byte "%",0
        jsr     field_next      ; field 1: left panel, lower line: alert or hint
        jsr     summary_hint
        jsr     field_next      ; field 2: right panel, upper line: clock, day
        lda     #UI_WHITE
        sta     summary_ink
        ldx     #54
        jsr     have
        bcc     @period
        display_clock summary_hour, summary_minute
        lda     summary_hour
        jsr     pdec
        jsr     puts
        .byte ":",0
        lda     summary_minute
        cmp     #10
        bcs     :+
        jsr     puts
        .byte "0",0
:       lda     summary_minute
        jsr     pdec
        jmp     @day
@period:
        lda     #<summary_periods
        sta     gp2
        lda     #>summary_periods
        sta     gp2+1
        ldx     period
        lda     #5
        jsr     word
@day:   lda     #UI_LABEL
        sta     summary_ink
        jsr     puts
        .byte " - DAY ",0     ; "10:30 - DAY 12": 42 of the panel's 45 pixels
        ; Day of the journey: the day of the year of STATUS (INT(date * 365
        ; + 1)) less 125, plus 365 across New Year: the crash of May 6 (day
        ; 126) is day 1.
        fld     s_date
        fop     FMULT, f_365
        fop     FADD, f_one
        jsr     AYINT
        lda     $A1
        sec
        sbc     #125
        sta     num
        lda     $A0
        sbc     #0
        sta     num+1
        bpl     :+
        lda     num
        clc
        adc     #<365
        sta     num
        lda     num+1
        adc     #>365
        sta     num+1
:       lda     #UI_WHITE
        sta     summary_ink
        jsr     print_u16
        jsr     field_next      ; field 3: right panel, lower line: the need
        fld     s_drink         ; that is worse (hunger when equal)
        fop     FCOMP, s_eat
        cmp     #1
        beq     @thirst
        jsr     puts
        .byte "HUNGER ",0
        fld     s_eat
        jsr     summary_gauge
        jmp     @restore
@thirst:
        jsr     puts
        .byte "THIRST ",0
        fld     s_drink
        jsr     summary_gauge
@restore:
        jsr     field_flush
        lda     summary_vector
        sta     $36
        lda     summary_vector+1
        sta     $37
        rts

; summary_hint -- field 1: a pending transition alert, else the thermal
; danger, immersion or wet clothes, the shelter, the items at hand, a
; caution, the recoverable items, or a rest / help hint. Clobbers A, X, Y.
summary_hint:
        lda     #UI_HINT
        sta     summary_ink
        lda     ui_pending
        beq     @thermal
        cmp     #7
        bcs     :+
        inc     summary_inverse
:
        cmp     #6
        bne     @alert_table
@ill:   lda     ui_previous+5
        bne     :+
        lda     #14             ; condition cleared before pending alert shown
        bne     @alert_table
:
        inc     summary_inverse
        and     #1
        beq     @starvation
        jsr     puts
        .byte "DEHYDRATION",0
        jmp     @alert_done
@starvation:
        lda     ui_previous+5
        and     #2
        beq     @exhaustion
        jsr     puts
        .byte "STARVATION",0
        jmp     @alert_done
@exhaustion:
        jsr     puts
        .byte "EXHAUSTION",0
        jmp     @alert_done
@alert_table:
        tax
        cpx     #9
        bcc     :+
        lda     #0              ; recoveries remain plain text, in green
        sta     summary_inverse
        lda     #UI_GOOD
        sta     summary_ink
:
        lda     summary_alert_lo-1,x
        clc
        adc     #<ui_hunger_worse
        pha
        lda     #>ui_hunger_worse
        adc     #0
        tax
        pla
        jsr     print_str_ax
@alert_done:
        lda     #0
        sta     ui_pending
        rts
@thermal:
        lda     ui_previous+5
        bne     @ill
@body:
        lda     ui_previous+3
        beq     @wet
        inc     summary_inverse
        cmp     #1
        bne     @hot
        jsr     puts
        .byte "HYPOTHERMIA",0
        rts
@hot:   jsr     puts
        .byte "HYPERTHERMIA",0
        rts
@wet:   lda     wet_mode
        beq     @shelter
        inc     summary_inverse
        cmp     #2
        bne     @damp
        jsr     puts
        .byte "IMMERSED",0
        rts
@damp:  jsr     puts
        .byte "WET CLOTHES",0
        rts
@shelter:
        lda     tree_in
        beq     :+
        jsr     puts
        .byte "CLIMB DOWN",0
        rts
:
        lda     shelter_inside
        beq     @cabin
        jsr     puts
        .byte "EXIT SHELTER",0
        rts
@cabin: lda     MAP+16
        beq     @items
        lda     px+1
        cmp     MAP+17
        bne     @items
        lda     py+1
        cmp     MAP+18
        bne     @items
        jsr     puts
        .byte "ENTER SHELTER",0
        rts
@items:
        lda     it_place+21
        cmp     #5
        bne     @wildlife
        ldx     #21
        jsr     at_ground
        bcc     @wildlife
        jsr     puts
        .byte "LOWER FOOD",0
        rts
@wildlife:  lda     animal_kind
        beq     @temperature
        lda     animal_x
        cmp     px+1
        bne     @temperature
        lda     animal_y
        cmp     py+1
        bne     @temperature
        inc     summary_inverse
        lda     animal_kind
        cmp     summary_quiet
        bne     :+
        jsr     puts
        .byte "IGNORE/MOVE",0
        rts
:       jsr     puts
        .byte "SCARE/IGNORE",0
        rts
@temperature:
        lda     #UI_FAIR        ; cautions
        sta     summary_ink
        lda     thermal_mode
        beq     @water_stock
        cmp     #1
        bne     @shiver
        jsr     puts
        .byte "SWEATING",0
        rts
@shiver: jsr    puts
        .byte "SHIVERING",0
        rts
@water_stock:
        lda     it_pack_hi+N_WATER
        bne     @scan
        lda     it_pack_lo+N_WATER
        cmp     #17
        bcs     @scan
        jsr     puts
        .byte "WATER LOW:INV",0
        rts
@scan:  lda     #UI_HINT
        sta     summary_ink
        ldx     #75
@item:  lda     it_place,x
        cmp     #255
        beq     @next
        jsr     at_ground
        bcc     @next
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        bne     @found
        beq     @next           ; exhausted ground provisions are not objects
@gear:
        lda     it_place,x
        beq     @found
@next:  dex
        bne     @item
        ldy     #2              ; lot 3: the BOW, the SPEAR, the SPLINT on
@craft: ldx     summary_cr,y    ; this cell's ground (not the ROCK: it lies
        lda     cr_b1,x         ; on every land cell)
        bne     @crn
        lda     cr_cx,y
        cmp     px+1
        bne     @crn
        lda     cr_cy,y
        cmp     py+1
        beq     @found
@crn:   dey
        bpl     @craft
        lda     cr_b1+2         ; the CLUB, until the player leaves the cell
        bne     @normal
        lda     cr_still
        beq     @normal
@found: jsr     puts
        .byte "ITEMS: INV",0
        rts
@normal:
        lda     #UI_CALM
        sta     summary_ink
        lda     night
        beq     @map_hint
        jsr     puts
        .byte "REST / HELP",0
        rts
@map_hint:
        jsr     puts
        .byte "TOPO / HELP",0
        rts
summary_gauge:
        fop     FCOMP, f_12
        cmp     #1
        beq     @very
        fop     FCOMP, f_6
        cmp     #1
        beq     @some
        lda     #UI_GOOD
        sta     summary_ink
        jsr     puts
        .byte "OKAY",0
        rts
@some:  lda     #UI_FAIR
        sta     summary_ink
        jsr     puts
        .byte "SO-SO",0
        rts
@very:  inc     summary_inverse
        jsr     puts
        .byte "VERY",0
        rts

; COUT hook, preserving the string/numeric printers' A/X/Y registers: the
; character joins the field buffer with its glyph, width and colours.
summary_output:
        pha
        txa
        pha
        tya
        pha
        tsx
        lda     $0103,x
        and     #127
        sec
        sbc     #32
        cmp     #59
        bcc     :+
        lda     #0
:       ldy     summary_n
        cpy     #UI_CHARS
        bcs     @done
        sta     summary_char    ; glyph = font + 7 * code
        lda     #0
        sta     summary_bits
        lda     summary_char
        asl     a
        rol     summary_bits
        asl     a
        rol     summary_bits
        asl     a
        rol     summary_bits
        sec
        sbc     summary_char
        bcs     :+
        dec     summary_bits
:       clc
        adc     #<summary_font
        sta     f_lo,y
        sta     gp1
        lda     summary_bits
        adc     #>summary_font
        sta     f_hi,y
        sta     gp1+1
        ldx     #0
        lda     (gp1,x)
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     f_w,y
        lda     summary_ink
        ldx     summary_inverse ; 0 = UI_BLACK
        beq     :+
        lda     #UI_WHITE
        ldx     #UI_WARN
:       sta     f_ink,y
        txa
        sta     f_bg,y
        inc     summary_n
@done:  pla
        tay
        pla
        tax
        pla
        rts

; field_next -- draw the current field, then move to the next one.
field_next:
        jsr     field_flush
        inc     summary_field
        lda     #0
        sta     summary_inverse
        lda     #UI_LABEL
        sta     summary_ink
        rts

; field_flush -- the buffered characters, rows 8f..8f+7 of the field's panel
; (f = field & 1; panel = field >> 1), black where nothing is written.
field_flush:
        lda     #0
        sta     summary_row
@row:   lda     summary_field
        and     #1
        asl     a
        asl     a
        asl     a
        adc     summary_row
        tax
        jsr     hgr_row2
        ldy     #48
        lda     #UI_BLACK
:       sta     line_pix,y
        dey
        bpl     :-
        lda     #0
        sta     summary_i
        lda     summary_field   ; right panel: UI_GAP pixels after the ribbon
        and     #2
        beq     :+
        lda     #UI_GAP
:       sta     summary_x
@char:  ldy     summary_i
        cpy     summary_n
        bcs     @pack
        lda     f_bg,y          ; warning strip: the cell, gaps included
        beq     @glyph
        ldx     summary_x
        beq     :+
        dex
:       ldy     summary_i
        lda     summary_x
        sec
        adc     f_w,y           ; last pixel = x + width
        sta     summary_end
        lda     f_bg,y
:       cpx     #49
        bcs     @glyph
        sta     line_pix,x
        inx
        cpx     summary_end
        bcc     :-
@glyph: ldy     summary_i
        lda     summary_row
        cmp     #7
        bcs     @advance        ; row 7: background only
        lda     f_lo,y
        sta     gp1
        lda     f_hi,y
        sta     gp1+1
        ldy     summary_row
        lda     (gp1),y
        and     #31
        sta     summary_bits
        ldy     summary_i
        ldx     summary_x
@bit:   lsr     summary_bits
        bcc     :+
        cpx     #49
        bcs     :+
        lda     f_ink,y
        sta     line_pix,x
:       inx
        lda     summary_bits
        bne     @bit
@advance:
        ldy     summary_i
        lda     summary_x
        sec
        adc     f_w,y
        sta     summary_x
        inc     summary_i
        jmp     @char
@pack:  lda     summary_field   ; groups 0..6 or 13..19
        and     #2
        beq     :+
        lda     #26
:       tax
        ldy     #0
:       jsr     dhgr_pack
        inx
        inx
        tya
        clc
        adc     #7
        tay
        cpy     #49
        bcc     :-
        inc     summary_row
        lda     summary_row
        cmp     #8
        bcs     :+
        jmp     @row
:       lda     #0
        sta     summary_n
        rts

summary_vector: .word 0
summary_field: .byte 0
summary_n: .byte 0
summary_ink: .byte 0
summary_x: .byte 0
summary_i: .byte 0
summary_end: .byte 0
summary_bits: .byte 0
summary_hour: .byte 0
summary_minute: .byte 0
summary_char: .byte 0
summary_row: .byte 0
summary_inverse: .byte 0
summary_periods: .byte "NIGHTDAWN AM   PM   DUSK "
; the alerts, as offsets from ui_hunger_worse
summary_alert_lo: .byte 0,ui_thirst_worse-ui_hunger_worse,ui_health_worse-ui_hunger_worse,ui_body_worse-ui_hunger_worse
        .byte ui_immersed-ui_hunger_worse,ui_condition-ui_hunger_worse,ui_condition-ui_hunger_worse,ui_condition-ui_hunger_worse
        .byte ui_hunger_better-ui_hunger_worse,ui_thirst_better-ui_hunger_worse,ui_health_better-ui_hunger_worse
        .byte ui_body_better-ui_hunger_worse,ui_out_water-ui_hunger_worse,ui_recovered-ui_hunger_worse
summary_cr: .byte 0, 1, 4       ; cr_b1 of BOW, SPEAR, SPLINT (cr_cx/cr_cy 0..2)
ui_hunger_worse: .byte "HUNGER WORSE",0
ui_thirst_worse: .byte "THIRST WORSE",0
ui_health_worse: .byte "HEALTH WORSE",0
ui_body_worse: .byte "BODY WORSE",0
ui_immersed: .byte "NOW IMMERSED",0
ui_condition: .byte "NEW CONDITION",0
ui_hunger_better: .byte "HUNGER BETTER",0
ui_thirst_better: .byte "THIRST BETTER",0
ui_health_better: .byte "HEALTH BETTER",0
ui_body_better: .byte "BODY BETTER",0
ui_out_water: .byte "OUT OF WATER",0
ui_recovered: .byte "ILL IMPROVED",0
        .include "summary_font.inc"

.segment "SUMMARY"
; Kind (6..9) of the species that noise cannot drive away (header byte 14
; >= 27: the Sierra rattlesnake), 0 if none: its hint is IGNORE/MOVE.
; Rewritten by the region pack (tools/build_disk.py).
summary_quiet: .byte 8
.export summary_quiet
