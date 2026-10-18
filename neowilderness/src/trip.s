; Small, frequently used trip dialogues, independent of the planner.
.segment "TRIPUI"
trip_choice: .byte 0
; Resident trip state is deliberately outside SAVE. Costs and raster cadence
; stay native; an indivisible step is offered explicitly when it exceeds the
; requested remainder. Merely opening this choice never advances the world.
navigation_travel_report:
        lda     msgnum
        pha
        lda     msgnum+1
        pha
        jsr     nav_trip_report
        pla
        sta     msgnum+1
        pla
        sta     msgnum
        rts
nav_trip_report:
        lda     route_active
        jeq     @left
        lda     msgnum
        sta     trip_elapsed
        lda     msgnum+1
        sta     trip_elapsed+1
        jsr     msg_begin
        jsr     trip_route_measure
        lda     #<trip_to
        ldx     #>trip_to
        jsr     trip_append
        jsr     trip_route_named
        lda     #<trip_stop
        ldx     #>trip_stop
        jsr     trip_append
        lda     trip_elapsed
        sta     msgnum
        lda     trip_elapsed+1
        sta     msgnum+1
        lda     #<trip_used
        ldx     #>trip_used
        jsr     trip_append
        lda     travel_remaining
        sta     msgnum
        lda     travel_remaining+1
        sta     msgnum+1
        lda     #<trip_left
        ldx     #>trip_left
        jsr     trip_append
        lda     travel_next_minutes
        beq     @done
        sta     msgnum
        lda     #0
        sta     msgnum+1
        lda     #<trip_next
        ldx     #>trip_next
        jmp     trip_append
@left:  lda     travel_remaining
        ora     travel_remaining+1
        beq     @done
        lda     travel_remaining
        sta     msgnum
        lda     travel_remaining+1
        sta     msgnum+1
        lda     #<nav_trip_left
        sta     gp1
        lda     #>nav_trip_left
        sta     gp1+1
        jsr     message_body
        lda     travel_next_minutes
        beq     @done
        sta     msgnum
        lda     #0
        sta     msgnum+1
        lda     #<nav_trip_step
        sta     gp1
        lda     #>nav_trip_step
        sta     gp1+1
        jsr     message_body
@done:  rts
nav_trip_left: .byte "|LEFT # MIN.",0
nav_trip_step: .byte " NEXT STEP # MIN.",0

navigation_travel_choice:
        lda     #0
        ldx     travel_pending
        bne     :+
        lda     #1
:       sta     trip_choice
@draw:  lda     trip_choice
        bne     @new
        lda     travel_remaining
        sta     msgnum
        lda     travel_remaining+1
        sta     msgnum+1
        lda     travel_next_minutes
        beq     @remaining
        sta     msgnum
        lda     #0
        sta     msgnum+1
        lda     #<nav_trip_extend
        ldx     #>nav_trip_extend
        bne     @show
@remaining:
        lda     #<nav_trip_resume
        ldx     #>nav_trip_resume
        bne     @show
@new:   cmp     #2
        beq     @abandon
        lda     #<nav_trip_new
        ldx     #>nav_trip_new
        bne     @show
@abandon:
        lda     #<nav_trip_abandon
        ldx     #>nav_trip_abandon
@show:  ldy     route_active
        beq     :+
        ldy     trip_choice
        bne     @tracked_choice
        lda     travel_next_minutes
        beq     @tracked_choice
        lda     #<trip_tracked_step
        ldx     #>trip_tracked_step
        bne     :+
@tracked_choice:
        lda     trip_tracked_lo,y
        ldx     trip_tracked_hi,y
:       jsr     message
        lda     route_active
        beq     :+
        jsr     trip_route_summary
        jmp     @terrain
@terrain:
:       lda     #<nav_trip_water
        sta     gp1
        lda     #>nav_trip_water
        sta     gp1+1
        jsr     message_body
@key:   jsr     wait_key
        cmp     #KC_ESC
        jeq     @cancel
        cmp     #KC_RET
        beq     @take
        cmp     #KC_LEFT
        beq     @toggle
        cmp     #KC_RIGHT
        beq     @toggle
        cmp     #KC_UP
        beq     @toggle
        cmp     #KC_DOWN
        bne     @key
@toggle:
        lda     trip_choice
        clc
        adc     #1
        ldx     #3
        ldy     route_active
        beq     :+
        inx
:       stx     g0
        cmp     g0
        bcc     :+
        lda     #0
:       sta     trip_choice
        jmp     @draw
@take:  lda     trip_choice
        cmp     #3
        beq     @readjust
        cmp     #2
        beq     @drop
        eor     #1              ; A=1 resume, A=0 request a new duration
        ldx     travel_pending
        bne     :+
        lda     #0              ; no remainder: resume needs a fresh duration
:       rts
@readjust:
        rts
@drop:  lda     #0
        sta     travel_pending
        sta     travel_remaining
        sta     travel_remaining+1
        sta     travel_next_minutes
@cancel:
        lda     #2
        rts
nav_trip_water: .byte "|WALK:LAND SWIM:WATER HERE/NEXT HALF",0
nav_trip_abandon: .byte "ABANDON TRIP? RETURN CONFIRM. ARROWS RESUME. ESC BACK.",0
nav_trip_resume: .byte "RESUME # MIN LEFT, SAME CAP. RETURN GO. ARROWS CHANGE/ABANDON. ESC BACK.",0
nav_trip_extend: .byte "NEXT STEP NEEDS # MIN, SAME CAP. RETURN TAKE STEP. ARROWS CHANGE/ABANDON. ESC BACK.",0
nav_trip_new: .byte "NEW TRIP? RETURN SET DURATION. ARROWS RESUME. ESC BACK.",0
.export travel_remaining, travel_pending, travel_next_minutes
.export navigation_travel_choice, navigation_travel_report

navigation_travel_resume:
        lda     travel_heading
        sta     heading
        lda     travel_heading+1
        sta     heading+1
        lda     travel_remaining
        sta     minutes
        lda     travel_remaining+1
        sta     minutes+1
        lda     travel_next_minutes
        beq     @done
        sta     minutes
        lda     #0
        sta     minutes+1
@done:  rts

navigation_travel_duration:
        lda     input_argument
        jne     @duration       ; explicit duration starts a fresh request
@approach:
        lda     route_active
        beq     @pending
        jsr     trip_route_measure
        lda     trip_dist
        bne     :+
        lda     #<trip_arrived
        ldx     #>trip_arrived
        jsr     message
        jsr     trip_route_summary
        lda     #2
        bne     @quit
:       fld     trip_dist
        fop     FCOMP, trip_two
        cmp     #1
        beq     @pending
        jsr     trip_approach_choice
        cmp     #2
        beq     @quit
        cmp     #3
        beq     @reorient
        cmp     #1
        bne     @duration
        lda     #$40
        sta     dep_running      ; consumed after native next-step cost is known
        lda     #1
        sta     minutes
        lda     #0
        sta     minutes+1
        jmp     @ready
@pending:
        lda     travel_pending
        ora     route_active
        beq     @duration
        jsr     navigation_travel_choice
        cmp     #3
        beq     @reorient
        cmp     #2
        beq     @quit
        cmp     #1
        beq     @resume
@duration:
        lda     #<m_hours
        ldx     #>m_hours
        jsr     get_duration
        bcs     @quit
        lda     msgnum
        ora     msgnum+1
        beq     @quit
        jsr     prepare_minutes
        jmp     @ready
@resume:
        jsr     navigation_travel_resume
@ready: lda     #0
        sta     travel_pending
        sta     travel_next_minutes
        clc
        rts
@quit:  sec
        rts
@reorient:
        ; Discard the return into do_walk. The resident trampoline loads
        ; NAVIGATION; its eventual RTS returns to the command dispatcher.
        pla
        pla
        jmp     navigation_route_open

; UI-only distance from the exact 8.8 player coordinate. No map lookup,
; random draw, movement preparation or simulation field is touched.
trip_route_measure:
        lda     route_x
        ldx     #0
        jsr     trip_delta
        fst     trip_dist
        fop     FMULT, trip_dist
        fst     trip_dist
        lda     route_y
        ldx     #py-px
        jsr     trip_delta
        fst     trip_axis
        fop     FMULT, trip_axis
        fop     FADD, trip_dist
        jsr     FSQR
        fst     trip_dist
        fop     FMULT, trip_ten
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     trip_tenths
        lda     $A0
        sta     trip_tenths+1
        rts
trip_delta:
        sta     g0
        sec
        lda     #0
        sbc     px,x
        tay
        lda     g0
        sbc     px+1,x
        jsr     GIVAYF
        fop     FMULT, trip_inv256
        rts
trip_route_summary:
        lda     route_active
        bne     :+
        rts
:
        jsr     trip_route_measure
        lda     #<trip_target
        ldx     #>trip_target
        jsr     trip_append
trip_route_named:
        lda     route_x
        cmp     M_GOALX
        bne     @crash
        lda     route_y
        cmp     M_GOALY
        bne     @crash
        lda     #<trip_rangers
        ldx     #>trip_rangers
        bne     @name
@crash: lda     route_x
        cmp     M_STARTX+1
        bne     @cabin
        lda     route_y
        cmp     M_STARTY+1
        bne     @cabin
        lda     #<trip_crash
        ldx     #>trip_crash
        bne     @name
@cabin: lda     MAP+16
        beq     @point
        lda     route_x
        cmp     MAP+17
        bne     @point
        lda     route_y
        cmp     MAP+18
        bne     @point
        lda     #<trip_cabin
        ldx     #>trip_cabin
        bne     @name
@point: lda     #<trip_point
        ldx     #>trip_point
@name:  jsr     trip_append
        lda     route_x
        sta     msgnum
        lda     #0
        sta     msgnum+1
        lda     #<trip_x
        ldx     #>trip_x
        jsr     trip_append
        lda     route_y
        sta     msgnum
        lda     #<trip_y
        ldx     #>trip_y
        jsr     trip_append
        lda     #0
        sta     msgnum
        sta     msgnum+1
@divide:
        lda     trip_tenths
        cmp     #10
        lda     trip_tenths+1
        sbc     #0
        bcc     @fraction
        sta     trip_tenths+1
        lda     trip_tenths
        sbc     #10
        sta     trip_tenths
        inc     msgnum
        bne     @divide
@fraction:
        lda     #<trip_whole
        ldx     #>trip_whole
        jsr     trip_append
        lda     trip_tenths
        sta     msgnum
        lda     #<trip_fraction
        ldx     #>trip_fraction
        jmp     trip_append
@done:  rts
trip_append:
        sta     gp1
        stx     gp1+1
        jmp     message_body
trip_target: .byte "|TO ",0
trip_rangers: .byte "RANGERS ",0
trip_crash: .byte "CRASH ",0
trip_cabin: .byte "CABIN ",0
trip_point: .byte "POINT ",0
trip_x: .byte "#",0
trip_y: .byte ",# ",0
trip_whole: .byte "#",0
trip_fraction: .byte ".# CELLS",0
trip_dist: .res 5
trip_axis: .res 5
trip_tenths: .word 0
trip_inv256: .byte $79,0,0,0,0
trip_ten: .byte $84,$20,0,0,0

; Near the selected point, the player can request exactly one native step.
; Its actual minutes are computed by the ordinary walking/swimming path.
; Reorientation returns to the resident dispatcher, which loads the planner.
trip_approach_choice:
        lda     #0
        sta     trip_choice
@draw:  lda     trip_choice
        beq     @step
        cmp     #1
        beq     @orient
        lda     #<trip_long
        ldx     #>trip_long
        bne     @show
@orient:
        lda     #<trip_orient
        ldx     #>trip_orient
        bne     @show
@step:  lda     #<trip_short
        ldx     #>trip_short
@show:  jsr     message
        jsr     trip_route_summary
@key:   jsr     wait_key
        cmp     #KC_ESC
        beq     @cancel
        cmp     #KC_RET
        beq     @take
        cmp     #KC_LEFT
        beq     @next
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_UP
        beq     @next
        cmp     #KC_DOWN
        bne     @key
@next:  inc     trip_choice
        lda     trip_choice
        cmp     #3
        bcc     @draw
        lda     #0
        sta     trip_choice
        beq     @draw
@take:  ldx     trip_choice
        lda     trip_approach_result,x
        rts
@cancel:
        lda     #2
        rts
trip_approach_result: .byte 1,3,0
trip_short: .byte "ONE NATIVE STEP? RETURN/ARROWS/ESC|!",0
trip_orient: .byte "READJUST CAP? RETURN/ARROWS/ESC|!",0
trip_long: .byte "SET DURATION? RETURN/ARROWS/ESC|!",0
trip_two: .byte $82,0,0,0,0

trip_arrived: .byte "AT TARGET. CHOOSE A NEW MAP TARGET TO CONTINUE.",0

trip_to: .byte "TO ",0
trip_stop: .byte "|!",0

trip_tracked_resume: .byte "SAME CAP: RESUME # MIN? RETURN/ARROWS/ESC",0
trip_tracked_new: .byte "SAME CAP: NEW DURATION? RETURN/ARROWS/ESC",0
trip_tracked_abandon: .byte "ABANDON TRIP? RETURN/ARROWS/ESC",0
trip_tracked_lo: .byte <trip_tracked_resume,<trip_tracked_new,<trip_tracked_abandon,<trip_tracked_orient
trip_tracked_hi: .byte >trip_tracked_resume,>trip_tracked_new,>trip_tracked_abandon,>trip_tracked_orient

trip_tracked_orient: .byte "READJUST CAP? RETURN/ARROWS/ESC",0

trip_tracked_step: .byte "SAME CAP: NEXT STEP # MIN? RETURN/ARROWS/ESC",0

trip_elapsed: .word 0
trip_used: .byte "|USED # MIN",0
trip_left: .byte " LEFT #",0
trip_next: .byte " NEXT #",0
