; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; frg.s -- the FORAGE module (lot 4, docs/FORAGE.md), directory entry 31
; ============================================================================
; Read from NEOWILD.BLK into the SIM window by forage_gate (src/forage.s) at
; each command of the lot, on both editions; runs at $9600 with SIM away, so
; it calls only resident code and INPUT (numbers, $5800): its own RND (the
; Lehmer generator of weather_random, the same seed), no load_totals. It
; prints its messages (the original's, msg n) and leaves the time of the
; action in camp_minutes, its effort in fg_eff (or s_metabolic with
; camp_act), a care selector in camp_med; forage_gate spends it.
;   CATCH/GET/FIND GAME|FISH  T0F/S07 $5B48 (TRAP or GEAR in use, hours)
;   KILL/ATTACK/DOUSE/CUT GAME|FISH  T0F/S07 $58DE (GUN, AXE or KNIFE)
;   SCARE GAME|FISH     msg 39
;   EAT, COOK           T12/S00 (NUTS, provisions, the wild foods),
;                       T11/S07 (meat, game, fish): source, spoilage,
;                       toxicity, detoxication, meal, salt
;   TASTE               T12/S08 $59D6
;   SKIN                T11/S07 $5848
;   PACK, DROP          T0D/S0F -> T0E/S02 (the second set, HIDE)
;   USE BAIT/TRAP/GEAR/GUN, IGNORE/FLAG/GET FOOD, CURE, the redirections
;   of T05/S00 ("PLEASE USE 'PACK' COMMAND"...)
; ============================================================================
.segment "FORAGE"
frg_main:
        lda     #0
        sta     fr_said
        sta     fr_fam
        sta     fr_k
        jsr     fr_default      ; noun 0: the grid's object
        ldx     noun
        cpx     #135
        jeq     fr_food_word
        cpx     #175
        jeq     fr_bait_word
        lda     verb
        cmp     #2
        bne     @class
        cpx     #57
        jeq     fr_use_gun
        cpx     #67
        jeq     fr_use_gear
        cpx     #72
        jeq     fr_use_trap
@class: jsr     fr_classify
        jsr     fr_available    ; T05/S00 $523F
        bcs     :+
        lda     #<c_m1
        ldx     #>c_m1
        jmp     fr_say
:       lda     verb            ; the redirections ($5408-$5478)
        cmp     #7              ; CARRY food, game, HIDE
        bne     :+
        lda     fr_fam
        bne     fr_use_pack
:       cmp     #1              ; GET/CATCH/FIND food or HIDE
        bne     :+
        lda     fr_fam
        cmp     #3
        beq     fr_use_pack
        cmp     #13
        beq     fr_use_pack
:       cmp     #9              ; BOIL, DRY food or game
        beq     :+
        cmp     #13
        bne     @verb
:       lda     fr_fam
        cmp     #3
        beq     fr_use_cook
        cmp     #11
        beq     fr_use_cook
        jmp     fr_sense
@verb:  ldx     #0
:       lda     fr_verbs,x
        beq     @none
        cmp     verb
        beq     @go
        inx
        bne     :-
@go:    lda     fr_verb_hi,x
        pha
        lda     fr_verb_lo,x
        pha
        rts
@none:  jmp     fr_sense
fr_use_pack:
        lda     #<fr_m_pack
        ldx     #>fr_m_pack
        jmp     fr_say
fr_use_cook:
        lda     #<fr_m_cook
        ldx     #>fr_m_cook
        jmp     fr_say
fr_verbs:   .byte 6, 8, 4, 11, 12, 15, 17, 18, 26, 31, 35, 1, 2, 0
fr_verb_lo: .byte <(fr_pack-1), <(fr_pack-1), <(fr_skin-1), <(fr_meal-1), <(fr_meal-1)
            .byte <(fr_cure-1), <(fr_attack-1), <(fr_attack-1), <(fr_attack-1)
            .byte <(fr_attack-1), <(fr_taste-1), <(fr_hunt-1), <(fr_use-1)
fr_verb_hi: .byte >(fr_pack-1), >(fr_pack-1), >(fr_skin-1), >(fr_meal-1), >(fr_meal-1)
            .byte >(fr_cure-1), >(fr_attack-1), >(fr_attack-1), >(fr_attack-1)
            .byte >(fr_attack-1), >(fr_taste-1), >(fr_hunt-1), >(fr_use-1)

; ---------------------------------------------------------------------------
; The object: noun -> family (3 food, 11 game, 13 HIDE), k, pile, record.
; ---------------------------------------------------------------------------
; fr_default -- noun 0 (CATCH, KILL, SKIN, COOK, TASTE of the grid): the
; first object the verb applies to (forage_cond chose the verb).
fr_default:
        lda     noun
        beq     :+
        rts
:       lda     verb
        cmp     #4
        beq     @skin
        cmp     #11
        beq     @food
        cmp     #35
        beq     @food
        lda     #80             ; CATCH, KILL: the game, else the fish
        ldx     fg_b2+4
        beq     :+
        lda     #81
:       jmp     fr_name
@skin:  ldx     #0
:       lda     fg_skin
        and     fg_bit,x
        bne     @pile
        inx
        cpx     #5
        bcc     :-
        rts
@food:  ldx     #0
:       lda     fg_gl,x
        ora     fg_gh,x
        ora     fg_pl,x
        ora     fg_ph,x
        bne     @pile
        inx
        cpx     #11
        bcc     :-
        lda     #23             ; NUTS
        jmp     fr_name
@pile:  cpx     #4              ; X = pile: GAME .. PLANTS by name,
        bcc     @animal         ; an animal by its region name
        txa
        clc
        adc     #76
        jmp     fr_name
@animal:
        txa                     ; region_species + 12 x
        asl     a
        asl     a
        sta     fr_t
        asl     a
        adc     fr_t
        tax
        ldy     #0
:       lda     region_species,x
        sta     nounbuf,y
        beq     :+
        inx
        iny
        cpy     #12
        bcc     :-
        lda     #0
        sta     nounbuf,y
:       lda     #76
        sta     noun
        rts
; fr_name -- noun A, its word in nounbuf (messages print ^ from it).
fr_name:
        sta     noun
        cmp     #76
        bcc     @rts            ; NUTS: the item name
        sec
        sbc     #80
        tax
        lda     fr_names_at,x
        tax
        ldy     #0
:       lda     fr_names,x
        sta     nounbuf,y
        beq     @rts
        inx
        iny
        bne     :-
@rts:   rts
fr_names: .byte "GAME",0,"FISH",0,"INSECTS",0,"FRUIT",0,"CACTI",0,"MUSHROOMS",0,"PLANTS",0
fr_names_at: .byte 0, 5, 10, 18, 24, 30, 40

; fr_classify -- fr_fam, fr_k, fr_j (pile), fr_q (record), fr_b1, fr_b2.
fr_classify:
        lda     #$FF
        sta     fr_q
        sta     fr_b2
        ldx     noun
        cpx     #38
        bcs     @second
        lda     #3              ; NUTS and the provisions (first set)
        sta     fr_fam
        cpx     #23
        bne     :+
        lda     #6
        sta     fr_q
:       jmp     fr_stock
@second:
        cpx     #94
        bne     :+
        lda     #13             ; HIDE
        sta     fr_fam
        lda     #19
        sta     fr_k
        lda     #FG_HIDE
        sta     fr_j
        jmp     fr_stock
:       cpx     #82             ; INSECTS .. PLANTS (82..86; the species
        bcc     :+              ; of the regions are 176 and above)
        cpx     #87
        bcs     :+
        lda     #3
        sta     fr_fam
        bne     @k
:       lda     #11
        sta     fr_fam
        cpx     #80             ; GAME, FISH (80, 81)
        bcc     :+
        cpx     #82
        bcc     @k
:       jsr     fr_animal       ; an animal of the region, by name
        bcs     :+
        lda     #0              ; none: absent everywhere
        sta     fr_k
        lda     #$FF
        sta     fr_b1
        rts
:       sta     fr_k
        bne     @pile
@k:     txa
        sec
        sbc     #75
        sta     fr_k
@pile:  ldx     fr_k
        dex
        stx     fr_j
        cpx     #6
        bcs     :+
        lda     fg_b2,x
        sta     fr_b2
:       cpx     #5              ; FISH .. PLANTS: their record
        bcc     :+
        txa
        sec
        sbc     #5
        sta     fr_q
:       cpx     #4              ; a live animal here: present (b2 = 0)
        bcs     fr_stock
        lda     fr_b2
        bpl     fr_stock
        lda     fr_j
        clc
        adc     #6
        cmp     animal_kind
        bne     fr_stock
        lda     animal_x
        cmp     px+1
        bne     fr_stock
        lda     animal_y
        cmp     py+1
        bne     fr_stock
        lda     #0
        sta     fr_b2
; fr_stock -- the pile's ounces: fr_gnd (here), fr_pk, and fr_b1.
fr_stock:
        lda     fr_fam
        cmp     #3
        bne     @second
        lda     fr_k
        bne     @second
        ldx     noun            ; provisions: the port's placement
        lda     #0
        sta     fr_pk
        sta     fr_pk+1
        sta     fr_gnd
        sta     fr_gnd+1
        lda     it_place,x
        cmp     #5              ; a hung pack is out of reach
        beq     :+
        lda     it_pack_lo,x
        sta     fr_pk
        lda     it_pack_hi,x
        sta     fr_pk+1
:       jsr     at_ground
        bcc     :+
        ldx     noun
        lda     it_gnd_lo,x
        sta     fr_gnd
        lda     it_gnd_hi,x
        sta     fr_gnd+1
:       lda     #0              ; b1: 1 ground, 2 pack -> $FF, 0, 2, 4
        sta     fr_t
        lda     fr_gnd
        ora     fr_gnd+1
        beq     :+
        inc     fr_t
:       lda     fr_pk
        ora     fr_pk+1
        beq     :+
        lda     fr_t
        ora     #2
        sta     fr_t
:       ldx     fr_t
        lda     fr_b1_of,x
        sta     fr_b1
        rts
@second:
        ldx     fr_j
        lda     fg_gl,x
        sta     fr_gnd
        lda     fg_gh,x
        sta     fr_gnd+1
        lda     fg_pl,x
        sta     fr_pk
        lda     fg_ph,x
        sta     fr_pk+1
        lda     fg_b1,x
        sta     fr_b1
        rts
fr_b1_of: .byte $FF, 0, 2, 4

; fr_animal -- C set when nounbuf names an animal of the region: A = its
; slot + 1 (k = 1..4).
fr_animal:
        ldx     #0              ; a carcass's own noun (synonyms: RATTLER)
:       lda     fg_n,x
        beq     :+
        cmp     noun
        beq     @slot
:       inx
        cpx     #4
        bcc     :--
        lda     #0              ; else by name: region_species, 4 x 12
        sta     fr_t
@name:  lda     fr_t
        asl     a
        asl     a
        sta     fr_u
        asl     a
        adc     fr_u
        tax
        ldy     #0
@char:  lda     nounbuf,y
        cmp     region_species,x
        bne     @next
        cmp     #0
        beq     @found
        inx
        iny
        cpy     #12
        bcc     @char
        lda     nounbuf,y
        beq     @found
@next:  inc     fr_t
        lda     fr_t
        cmp     region_count
        bcc     @name
        clc
        rts
@found: ldx     fr_t
@slot:  inx
        txa
        sec
        rts

; fr_available -- T05/S00 $523F: C clear when the object is not available
; (msg 1): an absent provision; a second-set object with no pile (b1 < 0)
; and no animal or game (b2 < 0), or a food with no pile.
fr_available:
        lda     fr_fam
        cmp     #3
        bne     :+
        lda     fr_k
        bne     :+
        ldx     noun            ; provisions: B1 < 0
        lda     it_place,x
        cmp     #$FF
        bne     @yes
        clc
        rts
:       lda     fr_b1
        bpl     @yes
        lda     fr_b2
        bmi     @no
        lda     noun
        cmp     #82
        bcc     @yes
@no:    clc
        rts
@yes:   sec
        rts

; ---------------------------------------------------------------------------
; Messages
; ---------------------------------------------------------------------------
; fr_say -- A/X a message (X = 0: a text of the bank): the first of the
; command replaces the result, the next ones follow it (camp_say's rule).
fr_say: ldy     fr_said
        inc     fr_said
        cpy     #0
        bne     :+
        jmp     message
:       cpx     #0
        bne     :+
        jsr     text_fetch
:       sta     gp1
        stx     gp1+1
        lda     #' '|$80
        jsr     msg_char
        jmp     message_body
fr_sense:
        lda     #<w_m2          ; msg 2
        ldx     #>w_m2
        jmp     fr_say
fr_ok:  lda     #<m_ok          ; msg 10
        ldx     #>m_ok
        jmp     fr_say
fr_already:
        lda     #<c_m11
        ldx     #>c_m11
        jmp     fr_say
fr_whatever:
        lda     #<fr_m18
        ldx     #>fr_m18
        jmp     fr_say
fr_mustkill:
        lda     #<fr_m38
        ldx     #>fr_m38
        jmp     fr_say
fr_unavailable:
        lda     #<c_m1
        ldx     #>c_m1
        jmp     fr_say

; ---------------------------------------------------------------------------
; Numbers
; ---------------------------------------------------------------------------
; fr_amount -- msg 32, a number of ounces (0 allowed) in fr_oz; C set:
; cancelled.
fr_amount:
        lda     #<fr_m32
        ldx     #>fr_m32
fr_amount_ax:                   ; (A/X: msg 31 then 32, fr_meal)
        ldy     #3              ; any 16-bit value, OZ accepted (src/input.s)
        jsr     number_entry
        lda     msgnum
        sta     fr_oz
        lda     msgnum+1
        sta     fr_oz+1
fr_asked:
        php
        lda     #0
        sta     fr_said
        plp
        rts

; fr_hours -- msg 27 and the original's reading of hours ($5CCF): digits
; and one decimal point (three decimals at most): minutes = INT(60 h + .5)
; with decimals, 60 h without; three integer digits or more, or h >= 25:
; "TOO LONG!" and again; a second point: a beep and again. fr_min; C set:
; cancelled (ESC).
fr_hours:
        lda     input_argument
        beq     @prompted
        lda     #<w_m27
        ldx     #>w_m27
        jsr     get_duration
        bcs     @inline_end
        jsr     prepare_minutes
        lda     minutes
        cmp     #<1500          ; same strict limit as the decimal reader: <25 h
        lda     minutes+1
        sbc     #>1500
        bcs     @inline_long
        lda     minutes
        sta     fr_min
        lda     minutes+1
        sta     fr_min+1
        clc
        jmp     fr_asked
@inline_long:
        lda     #<ol_long_msg
        ldx     #>ol_long_msg
        jsr     message
        sec
@inline_end:
        rts
@prompted:
        lda     #<fr_hour_hint
        ldx     #>fr_hour_hint
        jsr     message
@again: jsr     prompt
        ldx     #0
        stx     fr_t            ; length
        stx     fr_min          ; arrow entry is an exact number of minutes
        stx     fr_min+1
@key:   jsr     wait_key
        jsr     kbd_upcase
        cmp     #KC_ESC
        bne     :+
        lda     #<orient_cancel
        ldx     #>orient_cancel
        jsr     message
        sec
        jmp     fr_asked
:       cmp     #KC_UP
        jeq     @minute_up
        cmp     #KC_DOWN
        jeq     @minute_down
        cmp     #KC_RET
        beq     @parse
        cmp     #KC_LEFT
        bne     @char
        ldx     fr_t
        cpx     #$FF
        jeq     @clear
        cpx     #0
        beq     @key
        dec     fr_t
        dec     CH
        lda     #' '|$80
        jsr     COUT
        dec     CH
        jmp     @key
@char:  cmp     #'.'
        beq     :+
        cmp     #'0'
        bcc     @key
        cmp     #'9'+1
        bcs     @key
:       ldx     fr_t
        cpx     #$FF
        bne     :+
        pha
        jsr     fr_hour_prompt
        ldx     #0
        stx     fr_t
        pla
:       ldx     fr_t
        cpx     #8
        bcs     @key
        sta     fr_buf,x
        inc     fr_t
        ora     #$80
        jsr     COUT
        jmp     @key
@parse: ldx     fr_t
        cpx     #$FF
        bne     :+
        clc
        jmp     fr_asked        ; minute wheel bypasses decimal-hour parsing
:       lda     #0
        sta     FAC             ; h = 0
        sta     fr_u            ; integer digits
        sta     fr_dec          ; decimals ($80: the point seen)
        ldx     #0
@digit: cpx     fr_t
        beq     @value
        lda     fr_buf,x
        inx
        stx     fr_i
        cmp     #'.'
        bne     :+
        lda     fr_dec
        bmi     @beep
        lda     #$80
        sta     fr_dec
        bne     @next
:       and     #15
        sta     fr_d
        lda     fr_dec
        bpl     :+
        and     #$7F
        cmp     #3
        bcs     @next           ; a fourth decimal is ignored
        inc     fr_dec
        bne     @add
:       inc     fr_u
@add:   jsr     MUL10           ; h = 10 h + digit
        fst     fr_r
        ldy     fr_d
        lda     #0
        jsr     GIVAYF
        fop     FADD, fr_r
@next:  ldx     fr_i
        jmp     @digit
@beep:  jmp     @again          ; (the original beeps)
@value: lda     fr_u
        cmp     #3
        bcs     @long
        lda     fr_dec
        and     #$7F
        beq     :+
        sta     fr_i
@div:   jsr     DIV10           ; (uses X)
        dec     fr_i
        bne     @div
:       fst     fr_r
        fop     FCOMP, fr_25
        cmp     #$FF
        bne     @long
        fld     fr_r
        fop     FMULT, fr_60
        lda     fr_dec
        and     #$7F
        beq     :+
        fop     FADD, f_half
:       jsr     AYINT
        lda     $A1
        sta     fr_min
        lda     $A0
        sta     fr_min+1
        clc
        jmp     fr_asked
@long:  lda     #<ol_long_msg   ; "TOO LONG!"
        ldx     #>ol_long_msg
        jsr     message
        jmp     @again

@clear: jsr     fr_hour_prompt
        lda     #0
        sta     fr_t
        jmp     @key
@minute_up:
        lda     fr_min
        cmp     #<1499
        lda     fr_min+1
        sbc     #>1499
        bcs     @minute_draw
        inc     fr_min
        bne     @minute_draw
        inc     fr_min+1
        bne     @minute_draw
@minute_down:
        lda     fr_min
        ora     fr_min+1
        beq     @minute_draw
        lda     fr_min
        bne     :+
        dec     fr_min+1
:       dec     fr_min
@minute_draw:
        lda     #<fr_minute_hint
        ldx     #>fr_minute_hint
        jsr     message
        jsr     prompt
        lda     fr_min
        sta     num
        lda     fr_min+1
        sta     num+1
        jsr     print_u16
        lda     #$FF
        sta     fr_t
        jmp     @key
fr_minute_hint: .byte "TIME IN MINUTES: UP/DOWN, RETURN.",0
fr_hour_prompt:
        lda     #<fr_hour_hint
        ldx     #>fr_hour_hint
        jsr     message
        jmp     prompt
fr_hour_hint: .byte "SPECIFY TIME IN HOURS.|UP/DOWN: MINUTES. RETURN: CONFIRM.",0

; fr_source -- the pile eaten or cooked: b1 0 ground, 2 pack, 4 msg 71 (P
; or G); fr_src 0 ground, 1 pack, fr_av its ounces. C set: cancelled.
fr_source:
        lda     obj_keep
        bpl     :+
        lda     menu_noun
        cmp     noun
        bne     :+
        lda     obj_side
        bne     @pack
        beq     @ground
:       lda     fr_b1
        cmp     #2
        beq     @pack
        cmp     #4
        bne     @ground
        lda     #<fr_m71
        ldx     #>fr_m71
        jsr     message
        jsr     fr_choose_source
        cmp     #KC_ESC
        beq     @esc
        pha
        lda     #0
        sta     fr_said
        pla
        cmp     #'P'
        beq     @pack
@ground:
        lda     #0
        sta     fr_src
        lda     fr_gnd
        sta     fr_av
        lda     fr_gnd+1
        sta     fr_av+1
        clc
        rts
@pack:  lda     #1
        sta     fr_src
        lda     fr_pk
        sta     fr_av
        lda     fr_pk+1
        sta     fr_av+1
        clc
        rts
@esc:   lda     #<orient_cancel
        ldx     #>orient_cancel
        jsr     message
        sec
        rts

; fr_counter -- X = the spoilage counter of the chosen pile (fr_src):
; second set pack w11[k], ground w11[k+21] / w10[k+15]; NUTS and the
; provisions W11[n], their ground W11[n] (23..27) or W11[n+13] (28..37).
fr_counter:
        lda     fr_k
        beq     @first
        lda     fr_j
        ldx     fr_src
        bne     :+
        clc
        adc     #FG_CGND
:       tax
        rts
@first: lda     noun
        ldx     fr_src
        bne     @shared
        cmp     #28
        bcc     @shared
        clc
        adc     #FG_CPGND
        tax
        rts
@shared:
        sec
        sbc     #23-FG_CPROV
        tax
        rts
; fr_spoiled -- C set when counter X <= 0.
fr_spoiled:
        lda     fg_ch,x
        bmi     @yes
        ora     fg_cl,x
        beq     @yes
        clc
        rts
@yes:   sec
        rts

; fr_rnd -- FAC = RND: weather_random's generator (src/weather.s) on its
; seed, which SIM's copy shares.
fr_rnd: lda     #13
        sta     fr_i
@double:
        asl     weather_seed
        rol     weather_seed+1
        rol     weather_seed+2
        rol     weather_seed+3
        ldx     #3
@compare:
        lda     weather_seed,x
        cmp     fr_modulus,x
        bcc     @next
        bne     @subtract
        dex
        bpl     @compare
@subtract:
        sec
        ldx     #0
        ldy     #4
@sub:   lda     weather_seed,x
        sbc     fr_modulus,x
        sta     weather_seed,x
        inx
        dey
        bne     @sub
@next:  dec     fr_i
        bne     @double
        lda     #0
        sta     FAC
        fst     fr_r
        lda     #3
        sta     fr_u
@convert:
        fld     fr_r
        fop     FMULT, fr_256
        fst     fr_r
        ldx     fr_u
        ldy     weather_seed,x
        lda     #0
        jsr     GIVAYF
        fop     FADD, fr_r
        fst     fr_r
        dec     fr_u
        bpl     @convert
        fld     fr_modulus_float
        fop     FDIV, fr_r
        rts
.export fr_rnd
; fr_below -- (after fr_rnd) C set when FAC < the float at A/Y.
fr_below:
        jsr     FCOMP
        cmp     #$FF
        rts

; fr_mul -- fr_r = oz (fr_oz) x the byte A, as a float.
fr_mul: pha
        lda     fr_oz+1
        ldy     fr_oz
        jsr     GIVAYF
        fst     fr_r
        pla
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fr_r
        rts

; ---------------------------------------------------------------------------
; FOOD, BAIT, USE
; ---------------------------------------------------------------------------
fr_food_word:                   ; $520A, $5229
        lda     verb
        cmp     #35
        bne     :+
        lda     #<care_specific_message ; TASTE FOOD: msg 17
        ldx     #>care_specific_message
        jmp     fr_say
:       ldx     #1
        cmp     #37             ; IGNORE: 1, FLAG: 0 (msg 10)
        beq     :+
        dex
:       stx     fg_ignore
        cmp     #1
        jne     fr_ok
        lda     #<fr_m33        ; GET FOOD: msg 33
        ldx     #>fr_m33
        jmp     fr_say

fr_bait_word:                   ; T11/S00 $5DD4
        lda     verb
        cmp     #6
        beq     :+
        cmp     #12
        bne     @use
:       lda     #<c_m75         ; PACK, EAT BAIT: msg 75
        ldx     #>c_m75
        jmp     fr_say
@use:   lda     fg_ctx          ; woods or water here
        bne     @bait
        ldx     #37-23          ; or food carried ($4BE6)
:       lda     it_place+23,x
        cmp     #5
        beq     :+
        lda     it_pack_lo+23,x
        ora     it_pack_hi+23,x
        bne     @bait
:       dex
        bpl     :--
        ldx     #10
:       lda     fg_pl,x
        ora     fg_ph,x
        bne     @bait
        dex
        bpl     :-
        jmp     fr_unavailable
@bait:  lda     #1
        sta     fg_bait
        jmp     fr_ok

fr_use_trap:                    ; T11/S00 $5CEE: bait first (msg 84)
        lda     #FT_TRAP
        .byte   $2C
fr_use_gear:
        lda     #FT_GEAR
        sta     fr_t
        ldx     noun
        jsr     have
        jcc     fr_unavailable
        lda     fg_bait
        bne     :+
        lda     #<fr_m84
        ldx     #>fr_m84
        jmp     fr_say
:       lda     fr_t
        ora     fg_use
        sta     fg_use
        jmp     fr_ok

fr_use_gun:                     ; T11/S00 $5C42: in use, then in hand
        ldx     #57
        jsr     have
        jcc     fr_unavailable
        lda     #3
        sta     it_place+57
        lda     camp_use
        ora     #U_GUN
        sta     camp_use
        jmp     fr_ok

fr_use:                         ; USE food or game: msg 17
        lda     #<care_specific_message
        ldx     #>care_specific_message
        jmp     fr_say

fr_cure:                        ; CURE: food msg 18, animals msg 36
        lda     fr_fam
        cmp     #3
        jeq     fr_whatever
        cmp     #11
        jne     fr_sense
        lda     #<fr_m36
        ldx     #>fr_m36
        jmp     fr_say

; ---------------------------------------------------------------------------
; PACK, DROP (T0D/S0F -> T0E/S02): the second set and HIDE, no time.
; ---------------------------------------------------------------------------
fr_pack:
        lda     fr_k
        jeq     fr_sense
        lda     input_argument
        bne     @ask
        lda     verb            ; PACK (the grid's GET), 16 October 2026: no
        cmp     #8              ; question, the whole pile of the ground (the
        beq     @ask            ; piles weigh nothing: FORAGE.md 17.3)
        lda     fr_gnd
        sta     fr_oz
        lda     fr_gnd+1
        sta     fr_oz+1
        jmp     @amount
@ask:   jsr     fr_amount       ; DROP: the original's question
        bcc     @amount
        rts
@amount:
        lda     fr_oz
        ora     fr_oz+1
        jeq     fr_sense
        lda     verb
        cmp     #8
        beq     @sum_ground
        lda     fr_pk
        clc
        adc     fr_oz
        lda     fr_pk+1
        adc     fr_oz+1
        jmp     @sum_check
@sum_ground:
        lda     fr_gnd
        clc
        adc     fr_oz
        lda     fr_gnd+1
        adc     fr_oz+1
@sum_check:
        bcc     :+
        lda     #m_overflow
        ldx     #0
        jmp     fr_say
:       ldx     fr_j
        lda     verb
        cmp     #8
        beq     @drop
        lda     fr_gnd          ; PACK: at most the ground's (msg 64)
        sta     fr_av
        lda     fr_gnd+1
        sta     fr_av+1
        jsr     fr_exceeds
        bcc     :+
        rts
:       lda     fr_pk           ; the ground's record and counter copied
        ora     fr_pk+1         ; onto an empty pack pile (one that holds
        bne     :+              ; some keeps its own: ROM, 16 October 2026)
        jsr     fr_rec_gp
:       ldx     fr_j
        jsr     fr_ground_minus
        jsr     fr_pack_plus
@done:  ldx     fr_j
        jsr     fg_place
        lda     verb
        cmp     #8
        jeq     fr_ok
        lda     fr_oz           ; PACK: the ounces taken
        sta     msgnum
        lda     fr_oz+1
        sta     msgnum+1
        lda     #w_took
        ldx     #0
        jmp     fr_say
@drop:  lda     fr_pk           ; DROP: the ground's record is kept, but
        sta     fr_av           ; an empty ground pile takes the pack's
        lda     fr_pk+1
        sta     fr_av+1
        jsr     fr_exceeds
        bcc     :+
        rts
:       lda     fr_gnd
        ora     fr_gnd+1
        bne     :+
        jsr     fr_rec_pg
:       ldx     fr_j
        jsr     fr_pack_minus
        jsr     fr_ground_plus
        jmp     @done

; fr_rec_gp, fr_rec_pg -- the record (taste, code, percent: fr_q's) and the
; spoilage counter (fr_j's, the wild foods) of the ground's pile onto the
; pack's, or back.
fr_rec_gp:
        ldy     fr_q
        bmi     :+
        lda     fg_gt,y
        sta     fg_pt,y
        lda     fg_gx,y
        sta     fg_px,y
        lda     fg_gp,y
        sta     fg_pp,y
:       lda     fr_k
        cmp     #12
        bcs     :+
        ldy     fr_j
        lda     fg_cl+FG_CGND,y
        sta     fg_cl+FG_CPACK,y
        lda     fg_ch+FG_CGND,y
        sta     fg_ch+FG_CPACK,y
:       rts
fr_rec_pg:
        ldy     fr_q
        bmi     :+
        lda     fg_pt,y
        sta     fg_gt,y
        lda     fg_px,y
        sta     fg_gx,y
        lda     fg_pp,y
        sta     fg_gp,y
:       lda     fr_k
        cmp     #12
        bcs     :+
        ldy     fr_j
        lda     fg_cl+FG_CPACK,y
        sta     fg_cl+FG_CGND,y
        lda     fg_ch+FG_CPACK,y
        sta     fg_ch+FG_CGND,y
:       rts

; fr_exceeds -- C set (msg 64 printed) when fr_oz > fr_av.
fr_exceeds:
        lda     fr_av
        cmp     fr_oz
        lda     fr_av+1
        sbc     fr_oz+1
        bcs     :+
        lda     fr_av
        sta     msgnum
        lda     fr_av+1
        sta     msgnum+1
        lda     #<w_m64
        ldx     #>w_m64
        jsr     fr_say
        sec
        rts
:       clc
        rts

; Pile X (second set) +/- fr_oz.
fr_ground_minus:
        sec
        lda     fg_gl,x
        sbc     fr_oz
        sta     fg_gl,x
        lda     fg_gh,x
        sbc     fr_oz+1
        sta     fg_gh,x
        rts
fr_ground_plus:
        clc
        lda     fg_gl,x
        adc     fr_oz
        sta     fg_gl,x
        lda     fg_gh,x
        adc     fr_oz+1
        sta     fg_gh,x
        rts
fr_pack_minus:
        sec
        lda     fg_pl,x
        sbc     fr_oz
        sta     fg_pl,x
        lda     fg_ph,x
        sbc     fr_oz+1
        sta     fg_ph,x
        rts
fr_pack_plus:
        clc
        lda     fg_pl,x
        adc     fr_oz
        sta     fg_pl,x
        lda     fg_ph,x
        adc     fr_oz+1
        sta     fg_ph,x
        rts

; ---------------------------------------------------------------------------
; TASTE/SAMPLE (T12/S08 $59D6): no time, no draw.
; ---------------------------------------------------------------------------
fr_taste:
        lda     fr_fam
        cmp     #11
        beq     @eat
        cmp     #3
        jne     fr_sense
        lda     fr_b1           ; food: from where
        bpl     :+
        jmp     fr_unavailable
:       jsr     fr_source
        bcc     @taste
        rts
@eat:   lda     fr_b1           ; meat, game, fish: killed first
        bpl     :+
        jmp     fr_mustkill
:       jsr     fr_source
        bcc     @taste
        rts
@taste: jsr     fr_counter
        jsr     fr_spoiled
        bcc     :+
        lda     #<fr_m124
        ldx     #>fr_m124
        jmp     fr_say
:       ldx     fr_q            ; the taste of NUTS and the wild foods
        bmi     @okay
        lda     fr_fam
        cmp     #11             ; (FISH: its spoilage only)
        beq     @okay
        lda     fg_gt,x
        ldy     fr_src
        beq     :+
        lda     fg_pt,x
:       cmp     #8
        bcc     :+
        lda     #8
:       tax
        lda     fr_taste_lo,x
        pha
        lda     fr_taste_hi,x
        tax
        pla
        jmp     fr_say
@okay:  lda     #<fr_m123
        ldx     #>fr_m123
        jmp     fr_say
fr_taste_lo: .byte <fr_m123, <fr_m125, <fr_m126, <fr_m93, <fr_m94, <fr_m47, <fr_m89, <fr_m183, <fr_m184
fr_taste_hi: .byte >fr_m123, >fr_m125, >fr_m126, >fr_m93, >fr_m94, >fr_m47, >fr_m89, >fr_m183, >fr_m184

; ---------------------------------------------------------------------------
; EAT and COOK (T12/S00 food, T11/S07 meat, game, fish).
; ---------------------------------------------------------------------------
fr_meal:
        lda     fr_fam
        cmp     #13
        bne     :+
        lda     verb            ; HIDE: EAT msg 3, COOK msg 2
        cmp     #12
        jne     fr_sense
        lda     #<fr_m3
        ldx     #>fr_m3
        jmp     fr_say
:       lda     verb
        cmp     #11
        bne     @total
        lda     fire_on         ; COOK: a fire here or the stove in use (msg 65)
        bne     @total
        lda     camp_use
        and     #U_STOVE
        bne     @total
        lda     #<w_m65
        ldx     #>w_m65
        jmp     fr_say
@total: lda     fr_gnd          ; nothing to eat: T12 msg 1, T11 msg 38
        ora     fr_gnd+1
        ora     fr_pk
        ora     fr_pk+1
        bne     :+
        lda     fr_fam
        cmp     #11
        jeq     fr_mustkill
        jmp     fr_unavailable
:       lda     verb
        cmp     #12
        bne     @amount
        lda     fr_fam          ; EAT food: msg 31 when starving ($48A9 < 95)
        cmp     #3              ; or not fed for 12 hours (A2[17])
        bne     @amount
        lda     al_last+16
        cmp     #95
        bcc     @hungry
        fld     s_eat
        fop     FCOMP, fr_12
        cmp     #1
        bne     @amount
@hungry:
        lda     #<fr_m31        ; msg 31, then the question (msg 32)
        ldx     #>fr_m31
        jsr     fr_amount_ax
        jmp     @asked
@amount:
        jsr     fr_amount
@asked: bcc     :+
        rts
:       lda     fr_oz
        ora     fr_oz+1
        jeq     fr_sense
        ldx     #0              ; limits: EAT 48, COOK 288 (T12) or 848 (T11)
        lda     verb
        cmp     #12
        beq     :+
        inx
        lda     fr_fam
        cmp     #11
        bne     :+
        inx
:       lda     fr_lim_lo,x
        cmp     fr_oz
        lda     fr_lim_hi,x
        sbc     fr_oz+1
        bcs     :+
        lda     #<m_ridiculous
        ldx     #>m_ridiculous
        jmp     fr_say
:       jsr     fr_source
        bcc     :+
        rts
:       jsr     fr_exceeds
        bcc     :+
        rts
:       lda     verb
        cmp     #11
        jeq     fr_cook
; EAT: 2 minutes an ounce at 1.65 + .004 x the body's pounds.
        lda     fr_oz
        asl     a
        sta     camp_minutes
        lda     #0
        rol     a
        sta     camp_minutes+1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, fr_0_004
        fop     FADD, f_rest_rate
        fst     s_metabolic
        lda     #6
        sta     camp_act
        lda     #1              ; T0A/S05's first pass of the activity
        sta     resource_retention_due
        jsr     fr_counter      ; spoiled: RND >= .5 poisons ($5ADE)
        jsr     fr_spoiled
        bcc     @toxic
        jsr     fr_rnd
        lda     #<f_half
        ldy     #>f_half
        jsr     fr_below
        jcs     @meal
        jcc     @poison
@toxic: ldx     fr_q            ; NUTS, FISH and the wild foods
        jmi     @meal
        lda     fr_src
        bne     :+
        lda     fg_gx,x         ; ground: W10[i], W11[i]
        ldy     fg_gp,x
        jmp     @code
:       lda     fg_px,x         ; pack: b3[k], w9[k+15] (NUTS: W11[70])
        ldy     fg_pp,x
        cpx     #6
        bne     @code
        ldy     fg_gp,x
@code:  cmp     #0
        jeq     @meal           ; code 0: no draw
        sta     fr_code
        lda     #0              ; p = percent / 100
        jsr     GIVAYF
        fst     fr_p
        fld     f_100
        fop     FDIV, fr_p
        fst     fr_p
        lda     fr_code
        cmp     #3
        bne     @draw
        lda     M_LAT           ; code 3: x (1 - |lat| / 64)
        bpl     :+
        eor     #$FF
        clc
        adc     #1
:       tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fr_inv64
        fop     FSUB, f_one
        fop     FMULT, fr_p
        fst     fr_p
@draw:  jsr     fr_rnd
        lda     #<fr_p
        ldy     #>fr_p
        jsr     fr_below
        bcc     @meal
@poison:                        ; $5C90: condition 11 starts again, no food
        ldx     #10
        lda     #0
        sta     injury_prevented,x
        sta     injury_treated,x
        lda     #1
        sta     injury_active,x
        ldy     #4
:       lda     s_elap,y
        sta     injury_since+50,y
        dey
        bpl     :-
        jmp     fr_eaten
@meal:  jsr     fr_kpo          ; kcal = oz x kcal per ounce ($5CA6)
        jsr     fr_mul
        fst     fr_r
        fop     FADD, s_eaten
        fst     s_eaten
        fld     fr_r            ; A1[23] -= .8 kcal / body weight
        fop     FMULT, fr_0_8
        fst     fr_r
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FDIV, fr_r
        fop     FSUB, s_deff
        fst     s_deff
        jsr     fr_water        ; A1[22] -= oz x water % x .38 x .007
        jsr     fr_mul
        fop     FMULT, fr_0_007
        fop     FMULT, f_oz_hour
        fop     FSUB, s_defw
        fst     s_defw
        ldy     camp_minutes    ; A1[17] = elapsed + .017 x minutes
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fr_0_017
        fop     FADD, s_elap
        fst     s_last+5
        fld     f_zero          ; A2[17] (src/survival.s module_meal_prepare)
        fst     s_eat
        lda     noun            ; salt: NUTS, BACON, BOLOGNA, meat (not fish)
        cmp     #23
        beq     @salt
        cmp     #26
        beq     @salt
        cmp     #33
        beq     @salt
        lda     fr_fam
        cmp     #11
        bne     fr_eaten
        lda     fr_k
        cmp     #6
        beq     fr_eaten
@salt:  lda     #25             ; care selector 25, W($4A4A) -= 200
        sta     camp_med
        sec
        lda     exposure_counter
        sbc     #<200
        sta     exposure_counter
        lda     exposure_counter+1
        sbc     #>200
        sta     exposure_counter+1
fr_eaten:                       ; T0E/S02: the ounces off the pile
        jsr     fr_off
        jmp     fr_ok

; fr_off -- fr_oz off the chosen pile (fr_src), b1 again.
fr_off: lda     fr_k
        beq     @first
        ldx     fr_j
        lda     fr_src
        bne     :+
        jsr     fr_ground_minus
        jmp     fg_place
:       jsr     fr_pack_minus
        jmp     fg_place
@first: ldx     noun            ; provisions: ground or pack, and the total
        lda     fr_src
        bne     :+
        sec
        lda     it_gnd_lo,x
        sbc     fr_oz
        sta     it_gnd_lo,x
        lda     it_gnd_hi,x
        sbc     fr_oz+1
        sta     it_gnd_hi,x
        jmp     @total
:       sec
        lda     it_pack_lo,x
        sbc     fr_oz
        sta     it_pack_lo,x
        lda     it_pack_hi,x
        sbc     fr_oz+1
        sta     it_pack_hi,x
@total: sec
        lda     it_oz_lo,x
        sbc     fr_oz
        sta     it_oz_lo,x
        lda     it_oz_hi,x
        sbc     fr_oz+1
        sta     it_oz_hi,x
        ora     it_oz_lo,x
        bne     :+
        lda     #$FF            ; nothing left anywhere
        sta     it_place,x
:       rts

; fr_kpo, fr_water -- A = kcal per ounce, water percent of the object.
fr_kpo: lda     fr_k
        beq     :+
        ldx     fr_j
        lda     fr_kpo2,x
        rts
:       ldx     noun
        lda     it_kcal,x
        rts
fr_water:
        lda     fr_k
        beq     :+
        ldx     fr_j
        lda     fr_water2,x
        rts
:       ldx     noun
        lda     fr_water1-23,x
        rts
fr_kpo2:   .byte 75,75,75,75,75,40,40,30,25,25,10  ; w9[1..11]
fr_water2: .byte 40,40,40,40,40,75,50,75,75,75,90  ; w10[1..11]
fr_water1: .byte 5,0,25,0,0,20,0,60,0,20,50,20,80,60,90   ; W10[23..37]
fr_lim_lo: .byte <48, <288, <848
fr_lim_hi: .byte >48, >288, >848

; COOK ($5E62 / $5EE9): hours, cooked past 15 + INT(.6 oz) minutes: the
; ground counter of the pile = INT(48 x $4C48); detoxication; from the pack
; the ounces go to the ground (T0E/S02), with the pack's record unless
; detoxicated; a spoiled ground pile is thrown away first ($5EC4).
fr_cook:
        lda     fr_k            ; a provision from the pack must find its
        bne     :+              ; ground pile here (one ground pile an item)
        lda     fr_src
        beq     :+
        ldx     noun
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     :+
        jsr     at_ground
        bcs     :+
        lda     #<m_pile
        ldx     #>m_pile
        jmp     fr_say
:       jsr     fr_hours
        bcc     :+
        rts
:       lda     fr_min
        ora     fr_min+1
        jeq     fr_sense
        lda     fr_min
        sta     camp_minutes
        lda     fr_min+1
        sta     camp_minutes+1
        lda     #1              ; .01 x the total pounds
        sta     fg_eff
        lda     #1
        sta     resource_retention_due
        lda     #0
        sta     fr_cook_st      ; $4B83: 0 raw, 1 cooked, 2 detoxicated
        ldy     fr_oz           ; cooked: minutes > 15 + INT(.6 oz)
        lda     fr_oz+1
        jsr     GIVAYF
        fop     FMULT, fr_0_6
        jsr     AYINT
        clc
        lda     $A1
        adc     #15
        sta     fr_t
        lda     $A0
        adc     #0
        sta     fr_u
        lda     fr_t
        cmp     fr_min
        lda     fr_u
        sbc     fr_min+1
        bcc     :+
        jmp     @move
:       inc     fr_cook_st
        lda     fr_src          ; the ground counter: 48 x $4C48 (kept aside)
        pha
        lda     #0
        sta     fr_src
        jsr     fr_counter
        pla
        sta     fr_src
        stx     fr_i
        lda     fg_cl,x
        sta     fr_old
        lda     fg_ch,x
        sta     fr_old+1
        lda     #48
        jsr     forage_hours
        ldx     fr_i
        jsr     fg_count
        ldx     fr_q            ; detoxication of the chosen pile's code
        bmi     @move
        lda     fr_fam
        cmp     #11
        beq     @fish
        lda     fg_gx,x
        ldy     fr_src
        beq     :+
        lda     fg_px,x
:       cmp     #1
        bne     @code23
        lda     #<fr_0_85
        ldy     #>fr_0_85
        cpx     #6
        bne     @draw
        lda     #<fr_0_75       ; NUTS
        ldy     #>fr_0_75
        bne     @draw
@code23:
        cmp     #2
        bcc     @move
        cmp     #4
        bcs     @move
        cpx     #6              ; NUTS of codes 2, 3: no draw
        beq     @move
        lda     #<adv_leaf_p2_c ; .2
        ldy     #>adv_leaf_p2_c
        bne     @draw
@fish:  lda     #<fr_0_3
        ldy     #>fr_0_3
@draw:  sta     fr_t
        sty     fr_u
        jsr     fr_rnd
        lda     fr_t
        ldy     fr_u
        jsr     fr_below
        bcc     @move
        ldx     fr_q            ; detoxicated: the ground's record 0, 0
        lda     #0
        sta     fg_gt,x
        sta     fg_gx,x
        lda     #2
        sta     fr_cook_st
@move:  lda     fr_src          ; from the pack: onto the ground
        bne     :+
        jmp     fr_ok
:       lda     fr_cook_st
        cmp     #1
        bne     @pile
        ldx     fr_q            ; the pack's record, unless detoxicated
        bmi     @pile
        lda     fg_pt,x
        sta     fg_gt,x
        lda     fg_px,x
        sta     fg_gx,x
        cpx     #6
        beq     @pile
        lda     fg_pp,x
        sta     fg_gp,x
@pile:  lda     fr_cook_st      ; a spoiled ground pile is thrown away
        beq     @add
        lda     fr_old+1
        bmi     @throw
        ora     fr_old
        bne     @add
@throw: lda     fr_k
        beq     :+
        ldx     fr_j
        lda     #0
        sta     fg_gl,x
        sta     fg_gh,x
        beq     @add
:       ldx     noun
        sec
        lda     it_oz_lo,x
        sbc     it_gnd_lo,x
        sta     it_oz_lo,x
        lda     it_oz_hi,x
        sbc     it_gnd_hi,x
        sta     it_oz_hi,x
        lda     #0
        sta     it_gnd_lo,x
        sta     it_gnd_hi,x
@add:   lda     fr_k
        beq     @first
        ldx     fr_j
        jsr     fr_pack_minus
        jsr     fr_ground_plus
        jsr     fg_place
        jmp     fr_ok
@first: ldx     noun            ; provisions: pack -> ground here
        sec
        lda     it_pack_lo,x
        sbc     fr_oz
        sta     it_pack_lo,x
        lda     it_pack_hi,x
        sbc     fr_oz+1
        sta     it_pack_hi,x
        clc
        lda     it_gnd_lo,x
        adc     fr_oz
        sta     it_gnd_lo,x
        lda     it_gnd_hi,x
        adc     fr_oz+1
        sta     it_gnd_hi,x
        lda     px+1
        sta     it_x,x
        lda     py+1
        sta     it_y,x
        jmp     fr_ok
; ---------------------------------------------------------------------------
; SKIN (T11/S07 $5848): V = header byte 30, .5 for GAME; no tool needed.
; ---------------------------------------------------------------------------
fr_skin:
        lda     fr_fam
        cmp     #3
        jeq     fr_whatever
        cmp     #11
        jne     fr_sense
        lda     fr_k
        cmp     #6
        bne     :+
        lda     #<fr_m198       ; FISH
        ldx     #>fr_m198
        jmp     fr_say
:       ldx     fr_j            ; not skinnable: alive (msg 38) or done (11)
        lda     fg_skin
        and     fg_bit,x
        bne     :+
        lda     fr_b2
        cmp     #1
        jeq     fr_already
        jmp     fr_mustkill
:       cpx     #4              ; GAME: V = .5, hide 6, 100 V = 50
        bne     @animal
        lda     #6
        sta     fr_hide
        lda     #50
        sta     fr_min
        lda     #0
        sta     fr_min+1
        beq     @time
@animal:
        lda     fg_v,x          ; hide 12 V (V <= 15)
        sta     fr_t
        asl     a
        adc     fr_t
        asl     a
        asl     a
        sta     fr_hide
        lda     #0              ; 100 V
        sta     fr_min
        sta     fr_min+1
        ldy     fg_v,x
:       dey
        bmi     @time
        clc
        lda     fr_min
        adc     #100
        sta     fr_min
        bcc     :-
        inc     fr_min+1
        bne     :-
@time:  ldx     fr_j            ; meat on the ground > 12 V (msg 200)
        lda     fg_gh,x
        bne     :+
        lda     fr_hide
        cmp     fg_gl,x
        bcc     :+
        lda     #<fr_m200
        ldx     #>fr_m200
        jmp     fr_say
:       lda     light           ; minutes = INT(100 V / ((light + 1)(knife + 1)))
        beq     :+
        lsr     fr_min+1
        ror     fr_min
:       jsr     fr_knife
        bcc     :+
        lsr     fr_min+1
        ror     fr_min
:       lda     fr_min
        sta     camp_minutes
        lda     fr_min+1
        sta     camp_minutes+1
        lda     #2              ; .02 x the total pounds
        sta     fg_eff
        lda     fr_hide         ; the hide comes off the meat
        sta     fr_oz
        lda     #0
        sta     fr_oz+1
        ldx     fr_j
        jsr     fr_ground_minus
        ldx     #FG_HIDE
        jsr     fr_ground_plus
        jsr     fg_place
        ldx     fr_j
        lda     fg_bit,x
        eor     #$FF
        and     fg_skin
        sta     fg_skin
        lda     #<fr_m199
        ldx     #>fr_m199
        jmp     fr_say

; fr_knife -- C set when the KNIFE is in use (B2[59]) on this cell.
fr_knife:
        lda     care_tools
        and     #2
        beq     @no
        lda     px+1
        cmp     care_tool_x
        bne     @no
        lda     py+1
        cmp     care_tool_y
        bne     @no
        sec
        rts
@no:    clc
        rts

; ---------------------------------------------------------------------------
; Hunting and fishing (T0F/S07): GET/CATCH/FIND (verb 1), KILL/ATTACK
; (17), SCARE (18), DOUSE/STOP (26), CUT (31) on the second set's family
; 11: GAME, FISH and, for GET, the animals.
; ---------------------------------------------------------------------------
fr_attack:
        lda     fr_fam          ; food: INSECTS msg 10, else msg 20; HIDE 20
        cmp     #11
        beq     fr_hunt
        lda     verb
        cmp     #31
        beq     :+
        lda     fr_k
        cmp     #7
        jeq     fr_ok
        lda     #<fr_m20
        ldx     #>fr_m20
        jmp     fr_say
:       jmp     fr_sense
fr_hunt:
        lda     #2              ; the module's effort: .02 x the total pounds
        sta     fg_eff
        lda     fr_b2           ; $5800-$583C
        bmi     @absent
        beq     @present
        lda     verb            ; killed: GET -> PACK, else msg 11
        cmp     #1
        jeq     fr_use_pack
        jmp     fr_already
@absent:
        lda     verb
        cmp     #1
        jne     fr_sense
        lda     fr_b1
        jmi     fr_unavailable
        cmp     #2
        jeq     fr_already
        jmp     fr_use_pack
@present:
        lda     verb
        cmp     #1
        bne     :+
        lda     fr_k
        cmp     #5
        jcs     fr_catch
        lda     #<fr_m_kill     ; an animal: PLEASE USE 'KILL' COMMAND
        ldx     #>fr_m_kill
        jmp     fr_say
:       cmp     #18
        bne     :+
        lda     #<care_unwise_message   ; SCARE GAME/FISH: msg 39
        ldx     #>care_unwise_message
        jmp     fr_say
:       lda     fr_k
        cmp     #5
        jcc     fr_sense        ; (the animals' KILL is OUTDOOR's)
; KILL/ATTACK/DOUSE/CUT GAME|FISH ($58DE): the first means in use, cleared:
; GUN 21, BOW 20, SPEAR 19 (lot 3: fg_use, src/craft.s), AXE or KNIFE 18,
; CLUB or ROCK 17 (FT_CLUB, both cleared).
        lda     #3              ; .02 + .03 x the total pounds
        sta     fg_eff
        lda     camp_use
        and     #U_GUN
        beq     :+
        eor     camp_use
        sta     camp_use
        lda     #21
        bne     @means
:       lda     #FT_BOW
        ldy     #20
        jsr     fr_means
        bcs     @means
        lda     #FT_SPEAR
        ldy     #19
        jsr     fr_means
        bcs     @means
        lda     care_tools
        and     #3
        beq     :+
        jsr     fr_tool_here
        bcc     :+
        lda     care_tools
        and     #$FC
        sta     care_tools
        lda     #18
        bne     @means
:       lda     #FT_CLUB
        ldy     #17
        jsr     fr_means
        bcs     @means
        lda     #<c_m25         ; msg 25
        ldx     #>c_m25
        jmp     fr_say
@means: sta     fr_t
        lda     verb            ; CUT: a blade (18, 19)
        cmp     #31
        bne     :+
        lda     fr_t
        cmp     #18
        beq     :+
        cmp     #19
        beq     :+
        lda     #<c_m25
        ldx     #>c_m25
        jmp     fr_say
:       lda     #15
        sta     camp_minutes
        lda     #0
        sta     camp_minutes+1
        sta     FAC             ; p = .1 (means - 18) with light, else 0
        lda     light
        beq     @dark
        lda     fr_t
        sec
        sbc     #18
        bcc     @dark           ; the CLUB: -.1, never (as 0: RND >= 0)
        tay
        lda     #0
        jsr     GIVAYF
        jsr     DIV10
@dark:  fst     fr_p
        jsr     fr_rnd
        lda     #<fr_p
        ldy     #>fr_p
        jsr     fr_below
        bcs     :+
        jmp     fr_missed
:       lda     #<fr_m70        ; msg 70
        ldx     #>fr_m70
        jsr     fr_say
        jmp     fr_take
fr_means:                       ; A = an fg_use bit (lot 3), Y = its means:
        and     fg_use          ; C set, A = Y and the bit cleared when the
        beq     :+              ; weapon is in use
        eor     fg_use
        sta     fg_use
        tya
        sec
        rts
:       clc
        rts
fr_tool_here:                   ; AXE, KNIFE put in use on this cell
        lda     px+1
        cmp     care_tool_x
        bne     :+
        lda     py+1
        cmp     care_tool_y
        bne     :+
        sec
        rts
:       clc
        rts
fr_missed:
        lda     #<fr_m67        ; msg 67
        ldx     #>fr_m67
        jmp     fr_say

; CATCH ($5B48): TRAP (GAME) or FISHNG GEAR (FISH) in use, the hours, one
; draw: caught when RND <= minutes x .0007 (GAME) or .008 (FISH); the rest
; is credited ($5BBE).
fr_catch:
        ldx     #FT_TRAP
        cmp     #5
        beq     :+
        ldx     #FT_GEAR
:       txa
        and     fg_use
        bne     :+
        lda     #<fr_m66        ; msg 66
        ldx     #>fr_m66
        jmp     fr_say
:       jsr     fr_hours
        bcc     :+
        rts
:       lda     fr_min
        ora     fr_min+1
        jeq     fr_sense
        lda     fr_min
        sta     camp_minutes
        lda     fr_min+1
        sta     camp_minutes+1
        ldy     fr_min
        lda     fr_min+1
        jsr     GIVAYF
        fst     fr_mf           ; minutes
        lda     #<fr_0_0007
        ldy     #>fr_0_0007
        ldx     fr_k
        cpx     #5
        beq     :+
        lda     #<fr_0_008
        ldy     #>fr_0_008
:       jsr     FMULT
        fst     fr_p
        jsr     fr_rnd
        fop     FCOMP, fr_p
        cmp     #1
        beq     @fail           ; RND > p
        lda     #<w_m56         ; msg 56
        ldx     #>w_m56
        jsr     fr_say
        jsr     fr_take
        jmp     @rest
@fail:  jsr     fr_missed
@rest:  fld     fr_mf           ; A1[24] -= .025 x minutes
        fop     FMULT, fr_0_025
        fop     FSUB, s_defr
        fst     s_defr
        fld     fr_mf           ; A1[18] = elapsed + .01 x minutes
        fop     FMULT, c_0_01
        fop     FADD, s_elap
        fst     s_last+10
        rts

; fr_take -- the catch ($59AA): its ground counter INT(18 x $4C48) (FISH
; a third), skinnable, b2 = 1, 4 + INT(64 RND) ounces on the ground; FISH:
; its quality ($5A83).
fr_take:
        ldx     fr_j
        lda     #1
        sta     fg_b2,x
        lda     fg_bit,x
        ora     fg_skin
        sta     fg_skin
        ldy     #18
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fg_factor
        lda     fr_k
        cmp     #6
        bne     :+
        fop     FMULT, fr_third
:       jsr     fg_int
        lda     fr_j
        clc
        adc     #FG_CGND
        tax
        jsr     fg_count
        jsr     fr_rnd          ; 4 + INT(64 RND) ounces
        lda     FAC
        beq     :+
        clc
        adc     #6
        sta     FAC
:       jsr     AYINT
        clc
        lda     $A1
        adc     #4
        sta     fr_oz
        lda     #0
        sta     fr_oz+1
        ldx     fr_j
        jsr     fr_ground_plus
        jsr     fg_place
        lda     fr_k
        cmp     #6
        beq     :+
        rts
:       lda     #0              ; FISH: W9[64] = 0, then the draw
        sta     fg_gt
        lda     M_LAT           ; p0 = .05 - .001 |lat|
        bpl     :+
        eor     #$FF
        clc
        adc     #1
:       tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fr_0_001
        fop     FSUB, fr_0_05
        fst     fr_p
        jsr     fr_rnd
        fst     fr_r
        fop     FCOMP, fr_0_95
        cmp     #1
        bne     :+
        lda     #3              ; no scales: code 3, 15 %
        ldy     #15
        ldx     #121-119
        bne     @fish
:       fld     fr_r
        lda     #<fr_p
        ldy     #>fr_p
        jsr     fr_below
        bcc     :+
        lda     #2              ; flabby skin: code 2, 30 %
        ldy     #30
        ldx     #0
        beq     @fish
:       fld     fr_r
        fop     FMULT, adv_leaf_p2_c
        lda     #<fr_p
        ldy     #>fr_p
        jsr     fr_below
        bcc     :+
        lda     #2              ; oddly shaped
        ldy     #30
        ldx     #1
        bne     @fish
:       lda     #0              ; conventional: code 0, the percent kept
        sta     fg_gx
        ldx     #3
        bne     @say
@fish:  sta     fg_gx
        sty     fg_gp
@say:   lda     fr_fish_lo,x
        pha
        lda     fr_fish_hi,x
        tax
        pla
        jmp     fr_say
fr_fish_lo: .byte <fr_m119, <fr_m120, <fr_m121, <fr_m122
fr_fish_hi: .byte >fr_m119, >fr_m120, >fr_m121, >fr_m122

; ---------------------------------------------------------------------------
; Constants, texts, variables
; ---------------------------------------------------------------------------
MUL10    = $EA39
fg_bit:   .byte 1, 2, 4, 8, 16, 32
fr_modulus: .byte $9B,$DB,$FF,$03
fr_modulus_float: .byte $9A,$7F,$F6,$E6,$C0
fr_256:   .byte $89,0,0,0,0
fr_25:    .byte $85,$48,0,0,0
fr_60:    .byte $86,$70,0,0,0
fr_64:    .byte $87,$00,0,0,0
fr_12:    .byte $84,$40,0,0,0
fr_third: .byte $7F,$2A,$AA,$AA,$AB
fr_0_004: .byte $79,$03,$12,$6E,$98
fr_0_6:   .byte $80,$19,$99,$99,$9A
fr_0_85:  .byte $80,$59,$99,$99,$9A
fr_0_75:  .byte $80,$40,0,0,0
fr_0_3:   .byte $7F,$19,$99,$99,$9A
fr_0_95:  .byte $80,$73,$33,$33,$33
fr_0_05:  .byte $7C,$4C,$CC,$CC,$CD
fr_0_001: .byte $77,$03,$12,$6E,$98
fr_0_0007: .byte $76,$37,$80,$34,$6E   ; T0F/S07 $5C10
fr_0_008: .byte $7A,$03,$12,$6E,$98    ; $5C15
fr_0_025: .byte $7B,$4C,$CC,$CC,$CD
fr_0_8:   .byte $80,$4C,$CC,$CC,$CD    ; src/survival.s sv_0_8
fr_0_007: .byte $79,$65,$60,$41,$89    ; sv_0_007
fr_0_017: .byte $7B,$0B,$43,$95,$81    ; sv_0_017
fr_inv64: .byte $7B,0,0,0,0
adv_leaf_p2_c: .byte $7E,$4C,$CC,$CC,$CD       ; .2

fr_m_pack: .byte "PLEASE USE 'PACK' COMMAND.",0
fr_m_cook: .byte "PLEASE USE 'COOK' COMMAND.",0
fr_m_kill: .byte "PLEASE USE 'KILL' COMMAND.",0
fr_m3:   .byte "YOU CAN'T BE THAT HUNGRY",$A1,0
fr_m18:  .byte "WHATEVER TURNS YOU ON",$A1,0
fr_m20:  .byte "PARDON THE OBSERVATION, BUT YOU ARE STRANGE",$A1,0
fr_m31:  .byte "NOURISHMENT MAKES A LOT OF SENSE.|"
fr_m32:  .byte "PLEASE SPECIFY AMOUNT IN OUNCES.",0
fr_m33:  .byte "I'LL INTERRUPT YOUR TRAVEL IF YOU COME ACROSS FOOD SOURCES.",0
fr_m36:  .byte "YOU MUST BE WITH THE SPCA",$A1,0
fr_m38:  .byte "YOU MUST KILL THE ^ FIRST.",0
fr_m47:  .byte "HMM. UNRIPE RED FRUIT.",0
fr_m66:  .byte "USE THE PROPER DEVICE TO CATCH, OR WEAPON TO KILL.",0
fr_m67:  .byte "SORRY, BETTER LUCK NEXT TIME.",0
fr_m70:  .byte "ONE ^ HAS JUST BITTEN THE DUST",$A1,0
fr_m71:  .byte "IS THE FOOD FROM YOUR PACK [P] OR FROM THE GROUND [G]?",0
fr_m84:  .byte "YOU NEED SOME BAIT.",0
fr_m89:  .byte "AHA",$A1," NICE RIPE RED FRUIT.",0
fr_m93:  .byte "IT APPEARS TO BE UNRIPE WHITE FRUIT.",0
fr_m94:  .byte "IT IS SOME FORM OF RIPE WHITE FRUIT.",0
fr_m119: .byte "YOUR FISH HAS FLABBY SKIN AND SUNKEN EYES.",0
fr_m120: .byte "YOUR FISH IS ODDLY SHAPED.",0
fr_m121: .byte "YOUR FISH HAS NO SCALES.",0
fr_m122: .byte "YOUR FISH IS CONVENTIONAL IN SHAPE AND HAS SCALES.",0
fr_m123: .byte "ALTHOUGH NOT THE NECTAR OF THE GODS, THE TASTE IS OKAY.",0
fr_m124: .byte "IT SMELLS AND TASTES LIKE SPOILED FOOD.",0
fr_m125: .byte "THE TASTE IS VERY BITTER.",0
fr_m126: .byte "THERE IS A SHARP STINGING SENSATION ON YOUR TONGUE.",0
fr_m183: .byte "THESE PLANTS HAVE A MILKY COLORED SAP.",0
fr_m184: .byte "YOU NOTICE SILKY WINDBORNE SEEDS.",0
fr_m198: .byte "SORRY. GET HIDE FROM WILD ANIMALS OR SMALL GAME.",0
fr_m199: .byte "YOU NOW HAVE SOME HIDE. SEE INVENTORY FOR AMOUNT.",0
fr_m200: .byte "THERE'S TOO LITTLE ^ TO OBTAIN ANY HIDE.",0

fr_said: .byte 0
fr_fam:  .byte 0                ; 3 food, 11 game and meat, 13 HIDE
fr_k:    .byte 0                ; second set k (1..11, 19), 0 first set
fr_j:    .byte 0                ; pile (k - 1, HIDE 11)
fr_q:    .byte 0                ; record (FISH 0 .. PLANTS 5, NUTS 6), $FF
fr_b1:   .byte 0
fr_b2:   .byte 0
fr_src:  .byte 0                ; 0 ground, 1 pack
fr_gnd:  .word 0
fr_pk:   .word 0
fr_av:   .word 0
fr_oz:   .word 0
fr_min:  .word 0
fr_old:  .word 0
fr_hide: .byte 0
fr_code: .byte 0
fr_cook_st: .byte 0
fr_t:    .byte 0
fr_u:    .byte 0
fr_i:    .byte 0
fr_d:    .byte 0
fr_dec:  .byte 0
fr_buf:  .res 8
fr_r:    .res 5
fr_p:    .res 5
fr_mf:   .res 5
frg_end:
.export frg_main, frg_end

.segment "FORAGE"
        UI_TWO fr_choose_source, 'P', 'G'
