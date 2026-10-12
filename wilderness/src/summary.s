; Four short monochrome fields around the compass, outside the command area.
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
        lda     #0
        sta     summary_inverse
        ; Clear only the side panels, never the compass or command/results.
        ldx     #15
@clear: lda     hgr_lo,x
        sta     hp
        lda     hgr_hi,x
        sta     hp+1
        ldy     #39
        lda     #0
@byte:  cpy     #13
        bcc     @store
        cpy     #27
        bcc     @skip
@store: sta     (hp),y
@skip:  dey
        bpl     @byte
        dex
        bpl     @clear
        lda     $36
        sta     summary_vector
        lda     $37
        sta     summary_vector+1
        lda     #<summary_output
        sta     $36
        lda     #>summary_output
        sta     $37
        lda     #0
        sta     summary_y
        sta     summary_col
        lda     #13
        sta     summary_limit
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
        inc     summary_inverse ; poor health stays visible after its first alert
:
        jsr     pdec
        jsr     puts
        .byte "%",0
        lda     #0
        sta     summary_inverse
        lda     #8
        sta     summary_y
        lda     #0
        sta     summary_col
        jsr     puts
        .byte "HUNGER ",0
        fld     s_eat
        jsr     summary_gauge
        lda     #0
        sta     summary_inverse
        sta     summary_y
        lda     #27
        sta     summary_col
        lda     #40
        sta     summary_limit
        jsr     puts
        .byte "THIRST ",0
        fld     s_drink
        jsr     summary_gauge
        lda     #0
        sta     summary_inverse
        lda     #8
        sta     summary_y
        lda     #27
        sta     summary_col
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
        lda     #0              ; recoveries remain plain text
        sta     summary_inverse
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
        inc     summary_inverse
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
        inc     summary_inverse
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
        inc     summary_inverse
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
        jsr     puts
        .byte "OKAY",0
        rts
@some:  jsr     puts
        .byte "SO-SO",0
        rts
@very:  inc     summary_inverse
        jsr     puts
        .byte "VERY",0
        rts

; COUT hook, preserving the string/numeric printers' A/X/Y registers.
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
:       sta     summary_char
        ; gp1 = font + char * 7, preserving gp2 (puts' string pointer).
        lda     #0
        sta     gp1
        sta     gp1+1
        ldx     #7
@mul:   clc
        lda     gp1
        adc     summary_char
        sta     gp1
        lda     gp1+1
        adc     #0
        sta     gp1+1
        dex
        bne     @mul
        clc
        lda     gp1
        adc     #<summary_font
        sta     gp1
        lda     gp1+1
        adc     #>summary_font
        sta     gp1+1
        lda     summary_col
        cmp     summary_limit
        bcs     @done
        lda     #0
        sta     summary_row
@row:   clc
        lda     summary_row
        adc     summary_y
        tax
        lda     hgr_lo,x
        sta     hp
        lda     hgr_hi,x
        sta     hp+1
        ldy     summary_row
        lda     (gp1),y
        ldy     summary_inverse
        beq     :+
        eor     #127            ; black letters on a solid white warning strip
:
        ldy     summary_col
        sta     (hp),y
        inc     summary_row
        lda     summary_row
        cmp     #7
        bcc     @row
        inc     summary_col
@done:  pla
        tay
        pla
        tax
        pla
        rts
summary_vector: .word 0
summary_y: .byte 0
summary_col: .byte 0
summary_limit: .byte 0
summary_hour: .byte 0
summary_minute: .byte 0
summary_char: .byte 0
summary_row: .byte 0
summary_inverse: .byte 0
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
