; Four short colour fields around the compass, outside the command area:
; proportional DHGR small-font text (tools/genhud.py) drawn by hud_col.
; Inks by state: plain white, gauges OKAY green / SO-SO yellow / VERY pink,
; poor health pink, warnings as black letters on an orange strip.
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
        lda     ui_enabled
        beq     @done
        lda     ui_dirty
        beq     @done
        jsr     summary_prepare
        lda     scene_asset
        beq     @done
        jmp     overlay_load
@done:  rts

.segment "SUMMARY"
module_summary:
        ; Clear only the side panels (bytes 0..15 and 24..39 of both banks,
        ; rows 0..15), never the compass (16..23) or command/results.
        php
        sei
        ldx     #15
@clear: txa
        jsr     hud_row
        ldy     #39
@byte:  lda     #0
        sta     PAGE2_AUX
        sta     (hp),y
        sta     PAGE2_MAIN
        sta     (hp),y
        dey
        cpy     #23
        bne     :+
        ldy     #15             ; skip the compass bytes 16..23
:       tya
        bpl     @byte
        dex
        bpl     @clear
        plp
        lda     $36
        sta     summary_vector
        lda     $37
        sta     summary_vector+1
        lda     #<summary_output
        sta     $36
        lda     #>summary_output
        sta     $37
        ldx     #0
        jsr     summary_field
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
        jmp     @health
@period:
        lda     #<summary_periods
        sta     gp2
        lda     #>summary_periods
        sta     gp2+1
        ldx     period
        lda     #5
        jsr     word
@health: jsr    puts
        .byte " H=",0
        fld     f_hmax
        fop     FDIV, s_health
        fop     FMULT, f_100
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        cmp     #40
        bcs     :+
        ldx     #HUD_VERY       ; poor health stays visible after its first alert
        stx     summary_ink
:
        jsr     pdec
        jsr     puts
        .byte "%",0
        ldx     #1
        jsr     summary_field
        jsr     puts
        .byte "HUNGER ",0
        fld     s_eat
        jsr     summary_gauge
        ldx     #2
        jsr     summary_field
        jsr     puts
        .byte "THIRST ",0
        fld     s_drink
        jsr     summary_gauge
        ldx     #3
        jsr     summary_field
        lda     ui_pending
        beq     @thermal
        cmp     #7
        bcs     :+
        jsr     summary_alarm
:
        cmp     #6
        bne     @alert_table
@ill:   lda     ui_previous+5
        bne     :+
        lda     #14             ; condition cleared before pending alert shown
        bne     @alert_table
:
        jsr     summary_alarm
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
        lda     #HUD_INK        ; recoveries remain plain text
        sta     summary_ink
        lda     #0
        sta     summary_paper
:
        lda     summary_alert_lo-1,x
        pha
        lda     summary_alert_hi-1,x
        tax
        pla
        jsr     print_str_ax
@alert_done:
        lda     #0
        sta     ui_pending
        jmp     @restore
@thermal:
        lda     ui_previous+5
        beq     @body
        jmp     @ill
@body:
        lda     ui_previous+3
        beq     @wet
        jsr     summary_alarm
        cmp     #1
        bne     @hot
        jsr     puts
        .byte "HYPOTHERMIA",0
        jmp     @restore
@hot:   jsr     puts
        .byte "HYPERTHERMIA",0
        jmp     @restore
@wet:   lda     wet_mode
        beq     @shelter
        jsr     summary_alarm
        cmp     #2
        bne     @damp
        jsr     puts
        .byte "IMMERSED",0
        jmp     @restore
@damp:  jsr     puts
        .byte "WET CLOTHES",0
        jmp     @restore
@shelter:
        lda     tree_in
        beq     :+
        jsr     puts
        .byte "CLIMB DOWN",0
        jmp     @restore
:
        lda     shelter_inside
        beq     @cabin
        jsr     puts
        .byte "EXIT SHELTER",0
        jmp     @restore
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
        jmp     @restore
@items:
        lda     it_place+21
        cmp     #5
        bne     @wildlife
        ldx     #21
        jsr     at_ground
        bcc     @wildlife
        jsr     puts
        .byte "LOWER FOOD",0
        jmp     @restore
@wildlife:  lda     animal_kind
        beq     @temperature
        lda     animal_x
        cmp     px+1
        bne     @temperature
        lda     animal_y
        cmp     py+1
        bne     @temperature
        jsr     summary_alarm
        lda     animal_kind
        cmp     #8
        bne     :+
        jsr     puts
        .byte "IGNORE/MOVE",0
        jmp     @restore
:       jsr     puts
        .byte "SCARE/IGNORE",0
        jmp     @restore
@temperature:
        lda     thermal_mode
        beq     @water_stock
        cmp     #1
        bne     @shiver
        jsr     puts
        .byte "SWEATING",0
        jmp     @restore
@shiver: jsr    puts
        .byte "SHIVERING",0
        jmp     @restore
@water_stock:
        lda     it_pack_hi+N_WATER
        bne     @scan
        lda     it_pack_lo+N_WATER
        cmp     #17
        bcs     @scan
        jsr     puts
        .byte "WATER LOW:INV",0
        jmp     @restore
@scan: ldx     #75
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
        jmp     @normal
@found: jsr     puts
        .byte "ITEMS: INV",0
        jmp     @restore
@normal:
        lda     night
        beq     @map_hint
        jsr     puts
        .byte "REST / HELP",0
        jmp     @restore
@map_hint:
        jsr     puts
        .byte "TOPO / HELP",0
@restore:
        lda     summary_vector
        sta     $36
        lda     summary_vector+1
        sta     $37
        rts
summary_gauge:
        fop     FCOMP, f_12
        cmp     #1
        beq     @very
        fop     FCOMP, f_6
        cmp     #1
        beq     @some
        lda     #HUD_OKAY
        sta     summary_ink
        jsr     puts
        .byte "OKAY",0
        rts
@some:  lda     #HUD_SOSO
        sta     summary_ink
        jsr     puts
        .byte "SO-SO",0
        rts
@very:  lda     #HUD_VERY
        sta     summary_ink
        jsr     puts
        .byte "VERY",0
        rts

; summary_field -- X = field 0..3 (time/health, hunger, thirst, hint): pen
; and clip limit of its line, plain style.
summary_field:
        lda     summary_tops,x
        sta     summary_y
        lda     summary_xs,x
        sta     summary_x
        lda     summary_limits,x
        sta     summary_limit
summary_plain:
        lda     #HUD_INK
        ldx     #0
        beq     summary_style
; summary_alarm -- warnings: black letters on the alarm strip. Preserves A.
summary_alarm:
        pha
        lda     #0
        ldx     #HUD_ALARM
        jsr     summary_style
        pla
        rts
summary_style:
        sta     summary_ink
        stx     summary_paper
        rts

; COUT hook, preserving the string/numeric printers' A/X/Y registers.
; Character: glyph columns of width w (space: w = 2), advance w + 1; with a
; paper, the strip covers columns x-1..x+w, rows y-1..y+5. A character
; that would pass the field limit stops the field.
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
:       asl     a
        asl     a
        sta     summary_char    ; glyph offset: four column masks
        ldx     #4
@width: dex
        bmi     @blank
        txa
        adc     summary_char    ; carry clear
        tay
        lda     summary_font,y
        beq     @width
        inx
        txa
        bne     @fits
@blank: lda     #2
@fits:  sta     summary_w
        sec
        adc     summary_x       ; x + w + 1
        cmp     summary_limit
        beq     :+
        bcc     :+
        lda     summary_limit   ; past the limit: the field stops here
        sta     summary_x
        bcs     @done
:       pha                     ; next pen position
        lda     summary_paper
        beq     @ink
        sta     hud_ink
        ldx     summary_y
        dex
        stx     hud_top
        ldx     summary_x
        dex
        txa
        jsr     hud_pen
        ldx     summary_w
        inx
        inx
@strip: stx     summary_n
        lda     #$7F
        jsr     hud_col
        jsr     hud_next
        ldx     summary_n
        dex
        bne     @strip
@ink:   lda     summary_ink
        sta     hud_ink
        lda     summary_y
        sta     hud_top
        lda     summary_x
        jsr     hud_pen
        ldx     summary_char
@glyph: stx     summary_n
        lda     summary_font,x
        jsr     hud_col
        jsr     hud_next
        ldx     summary_n
        inx
        dec     summary_w
        bne     @glyph
        pla
        sta     summary_x
@done:  pla
        tay
        pla
        tax
        pla
        rts
summary_vector: .word 0
summary_y: .byte 0
summary_x: .byte 0
summary_limit: .byte 0
summary_w: .byte 0
summary_n: .byte 0
summary_ink: .byte 0
summary_paper: .byte 0
summary_hour: .byte 0
summary_minute: .byte 0
summary_char: .byte 0
; Fields (tools/genhud.PANEL_FIELDS): top row, first column, limit.
summary_tops: .byte 2, 9, 2, 9
summary_xs: .byte 1, 1, 85, 85
summary_limits: .byte 56, 56, 140, 140
summary_periods: .byte "NIGHTDAWN AM   PM   DUSK "
summary_alert_lo: .byte <ui_hunger_worse,<ui_thirst_worse,<ui_health_worse,<ui_body_worse,<ui_immersed,<ui_condition,<ui_condition,<ui_condition,<ui_hunger_better,<ui_thirst_better,<ui_health_better,<ui_body_better,<ui_out_water,<ui_recovered
summary_alert_hi: .byte >ui_hunger_worse,>ui_thirst_worse,>ui_health_worse,>ui_body_worse,>ui_immersed,>ui_condition,>ui_condition,>ui_condition,>ui_hunger_better,>ui_thirst_better,>ui_health_better,>ui_body_better,>ui_out_water,>ui_recovered
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
