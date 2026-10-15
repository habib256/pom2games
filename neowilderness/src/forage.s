; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; forage.s -- lot 4: hunting, fishing, gathering, meals (docs/FORAGE.md)
; ============================================================================
; The resident part of the lot (included by wild.s); the commands themselves
; are the FORAGE module (src/frg.s, directory entry 31), read from
; NEOWILD.BLK into the SIM window at each command on both editions
; (docs/FORAGE.md 17, docs/MEMORY.md 16):
;   forage_state   the second item set of the original (piles of the four
;                  animals, GAME, FISH, the five wild foods and HIDE), the
;                  spoilage counters, the quality records, the factor of the
;                  day $4C48, bait, IGNORE FOOD, TRAP/GEAR in use; saved by
;                  SAVE (src/save.s sv_ranges)
;   forage_here    the player left the cell of the ground piles (T0C/S0B
;                  $58A7): they are lost (called lazily: walk step, discovery,
;                  kill, the module, INVENTORY, the grid)
;   forage_found   (ADVENTURE module_resource_results) the discovery stored:
;                  quantity, quality record, spoilage counter (T0D/S00 $585F)
;   forage_kill    (OUTDOOR) a killed animal leaves its carcass (T06/S04 $593A)
;   forage_clock   (spend, health update) hours off every counter (T09/S05)
;   forage_day     (spend, a new day) $4C48 = 792 / D, D the degree-hours
;                  above 32 F of the day's air (T0C/S03; module_forage_day)
;   forage_gate    (resolve_menu, the head of dispatch) the lot's commands:
;                  the module, then its time through camp_done
;   forage_cond    the grid's condition of CATCH, KILL, SKIN, COOK, TASTE
;   forage_after   (alerts_after) "THERE IS A BAD SMELL IN THE AIR." (msg
;                  209) and the small game or fish leaving (msg 195, 196)
; ============================================================================
FORAGE_MODULE = 31              ; directory entry (memory.s MOD_COUNT)
FORAGE_RUN  = $9600             ; src/wild.cfg FRG: the SIM window
FG_PILES = 12                   ; piles: k = 1..11 (index k - 1), HIDE (11)
FG_HIDE  = 11
FG_CN    = 47                   ; spoilage counters (signed hours):
FG_CPACK = 0                    ;   pack, k = 1..11 (w11[k])
FG_CGND  = 11                   ;   ground, k = 1..11 (w11[k+21], w10[k+15])
FG_CPROV = 22                   ;   provisions 23..37, pack and 23..27 ground (W11[n])
FG_CPGND = 37 - 28              ;   + n: ground of 28..37 (W11[n+13])
FG_QN    = 7                    ; quality records: FISH .. PLANTS (k - 6), NUTS (6)
U_GUN    = 128                  ; camp_use: GUN in use (B2[57]), lost with time
FT_TRAP  = 1                    ; fg_use: TRAP and FISHNG GEAR in use (B2[72],
FT_GEAR  = 2                    ; B2[67]), lost on leaving the cell
; Provisions under the original's rules (EAT of 23..37 through the module:
; spoilage, pack or ground, salt; the smell of spoiled provisions), lot 4
; step 5: the initial value of fg_fidelity (a byte: tests set it); 0 keeps
; the HGR reference (test_reference_state.py).
FORAGE_FIDELITY = 0
SIGN     = $EB82                ; A <- 0, 1, $FF as FAC =0, >0, <0
ZERO_FAC = $E84E

.segment "LOWTEXT"
forage_state:
fg_b1:   .res FG_PILES, $FF     ; b1: $FF none, 0 ground, 2 pack, 4 both
fg_gl:   .res FG_PILES          ; w7: ounces on the ground (this cell)
fg_gh:   .res FG_PILES
fg_pl:   .res FG_PILES          ; w8: ounces in the pack
fg_ph:   .res FG_PILES
fg_b2:   .res 6, $FF            ; b2[1..6]: $FF absent, 0 present, 1 killed
; Counters of the saved game (build/re_forage/state.bin).
fg_cl:   .byte <24,<24,<24,<24,<18,<6,<6,<72,<96,<48,<120
         .res 11
         .byte <2426,<2426,<808,<2426,<2426,<116,<2426,<388,<2426,<1213,<38,<116,<2426,<58,<274
         .byte <116,<2426,<388,<2426,<1213,<38,<116,<2426,<58,<274
fg_ch:   .byte 0,0,0,0,0,0,0,0,0,0,0
         .res 11
         .byte >2426,>2426,>808,>2426,>2426,>116,>2426,>388,>2426,>1213,>38,>116,>2426,>58,>274
         .byte >116,>2426,>388,>2426,>1213,>38,>116,>2426,>58,>274
; Quality records, ground (W9 taste, W10 toxicity code, W11 percent) and
; pack (b4, b3, w9[k+15]); NUTS share W11[70] (initially 100).
fg_gt:   .res FG_QN
fg_gx:   .res FG_QN
fg_gp:   .byte 0,0,0,0,0,0,100
fg_pt:   .res FG_QN
fg_px:   .res FG_QN
fg_pp:   .res FG_QN
fg_skin: .byte 0                ; $4AE0: bit k - 1 skinnable (k = 1..6)
fg_bait: .byte 0                ; $4B50
fg_ignore: .byte 0              ; $4B75: IGNORE FOOD
fg_use:  .byte 0                ; FT_*
fg_factor: .byte $81,$4F,$05,$02,$98    ; $4C48 of the saved game (1.61734)
fg_x:    .byte $FF              ; the cell of the ground piles
fg_y:    .byte $FF
fg_v:    .res 4                 ; V (header byte 30) of the animals killed
fg_n:    .res 4                 ; their nouns (out_nouns): SKIN RATTLER
forage_state_end:
fg_hm:   .word 0                ; minutes of the health update (spend)
fg_fidelity: .byte FORAGE_FIDELITY      ; provisions through the module
fg_after: .byte 0               ; bit 0 the smell, bit 1 game, bit 2 fish left
fg_eff:  .byte 0                ; (module) effort of the action: 0 set, 1-3 k
fg_t:    .word 0                ; forage_hours
fg_q:    .byte 0                ; scratch
sim_bm:  .res 4                 ; sim_fetch: ProDOS's bitmap of $90-$AF
.export forage_ran
.export forage_state, forage_state_end, fg_b1, fg_gl, fg_gh, fg_pl, fg_ph, fg_b2
.export fg_cl, fg_ch, fg_gt, fg_gx, fg_gp, fg_pt, fg_px, fg_pp, fg_skin, fg_bait
.export fg_ignore, fg_use, fg_factor, fg_x, fg_y, fg_v, fg_n, fg_hm, fg_after, fg_eff

.segment "LOWCODE"
; forage_here -- (T0C/S0B $58A7) on another cell than the piles': meat,
; fish, wild foods and hide on the ground are lost (b1 = 2 with a pack
; stock, else $FF), the animals, game and fish there are gone (b2 = $FF),
; nothing to skin, no bait, TRAP and GEAR no longer in use; the CLUB and the
; ROCK left on the ground are settled by the next CRAFT or INVENTORY.
forage_here:
        lda     px+1
        cmp     fg_x
        bne     @left
        lda     py+1
        cmp     fg_y
        beq     @rts
@left:  lda     px+1
        sta     fg_x
        lda     py+1
        sta     fg_y
        ldx     #FG_PILES-1
@pile:  lda     fg_gl,x
        ora     fg_gh,x
        beq     @next
        lda     #0
        sta     fg_gl,x
        sta     fg_gh,x
        lda     fg_pl,x
        ora     fg_ph,x
        beq     :+
        lda     #2
        .byte   $2C             ; BIT abs: skips the next LDA
:       lda     #$FF
        sta     fg_b1,x
@next:  dex
        bpl     @pile
        ldx     #5
        lda     #$FF
:       sta     fg_b2,x
        dex
        bpl     :-
        lda     #0
        sta     fg_skin
        sta     fg_bait
        sta     fg_use
        sta     cr_still        ; lot 3: the CLUB, the ROCK (src/craft.s cr_here)
@rts:   rts

; fg_place -- X = pile: b1 from its stocks (4 both, 2 pack, 0 ground, $FF).
fg_place:
        lda     fg_pl,x
        ora     fg_ph,x
        beq     @ground
        lda     fg_gl,x
        ora     fg_gh,x
        beq     :+
        lda     #4
        .byte   $2C
:       lda     #2
        sta     fg_b1,x
        rts
@ground:
        lda     fg_gl,x
        ora     fg_gh,x
        beq     :+
        lda     #0
        .byte   $2C
:       lda     #$FF
        sta     fg_b1,x
        rts

; forage_hours -- fg_t = INT(A x $4C48) hours (a fresh counter).
forage_hours:
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, fg_factor
fg_int: jsr     AYINT
        lda     $A1
        sta     fg_t
        lda     $A0
        sta     fg_t+1
        rts

; fg_count -- X = counter: fg_t into it.
fg_count:
        lda     fg_t
        sta     fg_cl,x
        lda     fg_t+1
        sta     fg_ch,x
        rts

.segment "GCODE"
; sim_fetch -- X = directory entry: mem_fetch of a module of NEOWILD.BLK
; into the SIM window (FORAGE, the campfire of src/fire.s), with ProDOS's
; bitmap of pages $90-$AF freed around the READ_BLOCK (MLI refuses a buffer
; in pages it marks used), as module_save does.
sim_fetch:
        ldy     #3
:       lda     PD_BITMAP+18,y
        sta     sim_bm,y
        lda     #0
        sta     PD_BITMAP+18,y
        dey
        bpl     :-
        jsr     mem_fetch
        ldx     #3
:       lda     sim_bm,x
        sta     PD_BITMAP+18,x
        dex
        bpl     :-
        rts

; forage_skip -- (TRAVEL resource_scan, a food or game type) C set: no
; draw: REST/CAMP, or IGNORE FOOD (T0A/S00 $5A43: types 5-12 not examined).
forage_skip:
        lda     fg_ignore
        cmp     #1
        bcs     @rts
        lda     verb
        cmp     #V_REST
        beq     @yes
        cmp     #V_CAMP
        beq     @yes
        clc
@rts:   rts
@yes:   sec
        rts

.segment "TEXT"                 ; (WILDLO is short)
; forage_gate -- (resolve_menu, the head of dispatch) when the lot takes
; (verb, noun) (forage_wants): the module is read from NEOWILD.BLK into the
; SIM window (sim_fetch), run, then its time at its effort (camp_done, the
; common report). Otherwise returns to dispatch.
forage_gate:
        jsr     forage_wants
        bcs     :+
        rts
:       pla                     ; dispatch's return: the command ends here
        pla
        jsr     forage_here
        jsr     camp_begin
        lda     #0
        sta     sim_loaded      ; the module holds the SIM window
        sta     fg_eff
        sta     fg_ctx
        jsr     woods_here      ; what the module cannot test (BAIT)
        rol     fg_ctx
        jsr     water_bits
        ora     fg_ctx
        sta     fg_ctx
        ldx     #FORAGE_MODULE
        jsr     sim_fetch
        jsr     FORAGE_RUN
forage_ran:                     ; (tests: the module's decisions, before time)
        lda     camp_minutes
        ora     camp_minutes+1
        beq     @rts
        jsr     load_totals     ; SIM back: the load moved, the effort
        ldx     fg_eff          ; 1 .01, 2 .02, 3 .05 x the total pounds
        beq     @time
        lda     fg_eff_lo-1,x
        ldy     fg_eff_hi-1,x
        jsr     camp_effort
@time:  lda     #0
        jmp     camp_done
@rts:   rts
fg_eff_lo: .byte <c_0_01, <c_0_02, <fg_0_05
fg_eff_hi: .byte >c_0_01, >c_0_02, >fg_0_05
fg_0_05: .byte $7C,$4C,$CC,$CC,$CD      ; T0F/S07 .02 + .03
fg_ctx:  .byte 0                ; bit 0 water near (water_bits), bit 1 woods

.segment "CODE"                 ; (WILDLO is short: the WILDERNESS area)
; forage_wants -- C set when the lot handles (verb, noun) (docs/FORAGE.md
; 15.3): the second set (GAME, FISH, the foods, HIDE; the animals for the
; carcass verbs), NUTS and the provisions for the new verbs (EAT too under
; FORAGE_FIDELITY), FOOD, BAIT, USE TRAP/GEAR/GUN; noun 0 from the grid.
forage_wants:
        lda     verb
        beq     @no
        cmp     #40
        bcs     @no
        ldx     noun
        beq     @grid
        cpx     #135            ; FOOD: GET, TASTE, IGNORE, FLAG
        bne     :+
        ldx     #FGM_FOOD
        bne     @mask
:       cpx     #175            ; BAIT: GET, USE, PACK, EAT
        bne     :+
        ldx     #FGM_BAIT
        bne     @mask
:       cmp     #2              ; USE GUN, FISHNG GEAR, TRAP
        bne     @set
        cpx     #57
        beq     @yes
        cpx     #67
        beq     @yes
        cpx     #72
        beq     @yes
@set:   cpx     #23
        bcc     @no
        ldy     #FGM_NUTS
        cpx     #24
        bcc     @masky
        ldy     #FGM_PROV
        cpx     #38
        bcs     :+
        lda     fg_fidelity     ; EAT of the provisions too
        beq     @masky
        ldy     #FGM_NUTS
        bne     @masky
:
        ldy     #FGM_SECOND
        cpx     #94             ; HIDE
        beq     @masky
        cpx     #80
        bcc     @animal
        cpx     #87
        bcc     @masky
        cpx     #178
        bcc     @no
        cpx     #200
        bcs     @no
@animal:
        cpx     #76
        bcc     @no
        ldy     #FGM_ANIMAL
@masky: tya
        tax
@mask:  lda     verb            ; bit verb of the mask at X
        pha
        lsr     a
        lsr     a
        lsr     a
        stx     fg_q
        clc
        adc     fg_q
        tay
        pla
        and     #7
        tax
        lda     fg_masks,y
        and     forest_masks,x
        cmp     #1
        rts
@yes:   sec
        rts
@no:    clc
        rts
@grid:  cmp     #1              ; CATCH (not GET, FIND) and KILL, SKIN,
        bne     :+              ; COOK, TASTE: what the grid offers
        lda     inbuf
        cmp     #'C'
        bne     @no
        lda     #1
        bne     forage_cond
:       cmp     #4
        beq     forage_cond
        cmp     #11
        beq     forage_cond
        cmp     #35
        beq     forage_cond
        cmp     #17
        bne     @no
        lda     #C_ANIMAL       ; KILL with an animal here stays OUTDOOR's
        jsr     ctx_ok
        bcs     @no
        lda     #17

; forage_cond -- A = verb: C set when it applies here (the grid, src/menu.s
; X_FORAGE; forage_wants for noun 0): CATCH, KILL small game or fish
; present; SKIN a carcass of animal or game; COOK food with a fire or the
; stove in use; TASTE food.
forage_cond:
        pha
        jsr     forage_here
        pla
        cmp     #4
        bne     :+
        lda     fg_skin
        and     #$1F            ; not FISH (msg 198)
        cmp     #1
        rts
:       cmp     #11
        bne     @taste
        lda     fire_on
        bne     @food
        lda     camp_use
        and     #U_STOVE
        beq     @no
@food:  ldx     #10
:       lda     fg_gl,x
        ora     fg_gh,x
        ora     fg_pl,x
        ora     fg_ph,x
        bne     @yes
        dex
        bpl     :-
        lda     it_oz_lo+23     ; NUTS
        ora     it_oz_hi+23
        beq     @no
        ldx     #23
        jmp     have
@taste: cmp     #35
        beq     @food
        lda     fg_b2+4         ; CATCH, KILL
        beq     @yes
        lda     fg_b2+5
        beq     @yes
@no:    clc
        rts
@yes:   sec
        rts

; forage_menu -- (verb_extra, an X_FORAGE entry of the grid at gp2): KILL
; of game or fish only without an animal here (the animal's KILL is the
; grid's first contextual verb).
forage_menu:
        ldx     #3
:       lda     gp2
        cmp     fg_menu_lo,x
        beq     :+
        dex
        bpl     :-
@no:    clc
        rts
:       lda     fg_menu_verb,x
        cmp     #17
        bne     :+
        lda     #C_ANIMAL
        jsr     ctx_ok          ; (MENUSWAP)
        bcs     @no
        lda     #17
:       jmp     forage_cond
fg_menu_lo:   .byte <vt_catch, <vt_kill, <vt_skin, <vt_cook
fg_menu_verb: .byte 1, 17, 4, 11

; Verb masks (bit v of byte v / 8, verbs 0..39).
FGM_SECOND = 0                  ; GAME .. PLANTS, HIDE
FGM_ANIMAL = 5                  ; the animals: their carcass
FGM_PROV   = 10                 ; provisions 24..37
FGM_NUTS   = 15
FGM_FOOD   = 20                 ; FOOD
FGM_BAIT   = 25                 ; BAIT
fg_masks:
        .byte $D6,$BB,$06,$84,$08       ; 1 2 4 6 7 8 9 11 12 13 15 17 18 26 31 35
        .byte $D2,$BB,$00,$00,$08       ; 1 4 6 7 8 9 11 12 13 15 35
        .byte $10,$AA,$06,$00,$08       ; 4 9 11 13 15 17 18 35
        .byte $10,$BA,$06,$00,$08       ; 4 9 11 12 13 15 17 18 35
        .byte $02,$00,$00,$00,$68       ; 1 35 37 38
        .byte $46,$10,$00,$00,$00       ; 1 2 6 12

.segment "RESCODE"
; forage_after -- (alerts_after) GAME and FISH no longer sighted here (the
; port's resource_retention, dt / 128, or a walk) are gone: news bits 1, 2
; (msg 195, 196) unless the player walked; the ALERT module prints the news
; of fg_after (forage_news) after the command's result.
forage_after:
        ldx     #4
@seen:  lda     fg_b2,x
        bne     @gone
        lda     resource_seen
        and     fg_seen_bit-4,x
        bne     @gone
        lda     #$FF
        sta     fg_b2,x
        lda     act
        cmp     #1
        beq     @gone
        lda     fg_seen_bit-3,x ; 2 game, 4 fish
        ora     fg_after
        sta     fg_after
@gone:  inx
        cpx     #6
        bcc     @seen
        rts
fg_seen_bit: .byte 1, 2, 4

; forage_day -- (spend, a new day: in place of env_day) the day's factor,
; computed in ALERT once env_day has set the new day.
forage_day:
        jsr     env_day
        lda     #ALERT_MODULE
        jsr     overlay_load
        jmp     module_forage_day


; ============================================================================
; In the modules loaded when they run (docs/MEMORY.md 16)
; ============================================================================
.segment "ITEMS"
; forage_found_begin -- (module_resource_results, before the food) small game and fish
; found here are present (T0D/S00 events $0D, $0E: b2 = 0).
forage_found_begin:
        jsr     forage_here
        lda     MAP+36
        lsr     a
        bcc     :+
        ldx     #0
        stx     fg_b2+4
:       lsr     a
        bcc     :+
        ldx     #0
        stx     fg_b2+5
:       rts

; forage_found -- (module_resource_results, after each food's draws) adv_resource_index x
; = 2..7 (INSECTS, FRUIT, CACTI, MUSHROOMS, PLANTS, NUTS), quantity MAP+26+x,
; quality roll adv_resource_roll, FRUIT's third roll in FAC (T0D/S00 $585F).
; The mushrooms' code is never written, as in the original; their stray
; write into W10[1] is not reproduced (docs/FORAGE.md 12).
forage_found:
        fst     fg_r2           ; FRUIT's colour roll, when drawn
        ldx     adv_resource_index
        cpx     #7
        bne     @wild
        lda     MAP+33          ; NUTS: object 23, a provision on this cell
        sta     it_gnd_lo+23
        clc
        adc     it_pack_lo+23
        sta     it_oz_lo+23
        lda     #0
        sta     it_gnd_hi+23
        adc     it_pack_hi+23
        sta     it_oz_hi+23
        lda     px+1
        sta     it_x+23
        lda     py+1
        sta     it_y+23
        lda     it_place+23
        bpl     :+
        lda     #0
        sta     it_place+23
:       lda     #<720
        sta     fg_cl+FG_CPROV
        lda     #>720
        sta     fg_ch+FG_CPROV
        bne     @quality        ; (always)
@wild:  lda     MAP+26,x        ; ground pile k = x + 5 (index x + 4)
        sta     fg_gl+4,x
        lda     #0
        sta     fg_gh+4,x
        lda     fg_b1+4,x       ; b1 = 4 if it was 2, else 0
        cmp     #2
        bne     :+
        lda     #4
        .byte   $2C
:       lda     #0
        sta     fg_b1+4,x
        lda     fg_base-2,x     ; ground counter: INT(b2[k] x $4C48)
        jsr     forage_hours
        lda     adv_resource_index
        clc
        adc     #FG_CGND+4
        tax
        jsr     fg_count
@quality:
        ldx     adv_resource_index
        cpx     #3
        beq     @fruit
        lda     fg_qfirst-2,x   ; the rows of this food
        sta     fg_row
@row:   ldx     fg_row
        lda     fg_qrow,x
        bmi     @done           ; end of the food's rows: nothing written
        tay
        lda     fg_qthr_lo,y
        ldx     fg_qthr_hi,y
        jsr     fg_below
        bcc     @nextrow
        ldx     fg_row
        lda     fg_qrow+1,x     ; taste, code, percent ($FF: unchanged)
        ldy     fg_qrow+2,x
        pha
        lda     fg_qrow+3,x
        tax
        pla
        jmp     fg_record
@nextrow:
        lda     fg_row
        clc
        adc     #4
        sta     fg_row
        bne     @row
@done:  rts
@fruit: lda     #<adv_leaf_p2   ; r < .2: bitter (1, 1, 80)
        ldx     #>adv_leaf_p2
        jsr     fg_below
        bcc     :+
        lda     #1
        tay
        ldx     #80
        bne     fg_record
:       lda     #<f_half        ; r >= .5: safe (0, 0, the percent kept)
        ldx     #>f_half
        jsr     fg_below
        bcs     :+
        lda     #0
        tay
        ldx     #$FF
        bne     fg_record
:       ldy     #0              ; ripe ($5BEB): latitude > 0, P < S; else S < P
        lda     M_LAT
        bmi     @south
        beq     @south
        lda     #FG_FRUIT_P
        cmp     fauna_env       ; the season (percent of the year)
        bcs     @colour
        iny
        bne     @colour
@south: lda     fauna_env
        cmp     #FG_FRUIT_P
        bcs     @colour
        iny
@colour:
        sty     fg_row          ; m: 1 ripe
        fld     fg_r2           ; white when the third roll < .35
        fop     FCOMP, fg_0_35
        cmp     #$FF
        lda     #3              ; white: taste 3 + m, code 2
        ldy     #2
        bcs     :+
        lda     #5              ; red: taste 5 + m, code 3
        ldy     #3
:       clc
        adc     fg_row
        ldx     #30             ; green 30 %, ripe 10 %
        pha
        lda     fg_row
        beq     :+
        ldx     #10
:       pla
        jmp     fg_record
FG_FRUIT_P = 60                 ; resource record 8, byte 0 (TRAVEL resource_ranges)
fg_base: .byte 6, 72, 96, 48, 120       ; b2[7..11]
fg_r2:   .res 5
fg_row:  .byte 0
fg_0_35: .byte $7F,$33,$33,$33,$33      ; .35 (T0D/S00 $5BE6)

; fg_below -- C set when adv_resource_roll < the float at A/X.
fg_below:
        sta     gp2
        stx     gp2+1
        fld     adv_resource_roll
        lda     gp2
        ldy     gp2+1
        jsr     FCOMP
        cmp     #$FF
        rts

; fg_record -- the ground record of adv_resource_index (NUTS: 6, else x - 3
; for INSECTS .. PLANTS: FISH is 0): A = taste, Y = code, X = percent
; ($FF: unchanged).
fg_record:
        pha
        txa
        pha
        lda     adv_resource_index
        sec
        sbc     #1              ; x = 2..7 -> 1..6 (FISH 0, NUTS 6)
        tax
        pla
        cmp     #$FF
        beq     :+
        sta     fg_gp,x
:       pla
        cmp     #$FF
        beq     :+
        sta     fg_gt,x
:       tya
        cmp     #$FF
        beq     :+
        sta     fg_gx,x
:       rts
; Rows: threshold (0 .1, 1 .2, 2 .3, 3 .5), taste, code, percent; $80 ends.
fg_qfirst: .byte fg_q_ins-fg_qrow, 0, fg_q_cac-fg_qrow, fg_q_mus-fg_qrow
           .byte fg_q_pla-fg_qrow, fg_q_ins-fg_qrow
fg_qrow:
fg_q_ins: .byte 0, 1, 1, 80, $80        ; INSECTS, NUTS
fg_q_cac: .byte 0, 7, 1, 35, $80
fg_q_mus: .byte 2, $FF, $FF, 80, $80    ; the code is never written ($5A45)
fg_q_pla: .byte 0, 8, 1, 60, 1, 7, 1, 40, 2, 2, 2, 80, 3, 1, 1, 80, $80
fg_qthr_lo: .byte <adv_leaf_p1, <adv_leaf_p2, <adv_leaf_p3, <f_half
fg_qthr_hi: .byte >adv_leaf_p1, >adv_leaf_p2, >adv_leaf_p3, >f_half


.segment "OUTDOOR"
; forage_kill -- (OUTDOOR, an ATTACK that succeeds) the carcass of the
; animal of slot animal_kind - 6 (T06/S04 $593A-$5A45): 65 V^2 ounces of
; meat on the ground (V = header byte 30, out_value), 18 x $4C48 hours
; before it spoils, killed (b2 = 1), skinnable. The cannibal's header byte
; 15 (D5) is not rewritten: the port keeps no such byte.
forage_kill:
        jsr     forage_here
        lda     animal_kind
        sec
        sbc     #6
        tax                     ; slot = pile
        lda     out_nouns,x
        sta     fg_n,x
        lda     out_value,x
        sta     fg_v,x
        tay                     ; V^2 (V <= 15: a byte)
        lda     #0
@square:
        dey
        bmi     :+
        clc
        adc     fg_v,x
        bcc     @square
:       sta     fg_q
        lda     #0
        sta     fg_t
        sta     fg_t+1
        ldy     #65             ; 65 V^2 ounces
@meat:  clc
        lda     fg_t
        adc     fg_q
        sta     fg_t
        bcc     :+
        inc     fg_t+1
:       dey
        bne     @meat
        clc                     ; onto the ground pile
        lda     fg_t
        adc     fg_gl,x
        sta     fg_gl,x
        lda     fg_t+1
        adc     fg_gh,x
        sta     fg_gh,x
        lda     #1
        sta     fg_b2,x
        lda     fg_skin_bit,x
        ora     fg_skin
        sta     fg_skin
        jsr     fg_place
        txa
        pha
        lda     #18
        jsr     forage_hours
        pla
        clc
        adc     #FG_CGND
        tax
        jmp     fg_count
fg_skin_bit: .byte 1, 2, 4, 8, 16, 32


.segment "ALERT"
; forage_clock -- (ALERT, after each health update) T09/S05 $5A1D: with the air
; at 33 F and above (unsigned byte), INT(minutes / 60 + .5) hours off every
; counter, present or not; then the smell of spoiled food in the pack.
forage_clock:
        lda     airtemp
        cmp     #33
        bcc     @rts
        lda     fg_hm           ; (health_minutes, zeroed by the update)
        clc
        adc     #30
        sta     fg_t
        lda     fg_hm+1
        adc     #0
        ldx     #0              ; hours
@hour:  tay
        lda     fg_t
        sec
        sbc     #60
        sta     fg_t
        tya
        sbc     #0
        bcc     @hours
        inx
        bne     @hour
@hours: stx     fg_t
        txa
        beq     @rts
        ldx     #FG_CN-1
@count: lda     fg_cl,x
        sec
        sbc     fg_t
        sta     fg_cl,x
        bcs     :+
        dec     fg_ch,x
:       dex
        bpl     @count
        ldx     #10             ; T0D/S07 $5E3F: a pack pile spoiled
@smell: lda     fg_pl,x
        ora     fg_ph,x
        beq     @fresh
        lda     fg_ch,x
        bmi     @bad
        ora     fg_cl,x
        beq     @bad
@fresh: dex
        bpl     @smell
        lda     fg_fidelity
        beq     @rts
        ldx     #37-23          ; the provisions in the pack
@prov:  lda     it_place+23,x
        cmp     #2
        bne     @next
        lda     it_pack_lo+23,x
        ora     it_pack_hi+23,x
        beq     @next
        lda     fg_ch+FG_CPROV,x
        bmi     @bad
        ora     fg_cl+FG_CPROV,x
        beq     @bad
@next:  dex
        bpl     @prov
@rts:   rts
@bad:   lda     #1
        ora     fg_after
        sta     fg_after
        rts

; forage_news -- (al_show) the lot's news (forage_after, forage_clock):
; bit 0 msg 209, bit 1 msg 195, bit 2 msg 196, appended like an alert.
forage_news:
        ldx     #0
@bit:   lsr     fg_after
        bcc     @next
        stx     fg_q
        lda     fg_news_lo,x
        sta     gp1
        lda     fg_news_hi,x
        sta     gp1+1
        jsr     al_put
        ldx     fg_q
@next:  inx
        cpx     #3
        bcc     @bit
        rts
fg_news_lo: .byte <fg_m209, <fg_m195, <fg_m196
fg_news_hi: .byte >fg_m209, >fg_m195, >fg_m196
fg_m209: .byte "THERE IS A BAD SMELL IN THE AIR.",0
fg_m195: .byte "THE SMALL GAME DECIDED TO VAMOOSE.",0
fg_m196: .byte "THE FISH HAVE DEPARTED FOR BETTER FEEDING WATERS.",0

; module_forage_day -- (forage_day, a new day, SIM loaded) the day's cycle
; (weather_temperature; airtemp kept), then $4C48 = 792 / D (T0C/S03 $5AC2): D = the degree-hours above 32 F of the day's three linear
; segments (morning from dawn to the peak, evening from the end back to the
; peak, night from dawn + 24 back to the end), each the original's area
; ($5BCC), D at least 40 ($4C06 = INT(D) is not kept).
module_forage_day:
        lda     airtemp
        pha
        jsr     weather_temperature
        pla
        sta     airtemp
        lda     #0
        sta     fg_d            ; 0.0
        fld     wc_dawn
        fop     FADD, f_24
        fst     fg_ta24
        fld     s_rise          ; the night's anchor (weather_temperature)
        fop     FADD, wc_23
        fst     fg_a23
        ldx     #0
@seg:   stx     fg_i
        lda     fg_sa_lo,x      ; the offset: reference - INT(anchor x slope)
        ldy     fg_sa_hi,x
        jsr     MOVFM
        ldx     fg_i
        lda     fg_ss_lo,x
        ldy     fg_ss_hi,x
        jsr     FMULT
        jsr     AYINT
        ldx     fg_i
        lda     wc_max
        cpx     #2
        bne     :+
        lda     wc_min
:       ldy     #0              ; ref (signed) - INT - 32
        cmp     #$80
        bcc     :+
        dey
:       sec
        sbc     $A1
        tax
        tya
        sbc     $A0
        tay
        txa
        sec
        sbc     #32
        tax
        tya
        sbc     #0
        tay
        txa
        sty     fg_c
        tay
        lda     fg_c
        jsr     GIVAYF
        fst     fg_c
        ldx     fg_i
        lda     fg_ss_lo,x
        ldy     fg_ss_hi,x
        jsr     MOVFM
        fst     fg_s
        ldx     fg_i
        lda     fg_sta_lo,x
        ldy     fg_sta_hi,x
        jsr     MOVFM
        fst     fg_ta
        ldx     fg_i
        lda     fg_stb_lo,x
        ldy     fg_stb_hi,x
        jsr     MOVFM
        fst     fg_tb
        jsr     fg_seg
        fop     FADD, fg_d
        fst     fg_d
        ldx     fg_i
        inx
        cpx     #3
        jcc     @seg
        fop     FCOMP, fg_40
        cmp     #$FF
        bne     :+
        fld     fg_40
:       fop     FDIV, fg_792
        fst     fg_factor
        rts

; fg_seg -- FAC = the area above 32 F of s h + c between ta and tb, as
; T0C/S03 $5BCC: no crossing and below: 0; a crossing moves ta to the root;
; s/2 (tb^2 - ta^2) + c (tb - ta), negated for a falling segment.
fg_seg: fld     fg_s
        jsr     SIGN
        pha
        fld     fg_s
        fop     FMULT, fg_ta
        fop     FADD, fg_c
        jsr     SIGN
        sta     fg_i2
        fld     fg_s
        fop     FMULT, fg_tb
        fop     FADD, fg_c
        jsr     SIGN
        clc
        adc     fg_i2
        beq     @cross
        bpl     @area
        pla
        jmp     ZERO_FAC
@cross: fld     fg_s
        fop     FDIV, fg_c
        jsr     negate
        fst     fg_ta
@area:  fld     fg_tb
        fop     FMULT, fg_tb
        fst     fg_q2
        fld     fg_ta
        fop     FMULT, fg_ta
        fop     FSUB, fg_q2
        fop     FMULT, fg_s
        fop     FMULT, f_half
        fst     fg_q2
        fld     fg_ta
        fop     FSUB, fg_tb
        fop     FMULT, fg_c
        fop     FADD, fg_q2
        pla
        cmp     #$FF
        bne     :+
        jmp     negate
:       rts
fg_sa_lo:  .byte <wc_peak, <wc_peak, <fg_a23
fg_sa_hi:  .byte >wc_peak, >wc_peak, >fg_a23
fg_ss_lo:  .byte <wc_morning, <wc_evening, <wc_night
fg_ss_hi:  .byte >wc_morning, >wc_evening, >wc_night
fg_sta_lo: .byte <wc_dawn, <wc_end, <fg_ta24
fg_sta_hi: .byte >wc_dawn, >wc_end, >fg_ta24
fg_stb_lo: .byte <wc_peak, <wc_peak, <wc_end
fg_stb_hi: .byte >wc_peak, >wc_peak, >wc_end
fg_40:  .byte $86,$20,0,0,0
fg_792: .byte $8A,$46,0,0,0
fg_s:    .res 5
fg_ta:   .res 5
fg_tb:   .res 5
fg_c:    .res 5
fg_q2:   .res 5
fg_d:    .res 5
fg_ta24: .res 5
fg_a23:  .res 5
fg_i:    .res 1
fg_i2:   .res 1
