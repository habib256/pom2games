; Deliberate shortcuts and one observed, actionable correction. UI only.
; The caller installs main as the return address before replacing GRID.
.segment "CAMPUI"
context_cursor = menu_duration  ; retired duration index; not journey state
module_context:
        jsr     context_observe
        lda     context_cursor
        cmp     context_count
        jcc     context_draw
        lda     #0
        sta     context_cursor
context_draw:
        jsr     text_begin
        lda     #20
        sta     WNDTOP
        jsr     context_at
        ldx     #0
@choice:
        stx     context_item
        lda     #$FF
        cpx     context_cursor
        bne     :+
        lda     #$3F
:       sta     INVFLG
        cpx     #3
        beq     @fix_name
        lda     context_names_lo,x
        ldy     context_names_hi,x
        jmp     @print_name
@fix_name:
        ldx     context_issue
        lda     context_fix_lo-1,x
        ldy     context_fix_hi-1,x
@print_name:
        jsr     context_print
        lda     #$FF
        sta     INVFLG
        jsr     puts
        .byte "    ",0
        ldx     context_item
        inx
        cpx     context_count
        bcc     @choice
        jsr     topo_pad
        lda     #21
        jsr     context_at
        jsr     context_warning
        jsr     topo_pad
        lda     #22
        jsr     context_at
        ldx     context_cursor
        lda     context_help_lo,x
        ldy     context_help_hi,x
        jsr     context_print
        jsr     topo_pad
        lda     #23
        jsr     context_at
        jsr     puts
        .byte "ARROWS CHOOSE  RETURN OPEN  ESC VIEW",0
        jsr     topo_pad
        jsr     text_release
        jsr     show_dhgr
context_key:
        jsr     wait_key
        cmp     #KC_ESC
        beq     @back
        cmp     #KC_RET
        beq     @open
        cmp     #KC_LEFT
        beq     @previous
        cmp     #KC_UP
        beq     @previous
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_DOWN
        bne     context_key
@next:  inc     context_cursor
        lda     context_cursor
        cmp     context_count
        jcc     context_draw
        lda     #0
        sta     context_cursor
        jmp     context_draw
@previous:
        dec     context_cursor
        jpl     context_draw
        lda     context_count
        sec
        sbc     #1
        sta     context_cursor
        jmp     context_draw
@back:  jmp     back_to_view_now
@open:  jsr     back_to_view_now
        lda     context_cursor
        cmp     #3
        jeq     context_fix
        cmp     #0
        beq     @camp
        cmp     #1
        beq     @next_action
        jmp     navigation_route_open
@camp:  jmp     module_camp_departure
@next_action:
        lda     #5
        jmp     guidance_open

context_at:
        sta     CV
        jsr     t_vtab
        lda     #0
        sta     CH
        rts
context_print:
        sta     gp2
        sty     gp2+1
        ldy     #0
@char:  lda     (gp2),y
        beq     @done
        ora     #$80
        jsr     COUT
        iny
        bne     @char
@done:  rts

; Observe without consuming stock, time or RNG. The fourth choice exists
; only while the displayed condition has a corresponding deliberate action.
context_observe:
        lda     #3
        sta     context_count
        lda     #0
        sta     context_issue
        jsr     context_find_issue
        sta     context_issue
        beq     :+
        inc     context_count
:       rts
context_warning:
        ldx     context_issue
        beq     @done
        lda     context_warn_lo-1,x
        ldy     context_warn_hi-1,x
        jmp     context_print
@done:  rts
context_find_issue:
        lda     fire_on
        beq     @water
        lda     #1
        rts
@water: ldx     #N_WATER
        jsr     context_carried
        bcs     @food
        lda     #2
        rts
@food:  ldx     #23
@scan:  jsr     context_carried
        bcs     @capacity
        inx
        cpx     #38
        bcc     @scan
        cpx     #76
        bcs     :+
        ldx     #76
:       cpx     #87
        bcc     @scan
        lda     #3
        rts
@capacity:
        ldx     #0
@limit: lda     load_used+1,x
        cmp     load_limits+1,x
        bcc     @next
        bne     @full
        lda     load_used,x
        cmp     load_limits,x
        bcs     @full
@next:  inx
        inx
        cpx     #8
        bcc     @limit
        lda     #0
        rts
@full:  lda     #4
        rts
context_carried:
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        beq     @no
        jsr     member
        and     #G_HAND|G_PACK
        beq     @no
        sec
        rts
@no:    clc
        rts

; Forms retain their native source and portion confirmation. Reuse their
; resident trampoline so the original QUICK return frame is replaced once.
context_fix:
        lda     context_issue
        cmp     #1
        beq     @fire
        tax
        lda     context_verbs-2,x
        jmp     flows_execute
@fire: jsr     cg_puts
        .byte "DOUSE THIS FIRE? NO TIME PASSES.",0
        lda     #23
        jsr     fu_position
        jsr     cg_more
        .byte "RET:DOUSE FIRE ESC:BACK",0
@key:  jsr     cg_view_key
        cmp     #KC_ESC
        jeq     context_draw
        cmp     #KC_RET
        bne     @key
        lda     #0
        sta     cg_departure_origin
        sta     cg_cursor
        lda     #3
        sta     cg_choices
        jmp     cd_accept
context_count: .byte 3
context_issue: .byte 0
context_verbs: .byte 6,5,7
context_fix_lo: .byte <context_fix_fire,<context_fix_water,<context_fix_food,<context_fix_load
context_fix_hi: .byte >context_fix_fire,>context_fix_water,>context_fix_food,>context_fix_load
context_fix_fire: .byte "FIX: DOUSE",0
context_fix_water: .byte "FIX: DRINK",0
context_fix_food: .byte "FIX: EAT",0
context_fix_load: .byte "FIX: FIT",0
context_warn_lo: .byte <context_warn_fire,<context_warn_water,<context_warn_food,<context_warn_load
context_warn_hi: .byte >context_warn_fire,>context_warn_water,>context_warn_food,>context_warn_load
context_warn_fire: .byte "FIRE STILL BURNING HERE.",0
context_warn_water: .byte "NO CARRIED WATER STOCK.",0
context_warn_food: .byte "NO CARRIED FOOD STOCK.",0
context_warn_load: .byte "A CARRYING CAPACITY IS FULL. GET PREVIEWS FITTING PORTION.",0
context_item: .byte 0
context_names_lo: .byte <context_camp,<context_next,<context_map
context_names_hi: .byte >context_camp,>context_next,>context_map
context_help_lo: .byte <context_camp_help,<context_next_help,<context_map_help,<context_fix_help
context_help_hi: .byte >context_camp_help,>context_next_help,>context_map_help,>context_fix_help
context_camp: .byte "CAMP",0
context_next: .byte "NEXT ACTION",0
context_map: .byte "MAP",0
context_camp_help: .byte "REVIEW CAMP PREPARATION; CONFIRM EACH ACTION SEPARATELY.",0
context_next_help: .byte "REVIEW THE MOST PRESSING OBSERVED NEED.",0
context_map_help: .byte "REVIEW YOUR TARGET AND CAP; OPENING THE MAP DOES NOT MOVE YOU.",0

context_fix_help: .byte "REVIEW NATIVE SOURCE / PORTION; CONFIRM OR CANCEL EACH ACTION.",0
