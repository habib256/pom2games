; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; game.s -- Wilderness game logic, phases 1-2 (included by wild.s)
; ============================================================================
; The command line, the clock and the survival model of the original
; (docs/logic/*.md), computed like the original with the Applesoft floating
; point routines of the ROM:
;   - command line (letters and spaces, the 280-word vocabulary, last word of
;     each class wins), hours and ounces asked for separately;
;   - clock (hour, elapsed hours, date as a fraction of the year), energy
;     spent (base 1.65 kcal/min at rest, 5.2 walking, shivering extra),
;     water, food and rest
;     deficits, health = Hmax x product of the conditions (dehydration,
;     starvation, exhaustion: 100 (1 - (deficit / tolerance)^2)), death
;     under 0.3, GOAL% (progress toward the ranger outpost);
;   - dry/wet clothing, wind-adjusted temperature, body temperature, recovery
;     and thermal health factors
;     (thermal.s, with immersion and the documented reconstruction of bare skin);
;   - sun (declination, sunrise, sunset, night) and air temperature (season,
;     altitude, daily cycle) from the region climate of the map header;
;   - commands WALK, SWIM, REST, EAT, DRINK, GET, PACK, CARRY, WEAR, DROP, LOOK,
;     CLIMB TREE/DOWN, HANG FOOD, LOWER FOOD/BACKPACK,
;     ENTER/EXIT SHELTER, TOPO, VIEW, STATUS,
;     INVENTORY, HELP; the rest answers "not in this version yet".
; Initial food/water/rest accounting is compared with the original by
; test_adventure.py. Weather, walking and several health rules still differ;
; see docs/ADVENTURE_TESTS.md. Scalar/model tests do not prove full parity.
; ============================================================================

; Applesoft ROM floating point (FAC = floating accumulator at $9D-$A2)
MOVFM   = $EAF9                 ; FAC <- (A,Y)
MOVMF   = $EB2B                 ; (X,Y) <- FAC
FADD    = $E7BE                 ; FAC <- (A,Y) + FAC
FSUB    = $E7A7                 ; FAC <- (A,Y) - FAC
FMULT   = $E97F                 ; FAC <- (A,Y) * FAC
FDIV    = $EA66                 ; FAC <- (A,Y) / FAC
FCOMP   = $EBB2                 ; A <- 1, 0, $FF as FAC >, =, < (A,Y)
GIVAYF  = $E2F2                 ; FAC <- signed A (hi), Y (lo)
AYINT   = $E10C                 ; FAC -> signed int, $A0 (hi) $A1 (lo)
FSQR    = $EE8D
FSIN    = $EFF1
FATN    = $F09E
FEXP    = $EF09
FAC     = $9D
FACSGN  = $A2
CLREOP  = t_clreop             ; own text primitives (dhgr.s)

M_GOALX  = MAP + 8              ; goal cell
M_GOALY  = MAP + 9
M_LAT    = MAP + 12             ; latitude, degrees (signed)
M_TWIN   = MAP + 13             ; winter / summer mean temperature (deg F)
M_TSUM   = MAP + 14
M_WIND   = MAP + 15             ; highest wind (mph)
M_MAG    = MAP + 24             ; signed magnetic declination, degrees

MAXLINE  = 36                   ; typed command (row 23, src/menu.s)

.macro  fld     addr
        lda     #<(addr)
        ldy     #>(addr)
        jsr     MOVFM
.endmacro
.macro  fst     addr
        ldx     #<(addr)
        ldy     #>(addr)
        jsr     MOVMF
.endmacro
.macro  fop     routine, addr
        lda     #<(addr)
        ldy     #>(addr)
        jsr     routine
.endmacro

.segment "GZP": zeropage
gp1:     .res 2                 ; pointers
gp2:     .res 2
g0:      .res 1                 ; scratch
g1:      .res 1
g2:      .res 1
verb:    .res 1                 ; parsed command
qual:    .res 1
noun:    .res 1
found:   .res 1
linelen: .res 1
msgnum:  .res 2                 ; number shown by '#' in a message
minutes: .res 2                 ; time left to spend (advance)
used:    .res 2                 ; minutes walked
act:     .res 1                 ; 0 rest, 1 walk, 2 meal, 3 hang pack
stepmin: .res 1
wdx:     .res 2                 ; walking direction (8.8 cells per step)
wdy:     .res 2
nx:      .res 2                 ; next position
ny:      .res 2
shown:   .res 1                 ; a message is on the message lines
; $A4 is Applesoft's rounding byte: foliage must not leave it nonzero.
forest_crown_end: .res 1        ; forest.s
tilt:    .res 1                 ; view tilt: 0 level, 1 up, $FF down (LOOK U/D)


; ----------------------------------------------------------------------------
; Module overlays. Every module image is preloaded in auxiliary RAM; loading
; one copies its pristine image into its main window (memory.s), as the DOS
; BLOAD did, without any disk access. No call replaces its caller's window:
; simulation at $9600 may request input at $5800.
; overlay_reads counts these module loads (RAM copies or, for the optional
; native geography banks only, MLI reads), the HGR version's disk reads.
; ----------------------------------------------------------------------------
.segment "GDATA"
overlay_current: .byte 0
overlay_wanted: .byte 0
overlay_reads: .word 0
sim_loaded: .byte 0
sim_quiet: .byte 0
.segment "SCRATCH"
overlay_text: .res 160          ; scratch shared by sprites and sky
.segment "GCODE"

scr_status:
        jsr     status_fetch
        jmp     module_status
; INVENTORY shares the STATUS module: the load totals (SIM) first.
scr_inventory:
        jsr     load_totals_quiet
        jsr     status_fetch
        jmp     module_inventory
status_fetch:
        ldx     #16             ; STATUS -> $9600 (SIM is reloaded later)
        XL_ABS  XI_GAME, sim_fetch, @p05        ; (XL: from NEOWILD.BLK, 16 blocks
        jsr     mem_fetch                       ; up to $B5FF; docs/MEMORY.md 29)
        lda     #0
        sta     sim_loaded
        sta     sim_quiet
        rts
.segment "TEXT"                 ; (moved out of WILDGAME for the site sprites)
env_day:
        lda     #3
        jsr     overlay_load
        jmp     module_env_day
env_hour:
        lda     #3
        jsr     overlay_load
        jmp     module_env_hour

thermal:
        lda     #3
        jsr     overlay_load
        jmp     module_thermal
.segment "GCODE"

; A site sprite (scene_asset SITE_ASSET.., the log, the rock, the outpost)
; lives in the SIM window: PROJECT checks it is still there, else reads it
; from NEOWILD.BLK (module_site_load). The $5800 window then holds PROJECT.
site_load:
        pha
        lda     #11
        jsr     overlay_load
        pla
        jmp     module_site_load

overlay_load:
        cmp     #SITE_ASSET
        bcs     site_load
        cmp     #18
        bne     :+
        lda     #17             ; hazards and medical share one image
:       cmp     #3
        beq     @sim
        cmp     overlay_current
        bne     @load
        rts
@sim:   lda     sim_loaded
        beq     :+
        rts
:       lda     #1              ; keep the completed landscape during SIM;
        sta     ui_dirty        ; hide it only when its redraw actually starts
        lda     #3
@load:  sta     overlay_wanted
overlay_before_transfer = *
        tax
        jsr     mem_fetch
        lda     overlay_wanted
        cmp     #3
        bne     @ordinary
        inc     sim_loaded
        bne     @count
@ordinary:
        sta     overlay_current
@count:
        inc     overlay_reads
        bne     :+
        inc     overlay_reads+1
:
overlay_ready = *
        rts
.export overlay_before_transfer, overlay_ready

.segment "GDATA"
tree_in: .byte 0
tree_pack_place: .byte 0
.segment "GCODE"

; ----------------------------------------------------------------------------
; state (initial values: the first journey)
; ----------------------------------------------------------------------------
.segment "GDATA"
px:      .word  0               ; position, 8.8 cells (lo = fraction)
py:      .word  0
heading: .word  0               ; 0..559, 0 = north, 140 = east
dead:    .byte  0
journey_left: .word 0
journey_steps: .word 0
journey_halfcells: .word 0
journey_encounters: .word 0
outdoor_minutes: .byte 0
outdoor_result: .byte 0
outdoor_act: .byte 0
water_untreated: .byte 0
water_ground_untreated: .byte 0
water_drinking_untreated: .byte 0
water_rng: .byte $B7
.export water_rng, fauna_rng, weather_seed   ; free journey seeds (boot.s)
weak_health: .byte 0
won:     .byte  0
night:   .byte  0
shelter_inside: .byte 0         ; found cabin; distinct from crafted HUT
newday:  .byte  0
period:  .byte  0               ; 0 night, 1 dawn, 2 am, 3 pm, 4 dusk
airtemp: .byte  0               ; deg F, signed
wind:    .byte  7               ; mph
felt_temp: .word 0              ; signed F, wind-adjusted; no byte wrap
body_weight: .word 165          ; pounds, original first-journey value
cachex:  .byte  0               ; cell where the ground items are
cachey:  .byte  0
inbuf:   .res   MAXLINE+1
nounbuf: .res   13

; floats (5 bytes, Applesoft format)
s_hour:  .byte  $83, $60, $00, $00, $00        ; 7
s_elap:  .res   5                               ; 0
s_date:  .byte  $7F, $30, $58, $63, $3E        ; 0.34442 (May 6)
s_spent: .byte  $8A, $16, $00, $00, $00        ; 600 kcal
s_eaten: .byte  $8A, $7A, $00, $00, $00        ; 1000 kcal
s_drink: .byte  $82, $00, $00, $00, $00        ; hours since drinking: 2
s_eat:   .byte  $82, $00, $00, $00, $00        ; since eating
s_rest:  .byte  $82, $00, $00, $00, $00        ; since resting
s_defw:  .res   5               ; deficits (hours): water, food, rest
s_deff:  .res   5
s_defr:  .res   5
s_last:  .repeat 3
        .byte $82,$80,0,0,0     ; original A1[16..18], -2 hours
        .endrepeat
health_minutes: .word 0
health_period: .byte 15
health_due: .byte 0
fire_pos: .res  6               ; MAKE FIRE (fire.s fire_light): px, py,
fire_cx  = fire_pos+1           ; heading then: the fire's cell and its
fire_cy  = fire_pos+3           ; bearing in the view (src/fire.s)
fire_bear = fire_pos+4
.export fire_cx, fire_cy, fire_bear
meal_remaining: .byte 0
s_health: .byte $83, $7B, $BB, $44, $34        ; saved first journey Hmax
s_body:  .byte $87, $45, $33, $33, $33  ; 98.6 F
s_therm_rate: .res 5             ; signed F/hour
s_therm_factor: .byte $81, 0, 0, 0, 0 ; health multiplier, initially 1
s_insul: .res 5
s_metabolic: .res 5             ; activity kcal/min
s_step: .res 5                  ; minutes of the current simulation step
thermal_zone: .byte 0           ; actual branch: neutral/hot/cold
thermal_mode: .byte 2           ; first journey starts shivering ($4B87 = 1)
wet_mode: .byte 0               ; 0 dry, 1 wet, 2 immersed (original $4B70)
s_d0:    .res   5               ; start -> goal distance (units)
s_rise:  .res   5               ; sunrise, sunset (hours)
s_set:   .res   5
s_t0:    .res   5               ; mean sea-level temperature of the day
t1:      .res   5               ; scratch floats
t2:      .res   5
t3:      .res   5
t4:      .res   5
t5:      .res   5
travel_major: .res 1            ; original-unit raster, retained across overlays
travel_axis:  .res 1
travel_sign:  .res 1
travel_accum: .res 5
travel_delta: .res 5

        .include "gamedata.inc" ; build/, from tools/gendata.py

.segment "GCODE"

; ----------------------------------------------------------------------------
; game_start -- after the view engine's initialisation
; ----------------------------------------------------------------------------
game_start:
        lda     #21
        jsr     overlay_load
        jsr     module_game_init
        jsr     show_view
        lsr     view_loading+1  ; subsequent redraws use the clean curtain
        lda     #<m_crash
        ldx     #>m_crash
        jsr     message
        jmp     main

.segment "GCODE"
; main loop: read a command, parse it, run it
main:   lda     dead
        ora     won
        bne     the_end
        jsr     get_line
main_command:
        jsr     camp_command_begin
        lda     #0
        sta     shown
        jsr     do_command
main_command_done:
        jsr     finish_simulation
        jsr     alerts_after    ; lot 13: original alerts, forced sleep, summary
        jmp     main

the_end:
        lda     #21
        jsr     overlay_load
        jmp     module_ending

; ----------------------------------------------------------------------------
; command line
; ----------------------------------------------------------------------------
; get_line and prompt: src/menu.s (the four 80-column rows, lot 8).
.segment "CODE"
vtab:
        sta     vtab_target+1
        lda     text_vector_hi
        beq     vtab_set
vtab_pad:
        lda     CV
        cmp     vtab_target+1
        bcs     vtab_set
        jsr     topo_pad
        inc     CV
        jsr     t_vtab
        lda     #0
        sta     CH
        beq     vtab_pad
vtab_set:
vtab_target:
        lda     #0
        sta     CV
        lda     #0
        sta     CH
        jmp     t_vtab
.segment "GCODE"

; Common inline durations are resident; the general numeric reader remains
; in INPUT for prompted entry, quantities and more elaborate syntax.
.segment "GCODE"
get_duration:
        jmp     duration_entry
get_quantity:
        ldy     #2
        bne     number_entry
get_number:
        ldy     #0
number_entry:
        sty     input_mode
        cpy     #1
        bne     :+
        pha                     ; A/X hold the prompted duration message
        lda     input_argument
        cmp     #2              ; fully validated resident inline duration
        bne     @prompted
        pla
        lda     #0
        sta     shown
        clc
        rts
@prompted:
        pla
:
        cpy     #2
        beq     @load
        ldy     input_argument
        bne     :+
        jsr     message
:
@load:  lda     #13
        jsr     overlay_load
        jmp     module_number

; Either duration reader can return without an INPUT module being present.
prepare_minutes:
        lda     input_unit
        cmp     #2
        jne     mul60
        lda     msgnum
        sta     minutes
        lda     msgnum+1
        sta     minutes+1
        rts

.segment "SCRATCH"
input_argument: .res 1
input_value: .res 2
input_unit: .res 1
input_mode: .res 1
input_interrupted: .res 1
stock_available: .res 2
parser_word_seen: .res 1
parser_badverb: .res 1
travel_reason: .res 1
travel_action: .res 1
load_excess: .res 8
load_free: .res 8
load_reason_weight: .res 1
load_reason_volume: .res 1
load_reason_overflow: .res 1
.segment "GCODE"

; ----------------------------------------------------------------------------
; parser: words of inbuf against the vocabulary (lists by length)
; ----------------------------------------------------------------------------
; Exact travel/rest and screen commands need no vocabulary disk read.
; Qualified, longer and unknown commands retain the complete original parser.
do_command:
        lda     #0
        sta     input_argument
        sta     travel_action
        sta     parser_word_seen
fast_command:
        ldx     #0
@word:  stx     g0
        lda     fast_words,x
        beq     @full
        sta     g2
        cmp     linelen
        bcc     :+
        bne     @next
:
        ldy     #0
@letter:
        inx
        lda     fast_words,x
        cmp     inbuf,y
        bne     @next
        iny
        cpy     g2
        bcc     @letter
        cpy     linelen
        beq     @dispatch
        lda     fast_words+1,x
        bpl     @next           ; screens cannot accept a duration
        jsr     fast_duration
        bcs     @next
@dispatch:
        inx
        lda     fast_words,x
        pha
        lda     #0
        sta     qual
        sta     noun
        sta     nounbuf
        sta     verb
        sta     parser_badverb
        lda     #1
        sta     found
        pla
        bmi     @travel
        sta     noun
        sec
        sbc     #N_TOPO
        tax
        lda     screen_lo,x
        sta     gp1
        lda     screen_hi,x
        sta     gp1+1
        jmp     (gp1)
@travel:
        pha
        and     #63
        sta     verb
        pla
        and     #64
        bne     @rest
        jmp     do_walk
@rest:  jmp     do_rest
@next:  lda     g0
        clc
        adc     g2
        adc     #2
        tax
        jmp     @word
@full:  lda     parser_word_seen
        bne     @parse
        jmp     general_command
@parse: jsr     parse
        jmp     dispatch
.segment "LOWTEXT"
; Bit 7 identifies a duration verb; bit 6 distinguishes rest from travel.
fast_words:
        .byte 4,"WALK",V_WALK|$80,4,"REST",V_REST|$C0,4,"SWIM",V_SWIM|$80
        .byte 5,"SLEEP",V_REST|$C0
        .byte 4,"TOPO",103,4,"VIEW",104,6,"STATUS",105
        .byte 9,"INVENTORY",106,4,"HELP",107,3,"MAP",109
        .byte 9,"EQUIPMENT",110
        .byte 1,"M",109,1,"T",103,1,"S",105,0   ; one key: MAP, TOPO, STATUS (alone only)
.segment "RODATA"
; Complete input/vocabulary fallback runs at most once per command.
general_command:
        ldx     #0
@scan:  lda     inbuf,x
        beq     @ordinary
        cmp     #'Q'
        beq     @input
        cmp     #'0'
        bcc     @next_char
        cmp     #'9'+1
        bcc     @input
@next_char:
        inx
        bne     @scan
@input: inc     parser_word_seen
        lda     #13
        jsr     overlay_load
        jsr     module_input_command
        bcs     :+
        jmp     fast_command
:       rts
@ordinary: jsr parse
        jmp     dispatch

; Positive byte-sized durations preserve X, the fast-word table cursor.
; Larger numbers and other forms leave the line intact for INPUT.
fast_duration:
        lda     inbuf,y
        cmp     #' '
        bne     @bad
@spaces:
        iny
        lda     inbuf,y
        cmp     #' '
        beq     @spaces
        cmp     #'0'
        bcc     @bad
        cmp     #'9'+1
        bcs     @bad
        lda     #0
        sta     input_value
@digit: lda     inbuf,y
        cmp     #'0'
        bcc     @digits_done
        cmp     #'9'+1
        bcs     @digits_done
        and     #15
        sta     g1
        lda     input_value
        cmp     #26
        bcs     @bad
        cmp     #25
        bcc     @multiply
        lda     g1
        cmp     #6
        bcs     @bad
        lda     input_value
@multiply:
        jsr     fast_digit
        iny
        bne     @digit
@bad:   sec
        rts
@digits_done:
        lda     input_value
        beq     @bad            ; zero keeps the existing cancellation path
        lda     #1
        sta     input_unit
@unit_spaces:
        lda     inbuf,y
        cmp     #' '
        bne     @unit
        iny
        bne     @unit_spaces
@unit:  cmp     #0
        beq     @good
        cmp     #'H'
        beq     @hour
        cmp     #'M'
        bne     @bad
        iny
        lda     inbuf,y
        cmp     #'I'
        bne     @bad
        iny
        lda     inbuf,y
        cmp     #'N'
        bne     @bad
        inc     input_unit
@hour:  iny
@tail:  lda     inbuf,y
        beq     @good
        cmp     #' '
        bne     @bad
        iny
        bne     @tail
@good:  jmp     fast_accept
.segment "GCODE"
; A = previous byte value, g1 = next digit, already checked for overflow.
fast_digit:
        asl
        sta     input_value
        asl
        asl
        clc
        adc     input_value
        clc
        adc     g1
        sta     input_value
        rts

fast_accept:  lda     input_value
        sta     msgnum
        lda     #0
        sta     msgnum+1
        ldy     g2
        sty     linelen
        sta     inbuf,y
        lda     #2
        sta     input_argument
        clc
        rts

parse:  lda     #1
        jsr     overlay_load
        jmp     module_parse
.segment "VOCAB"
module_parse:
        lda     #0
        sta     verb
        sta     qual
        sta     noun
        sta     found
        sta     parser_word_seen
        sta     parser_badverb
        ldx     #0              ; X = position in inbuf
@skip:  lda     inbuf,x
        beq     @end
        cmp     #' '
        bne     @word
        inx
        bne     @skip
@word:  stx     g0              ; start
@len:   lda     inbuf,x
        beq     @got
        cmp     #' '
        beq     @got
        inx
        bne     @len
@got:   stx     g1              ; end
        txa
        sec
        sbc     g0
        sta     g2              ; length
        cmp     #13
        bcs     @next
        jsr     lookup
@next:  lda     parser_word_seen
        bne     :+
        inc     parser_word_seen
        lda     found
        bne     :+
        inc     parser_badverb
:       ldx     g1
        jmp     @skip
@end:   rts

.segment "GCODE"
; lookup -- the word inbuf[g0], length g2: sets verb / qual / noun
lookup: ldx     g2
        lda     voc_len_lo-1,x
        sta     gp1
        lda     voc_len_hi-1,x
        sta     gp1+1
@entry: ldy     #0
        lda     (gp1),y
        cmp     #$FF
        beq     @none
        ldx     g0
@cmp:   lda     (gp1),y
        cmp     inbuf,x
        bne     @skip
        inx
        iny
        cpy     g2
        bcc     @cmp
        lda     (gp1),y         ; code: noun < 200 <= verb < 245 <= qualifier
        ldx     #2
        cmp     #200
        bcc     @class
        ldx     #0
        sbc     #200
        cmp     #45
        bcc     @class
        ldx     #1
        sbc     #45
@class: sta     verb,x          ; verb, qual, noun are consecutive
        lda     #1
        sta     found
        cpx     #2
        bne     @none
        ldx     g0              ; keep the noun's text for messages
        ldy     #0
@copy:  lda     inbuf,x
        sta     nounbuf,y
        inx
        iny
        cpy     g2
        bcc     @copy
        lda     #0
        sta     nounbuf,y
@none:  rts
@skip:  lda     g2              ; next entry: length + 1 byte
        sec                     ; (+1 by the carry)
        adc     #0
        clc
        adc     gp1
        sta     gp1
        bcc     @entry
        inc     gp1+1
        bcs     @entry

; ----------------------------------------------------------------------------
; dispatch
; ----------------------------------------------------------------------------
; Lot 2 fidelity (docs/CAMP.md section 6): DRINK credits oz x (.73 - .6 x
; $4C7A) with the evolving $4C7A and sets care selector 6, as T0F/S00; 0
; keeps the frozen .38 of the HGR reference.
DRINK_FIDELITY = 0              ; integration: 0 until the reference is rebased (lot 2 fidelity, 5c72719)
V_GET   = 1
V_USE   = 2
V_WEAR  = 5
V_PACK  = 6
V_CARRY = 7
V_DROP  = 8
V_DRINK = 10
V_EAT   = 12
V_LOOK  = 16
V_WAIT  = 19
V_REST  = 20
V_CAMP  = 21
V_WALK  = 22
V_RUN   = 23
V_SWIM  = 24
V_CLIMB = 25
V_LOWER = 29
V_HANG  = 34
V_MOVE  = 27
V_PAN   = 36
V_EXIT  = 39
V_ENTER = 40
V_CRAWL = 43
V_EXER  = 44
N_WATER = 22
N_COMPASS = 53
N_TOPO  = 103
N_HELP  = 107

.segment "VOCAB"
; Qualifiers identify the original's five shared nouns.
resolve_noun:
        lda     qual
        cmp     #2              ; COTTON SOCKS
        bne     @kit
        lda     noun
        cmp     #6
        bne     @done
        lda     #18
        bne     @set
@kit:   lda     noun
        cmp     #41
        bne     @tab
        lda     qual
        cmp     #4              ; SNAKEBITE KIT
        bne     @sew
        lda     #42
        bne     @set
@sew:   cmp     #5              ; SEWING KIT
        bne     @done
        lda     #65
        bne     @set
@tab:   cmp     #46
        bne     @done
        lda     qual
        cmp     #7              ; SALT TABLETS
        bne     @done
        lda     #48
@set:   sta     noun
@done:  rts

.segment "GCODE"
; resolve_menu -- an item chosen in a list of the menu (src/menu.s) names
; the noun: its display name is not the vocabulary's (COTTN SOCKS).
resolve_menu:
        lda     menu_noun
        bne     :+
        jsr     resolve_noun
        jmp     forage_gate     ; lot 4: its commands end there
:       sta     noun
        jmp     forage_gate
.segment "VOCAB"
dispatch:
        jsr     resolve_menu
        lda     parser_badverb
        beq     :+
        lda     #<m_unknown
        ldx     #>m_unknown
        jmp     message
:       lda     linelen
        bne     :+
        rts
:
        lda     found
        bne     @known
        lda     #<m_what
        ldx     #>m_what
        jmp     message
@known: lda     noun
        cmp     #177            ; NATURE: original frequency control
        bne     :+
        jmp     do_nature
:       lda     noun            ; screens: TOPO VIEW STATUS INVENTORY HELP CLUE
        cmp     #N_TOPO
        bcc     @verb
        cmp     #N_HELP+2
        bcs     @verb
        sbc     #N_TOPO-1       ; carry clear: 1..6 -> 0..5
        tax
        lda     screen_lo,x
        sta     gp1
        lda     screen_hi,x
        sta     gp1+1
        jmp     (gp1)
@verb:  ldx     #0
@find:  lda     verbs,x
        beq     @none
        cmp     verb
        beq     @go
        inx
        bne     @find
@go:    lda     verb_lo,x
        sta     gp1
        lda     verb_hi,x
        sta     gp1+1
        jmp     (gp1)
@none:  lda     verb
        bne     @later
        lda     #<m_oops
        ldx     #>m_oops
        jmp     message
@later: jmp     verb_more       ; lot 13 care verbs, then lot 2 MAKE/BUILD, BOIL (camp_verb)

; ----------------------------------------------------------------------------
; screens
; ----------------------------------------------------------------------------
.segment "GCODE"
do_nature:
        lda     #13
        jsr     overlay_load
        jmp     module_nature

; CLUE reaches this only after the vocabulary overlay has been loaded.
.segment "VOCAB"
scr_notyet:
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message

scr_view = show_view
.segment "GCODE"

; HELP joins STATUS and INVENTORY in the STATUS module (SIM window): the
; former SCREENS module (2) is gone.
.pushseg
.segment "CODE"
scr_help:
        jsr     status_fetch
        jmp     module_help
.popseg
.segment "STATUS"
; HELP, a page of the cycle (src/pages.s): four blocks on one 80-column
; page, a block's first line its heading (inverse). Written row by row (no
; stale cell, differential): band 1 from row 2 has TRAVEL at column 0 and
; EQUIPMENT at ST_RIGHT, band 2 from row 12 SURVIVAL and HEALTH; the two
; blocks of a band advance a line a row, each stopping at its 0.
module_help:
        lda     #PG_HELP
        jsr     page_top
        lda     #BANK_DISK
        sta     SITE_ENTRY
        lda     help_disk_block
        sta     SITE_ENTRY+1
        lda     help_disk_block+1
        sta     SITE_ENTRY+2
        lda     help_disk_length
        sta     SITE_ENTRY+3
        lda     help_disk_length+1
        sta     SITE_ENTRY+4
        lda     #0
        sta     SITE_ENTRY+5
        lda     #$58
        sta     SITE_ENTRY+6
        ldx     #TB_FETCH
        jsr     mem_fetch
        lda     SITE_BANK_OF
        sta     SITE_ENTRY
        lda     #0
        sta     SITE_ENTRY+4
        lda     #$FF
        sta     overlay_current
        jmp     module_help_body
help_disk_block: .word 0
help_disk_length: .word 0
.segment "GCODE"
do_site:
        lda     #10
        jsr     overlay_load
        jmp     module_site
scr_map:
        lda     #10
        jsr     overlay_load
        jmp     module_topo
scr_topo:
        lda     #10
        jsr     overlay_load
        jmp     module_graphical_topo
shelter_view:
        lda     #10
        jsr     overlay_load
        jmp     module_shelter_view

; show_view -- landscape by day/full Moon; dark sky and no landscape otherwise
show_view:
        jsr     view_hide
show_view_hidden:
        jsr     scene_update
        lda     #0
        sta     sim_loaded
        jsr     summary_prepare
        jsr     show_view_scene
        jmp     show_dhgr
show_view_scene:
        lda     shelter_inside
        beq     :+
        jsr     shelter_view
        jmp     hud_draw
:
        jsr     stars_view_dark ; star list of the hour, then lda view_dark
        bne     @dark
        jsr     scene_prepare
        jsr     view_full
        jmp     animal_view
@dark:  lda     #0
        sta     scene_drawn
        ; view_full clears the terrain before the dark-sky pass.
        jsr     view_full
        jsr     animal_view     ; the animal, a night silhouette (2026-10-15)
        lda     shown
        bne     @done
        lda     #<m_nolight
        ldx     #>m_nolight
        jmp     message
@done:  rts
; animal_view -- after the view (show_view_scene): an animal is always seen
; while it is there, but in the shelters (no view) and looking up (PROJECT
; module_animal, docs/LOOK_UPDOWN.md 5).
animal_view:
        lda     animal_kind
        beq     @none
        lda     #11
        jsr     overlay_load
        jmp     module_animal
@none:  rts
; animal_unpan -- (turn_view, scene_drawn $83) the background under the
; animal back on screen (OUTDOOR), then the scene of the view again (PROJECT
; module_project: the site's sprite_*, which the animal's replaced): the
; view scrolls, animal_view draws the animal after. Keeps X.
animal_unpan:
        txa
        pha
        lda     #22
        jsr     overlay_load
        jsr     module_animal_unbg
        lda     #11
        jsr     overlay_load
        jsr     module_project
        pla
        tax
        rts

.segment "LOWCODE"
; ----------------------------------------------------------------------------
; Night stars (lot 7 step 5, docs/STARS.md). The visible list (st_a...) and
; stars_frame, stars_column (src/stars_draw.s) are in bank 2 of the main
; language card (SKYRES, $DE00): the two wrappers below select it for
; reading (write-protected), call, and give the ROM back. ProDOS 8 keeps
; only its QUIT code in that bank ($D100-$D3FF); render masks interrupts.
; Each hook replaces one instruction of the same size in CODE/GCODE.

; stars_dhgr_frame -- render_frame: dhgr_frame, then the stars of the mood.
stars_dhgr_frame:
        lda     tilt            ; LOOK UP / DOWN: constants of a new tilt
        cmp     tilt_shown
        beq     :+
        jsr     tilt_apply
:       jsr     dhgr_frame
        lda     tilt            ; looking up: no sprite (the original's rule)
        cmp     #1
        bne     :+
        sta     draw_dark
:       bit     $C080           ; main language card RAM, bank 2, read only
        jsr     stars_frame
        bit     $C082           ; ROM again
        rts

; stars_span -- stars_column's spans: dspan gives the ROM back (its rows are
; in bank 2 too, src/dhgr.s), the stars' code needs bank 2 again.
stars_span:
        jsr     scene_span
        bit     $C080
        rts

; stars_sky_column -- render_sky: the stars of the column, then the Moon.
stars_sky_column:
        bit     $C080
        jsr     stars_column
        bit     $C082
        jmp     sky_column

; stars_view_dark -- show_view_scene, before the view: recompute the list
; when sky_position changed the hour (stars_stale) and it is night, then
; lda view_dark. The module (ID 25) runs in the SIM window $9600, which both
; callers of show_view_scene have released (sim_loaded = 0; cleared again
; here: the next simulation copies its pristine image back); the $5800
; window keeps its module, so overlay_current is kept too. The module uses
; the zero page $5E-$A1, free between two commands, and no random draw.
stars_view_dark:
        lda     tilt            ; LOOK UP has its own projection: a list
        cmp     #1              ; computed for the other one is stale
        beq     :+
        lda     #0
:       cmp     stars_list_up
        beq     :+
        inc     stars_stale
:       lda     stars_stale
        beq     @done
        lda     night           ; the list only serves night moods
        beq     @done
        lda     overlay_current
        pha
        lda     #25
        jsr     overlay_load
        jsr     module_sky_stars
        pla
        sta     overlay_current
        lda     #0
        sta     sim_loaded
        sta     stars_stale
@done:  lda     view_dark
        rts

; stars_mark -- end of sky_position (dhgr.s): the Sun or Moon of a new hour.
stars_mark:
        sta     moon_phase
        lda     #1
        sta     stars_stale
        rts

.segment "LOWTEXT"
stars_stale: .byte 1            ; 1: compute the list at the next night view
AB_J0:  .byte 0                 ; the animal's background (OUTDOOR ab_copy):
AB_N:   .byte 0                 ; its first byte, bytes - 1 (PROJECT)
stars_list_up: .byte 0          ; the list's projection: 1 LOOK UP (stars.s st_inputs)
.segment "GCODE"

; Commands such as EAT/DRINK leave no explicit VIEW call. Restore their
; picture silently: preserve their messages and do not add key prompts.
.segment "LOWCODE"
finish_simulation:
        lda     sim_loaded
        beq     @done
        lda     #0
        sta     sim_loaded
        lsr     sim_quiet       ; loaded quietly: the view was never hidden
        bcs     @done
        jsr     view_hide       ; SIM kept the old frame; hide partial drawing
        jsr     summary_prepare
        lda     shown
        pha
        lda     #1              ; restore silently, including night/cabin views
        sta     shown
        jsr     show_view_scene
        pla
        sta     shown
        jmp     show_dhgr
@done:  rts

.segment "CODE"
turn_view:                      ; X = view_turn kind; fixed geometry scrolls with terrain
        lda     shelter_inside  ; a dark night scrolls too: its stars and ridge
        bne     @full           ; depend on the azimuth alone (lot 7)
        lda     scene_drawn
        bpl     :+              ; $83: the animal's background is kept
        jsr     animal_unpan
        lda     scene_drawn
:       cmp     #2
        bcs     @full          ; multiple candidates require nearest-visible selection
@pan:   jsr     scene_pan_load
        clc
        bcc     @turn
@full:  sec
@turn:  php
        jsr     view_turn
        plp
        bcc     :+
        jmp     show_view
:       jmp     animal_view     ; the animal again, centred

.segment "GCODE"
; ----------------------------------------------------------------------------
; verbs
; ----------------------------------------------------------------------------
do_look:
        jmp     module_tree_look
look_invalid:
        lda     #<m_oops
        ldx     #>m_oops
        jmp     message
do_tree:
        lda     #26
        jsr     overlay_load
        jmp     module_tree_command

magnetic_heading:
        lda     #3
        jsr     overlay_load
        lda     #12
        jsr     overlay_load
        jmp     module_magnetic_heading
game_init_environment:
        jsr     env_day
        jsr     env_hour
        jmp     game_init_restore
game_init_hud:
        jsr     hud_init
        jmp     ui_monitor
.segment "TRAVEL"
module_magnetic_heading:
        ; T10/S0C adds TOPO $60A9 to magnetic cardinal directions.
        lda     orient_aid      ; COMPASS in use (lot 7, src/orient.s)
        lsr     a
        bcc     @declination
        jsr     weather_random
        fop     FSUB, f_half
        jsr     negate
        fop     FMULT, f_4     ; native compass precision, W9 = 4 degrees
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        fst     compass_error
        jmp     @magnetic
@declination:
        fld     f_zero
        fst     compass_error
@magnetic:
        ldy     M_MAG
        lda     #0
        cpy     #128
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FADD, compass_error
        fop     FMULT, f_deg_heading
        fop     FADD, f_half    ; nearest port azimuth, not a biased truncation
        jsr     AYINT
        clc
        lda     heading
        adc     $A1
        sta     ang
        lda     heading+1
        adc     $A0
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     heading
        lda     ang+1
        sta     heading+1
        rts
compass_error: .res 5
.segment "GCODE"

.pushseg
.segment "BSS"
route_x: .res 1
route_y: .res 1
route_active: .res 1
route_setting: .res 1
.segment "TEXT"
travel_remaining: .word 0
travel_pending: .byte 0
travel_next_minutes: .byte 0
travel_heading: .word 0

travel_ui_load:
        lda     #10
        jsr     overlay_load
        jmp     trip_load
travel_state_save:
        ldx     #1
@copy:  lda     heading,x
        sta     travel_heading,x
        lda     minutes,x
        sta     travel_remaining,x
        dex
        bpl     @copy
        ora     minutes+1       ; A still holds the low byte after the loop
        beq     @done
        lda     verb
        sta     travel_pending
@done:  rts
.popseg

; WALK, GO, RUN, MOVE, CRAWL, SWIM: hours, then cells along the
; heading. WALK and SWIM use original integer-unit raster paths and costs.
; Both stop before the two-cell outer band; a rejected step spends no time.
do_walk:
        lda     tree_in
        beq     :+
        jmp     do_tree
:
        lda     shelter_inside
        beq     :+
        jmp     do_site
:
        jsr     camp_walk       ; douse the fire first (M5), then LDA night:
        beq     :+              ; no first step when already after sunset
        lda     #<m_dark
        ldx     #>m_dark
        jmp     message
:
        jsr     travel_ui_load
        jsr     navigation_travel_duration
        bcc     :+
        rts
:       lda     #0              ; travel levels the view (as the original)
        sta     tilt
        lda     verb
        cmp     #V_SWIM
        bne     @walk_prepare
        jsr     swim_prepare
        jmp     @prepared
@walk_prepare:
        jsr     walk_prepare
@prepared:
        lda     #0
        sta     fauna_alert     ; this trip has no new encounter before its first step
        sta     used
        sta     used+1
        sta     input_interrupted
        sta     travel_shore
        sta     travel_reason
        inc     travel_action
@cell:  lda     KBD
        cmp     #KC_ESC|$80
        beq     @cancel
        bit     $C062
        bpl     :+
@cancel:bit     KBDSTRB
        inc     input_interrupted
        jmp     @stop
:       jsr     swim_next
        clc
        lda     px
        adc     wdx
        sta     nx
        lda     px+1
        adc     wdx+1
        sta     nx+1
        cmp     #2              ; leave two full cells outside the travel area
        bcs     :+
        jmp     @edge
:
        cmp     #GW-2
        bcc     :+
        jmp     @edge
:
        clc
        lda     py
        adc     wdy
        sta     ny
        lda     py+1
        adc     wdy+1
        sta     ny+1
        cmp     #2
        bcs     :+
        jmp     @edge
:
        cmp     #GH-2
        bcc     :+
        jmp     @edge
:
        jsr     native_next
        bpl     @land
        ldx     verb
        cpx     #V_SWIM
        beq     @swim
        jsr     native_walk_water
        jcc     @stop
@land:  ldx     verb
        cpx     #V_SWIM
        bne     :+
        jsr     swim_land
        jcc     @stop
        jmp     @swim
:       sta     g0
        jsr     native_here
        and     #$7F
        sta     g1
        jsr     walk_step
        bcc     @time
        jmp     @pace
@swim:  lda     used
        ora     used+1
        bne     :+
        lda     #15             ; T08/S07 $5AEE: first swimming health interval
        sta     health_period
:       jsr     swim_step
        bcc     :+
        jmp     @pace
:       jmp     @time
@time:  jsr     travel_short_budget
        bne     @go
        lda     stepmin
        cmp     minutes         ; a complete native step must fit the budget
        bcc     @go
        beq     @go
        jmp     @time_end
@go:    sec
        lda     minutes
        sbc     stepmin
        sta     minutes
        lda     minutes+1
        sbc     #0
        sta     minutes+1
        clc
        lda     used
        adc     stepmin
        sta     used
        bcc     :+
        inc     used+1
:       lda     nx
        sta     px
        lda     nx+1
        sta     px+1
        lda     ny
        sta     py
        lda     ny+1
        sta     py+1
        jsr     forage_here     ; lot 4: the ground piles stay behind
        lda     verb
        cmp     #V_SWIM
        beq     :+
        jsr     walk_climb
:
        lda     stepmin
        ldx     #1
        jsr     spend
@progress:
        lda     #10
        jsr     overlay_load
        jsr     module_topo_moving ; the minutes are in the map's cue
        lda     #0              ; progress never asks for acknowledgement
        sta     shown
        jsr     at_goal
        lda     dead
        ora     won
        ora     fauna_alert
        bne     @stop
        lda     travel_shore
        bne     @shore
        lda     night
        bne     :+
        lda     minutes
        ora     minutes+1
        beq     @stop           ; do not probe another step after the budget ends
        jmp     @cell
:       lda     #3
        sta     travel_reason
        jmp     @stop
@shore: lda     #2
        sta     travel_reason
        jmp     @stop
@edge:  lda     #4
        sta     travel_reason
        jmp     @stop
@pace:  lda     #7
        sta     travel_reason
        jmp     @stop
@time_end:
        lda     minutes
        ora     minutes+1
        beq     @stop
        lda     stepmin
        sta     travel_next_minutes
        lda     #9
        sta     travel_reason
@stop:  jsr     travel_state_save
        jsr     t_home          ; the full-screen MAP covered rows 20-23
        lda     #0              ; and the next walk redraws all of it
        sta     topo_cue_end
        lda     used
        sta     msgnum
        lda     used+1
        sta     msgnum+1
        lda     dead
        beq     :+
        jmp     report
:       lda     fauna_alert
        beq     :+
        lda     #5
        sta     travel_reason
        jsr     fauna_cause
:       lda     input_interrupted
        beq     :+
        lda     #6
        sta     travel_reason
:
        jsr     show_view
        lda     #<m_travel
        ldx     #>m_travel
        jsr     message
        lda     travel_pending
        ora     route_active
        beq     :+
        jsr     travel_ui_load
        jsr     navigation_travel_report
:       jmp     report
.export walk_progress := @progress

; REST, SLEEP, WAIT, PAUSE, CAMP, EXERCISE: hours at rest
do_rest:
        lda     #<m_hours
        ldx     #>m_hours
        jsr     get_duration
        jcs     @out
        lda     msgnum+1
        pha
        lda     msgnum
        pha
        jsr     prepare_minutes
        lda     #3
        jsr     overlay_load
        jsr     module_rest_prepare
@step:  lda     minutes+1       ; first interval 30; health chooses later ones
        bne     @full
        lda     minutes
        beq     @done
        cmp     health_period
        bcc     @last
@full:  lda     health_period
@last:  sta     stepmin
        sec
        lda     minutes
        sbc     stepmin
        sta     minutes
        lda     minutes+1
        sbc     #0
        sta     minutes+1
        lda     #3
        jsr     overlay_load
        jsr     module_rest_step
        bcs     @done
        lda     stepmin
        ldx     #0
        jsr     spend
        lda     dead
        ora     fauna_alert
        beq     @step
@done:  lda     #3
        jsr     overlay_load
        jsr     module_rest_finish
        lda     dead            ; died on the way: just the news
        beq     :+
        pla
        pla
        jmp     report
:       pla
        sta     msgnum
        pla
        sta     msgnum+1
        jsr     show_view
        jmp     rest_result
@out:   rts

.segment "TEXT"
; Resident result printer: the scene may have replaced the shared overlay.
rest_result:
        lda     fauna_alert
        beq     :+
        jsr     fauna_cause
:       lda     #3
        jsr     overlay_load
        jmp     module_rest_result

; EAT food: ounces, from the pack first, then the ground at the item's ground cell.
; T12/S00 credits .8*kcal/body weight and the food's water, then spends
; 16 minutes at metabolic rate 2.31; see module_meal_prepare.
.segment "GCODE"
do_eat:
        lda     noun
        cmp     #41
        bcc     @food
        cmp     #52
        bcs     @food
        jmp     do_medical
@food:
        lda     #3
        jsr     overlay_load
        jmp     module_eat
.segment "ENVIRON"
module_eat: lda     noun
        bne     :+
        lda     #<m_food_object
        ldx     #>m_food_object
        jmp     message
:       lda     noun
        cmp     #N_WATER
        bne     @food
        lda     #<m_usedrink
        ldx     #>m_usedrink
        jmp     message
@food:  cmp     #23
        bcc     @not
        cmp     #38
        bcc     @ok
@not:   lda     #<m_notfood
        ldx     #>m_notfood
        jmp     message
@ok:    tax
        jsr     have
        bcs     @ask
        jmp     no_item
@ask:   lda     #<m_ounces
        ldx     #>m_ounces
        jsr     get_quantity
        bcc     :+
        rts
:       ldx     noun
        jsr     take_oz         ; msgnum = ounces actually taken
        lda     msgnum
        beq     @none
        ldx     noun            ; kcal = ounces * kcal/oz
        lda     it_kcal,x
        sta     g0
        jsr     oz_times        ; FAC = msgnum * g0
        fst     t1
        fop     FADD, s_eaten
        fst     s_eaten
        lda     #3
        jsr     overlay_load
        jsr     module_meal_prepare
        lda     #<m_ate
        ldx     #>m_ate
        jsr     message
        lda     msgnum
        asl                     ; T12/S00: two minutes per ounce eaten
        sta     meal_remaining
@step:  lda     meal_remaining
        cmp     health_period
        bcc     :+
        lda     health_period
:       sta     stepmin
        sec
        lda     meal_remaining
        sbc     stepmin
        sta     meal_remaining
        lda     stepmin
        ldx     #2              ; meal metabolic rate = 1.4 * base
        jsr     spend
        lda     dead
        ora     fauna_alert
        bne     @done
        lda     meal_remaining
        bne     @step
@done:
        jmp     report
@none:  jmp     no_item

; DRINK WATER from the canteen costs no time (original T0F/S00).
; Negative hydration credit survives until the next health update.
.segment "GCODE"
do_drink:
        lda     noun
        cmp     #41
        bcc     @water
        cmp     #52
        bcs     @water
        jmp     do_medical
@water:
        lda     #3
        jsr     overlay_load
        jmp     module_drink
.segment "ENVIRON"
module_drink:
        lda     noun
        bne     :+
        lda     #<m_drink_object
        ldx     #>m_drink_object
        jmp     message
:       lda     #0              ; ground water is safe unless a river pile
        sta     water_ground_untreated  ; is made for this drink (drink_source)
        lda     noun
        cmp     #N_WATER
        beq     @water
        cmp     #169            ; RAIN, SNOW, ICE (src/water.s)
        bcc     :+
        cmp     #172
        bcs     :+
        jmp     drink_rain
:       lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message
@water: tax
        jsr     have
        bcs     module_drink_water
drink_rain:
        jsr     drink_source    ; rain, snow, ice, a river (src/water.s)
        bcs     :+
        rts
:       lda     #N_WATER
        sta     noun
module_drink_water:
        lda     #<m_ounces
        ldx     #>m_ounces
        jsr     get_quantity
        bcc     :+
        rts
:       jsr     drink_limit     ; resident (src/camp.s)
        bcc     :+
        rts
:       ldx     #N_WATER
        lda     water_untreated
        ldy     it_place+N_WATER
        cpy     #5
        bne     :+
        lda     #0              ; a hung pack is not a source for this drink
:       sta     water_drinking_untreated
        lda     obj_keep
        bpl     :+
        lda     obj_side
        bne     @consume
        lda     water_ground_untreated
        sta     water_drinking_untreated
        jmp     @consume
:       jsr     at_ground
        bcc     @consume
        lda     it_place+N_WATER
        cmp     #5
        beq     @ground_quality
        lda     it_pack_hi+N_WATER
        bne     @consume
        lda     msgnum+1
        beq     :+
        lda     #255            ; take_oz caps one consumption at 255 OZ
        bne     @compare_water
:       lda     msgnum
@compare_water:
        cmp     it_pack_lo+N_WATER
        bcc     @consume
        beq     @consume
@ground_quality:
        lda     water_ground_untreated
        ora     water_drinking_untreated
        sta     water_drinking_untreated
@consume:
        lda     #21
        jsr     overlay_load
        jsr     module_drink_frame
        jsr     take_oz
        lda     msgnum
        beq     @none
        jsr     water_hazard
.if DRINK_FIDELITY
        jsr     drink_credit    ; oz x (.73 - .6 x $4C7A), src/camp.s
.else
        ldy     msgnum
        lda     msgnum+1
        jsr     GIVAYF
        fop     FMULT, f_oz_hour
.endif
        fop     FSUB, s_defw
        fst     s_defw
        jsr     alert_drink     ; lot 13: ounces of the drinking session ($4BD4)
        fld     f_half
        fst     s_drink
        fld     s_elap
        fst     s_last
.if DRINK_FIDELITY
        jsr     drink_care      ; care selector 6
.endif
        lda     #<m_drank
        ldx     #>m_drank
        jsr     message
        jsr     ui_monitor      ; drinking changes thirst/illness without spend
        jmp     report
@none:  jmp     no_item

.segment "GCODE"
; Equipment moves between ground, pack, hand and body. Food/water always
; goes into the pack/canteen. Transfers are atomic against load limits;
; action durations remain unknown.
; DROP/REMOVE share verb 8 in the original vocabulary: both leave on ground.
; WATER, the CANTEEN (FILL/REFILL), RAIN, SNOW and ICE go to CAMP first.
.segment "LOWCODE"
do_get:
        lda     noun
        cmp     #N_WATER
        beq     @water
        cmp     #64
        beq     @water
        cmp     #169
        bcc     get_item
        cmp     #172
        bcs     get_item
@water: lda     #4
        jsr     overlay_load
        jmp     module_collect
get_item:
        lda     #14
        jsr     overlay_load
        jmp     module_do_get
.segment "GCODE"
water_hazard:
        lda     water_drinking_untreated
        bne     :+
        rts
:       lda     #22
        jsr     overlay_load
        jmp     module_water_hazard
animal_attack:
        lda     #22
        jsr     overlay_load
        jmp     module_animal_attack
do_outdoor:
        lda     #22
        jsr     overlay_load
        jsr     module_outdoor
do_outdoor_done:
        lda     outdoor_minutes
        beq     :+
        ldx     outdoor_act
        jsr     spend
:       jsr     show_view
outdoor_report:
        lda     #22
        jsr     overlay_load
        jmp     module_outdoor_report
do_wear:
        lda     #14
        jsr     overlay_load
        jmp     module_do_wear
do_drop:
        lda     #14
        jsr     overlay_load
        jmp     module_do_drop

.segment "ITEMS"
module_do_get:
        lda     noun
        cmp     #21
        bne     :+
        lda     it_place+21
        cmp     #5
        bne     :+
        jmp     do_tree
:       jsr     item_noun
        bcs     :+
        rts
:       jsr     have
        bcs     @have
        jmp     item_missing
@have:  lda     verb
        cmp     #V_CARRY
        beq     @container
        cpx     #21             ; a backpack cannot contain itself
        bne     @container
        jmp     @empty
@container:
        cpx     #N_WATER
        beq     @canteen
        cpx     #38
        bcs     @equipment
        cpx     #23
        bcs     @bag
@equipment:
        lda     verb
        cmp     #V_CARRY
        beq     @ready
@bag:   lda     it_place+21
        cmp     #5
        jeq     @empty
        cmp     #0
        jeq     @empty
        cmp     #$FF
        jeq     @empty
        bne     @ready
@canteen:
        lda     it_place+64
        cmp     #5
        jeq     @empty
        cmp     #0
        jeq     @empty
        cmp     #$FF
        jeq     @empty
@ready: jsr     transfer_amount
        bcc     :+
        rts
:       lda     #0              ; the tent is a site sprite on XL (lot 3):
        sta     scene_cache_valid ; the next view recomputes the scene
        jsr     save_item
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        jsr     at_ground
        bcc     @packed
        clc
        lda     it_pack_lo,x
        adc     msgnum
        sta     it_pack_lo,x
        lda     it_pack_hi,x
        adc     msgnum+1
        sta     it_pack_hi,x
        bcc     :+
        jmp     reject_overflow  ; even an overflowing quantity is atomic
:       sec
        lda     it_gnd_lo,x
        sbc     msgnum
        sta     it_gnd_lo,x
        lda     it_gnd_hi,x
        sbc     msgnum+1
        sta     it_gnd_hi,x
@packed:
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @gear
        lda     #4              ; ground stock remains elsewhere
        bne     @store
@gear:  lda     #2
        ldy     verb
        cpy     #V_CARRY
        bne     @store
        cpx     #N_WATER
        bcc     @hand
        cpx     #38
        bcc     @pack
@hand:  lda     #3
        bne     @store
@pack:  lda     #2
@store: sta     it_place,x
        jsr     accept_load
        bcs     @result         ; ground water is safe (T0F/S00 $587C, lot 2)
        rts
@result:
        jsr     item_followup_arm
        lda     saved_item      ; packing/holding worn clothing removes a layer
        cmp     #1              ; only after the load check has accepted it
        bne     :+
        jsr     native_clothes_changed
        ldx     noun            ; thermal_clothes and its overlay clobber X
:       lda     it_place,x
        cmp     #3
        beq     @carried
        lda     #<m_taken
        ldx     #>m_taken
        jmp     message
@carried:
        lda     #<m_carried
        ldx     #>m_carried
        jmp     message

@empty: cpx     #21
        bne     :+
        lda     #<m_selfpack
        ldx     #>m_selfpack
        jmp     message
:       cpx     #N_WATER
        beq     @needcan
        lda     #<m_needpack
        ldx     #>m_needpack
        jmp     message
@needcan:
        lda     #<m_needcan
        ldx     #>m_needcan
        jmp     message

; A real increase of a provision's carried stock can continue as a meal.
; Already-carried items and refused transfers leave the UI union alone.
item_followup_arm:
        cpx     #N_WATER
        bcc     @done
        cpx     #38
        bcs     @done
        lda     mn_mode
        beq     @done
        lda     mq_n
        bne     @done
        sec
        lda     it_pack_lo,x
        sbc     saved_item+1
        tay
        lda     it_pack_hi,x
        sbc     saved_item+2
        bcc     @done
        bne     @large
        tya
        beq     @done
        bne     @portion
@large: lda     #255
@portion:
        sta     dep_mask+1
        stx     dep_mask
        lda     #$80
        cpx     #N_WATER
        bne     :+
        lda     #$81
:
        sta     dep_running
        lda     journey_encounters
        sta     dep_cursor
@done:  rts

module_do_wear:
        jsr     item_noun
        bcs     :+
        rts
:       cpx     #2
        bcc     @not
        cpx     #9
        bcc     @clothes
        cpx     #12
        bcc     @not
        cpx     #21
        bcc     @clothes
        cpx     #43             ; sunglasses
        beq     @clothes
        cpx     #54             ; watch
        bne     @not
@clothes:
        jsr     have
        bcs     @wear
        jmp     item_missing
@wear:  jsr     save_item
        lda     #1
        sta     it_place,x
        jsr     accept_load
        bcs     :+
        rts
:       jsr     native_clothes_changed
        lda     #<m_worn
        ldx     #>m_worn
        jmp     message
@not:   lda     #<m_notwear
        ldx     #>m_notwear
        jmp     message

module_do_drop:
        jsr     item_noun
        bcs     :+
        rts
:       lda     it_place,x
        cmp     #5
        bne     :+
        jmp     item_missing
:       cpx     #21
        bne     @notbag
        jsr     load_totals_quiet ; capacity inspection cannot change the scene
        lda     load_used+4
        ora     load_used+5
        bne     @container
@notbag:
        cpx     #64
        bne     @drop
        lda     it_pack_lo+N_WATER
        ora     it_pack_hi+N_WATER
        beq     @drop
@container:
        cpx     #21
        bne     :+
        lda     #<m_empty_pack
        ldx     #>m_empty_pack
        jmp     message
:       lda     #<m_empty_can
        ldx     #>m_empty_can
        jmp     message
@drop:  ldx     noun
        jsr     transfer_amount
        bcc     :+
        rts
:       lda     it_place,x
        jeq     @missing
        cmp     #$FF
        jeq     @missing
        jsr     save_item
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        jeq     @missing
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @merge
        jsr     at_ground
        bcs     @merge
        ; One ground pile per item: preserve a distant pile rather than
        ; relocating it silently. Collect it before dropping this stock.
        lda     #<m_pile
        ldx     #>m_pile
        jmp     message
@merge: clc
        lda     it_gnd_lo,x
        adc     msgnum
        sta     it_gnd_lo,x
        lda     it_gnd_hi,x
        adc     msgnum+1
        sta     it_gnd_hi,x
        bcc     :+
        jmp     reject_overflow
:       sec
        lda     it_pack_lo,x
        sbc     msgnum
        sta     it_pack_lo,x
        lda     it_pack_hi,x
        sbc     msgnum+1
        sta     it_pack_hi,x
@gear:  lda     it_pack_lo,x
        ora     it_pack_hi,x
        beq     :+
        cpx     #N_WATER
        bcc     :+
        cpx     #38
        bcs     :+
        lda     #4
        bne     @place
:       lda     #0
@place:
        sta     it_place,x
        sta     scene_cache_valid ; the tent is a site sprite on XL (lot 3)
        lda     px+1
        sta     it_x,x
        lda     py+1
        sta     it_y,x
        jsr     item_load_totals ; TENT changes a site sprite; other drops keep the view
        lda     saved_item
        cmp     #1
        bne     :+
        jsr     native_clothes_changed
:       lda     #<m_dropped
        ldx     #>m_dropped
        jmp     message
@missing:
        jmp     item_missing

; Validate a noun before any indexed item access. C set on success.
item_noun:
        ldx     noun
        beq     @what
        cpx     #76
        bcc     @ok
        cpx     #89             ; lot 3: BOW, SPEAR, CLUB, ROCK, SPLINT, the
        bcc     @notyet         ; CRAFT module in the SIM window (src/craft.s
        cpx     #94             ; cr_items); C clear: the caller returns
        bcs     @notyet
        jsr     load_totals_quiet ; lot 14: the load now (CRAFT checks it;
        lda     #0              ; SIM quietly: no curtain, the view intact)
        sta     sim_quiet
        sta     sim_loaded      ; the module holds the SIM window
        ldx     #CRAFT_MODULE
        jsr     sim_fetch
        jsr     CRAFT_RUN
        jsr     load_totals_quiet ; the load moved (TRAVEL's pounds)
        clc
        rts
@notyet:
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     @msg
@what:  lda     #<m_object
        ldx     #>m_object
@msg:   jsr     message
        clc
        rts
@ok:    sec
        rts

item_missing:
        lda     #<m_notthere
        ldx     #>m_notthere
        jmp     message

.segment "GCODE"

no_item:
        lda     #<m_noitem
        ldx     #>m_noitem
        jmp     message

; Current totals and the pre-transfer snapshot (LOW is RAM).
.segment "LOWTEXT"
load_used: .res 8              ; weight, wear, pack, hand (16-bit)
; First Sierra character's native capacities. Container weights include
; their contents; a carried backpack does not occupy the hand allowance.
load_limits: .word 815, 2149, 6000, 2686
load_vol: .res 2
load_bad: .byte 0
saved_item: .res 5
; EQUIPMENT has a distinct page and keeps its selected item across overlays.
eq_selected: .byte 0
scr_equipment:
        jsr     load_totals_quiet
        jsr     status_fetch
        ldx     #33             ; direct fetch: 33 is also the first scene asset
        jsr     mem_fetch
        jmp     module_equipment
.segment "GCODE"

.segment "ITEMS"
 ; Transfer quantities are ounces of first-set provisions only. Omitted
; quantity keeps ALL. Reject before saving/changing anything; never clamp.
transfer_amount:
        cpx     #N_WATER
        jcc     @gear
        cpx     #38
        jcs     @gear
        lda     verb
        cmp     #V_DROP
        beq     @pack
        jsr     at_ground
        bcs     :+
        lda     input_argument
        jne     @missing
        clc
        rts
:       lda     it_gnd_lo,x
        sta     msgnum
        lda     it_gnd_hi,x
        jmp     @stock
@pack:  lda     it_pack_lo,x
        sta     msgnum
        lda     it_pack_hi,x
@stock: sta     msgnum+1
        lda     input_argument
        beq     @ok
        lda     input_unit
        beq     :+
        cmp     #3
        bne     @bad
:       lda     input_value
        ora     input_value+1
        beq     @bad
        lda     msgnum
        cmp     input_value
        lda     msgnum+1
        sbc     input_value+1
        bcc     @short
        lda     input_value
        sta     msgnum
        lda     input_value+1
        sta     msgnum+1
        cpx     #N_WATER
        bne     @ok
        lda     verb
        cmp     #V_DROP
        beq     @ok
        lda     #0
        sta     stock_available
        sta     stock_available+1
        lda     it_pack_hi+N_WATER
        bne     @capacity
        sec
        lda     #64
        sbc     it_pack_lo+N_WATER
        bcc     @capacity
        sta     stock_available
        lda     msgnum+1
        bne     @capacity
        lda     stock_available
        cmp     msgnum
        bcs     @ok
@capacity:
        lda     #<water_capacity
        ldx     #>water_capacity
        jmp     @say
@ok:    clc
        rts
@gear:  lda     input_argument
        beq     @ok
@bad:   lda     #<transfer_bad
        ldx     #>transfer_bad
        jmp     @say
@short: lda     #<transfer_short
        ldx     #>transfer_short
        jmp     @say
@missing:
        lda     #<m_notthere
        ldx     #>m_notthere
@say:   jsr     message
        sec
        rts

save_item:
        lda     it_place,x
        sta     saved_item+0
        lda     it_pack_lo,x
        sta     saved_item+1
        lda     it_pack_hi,x
        sta     saved_item+2
        lda     it_gnd_lo,x
        sta     saved_item+3
        lda     it_gnd_hi,x
        sta     saved_item+4
        rts

.segment "GCODE"
; load_totals recomputes usage, never trusting cached counters. Ground
; quantities have no load; food volume = carried ounces * in3 per ounce.
; The small food multiplier is 1..3 (checked by gendata.py). Every 16-bit
; overflow sets load_bad rather than wrapping into apparent free capacity.
load_totals:
        lda     #3
        jsr     overlay_load
        jmp     module_load_totals
; INVENTORY only reads the load totals (lot 4): SIM is copied without the
; text curtain, and finish_simulation keeps the intact view (no raycast).
load_totals_quiet:
        lda     sim_loaded
        bne     :+
        ldx     #3
        jsr     mem_fetch
        inc     sim_loaded
        inc     sim_quiet
        inc     overlay_reads   ; the same module copy as overlay_load counts
        bne     :+
        inc     overlay_reads+1
:       jmp     module_load_totals

.segment "ENVIRON"
module_load_totals:
        clc                     ; native canteen W5 = 16 + contained water
        lda     it_pack_lo+N_WATER
        adc     #16
        sta     it_oz_lo+64
        lda     it_pack_hi+N_WATER
        adc     #0
        sta     it_oz_hi+64
        lda     it_pack_lo+N_WATER
        asl
        sta     it_vol_lo+64
        lda     it_pack_hi+N_WATER
        rol
        sta     it_vol_hi+64
        clc                     ; native canteen W6 = 16 + 2 * contained water
        lda     it_vol_lo+64
        adc     #16
        sta     it_vol_lo+64
        bcc     :+
        inc     it_vol_hi+64
:
        lda     #1
        sta     ui_dirty
        lda     #0
        sta     load_bad
        ldx     #7
@clear: sta     load_used,x
        dex
        bpl     @clear
        ldx     #75
@item:  lda     it_place,x
        cmp     #5
        jeq     @next
        cmp     #0
        jeq     @next
        cmp     #$FF
        jeq     @next
        cpx     #N_WATER
        bcc     @gear
        beq     @next           ; already included in the canteen, never twice
        cpx     #38
        bcs     @gear
        lda     it_pack_lo,x
        sta     num
        lda     it_pack_hi,x
        sta     num+1
        ldy     #0
        jsr     load_add
        lda     #0
        sta     load_vol
        sta     load_vol+1
        ldy     it_vol_lo,x
@mul:   clc
        lda     load_vol
        adc     num
        sta     load_vol
        lda     load_vol+1
        adc     num+1
        sta     load_vol+1
        bcc     :+
        inc     load_bad
:       dey
        bne     @mul
        ldy     #4
        cpx     #N_WATER
        bne     @volume
        lda     it_place+64     ; water follows its canteen's destination
        asl
        tay
        jmp     @volume
@gear:  lda     it_oz_lo,x
        sta     num
        lda     it_oz_hi,x
        sta     num+1
        ldy     #0
        jsr     load_add
        cpx     #21
        beq     @next           ; backpack's own volume is outside its capacity
        lda     it_vol_lo,x
        sta     load_vol
        lda     it_vol_hi,x
        sta     load_vol+1
        lda     it_place,x
        asl
        tay
@volume:
        lda     load_vol
        sta     num
        lda     load_vol+1
        sta     num+1
        jsr     load_add
@next:  dex
        beq     :+
        jmp     @item
:       ldx     #4              ; lot 14: the second set carried (BOW, SPEAR,
@craft: lda     cr_b1,x         ; CLUB, ROCK, SPLINT: W5, W6 of CRAFT.md
        beq     @cnext          ; 4.1), its volume in its place (1 worn,
        cmp     #4              ; 2 pack, 3 hand); 0 ground, $FF none
        bcs     @cnext
        asl     a
        pha
        lda     lt_crw,x
        sta     num
        lda     #0
        sta     num+1
        tay
        jsr     load_add
        lda     lt_crv,x
        sta     num
        pla
        tay
        jsr     load_add
@cnext: dex
        bpl     @craft
        ldx     noun
        rts
lt_crw: .byte   50, 50, 100, 100, 50    ; oz
lt_crv: .byte   90, 90, 200, 100, 120   ; in3

load_add:
        clc
        lda     load_used,y
        adc     num
        sta     load_used,y
        lda     load_used+1,y
        adc     num+1
        sta     load_used+1,y
        bcc     :+
        inc     load_bad
:       rts

; accept_load -- C set if the tentative transfer fits; otherwise restore
; all five changed fields and report the refusal. X returns as noun.
.segment "ITEMS"
; Inventory transfers take no time. The tent alone changes the rendered
; scene (its site sprite); keep the ordinary repaint for that item. Clothes
; retain native_clothes_changed and any simulation it requests afterwards.
item_load_totals:
        cpx     #9              ; N_TENT / SITE_TENT
        beq     @scene
        jmp     load_totals_quiet
@scene: jmp     load_totals
accept_load:
        jsr     item_load_totals
        lda     load_bad
        bne     reject_overflow
        ldy     #6
@check: lda     load_limits,y
        cmp     load_used,y
        lda     load_limits+1,y
        sbc     load_used+1,y
        bcc     reject_load
        dey
        dey
        bpl     @check
        sec
        rts
reject_load:
        lda     #0
        sta     load_reason_overflow
        sta     load_reason_weight
        sta     load_reason_volume
        ldy     #0
@excess:
        sec
        lda     load_used,y
        sbc     load_limits,y
        sta     load_excess,y
        lda     load_used+1,y
        sbc     load_limits+1,y
        sta     load_excess+1,y
        bcc     @within
        ora     load_excess,y
        beq     @within
        tya
        bne     @volume
        inc     load_reason_weight
        bne     @next
@volume:
        sta     load_reason_volume
        bne     @next
@within:
        lda     #0
        sta     load_excess,y
        sta     load_excess+1,y
@next:  iny
        iny
        cpy     #8
        bne     @excess
        jmp     restore_item
reject_overflow:
        lda     #1
        sta     load_reason_overflow
restore_item:
        lda     saved_item+0
        sta     it_place,x
        lda     saved_item+1
        sta     it_pack_lo,x
        lda     saved_item+2
        sta     it_pack_hi,x
        lda     saved_item+3
        sta     it_gnd_lo,x
        lda     saved_item+4
        sta     it_gnd_hi,x
        jsr     item_load_totals
        ldy     #0
@free:  sec
        lda     load_limits,y
        sbc     load_used,y
        sta     load_free,y
        lda     load_limits+1,y
        sbc     load_used+1,y
        sta     load_free+1,y
        bcs     :+
        lda     #0
        sta     load_free,y
        sta     load_free+1,y
:       iny
        iny
        cpy     #8
        bne     @free
        jsr     load_report
        ldx     noun
        clc
        rts

load_report:
        lda     load_reason_overflow
        beq     @normal
        lda     #<m_overflow
        ldx     #>m_overflow
        jmp     message
@normal:
        lda     #<m_volume
        ldx     #>m_volume
        ldy     load_reason_weight
        beq     @header
        lda     #<m_weight
        ldx     #>m_weight
        ldy     load_reason_volume
        beq     @header
        lda     #<m_both
        ldx     #>m_both
@header:
        jsr     message         ; then one row of the result column per cause
        jsr     msg_newline
        lda     load_reason_weight
        beq     @vol
        jsr     puts
        .byte "WEIGHT: +",0
        ldy     #0
        jsr     load_numbers
        jsr     msg_newline
@vol:   ldy     load_reason_volume
        beq     @done
        tya
        pha
        lsr
        tax
        dex
        lda     load_place_lo,x
        sta     gp2
        lda     load_place_hi,x
        sta     gp2+1
        jsr     message_string
        jsr     msg_flush
        pla
        tay
        jsr     load_numbers
@done:  rts

; Y indexes weight or a volume. Print excess and capacity after rollback.
load_numbers:
        tya
        pha
        lda     load_excess,y
        sta     num
        lda     load_excess+1,y
        sta     num+1
        jsr     print_u16
        pla
        pha
        jsr     load_unit
        jsr     puts
        .byte "; FREE ",0
        pla
        tay
        tya
        pha
        lda     load_free,y
        sta     num
        lda     load_free+1,y
        sta     num+1
        jsr     print_u16
        pla
        jsr     load_unit
        rts
load_unit:
        cmp     #0
        beq     @oz
        jsr     puts
        .byte " IN3",0
        rts
@oz:    jsr     puts
        .byte " OZ",0
        rts
load_place_lo: .byte <load_wear,<load_pack,<load_hand
load_place_hi: .byte >load_wear,>load_pack,>load_hand
load_wear: .byte "  WEAR: +",0
load_pack: .byte "  PACK: +",0
load_hand: .byte "  HAND: +",0

.segment "GCODE"
; report -- after a command that took time: warnings
report:
        ldx     #0
        lda     dead
        bne     @result
        inx
        lda     won
        bne     @result
        inx
        lda     fauna_alert
        bpl     :+
        jmp     outdoor_report
:       rts                     ; lot 13: weakness is announced by message 176 (alerts.s)
@result: jmp    report_message
.segment "LOWCODE"
report_message:
        lda     travel_action
        beq     @message
        txa
        clc
        adc     #3
        tax
@message:
        lda     report_lo,x
        pha
        lda     report_hi,x
        tax
        pla
        jmp     message
.segment "LOWTEXT"
report_lo: .byte <m_dead,<m_goal,<m_weak,<m_dead_travel,<m_goal_travel,<m_weak_travel
report_hi: .byte >m_dead,>m_goal,>m_weak,>m_dead_travel,>m_goal_travel,>m_weak_travel
.segment "GCODE"

; ----------------------------------------------------------------------------
; inventory helpers
; ----------------------------------------------------------------------------
; have -- item X present and reachable (C set): carried, or on the ground at
; the item's ground cell.
have:   lda     it_place,x
        cmp     #$FF
        beq     @no
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        cmp     #5
        beq     @ground_food
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        bne     @yes
@ground_food:
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @no
        jmp     at_ground
@gear:  cmp     #5
        beq     @no
        cmp     #0
        bne     @yes
        jmp     at_ground
@yes:   sec
        rts
@no:    clc
        rts

; at_ground -- C set when item X has its ground pile on the player cell
at_ground:
        lda     px+1
        cmp     it_x,x
        bne     @no
        lda     py+1
        cmp     it_y,x
        bne     @no
        sec
        rts
@no:    clc
        rts

; take_oz -- remove up to msgnum ounces of item X (pack first, then the ground
; at the item's ground cell); msgnum = ounces removed (at most 255)
take_oz:
        stx     take_oz_item+1
        lda     overlay_current
        pha
        lda     #22
        jsr     overlay_load
take_oz_item:
        ldx     #0
        jsr     module_take_oz
        pla
        bmi     @restored       ; invalidated UI window has no native caller
        jsr     overlay_load
@restored:
        ldx     take_oz_item+1
        rts
.pushseg
.segment "OUTDOOR"
module_take_oz:
        stx     g2
        lda     msgnum+1
        beq     :+
        lda     #255
        sta     msgnum
:       lda     msgnum
        sta     g0              ; still wanted
        lda     #0
        sta     msgnum+1
        sta     g1              ; taken
        lda     obj_keep
        bpl     :+
        cpx     menu_noun
        bne     :+
        lda     obj_side
        beq     @ground
:       lda     it_place,x
        cmp     #5
        beq     @ground
        lda     it_pack_hi,x    ; from the pack
        bne     @pfull
        lda     it_pack_lo,x
        cmp     g0
        bcc     @ptake          ; less than wanted: all of it
@pfull: lda     g0
@ptake: sta     g1
        sec
        lda     it_pack_lo,x
        sbc     g1
        sta     it_pack_lo,x
        lda     it_pack_hi,x
        sbc     #0
        sta     it_pack_hi,x
        sec
        lda     g0
        sbc     g1
        sta     g0
        beq     @done
        lda     obj_keep
        bpl     @ground
        cpx     menu_noun
        bne     @ground
        lda     obj_side
        bne     @done
@ground:
        jsr     at_ground        ; then from the ground, at the item's ground cell
        bcc     @done
        ldx     g2
        lda     it_gnd_hi,x
        bne     @gfull
        lda     it_gnd_lo,x
        cmp     g0
        bcc     @gtake
@gfull: lda     g0
@gtake: sta     g0
        sec
        lda     it_gnd_lo,x
        sbc     g0
        sta     it_gnd_lo,x
        lda     it_gnd_hi,x
        sbc     #0
        sta     it_gnd_hi,x
        clc
        lda     g1
        adc     g0
        sta     g1
@done:  ldx     g2
        lda     g1
        sta     msgnum
        sec                     ; the total
        lda     it_oz_lo,x
        sbc     g1
        sta     it_oz_lo,x
        lda     it_oz_hi,x
        sbc     #0
        sta     it_oz_hi,x
        jmp     load_totals

.popseg

; oz_times -- FAC = msgnum (byte) * g0
.segment "ENVIRON"
oz_times:
        ldy     msgnum
        lda     #0
        jsr     GIVAYF
        fst     t3
        ldy     g0
        lda     #0
        jsr     GIVAYF
        fop     FMULT, t3
        rts

; mul60 -- minutes = msgnum (hours, byte) * 60
.segment "GCODE"
mul60:
        lda     #21
        jsr     overlay_load
        jmp     module_mul60
.segment "ADVENTURE"
module_mul60: lda     msgnum
        sta     g0
        lda     #0
        sta     minutes
        sta     minutes+1
        ldx     #60
@add:   clc
        lda     minutes
        adc     g0
        sta     minutes
        bcc     :+
        inc     minutes+1
:       dex
        bne     @add
        rts

.segment "GCODE"
; cell_at -- A = grid byte of cell (Y = x, X = y); N = water
cell_at:
        sty     cell_at_y+1
        jsr     grid_row
        sta     gp2
        sty     gp2+1
cell_at_y:
        ldy     #0
        lda     (gp2),y
        rts

; tree_ok -- C set when a tree stands here (src/tree.s tree_here: outside,
; woods, under the timberline). Clobbers gp2 (cell_at).
.segment "CODE"
tree_ok:
        lda     shelter_inside
        bne     @no
        jsr     woods_here
        bcc     @no
        jsr     level_here
        clc
        adc     M_BASE
        sta     g0
        lda     MAP+27
        bne     :+
        lda     #110
:       cmp     g0
        beq     @no
        bcs     @yes
@no:    clc
        rts
@yes:   sec
        rts

.segment "GCODE"
.segment "LOWCODE"
; water_bits -- (the grid) A = bit 1: the player's cell is water; bit 0: the
; next half-step of the heading enters water (TRAVEL's own test,
; module_swim_land: SWIM starts, WALK stops at "WATER AHEAD"). The probe
; runs only with water in the 3 x 3 cells around, and keeps the travel
; state (swim_probe). Cached for the position and heading.
water_bits:
        ldx     #5
:       lda     px,x            ; px, py, heading
        cmp     wb_key,x
        bne     @new
        dex
        bpl     :-
        bmi     @done
@new:   ldx     #5
:       lda     px,x
        sta     wb_key,x
        dex
        bpl     :-
        lda     px              ; half-cell coordinates (native_here)
        asl     a
        lda     px+1
        rol     a
        sta     wb_x
        tay
        lda     py
        asl     a
        lda     py+1
        rol     a
        sta     wb_y
        tax
        lda     #0
        sta     wb_bits
        jsr     cell_native
        bpl     :+
        lda     #2
        sta     wb_bits
:       ldx     #8              ; water in the 3 x 3 cells?
@scan:  stx     wb_i
        lda     wb_x
        clc
        adc     wb_dx,x
        tay
        lda     wb_y
        clc
        adc     wb_dy,x
        tax
        jsr     cell_native
        bmi     @near
        ldx     wb_i
        dex
        bpl     @scan
        bmi     @done
@near:  jsr     swim_probe
        bcc     @done
        inc     wb_bits
@done:  lda     wb_bits
        rts

.segment "GCODE"
; swim_probe -- C set when the next half-step enters water (TRAVEL loaded
; into $5800); the travel state the probe writes is put back (t1 ..
; travel_delta, g0, g1, travel_reason: the state of the reference).
swim_probe:
        ldx     #37
:       lda     t1,x
        pha
        dex
        bpl     :-
        lda     g0
        pha
        lda     g1
        pha
        lda     travel_reason
        pha
        lda     #12
        jsr     overlay_load
        jsr     module_swim_prepare
        jsr     swim_land_probe
        pla                     ; C is kept by PLA, STA and INX
        sta     travel_reason
        pla
        sta     g1
        pla
        sta     g0
        ldx     #256-38
:       pla
        sta     t1+38-256,x
        inx
        bne     :-
        rts
.assert travel_delta + 5 - t1 = 38, error, "swim_probe: t1 .. travel_delta"

.segment "MENUCODE"
wb_dx:  .byte   <-2, 0, 2, <-2, 0, 2, <-2, 0, 2
wb_dy:  .byte   <-2, <-2, <-2, 0, 0, 0, 2, 2, 2
.segment "LOWTEXT"
wb_key:  .res 6
wb_bits: .res 1
wb_x:    .res 1
wb_y:    .res 1
wb_i:    .res 1

.segment "LOWCODE"
; lower_ok -- C set when the backpack hangs on this cell (LOWER FOOD).
lower_ok:
        lda     it_place+21
        cmp     #5
        bne     @no
        lda     px+1
        cmp     it_x+21
        bne     @no
        lda     py+1
        cmp     it_y+21
        bne     @no
        sec
        rts
@no:    clc
        rts

; level_here -- A = level of the player's cell
.segment "CODE"
level_here:
        ldx     py+1
        ldy     px+1
        jsr     cell_at
        and     #$7F
        rts
.segment "GCODE"

; at_goal -- won when within one cell of the outpost
at_goal:
        lda     #10
        jsr     overlay_load
        jmp     module_at_goal
.segment "SITES"
module_at_goal:
        lda     MAP+37
        beq     @legacy
        lda     px
        ora     py
        bne     @no
        lda     px+1
        cmp     M_GOALX
        bne     @no
        lda     py+1
        cmp     M_GOALY
        bne     @no
        beq     @win
@legacy:
        lda     px+1
        sec
        sbc     M_GOALX
        jsr     @near
        bcc     @no
        lda     py+1
        sec
        sbc     M_GOALY
        jsr     @near
        bcc     @no
@win:   lda     #1
        sta     won
@no:    rts
@near:  clc                     ; C set when A in -1..1
        adc     #1
        cmp     #3
        rol     a               ; carry: A+1 >= 3
        eor     #1
        lsr     a
        rts

.segment "GCODE"

; ----------------------------------------------------------------------------
; simulation
; ----------------------------------------------------------------------------
; spend -- A minutes (<= 255) of activity X (0 rest, 1 walk): clock, energy,
; deficits, environment, body temperature and health.
spend:  stx     act
        sta     scene_minutes
        tay
        lda     #0
        jsr     GIVAYF
        fst     t5              ; minutes
        fst     s_step
        fop     FMULT, f_inv60
        fst     t4              ; hours
        fop     FADD, s_hour    ; hour of the day, wrapping at 24
        fst     s_hour
        fop     FCOMP, f_24
        cmp     #$FF
        beq     :+
        fld     f_24
        fop     FSUB, s_hour    ; s_hour - 24: a new day
        fst     s_hour
        lda     #1
        sta     newday
:       fld     t4
        fop     FADD, s_elap
        fst     s_elap
        fld     t5              ; date += minutes / 525600
        fop     FMULT, f_inv_year
        fop     FADD, s_date
        fst     s_date
        fop     FCOMP, f_one
        cmp     #$FF
        beq     :+
        fld     f_one
        fop     FSUB, s_date    ; s_date - 1
        fst     s_date
:       lda     #3
        jsr     overlay_load
        jsr     module_survival_clock
        jsr     spend_energy
        lda     newday
        beq     :+
        lda     #0
        sta     newday
        lda     #22
        jsr     overlay_load
        jsr     module_medical_day
        jsr     forage_day      ; env_day, then lot 4's $4C48 (ALERT)
:       ; Fauna only reads the new clock and terrain, not air temperature.
        ; Keep ENV loaded for its checks instead of loading THERM, then ENV,
        ; then THERM again when health is due. DOS reads dominate real travel.
        jsr     native_here
        asl     a               ; water bit -> carry
        lda     #0
        rol     a
        asl     a               ; 0 dry / 2 immersed, no persistent wetness
        sta     wet_mode
        jsr     weather_wet
        jsr     env_hour
@health_due:
        lda     health_due
        beq     @done
        lda     health_minutes+1
        ldy     health_minutes
        jsr     GIVAYF
        fst     s_step          ; thermal update uses time since last update
        lda     health_minutes  ; lot 4: for the spoilage clock (ALERT)
        sta     fg_hm
        lda     health_minutes+1
        sta     fg_hm+1
        jsr     weather_step
        jsr     thermal
        jsr     health_alerts   ; health, then the original alert rules (alerts.s)
@done:  lda     act
        cmp     #1
        bne     :+
        jsr     scene_update    ; native health/wind precede T0A/S00
:       jsr     stationary_resources
        jmp     ui_monitor

.segment "ENVIRON"
native_finish_resources:
        lda     act
        cmp     #4              ; native animal reactions do not discover resources
        bne     :+
        lda     #0
        sta     scene_minutes   ; subsequent VIEW must not rescan the reaction
        rts
:       cmp     #5
        bne     :+
        lda     #22
        jsr     overlay_load
        jsr     module_wound_retention
:       cmp     #1
        beq     native_finish_travel
native_stationary_resources:
        jsr     fauna_environment
        lda     #12
        jsr     overlay_load
        jmp     module_stationary_resources
native_finish_travel:
        lda     #12
        jsr     overlay_load
        jmp     module_stationary_resources_tail
.segment "GCODE"
native_resource_results:
        lda     MAP+36
        beq     @done
        lda     #14             ; ITEMS (lot 4: the piles, src/forage.s)
        jsr     overlay_load
        jmp     module_resource_results
@done:  rts
.segment "ENVIRON"
native_nature:
        jsr     fauna_age
        jmp     native_stationary_resources

.segment "GCODE"
stationary_resources:
        jmp     native_finish_resources

; spend_energy -- integer kcal for this step, matching m098. The most
; recently computed shivering flag contributes .04*body weight kcal/min.
; s_metabolic retains the base rate used by the thermal thresholds.
spend_energy:
        lda     #3
        jsr     overlay_load
        jmp     module_spend_energy
.segment "ENVIRON"
module_spend_energy:
        lda     act
        cmp     #4
        bcc     :+
        fld     s_metabolic     ; reaction's effort prepared by OUTDOOR
        jmp     @base
:
        cmp     #3
        bne     :+
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, tree_effort
        fop     FADD, f_rest_rate
        jmp     @base
:        cmp     #2
        bne     :+
        fld     f_eat_rate
        jmp     @base
:       cmp     #1
        beq     @walk
        fld     f_rest_rate
        jmp     @base
@walk:  lda     verb
        cmp     #V_SWIM
        bne     @land
        jsr     swim_metabolic
        jmp     @base
@land:  jsr     module_land_metabolic
@base:  fst     s_metabolic
        lda     thermal_mode
        cmp     #2
        bne     @cost
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FMULT, f_shiver_k
        fop     FADD, s_metabolic
@cost:  fst     t3                      ; original rounds the effective rate
        fld     t3
        fop     FMULT, s_step
        jsr     AYINT
        lda     $A0
        ldy     $A1
        jsr     GIVAYF
        fst     t3                      ; integer cost for the food deficit
        fop     FADD, s_spent
        fst     s_spent
        rts

.segment "GCODE"
swim_metabolic:
        lda     #3
        jsr     overlay_load
        jmp     module_swim_metabolic

swim_step:
        lda     #3
        jsr     overlay_load
        lda     #12
        jsr     overlay_load
        jmp     module_swim_step

swim_prepare:
        lda     #3              ; shore probes call native_here in SIM, even before a step
        jsr     overlay_load
        lda     #12
        jsr     overlay_load
        jmp     module_swim_prepare

walk_prepare:
        lda     #3
        jsr     overlay_load
        lda     #12
        jsr     overlay_load
        jmp     module_walk_prepare
walk_step:
        lda     #12
        jsr     overlay_load
        jmp     module_walk_step
walk_climb:
        lda     #12
        jsr     overlay_load
        jmp     module_walk_climb

swim_next:
        lda     #12
        jsr     overlay_load
        jmp     module_swim_next

.segment "LOWCODE"
swim_land:
        lda     #12
        jsr     overlay_load
        jmp     module_swim_land
.segment "SCRATCH"
travel_shore: .res 1
.segment "GCODE"

; health -- H = Hmax x (1 - (Dw/190)^2) (1 - (Df/480)^2) (1 - (Dr/68)^2), each
; factor at least 0; dead under 0.3
health: lda     #3
        jsr     overlay_load
        jmp     module_health

injury_health:
        lda     #18
        jsr     overlay_load
        jsr     module_medical_clothing
        jsr     module_medical_apply
        jsr     module_hazards
        lda     #17
        jsr     overlay_load
        jmp     module_injury_health
do_medical:
        jsr     orient_use      ; lot 7: USE MAP, COMPASS, WATCH... SHADOW
        lda     #19
        jsr     overlay_load
        jmp     module_medical_command
.assert print_str_ax > 0, error ; STATUS, INVENTORY print with it (print.asm .ifref)
medical_apply:
        lda     #17
        jsr     overlay_load
        jsr     module_medical_clothing
        jmp     module_medical_apply
tree_spend:
        lda     #30
        ldx     #3
        jsr     spend
        jmp     report

medical_spend:
        pha
        jsr     medical_apply
        lda     #<m_ok
        ldx     #>m_ok
        jsr     message
        pla
        beq     @done
        ldx     #0
        jsr     spend
@done:  jmp     report

clamp0: lda     FACSGN
        bpl     @ok
        lda     #0
        sta     FAC
        sta     FACSGN
@ok:    rts

negate: lda     FAC
        beq     @z
        lda     FACSGN
        eor     #$FF
        sta     FACSGN
@z:     rts

; env_day -- once a day (and at the start): the sun and the day's mean
; temperature T0; env_hour then gives the period and the air temperature.
;   sin(decl) = 0.398 sin(2 pi date - 1.378); half day excess
;   x = 12/pi asin(tan(lat) tan(decl)); sunrise 6 - x, sunset 18 + x;
;   night outside [sunrise - 0.75, sunset + 0.75].
;   T0 = (Tw + Ts)/2 + (Ts - Tw)/2 sin(2 pi (date - 1/4)); A = altitude/100;
;   mean Tm = T0 - A/4; range 15 + A/5 + 0.15 |lat|; minimum at sunrise - 1,
;   maximum at sunset - 4, linear in between and over the night.
.segment "ENVIRON"
module_env_day:
        fld     s_date
        fop     FMULT, f_2pi
        fop     FSUB, f_1_378           ; 1.378 - 2 pi date
        jsr     negate
        jsr     FSIN
        fop     FMULT, f_0_398
        fst     t1                      ; sin(decl)
        fop     FMULT, t1
        fop     FSUB, f_one             ; cos^2
        jsr     FSQR
        fst     t2                      ; cos(decl)
        fld     t2
        fop     FDIV, t1                ; tan(decl) = sin / cos
        fst     t3
        ldy     M_LAT                   ; tan(lat): sin / cos
        lda     #0
        cpy     #$80
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FMULT, f_rad
        fst     t4                      ; lat in radians
        jsr     FSIN
        fst     t1
        fld     t4
        fop     FADD, f_half_pi         ; cos = sin(lat + pi/2)
        jsr     FSIN
        fop     FDIV, t1                ; tan(lat) = sin / cos
        fop     FMULT, t3               ; y = tan(lat) tan(decl)
        fst     t1                      ; asin(y) = atn(y / sqrt(1 - y^2))
        fop     FMULT, t1
        fop     FSUB, f_one
        jsr     FSQR
        fop     FDIV, t1                ; y / sqrt(1 - y^2)
        jsr     FATN
        fop     FMULT, f_12_pi          ; x (hours)
        fst     t1
        fop     FSUB, f_6               ; sunrise = 6 - x
        fst     s_rise
        fld     t1
        fop     FADD, f_18
        fst     s_set
        ; T0 = (Tw + Ts)/2 + (Ts - Tw)/2 sin(2 pi (date - 1/4))
        fld     f_quarter
        fop     FSUB, s_date            ; date - 1/4
        fop     FMULT, f_2pi
        jsr     FSIN
        fst     t1
        sec                             ; (Ts - Tw) / 2
        lda     M_TSUM
        sbc     M_TWIN
        tay
        lda     #0
        jsr     GIVAYF
        fop     FMULT, f_half
        fop     FMULT, t1
        fst     t1
        clc                             ; (Tw + Ts) / 2
        lda     M_TSUM
        adc     M_TWIN
        tay
        lda     #0
        rol     a
        jsr     GIVAYF
        fop     FMULT, f_half
        fop     FADD, t1                ; T0
        fst     s_t0
        jsr     weather_daily
        jsr     native_here
        and     #127
        sta     weather_day_level
        rts

; env_hour -- period of the day (night, dawn, am, pm, dusk) and the air
; temperature at this hour and altitude, from env_day's values
.segment "THERMAL"
module_env_hour:
        ; period: night, dawn, am, pm, dusk
        fld     s_rise
        fop     FSUB, f_twilight        ; ... 0.75 - rise
        jsr     negate                  ; rise - 0.75
        ldx     #0                      ; period counts up (X is not kept by
        stx     period                  ; the ROM float routines)
        fop     FCOMP, s_hour           ; vs hour
        cmp     #1
        beq     @per                    ; hour < rise - 0.75: night
        inc     period
        fld     s_rise
        fop     FCOMP, s_hour
        cmp     #1
        beq     @per                    ; dawn
        inc     period
        fld     f_12
        fop     FCOMP, s_hour
        cmp     #1
        beq     @per                    ; am
        inc     period
        fld     s_set
        fop     FCOMP, s_hour
        cmp     #1
        beq     @per                    ; pm
        inc     period
        fld     s_set
        fop     FADD, f_twilight
        fop     FCOMP, s_hour
        cmp     #1
        beq     @per                    ; dusk
        lda     #0
        sta     period
@per:   lda     #0
        ldx     period
        bne     :+
        lda     #1
:       sta     night
        jsr     sky_position
        jsr     weather_temperature
        jsr     temperature_wave
        jsr     weather_air_visibility
        jmp     thermal_wind

; T09/S08 $5986: INT(5*SIN(.0187*elapsed + phase)), including floor
; for negative values. Keep the saved first-journey phase as mutable state.
temperature_wave:
        fld     s_elap
        fop     FMULT, f_temp_frequency
        fop     FADD, s_temp_phase
        jsr     FSIN
        fop     FMULT, f_5
        jsr     AYINT
        clc
        lda     $A1
        adc     airtemp
        sta     airtemp
        rts

.segment "LOWTEXT"
s_temp_phase: .byte $82,$72,$B2,$61,$CF ; saved Sierra first journey, 3.7921375772
; Used only by the loaded daily environment module.
.segment "ENVIRON"
f_temp_frequency: .byte $7B,$19,$30,$BE,$0E ; .0187 radians/hour

.segment "GCODE"
; dist_goal -- FAC = distance from the player to the outpost, in map units
dist_goal:
        lda     #21
        jsr     overlay_load
        jmp     module_dist_goal

; STATUS and the hall of fame run in the SIM window: ADVENTURE ($5800)
; returns to them directly.
.pushseg
.segment "LOWCODE"
goal_pct:
        lda     #21
        jsr     overlay_load
        jmp     module_progress
.popseg

; goal_pct -- A = GOAL% (0..100):
;   u = hours elapsed, v = 0.6 (D0 - d) / u, e = exp(-2.5 u / D0),
;   G = e + v (1 - e) (G = 1 when u = 0)
; ----------------------------------------------------------------------------
; messages
; ----------------------------------------------------------------------------
; Results replace previous messages without consuming a command key.
; They fill the result column (rows 20-22, columns 0-38: src/menu.s),
; wrapped by words, and persist until the next action supplies a result.
message:
        cpx     #0              ; a text of the bank: A = its number
        bne     :+
        jsr     text_fetch
:       sta     gp1
        stx     gp1+1
        jsr     msg_begin
message_body:                   ; camp_say: a message after the previous one
message_text:                   ; alerts.s appends from the cursor (gp1 set)
        ldy     #0
@ch:    lda     (gp1),y
        beq     @end
        cmp     #'|'
        beq     @nl
        cmp     #'^'
        beq     @noun
        cmp     #'#'
        beq     @num
        cmp     #'$'
        beq     @stock
        cmp     #'!'
        beq     @reason
        cmp     #'~'
        jeq     @unknown
        cmp     #'@'
        jeq     message_region
        cmp     #'%'
        jeq     message_plural
        ora     #$80
        jsr     message_char
@next:  iny
        bne     @ch
@end:   jsr     msg_flush
        lda     #1
        sta     shown
        rts
@nl:    jsr     msg_newline
        jmp     @next
@noun:  tya
        pha
        ldx     noun
        beq     @typed
        cpx     #76
        bcs     @typed
        lda     it_name_lo,x
        sta     gp2
        lda     it_name_hi,x
        sta     gp2+1
        jmp     @name
@typed: lda     #<nounbuf
        sta     gp2
        lda     #>nounbuf
        sta     gp2+1
@name:  jsr     message_string
        pla
        tay
        jmp     @next
@num:   tya
        pha
        lda     msgnum
        sta     num
        lda     msgnum+1
        sta     num+1
        jsr     msg_flush
        jsr     print_u16
        pla
        tay
        jmp     @next
@stock: tya
        pha
        lda     stock_available
        sta     num
        lda     stock_available+1
        sta     num+1
        jsr     msg_flush
        jsr     print_u16
        pla
        tay
        jmp     @next
@reason:
        tya
        pha
        ldx     travel_reason
        lda     travel_reason_lo,x
        sta     gp2
        lda     travel_reason_hi,x
        sta     gp2+1
        jsr     message_string
        pla
        tay
        jmp     @next
@unknown:
        tya
        pha
        ldy     #0
@skip:  lda     inbuf,y
        cmp     #' '
        bne     @word
        iny
        bne     @skip
@word:  ldx     #12
@letter:
        lda     inbuf,y
        beq     @word_end
        cmp     #' '
        beq     @word_end
        ora     #$80
        jsr     message_char
        iny
        dex
        bne     @letter
@word_end:
        pla
        tay
        jmp     @next

message_next = @next
message_string:
        ldy     #0
@char:  lda     (gp2),y
        beq     @end
        ora     #$80
        jsr     message_char
        iny
        bne     @char
@end:   rts

.pushseg
.segment "CODE"
; Optional S for the 16-bit number printed by '#'; 257 is plural too.
message_plural:
        lda     msgnum
        eor     #1
        ora     msgnum+1
        beq     @next
        lda     #'S'|$80
        jsr     message_char
@next:  jmp     message_next
.popseg

; Words are placed whole in the result column; the last column stays
; reserved, so an expanded name can never scroll the window (src/menu.s).
message_char = msg_char

; ----------------------------------------------------------------------------
; STATUS and INVENTORY (text screens)
; ----------------------------------------------------------------------------
.segment "GCODE"
text_screen:
        jsr     text_mode40     ; menus keep the 40-column layout
        lda     #0
        sta     WNDTOP
        jsr     vtab
        ; Fall through to the shared COUT installer.
text_begin:
        lda     $36
        sta     text_vector_lo
        lda     $37
        sta     text_vector_hi
        lda     #<topo_output
        sta     $36
        lda     #>topo_output
        sta     $37
        rts

.segment "CODE"

back_to_view_now:
        lda     #20
        sta     WNDTOP
        jsr     text_mode80     ; menu rows 20..23 are cleared in both pages
        jsr     t_home
        jsr     show_dhgr
        lda     #0
        sta     shown
        rts

.segment "GCODE"
; puts -- print the string after the JSR (0-terminated), "|" = new line
puts:   pla
        sta     gp2
        pla
        sta     gp2+1
        ldy     #0
@ch:    inc     gp2
        bne     :+
        inc     gp2+1
:       lda     (gp2),y
        beq     @end
        cmp     #'|'
        bne     :+
        jsr     CROUT
        jmp     @ch
:       ora     #$80
        jsr     COUT
        jmp     @ch
@end:   lda     gp2+1
        pha
        lda     gp2
        pha
        rts

; word -- print A characters of the table at gp2 + X * A (fixed-width words)
word:   sta     g2
        txa
        tay
        lda     #0
@mul:   dey
        bmi     @got
        clc
        adc     g2
        jmp     @mul
@got:   tay
        ldx     g2
@ch:    lda     (gp2),y
        ora     #$80
        jsr     COUT
        iny
        dex
        bne     @ch
        rts

; pdec -- print A (0..255) in decimal
.segment "LOWCODE"
pdec:   sta     num
        lda     #0
        sta     num+1
        jmp     print_u16

tab = pad_to                    ; A = column: differential spaces up to it
.segment "GCODE"

.segment "STATUS"
sky_words: .byte "CLEARCLOUDRAIN SNOW "

.segment "GCODE"
; ----------------------------------------------------------------------------
; tables
; ----------------------------------------------------------------------------
.segment "LOWTEXT"
screen_lo:
        .byte   <scr_topo, <scr_view, <scr_status, <scr_inventory, <scr_help, <scr_notyet, <scr_map, <scr_equipment
screen_hi:
        .byte   >scr_topo, >scr_view, >scr_status, >scr_inventory, >scr_help, >scr_notyet, >scr_map, >scr_equipment
.segment "GDATA"
verbs:  .byte   17, 18, 37, V_WEAR, V_DROP, V_GET, V_CARRY, V_PACK, V_DRINK, V_EAT, V_LOOK, V_PAN
        .byte   41, 42          ; SAVE, RESTORE (lot 9, src/save.s)
        .byte   V_WAIT, V_REST, V_CAMP, V_EXER, V_WALK, V_RUN, V_MOVE, V_CRAWL, V_SWIM, V_ENTER, V_EXIT, V_USE, 26, V_CLIMB, V_HANG, V_LOWER, 30, 32, 0
verb_lo:
        .byte <do_outdoor, <do_outdoor, <do_outdoor
        .byte   <do_wear, <do_drop, <do_get, <do_get, <do_get, <do_drink, <do_eat, <do_look, <do_look
        .byte   <do_save, <do_save
        .byte   <do_rest, <do_rest, <do_rest, <do_rest, <do_walk, <do_walk, <do_walk, <do_walk, <do_walk
        .byte   <do_site, <do_site, <do_medical, <do_medical, <do_tree, <do_medical, <do_medical, <do_medical, <do_medical ; HANG: care.s (lot 13)
verb_hi:
        .byte >do_outdoor, >do_outdoor, >do_outdoor
        .byte   >do_wear, >do_drop, >do_get, >do_get, >do_get, >do_drink, >do_eat, >do_look, >do_look
        .byte   >do_save, >do_save
        .byte   >do_rest, >do_rest, >do_rest, >do_rest, >do_walk, >do_walk, >do_walk, >do_walk, >do_walk
        .byte   >do_site, >do_site, >do_medical, >do_medical, >do_tree, >do_medical, >do_medical, >do_medical, >do_medical
card_lo: .byte  <0, <140, <280, <420
card_hi: .byte  >0, >140, >280, >420
cdef_lo: .byte  <s_defw, <s_deff, <s_defr
cdef_hi: .byte  >s_defw, >s_deff, >s_defr
ctol_lo: .byte  <f_tol_water, <f_tol_food, <f_tol_rest
ctol_hi: .byte  >f_tol_water, >f_tol_food, >f_tol_rest

.segment "TEXT"
        .include "messages.inc"

        .include "travel.s"
        .include "survival.s"
        .include "thermal.s"
        .include "weather.s"
        .include "medical.s"
        .include "hazards.s"
        .include "sites.s"
        .include "topo_dhgr.s"
        .include "project.s"
        .include "tree.s"
.segment "CODE"

.segment "ENVIRON"
native_walk_water:
        sta     g0
        lda     #1
        sta     travel_reason
        lda     MAP+37
        beq     @no
        sta     travel_shore
        lda     g0
        and     #$7F
        sec
        rts
@no:    clc
        rts
native_clothes_changed:
        lda     MAP+37
        beq     @done
        jsr     thermal_clothes
        lda     #15
        sta     health_period
        lda     #14
        jsr     overlay_load
@done:  rts
