; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; grid.s -- the GRID module (docs/MENUS.md 4, docs/MEMORY.md 18): what RETURN
; does in the grid of src/menu.s, and the queue of prerequisites.
;
; Copied from the store to GRID_RUN (the SIM window, below the grid's image
; MENUSWAP at $B000 and above the campfire's buffers) at each RETURN in the
; grid and at each step of a queue (menu.s grid_fetch): the SIM window is
; free at the prompt (finish_simulation), the $5800 window keeps its module
; (CAMP between the steps of MAKE FIRE). It calls the resident code and
; MENUSWAP only, loads no module, and ends in idle (a list shown),
; done_menu (get_line returns a command) or get_line_body (the prompt).
;
;   module_select   RETURN: a verb opens its list or composes its command;
;                   an entry of a list completes it. A greyed verb beeps. A
;                   list of one entry is skipped (its entry chosen).
;   module_queue    get_line with a queue: the step that ran is checked (its
;                   flag, no new encounter), then the next one is typed.
;   grid_item_name  the display name of a list's item (text_of).
;
; Lists: GET names the water sources, the piles of lot 4 and the items on
; the ground, hung here or in the hand, and composes PACK x, or CARRY x
; (the backpack, the canteen, no backpack, a PACK refused), GET x for the
; BOW, SPEAR, CLUB, ROCK, SPLINT on the ground here (lot 3: into the hand,
; the original's GET; DROP and USE name them too, gr_where); WEAR the
; clothes not worn, then the worn ones ("-": PACK x takes one off); EAT the
; piles of food, the provisions, the oral remedies, then TASTE and the
; ounces (at most what is here); DRINK the sources, then the ounces (at
; most what is here and .2 x the body weight); USE the items USE handles,
; then the fire; KILL, CATCH, SKIN, COOK their named targets; MAKE what can
; be made here (FIRE, WATER).
;
; The queue (docs/MENUS.md 4): a choice of the grid may need commands of
; the original first (MAKE FIRE: USE FUEL in rain or wind, USE MATCHES,
; then USE FIRE in the cold; BOIL: USE UTENSILS; CATCH: USE BAIT, TRAP or
; FISHNG GEAR; KILL: the best weapon (GUN, BOW, SPEAR, AXE, KNIFE; none
; when one is in use); MAKE WATER: USE GND COVER; USE STOVE:
; FUEL, MATCHES; USE FRSTAID KIT at night: USE FLASHLIGHT; the MEDICAL
; page's CUT BODY: USE KNIFE). They are typed one by one, exactly as the
; keyboard would (same time, draws, state); a step already done is skipped
; (PRE), a step that failed (POST: its flag not set) or a new encounter
; ends the queue, the refusal visible. Typed commands keep the original's
; refusals: only menu intentions request preparation.
; ============================================================================
GRID_MODULE = 32                ; directory entry (memory.s MOD_COUNT)
GRID_RUN = $A000                ; src/wild.cfg GRIDM
BELL1    = $FBDD                ; Monitor: the speaker alone
; Steps of the queue (gr_steps): flags + check, noun (0: mq_noun, named
; after the text), text.
Q_PRE    = $80                  ; skipped when its check holds already
Q_POST   = $40                  ; the queue ends when its check fails
Q_INV    = $20                  ; the queue ends when its check holds
Q_SIZE   = $10                  ; append a portion (BOIL) or duration (CATCH)
S_FUEL   = 0
S_MATCH  = 1
S_MKFIRE = 2
S_UFIRE  = 3
S_COVER  = 4
S_RAINC  = 5
S_MKWAT  = 6
S_UTENS  = 7
S_BOIL   = 8
S_BAIT   = 9
S_TRAP   = 10
S_GEAR   = 11
S_GUN    = 12
S_AXE    = 13
S_KNIFE  = 14
S_FLASH  = 15
S_STOVE  = 16
S_KIT    = 17
S_CUT    = 18
S_KILL   = 19
S_CATCH  = 20
S_PACK   = 21
S_CARRY  = 22
S_BOW    = 23                   ; lot 3: the crafted weapons of KILL
S_SPEAR  = 24
S_OBJECTS = 25                  ; the OBJECTS page again after its transfer
S_EQUIPMENT = 26
S_CARE_RETURN = 27
S_CRAFT_RETURN = 28
S_CRAFT_MAKE = 30
S_CRAFT_USE = 29
S_DEPARTURE_RETURN = 31
MQ_CATCH_DUR = mq_list+4        ; CATCH uses at most 3 of the 5 queue slots

.segment "GRID"
; ----------------------------------------------------------------------------
; module_select -- RETURN on the selected cell.
; ----------------------------------------------------------------------------
module_select:
        lda     mn_level
        cmp     #1
        jne     gr_entry
        ldx     mn_cur
        lda     mn_idx,x
        cmp     #126
        jeq     gr_quick_fetch
        lda     mn_idx,x        ; CMP must not replace the native grey bit
        bpl     :+
        and     #$7F
        jmp     gr_refusal_fetch
gr_beep:
        jsr     BELL1
        jmp     idle
:       sta     mn_verb
        txa
        jsr     text_of         ; gp2 = label; its kind and context before it
        ldy     #0
        sec
        lda     gp2
        sbc     #2
        sta     gp2
        bcs     :+
        dec     gp2+1
:       lda     (gp2),y
        and     #$7F
        sta     mn_kind
        iny
        lda     (gp2),y
        sta     gr_t
        iny
        tya
        clc
        adc     gp2
        sta     gp2
        bcc     :+
        inc     gp2+1
:       jsr     append_str      ; gp2 then points to the suffix, if any
        lda     gr_t
        and     #C_SUFFIX
        beq     :+
        jsr     append_str
:       lda     mn_kind
        jeq     done_menu       ; K_NONE: the label is the command
        cmp     #K_ITEMS
        jcs     gr_items
        cmp     #K_DUR
        bne     :+
        ldx     mn_verb
        cpx     #5              ; common selector for WALK/SWIM/REST/WAIT
        jcc     done_menu
:       lda     mn_kind
        cmp     #K_LOOK+1
        bcs     :+
        ldx     #<list_dur      ; K_DUR, K_LOOK
        ldy     #>list_dur
        cmp     #K_DUR
        jeq     gr_strings
        ldx     #<list_look
        ldy     #>list_look
        jmp     gr_strings
:       cmp     #K_CLIMB
        bne     :+
        jsr     append_space    ; one applies: CLIMB DOWN in a tree, else TREE
        ldx     #<str_tree
        ldy     #>str_tree
        lda     tree_in
        beq     gr_word
        ldx     #<str_down
        ldy     #>str_down
gr_word:
        stx     gp2
        sty     gp2+1
        jsr     append_str
        jmp     done_menu
:       cmp     #K_CARE
        bne     :+
        lda     #0              ; STATUS, the MEDICAL page on the first
        sta     linelen         ; condition (pages.s pg_open)
        inc     pg_open
        ldx     #<str_status
        ldy     #>str_status
        bne     gr_word
:       cmp     #K_BOIL
        bne     gr_make
        lda     camp_use
        and     #U_UTENS
        bne     :+
        lda     #18             ; preparation is deliberate before choosing ounces
        jmp     gr_refusal_fetch
:       lda     it_pack_lo+N_WATER      ; BOIL: the ounces, at most the
        ldy     it_pack_hi+N_WATER      ; canteen's (else the pile's here:
        bne     @big                    ; camp.s camp_boil)
        tax
        bne     @lo
        ldx     #N_WATER
        jsr     at_ground
        lda     #0
        bcc     @lo
        lda     it_gnd_lo+N_WATER
        ldy     it_gnd_hi+N_WATER
        beq     @lo
@big:   lda     #255
@lo:    sta     gr_cap
        ldx     #<list_qty
        ldy     #>list_qty
        lda     #0
        jmp     gr_sizes
; MAKE: FIRE and WATER, those that can be made here (menu.s mk_fire,
; mk_water); the list starts at WATER when the fire cannot.
gr_make:
        lda     #0
        sta     gr_t
        jsr     mk_fire
        rol     gr_t
        jsr     mk_water
        lda     #0
        adc     gr_t
        ldx     #<list_make
        ldy     #>list_make
        lsr     gr_t
        bcs     :+
        ldx     #<list_water
        ldy     #>list_water
:       sta     mn_count
        jmp     gr_open

; gr_strings -- X/Y = a list of strings (empty string ends): level 2.
gr_strings:
        stx     mn_list
        sty     mn_list+1
        stx     gp2
        sty     gp2+1
        lda     #0
        sta     mn_count
:       ldy     #0
        lda     (gp2),y
        beq     gr_list
        jsr     skip_str
        inc     mn_count
        bne     :-
; gr_open -- X/Y = the strings, mn_count of them: the list at level 2 (or 3
; from a list), six cells of 6; a list of one entry is chosen at once.
gr_open:
        stx     mn_list
        sty     mn_list+1
gr_list:
        lda     #0
        sta     mn_items
        sta     mn_hdr
        lda     #6
        sta     mn_cols
        sta     mn_wid
gr_level:
        lda     #0
        sta     mn_cur
        sta     mn_top
        inc     mn_level
        jsr     gr_recall
        jsr     gr_catch_focus
        lda     mn_count
        beq     :+
        cmp     #1
        jeq     module_select   ; one entry: chosen
        jsr     redraw
        jmp     idle
:       jsr     level1          ; nothing to name (cannot happen: the verb
        jsr     redraw          ; would be greyed)
        jmp     gr_beep

 ; A local carcass suggests GET; opening that list selects the catch itself
; rather than unrelated water or equipment. RETURN still confirms the item.
gr_catch_focus:
        lda     mn_level
        cmp     #2
        bne     @done
        lda     mn_items
        beq     @done
        lda     gr_f
        bne     @done           ; F_GET = 0
        lda     mn_anim
        cmp     #8              ; context identity GET + 1
        bne     @done
        ldy     #0
@scan:  lda     overlay_text,y
        cmp     #80
        bcc     @next
        cmp     #82
        bcs     @next
        tax
        lda     fg_b2-76,x
        cmp     #1
        beq     @found
@next:  iny
        cpy     mn_count
        bcc     @scan
@done:  rts
@found: sty     mn_cur
        rts

; gr_items -- an item verb: its list (gr_build) at level 2.
gr_items:
        sbc     #K_ITEMS
        sta     gr_f
        jsr     gr_build
        lda     #1
        sta     mn_items
        lda     #3
        sta     mn_cols
        lda     #12
        sta     mn_wid
        bne     gr_level

; ----------------------------------------------------------------------------
; gr_entry -- RETURN in a list: the entry completes the command.
; ----------------------------------------------------------------------------
gr_entry:
        lda     mn_kind         ; (the module is fresh: the filter again)
        sec
        sbc     #K_ITEMS
        sta     gr_f
        lda     mn_kind
        cmp     #K_BOIL
        bne     :+
        ldy     mn_cur
        lda     gr_size,y
        sta     menu_portion+2
        lda     mn_cur          ; BOIL WATER n OZ: USE UTENSILS first
        sta     mq_noun
        jsr     q_clear
        lda     #S_UTENS
        jsr     q_add
        lda     #S_BOIL
        jmp     q_last
:       cmp     #K_MAKE
        bne     :+
        lda     mn_cur          ; MAKE FIRE or MAKE WATER: their queues
        jsr     text_of
        ldy     #0
        lda     (gp2),y
        cmp     #'W'
        jeq     gr_mkwater
        jmp     gr_mkfire
:       lda     mn_items
        bne     gr_item
        lda     gr_f
        cmp     #F_CATCH
        jeq     gr_catch_queue
        lda     mn_level        ; durations, directions, ounces: appended
        cmp     #3
        bne     gr_append
        lda     gr_f
        cmp     #F_EAT
        bne     gr_append
        lda     mn_cur          ; EAT's first entry: TASTE x
        bne     gr_append
        sta     linelen
        ldx     #<str_taste
        ldy     #>str_taste
        stx     gp2
        sty     gp2+1
        jsr     append_str
        lda     menu_noun
        jsr     gr_name_of
        jmp     done_menu
gr_append:
        jsr     gr_remember
        jsr     append_space
        lda     mn_cur
        jsr     text_of
        jsr     append_str
        jmp     done_menu
gr_name_of:                     ; A = item: " " + its name to inbuf
        pha
        jsr     append_space
        pla
        tax
        jsr     grid_item_name
        jmp     append_str
gr_with_name:                   ; " " + the selected item's name to inbuf
        jsr     append_space
        lda     mn_cur
        jsr     text_of
        jmp     append_str

; An item of a list: per verb.
gr_item:
        ldy     mn_cur
        lda     overlay_text,y
        sta     gr_x
        cmp     #169            ; RAIN 169, SNOW 170: their own nouns
        beq     :+
        cmp     #170
        beq     :+
        and     #$7F            ; (WEAR: bit 7, worn)
:       sta     menu_noun
        sta     mq_noun
        ldx     gr_f
        lda     gr_do_lo,x
        sta     gp1
        lda     gr_do_hi,x
        sta     gp1+1
        jmp     (gp1)
gr_do_lo: .byte <gr_get, <gr_wear, <gr_named, <gr_eat, <gr_use, <gr_drink
          .byte <gr_kill, <gr_named, <gr_catch, <gr_named
gr_do_hi: .byte >gr_get, >gr_wear, >gr_named, >gr_eat, >gr_use, >gr_drink
          .byte >gr_kill, >gr_named, >gr_catch, >gr_named

; DROP, SKIN, COOK x: the verb and the name.
gr_named:
        lda     mn_cur
        jmp     gr_append

; WEAR x, or a worn one (bit 7): PACK x takes it off (gr_pack).
gr_wear:
        lda     gr_x
        bpl     gr_named
        jmp     gr_pack

; GET: a source of water (WATER, RAIN, SNOW) is collected (GET x: the
; canteen); anything else goes to the pack or the hand (gr_pack).
gr_get:
        lda     menu_noun
        cmp     #N_WATER
        beq     gr_named
        cmp     #169
        bcs     gr_named
        cmp     #94             ; lot 3: GET BOW .. SPLINT, into the hand as
        bcs     gr_pack         ; the original's GET (src/craft.s cr_items)
        cmp     #89
        bcs     gr_named
; gr_pack -- mq_noun to the pack: PACK x, then CARRY x if PACK is refused
; (gear only: the provisions and the piles go to the pack alone); CARRY x
; at once for the backpack, the canteen and gear without a backpack.
gr_pack:
        jsr     q_clear
        ldx     mq_noun
        cpx     #21
        beq     @carry
        cpx     #64
        beq     @carry
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcc     @pack
        cpx     #76
        bcs     @pack
@gear:  lda     it_place+21     ; the backpack on the ground, hung or lost
        beq     @carry
        cmp     #5
        beq     @carry
        cmp     #$FF
        beq     @carry
        lda     #S_PACK
        jsr     q_add
@carry: lda     #S_CARRY
        jmp     q_last
@pack:  lda     #S_PACK
        jmp     q_last

; EAT: food (provisions, piles) opens TASTE and the ounces; a remedy is
; eaten at once.
gr_eat:
        lda     menu_noun
        cmp     #38
        bcc     :+
        cmp     #76
        bcc     gr_named
:       jsr     gr_with_name
        jsr     gr_avail        ; gr_cap = the ounces here
        ldx     #<list_taste
        ldy     #>list_taste
        lda     #1
        bne     gr_sizes
; DRINK: the ounces, at most what is here and .2 x the body weight
; (camp.s drink_limit: "DON'T BE RIDICULOUS!" above).
gr_drink:
        jsr     gr_with_name
        jsr     gr_avail
        lda     body_weight     ; .2 x the weight: weight / 5
        sta     gr_t
        lda     body_weight+1
        ldx     #0
@five:  pha
        lda     gr_t
        sec
        sbc     #5
        sta     gr_t
        pla
        sbc     #0
        bcc     :+
        inx
        bne     @five
:       cpx     gr_cap
        bcs     :+
        stx     gr_cap
:       ldx     #<list_qty
        ldy     #>list_qty
        lda     #0
; gr_sizes -- X/Y = the strings (TASTE first when A = 1), the sizes up to
; gr_cap ounces (one at least): the list at level 3.
gr_sizes:
        sta     mn_count
        ldy     #0
:       lda     gr_size,y
        cmp     gr_cap
        beq     @in
        bcs     @done
@in:    inc     mn_count
        iny
        cpy     #gr_size_end-gr_size
        bcc     :-
@done:  tya
        bne     :+
        inc     mn_count        ; none fits: the smallest anyway
:       ldy     #>list_qty
        jmp     gr_open
gr_size: .byte 1, 2, 4, 8, 12, 16, 24, 32, 48
gr_size_end:

; Remember choices only when their final entry is validated, never while
; moving or cancelling. EAT's TASTE entry deliberately keeps the last meal.
gr_remember:
@portion:
        lda     mn_level
        cmp     #3
        bne     @done
        ldx     #0
        ldy     mn_cur
        lda     gr_f
        cmp     #F_EAT
        bne     @drink
        dey
        bmi     @done
        bpl     @save
@drink: cmp     #F_DRINK
        bne     @done
        inx
@save:  lda     gr_size,y
        sta     menu_portion,x
@done:  rts

; Clamp a recalled portion down to a currently offered quantity. The
; selected source and all menu entries remain available to the player.
gr_recall:
        lda     mn_kind
        jmp     @quantity
@done:  rts
@quantity:
        ldx     #2
        cmp     #K_BOIL
        beq     @portion
        lda     mn_level
        cmp     #3
        bne     @done
        ldx     #0
        lda     gr_f
        cmp     #F_EAT
        beq     @portion
        cmp     #F_DRINK
        bne     @done
        inx
@portion:
        lda     menu_portion,x
        beq     @done
        ldy     #0
@find:  cmp     gr_size,y
        bcc     @found
        iny
        cpy     #gr_size_end-gr_size
        bcc     @find
@found: tya
        beq     @offset
        sec
        sbc     #1
@offset:
        cpx     #0
        bne     @clamp
        clc
        adc     #1              ; EAT keeps TASTE before the portions
@clamp: cmp     mn_count
        bcc     @select
        lda     mn_count
        sec
        sbc     #1
@select:sta     mn_cur
        rts

; gr_avail -- gr_cap = the ounces of menu_noun here (255: plenty): its pack
; stock (not in a hung pack) and its ground stock on this cell; a pile of
; lot 4 the same; WATER also a source (160 oz: water_pile), RAIN, SNOW 160.
gr_avail:
        lda     #0
        sta     gr_lo
        sta     gr_hi
        ldx     menu_noun
        cpx     #169
        bcs     @source         ; RAIN, SNOW
        cpx     #76
        bcs     @pile
        cpx     #N_WATER
        bne     @prov
        jsr     grid_water
        bcc     :+
@source:
        lda     #160
        jsr     @add
:       ldx     menu_noun
        cpx     #N_WATER
        bne     @cap
@prov:  lda     it_place,x
        cmp     #5
        beq     :+
        lda     it_pack_lo,x
        ldy     it_pack_hi,x
        jsr     @add_ay
:       jsr     at_ground
        bcc     @cap
        lda     it_gnd_lo,x
        ldy     it_gnd_hi,x
        jsr     @add_ay
        jmp     @cap
@pile:  lda     #FG_HIDE
        cpx     #94
        beq     :+
        txa
        sec
        sbc     #76
:       tax
        lda     fg_pl,x
        ldy     fg_ph,x
        jsr     @add_ay
        lda     fg_gl,x
        ldy     fg_gh,x
        jsr     @add_ay
@cap:   lda     gr_lo
        ldy     gr_hi
        beq     :+
        lda     #255
:       sta     gr_cap
        rts
@add:   ldy     #0
@add_ay:
        clc
        adc     gr_lo
        sta     gr_lo
        tya
        adc     gr_hi
        sta     gr_hi
        rts

; USE x: STOVE wants FUEL and MATCHES (or the fire) in use first; the
; FRSTAID KIT in the dark, the flashlight (camp.s use_stove, care.s).
gr_use:
        jsr     q_clear
        jsr     q_use_prepare
        lda     #S_CRAFT_USE
        jmp     q_last

; Shared by the grid and both object pages. Only called after validation.
; The selected tool remains explicit; auxiliary tools are prepared here.
q_use_prepare:
        lda     menu_noun
        cmp     #71
        bne     @kit
        lda     #S_FUEL
        jsr     q_add
        lda     fire_near
        bne     @done
        lda     #S_MATCH
        jmp     q_add
@kit:   cmp     #41
        beq     gr_flash
        cmp     #67
        beq     @bait
        cmp     #72
        bne     @done
@bait:  lda     #S_BAIT
        jmp     q_add
@done:  rts

; Entered through a stack trampoline after STATUS has been replaced by GRID.
; Non-USE commands retain their precise source and quantity in inbuf.
module_object_use:
        jsr     menu_gather     ; page rendering replaced the menu string helpers
        lda     menu_noun
        sta     mq_noun
        jsr     q_clear
        lda     inbuf
        cmp     #'U'
        bne     @ordinary
        jsr     q_use_prepare
        lda     #S_CRAFT_USE
        jsr     q_add
        lda     pg_cur
        cmp     #PG_EQUIPMENT
        lda     #S_OBJECTS
        bcc     :+
        lda     #S_EQUIPMENT
:       jsr     q_add
        jsr     q_start
        jmp     obj_type
@ordinary:
        lda     pg_cur
        cmp     #PG_EQUIPMENT
        lda     #S_OBJECTS
        bcc     :+
        lda     #S_EQUIPMENT
:       sta     mq_list
        sta     mq_list+1
        lda     #2
        sta     mq_n
        lsr     a
        sta     mq_i
        lda     journey_encounters
        sta     mq_enc
        jmp     obj_type
; gr_flash -- (the kit, the MEDICAL page) USE FLASHLIGHT when it is dark and
; the flashlight is here.
gr_flash:
        lda     light
        bne     :+
        ldx     #66
        jsr     have
        bcc     :+
        lda     #S_FLASH
        jmp     q_add
:       rts

; KILL x (GAME, FISH): the best weapon first (frg.s fr_hunt: GUN, BOW,
; SPEAR, then AXE or KNIFE in use; lot 3), unless one is in use already
; (the CLUB or the ROCK too: means 17, the player's choice). The CLUB and
; the ROCK are never proposed: by day p = -.1 (never), at night 0.
gr_kill:
        jsr     q_clear
        lda     fg_use
        and     #FT_BOW|FT_SPEAR|FT_CLUB
        bne     @kill
        lda     camp_use
        and     #U_GUN
        bne     @kill
        lda     #11             ; AXE/KNIFE only count on their activation cell
        sta     gr_t
        jsr     q_check
        bcs     @kill
        inc     gr_t
        jsr     q_check
        bcs     @kill
        ldy     #S_GUN
        ldx     #57
        jsr     mk_stock        ; (menu.s: here, with a shot left)
        bcs     @use
        ldx     #89             ; the BOW, the SPEAR here or carried
        jsr     gr_where
        ldy     #S_BOW
        cmp     #$FF
        bne     @use
        inx
        jsr     gr_where
        ldy     #S_SPEAR
        cmp     #$FF
        bne     @use
        ldy     #S_AXE
        ldx     #58
        jsr     have
        bcs     @use
        iny
        ldx     #59
        jsr     have
        bcc     @kill
@use:   tya
        jsr     q_add
@kill:  jmp     gr_hunt_review
module_hunt_go:
        lda     #S_KILL
        jmp     q_last

; Tail-call through SITES: NAVIGATION may overwrite GRID. The untouched
; queue is a proposal until review returns via hunt_execute.
gr_hunt_review:
        lda     #10
        jsr     overlay_load
        jmp     hunt_open
; CATCH x: the bait, then the TRAP (GAME) or the FISHNG GEAR (FISH).
gr_catch:
        jsr     gr_with_name
        ldx     #<list_dur
        ldy     #>list_dur
        jmp     gr_strings
gr_catch_queue:
        lda     mn_cur
        sta     MQ_CATCH_DUR    ; survives loading each prerequisite
        jsr     q_clear
        lda     #S_BAIT
        jsr     q_add
        ldy     #S_TRAP
        ldx     #72
        lda     menu_noun
        cmp     #80
        beq     :+
        iny
        ldx     #67
:       jsr     have
        bcc     :+
        tya
        jsr     q_add
:       lda     #S_CATCH
        jmp     q_last

; MAKE FIRE: FUEL in rain or wind (not in the cabin), a match, the fire,
; then USE FIRE when the air is cold (below 50 F felt: never in heat, it
; would saturate).
gr_mkfire:
        jsr     q_clear
        jsr     camp_storm
        bcc     :+
        lda     shelter_inside
        bne     :+
        lda     #S_FUEL
        jsr     q_add
:       lda     #S_MATCH
        jsr     q_add
        lda     #S_MKFIRE
        jsr     q_add
        lda     felt_temp+1
        bmi     :+
        bne     q_start
        lda     felt_temp
        cmp     #50
        bcs     q_start
:       lda     #S_UFIRE
        jmp     q_last
; MAKE WATER: the GND COVER (or the RAINCOAT) in use first.
gr_mkwater:
        jsr     q_clear
        ldy     #S_COVER
        ldx     #11
        jsr     have
        bcs     :+
        iny
:       tya
        jsr     q_add
        lda     #S_MKWAT
        jmp     q_last

; ----------------------------------------------------------------------------
; the queue
; ----------------------------------------------------------------------------
q_clear:
        lda     #0
        sta     mq_n
        sta     mq_i
        rts
q_add:  ldx     mq_n
        sta     mq_list,x
        inc     mq_n
        rts
; q_last -- the last step A, then the queue starts: its first step (one
; already done is skipped) is typed now.
q_last: jsr     q_add
q_start:
        lda     journey_encounters
        sta     mq_enc
        jmp     q_next

; module_queue -- (get_line, mq_n set) the step that ran: a new encounter
; (an animal accepted, fauna_alert) ends the queue; its check decides
; (POST: ends when it fails; INV: ends when it holds); then the next step.
module_queue:
        lda     journey_encounters
        cmp     mq_enc
        jne     q_stop
        ldx     mq_i
        lda     mq_list-1,x
        jsr     q_step
        and     #Q_POST|Q_INV
        beq     q_next
        jsr     q_check
        bit     gr_t
        bvc     :+
        jcc     q_stop          ; POST: failed
:       bvs     q_next
        jcs     q_stop          ; INV: done, the fallback is not needed
q_next: ldx     mq_i
        cpx     mq_n
        jcs     q_stop
        inc     mq_i
        lda     mq_list,x
        cmp     #S_CARE_RETURN
        jeq     q_care_return
        cmp     #S_CRAFT_RETURN
        jeq     q_craft_return
        cmp     #S_DEPARTURE_RETURN
        jeq     q_departure_return
        jsr     q_step
        bpl     q_type
        jsr     q_check
        bcs     q_next          ; PRE: done already
; q_type -- the step at gp2 (after its flags) in inbuf: its text, its noun
; (or mq_noun and its name), then its portion/duration; the last step
; leaves no queue.
q_type: lda     #0
        sta     linelen
        ldy     #1
        lda     (gp2),y
        sta     gr_x
        bne     :+
        lda     mq_noun
:       sta     menu_noun
        lda     gp2
        clc
        adc     #2
        sta     gp2
        bcc     :+
        inc     gp2+1
:       jsr     append_str
        lda     gr_x
        bne     :+
        lda     mq_noun
        jsr     gr_name_of
:       lda     gr_t            ; BOIL: list_qty[mq_noun]; CATCH: its duration
        and     #Q_SIZE
        beq     @last
        ldx     mq_i
        lda     mq_list-1,x
        cmp     #S_CATCH
        beq     @duration
        lda     #<list_qty
        sta     gp2
        lda     #>list_qty
        ldx     mq_noun
        jmp     @size
@duration:
        lda     #<list_dur
        sta     gp2
        lda     #>list_dur
        ldx     MQ_CATCH_DUR
@size:  sta     gp2+1
:       dex
        bmi     :+
        jsr     skip_str
        jmp     :-
:       jsr     append_space
        jsr     append_str
@last:  ldx     mq_i
        cpx     mq_n
        bcc     :+
        lda     #0
        sta     mq_n
:       jmp     done            ; (the grid or the typed line, as it began)
q_stop: lda     journey_encounters
        cmp     mq_enc
        bne     @clear
        ldx     mq_n
        beq     @clear
        dex
        lda     mq_list,x
        cmp     #S_CARE_RETURN
        jeq     q_care_return    ; preparation failed: show refusal, skip the care
        cmp     #S_CRAFT_RETURN
        jeq     q_craft_return
        cmp     #S_DEPARTURE_RETURN
        jeq     q_departure_return
        cmp     #S_OBJECTS
        beq     @page
        cmp     #S_EQUIPMENT
        beq     @page
@clear: lda     #0
        sta     mq_n
        jmp     get_line_body
@page:  pha
        lda     #0
        sta     mq_n
        pla
        jsr     q_step
        jmp     q_type

; q_step -- A = step: gp2 = its entry, A = gr_t = its flags (N = Q_PRE).
q_step: tax
        lda     #<gr_steps
        sta     gp2
        lda     #>gr_steps
        sta     gp2+1
@find:  dex
        bmi     @at
        lda     gp2             ; past the flags and the noun, then the text
        clc
        adc     #2
        sta     gp2
        bcc     :+
        inc     gp2+1
:       jsr     skip_str
        jmp     @find
@at:    ldy     #0
        lda     (gp2),y
        sta     gr_t
        rts

; q_check -- C set when the check of the step (gr_t's low bits) holds: its
; flag (Q_* codes 1-13 and 15, a crafted weapon in use: address, mask), or
; 14: mq_noun is in the pack.
q_check:
        lda     gr_t
        and     #$0F
        tax
        cpx     #14
        beq     @pack
        cpx     #11
        beq     @tool_cell
        cpx     #12
        bne     @flag_address
@tool_cell:
        lda     care_tool_x
        cmp     px+1
        bne     @not_here
        lda     care_tool_y
        cmp     py+1
        beq     @flag_address
@not_here:
        clc
        rts
@flag_address:
        lda     q_chk_lo-1,x
        sta     @flag+1
        lda     q_chk_hi-1,x
        sta     @flag+2
        lda     q_chk_mask-1,x
@flag:  and     $FFFF
        cmp     #1
        rts
@pack:  ldx     mq_noun
        lda     it_place,x
        cmp     #2
        beq     :+
        cmp     #4
        beq     :+
        clc
        rts
:       sec
        rts
q_chk_lo:   .byte <camp_use, <camp_use, <fire_on, <fire_near, <camp_use, <camp_use
            .byte <fg_bait, <fg_use, <fg_use, <camp_use, <care_tools, <care_tools, <camp_use, 0, <fg_use
q_chk_hi:   .byte >camp_use, >camp_use, >fire_on, >fire_near, >camp_use, >camp_use
            .byte >fg_bait, >fg_use, >fg_use, >camp_use, >care_tools, >care_tools, >camp_use, 0, >fg_use
q_chk_mask: .byte U_FUEL, U_MATCH, $FF, $FF, U_COVER, U_UTENS
            .byte $FF, FT_TRAP, FT_GEAR, U_GUN, 1, 2, U_FLASH, 0, FT_BOW|FT_SPEAR
; The steps: flags | check, noun (0: mq_noun), text (the keyboard's).
gr_steps:
        .byte   Q_PRE|Q_POST|1, 40, "USE FUEL", 0                ; S_FUEL
        .byte   Q_PRE|Q_POST|2, 38, "USE MATCHES", 0             ; S_MATCH
        .byte   Q_POST|3, 88, "MAKE FIRE", 0                     ; S_MKFIRE
        .byte   Q_PRE|4, 88, "USE FIRE", 0                       ; S_UFIRE
        .byte   Q_PRE|Q_POST|5, 11, "USE GND COVER", 0           ; S_COVER
        .byte   Q_PRE|Q_POST|5, 12, "USE RAINCOAT", 0            ; S_RAINC
        .byte   0, N_WATER, "MAKE WATER", 0                      ; S_MKWAT
        .byte   Q_PRE|Q_POST|6, 73, "USE UTENSILS", 0            ; S_UTENS
        .byte   Q_SIZE, N_WATER, "BOIL WATER", 0                 ; S_BOIL
        .byte   Q_PRE|Q_POST|7, 175, "USE BAIT", 0                      ; S_BAIT
        .byte   Q_PRE|Q_POST|8, 72, "USE TRAP", 0                ; S_TRAP
        .byte   Q_PRE|Q_POST|9, 67, "USE FISHNG GEAR", 0         ; S_GEAR
        .byte   Q_PRE|Q_POST|10, 57, "USE GUN", 0                ; S_GUN
        .byte   Q_PRE|Q_POST|11, 58, "USE AXE", 0                ; S_AXE
        .byte   Q_PRE|Q_POST|12, 59, "USE KNIFE", 0              ; S_KNIFE
        .byte   Q_PRE|Q_POST|13, 66, "USE FLASHLIGHT", 0         ; S_FLASH
        .byte   0, 71, "USE STOVE", 0                            ; S_STOVE
        .byte   0, 41, "USE FRSTAID KIT", 0                      ; S_KIT
        .byte   0, 158, "CUT BODY", 0                            ; S_CUT
        .byte   0, 0, "KILL", 0                                  ; S_KILL
        .byte   Q_SIZE, 0, "CATCH", 0                             ; S_CATCH (list_dur)
        .byte   Q_INV|14, 0, "PACK", 0                           ; S_PACK
        .byte   0, 0, "CARRY", 0                                 ; S_CARRY
        .byte   Q_PRE|Q_POST|15, 89, "USE BOW", 0                ; S_BOW
        .byte   Q_PRE|Q_POST|15, 90, "USE SPEAR", 0              ; S_SPEAR
        .byte   0, 106, "INVENTORY", 0                           ; S_OBJECTS
        .byte   0, 110, "EQUIPMENT", 0                           ; S_EQUIPMENT
        .byte   0, 106, "STATUS", 0                              ; S_CARE_RETURN
        .byte   0, 106, "STATUS", 0                              ; S_CRAFT_RETURN guard only
        .byte   0, 0, "USE", 0                                   ; S_CRAFT_USE
        .byte   0, 0, "MAKE", 0                                  ; S_CRAFT_MAKE
        .byte   0, 106, "STATUS", 0                              ; S_DEPARTURE_RETURN

; One already composed native command, then return to the optional checklist.
module_departure_queue:
        lda     #0
        sta     obj_keep
        lda     #S_DEPARTURE_RETURN
        sta     mq_list
        sta     mq_list+1
        lda     #2
        sta     mq_n
        lda     #1
        sta     mq_i
        lda     journey_encounters
        sta     mq_enc
        jmp     obj_type
q_departure_return:
        ; A callback comes from get_line, while the initial checklist came
        ; from do_command (typed STATUS and game-port UP both type STATUS).
        ; Resume with the latter return address: obj_type executes the next
        ; command itself; main must not execute its trimmed line a second time.
        pla
        pla
        lda     #>(main_command_done-1)
        pha
        lda     #<(main_command_done-1)
        pha
        lda     #10
        jsr     overlay_load
        jmp     departure_resume

; ----------------------------------------------------------------------------
; the lists of items
; ----------------------------------------------------------------------------
; gr_build -- the items of filter gr_f in overlay_text (mn_count): the
; sources of water first (GET, DRINK), then the ranges of gr_ranges for
; this filter (gr_ok), the worn clothes last (WEAR, bit 7), the fire last
; (USE).
gr_build:
        lda     #0
        sta     mn_count
        sta     gr_worn
        lda     gr_f
        cmp     #F_DRINK
        beq     :+
        cmp     #F_GET
        bne     @ranges
        ldx     #64             ; GET: into the canteen
        jsr     have
        bcc     @ranges
:       jsr     grid_water    ; a river, a lake or rain: WATER
        bcs     @water
        ldx     #N_WATER        ; DRINK: the canteen or the pile here
        lda     gr_f
        bne     :+
        jsr     member          ; GET: the pile here
        and     #G_GROUND
        bne     @water
        beq     @sky
:       jsr     have
        bcc     @sky
@water: lda     #N_WATER
        jsr     gr_put
@sky:   lda     weather_sky     ; RAIN, or SNOW falling or lying
        cmp     #2
        bne     :+
        lda     #169
        jsr     gr_put
:       cmp     #3
        beq     @snow
        jsr     level_here
        cmp     M_SNOW
        bcc     @ranges
@snow:  lda     #170
        jsr     gr_put
@ranges:
        ldx     gr_f
        ldy     gr_range_at,x
@range: lda     gr_ranges,y
        beq     @end
        sta     gr_x
        lda     gr_ranges+1,y
        sta     gr_hi
        iny
        iny
        sty     gr_lo
@item:  ldx     gr_x
        jsr     gr_ok
        bcc     :+
        lda     gr_x
        ora     gr_worn
        jsr     gr_put
:       inc     gr_x
        lda     gr_x
        cmp     gr_hi
        bcc     @item
        ldy     gr_lo
        lda     gr_f            ; WEAR: then the worn ones
        cmp     #F_WEAR
        bne     @range
        lda     gr_worn
        bne     @range
        lda     #$80
        sta     gr_worn
        dey
        dey
        bne     @range
@end:   lda     gr_f            ; USE: the fire last, while it burns
        cmp     #F_USE
        bne     :+
        lda     fire_on
        beq     :+
        lda     #N_FIRE
gr_put: ldy     mn_count
        sta     overlay_text,y
        inc     mn_count
:       rts
; Per filter, (first, last + 1) pairs, 0 ends: GET the piles before the
; items (WATER is a source), EAT the piles of food before the provisions
; and the remedies, COOK the piles and NUTS.
gr_range_at: .byte gr_r_get-gr_ranges, gr_r_wear-gr_ranges, gr_r_drop-gr_ranges
             .byte gr_r_eat-gr_ranges, gr_r_use-gr_ranges, gr_r_none-gr_ranges
             .byte gr_r_game-gr_ranges, gr_r_skin-gr_ranges, gr_r_game-gr_ranges
             .byte gr_r_cook-gr_ranges
gr_ranges:
gr_r_get:  .byte 76, 95, 1, N_WATER, N_WATER+1, 76
gr_r_none: .byte 0
gr_r_wear: .byte 2, 55, 0
gr_r_drop: .byte 1, 95, 0
gr_r_eat:  .byte 76, 87
gr_r_prov: .byte 23, 51, 0
gr_r_use:  .byte 9, 74, 89, 94, 0
gr_r_game: .byte 80, 82, 0
gr_r_skin: .byte 76, 81, 0
gr_r_cook: .byte 76, 87, 23, 24, 0

; gr_ok -- C set when item X belongs to the list of gr_f: the grid's test
; (menu.s item_ok) for GET, DROP, EAT, USE; WEAR: the clothes WEAR
; accepts, accessible, not worn (then worn: gr_worn); KILL, CATCH: GAME
; or FISH present; SKIN: a carcass to skin; COOK: a pile of food, NUTS.
gr_ok:  lda     gr_f
        sta     mn_t
        cmp     #F_WEAR
        beq     @wear
        cmp     #F_KILL
        bcc     @item
        cmp     #F_SKIN
        beq     @skin
        cmp     #F_COOK
        beq     @cook
        lda     fg_b2-76,x      ; GAME (80), FISH (81): present (0)
        bne     @no
        sec
        rts
@item:  cpx     #89             ; lot 3: BOW .. SPLINT, exactly
        bcc     @first
        cpx     #94
        bcc     @craft
@first: jmp     item_ok
@craft: jsr     gr_where
        ldy     gr_f
        beq     @get
        cmp     #$FF
        beq     @no
        cpy     #F_DROP
        bne     @yes            ; USE: here or carried
        cmp     #1              ; DROP: carried (1..3)
        rts
@get:   cmp     #1              ; GET: on this cell's ground
        bcs     @no
@yes:   sec
        rts
@cook:  jsr     member          ; (NUTS: any stock here)
        cmp     #1
        rts
@skin:  txa                     ; bit X - 76 of fg_skin (not FISH)
        sec
        sbc     #76
        tay
        lda     fg_skin
:       lsr     a
        dey
        bpl     :-
        rts
@wear:  cpx     #9              ; module_do_wear's clothes: 2-8, 12-20,
        bcc     :+              ; the sunglasses, the watch
        cpx     #12
        bcc     @no
        cpx     #21
        bcc     :+
        cpx     #43
        beq     :+
        cpx     #54
        bne     @no
:       jsr     member
        beq     @no
        and     #G_WORN
        beq     :+
        lda     #$80
:       eor     gr_worn         ; worn on the second pass only
        bne     @no
        sec
        rts
@no:    clc
        rts

; gr_where -- X = 89..93 (BOW, SPEAR, CLUB, ROCK, SPLINT): A = its place
; now, as CRAFT's cr_where once cr_here has settled the cell: $FF absent or
; on the ground of another cell, 0 on this one's, 1 worn, 2 pack, 3 hand;
; the CLUB left on the ground is lost once the player has left the cell, a
; ROCK not carried lies on every land cell (cr_still 0: not settled yet;
; water_bits, cached at the prompt). X kept.
gr_where:
        txa
        sec
        sbc     #89
        tay
        lda     cr_b1,y
        cpy     #3
        beq     @rock
        cmp     #0
        bne     @rts
        cpy     #2
        bne     @cell
        lda     cr_still
        beq     @away
        lda     #0
        rts
@cell:  cpy     #4
        bne     :+
        ldy     #2
:       lda     cr_cx,y
        cmp     px+1
        bne     @away
        lda     cr_cy,y
        cmp     py+1
        bne     @away
        lda     #0
        rts
@rock:  cmp     #2
        bcs     @rts            ; carried
        ldy     cr_still
        bne     @rts            ; settled: 0 here, $FF in the water
        lda     wb_bits
        and     #2
        beq     @rts            ; 0: on this land cell
@away:  lda     #$FF
@rts:   rts

append_space:                   ; (from MENUSWAP: the grid alone uses it)
        lda     #' '
        ldx     linelen
        cpx     #MAXLINE
        bcs     :+
        sta     inbuf,x
        inc     linelen
:       rts

; grid_item_name -- (text_of, the queue) gp2 = the display name of item X:
; the inventory's (76..79: the region's species, 12 letters at most; the
; second set; FIRE; RAIN, SNOW), after "-" when worn (bit 7, WEAR's list).
grid_item_name:
        ldy     #0
        cpx     #169
        jeq     @rain
        cpx     #170
        jeq     @snow
        txa
        bpl     :+
        and     #$7F
        tax
        lda     #'-'
        sta     gr_name
        iny
:       cpx     #76
        bcs     @set
        lda     it_name_lo,x
        sta     gp1
        lda     it_name_hi,x
        sta     gp1+1
        sty     gn_o            ; "2QT CANTEEN": CANTEEN (16 October 2026:
        ldy     #0              ; a digit makes the typed line a number for
        lda     (gp1),y         ; INPUT, "INVALID VALUE OR UNIT")
        cmp     #'9'+1
        bcs     @name
:       iny
        lda     (gp1),y
        cmp     #' '
        bne     :-
        tya                     ; (C set: past the space)
        adc     gp1
        sta     gp1
        bcc     @name
        inc     gp1+1
@name:  ldy     gn_o
        lda     gp1+1
@copy:  sta     gp1+1
        sty     gn_o
        ldy     #0
:       lda     (gp1),y
        beq     @end
        sty     gn_i
        ldy     gn_o
        sta     gr_name,y
        inc     gn_o
        ldy     gn_i
        iny
        cpy     #12
        bcc     :-
@end:   ldy     gn_o
        lda     #0
        sta     gr_name,y
        lda     #<gr_name
        sta     gp2
        lda     #>gr_name
        sta     gp2+1
        rts
@set:   cpx     #80             ; the species of the region: 12 x (X - 76)
        bcs     @second
        txa
        sbc     #76-1           ; (C clear)
        asl     a
        asl     a
        sta     gn_i
        asl     a
        adc     gn_i
        adc     #<region_species
        sta     gp1
        lda     #>region_species
        adc     #0
        bne     @copy
@rain:  lda     #<str_rain
        ldx     #>str_rain
        bne     @word
@snow:  lda     #<str_snow
        ldx     #>str_snow
        bne     @word
@second:
        lda     #<str_fire
        cpx     #N_FIRE
        beq     @lo
        lda     gr_second-80,x
        cpx     #94
        bne     @lo
        lda     #<str_hide
@lo:    ldx     #>str_fire
@word:  sta     gp1
        txa
        ldy     #0
        beq     @copy
; This trampoline fits the padding before the aligned names. The native
; INPUT/CAMP window at $5800 may still be live when a greyed verb is chosen.
gr_refusal_fetch:
        pha
        lda     #10
        jsr     overlay_load
        pla
        jmp     refusal_open
gr_quick_fetch:
        lda     #10
        jsr     overlay_load
        jmp     context_open
        .align $100            ; grid_item_name shares this page's high byte
str_fire:     .byte "FIRE", 0
str_game:     .byte "GAME", 0
str_fish:     .byte "FISH", 0
str_insects:  .byte "INSECTS", 0
str_fruit:    .byte "FRUIT", 0
str_cacti:    .byte "CACTI", 0
str_mushrooms: .byte "MUSHROOMS", 0
str_plants:   .byte "PLANTS", 0
str_hide:     .byte "HIDE", 0
str_bow:      .byte "BOW", 0
str_spear:    .byte "SPEAR", 0
str_club:     .byte "CLUB", 0
str_rock:     .byte "ROCK", 0
str_splint:   .byte "SPLINT", 0
str_hut:      .byte "HUT",0
str_igloo:    .byte "IGLOO",0
str_trench:   .byte "TRENCH",0
gr_second: .byte <str_game, <str_fish, <str_insects, <str_fruit, <str_cacti
           .byte <str_mushrooms, <str_plants, 0, 0
           .byte <str_bow, <str_spear, <str_club, <str_rock, <str_splint
           .byte <str_hide, <str_hut, <str_igloo, <str_trench
.assert >str_fire = >str_splint, error, "grid_item_name: one page for the second set"
str_rain:     .byte "RAIN", 0
str_snow:     .byte "SNOW", 0
str_tree:     .byte "TREE", 0
str_down:     .byte "DOWN", 0
str_taste:    .byte "TASTE", 0
; The string lists (the empty string ends one).
.pushseg
.segment "LOWTEXT"
list_dur:   .byte "10 MIN",0,"20 MIN",0,"30 MIN",0,"1 H",0,"2 H",0,"4 H",0,"8 H",0,0
list_look:  .byte "LEFT",0,"RIGHT",0,"BACK",0,"AHEAD",0,"UP",0,"DOWN",0,"NORTH",0,"EAST",0,"SOUTH",0,"WEST",0,"SUN",0,"STARS",0,"AZIMUTH",0,0
.popseg
list_make:  .byte "FIRE",0
list_water: .byte "WATER",0,0
list_taste: .byte "TASTE",0
list_qty:   .byte "1 OZ",0,"2 OZ",0,"4 OZ",0,"8 OZ",0,"12 OZ",0,"16 OZ",0,"24 OZ",0,"32 OZ",0,"48 OZ",0,0
.assert >list_taste = >list_qty, error, "gr_sizes: one high byte"
; Module state (fresh at each copy).
gr_f:    .byte 0                ; the item filter of the open verb
gr_t:    .byte 0
gr_x:    .byte 0
gr_lo:   .byte 0
gr_hi:   .byte 0
gr_cap:  .byte 0
gr_worn: .byte 0
gn_i:    .byte 0
gn_o:    .byte 0
gr_name: .res 14

; Preserve native feedback until the player acknowledges or stays in the view.
q_care_return:
        lda     #0
        sta     mq_n
        lda     #23
        sta     CV
        jsr     t_vtab
        lda     #41
        sta     CH
        jsr     puts
        .byte   "RETURN CARE  ESC VIEW",0
q_care_wait:
        jsr     wait_key
        cmp     #KC_ESC
        jeq     get_line_body
        cmp     #KC_RET
        beq     @open
        cmp     #' '
        bne     q_care_wait
@open:  ldx     #0
        ldy     #0
        sty     gr_f
@scan:  lda     injury_active,x
        beq     @next
        iny
        cpx     sr_condition
        bne     @next
        sty     gr_f
@next:  inx
        cpx     #13
        bcc     @scan
        lda     gr_f
        bne     @focus          ; still active: retain condition and gesture
        lda     #0
        sta     sr_gesture
        lda     sr_focus
        sty     gr_f
        cmp     gr_f
        bcc     @focus
        tya                     ; gone: nearest valid neighbour, or tab if none
@focus: ora     #$40
        sta     pg_open
        lda     #S_CARE_RETURN
        jsr     q_step
        jmp     q_type

; MAKE result remains visible. LEFT/RIGHT changes only the follow-up choice.
q_craft_return:
        lda     #0
        sta     mq_n
        sta     gr_f
q_craft_draw:
        lda     #23
        sta     CV
        jsr     t_vtab
        lda     #41
        sta     CH
        lda     gr_f
        beq     @recipes
        lda     mq_noun
        cmp     #95
        bcc     @objects
        jsr     puts
        .byte   "RETURN ENTER",0
        jmp     @keys
@objects:
        jsr     puts
        .byte   "RETURN OBJECTS",0
        jmp     @keys
@recipes:
        jsr     puts
        .byte   "RETURN RECIPES",0
@keys:  jsr     puts
        .byte   "  </>  ESC VIEW",0
        lda     #79
        jsr     tab
q_craft_wait:
        jsr     wait_key
        cmp     #KC_ESC
        beq     @view
        cmp     #KC_LEFT
        beq     @recipes_choice
        cmp     #KC_RIGHT
        beq     @product_choice
        cmp     #KC_RET
        beq     @open
        cmp     #' '
        bne     q_craft_wait
@open:  lda     gr_f
        bne     @product
        lda     cr_return_focus
        ora     #$80
        sta     cr_return_focus
        lda     #PG_CRAFT
        sta     pg_cur
        lda     #$FF
        sta     pg_open
        jmp     scr_status
@product:
        ldx     mq_noun
        cpx     #95
        bcs     @enter
        cpx     #89
        bcc     @gear
        jsr     gr_where
        bne     @carried
        beq     @local
@gear:  lda     it_place,x
        beq     @local
@carried:
        ldy     #1
        bne     @side
@local: ldy     #0
@side:  sty     obj_side
        txa
        sta     obj_selected,y
        lda     #$80
        sta     obj_keep
        jmp     scr_inventory
@enter: lda     #S_CRAFT_USE
        jsr     q_step
        jmp     q_type          ; explicit native USE, never replay MAKE
@recipes_choice:
        lda     #0
        beq     @choice
@product_choice:
        jsr     q_craft_available
        bcc     q_craft_wait
        lda     #1
@choice:sta     gr_f
        jmp     q_craft_draw
@view:  lda     #0
        sta     cr_return_focus
        jmp     get_line_body

; Only offer the product when it is reachable after native MAKE.
q_craft_available:
        ldx     mq_noun
        cpx     #95
        bcs     @shelter
        cpx     #89
        bcc     @gear
        jsr     gr_where
        cmp     #$FF
        bne     @yes
@no:    clc
        rts
@gear:  jmp     have
@shelter:
        txa
        sec
        sbc     #95
        tax
        lda     cr_sx,x
        cmp     px+1
        bne     @no
        lda     cr_sy,x
        cmp     py+1
        bne     @no
@yes:   sec
        rts

; CRAFT uses the same native preparation queue as object USE.
module_craft_prepare:
        jsr     menu_gather
        jsr     q_clear
        lda     mq_noun
        cmp     #95
        bcs     @axe
        cmp     #91
        beq     @make
        cmp     #58
        bcc     @make
        ldx     #59
        lda     #S_KNIFE
        bne     @tool
@axe:   ldx     #58
        lda     #S_AXE
@tool:  pha
        jsr     have
        pla
        bcc     @make
        jsr     q_add
@make:  lda     #S_CRAFT_MAKE
        jsr     q_add
        lda     #S_CRAFT_RETURN
        jsr     q_add
        jsr     q_start
        jmp     obj_type

; A useful context changes the initial verb once. Movement, cancellation and
; subsequent actions in that context keep the player's explicit choice. This
; routine only selects an offered verb: RETURN still follows native lists,
; quantities and confirmations. An animal never selects an attack implicitly.
module_context_focus:
        ldy     mn_count
        lda     #126
        sta     mn_idx,y
        inc     mn_count
        ; A reachable catch takes priority over resuming an interrupted
        ; journey. Packing it leaves that journey intact for the next prompt.
        ldx     #80             ; only an actual local catch, not live game
@catch: lda     fg_b2-76,x
        cmp     #1
        bne     @next
        jsr     member
        and     #G_GROUND
        bne     @get
@next:  inx
        cpx     #82
        bcc     @catch
        lda     travel_pending
        beq     @crossing
        cmp     #V_SWIM
        beq     @swim
        lda     #1              ; pending WALK and its native synonyms
        bne     @candidate
@crossing:
        lda     #0              ; offered SWIM means water here or ahead
        jsr     context_offered
        bcs     @swim
        lda     s_drink         ; native hours since drinking >= 4
        cmp     #$83
        bcc     @none
        lda     #6              ; DRINK must also have an offered source
        bne     @candidate
@get:   lda     #7
        bne     @candidate
@swim:  lda     #0
@candidate:
        jsr     context_offered
        bcc     @none
        tax
        inx                     ; zero remains the absence of a suggestion
        cpx     mn_anim
        stx     mn_anim
        beq     @done
        sta     mn_verb
@done:  rts
@none:  lda     #0
        sta     mn_anim
        rts
; A=verb_table identity. Greyed entries deliberately do not match.
context_offered:
        ldy     mn_count
@scan:  dey
        bmi     @no
        cmp     mn_idx,y
        bne     @scan
        sec
        rts
@no:    clc
        rts

; NAVIGATION returns one deliberate action; no follow-up runs implicitly.
module_flows_execute:
        cmp     #$FF
        beq     @cancel
        ldx     #0
@find:  cmp     mn_idx,x
        beq     @open
        inx
        cpx     mn_count
        bcc     @find
        jmp     gr_refusal_fetch ; A is still the requested verb identity
@open:  stx     mn_cur
        lda     #1
        sta     mn_mode
        jmp     module_select
@cancel:
        jmp     get_line_body

verb_of_cur:
        ldx     mn_cur
        lda     mn_idx,x
        and     #$7F
        sta     mn_verb
        rts

quick_label:
        lda     #<quick_text
        sta     gp2
        lda     #>quick_text
        sta     gp2+1
        rts
quick_text: .byte "QUICK",0

; GRID stays loaded throughout menu navigation: level1 fetches it before
; selecting the initial cell, and both callers run before a command starts.
; scroll_to_cur -- the three visible rows include the selected cell.
scroll_to_cur:
        lda     mn_cur
        ldx     #0
:       cmp     mn_cols
        bcc     :+
        sbc     mn_cols
        inx
        bne     :-
:       cpx     mn_top          ; X = row of the selection
        bcs     :+
        stx     mn_top
        rts
:       txa
        sec
        sbc     #MN_ROWS-1
        bcc     :+
        cmp     mn_top
        bcc     :+
        sta     mn_top
:       rts

module_hunt_execute:
        cmp     #0
        beq     @cancel
        cmp     #2
        beq     @craft
        lda     mq_n
        beq     @hunt
        lda     #$85
        jsr     hunt_arm
        jmp     q_start         ; activate once, then return to the review
@hunt: lda     #$86
        jsr     hunt_arm
        jmp     module_hunt_go
@craft:lda     #$85
        jsr     hunt_arm
        lda     #2
        jmp     hunter_result_fetch
@cancel:
        jsr     q_clear
        jmp     get_line_body
hunt_arm:
        sta     dep_running
        lda     mq_noun
        sta     dep_mask
        lda     journey_encounters
        sta     dep_cursor
        rts
module_hunt_again:
        jsr     q_clear
        lda     dep_mask
        sta     mq_noun
        sta     menu_noun
        jmp     gr_kill
hunter_result_fetch:
        pha
        lda     #10
        jsr     overlay_load
        pla
        jmp     hunter_result_execute
