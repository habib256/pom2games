; VERHILLE Arnaud — GPL-3.0. Read-only explanations for menu intentions.
; A = verb_table identity, including an intention absent from the live grid.
; Only UI scratch and registers change. Never run a command to discover a cause.
.segment "CAMPUI"
module_refusal:
        sta     refusal_verb
        cmp     #18
        jeq     refusal_boil
        cmp     #17
        jeq     refusal_cook
        cmp     #7
        jeq     refusal_get
        cmp     #2
        jcc     refusal_travel
        cmp     #5
        jeq     refusal_food
        cmp     #6
        jeq     refusal_water
        cmp     #16
        jeq     refusal_care
        cmp     #19
        jeq     refusal_skin
        cmp     #20
        jeq     refusal_game
        cmp     #21
        jeq     refusal_game
        jsr     puts_refusal
        .byte "NO ACCESSIBLE OBJECT FOR THIS ACTION.|CHECK OBJECTS AND EQUIPMENT.",0
        jmp     refusal_wait
refusal_boil:
        lda     fire_on
        bne     @utensils
        lda     camp_use
        and     #U_STOVE
        bne     @utensils
        jmp     refusal_prepare
@utensils:
        lda     camp_use
        and     #U_UTENS
        jeq     refusal_prepare
        ldx     #73
        jsr     have
        bcs     @water
        jsr     puts_refusal
        .byte "BOIL NEEDS ACCESSIBLE UTENSILS.|RECOVER UTENSILS; THEN CHOOSE BOIL.",0
        jmp     refusal_wait
@water: jsr     puts_refusal
        .byte "NO WATER STOCK AVAILABLE TO BOIL.|COLLECT OR MAKE WATER FIRST.",0
        jmp     refusal_wait
refusal_cook:
        lda     fire_on
        bne     refusal_food_cook
        lda     camp_use
        and     #U_STOVE
        bne     refusal_food_cook
        jmp     refusal_prepare
refusal_food_cook:
        jsr     puts_refusal
        .byte "NO FOOD STOCK AVAILABLE TO COOK.|RECOVER MEAT, FORAGE OR FIND NUTS.",0
        jmp     refusal_wait
refusal_food:
        jsr     puts_refusal
        .byte "NO ACCESSIBLE FOOD OR ORAL MEDICINE.|RECOVER FOOD OR LOWER HUNG FOOD.",0
        jmp     refusal_wait
refusal_water:
        jsr     puts_refusal
        .byte "NO ACCESSIBLE WATER SOURCE OR STOCK.|FIND WATER, MAKE WATER OR LOWER FOOD.",0
        jmp     refusal_wait
refusal_get:
        ldx     #64
        jsr     have
        bcs     @empty
        ; A missing canteen matters only if water actually exists here.
        lda     camp_untreated
        pha
        jsr     grid_water
        pla
        sta     camp_untreated
        bcc     @empty
        jsr     puts_refusal
        .byte "COLLECTING WATER NEEDS A CANTEEN.|RECOVER A CANTEEN, OR CHOOSE DRINK.",0
        jmp     refusal_wait
@empty: jsr     puts_refusal
        .byte "NOTHING ACCESSIBLE TO GET HERE.|FIND GROUND ITEMS OR LOWER HUNG FOOD.",0
        jmp     refusal_wait
refusal_care:
        jsr     puts_refusal
        .byte "NO ACTIVE CONDITION NEEDS CARE.|CHECK STATUS FOR HEALTH AND PROTECTION.",0
        jmp     refusal_wait
refusal_skin:
        jsr     puts_refusal
        .byte "NO UNSKINNED CARCASS AVAILABLE.|CATCH GAME; FISH CANNOT BE SKINNED.",0
        jmp     refusal_wait
refusal_game:
        jsr     puts_refusal
        .byte "NO LIVE GAME OR FISH AVAILABLE HERE.|SEARCH ANOTHER AREA.",0
        jmp     refusal_wait
refusal_travel:
        lda     night
        beq     @terrain
        jsr     puts_refusal
        .byte "TRAVEL IS REFUSED AT NIGHT.|REST OR WAIT FOR DAYLIGHT.",0
        jmp     refusal_wait
@terrain:
        lda     refusal_verb
        bne     @walk
        jsr     puts_refusal
        .byte "NO WATER HERE OR IN THE NEXT STEP.|CHOOSE WALK OR TURN TOWARD WATER.",0
        jmp     refusal_wait
@walk: jsr     puts_refusal
        .byte "WALK NEEDS DRY GROUND HERE AND AHEAD.|CHOOSE SWIM OR TURN TOWARD DRY LAND.",0
refusal_wait:
        jsr     puts_refusal_more
        .byte "|RETURN / ESC: VIEW",0
refusal_key:
        jsr     cg_view_key
        cmp     #KC_RET
        beq     @leave
        cmp     #KC_ESC
        bne     refusal_key
@leave: jmp     refusal_close

; Inline strings use the resident printer, not a simulation overlay.
puts_refusal:
        jsr     msg_begin
puts_refusal_more:
        pla
        sta     gp2
        pla
        sta     gp2+1
        ldy     #0
@char: inc     gp2
        bne     :+
        inc     gp2+1
:       lda     (gp2),y
        beq     @done
        cmp     #'|'
        beq     @newline
        ora     #$80
        jsr     msg_char
        jmp     @char
@newline:
        jsr     msg_newline
        jmp     @char
@done:  jsr     msg_flush
        lda     #1
        sta     shown
        lda     gp2+1
        pha
        lda     gp2
        pha
        rts
refusal_verb: .byte 0

; Finish any text output before restoring the preserved mixed DHGR picture.
; Calling wait_key after show_dhgr could reveal the stale text page again.
.pushseg
.segment "GUIDANCE"
guidance_view_key:
        jsr     text_finish
        jsr     show_dhgr
        jmp     keyboard_wait

.popseg

; CAMPUI keeps its own copy: GUIDANCE occupies the same SIM window.
cg_view_key:
        jsr     text_finish
        jsr     show_dhgr
        jmp     keyboard_wait

; There is no selected source yet: return to the native source form once ready.
refusal_prepare:
        ldx     #0
        lda     refusal_verb
        cmp     #17
        beq     @copy
        ldx     #5
@copy: ldy     #0
@char: lda     refusal_commands,x
        sta     inbuf,y
        beq     @ready
        inx
        iny
        bne     @char
@ready:sty     linelen
        lda     #0
        sta     menu_noun
        sta     obj_keep
        lda     refusal_verb
        jmp     module_campguide
refusal_commands: .byte "COOK",0,"BOIL WATER",0
