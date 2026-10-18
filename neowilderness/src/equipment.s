; EQUIPMENT: physical placement and effective use are independent states.
; Directory 33 is fetched directly; scene asset 33 still uses site_load.
.segment "EQUIPMENT"
EQ_ROWS = 14
EQ_VISIBLE = EQ_ROWS * 2
module_equipment:
        lda     #$FF
        sta     overlay_current ; the $5800 window was fetched directly
        lda     #0
        sta     eq_keep
        lda     obj_keep
        beq     :+
        pha
        lda     #0
        sta     obj_keep
        lda     #1
        sta     pg_focus
        pla
        bpl     :+              ; $40: modal cancel; $80: command result
        jsr     eq_follow_role
        lda     #1
        sta     eq_keep
:       jsr     eq_build
        lda     #0
        sta     eq_cur
        ldx     #0
@find:  lda     overlay_text,x
        cmp     eq_selected
        beq     @found
        inx
        cpx     eq_n
        bcc     @find
        ldx     #0              ; first item in the selected role
@found: stx     eq_cur
        jsr     eq_forward
        bcs     equipment_draw
        lda     #0
        sta     eq_cur
        sta     pg_focus

equipment_draw:
        lda     #PG_EQUIPMENT
        jsr     page_top
        lda     eq_cur
        sec
        sbc     #EQ_VISIBLE-1
        bcs     :+
        lda     #0
:       sta     eq_top
        lda     eq_n
        clc
        adc     #1
        lsr
        cmp     #EQ_ROWS
        bcc     :+
        lda     #EQ_ROWS
:       sta     eq_split
        lda     #41
        jsr     tab
        lda     #3
        ldx     #1
        jsr     st_at_x
        lda     #0
        sta     eq_row
@role:  ldx     eq_row
        lda     #$FF
        cpx     eq_view
        bne     :+
        lda     #$3F
:       sta     INVFLG
        lda     eq_groups_lo,x
        ldy     eq_groups_hi,x
        jsr     print_str_ay
        lda     #$FF
        sta     INVFLG
        jsr     puts
        .byte   "  ",0
        inc     eq_row
        lda     eq_row
        cmp     #4
        bcc     @role
        lda     #41
        jsr     tab
        lda     #4
        ldx     #0
        jsr     st_at_x
        lda     #41
        jsr     tab
        lda     #0
        sta     eq_row
@row:   inc     CV
        jsr     t_vtab
        lda     #0
        sta     CH
        lda     #1
        jsr     tab
        lda     eq_row
        cmp     eq_split
        bcs     @empty
        clc
        adc     eq_top
        tax
        jsr     eq_cell
        lda     #21
        jsr     tab
        lda     eq_row
        clc
        adc     eq_top
        adc     eq_split
        tax
        jsr     eq_cell
@empty: lda     #41
        jsr     tab
        inc     eq_row
        lda     eq_row
        cmp     #EQ_ROWS
        jcc     @row
        inc     CV
        jsr     t_vtab
        lda     #0
        sta     CH
        lda     #41
        jsr     tab             ; left bottom; right column is drawn separately
        lda     #2
        ldx     #41
        jsr     st_at_x
        lda     #80
        jsr     tab             ; right title before its contents
        lda     eq_n
        bne     :+
        lda     #3
        jsr     eq_at
        jsr     puts
        .byte   "NO ITEM IN THIS ROLE",0
        lda     #4
        jsr     eq_at
        jsr     puts
        .byte   "NO ACTION: CHOOSE A NONEMPTY ROLE",0
        jmp     @details_done
:       lda     eq_cur
        tax
        lda     overlay_text,x
        jmi     @details_done
        sta     eq_item
        sta     eq_selected
        lda     #3
        jsr     eq_at
        ldx     eq_item
        jsr     eq_name
        jsr     print_str_ax
        lda     #4
        jsr     eq_at
        lda     pg_focus
        bne     @action_hint
        jsr     puts
        .byte   "RETURN: ENTER THE LIST",0
        jmp     @location
@action_hint:
        jsr     puts
        .byte   "RETURN: CHOOSE AN ACTION",0
@location:
        lda     #5
        jsr     eq_at
        jsr     puts
        .byte   "LOCATION: ",0
        jsr     eq_location
        lda     #7
        jsr     eq_at
        jsr     puts
        .byte   "ACTIVE: ",0
        ldx     eq_item
        jsr     eq_active
        beq     @inactive
        lda     #0
        beq     @active_test
@inactive:
        lda     #1
@active_test:
        cmp     #0
        jsr     eq_yes
        lda     #8
        jsr     eq_at
        jsr     puts
        .byte   "HANDS VOLUME: ",0
        lda     load_used+6
        sta     num
        lda     load_used+7
        sta     num+1
        jsr     print_u16
        lda     #'/'|$80
        jsr     COUT
        lda     load_limits+6
        sta     num
        lda     load_limits+7
        sta     num+1
        jsr     print_u16
        jsr     puts
        .byte   " IN3",0
        lda     #9
        jsr     eq_at
        jsr     puts
        .byte   "PACK/HANDS FREE IN3: ",0
        ldy     #4
        jsr     eq_free
        lda     #'/'|$80
        jsr     COUT
        ldy     #6
        jsr     eq_free
        lda     #10
        jsr     eq_at
        jsr     puts
        .byte   "WEIGHT FREE: ",0
        ldy     #0
        jsr     eq_free
        jsr     puts
        .byte   " OZ WEAR ",0
        ldy     #2
        jsr     eq_free
        jsr     puts
        .byte   " IN3",0
@details_done:
        lda     #13
        jsr     eq_at
        jsr     puts
        .byte   "TRAP PREPARED: ",0
        lda     fg_use
        and     #FT_TRAP
        cmp     #FT_TRAP
        jsr     eq_yes
        lda     #14
        jsr     eq_at
        jsr     puts
        .byte   "FISHING ACTIVE: ",0
        lda     fg_use
        and     #FT_GEAR
        cmp     #FT_GEAR
        jsr     eq_yes
        lda     #15
        jsr     eq_at
        jsr     puts
        .byte   "BAIT READY: ",0
        lda     fg_bait
        cmp     #1
        jsr     eq_yes
        lda     #20
        jsr     eq_at           ; finish the right-hand frame only
        lda     #20
        ldx     #0
        jsr     st_at_x         ; keep the last rows of both item columns
        ldx     #3
@answer:
        lda     eq_keep
        beq     :+
        lda     #39
        sta     CH
:       lda     #41
        jsr     tab
        lda     #80
        sta     CH              ; leave right hints intact until their final text
        jsr     CROUT
        dex
        bne     @answer
        lda     #1
        sta     eq_keep
        lda     #20
        jsr     eq_at
        lda     #23
        jsr     eq_at
        lda     #<eq_keys
        ldy     #>eq_keys
        ldx     pg_focus
        bne     :+
        lda     #<eq_tab_keys
        ldy     #>eq_tab_keys
:       jsr     page_foot23_x

equipment_key:
        jsr     wait_key
        ldx     pg_focus
        bne     @list
        cmp     #KC_RET
        beq     @focus
        jmp     @page
@focus: jsr     eq_forward
        inc     pg_focus
        jmp     equipment_draw
@list:  cmp     #KC_LEFT
        beq     @role_left
        cmp     #KC_RIGHT
        beq     @role_right
        cmp     #KC_RET
        jeq     eq_act
        cmp     #KC_DOWN
        beq     @down
        cmp     #KC_UP
        beq     @up
@page:  jsr     page_keys
        jmp     equipment_key
@role_left:
        lda     eq_view
        clc
        adc     #3
        bne     @role_set
@role_right:
        lda     eq_view
        clc
        adc     #1
@role_set:
        and     #3
        sta     eq_view
        jsr     eq_build
        lda     #0
        sta     eq_cur
        jmp     equipment_draw
@down:  lda     eq_cur
        pha
        inc     eq_cur
        jsr     eq_forward
        bcc     :+
        pla
        jmp     equipment_draw
:       pla
        sta     eq_cur
        jmp     equipment_key
@up:    dec     eq_cur
        ldx     eq_cur
@prev:  bmi     @tabs
        lda     overlay_text,x
        bpl     @set
        dex
        bpl     @prev
@tabs:  lda     #0
        sta     pg_focus
        beq     @redraw
@set:   stx     eq_cur
@redraw:
        jmp     equipment_draw

eq_forward:
        ldx     eq_cur
@find:  cpx     eq_n
        bcs     @no
        lda     overlay_text,x
        bpl     @yes
        inx
        bne     @find
@yes:   stx     eq_cur
        sec
        rts
@no:    clc
        rts

eq_at:  jmp     st_at
eq_yes: bne     @no
        jsr     puts
        .byte   "YES",0
        rts
@no:    jsr     puts
        .byte   "NO",0
        rts

eq_place:
        ldx     eq_item
        cpx     #89
        bcs     :+
        lda     it_place,x
        rts
:       lda     cr_b1-89,x
        rts

eq_free:
        sec
        lda     load_limits,y
        sbc     load_used,y
        sta     num
        lda     load_limits+1,y
        sbc     load_used+1,y
        sta     num+1
        bcs     :+
        lda     #0
        sta     num
        sta     num+1
:       jmp     print_u16

; Four navigation groups: the three equipment roles, then stowed gear.
; ACTIVE is read from simulation flags, never inferred from placement.
eq_build:
        lda     #0
        sta     eq_n
        lda     eq_view
        sta     eq_g
        ldx     #1
@item:  cpx     #22
        bne     :+
        ldx     #38
:       cpx     #76
        bne     :+
        ldx     #89
:       stx     eq_item
        lda     eq_g
        cmp     #2
        beq     @active
        jsr     eq_place
        ldy     eq_g
        cmp     eq_places,y
        beq     @add
        bne     @next
@active:
        jsr     eq_active
        beq     @next
@add:   txa
        jsr     eq_append
@next:  inx
        cpx     #94
        bcc     @item
        rts

eq_append:
        ldy     eq_n
        sta     overlay_text,y
        inc     eq_n
        rts

; X preserved; A nonzero when the corresponding effective-use flag is set.
eq_active:
        cpx     #89
        bcs     @crafted
        jsr     have
        bcc     @no
        cpx     #58
        beq     @tool
        cpx     #59
        bne     @lookup
@tool:  lda     px+1
        cmp     care_tool_x
        bne     @no
        lda     py+1
        cmp     care_tool_y
        bne     @no
@lookup:
        ldy     #eq_active_end-eq_active_items-1
@find:  txa
        cmp     eq_active_items,y
        beq     @flag
        dey
        bpl     @find
@no:    lda     #0
        rts
@flag:  lda     eq_active_lo,y
        sta     gp2
        lda     eq_active_hi,y
        sta     gp2+1
        lda     eq_active_masks,y
        sta     @mask+1
        ldy     #0
        lda     (gp2),y
@mask:  and     #0
        rts
@crafted:
        cpx     #93
        bne     :+
        lda     cr_b1+4
        cmp     #1
        bne     @no
        lda     medical_actions+2
        rts
:       lda     cr_b1-89,x
        cmp     #$FF
        beq     @no
        lda     eq_weapon_masks-89,x
        and     fg_use
        rts

; Two 20-column cells, top-to-bottom in each column. The selected item's
; full name remains in the right-hand sheet and in native action commands.
eq_cell:
        cpx     eq_n
        bcs     @done
        lda     overlay_text,x
        sta     eq_item
        cpx     eq_cur
        bne     @plain
        lda     pg_focus
        beq     @plain
        lda     #'>'|$80
        bne     @mark
@plain: lda     #' '|$80
@mark:  jsr     COUT
        lda     #' '|$80
        jsr     COUT
        ldx     eq_item
        jsr     eq_name
        sta     gp2
        stx     gp2+1
        ldy     #0
@name:  lda     (gp2),y
        beq     @done
        cpy     #15
        bcc     @char
        pha
        iny
        lda     (gp2),y
        dey
        tax
        pla
        cpx     #0
        beq     @char
        lda     #'.'
@char:  ora     #$80
        jsr     COUT
        iny
        cpy     #16
        bcc     @name
@done:  rts

eq_name:
        cpx     #89
        bcs     :+
        lda     it_name_lo,x
        pha
        lda     it_name_hi,x
        tax
        pla
        rts
:       lda     eq_names_lo-89,x
        pha
        lda     eq_names_hi-89,x
        tax
        pla
        rts

eq_act:
        lda     eq_n
        jeq     equipment_key
        ldx     eq_cur
        lda     overlay_text,x
        jmi     equipment_key
        sta     menu_noun
        sta     eq_item
        jsr     eq_place
        cmp     #0
        bne     @carried
        lda     #0
        beq     @source
@carried:
        lda     #1
@source:
        sta     ob_s            ; actual source, without changing OBJECTS selection
        ldx     eq_item
        jsr     eq_name
        sta     gp2
        stx     gp2+1
        ldy     #0
        lda     (gp2),y
        cmp     #'9'+1
        bcs     :+
@skip:  iny
        lda     (gp2),y
        cmp     #' '
        bne     @skip
        iny
:       ldx     #0
@verb:  lda     eq_use,x
        sta     ob_line,x
        inx
        cpx     #4
        bcc     @verb
@name:  lda     (gp2),y
        sta     ob_line,x
        beq     @ready
        inx
        iny
        bne     @name
@ready: lda     #0
        sta     ob_m
        sta     ob_m+1
        jmp     equipment_object

eq_location:
        jsr     eq_place
        bne     @carried
        lda     #om_local_label
        jmp     om_bank_puts
@carried:
        tay
        lda     eq_place_names,y
        pha
        lda     #om_to_body
        jmp     st_bank_suffix
eq_follow_role:
        lda     eq_selected
        beq     @done
        sta     eq_item
        tax
        lda     eq_view
        cmp     #2
        bne     @place
        jsr     eq_active
        bne     @done
@place: jsr     eq_place
        ldx     #0
        cmp     #1
        beq     @set
        inx
        cmp     #3
        beq     @set
        ldx     #3
@set:   stx     eq_view
@done:  rts
; Offsets in om_to_body: BODY, WORN, HANDS, PACK, LOCAL HUNG.
eq_place_names: .byte 21,5,16,10,21,21
eq_groups_lo: .byte <eq_worn,<eq_hands,<eq_used,<eq_pack
eq_groups_hi: .byte >eq_worn,>eq_hands,>eq_used,>eq_pack
eq_worn: .byte "WORN",0
eq_hands: .byte "HANDS",0
eq_used: .byte "ACTIVE",0
eq_pack: .byte "PACK",0
eq_places: .byte 1,3,$FF,2
eq_keys: .byte MS_RET," ACTIONS ",MS_UP,MS_DOWN," ITEM ",MS_LEFT,MS_RIGHT," ROLE",0
eq_tab_keys: .byte MS_RET," LIST",0
eq_use: .byte "USE "
eq_names_lo: .byte <eq_bow,<eq_spear,<eq_club,<eq_rock,<eq_splint
eq_names_hi: .byte >eq_bow,>eq_spear,>eq_club,>eq_rock,>eq_splint
eq_bow: .byte "BOW",0
eq_spear: .byte "SPEAR",0
eq_club: .byte "CLUB",0
eq_rock: .byte "ROCK",0
eq_splint: .byte "SPLINT",0
eq_weapon_masks: .byte FT_BOW,FT_SPEAR,FT_CLUB,FT_CLUB

eq_active_items: .byte 38,39,40,66,71,73,57,11,12,53,54,58,59,67,72
eq_active_end:
eq_active_lo: .byte <camp_use,<camp_use,<camp_use,<camp_use,<camp_use,<camp_use,<camp_use,<camp_use,<camp_use,<orient_aid,<orient_aid,<care_tools,<care_tools,<fg_use,<fg_use
eq_active_hi: .byte >camp_use,>camp_use,>camp_use,>camp_use,>camp_use,>camp_use,>camp_use,>camp_use,>camp_use,>orient_aid,>orient_aid,>care_tools,>care_tools,>fg_use,>fg_use
eq_active_masks: .byte U_MATCH,U_GLASS,U_FUEL,U_FLASH,U_STOVE,U_UTENS,U_GUN,U_COVER,U_COVER,1,2,1,2,FT_GEAR,FT_TRAP

eq_frames:
        PF 2,19,0,39,eq_title
        PF 2,11,41,79,eq_state
        PF 12,16,41,79,eq_catch
        .byte PF_END
eq_title: .byte "EQUIPMENT",0
eq_state: .byte "SELECTED ITEM",0
eq_catch: .byte "CATCH READINESS",0
eq_n: .byte 0
eq_g: .byte 0
eq_row: .byte 0
eq_split: .byte 0
eq_top: .byte 0
eq_cur: .byte 0
eq_item: .byte 0
eq_keep: .byte 0

.pushseg
.segment "STATUS"
; Keep the caller outside $5800 while replacing EQUIPMENT with the editor.
equipment_object:
        lda     #20
        jsr     overlay_load
        jmp     object_menu
.popseg

.pushseg
.segment "BSS"
eq_view: .res 1                 ; interface role, outside SAVE
.popseg

; MENU shares this disk window; resident dispatch abandons its caller.
menu_draw:
        lda     #66
        jsr     st_heading
        jsr     st_rangers
        jsr     puts
        .byte   "|JOURNEY DONE: ", 0
        lda     st_done
        jsr     pdec
        jsr     puts
        .byte   "%  ", 0
        lda     st_done
        jsr     st_cells
        jsr     bar
        lda     #6              ; (XL: under the RANGERS post-it)
        jsr     vtab
        lda     #76
        jsr     st_heading
        jsr     pg_first
        lda     #82
        jsr     pg_line_text
        jsr     pg_line
        lda     #102
        jsr     pg_line_text
        jsr     pg_line
        lda     #113
        jsr     pg_line_text
        jsr     pg_line
        jsr     puts
        .byte   "PREPARE",0
        lda     #$FF
        sta     INVFLG
        jsr     pg_line
        jsr     puts
        .byte   "SURVIVAL",0
        lda     #$FF
        sta     INVFLG
        jsr     pg_line
        jsr     puts
        .byte   "NIGHT",0
        lda     #$FF
        sta     INVFLG
        jsr     pg_line
        jsr     puts
        .byte   "NEXT ACTION",0
        lda     #$FF
        sta     INVFLG
        lda     #<pg_k_menu_x
        ldy     #>pg_k_menu_x
        jsr     page_foot_x
        jmp     pg_menu_key
