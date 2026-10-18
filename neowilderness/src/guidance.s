; VERHILLE Arnaud — GPL-3.0. Guided survival: inspection is read-only.
; A = MEAL/WATER/ENERGY/BODY (0..3). dep_cursor belongs to UI, outside SAVE.
; SITES restores GRID only after the player accepts; native menus retain
; source, taste, portion and duration confirmation and native refusals.
.segment "GUIDANCE"
module_guidance:
        pha
        jsr     menu_gather     ; STATUS had overwritten MENUSWAP inspectors
        pla
        and     #3
        sta     dep_cursor
guidance_draw:
        jsr     text_mode80
        jsr     text_begin
        lda     #0
        sta     WNDTOP
        sta     dep_mask
        sta     dep_mask+1
@clear: lda     dep_mask
        jsr     guidance_at
        jsr     topo_pad
        inc     dep_mask
        lda     dep_mask
        cmp     #24
        bcc     @clear
        lda     #0
        jsr     guidance_at
        jsr     puts
        .byte "SURVIVAL GUIDE",0
        jsr     topo_pad
        lda     #3
        jsr     guidance_at
        ldx     dep_cursor
        lda     guidance_lo,x
        sta     gp2
        lda     guidance_hi,x
        sta     gp2+1
        ldx     dep_cursor
        cpx     #2
        beq     @energy_header
        cpx     #3
        bne     @header
        jsr     guidance_comfort
        bne     @thermal_header
        lda     #<guidance_comfortable
        sta     gp2
        lda     #>guidance_comfortable
        sta     gp2+1
        jmp     @header
@thermal_header:
        lda     thermal_mode
        cmp     #1
        bne     @header
        lda     #$82
        sta     dep_mask
        lda     #<guidance_hot
        sta     gp2
        lda     #>guidance_hot
        sta     gp2+1
        jmp     @header
@energy_header:
        lda     #$82
        sta     dep_mask
        fld     s_rest
        fop     FCOMP, f_16
        cmp     #1
        beq     @beat
        fld     s_defr
        fop     FCOMP, f_12
        cmp     #1
        bne     @normal_energy
        lda     #$84
        sta     dep_mask
        lda     #<guidance_tired
        ldx     #>guidance_tired
        bne     @energy_text
@beat:  lda     #$86
        sta     dep_mask
        lda     #<guidance_beat
        ldx     #>guidance_beat
        bne     @energy_text
@normal_energy:
        lda     #<guidance_energy
        ldx     #>guidance_energy
@energy_text:
        sta     gp2
        stx     gp2+1
@header:jsr     guidance_print
        jsr     topo_pad
        lda     #6
        jsr     guidance_at
        lda     dep_cursor
        jeq     @food
        cmp     #1
        jeq     @water
        cmp     #2
        jeq     @rest
        jsr     guidance_comfort
        jeq     @footer
        lda     thermal_mode
        cmp     #1
        jeq     @hot
        lda     fire_on
        jne     @fire
        ldx     #38
        jsr     mk_stock
        bcc     @matches
        jsr     mk_fire
        jcs     @available
        jsr     puts
        .byte "NEED FUEL IN STORM OR DRY LAND.",0
        jmp     @footer
@hot:   jsr     puts
        .byte "HOT: SEEK SHADE, REST AND DRINK; AVOID FIRE.",0
        jmp     @footer
@matches:
        jsr     puts
        .byte "NEED MATCHES WITH USES LEFT.",0
        jmp     @footer
@fire:  jsr     puts
        .byte "FIRE PRESENT: CHOOSE USE FIRE.",0
        jmp     @footer
@rest:  jsr     puts
        .byte "REST AVAILABLE; SEEK SHELTER IN COLD.",0
        jmp     @footer
@water: lda     camp_untreated
        pha
        jsr     grid_water
        pla                     ; legacy water_here marks contamination
        sta     camp_untreated  ; inspection must preserve it (and carry)
        jcs     @available
        ldx     #N_WATER
        jsr     have
        jcs     @stock
        lda     weather_sky
        cmp     #2
        jcs     @available
        jsr     level_here
        cmp     M_SNOW
        jcs     @available
        jsr     puts
        .byte "NO WATER HERE: FIND OR MAKE WATER.",0
        jmp     @footer
@food:  lda     #F_EAT
        sta     mn_t
        ldx     #23
@scan:  jsr     item_ok
        jcs     @stock
        inx
        cpx     #38
        bcc     @scan
        cpx     #76
        bcs     :+
        ldx     #76
:       cpx     #87
        bcc     @scan
        jsr     puts
        .byte "NO FOOD HERE: FORAGE OR HUNT.",0
        jmp     @footer
@stock: stx     dep_mask+1
@available:
        jsr     puts
        .byte "AVAILABLE HERE; CHOOSE SOURCE NEXT.",0
        lda     #7
        jsr     guidance_at
        ldx     dep_mask+1
        jeq     @footer
        lda     it_name_lo,x
        sta     gp2
        lda     it_name_hi,x
        sta     gp2+1
        jsr     guidance_print
        jsr     puts
        .byte ": TRY ",0
        lda     #4
        ldx     dep_cursor
        beq     :+
        asl     a
:       sta     num
        ldx     dep_mask+1
        jsr     member
        and     #G_PACK
        beq     @ground
        ldx     dep_mask+1
        cpx     #76
        bcs     @pilepack
        lda     it_pack_hi,x
        bne     @amount
        lda     it_pack_lo,x
        jmp     @limit
@pilepack:
        txa
        sec
        sbc     #76
        tax
        lda     fg_ph,x
        bne     @amount
        lda     fg_pl,x
        jmp     @limit
@ground:
        ldx     dep_mask+1
        cpx     #76
        bcs     @pileground
        lda     it_gnd_hi,x
        bne     @amount
        lda     it_gnd_lo,x
        jmp     @limit
@pileground:
        txa
        sec
        sbc     #76
        tax
        lda     fg_gh,x
        bne     @amount
        lda     fg_gl,x
@limit: cmp     num
        bcs     @amount
        sta     num
@amount:
        lda     num
        jsr     pdec
        jsr     puts
        .byte " OZ",0
@footer:
        jsr     topo_pad
        lda     #22
        jsr     guidance_at
        jsr     puts
        .byte "UP/DOWN NEED  RETURN ACTION  ESC VIEW",0
        jsr     topo_pad
        jsr     text_release
        jsr     show_text
guidance_key:
        jsr     wait_key
        cmp     #KC_ESC
        beq     guidance_leave
        cmp     #KC_RET
        beq     guidance_take
        cmp     #KC_UP
        beq     @up
        cmp     #KC_DOWN
        bne     guidance_key
        inc     dep_cursor
        bne     @wrap
@up:    dec     dep_cursor
@wrap:  lda     dep_cursor
        and     #3
        jmp     module_guidance
guidance_leave:
        lda     #0
        sta     dep_mask
        jmp     back_to_view_now
guidance_take:
        lda     dep_cursor
        cmp     #3
        bne     @execute
        jsr     guidance_comfort
        beq     guidance_key    ; comfortable BODY never prepares a command
@execute:
        lda     #10
        jsr     overlay_load
        lda     dep_cursor
        jmp     guidance_execute

guidance_comfort:
        lda     thermal_mode
        ora     wet_mode
        rts

guidance_print:
        ldy     #0
@char:  lda     (gp2),y
        beq     @done
        ora     #$80
        jsr     COUT
        iny
        bne     @char
@done:  rts
guidance_lo: .byte <guidance_meal,<guidance_water,<guidance_energy,<guidance_body
guidance_hi: .byte >guidance_meal,>guidance_water,>guidance_energy,>guidance_body
guidance_meal: .byte "MEAL: UP TO 4 OZ, LIMITED TO STOCK; TASTE FIRST.",0
guidance_water: .byte "WATER: UP TO 8 OZ, LIMITED TO STOCK; TASTE IS NO SAFETY TEST.",0
guidance_energy: .byte "ENERGY: TRY REST 30 MIN, THEN REVIEW.",0
guidance_hot: .byte "BODY: COOL DOWN. RETURN OPENS REST.",0
guidance_body: .byte "BODY: MAKE THEN USE FIRE; CHECK WET CLOTHES.",0

guidance_comfortable: .byte "BODY COMFORTABLE: NO ACTION NEEDED",0

guidance_tired: .byte "ENERGY TIRED: TRY REST 2 H, THEN REVIEW.",0
guidance_beat: .byte "ENERGY BEAT: TRY REST 8 H, THEN REVIEW.",0

; This overlay is independent of the map planner.
guidance_at:
        sta     CV
        lda     #0
        sta     CH
        jmp     t_vtab
