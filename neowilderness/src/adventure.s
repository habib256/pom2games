.segment "ADVENTURE"
module_game_init:
        lda     #0
        sta     travel_pending
        sta     route_active
        sta     route_setting
        sta     threat_context
        sta     threat_seen
        sta     route_context
        sta     camp_pending
        sta     dep_running
        jsr     module_view_init
        lda     px+1
        sta     cachex
        lda     py+1
        sta     cachey
        ldx     #75
@ground:
        lda     cachex
        sta     it_x,x
        lda     cachey
        sta     it_y,x
        dex
        bne     @ground
        jsr     load_totals
        jsr     module_native_clothes_init
        jsr     module_dist_goal       ; D0 = distance to the outpost at the start
        fst     s_d0
        jmp     game_init_environment

.segment "ENVIRON"
game_init_restore:
        lda     MAP+28          ; optional native saved startup temperatures
        beq     :+
        lda     MAP+29
        sta     airtemp
        lda     MAP+30
        sta     felt_temp
        lda     #0
        sta     felt_temp+1
        lda     MAP+31
        sta     wind
:
        jmp     game_init_hud


.segment "ADVENTURE"
module_dist_goal:
        lda     M_GOALX
        jsr     @delta
        fst     t1
        fop     FMULT, t1
        fst     t1
        lda     M_GOALY
        ldx     #py-px
        jsr     @delta2
        fst     t2
        fop     FMULT, t2
        fop     FADD, t1
        jmp     FSQR
@delta: ldx     #0
@delta2:                        ; exact signed 8.8 difference, including fractions
        sta     g0
        sec
        lda     #0
        sbc     px,x
        sta     num
        lda     g0
        sbc     px+1,x
        ldy     num
        jsr     GIVAYF
        fop     FMULT, adv_inv128
        rts
.segment "ADVENTURE"
module_goal_pct:
        fld     s_elap
        lda     FAC
        bne     :+
        lda     #100
        rts
:       jsr     module_dist_goal
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



; Straight-line route completion, independent of the native efficiency score.
.segment "ADVENTURE"
; T0D/S00 materializes discoveries after both encounter scans. Header scratch
; retains quantities and quality rolls for the six wild foods (INSECTS through
; WILD NUTS, item 23: message 155); small game/fish are sightings and shelters
; need no quantity draw. Draws (docs/FORAGE.md section 4, measured on the
; ROM): one for the quantity, one for the quality, and for FRUIT a third one
; when .2 <= quality < .5 (ripe or green). In ITEMS since lot 4 (the piles
; stored by forage_found, src/forage.s; docs/MEMORY.md 16).
.segment "ITEMS"
module_resource_results:
        jsr     forage_found_begin      ; lot 4: game, fish present
        lda     #2
        sta     adv_resource_index
@next: ldx     adv_resource_index
        lda     adv_resource_bits,x
        and     MAP+36
        jeq     @none
        jsr     weather_random
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC             ; INT(32 * RND) + 4 ounces
        jsr     AYINT
        ldx     adv_resource_index
        lda     $A1
        clc
        adc     #4
        sta     MAP+26,x
        jsr     weather_random  ; quality (NUTS too: r < .1 toxic)
        fst     adv_resource_roll
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC
        inc     FAC
        jsr     AYINT
        ldx     adv_resource_index
        lda     $A1
        sta     adv_resource_sample        ; retained quality roll; consumption is separate
        cpx     #6              ; native leafy plants classify the same RND
        bne     @other
        ldy     #0
@leaf: sty     adv_resource_quality
        lda     adv_leaf_prob_lo,y
        sta     @compare+1
        lda     adv_leaf_prob_hi,y
        sta     @compare+3
        fld     adv_resource_roll
@compare:
        fop     FCOMP, adv_leaf_p1
        cmp     #$FF
        beq     @leaf_done
        ldy     adv_resource_quality
        iny
        cpy     #4
        bne     @leaf
        sty     adv_resource_quality
@leaf_done:
        ldy     adv_resource_quality
        lda     adv_leaf_method,y
        sta     MAP+38
        lda     adv_leaf_kcal,y
        sta     MAP+39
        jmp     @skip
@other:
        cpx     #3              ; FRUIT: a third roll when .2 <= r < .5
        bne     @skip
        fld     adv_resource_roll
        fop     FCOMP, adv_leaf_p2      ; .2
        cmp     #$FF
        beq     @skip           ; r < .2: poisonous, no more
        fld     adv_resource_roll
        fop     FCOMP, f_half
        cmp     #$FF
        bne     @skip           ; r >= .5: safe, no more
        jsr     weather_random  ; white or red, ripe or green
@skip: jsr     forage_found    ; lot 4: the pile, its record and counter
@none: inc     adv_resource_index
        lda     adv_resource_index
        cmp     #8
        jne     @next
        rts
adv_resource_bits: .byte 1,2,4,8,16,32,64,128
adv_resource_index: .byte 0
adv_resource_quality: .byte 0
.segment "ENVIRON"
adv_resource_sample: .byte 0
.segment "ITEMS"
adv_resource_roll: .res 5
adv_leaf_p1: .byte $7D,$4C,$CC,$CC,$CD
adv_leaf_p2: .byte $7E,$4C,$CC,$CC,$CD
adv_leaf_p3: .byte $7F,$19,$99,$99,$9A
adv_leaf_prob_lo: .byte <adv_leaf_p1,<adv_leaf_p2,<adv_leaf_p3,<f_half
adv_leaf_prob_hi: .byte >adv_leaf_p1,>adv_leaf_p2,>adv_leaf_p3,>f_half
adv_leaf_method: .byte 8,7,2,1,0
adv_leaf_kcal: .byte 60,40,80,80,0
.segment "ADVENTURE"

; Sierra retains rounded per-part losses. Removing a layer inverts the
; previous rounded combination, so reconstructing the wardrobe from bare
; skin after every action loses the original history.
module_native_clothes_init:
        lda     MAP+37
        beq     @done
        ldx     #23
@copy: lda     adv_clothes_initial,x
        sta     MAP+40,x
        dex
        bpl     @copy
        lda     #$7E
        sta     clothing_cache
        lda     #$10
        sta     clothing_cache+1
        lda     #0
        sta     clothing_cache+2
@done: rts
.segment "ADVENTURE"
adv_clothes_initial: .word 500,42,46,97,70,54,2000,74,76,148,104,77
.segment "ADVENTURE"

module_native_clothes_update:
        ldx     #2
@cache: lda     clothing_cache,x
        sta     t5,x
        lda     g0,x
        sta     clothing_cache,x
        dex
        bpl     @cache
        lda     #2
        sta     adv_clothes_item
@item: lda     adv_clothes_item
        sec
        sbc     #2
        pha
        and     #7
        tax
        lda     forest_masks,x
        sta     adv_clothes_bit
        pla
        lsr
        lsr
        lsr
        tax
        lda     t5,x
        eor     clothing_cache,x
        and     adv_clothes_bit
        jeq     @next
        lda     clothing_cache,x
        and     adv_clothes_bit
        sta     adv_clothes_add
        lda     #0
        sta     adv_clothes_wet
@mode: ldx     adv_clothes_item
        ldy     th_loss_lo-2,x
        lda     th_loss_hi-2,x
        ldx     adv_clothes_wet
        beq     :+
        ldx     adv_clothes_item
        ldy     th_wet_lo-2,x
        lda     th_wet_hi-2,x
:       jsr     GIVAYF
        fst     t1
        lda     FAC
        jeq     @next
        ldx     adv_clothes_item
        lda     it_kcal,x
        asl
        clc
        adc     adv_clothes_wet
        tax
        stx     adv_clothes_part
        ldy     MAP+38,x        ; part 2 maps to dry torso at MAP+42
        lda     MAP+39,x
        jsr     GIVAYF
        fst     t2
        lda     adv_clothes_add
        beq     @remove
        fop     FADD, t1
        jmp     @combine
@remove:
        fop     FSUB, t1        ; garment - previous loss
@combine:
        fst     t3
        fld     t1
        fop     FMULT, t2
        fst     t2
        fld     t3
        fop     FDIV, t2
        fop     FADD, f_half
        jsr     AYINT
        ldx     adv_clothes_part
        lda     $A1
        sta     MAP+38,x
        lda     $A0
        sta     MAP+39,x
        lda     adv_clothes_wet
        bne     @next
        lda     #12
        sta     adv_clothes_wet
        jmp     @mode
@next: inc     adv_clothes_item
        lda     adv_clothes_item
        cmp     #21
        jcc     @item
        rts
adv_clothes_item: .byte 0
adv_clothes_bit: .byte 0
adv_clothes_add: .byte 0
adv_clothes_wet: .byte 0
adv_clothes_part: .byte 0

module_progress:
        jsr     module_dist_goal
        fop     FMULT, adv_half
        fst     adv_distance
        fop     FADD, adv_ceil
        jsr     AYINT
        lda     $A1
        sta     journey_left
        lda     $A0
        sta     journey_left+1
        lda     won
        bne     @arrived
        lda     s_d0
        beq     @arrived
        fld     s_d0
        fop     FMULT, adv_half
        fop     FDIV, adv_distance ; distance / initial distance
        fop     FSUB, adv_one     ; 1 - distance / initial distance
        jsr     clamp0
        fop     FMULT, adv_100
        jsr     AYINT
        lda     $A1
        cmp     #100
        bcc     @done
        lda     #99             ; only an actual arrival completes the route
@done:  rts
@arrived:
        lda     #0
        sta     journey_left
        sta     journey_left+1
        lda     #100
        rts

; Dedicated ending stays visible until the player explicitly presses a key.
module_ending:
        jsr     text_screen
        lda     won
        jeq     @lost
        jsr     puts
        .byte "        RANGER OUTPOST REACHED",13,13
        .byte "   +-------------------------------+",13
        .byte "        YOU SURVIVED WILDERNESS",13
        .byte "   +-------------------------------+",13,13
        .byte "THE RANGERS WELCOME YOU TO SAFETY.",13,13,0
        jmp     @stats
@lost:  jsr     puts
        .byte "       LOST IN THE WILDERNESS",13,13
        .byte "YOUR JOURNEY ENDED BEFORE RESCUE.",13,13,0
@stats: jsr     puts
        .byte "JOURNEY TIME: ",0
        fld     s_elap
        fop     FMULT, adv_60
        fop     FADD, adv_half
        jsr     AYINT
        lda     $A1
        sta     num
        lda     $A0
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " MINUTES",13,"TRAVEL STEPS: ",0
        lda     journey_steps
        sta     num
        lda     journey_steps+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte 13,"TRAVEL DISTANCE: ",0
        lda     journey_halfcells+1
        lsr
        sta     num+1
        lda     journey_halfcells
        ror
        sta     num
        php
        jsr     print_u16
        plp
        bcc     :+
        jsr     puts
        .byte ".5",0
:       jsr     puts
        .byte " CELLS",13,"WILDLIFE ENCOUNTERS: ",0
        lda     journey_encounters
        sta     num
        lda     journey_encounters+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte 13,"FINAL HEALTH: ",0
        fld     f_hmax
        fop     FDIV, s_health
        fop     FMULT, adv_100
        fop     FADD, adv_half
        jsr     AYINT
        lda     $A1
        jsr     pdec
        jsr     puts
        .byte "%",13,"WATER LEFT: ",0
        lda     it_pack_lo+N_WATER
        sta     num
        lda     it_pack_hi+N_WATER
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " OZ",13,"FOOD LEFT: ",0
        lda     #0
        sta     num
        sta     num+1
        ldx     #23
@food:  lda     it_place,x
        cmp     #5
        beq     @next
        clc
        lda     num
        adc     it_pack_lo,x
        sta     num
        lda     num+1
        adc     it_pack_hi,x
        sta     num+1
@next:  inx
        cpx     #38
        bcc     @food
        jsr     print_u16
        jsr     puts
        .byte " OZ",13,0
        jsr     puts
        .byte "NATIVE JOURNEY RATING: ",0
        jsr     module_goal_pct
        jsr     pdec
        jsr     puts
        .byte "%",13,13,"        PRESS A KEY FOR THE MENU",0
ending_key:
        jsr     wait_key
        jmp     quit
adv_half: .byte $80,0,0,0,0
adv_ceil: .byte $80,$7F,$F9,$72,$47 ; .9999, ceiling at display precision
adv_one: .byte $81,0,0,0,0
adv_100: .byte $87,$48,0,0,0
adv_60: .byte $86,$70,0,0,0
adv_distance: .res 5

.segment "ADVENTURE"
adv_inv128: .byte $7A,0,0,0,0

; Startup-only work lives in ADV, leaving resident memory for transitions.
.segment "ADVENTURE"
module_view_init:
        lda     M_STARTX
        sta     px
        lda     M_STARTX+1
        sta     px+1
        lda     M_STARTY
        sta     py
        lda     M_STARTY+1
        sta     py+1
        lda     M_HEAD
        sta     heading
        lda     M_HEAD+1
        sta     heading+1
        jsr     project_init
        lda     #0              ; a level view (the loader leaves Applesoft's
        sta     tilt            ; zero page values)
        sta     STORE80ON       ; PAGE2 banks $2000-$3FFF (DHGR)
        lda     #<t_cout        ; 40-column output under DHGR (dhgr.s)
        sta     $36
        lda     #>t_cout
        sta     $37
        jsr     show_text       ; text80 = 0: the 40-column introduction stays
        lda     HIRES
        lda     LOWSCR
        lda     MIXSET
        lda     #20
        sta     WNDTOP
        ; Rows 20..23 become 80-column text (both pages): clear them while
        ; the introduction (rows 0..19, 40 columns) stays on screen.
        jsr     text_mode80
        jmp     t_home

project_init:
        rts
; Called by SIM before take_oz. Only clean, entirely carried drinking keeps
; the preserved landscape. Native consumption, hazards and HUD still run.
.segment "ADVENTURE"
module_drink_frame:
        lda     water_drinking_untreated
        bne     @done
        lda     it_place+N_WATER
        cmp     #5
        beq     @done
        lda     obj_keep
        bpl     @pack_amount
        lda     obj_side
        beq     @done
@pack_amount:
        lda     msgnum+1
        bne     @done
        lda     it_pack_hi+N_WATER
        bne     @quiet
        lda     it_pack_lo+N_WATER
        cmp     msgnum
        bcc     @done
@quiet: lda     #1
        sta     sim_quiet
@done:  ldx     #N_WATER        ; overlay_load used X for ADVENTURE's directory
        rts
