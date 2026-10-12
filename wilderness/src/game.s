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
CLREOP  = $FC42

M_GOALX  = MAP + 8              ; goal cell
M_GOALY  = MAP + 9
M_LAT    = MAP + 12             ; latitude, degrees (signed)
M_TWIN   = MAP + 13             ; winter / summer mean temperature (deg F)
M_TSUM   = MAP + 14
M_WIND   = MAP + 15             ; highest wind (mph)
M_MAG    = MAP + 24             ; signed magnetic declination, degrees

MSG_ROW  = 21                   ; message lines 21-23, command line 20
CMD_ROW  = 20
MAXLINE  = 36

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


; ----------------------------------------------------------------------------
; Disk overlays. DOS owns ZP during BLOAD; dos.asm restores every byte,
; including FAC, the text window and the command state. Preserve the four
; mixed text rows around DOS's output. No call replaces its caller's window:
; simulation at $2000 may request input at $5800.
; ----------------------------------------------------------------------------
.segment "GDATA"
overlay_current: .byte 0
overlay_wanted: .byte 0
overlay_reads: .word 0
sim_loaded: .byte 0
.segment "SCRATCH"
overlay_text: .res 160
.segment "GCODE"

scr_status:
        lda     #16
        jsr     overlay_load
        jmp     module_status
scr_inventory:
        lda     #2
        jsr     overlay_load
        jmp     module_inventory
env_day:
        lda     #3
        jsr     overlay_load
        jmp     module_env_day
env_hour:
        lda     #4
        jsr     overlay_load
        jmp     module_env_hour

thermal:
        lda     #4
        jsr     overlay_load
        jmp     module_thermal

overlay_load:
        cmp     #18
        bne     :+
        lda     #17             ; hazards and medical share one image
:       cmp     #3
        beq     @sim
        cmp     #4
        beq     @sim
        cmp     overlay_current
        bne     @load
        rts
@sim:   lda     sim_loaded
        beq     :+
        rts
:       lda     #1
        sta     ui_dirty        ; SIM overwrites the cached graphical header
        lda     TXTSET          ; HGR is hidden while its RAM holds simulation
        lda     #3              ; all three simulation IDs share one binary
@load:  sta     overlay_wanted
        ldx     #39
@save:  .repeat 4, I
        lda     $0650+I*$80,x
        sta     overlay_text+I*40,x
        .endrepeat
        dex
        bpl     @save
        ; DOS uses the live text window, confined to the message rows.
        ldx     #9
@window:
        lda     $20,x
        sta     apple2_zp_buf+$20,x
        dex
        bpl     @window
        jsr     dos_cmd_new
        lda     #<ov_prefix
        ldy     #>ov_prefix
        jsr     dos_cmd_add
        ldx     overlay_wanted
        lda     overlay_name_lo-1,x
        ldy     overlay_name_hi-1,x
        jsr     dos_cmd_add
overlay_before_dos = *
        jsr     dos_cmd_run
        ldx     #39
@restore:
        .repeat 4, I
        lda     overlay_text+I*40,x
        sta     $0650+I*$80,x
        .endrepeat
        dex
        bpl     @restore
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
.export overlay_before_dos, overlay_ready

.segment "GDATA"
overlay_name_lo: .byte <ov_vocab, <ov_screen, <ov_env, <ov_env, <ov_wreck, <ov_bear, <ov_cougar, <ov_snake, <ov_cabin, <ov_sites, <ov_project, <ov_travel, <ov_input, <ov_items, <ov_summary, <ov_status, <ov_medical, <ov_medical, <ov_medview, <ov_tree
overlay_name_hi: .byte >ov_vocab, >ov_screen, >ov_env, >ov_env, >ov_wreck, >ov_bear, >ov_cougar, >ov_snake, >ov_cabin, >ov_sites, >ov_project, >ov_travel, >ov_input, >ov_items, >ov_summary, >ov_status, >ov_medical, >ov_medical, >ov_medview, >ov_tree
ov_prefix: .byte "BLOAD WILD",0
ov_vocab: .byte "VOC,A$5800", 0
ov_screen: .byte "SCR,A$5800", 0
ov_env: .byte "SIM,A$2000", 0
ov_wreck: .byte "PLN,A$5800", 0
ov_bear: .byte "BER,A$5800", 0
ov_cougar: .byte "COU,A$5800", 0
ov_snake: .byte "RAT,A$5800", 0
ov_cabin: .byte "HUT,A$5800", 0
ov_sites: .byte "SIT,A$5800", 0
ov_project: .byte "PRJ,A$5800", 0
ov_input: .byte "INP,A$5800", 0
ov_items: .byte "ITM,A$5800", 0
ov_summary: .byte "HUD,A$5800",0
ov_status: .byte "STA,A$5800",0
ov_travel: .byte "TRV,A$5800",0
ov_medical: .byte "MED,A$5800",0
ov_medview: .byte "MVI,A$5800",0
ov_tree: .byte "TRE,A$5800",0
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
rnd:     .word  $ACE1
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
        lda     #20
        jsr     overlay_load
        jsr     module_game_init
        jsr     show_view
        lda     #<m_crash
        ldx     #>m_crash
        jsr     message
        jmp     main

.segment "TREE"
module_game_init:
        lda     px+1
        sta     cachex
        lda     py+1
        sta     cachey
        ldx     #75
@ground:
        lda     cachex
        sta     it_x,x
        lda     cachey
        sta     it_y,x
        dex
        bne     @ground
        jsr     load_totals
        jsr     dist_goal       ; D0 = distance to the outpost at the start
        fst     s_d0
        jsr     env_day
        jsr     hud_init
        jsr     env_hour
        jsr     ui_monitor
        rts

.segment "GCODE"
; main loop: read a command, parse it, run it
main:   lda     dead
        ora     won
        bne     the_end
        jsr     get_line
        lda     #0
        sta     shown
        jsr     do_command
        jsr     finish_simulation
        jsr     summary_refresh
        jmp     main

the_end:
        jsr     wait_any
        jmp     quit

; ----------------------------------------------------------------------------
; command line
; ----------------------------------------------------------------------------
; get_line -- "? " on row 20, letters and spaces up to 36, LEFT erases; on an
; empty line LEFT / RIGHT turn the view 22.5 degrees; ESC clears input.
get_line:
        lda     #0
        sta     linelen
        jsr     prompt
idle:   lda     KBD             ; tests wait for this loop
        bpl     idle
        bit     KBDSTRB
        and     #$7F
        jsr     kbd_upcase
        cmp     #KC_RET
        beq     @done
        ldx     linelen
        cmp     #KC_LEFT
        beq     @left
        cmp     #KC_RIGHT
        beq     @right
        cmp     #KC_ESC
        bne     @char
        jmp     get_line
@left:  cpx     #0
        beq     @turnl
        dec     linelen
        dec     CH
        lda     #' '|$80
        jsr     COUT
        dec     CH
        jmp     idle
@turnl: ldx     #0
        beq     @turn
@right: cpx     #0
        bne     idle
        ldx     #1
@turn:  jsr     turn_view
        jmp     idle
@char:  cmp     #' '
        bcc     idle
        cmp     #'Z'+1
        bcs     idle
@put:   cpx     #MAXLINE
        bcs     idle
        sta     inbuf,x
        inc     linelen
        ora     #$80
        jsr     COUT
        jmp     idle
@done:  ldx     linelen
        lda     #0
        sta     inbuf,x
        rts

prompt: lda     #CMD_ROW
        jsr     vtab
        jsr     CLREOL
        lda     #'?'|$80
        jsr     COUT
        lda     #' '|$80
        jmp     COUT

.segment "CODE"
vtab:   sta     CV
        lda     #0
        sta     CH
        jmp     VTAB
.segment "GCODE"

; Input overlay: only numeric actions and QUIT load it.
get_duration:
        ldy     #1
        bne     number_entry
get_quantity:
        ldy     #2
        bne     number_entry
get_number:
        ldy     #0
number_entry:
        sty     input_mode
        cpy     #2
        beq     @load
        ldy     input_argument
        bne     :+
        jsr     message
:
@load:  lda     #13
        jsr     overlay_load
        jmp     module_number

.segment "INPUT"
; Both callers have just read a duration, so INPUT is still loaded here.
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
        lda     linelen
        cmp     #5
        bne     :+
        lda     inbuf
        cmp     #'S'
        beq     @input          ; SLEEP avoids VOCAB -> INPUT round trip
:
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
@input: lda     #13
        jsr     overlay_load
        jsr     module_input_command
        bcc     @ordinary
        rts
@ordinary:
        ldx     #0
@word:  stx     g0
        lda     fast_words,x
        beq     @full
        sta     g2
        cmp     linelen
        bne     @next
        ldy     #0
@letter:
        inx
        lda     fast_words,x
        cmp     inbuf,y
        bne     @next
        iny
        cpy     g2
        bcc     @letter
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
        and     #127
        sta     verb
        cmp     #V_REST
        beq     @rest
        jmp     do_walk
@rest:  jmp     do_rest
@next:  lda     g0
        clc
        adc     g2
        adc     #2
        tax
        jmp     @word
@full:  jsr     parse
        jmp     dispatch
.segment "LOWTEXT"
; High bit distinguishes a travel/rest verb from a screen noun.
fast_words:
        .byte 4,"WALK",V_WALK|$80,4,"REST",V_REST|$80,4,"SWIM",V_SWIM|$80
        .byte 4,"TOPO",103,4,"VIEW",104,6,"STATUS",105
        .byte 9,"INVENTORY",106,4,"HELP",107,0
.segment "GCODE"
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

.segment "VOCAB"
dispatch:
        jsr     resolve_noun
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
@later: lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message

; ----------------------------------------------------------------------------
; screens
; ----------------------------------------------------------------------------
.segment "GCODE"
do_nature:
        lda     #13
        jsr     overlay_load
        jmp     module_nature

scr_notyet:
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message

scr_view:
        jmp     show_view

scr_help:
        lda     #2
        jsr     overlay_load
        jmp     module_help
.segment "SCREENS"
module_help:
        lda     #0
        sta     help_page
help_redraw:
        jsr     text_screen
        lda     #$3F
        sta     $32             ; inverse title, readable on a monochrome display
        jsr     puts
        .byte " WILDERNESS - HELP ",0
        lda     #$FF
        sta     $32
        jsr     puts
        .byte "||",0
        ldx     help_page
        lda     help_lo,x
        pha
        lda     help_hi,x
        tax
        pla
        jsr     print_str_ax
        lda     #20
        jsr     vtab
        jsr     puts
        .byte "1 TRAVEL  2 SURVIVAL|N/SPACE NEXT   B BACK|ESC/RETURN: VIEW|I INVENTORY  S STATUS  T TOPO",0
help_key:
        jsr     wait_key
        cmp     #'I'
        jeq     scr_inventory
        cmp     #'S'
        jeq     scr_status
        cmp     #'T'
        jeq     scr_topo
        cmp     #KC_ESC
        jeq     back_to_view_now
        cmp     #KC_RET
        jeq     back_to_view_now
        cmp     #'1'
        beq     @select
        cmp     #'2'
        beq     @select
        cmp     #'N'
        beq     @next
        cmp     #' '
        beq     @next
        cmp     #'B'
        bne     help_key
@next: lda     help_page
        eor     #1
        sta     help_page
        jmp     help_redraw
@select:
        sec
        sbc     #'1'
        sta     help_page
        jmp     help_redraw
help_page: .byte 0
help_lo: .byte <help_travel,<help_survival
help_hi: .byte >help_travel,>help_survival
help_travel:
        .byte "1/2  TRAVEL AND ORIENTATION",13,13
        .byte "LOOK N/E/S/W  FACE A COMPASS POINT",13
        .byte "LOOK L/R/B    TURN OR LOOK BEHIND",13
        .byte "LEFT/RIGHT   TURN ON AN EMPTY LINE",13,13
        .byte "WALK 1 H     WALK IN YOUR DIRECTION",13
        .byte "SWIM 1 H     CROSS WATER",13
        .byte "ESC          STOP AFTER THIS STEP",13,13
        .byte "TOPO         MAP; ARROWS/WASD SCROLL",13
        .byte "C            CENTER MAP ON YOU",13
        .byte "STATUS       HEALTH; M FOR MEDICAL",13,13
        .byte "ENTER SHELTER / EXIT SHELTER",13
        .byte "USE THE CABIN AT ITS MAP CELL.",0
help_survival:
        .byte "2/2  SUPPLIES AND REST",13,13
        .byte "DRINK WATER 4 OZ",13,"EAT CHEESE 8 OZ",13
        .byte "REST 1 H     REST; WAIT 10 MIN WAITS",13,13
        .byte "INVENTORY    1-5 SELECT ITEM LOCATION",13
        .byte "GET AXE      PACK; CARRY AXE IN HAND",13
        .byte "WEAR PARKA   WEAR; DROP AXE PUTS DOWN",13
        .byte "USE FLAGYL   ONE MEDICAL DOSE",13,13
        .byte "CLIMB TREE / CLIMB DOWN",13
        .byte "HANG FOOD    HANG PACK AND CONTENTS",13
        .byte "LOWER FOOD   RECOVER AT THE SAME TREE",13,13
        .byte "OMIT AMOUNT TO BE ASKED. ESC CANCELS.",13
        .byte "H = HOURS; MIN = MINUTES; OZ = OUNCES.",0
.segment "GCODE"
do_site:
        lda     #10
        jsr     overlay_load
        jmp     module_site
scr_topo:
        lda     #10
        jsr     overlay_load
        jmp     module_topo
shelter_view:
        lda     #10
        jsr     overlay_load
        jmp     module_shelter_view

; show_view -- the view, or black and NOT ENOUGH LIGHT at night
show_view:
        jsr     scene_update
        lda     #0
        sta     sim_loaded
        jsr     summary_prepare
        jsr     show_view_scene
        lda     TXTCLR
        rts
show_view_scene:
        lda     shelter_inside
        beq     :+
        jsr     shelter_view
        jmp     hud_draw
:
        lda     night
        bne     @dark
        jsr     scene_prepare
        jmp     view_full
@dark:  lda     #0
        sta     scene_drawn
        ; view_full clears the terrain before the dark-sky pass.
        jsr     view_full
        lda     #<m_nolight
        ldx     #>m_nolight
        jmp     message

; Commands such as EAT/DRINK leave no explicit VIEW call. Restore their
; picture silently: preserve their messages and do not add key prompts.
.segment "CODE"
finish_simulation:
        lda     sim_loaded
        beq     @done
        lda     #0
        sta     sim_loaded
        jsr     summary_prepare
        lda     night
        ora     shelter_inside
        bne     @blank
        jsr     scene_prepare
        jsr     view_full
        jmp     @flip
@blank: lda     #0
        ldy     #39
@clear: jsr     clear_rows
        dey
        bpl     @clear
        lda     shelter_inside
        bne     :+
        jsr     view_full
:       jsr     hud_draw
@flip:  lda     TXTCLR
@done:  rts

.segment "CODE"
turn_view:                      ; X = view_turn kind; fixed geometry scrolls with terrain
        lda     night
        ora     shelter_inside
        bne     @full
        lda     scene_drawn
        cmp     #2
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
:       rts

.segment "GCODE"
; ----------------------------------------------------------------------------
; verbs
; ----------------------------------------------------------------------------
do_look:
        jmp     module_tree_look
do_tree:
        lda     #20
        jsr     overlay_load
        jmp     module_tree_command

magnetic_heading:
        ; T10/S0C adds TOPO $60A9 to magnetic cardinal directions.
        ldy     M_MAG
        lda     #0
        cpy     #128
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
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

; WALK, GO, RUN, MOVE, CRAWL, SWIM: hours, then cells along the
; heading. Our rule (the original's is not decoded yet): a cell (2 units)
; WALK takes 19 minutes per cell, plus 6 per level climbed.
; SWIM uses original integer-unit paths and the normal-swimming duration formula.
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
        lda     night           ; no first step when already after sunset
        beq     :+
        lda     #<m_dark
        ldx     #>m_dark
        jmp     message
:
        lda     #<m_hours
        ldx     #>m_hours
        jsr     get_duration
        bcs     @quit
        lda     msgnum
        ora     msgnum+1
        bne     @start
@quit:  rts
@start: jsr     prepare_minutes           ; minutes = hours * 60
        lda     heading
        sta     ang
        lda     heading+1
        sta     ang+1
        jsr     direction
        lda     dx
        sta     wdx
        lda     dx+1
        sta     wdx+1
        lda     dy
        sta     wdy
        lda     dy+1
        sta     wdy+1
        lda     verb
        cmp     #V_SWIM
        bne     :+
        jsr     swim_prepare
:
        lda     #0
        sta     used
        sta     used+1
        sta     input_interrupted
        sta     travel_shore
        sta     travel_reason
        inc     travel_action
@cell:  lda     KBD
        cmp     #KC_ESC|$80
        bne     :+
        bit     KBDSTRB
        inc     input_interrupted
        jmp     @stop
:        lda     verb
        cmp     #V_SWIM
        bne     :+
        jsr     swim_next
:       clc
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
        tax
        ldy     nx+1
        jsr     cell_at
        bpl     @land
        ldx     verb
        cpx     #V_SWIM
        beq     @swim
        jmp     @water
@land:  ldx     verb
        cpx     #V_SWIM
        bne     :+
        jsr     swim_land
        jcc     @stop
        jmp     @swim
:       sta     g0
        ldx     py+1
        ldy     px+1
        jsr     cell_at
        and     #$7F
        sta     g1
        lda     #19             ; minutes for this cell
        sta     stepmin
        lda     g0
        sec
        sbc     g1
        bcc     @time           ; downhill
        beq     @time
        cmp     #40             ; 19 + 6*40 > 255: reject before multiplying
        bcc     :+
        jmp     @pace
:
        sta     g1
        asl     a
        adc     g1
        asl     a               ; 6 per level
        bcc     :+
        jmp     @pace
:       adc     stepmin
        bcc     :+
        jmp     @pace
:
        sta     stepmin
        jmp     @time
@swim:  lda     used
        ora     used+1
        bne     :+
        lda     #15             ; T08/S07 $5AEE: first swimming health interval
        sta     health_period
:       jsr     swim_step
        bcc     :+
        jmp     @pace
:       lda     minutes+1
        bne     @go
        lda     stepmin
        lsr                     ; native admits >= floor(dt/2), then spends all dt
        cmp     minutes
        bcc     @go
        beq     @go
        jmp     @time_end
@time:  lda     minutes+1       ; enough time left?
        bne     @go
        lda     minutes
        cmp     stepmin
        bcs     :+
        jmp     @time_end
:
@go:    sec
        lda     minutes
        sbc     stepmin
        sta     minutes
        lda     minutes+1
        sbc     #0
        sta     minutes+1
        bcs     :+
        lda     #0              ; stop after a swimming step overshoots the request
        sta     minutes
        sta     minutes+1
:
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
        lda     stepmin
        ldx     #1
        jsr     spend
@progress:
        lda     #10
        jsr     overlay_load
        jsr     module_topo_moving
        lda     used
        sta     msgnum
        lda     used+1
        sta     msgnum+1
        lda     #<m_moving
        ldx     #>m_moving
        jsr     message
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
        lda     #9
        sta     travel_reason
        jmp     @stop
@water: lda     #1
        sta     travel_reason
@stop:  lda     used
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
:       lda     input_interrupted
        beq     :+
        lda     #6
        sta     travel_reason
:
        jsr     show_view
        lda     #<m_travel
        ldx     #>m_travel
        jsr     message
        jmp     report
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
        lda     stepmin
        ldx     #0
        jsr     spend
        lda     dead
        ora     fauna_alert
        beq     @step
@done:  lda     dead            ; died on the way: just the news
        beq     :+
        pla
        pla
        jmp     report
:       lda     verb            ; WAIT and PAUSE do not count as rest
        cmp     #V_WAIT
        beq     @msg
        fld     f_half          ; original REST leaves A2[18] at .5 hours
        fst     s_rest
@msg:   pla
        sta     msgnum
        pla
        sta     msgnum+1
        jsr     show_view
        jmp     rest_result
@out:   rts

.segment "TEXT"
; Resident result printer: the scene may have replaced the shared overlay.
rest_result:
        lda     verb
        cmp     #V_WAIT
        bne     @rest
        lda     #<m_waited
        ldx     #>m_waited
        ldy     input_unit
        cpy     #2
        bne     @fauna
        lda     #<m_wait_minutes
        ldx     #>m_wait_minutes
        jmp     @fauna
@rest:
        lda     #<m_rested
        ldx     #>m_rested
        ldy     input_unit
        cpy     #2
        bne     @fauna
        lda     #<m_rest_minutes
        ldx     #>m_rest_minutes
@fauna: ldy     fauna_alert
        beq     :+
        lda     #<m_fauna_stop
        ldx     #>m_fauna_stop
:
        jsr     message
        jmp     report

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
        lda     #16
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
:       lda     noun
        cmp     #N_WATER
        beq     @water
        lda     #<m_notyet
        ldx     #>m_notyet
        jmp     message
@water: tax
        jsr     have
        bcs     @ask
        jmp     no_item
@ask:   lda     #<m_ounces
        ldx     #>m_ounces
        jsr     get_quantity
        bcc     :+
        rts
:       ldx     #N_WATER
        jsr     take_oz
        lda     msgnum
        beq     @none
        ldy     msgnum
        lda     msgnum+1
        jsr     GIVAYF
        fop     FMULT, f_oz_hour
        fop     FSUB, s_defw
        fst     s_defw
        fld     f_half
        fst     s_drink
        fld     s_elap
        fst     s_last
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
do_get:
        lda     #14
        jsr     overlay_load
        jmp     module_do_get
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
        beq     @empty
        cmp     #0
        beq     @empty
        cmp     #$FF
        beq     @empty
@ready: jsr     save_item
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        jsr     at_ground
        bcc     @packed
        clc
        lda     it_pack_lo,x
        adc     it_gnd_lo,x
        sta     it_pack_lo,x
        lda     it_pack_hi,x
        adc     it_gnd_hi,x
        sta     it_pack_hi,x
        bcc     :+
        jmp     reject_overflow  ; even an overflowing quantity is atomic
:       lda     #0
        sta     it_gnd_lo,x
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
        bcs     :+
        rts
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
:       lda     #<m_worn
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
        jsr     load_totals
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
        lda     it_place,x
        beq     @missing
        cmp     #$FF
        beq     @missing
        jsr     save_item
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        beq     @missing
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
        adc     it_pack_lo,x
        sta     it_gnd_lo,x
        lda     it_gnd_hi,x
        adc     it_pack_hi,x
        sta     it_gnd_hi,x
        bcc     :+
        jmp     reject_overflow
:       lda     #0
        sta     it_pack_lo,x
        sta     it_pack_hi,x
@gear:  lda     #0
        sta     it_place,x
        lda     px+1
        sta     it_x,x
        lda     py+1
        sta     it_y,x
        jsr     load_totals
        lda     #<m_dropped
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
; Our additive model: limits = our initial usage + original initial free
; capacities (43 oz, 1525/4134/2542 in3). This reproduces the starting
; balance, not the original's still-unexplained container accounting.
load_limits: .word 879, 2149, 6000, 2874
load_vol: .res 2
load_bad: .byte 0
saved_item: .res 5
load_words: .byte "WEIGHT  WEAR VOLPACK VOLHAND VOL"
.segment "GCODE"

.segment "ITEMS"
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

.segment "ENVIRON"
module_load_totals:
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
        beq     @next
        cmp     #0
        beq     @next
        cmp     #$FF
        beq     @next
        cpx     #N_WATER
        bcc     @gear
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
:       ldx     noun
        rts

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
accept_load:
        jsr     load_totals
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
        jsr     load_totals
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
        jsr     message
        lda     #22
        jsr     vtab
        lda     load_reason_weight
        beq     @vol
        jsr     puts
        .byte "  WEIGHT: +",0
        ldy     #0
        jsr     load_numbers
        lda     #23
        jsr     vtab
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
report: lda     dead
        beq     @alive
        lda     #<m_dead
        ldx     #>m_dead
        ldy     travel_action
        beq     :+
        lda     #<m_dead_travel
        ldx     #>m_dead_travel
:
        jmp     message
@alive: lda     won
        beq     @weak
        lda     #<m_goal
        ldx     #>m_goal
        ldy     travel_action
        beq     :+
        lda     #<m_goal_travel
        ldx     #>m_goal_travel
:
        jmp     message
@weak:  fld     f_hmax          ; weak under a third of Hmax
        fop     FDIV, s_health  ; H / Hmax
        fop     FCOMP, f_third
        cmp     #1
        beq     @ok
        lda     #<m_weak
        ldx     #>m_weak
        ldy     travel_action
        beq     :+
        lda     #<m_weak_travel
        ldx     #>m_weak_travel
:
        jmp     message
@ok:    rts

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
        lda     it_place,x
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
        lda     it_place,x
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
mul60:  lda     msgnum
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

; cell_at -- A = grid byte of cell (Y = x, X = y); N = water
cell_at:
        lda     grid_lo,x
        sta     gp2
        lda     grid_hi,x
        sta     gp2+1
        lda     (gp2),y
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
        lda     #1
        sta     won
@no:    rts
@near:  clc                     ; C set when A in -1..1
        adc     #1
        cmp     #3
        rol     a               ; carry: A+1 >= 3
        eor     #1
        lsr     a
        rts

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
        lda     #18
        jsr     overlay_load
        jsr     module_medical_day
        jsr     env_day
:       ; Fauna only reads the new clock and terrain, not air temperature.
        ; Keep ENV loaded for its checks instead of loading THERM, then ENV,
        ; then THERM again when health is due. DOS reads dominate real travel.
        ldx     py+1
        ldy     px+1
        jsr     cell_at
        asl     a               ; water bit -> carry
        lda     #0
        rol     a
        asl     a               ; 0 dry / 2 immersed, no persistent wetness
        sta     wet_mode
        jsr     weather_wet
        lda     act
        cmp     #1              ; original T09/S08 skips T0A/S00 at rest/meals
        bne     @stationary
        jsr     scene_update
        jmp     @thermal
@stationary:
        lda     #0
        sta     scene_minutes
        sta     fauna_alert
@thermal:
        jsr     env_hour
        lda     health_due
        beq     @done
        lda     health_minutes+1
        ldy     health_minutes
        jsr     GIVAYF
        fst     s_step          ; thermal update uses time since last update
        jsr     weather_step
        jsr     thermal
        jsr     health
@done:  jmp     ui_monitor

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
@land:  fld     f_walk_rate
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
        lda     #12
        jsr     overlay_load
        jmp     module_swim_prepare

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
        lda     #19
        jsr     overlay_load
        jmp     module_medical_command
scr_medical:
        jsr     medical_apply
        lda     #19
        jsr     overlay_load
        jmp     module_medical_status
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
        jmp     weather_daily

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
f_temp_frequency: .byte $7B,$19,$30,$BE,$0E ; .0187 radians/hour

.segment "GCODE"
; dist_goal -- FAC = distance from the player to the outpost, in map units
dist_goal:
        lda     M_GOALX
        jsr     @delta
        fst     t1
        fop     FMULT, t1
        fst     t1
        lda     M_GOALY
        ldx     #py-px
        jsr     @delta2
        fst     t2
        fop     FMULT, t2
        fop     FADD, t1
        jmp     FSQR
@delta: ldx     #0
@delta2:                        ; FAC = (goal cell - position) x 2 units
        sec
        sbc     px+1,x
        tay
        lda     #0
        cpy     #$80
        bcc     :+
        lda     #$FF
:       jsr     GIVAYF
        fop     FMULT, f_2
        rts

; goal_pct -- A = GOAL% (0..100):
;   u = hours elapsed, v = 0.6 (D0 - d) / u, e = exp(-2.5 u / D0),
;   G = e + v (1 - e) (G = 1 when u = 0)
; ----------------------------------------------------------------------------
; messages
; ----------------------------------------------------------------------------
; Results replace previous messages without consuming a command key.
; The three rows persist until the next action supplies a result.
message:
        sta     gp1
        stx     gp1+1
@clear: lda     #MSG_ROW
        jsr     vtab
        jsr     CLREOP
        lda     #'>'|$80
        jsr     COUT
        lda     #' '|$80
        jsr     COUT
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
        ora     #$80
        jsr     message_char
@next:  iny
        bne     @ch
@end:   lda     #1
        sta     shown
        rts
@nl:    lda     CV
        cmp     #23
        bcs     @end
        jsr     CROUT
        lda     #' '|$80
        jsr     COUT
        jsr     COUT
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

message_string:
        ldy     #0
@char:  lda     (gp2),y
        beq     @end
        ora     #$80
        jsr     message_char
        iny
        bne     @char
@end:   rts

; Reserve the last column so an expanded name can never scroll the window.
message_char:
        pha
        lda     CH
        cmp     #39
        bcs     @clip
        pla
        jmp     COUT
@clip:  pla
        rts

; wait_any -- a key (messages read)
wait_any:
        jsr     wait_key
        lda     #0
        sta     shown
        rts

; ----------------------------------------------------------------------------
; STATUS and INVENTORY (text screens)
; ----------------------------------------------------------------------------
text_screen:
        lda     #0
        sta     WNDTOP
        lda     TXTSET
        jmp     HOME

back_to_view:
        jsr     wait_key
back_to_view_now:
        lda     #20
        sta     WNDTOP
        lda     TXTCLR
        lda     MIXSET
        jsr     HOME
        lda     #0
        sta     shown
        rts

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

tab:    sta     CH
        rts
.segment "GCODE"

.segment "SCREENS"
.segment "STATUS"
sky_words: .byte "CLEARCLOUDRAIN SNOW "
.segment "SCREENS"
        .include "inventory.s"

.segment "GCODE"
; ----------------------------------------------------------------------------
; tables
; ----------------------------------------------------------------------------
.segment "LOWTEXT"
screen_lo:
        .byte   <scr_topo, <scr_view, <scr_status, <scr_inventory, <scr_help, <scr_notyet
screen_hi:
        .byte   >scr_topo, >scr_view, >scr_status, >scr_inventory, >scr_help, >scr_notyet
.segment "GDATA"
verbs:  .byte   V_WEAR, V_DROP, V_GET, V_CARRY, V_PACK, V_DRINK, V_EAT, V_LOOK, V_PAN
        .byte   V_WAIT, V_REST, V_CAMP, V_EXER, V_WALK, V_RUN, V_MOVE, V_CRAWL, V_SWIM, V_ENTER, V_EXIT, V_USE, 26, V_CLIMB, V_HANG, V_LOWER, 30, 32, 0
verb_lo:
        .byte   <do_wear, <do_drop, <do_get, <do_get, <do_get, <do_drink, <do_eat, <do_look, <do_look
        .byte   <do_rest, <do_rest, <do_rest, <do_rest, <do_walk, <do_walk, <do_walk, <do_walk, <do_walk
        .byte   <do_site, <do_site, <do_medical, <do_medical, <do_tree, <do_tree, <do_medical, <do_medical, <do_medical
verb_hi:
        .byte   >do_wear, >do_drop, >do_get, >do_get, >do_get, >do_drink, >do_eat, >do_look, >do_look
        .byte   >do_rest, >do_rest, >do_rest, >do_rest, >do_walk, >do_walk, >do_walk, >do_walk, >do_walk
        .byte   >do_site, >do_site, >do_medical, >do_medical, >do_tree, >do_tree, >do_medical, >do_medical, >do_medical
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
        .include "project.s"
        .include "tree.s"
.segment "CODE"
