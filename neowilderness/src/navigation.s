; VERHILLE Arnaud — GPL-3.0. XL player-visible route planning.
.segment "NAVIGATION"
navigation_site:
        lda     #1
        sta     ui_dirty
        lda     verb
        cmp     #V_ENTER
        beq     @enter
        cmp     #V_EXIT
        beq     @exit
        lda     #<site_leave
        ldx     #>site_leave
        jmp     message
@enter: lda     noun
        cmp     #137             ; SHELTER (found); HUT, IGLOO, TRENCH, TENT: lot 3
        jne     @crafted
        lda     tree_in
        beq     :+
        jmp     do_tree          ; tail-call resident loader before replacing SITES
:
        lda     shelter_inside
        bne     @already
        lda     MAP+16
        beq     @absent
        lda     px+1
        cmp     MAP+17
        bne     @absent
        lda     py+1
        cmp     MAP+18
        bne     @absent
        lda     MAP+37
        beq     :+
        lda     px
        cmp     MAP+34
        bne     @absent
        lda     py
        cmp     MAP+35
        bne     @absent
        ; The animal stays (D4, docs/CRAFT.md 3.4): risk x .1 inside,
        ; ATTACK and SCARE allowed; the shelter shows no view.
:       lda     #1
        sta     shelter_inside
        jmp     show_view
@exit:  lda     noun
        cmp     #137
        jne     @crafted
        lda     shelter_inside
        beq     @outside
        lda     #0
        sta     shelter_inside
        sta     scene_minutes
        lda     night
        bne     @exit_view       ; dark view supplies its own single message
        lda     #<site_outside
        ldx     #>site_outside
        jsr     message
@exit_view:
        jmp     show_view
@specific:
        lda     #<site_specific
        ldx     #>site_specific
        jmp     message
@absent:
        lda     #<site_absent
        ldx     #>site_absent
        jmp     message
@already:
        lda     #<site_already
        ldx     #>site_already
        jmp     message
@outside:
        lda     #<site_outside
        ldx     #>site_outside
        jmp     message

; ENTER, EXIT of the HUT, IGLOO, TRENCH (lot 3, docs/CRAFT.md; T12/S08 as
; probed): absent msg 1; ENTER inside msg 11, else in (msg 10, the IGLOO
; 35 F, health steps of 15 minutes); EXIT outside msg 11, else out (msg 10).
; The TENT alike, present here or carried.
@crafted:
        ldx     noun
        cpx     #9
        beq     :+
        cpx     #95
        bcc     @specific
        cpx     #98
        bcs     @specific
        txa
        sec
        sbc     #95
        tay
        lda     cr_sx,y
        cmp     px+1
        bne     @gone
        lda     cr_sy,y
        cmp     py+1
        bne     @gone
        beq     @here
:       jsr     have
        bcc     @gone
@here:  lda     verb
        cmp     #V_ENTER
        bne     @out
        lda     tree_in
        beq     :+
        jmp     do_tree
:       lda     shelter_inside
        bne     @have
        ldx     #1
        lda     noun
        cmp     #96             ; IGLOO
        bne     :+
        inx
:       stx     shelter_inside
        lda     #15
        sta     health_period
        bne     @ok
@out:   lda     shelter_inside
        beq     @have
        lda     #0
        sta     shelter_inside
        sta     scene_minutes
@ok:    lda     #<m_ok
        ldx     #>m_ok
        jsr     message
        jmp     show_view
@have:  lda     #<c_m11
        ldx     #>c_m11
        jmp     message
@gone:  lda     #<c_m1
        ldx     #>c_m1
        jmp     message


; Cursor coordinates are deliberately chosen by the player on the displayed
; map. No pathfinding, hazard queries or hidden resource lookup takes place.
module_navigation:
        lda     #0
        sta     nav_frame_valid
        lda     route_active
        beq     @new
        lda     route_x
        sta     nav_x
        lda     route_y
        sta     nav_y
        lda     #2
        sta     nav_review
        lda     #0
        sta     nav_choice
        jmp     nav_redraw
@new:   lda     px+1
        sta     nav_x
        lda     py+1
        sta     nav_y
        lda     #0
        sta     nav_review
        sta     nav_choice
        jsr     nav_bounds
        jmp     nav_menu

; Every destination is available through the game port. The typed C/H/R
; shortcuts remain conveniences when moving the map cursor.
nav_menu:
        lda     #0
        sta     nav_frame_valid ; chooser labels replace terrain in rows 3..9
        jsr     nav_window
        jsr     topo_draw
        lda     #1
        jsr     nav_at
        jsr     puts
        .byte "PLAN A DIRECTION - SELECT DESTINATION",0
        jsr     topo_pad
        lda     #0
        jsr     nav_menu_item
        jsr     puts
        .byte "CURSOR: CHOOSE A MAP POINT",0
        jsr     topo_pad
        lda     #1
        jsr     nav_menu_item
        jsr     puts
        .byte "RANGERS",0
        jsr     topo_pad
        lda     #2
        jsr     nav_menu_item
        jsr     puts
        .byte "CRASH SITE",0
        jsr     topo_pad
        lda     MAP+16
        beq     :+
        lda     #3
        jsr     nav_menu_item
        jsr     puts
        .byte "CABIN",0
        jsr     topo_pad
:       lda     #$FF
        sta     INVFLG
        lda     #23
        jsr     nav_at
        jsr     puts
        .byte "ARROWS CHOOSE  RETURN MAP TARGET  ESC BACK",0
        jsr     topo_pad
        jsr     text_release
        jsr     show_text
nav_menu_key:
        jsr     wait_key
        cmp     #KC_ESC
        jeq     topo_redraw
        cmp     #KC_RET
        beq     @take
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_DOWN
        beq     @next
        cmp     #KC_RIGHT
        bne     nav_menu_key
@next:  inc     nav_choice
        lda     #3
        ldx     MAP+16
        beq     :+
        lda     #4
:       cmp     nav_choice
        bne     @draw
        lda     #0
        sta     nav_choice
        beq     @draw
@previous:
        dec     nav_choice
        bpl     @draw
        lda     #2
        ldx     MAP+16
        beq     :+
        lda     #3
:       sta     nav_choice
@draw:  jmp     nav_menu
@take:  lda     nav_choice
        beq     @cursor
        cmp     #1
        bne     :+
        lda     M_GOALX
        sta     nav_x
        lda     M_GOALY
        jmp     nav_landmark
:       cmp     #2
        bne     :+
        lda     M_STARTX+1
        sta     nav_x
        lda     M_STARTY+1
        jmp     nav_landmark
:       lda     MAP+17
        sta     nav_x
        lda     MAP+18
        jmp     nav_landmark
@cursor:
        jmp     nav_redraw
nav_menu_item:
        sta     nav_option
        asl     a
        clc
        adc     #3
        jsr     nav_at
        lda     #$FF
        ldx     nav_option
        cpx     nav_choice
        bne     :+
        lda     #$3F
:       sta     INVFLG
        rts

; Position without vtab's differential padding: moving from the summary
; to the footer must never erase the terrain between them.
nav_at:
        sta     CV
        jsr     t_vtab
        lda     #0
        sta     CH
        rts
nav_redraw:
        jsr     nav_window
        lda     nav_frame_valid
        beq     @full
        lda     topo_x
        cmp     nav_frame_x
        bne     @full
        lda     topo_y
        cmp     nav_frame_y
        bne     @full
        jsr     text_begin
        lda     nav_frame_target_x
        ldx     nav_frame_target_y
        jsr     topo_put_cell   ; erase the prior marker with native terrain/site
        jmp     @marker
@full:
        jsr     topo_draw
@marker:
        lda     topo_x
        sta     nav_frame_x
        lda     topo_y
        sta     nav_frame_y
        lda     nav_x
        sta     nav_frame_target_x
        lda     nav_y
        sta     nav_frame_target_y
        lda     #1
        sta     nav_frame_valid
        lda     nav_x
        ldx     nav_y
        jsr     topo_at
        lda     #'+'|$80
        jsr     topo_put2
        jsr     nav_measure
        lda     #1
        jsr     nav_at
        jsr     puts
        .byte "TARGET ",0
        jsr     nav_target_name
        lda     nav_x
        jsr     pdec
        lda     #','|$80
        jsr     COUT
        lda     nav_y
        jsr     pdec
        jsr     puts
        .byte "  ",0
        lda     nav_tenths
        sta     num
        lda     nav_tenths+1
        sta     num+1
        jsr     nav_distance_print
        jsr     puts
        .byte " CELLS  ",0
        lda     nav_same
        beq     :+
        jsr     puts
        .byte "HERE - MOVE TARGET",0
        jmp     @no_magnetic
:
        lda     nav_true
        sta     num
        lda     nav_true+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " DEG TRUE",0
        ldx     #53
        jsr     have
        bcc     @no_magnetic
        jsr     puts
        .byte " / ",0
        lda     nav_mag
        sta     num
        lda     nav_mag+1
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte " MAG",0
@no_magnetic:
        jsr     topo_pad
        lda     #23
        jsr     nav_at
        lda     nav_review
        cmp     #2
        beq     @follow
        cmp     #0
        beq     @choose
        jsr     puts
        .byte "RETURN TAKE CAP (NO TRAVEL)  ESC CHANGE TARGET",0
        jmp     @ready
@follow:
        jsr     nav_follow_label
        jmp     @ready
@choose:
        jsr     puts
        .byte "ARROWS TARGET  C/H/R LANDMARK  RETURN REVIEW  ESC BACK",0
@ready: jsr     topo_pad
        jsr     text_release
        jsr     show_text
nav_key:
        lda     nav_review
        cmp     #2
        jeq     nav_follow_key
        jsr     wait_key
        cmp     #KC_ESC
        bne     @enter
        lda     nav_review
        beq     @back
        lda     #0
        sta     nav_review
        jmp     nav_redraw
@back:  jmp     topo_redraw
@enter: cmp     #KC_RET
        bne     @move
        lda     nav_same
        jne     nav_key           ; no direction when standing on the target
        lda     nav_review
        bne     nav_take
        inc     nav_review
        jmp     nav_redraw
@move:  ldx     nav_review
        jne     nav_key
        cmp     #KC_LEFT
        bne     :+
        dec     nav_x
        jmp     nav_moved
:       cmp     #KC_RIGHT
        bne     :+
        inc     nav_x
        jmp     nav_moved
:       cmp     #KC_UP
        bne     :+
        inc     nav_y
        jmp     nav_moved
:       cmp     #KC_DOWN
        bne     :+
        dec     nav_y
        jmp     nav_moved
:       cmp     #'C'
        bne     :+
        lda     M_STARTX+1
        sta     nav_x
        lda     M_STARTY+1
        jmp     nav_landmark
:       cmp     #'H'
        bne     :+
        lda     MAP+16
        beq     nav_key
        lda     MAP+17
        sta     nav_x
        lda     MAP+18
        jmp     nav_landmark
:       cmp     #'R'
        jne     nav_key
        lda     M_GOALX
        sta     nav_x
        lda     M_GOALY
nav_landmark:
        sta     nav_y
nav_moved:
        jsr     nav_bounds
        jmp     nav_redraw

nav_take:
        ; dep_mask/dep_cursor are a UI union: the checklist is inactive while
        ; orientation runs. Keep the proposed target outside NAVIGATION,
        ; because native compass autoactivation calls load_totals/SIM.
        lda     nav_x
        sta     dep_mask
        lda     nav_y
        sta     dep_mask+1
        lda     #1
        sta     route_setting
        sta     dep_cursor       ; third union byte: active marker for commit
        ; A compass uses the magnetic bearing. Native watch/shadow estimates
        ; use geographic north; their ordinary visibility/time rules remain.
        lda     nav_true
        sta     orient_deg
        lda     nav_true+1
        sta     orient_deg+1
        lda     orient_aid
        and     #6
        bne     @apply
        lda     nav_mag
        sta     orient_deg
        lda     nav_mag+1
        sta     orient_deg+1
@apply: lda     #0
        sta     topo_cue_end
        jsr     back_to_view_now
        lda     #V_LOOK
        sta     verb
        lda     #ORIENT_MODULE
        jsr     overlay_load       ; replaces SITES, never this SIM-window code
        jmp     module_orient_target

nav_target_name:
        lda     nav_x
        cmp     M_GOALX
        bne     @crash
        lda     nav_y
        cmp     M_GOALY
        bne     @crash
        jsr     puts
        .byte "RANGERS ",0
        rts
@crash: lda     nav_x
        cmp     M_STARTX+1
        bne     @cabin
        lda     nav_y
        cmp     M_STARTY+1
        bne     @cabin
        jsr     puts
        .byte "CRASH SITE ",0
        rts
@cabin: lda     MAP+16
        beq     @point
        lda     nav_x
        cmp     MAP+17
        bne     @point
        lda     nav_y
        cmp     MAP+18
        bne     @point
        jsr     puts
        .byte "CABIN ",0
@point: rts

 ; Followed destination survives replacement of the navigation overlay.
; Reviewing or abandoning it is UI only; resuming uses native orientation.
nav_follow_label:
        lda     nav_choice
        beq     @resume
        cmp     #1
        beq     @change
        jsr     puts
        .byte "ABANDON TARGET: RETURN CONFIRM  ARROWS CHOOSE  ESC BACK",0
        rts
@change:
        jsr     puts
        .byte "CHANGE TARGET: RETURN MAP  ARROWS CHOOSE  ESC BACK",0
        rts
@resume:
        jsr     puts
        .byte "RESUME CAP: RETURN APPLY  ARROWS CHANGE/ABANDON  ESC BACK",0
        rts
nav_follow_key:
        jsr     wait_key
        cmp     #KC_ESC
        jeq     topo_redraw
        cmp     #KC_RET
        beq     @take
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_DOWN
        bne     nav_follow_key
@next:  inc     nav_choice
        lda     nav_choice
        cmp     #3
        bcc     @draw
        lda     #0
        sta     nav_choice
        beq     @draw
@previous:
        dec     nav_choice
        bpl     @draw
        lda     #2
        sta     nav_choice
@draw:  jmp     nav_redraw
@take:  lda     nav_choice
        beq     @resume
        cmp     #1
        beq     @change
        lda     #0
        sta     route_active
        sta     travel_pending
        sta     travel_next_minutes
        sta     travel_remaining
        sta     travel_remaining+1
        jmp     topo_redraw
@change:
        lda     #0
        sta     nav_review
        sta     nav_choice
        jmp     nav_menu
@resume:
        lda     nav_same
        bne     nav_follow_key
        jmp     nav_take

; Traversable two-cell boundary. This also keeps + clear of the three
; informational rows of the map even when its window is clamped.
nav_bounds:
        ldx     #1
@axis:  lda     nav_x,x
        cmp     #2
        bcs     :+
        lda     #2
:       cmp     nav_limit,x
        bcc     :+
        lda     nav_limit,x
:       sta     nav_x,x
        dex
        bpl     @axis
        rts
nav_limit: .byte GW-3, GH-3
nav_window:
        ldx     #1
@axis:  lda     nav_x,x
        sec
        sbc     nav_half,x
        bcs     :+
        lda     #0
:       cmp     topo_max,x
        bcc     :+
        lda     topo_max,x
:       sta     topo_x,x
        dex
        bpl     @axis
        rts
nav_half: .byte TOPO_W/2, TOPO_H/2

; Euclidean distance and atan2(east,north), using the exact player position
; and the selected integer map coordinate. One decimal cell precision.
nav_measure:
        lda     nav_x
        ldx     #0
        jsr     nav_delta
        fst     nav_east
        fop     FMULT, nav_east
        fst     nav_dist
        lda     nav_y
        ldx     #py-px
        jsr     nav_delta
        fst     nav_north
        fop     FMULT, nav_north
        fop     FADD, nav_dist
        jsr     FSQR
        lda     FAC
        beq     @same
        lda     #0
        beq     :+
@same:  lda     #1
:       sta     nav_same
        fop     FMULT, nav_ten
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     nav_tenths
        lda     $A0
        sta     nav_tenths+1
        fld     nav_north
        lda     FAC
        beq     @eastwest
        fop     FDIV, nav_east
        jsr     FATN
        fop     FMULT, nav_rad_deg
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     num
        lda     $A0
        sta     num+1
        lda     nav_north+1
        bpl     @wrap
        clc
        lda     num
        adc     #180
        sta     num
        lda     num+1
        adc     #0
        sta     num+1
        jmp     @wrap
@eastwest:
        lda     #90
        sta     num
        lda     #0
        sta     num+1
        lda     nav_east+1
        bpl     @wrap
        lda     #<270
        sta     num
        inc     num+1
@wrap:  jsr     nav_wrap
        lda     num
        sta     nav_true
        lda     num+1
        sta     nav_true+1
        lda     M_MAG
        ldx     #0
        cmp     #128
        bcc     :+
        dex
:       stx     g0
        sec
        lda     num
        sbc     M_MAG
        sta     num
        lda     num+1
        sbc     g0
        sta     num+1
        jsr     nav_wrap
        lda     num
        sta     nav_mag
        lda     num+1
        sta     nav_mag+1
        rts
nav_delta:
        sta     g0
        sec
        lda     #0
        sbc     px,x
        tay
        lda     g0
        sbc     px+1,x
        jsr     GIVAYF
        fop     FMULT, nav_inv256
        rts
nav_wrap:
        lda     num+1
        bpl     @high
        clc
        lda     num
        adc     #<360
        sta     num
        lda     num+1
        adc     #>360
        sta     num+1
@high:  lda     num
        cmp     #<360
        lda     num+1
        sbc     #>360
        bcc     @done
        sta     num+1
        lda     num
        sbc     #<360
        sta     num
@done:  rts
nav_distance_print:
        ldx     #0
        stx     nav_remainder
@divide:
        lda     num
        cmp     #10
        lda     num+1
        sbc     #0
        bcc     @fraction
        sta     num+1
        lda     num
        sbc     #10
        sta     num
        inc     nav_remainder
        bne     @divide
@fraction:
        lda     num
        pha
        lda     nav_remainder
        sta     num
        lda     #0
        sta     num+1
        jsr     print_u16
        lda     #'.'|$80
        jsr     COUT
        pla
        ora     #'0'|$80
        jmp     COUT
nav_x: .byte 0
nav_y: .byte 0
nav_review: .byte 0
nav_choice: .byte 0
nav_option: .byte 0
nav_same: .byte 0
nav_true: .word 0
nav_mag: .word 0
nav_tenths: .word 0
nav_remainder: .byte 0
nav_frame_valid: .byte 0
nav_frame_x: .byte 0
nav_frame_y: .byte 0
nav_frame_target_x: .byte 0
nav_frame_target_y: .byte 0
nav_east: .res 5
nav_north: .res 5
nav_dist: .res 5
nav_inv256: .byte $79,0,0,0,0
nav_ten: .byte $84,$20,0,0,0
nav_rad_deg: .byte $86,$65,$2F,$1A,$A0
.export nav_x, nav_y, nav_true, nav_mag, nav_tenths, nav_key
