; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hof.s -- wildhof.bin, the end-of-game module (lot 7, step 6; ID 24)
; ============================================================================
; Runs once per journey, after the ending screen, before the game returns to
; the menu. It is not resident: module_end (src/hof_load.inc, in INPUT) reads
; the file NEOWILD.END from the disk into the SIM window at $9600 (the
; simulation is over) and jumps to its first byte. The module then
;   1. gathers the result from the resident state: won / dead (outcome),
;      MAP+22 level, region_number (written by the region pack), journey_kind
;      (written by the loader), goal_pct (STATUS "DONE=", 0-100), health % =
;      round(H / Hmax * 100), hours = INT(s_elap). Not MAP+32 / MAP+33: the
;      wild food scan of TRAVEL and ADVENTURE stores its quantities in
;      MAP+28..MAP+33 once the player walks;
;   2. computes the score (16 bits, tools/score_ref.py is the oracle):
;      base = progress * 10 + 1000 (arrived) + health * 5 (arrived; else
;             health * 5 * progress / 100) + max(0, 720 - hours) (arrived);
;      score = base * (10 + level) / 14, every division rounded down
;   3. clears the 40-column text page 1 and shows the breakdown;
;   4. free journey (journey_kind = 1) or region outside 1-6: "NOT RANKED", no disk
;      access. Otherwise reads NEOWILD.HOF into $5800 (hm_load), counts the
;      journey, finds the rank (score descending, then hours ascending; the
;      new result goes after equal ones; a score of 0 is never ranked) and, in the top 5, inserts a blank
;      entry and edits its name in place (8 characters A-Z 0-9 space . -,
;      left arrow / DELETE erase, RETURN keeps, ESC removes the entry);
;      writes the file back (hm_save) and reports SAVED, WRITE-PROTECTED or
;      DISK ERROR $xx. A read error shows its code and writes nothing;
;   5. "PRESS A KEY FOR THE MENU.", one key, then INPUT again and
;      module_restart (NEOWILD.SYSTEM, the menu).
; The score stays on screen in every case. Memory: code at $9600 (SIM
; window), the file in $5800-$59FF (module window: goal_pct leaves ADVENTURE
; there, which is no longer needed; $5A00-$5A9F: pathname and the saved
; entries), text page 1, zero page gp1/gp2.
;
; Game build: wild.s includes this file after game.s (it uses gp1, MAP, the
; ROM float equates and the game labels directly); wild.cfg gives the HOF
; segment a memory area at $9600 written to build/wildhof.bin.
; Bench build (hof.mk): assembled alone with -D HOF_BENCH; the game labels
; are imported from src/hof_test.s and the exit returns to the bench.
; ============================================================================

.ifdef HOF_BENCH
        .include "apple2.inc"
.import won, dead, s_elap, s_health, f_hmax, region_name, geo_path
.import region_number, journey_kind
.import mli_call, goal_pct, overlay_load, module_restart, bench_next, io_buffer
MAP     = $7000
MOVFM   = $EAF9                 ; FAC <- (A,Y)
FADD    = $E7BE                 ; FAC <- (A,Y) + FAC
FMULT   = $E97F                 ; FAC <- (A,Y) * FAC
FDIV    = $EA66                 ; FAC <- (A,Y) / FAC
AYINT   = $E10C                 ; FAC -> signed int, $A0 (hi) $A1 (lo)
FAC     = $9D
HOF_ZP  = $D0
.endif
.ifndef HOF_ZP
HOF_ZP  = gp1                   ; gp1, gp2: free once the journey is over
.endif
HOF_BUF   = $5800
HOF_PATHBUF = $5A00             ; 65 bytes, module window
hof_saved = $5A50               ; 80 bytes: the scenario's entries before
                                ; the insertion (ESC puts them back)
HOF_MLI   = mli_call
HOF_IOBUF = io_buffer
HOF_PATH  = geo_path
HOF_LCROM = $C082
HOF_BELL  = $FBDD               ; Monitor BELL1: speaker only, no COUT
HOF_INPUT = 13                  ; module that holds module_restart

.segment "HOF"
hof_main:
        cld
        bit     KBDSTRB         ; drop a key left by the ending screen
        jsr     hof_gather
        jsr     hof_score
        sta     TXTSET          ; 40-column text page 1, primary characters
        sta     LOWSCR
        sta     COL80OFF
.ifndef HOF_BENCH
        XL_IMM  XI_END, $0F, @x42     ; (XL, docs/MENUS.md 9: ALTCHARSET stays on)
.endif
        sta     $C00E           ; ALTCHAROFF
        bit     DHIRES_OFF
        jsr     hm_clear
        jsr     hof_breakdown
        lda     hof_kind
        bne     @free
        lda     hof_region
        beq     @free
        cmp     #7
        bcs     @free
        jsr     hm_load
        bcc     @loaded
        pha
        lda     #21
        jsr     hm_clear_row
        pla
        jsr     hm_unreadable
        jmp     @key
@free:  lda     #<hof_m_free
        ldy     #>hof_m_free
        jsr     hof_message21
        jmp     @key
@loaded:
        jsr     hof_count
        jsr     hof_find_rank
        lda     hof_rank
        cmp     #HM_RANKS
        bcc     @record
        jsr     hof_table
        lda     #<hof_m_not_top
        ldy     #>hof_m_not_top
        jsr     hof_message21
        jmp     @save
@record:
        jsr     hof_insert
        jsr     hof_table
        jsr     hof_rank_message
        lda     #22
        jsr     hm_clear_row
        lda     #<hof_m_help
        ldy     #>hof_m_help
        jsr     hm_print
        jsr     hof_name
        bcc     @named
        jsr     hof_restore     ; ESC: the table as it was read
        jsr     hof_table
        lda     #<hof_m_skipped
        ldy     #>hof_m_skipped
        jsr     hof_message21
        jmp     @save
@named: jsr     hof_table
@save:  jsr     hm_save
        php
        pha
        lda     #22
        jsr     hm_clear_row
        pla
        plp
        bcc     @saved
        cmp     #$2B
        bne     @error
        lda     #<hof_m_protected
        ldy     #>hof_m_protected
        jsr     hm_print
        jmp     @key
@error: pha
        lda     #<hof_m_disk
        ldy     #>hof_m_disk
        jsr     hm_print
        pla
        jsr     hm_hex
        lda     #<hof_m_not_saved
        ldy     #>hof_m_not_saved
        jsr     hm_print
        jmp     @key
@saved: lda     #<hof_m_saved
        ldy     #>hof_m_saved
        jsr     hm_print
@key:   lda     #23
        jsr     hm_clear_row
        lda     #<hm_m_key
        ldy     #>hm_m_key
        jsr     hm_print
        jsr     hof_key
hof_exit:
        lda     #HOF_INPUT      ; INPUT back in $5800, then the menu
        jsr     overlay_load
.ifdef HOF_BENCH
        jmp     bench_next
.else
        jmp     module_restart
.endif

; ----------------------------------------------------------------------------
; hof_gather -- the result, from the resident state.
hof_gather:
        bit     HOF_LCROM       ; Applesoft ROM for the float routines
        lda     #1              ; outcome: 1 arrived, 2 died, 3 abandoned
        ldx     won
        bne     :+
        lda     #2
        ldx     dead
        bne     :+
        lda     #3
:       sta     hof_outcome
        lda     MAP+22
        sta     hof_level
        lda     region_number   ; not MAP+32 / MAP+33 (wild food quantities)
        sta     hof_region
        lda     journey_kind
        sta     hof_kind
        jsr     goal_pct        ; DONE% 0..100 (loads ADVENTURE)
        sta     hof_progress
        lda     #<f_hmax        ; health % = round(H / Hmax * 100)
        ldy     #>f_hmax
        jsr     MOVFM
        lda     #<s_health
        ldy     #>s_health
        jsr     FDIV
        lda     #<hof_f100
        ldy     #>hof_f100
        jsr     FMULT
        lda     #<hof_fhalf
        ldy     #>hof_fhalf
        jsr     FADD
        jsr     AYINT
        lda     $A1
        ldx     $A0
        beq     :+
        lda     #0              ; negative: 0
        cpx     #$80
        bcs     :+
        lda     #255            ; 256 or more: clamped by hof_score
:       sta     hof_health
        lda     #<s_elap        ; hours = INT(s_elap), at most 32767
        ldy     #>s_elap
        jsr     MOVFM
        lda     FAC
        cmp     #$90            ; exponent: 2^15 or more
        bcc     :+
        lda     #$FF
        sta     hof_hours
        lda     #$7F
        sta     hof_hours+1
        rts
:       jsr     AYINT
        lda     $A1
        sta     hof_hours
        lda     $A0
        sta     hof_hours+1
        rts

; hof_score -- clamp the inputs, then the components and the score.
hof_score:
        lda     hof_progress
        cmp     #101
        bcc     :+
        lda     #100
:       sta     hof_progress
        lda     hof_health
        cmp     #101
        bcc     :+
        lda     #100
:       sta     hof_health
        lda     hof_level
        bne     :+
        lda     #1
:       cmp     #11
        bcc     :+
        lda     #10
:       sta     hof_level
        clc
        adc     #10
        sta     hof_mult
        lda     hof_progress    ; P = progress * 10 = (p * 4 + p) * 2
        ldx     #0
        jsr     hof_times5
        asl     a
        sta     hof_p
        txa
        rol     a
        sta     hof_p+1
        lda     hof_health      ; H = health * 5 (* progress / 100 when
        ldx     #0              ; the journey did not arrive)
        jsr     hof_times5
        sta     hof_h
        stx     hof_h+1
        lda     hof_outcome
        cmp     #1
        beq     :+
        lda     hof_h
        ldy     hof_h+1
        ldx     hof_progress
        jsr     hof_mul
        lda     #100
        jsr     hof_div
        lda     hof_q
        sta     hof_h
        lda     hof_q+1
        sta     hof_h+1
:
        lda     #0
        sta     hof_a
        sta     hof_a+1
        sta     hof_s
        sta     hof_s+1
        lda     hof_outcome
        cmp     #1
        bne     @sum
        lda     #<1000
        sta     hof_a
        lda     #>1000
        sta     hof_a+1
        sec                     ; S = 720 - hours, if positive
        lda     #<720
        sbc     hof_hours
        tax
        lda     #>720
        sbc     hof_hours+1
        bcc     @sum
        stx     hof_s
        sta     hof_s+1
@sum:   clc
        lda     hof_p
        adc     hof_a
        sta     hof_base
        lda     hof_p+1
        adc     hof_a+1
        sta     hof_base+1
        clc
        lda     hof_base
        adc     hof_h
        sta     hof_base
        lda     hof_base+1
        adc     hof_h+1
        sta     hof_base+1
        clc
        lda     hof_base
        adc     hof_s
        sta     hof_base
        lda     hof_base+1
        adc     hof_s+1
        sta     hof_base+1
        lda     hof_base        ; score = base * mult / 14
        ldy     hof_base+1
        ldx     hof_mult
        jsr     hof_mul
        lda     #14
        jsr     hof_div
        lda     hof_q
        sta     hof_total
        lda     hof_q+1
        sta     hof_total+1
        rts

; hof_mul -- hof_q = (A lo, Y hi) * X, by additions (X <= 100).
hof_mul:
        sta     hof_m
        sty     hof_m+1
        lda     #0
        sta     hof_q
        sta     hof_q+1
        cpx     #0
        beq     @done
@add:   clc
        lda     hof_q
        adc     hof_m
        sta     hof_q
        lda     hof_q+1
        adc     hof_m+1
        sta     hof_q+1
        dex
        bne     @add
@done:  rts

; hof_div -- hof_q = hof_q / A (2 <= A < 128), remainder dropped.
hof_div:
        sta     hof_m
        lda     #0
        ldx     #16
@bit:   asl     hof_q
        rol     hof_q+1
        rol     a
        cmp     hof_m
        bcc     @next
        sbc     hof_m
        inc     hof_q
@next:  dex
        bne     @bit
        rts

; hof_times5 -- A = value < 256 -> A (lo) / X (hi) = 5 * value.
hof_times5:
        sta     hof_t5
        stx     hof_t5+1
        asl     a
        rol     hof_t5+1
        asl     a
        rol     hof_t5+1
        clc
        adc     hof_t5
        tay
        lda     hof_t5+1
        adc     #0
        tax
        tya
        rts

; ----------------------------------------------------------------------------
; Rows 0..12: the breakdown (score_ref.breakdown).
VALUE_COL = 28

hof_breakdown:
        lda     #<hof_m_title
        ldy     #>hof_m_title
        ldx     #13
        jsr     hm_title
        lda     #2              ; "REGION, LEVEL n (FREE)"
        ldy     #0
.ifndef HOF_BENCH
        XL_ABS  XI_END, hx_title_at, @x67       ; (XL: the post-it's title)
.endif
        jsr     hm_at
        ldx     #0
:       lda     region_name,x
        beq     :+
        jsr     hm_char
        inx
        cpx     #16
        bne     :-
:       lda     #<hof_m_level
        ldy     #>hof_m_level
        jsr     hm_print
        lda     hof_level
        jsr     hof_byte0
        lda     hof_kind
        beq     :+
        lda     #<hof_m_free_tag
        ldy     #>hof_m_free_tag
        jsr     hm_print
:       lda     #3              ; "ARRIVED AFTER n HOURS"
.ifndef HOF_BENCH
        XL_IMM  XI_END, 1, @x68                 ; (XL: right of the post-it's bar)
.endif
        ldy     #0
.ifndef HOF_BENCH
        XL_ABS  XI_END, hx_title_end, @x69
.endif
        jsr     hm_at
        ldx     hof_outcome
        jsr     hof_outcome_word
        lda     #<hof_m_after
        ldy     #>hof_m_after
        jsr     hm_print
        jsr     hof_print_hours
        lda     #<hof_m_hours
        ldy     #>hof_m_hours
        jsr     hm_print
        ldx     #5              ; PROGRESS
        lda     #<hof_m_progress
        ldy     #>hof_m_progress
        jsr     hof_line
        lda     hof_progress
        ldx     #0
        ldy     #3
        jsr     hm_num
        lda     #<hof_m_x10
        ldy     #>hof_m_x10
        jsr     hm_print
        ldx     #hof_p-hof_values
        lda     #5
        jsr     hof_value
        ldx     #6              ; ARRIVAL
        lda     #<hof_m_arrival
        ldy     #>hof_m_arrival
        jsr     hof_line
        jsr     hof_yes_no
        ldx     #hof_a-hof_values
        lda     #6
        jsr     hof_value
        ldx     #7              ; HEALTH
        lda     #<hof_m_health
        ldy     #>hof_m_health
        jsr     hof_line
        lda     hof_health
        ldx     #0
        ldy     #3
        jsr     hm_num
        lda     #<hof_m_x5
        ldy     #>hof_m_x5
        jsr     hm_print
        lda     hof_outcome
        cmp     #1
        beq     :+
        lda     #<hof_m_times   ; " X progress%"
        ldy     #>hof_m_times
        jsr     hm_print
        lda     hof_progress
        jsr     hof_byte0
        lda     #'%'
        jsr     hm_char
:       ldx     #hof_h-hof_values
        lda     #7
        jsr     hof_value
        ldx     #8              ; SPEED
        lda     #<hof_m_speed
        ldy     #>hof_m_speed
        jsr     hof_line
        lda     hof_outcome
        cmp     #1
        bne     :+
        lda     #<hof_m_720
        ldy     #>hof_m_720
        jsr     hm_print
        jsr     hof_print_hours
        jmp     :++
:       lda     #<hof_m_no
        ldy     #>hof_m_no
        jsr     hm_print
:       ldx     #hof_s-hof_values
        lda     #8
        jsr     hof_value
        lda     #9
        ldy     #VALUE_COL
        jsr     hm_at
        lda     #<hof_m_dashes
        ldy     #>hof_m_dashes
.ifndef HOF_BENCH
        XL_ABS  XI_END, hm_line_x, @x61         ; (XL: a MouseText line)
.endif
        jsr     hm_print
        ldx     #10             ; TOTAL
        lda     #<hof_m_total
        ldy     #>hof_m_total
        jsr     hof_line
        ldx     #hof_base-hof_values
        lda     #10
        jsr     hof_value
        ldx     #11             ; LEVEL n X m/14
        lda     #<hof_m_level_row
        ldy     #>hof_m_level_row
        jsr     hof_line
        lda     hof_level
        ldx     #0
        ldy     #3
        jsr     hm_num
        lda     #<hof_m_times
        ldy     #>hof_m_times
        jsr     hm_print
        lda     hof_mult
        jsr     hof_byte0
        lda     #<hof_m_14
        ldy     #>hof_m_14
        jsr     hm_print
        ldx     #hof_total-hof_values
        lda     #11
        jsr     hof_value
        ldx     #12             ; SCORE, value in inverse
        lda     #<hof_m_score
        ldy     #>hof_m_score
        jsr     hof_line
        lda     #$80
        sta     hm_inverse
        ldx     #hof_total-hof_values
        lda     #12
        jsr     hof_value
        lda     #0
        sta     hm_inverse
        rts

; hof_line -- X = row: A/Y = text at column 0.
hof_line:
        pha
        tya
        pha
        txa
.ifndef HOF_BENCH
        XL_IMM  XI_END, 1, @x70                 ; (XL: right of the post-it's bar)
.endif
        ldy     #0
        jsr     hm_at
        pla
        tay
        pla
        jmp     hm_print

; hof_value -- A = row, X = offset of a u16 in hof_values: five digits at
; VALUE_COL.
hof_value:
        stx     hof_t5
        ldy     #VALUE_COL
        jsr     hm_at
        ldy     hof_t5
        lda     hof_values,y
        ldx     hof_values+1,y
        ldy     #5
        jmp     hm_num

hof_byte0:
        ldx     #0
        ldy     #0
        jmp     hm_num

hof_print_hours:
        lda     hof_hours
        ldx     hof_hours+1
        ldy     #0
        jmp     hm_num

hof_yes_no:
        lda     hof_outcome
        cmp     #1
        bne     :+
        lda     #<hof_m_yes
        ldy     #>hof_m_yes
        jmp     hm_print
:       lda     #<hof_m_no
        ldy     #>hof_m_no
        jmp     hm_print

; hof_outcome_word -- X = outcome 1..3 (else "?").
hof_outcome_word:
        dex
        cpx     #3
        bcc     :+
        lda     #'?'
        jmp     hm_char
:       lda     hof_words_lo,x
        ldy     hof_words_hi,x
        jmp     hm_print

; hof_message21 -- A/Y = text on a cleared row 21.
hof_message21:
        pha
        tya
        pha
        lda     #21
        jsr     hm_clear_row
        pla
        tay
        pla
        jmp     hm_print

hof_rank_message:
        lda     #21
        jsr     hm_clear_row
        lda     #<hof_m_rank
        ldy     #>hof_m_rank
        jsr     hm_print
        lda     hof_rank
        clc
        adc     #'1'
        jsr     hm_char
        lda     #<hof_m_type
        ldy     #>hof_m_type
        jmp     hm_print

; ----------------------------------------------------------------------------
; hof_table -- rows 14..19: "REGION - TOP 5", then the five entries
; (score_ref.table_line).
hof_table:
        lda     #14
.ifndef HOF_BENCH
        XL_ABS  XI_END, hof_top_x, @x62         ; (XL: the table in a box)
.endif
        jsr     hm_clear_row
        ldx     #0
:       lda     region_name,x
        beq     :+
        jsr     hm_char
        inx
        cpx     #16
        bne     :-
:       lda     #<hof_m_top
        ldy     #>hof_m_top
.ifndef HOF_BENCH
        XL_ABS  XI_END, hof_title_x, @x63
.endif
        jsr     hm_print
        lda     #0
        sta     hof_k
@line:  lda     hof_k
        clc
        adc     #15
.ifndef HOF_BENCH
        XL_ABS  XI_END, hof_row_x, @x64
.endif
        jsr     hm_clear_row
        lda     hof_region
        ldx     hof_k
        jsr     hm_entry
        ldx     hof_k
        jsr     hm_rank_head
        bcs     @next
        lda     #' '
        jsr     hm_char
        ldy     #HM_E_HOURS+1
        lda     (hm_ent),y
        tax
        dey
        lda     (hm_ent),y
        ldy     #5
        jsr     hm_num
        lda     #'H'
        jsr     hm_char
        lda     #' '
        jsr     hm_char
        lda     #'L'
        jsr     hm_char
        ldy     #HM_E_LEVEL
        lda     (hm_ent),y
        pha
        jsr     hof_byte0
        pla
        cmp     #10
        bcs     :+
        lda     #' '
        jsr     hm_char
:       lda     #' '
        jsr     hm_char
        ldy     #HM_E_OUTCOME
        lda     (hm_ent),y
        tax
        jsr     hof_outcome_word
@next:  inc     hof_k
        lda     hof_k
        cmp     #HM_RANKS
        bne     @line
        rts

; ----------------------------------------------------------------------------
; hof_count -- the total and the scenario's journey counters, saturating.
hof_count:
        ldx     #2
        jsr     @inc
        lda     hof_region
        asl     a
        adc     #2              ; 4 + 2 * (region - 1)
        tax
@inc:   inc     HOF_BUF,x
        bne     :+
        inc     HOF_BUF+1,x
        bne     :+
        dec     HOF_BUF,x       ; 65535 stays
        dec     HOF_BUF+1,x
:       rts

; hof_find_rank -- hof_rank = first entry the result beats (5: none).
hof_find_rank:
        lda     #HM_RANKS       ; a score of 0 is never ranked
        sta     hof_rank
        lda     hof_total
        ora     hof_total+1
        beq     @found
        lda     #0
        sta     hof_rank
@entry: lda     hof_region
        ldx     hof_rank
        jsr     hm_entry
        ldy     #HM_E_OUTCOME
        lda     (hm_ent),y
        beq     @found          ; an empty entry
        ldy     #HM_E_SCORE+1
        lda     hof_total+1
        cmp     (hm_ent),y
        bne     @score
        dey
        lda     hof_total
        cmp     (hm_ent),y
        bne     @score
        ldy     #HM_E_HOURS+1   ; equal scores: fewer hours first
        lda     (hm_ent),y
        cmp     hof_hours+1
        bne     @hours
        dey
        lda     (hm_ent),y
        cmp     hof_hours
        beq     @next           ; same score and hours: after the old one
@hours: bcs     @found          ; entry hours > ours
        bcc     @next
@score: bcs     @found          ; our score > entry
@next:  inc     hof_rank
        lda     hof_rank
        cmp     #HM_RANKS
        bne     @entry
@found: rts

; hof_insert -- save the scenario's 80 bytes, then rebuild them with a
; blank-named entry at hof_rank (the fifth entry drops out).
hof_insert:
        lda     hof_rank
        asl     a
        asl     a
        asl     a
        asl     a
        sta     hof_rank_offset
        ora     #8
        sta     hof_name_end
        lda     hof_region
        ldx     #0
        jsr     hm_entry
        ldy     #HM_BLOCK-1
:       lda     (hm_ent),y
        sta     hof_saved,y
        dey
        bpl     :-
        ldx     #0              ; X: source offset in hof_saved
        ldy     #0              ; Y: destination offset
@entry: cpy     hof_rank_offset
        bne     @copy
        lda     #' '|$80        ; the new entry
:       sta     (hm_ent),y
        iny
        cpy     hof_name_end
        bne     :-
        lda     hof_total
        sta     (hm_ent),y
        iny
        lda     hof_total+1
        sta     (hm_ent),y
        iny
        lda     hof_hours
        sta     (hm_ent),y
        iny
        lda     hof_hours+1
        sta     (hm_ent),y
        iny
        lda     hof_level
        sta     (hm_ent),y
        iny
        lda     hof_outcome
        sta     (hm_ent),y
        iny
        lda     #0
        sta     (hm_ent),y
        iny
        sta     (hm_ent),y
        iny
        jmp     @more
@copy:  lda     #HM_ESIZE
        sta     hof_k
:       lda     hof_saved,x
        sta     (hm_ent),y
        inx
        iny
        dec     hof_k
        bne     :-
@more:  cpy     #HM_BLOCK
        bne     @entry
        rts

hof_restore:
        lda     hof_region
        ldx     #0
        jsr     hm_entry
        ldy     #HM_BLOCK-1
:       lda     hof_saved,y
        sta     (hm_ent),y
        dey
        bpl     :-
        rts

; ----------------------------------------------------------------------------
; hof_name -- edit the name of the new entry on its table row. C clear:
; RETURN with at least one character; C set: ESC.
hof_name:
        lda     #0
        sta     hof_len
        lda     #38
        sta     hof_wheel
@draw:  lda     hof_region
        ldx     hof_rank
        jsr     hm_entry
        lda     hof_rank
        clc
        adc     #15
        sta     hof_k
.ifndef HOF_BENCH
        XL_IMM  XI_END, 3, @x65                 ; (XL: right of the box's bar)
.endif
        ldy     #2
        jsr     hm_at
        lda     #0
        sta     hof_t5
:       ldy     hof_t5          ; the eight name characters
        lda     (hm_ent),y
        and     #$7F
        jsr     hm_char
        inc     hof_t5
        lda     hof_t5
        cmp     #8
        bne     :-
        lda     hof_len         ; the cursor: an inverse space
        cmp     #8
        bcs     @key
        clc
        lda     hof_len
.ifndef HOF_BENCH
        XL_IMM  XI_END, 3, @x66
.endif
        adc     #2
        tay
        lda     hof_k
        jsr     hm_at
        lda     #$80
        sta     hm_inverse
        lda     #' '
        jsr     hm_char
        lda     #0
        sta     hm_inverse
@key:   jsr     hof_key
        cmp     #KC_UP
        jeq     @wheel_up
        cmp     #KC_DOWN
        jeq     @wheel_down
        cmp     #KC_RIGHT
        jeq     @wheel_next
        cmp     #KC_RET
        bne     @esc
        lda     hof_len
        beq     @bad
        clc
        rts
@esc:   cmp     #KC_ESC
        bne     @erase
        sec
        rts
@erase: cmp     #KC_LEFT
        beq     :+
        cmp     #$7F            ; DELETE
        bne     @char
:       ldy     hof_len
        beq     @bad
        dey
        sty     hof_len
        lda     #' '|$80
        sta     (hm_ent),y
        jmp     @draw
@char:  ldy     hof_len
        cpy     #8
        bcs     @bad
        cmp     #' '
        bne     :+
        cpy     #0              ; no leading space
        beq     @bad
        bne     @take
:       cmp     #'.'
        beq     @take
        cmp     #'-'
        beq     @take
        cmp     #'0'
        bcc     @bad
        cmp     #'9'+1
        bcc     @take
        cmp     #'A'
        bcc     @bad
        cmp     #'Z'+1
        bcs     @bad
@take:  ora     #$80
        sta     (hm_ent),y
        inc     hof_len
        jmp     @draw
@bad:   jsr     HOF_BELL
        jmp     @key

@wheel_up:
        inc     hof_wheel
        lda     hof_wheel
        cmp     #39
        bcc     @wheel_put
        lda     #0
        beq     @wheel_put
@wheel_down:
        dec     hof_wheel
        lda     hof_wheel
        bpl     @wheel_put
        lda     #38
@wheel_put:
        sta     hof_wheel
        tax
        lda     hof_letters,x
        ora     #$80
        ldy     hof_len
        bne     :+
        inc     hof_len
        iny
:       dey
        sta     (hm_ent),y
        jmp     @draw
@wheel_next:
        lda     #0
        sta     hof_wheel
        lda     #'A'
        jmp     @char
hof_wheel: .byte 38
hof_letters: .byte "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-"

; hof_key -- wait for a key: A = ASCII, letters in upper case. Tests stop
; at hof_key_wait (tests/test_hof.py).
hof_key:
hof_key_wait:
.ifndef HOF_BENCH
        jsr     ui_poll
        beq     hof_key_wait
.else
        lda     KBD
        bpl     hof_key_wait
        bit     KBDSTRB
        and     #$7F
.endif
        cmp     #'a'
        bcc     :+
        cmp     #'z'+1
        bcs     :+
        and     #$DF
:       rts

; ----------------------------------------------------------------------------
; The scenarios of the edition (6 or 1), written by tools/build_disk.py.
hm_regions: .byte 6
.export hm_regions
        .include "hof_menu.s"

hof_f100:  .byte $87, $48, 0, 0, 0      ; 100
hof_fhalf: .byte $80, 0, 0, 0, 0        ; 0.5
hof_words_lo: .byte <hof_m_arrived, <hof_m_died, <hof_m_abandoned
hof_words_hi: .byte >hof_m_arrived, >hof_m_died, >hof_m_abandoned
hof_name_end:    .byte 0                ; patched: rank offset + 8
hof_rank_offset: .byte 0                ; patched: rank * 16

hof_m_title:     .byte "JOURNEY SCORE", 0
hof_m_level:     .byte ", LEVEL ", 0
hof_m_free_tag:  .byte " (FREE)", 0
hof_m_after:     .byte " AFTER ", 0
hof_m_hours:     .byte " HOURS", 0
hof_m_arrived:   .byte "ARRIVED", 0
hof_m_died:      .byte "DIED", 0
hof_m_abandoned: .byte "ABANDONED", 0
hof_m_progress:  .byte "PROGRESS  ", 0
hof_m_x10:       .byte "% X 10", 0
hof_m_arrival:   .byte "ARRIVAL   ", 0
hof_m_health:    .byte "HEALTH    ", 0
hof_m_x5:        .byte "% X 5", 0
hof_m_speed:     .byte "SPEED     ", 0
hof_m_720:       .byte "720 - ", 0
hof_m_yes:       .byte "YES", 0
hof_m_no:        .byte "NO", 0
hof_m_dashes:    .byte "-----", 0
hof_m_total:     .byte "TOTAL", 0
hof_m_level_row: .byte "LEVEL     ", 0
hof_m_times:     .byte " X ", 0
hof_m_14:        .byte "/14", 0
hof_m_score:     .byte "POINTS", 0
hof_m_top:       .byte " - TOP 5", 0
hof_m_free:      .byte "FREE JOURNEY: NOT RANKED.", 0
hof_m_not_top:   .byte "NOT IN THE TOP 5.", 0
hof_m_skipped:   .byte "NOT RECORDED.", 0
hof_m_rank:      .byte "NEW RECORD: RANK ", 0
hof_m_type:      .byte ". TYPE YOUR NAME.", 0
hof_m_help:      .byte "UP/DN LETTER > NEXT RET SAVE ESC SKIP", 0
hof_m_saved:     .byte "HALL OF FAME SAVED.", 0
hof_m_protected: .byte "DISK WRITE-PROTECTED: NOT SAVED.", 0
hof_m_disk:      .byte "DISK ERROR $", 0
hof_m_not_saved: .byte ": NOT SAVED.", 0

; State: inputs, then the components (read by tests/test_hof.py).
hof_outcome:  .byte 0
hof_level:    .byte 0
hof_region:   .byte 0
hof_kind:     .byte 0
hof_progress: .byte 0
hof_health:   .byte 0
hof_hours:    .word 0
hof_mult:     .byte 0
hof_rank:     .byte 0
hof_values:
hof_p:        .word 0
hof_a:        .word 0
hof_h:        .word 0
hof_s:        .word 0
hof_base:     .word 0
hof_total:    .word 0           ; the score
hof_t5:       .word 0
hof_m:        .word 0
hof_q:        .word 0
hof_k:        .byte 0
hof_len:      .byte 0
hof_end:

.ifndef HOF_BENCH
; ----------------------------------------------------------------------------
; NeoWildernessXL only (docs/MENUS.md 9): the tail of NEOWILD.END (segment
; ENDX, build/wildendx.bin, appended by tools/build_disk.py to XL's copy):
; the title band a double line ($5C), the total's line MouseText ($53), the
; table of the scenario in a box (its title in inverse, then '_'; the five
; rows between the bars $5F and $5A, their text from column 1; the bottom
; line $4C on row 20).
.segment "ENDX"
endx_base:
; hm_dline_x -- (hm_title's 40 spaces) the double line across row 0.
hm_dline_x:
        lda     #MT_DLINE
        bne     hx_fill
; hm_line_x -- (the dashes of the total) A/Y = the dashes: as many cells of
; the line $53.
hm_line_x:
        sta     @src+1
        sty     @src+2
        ldy     #0
@src:   lda     $FFFF,y
        beq     :+
        iny
        bne     @src
:       tya
        tax
        lda     #MT_LINE
; hx_fill -- X cells of A from hm_col.
hx_fill:
        ldy     hm_col
:       sta     (hm_ptr),y
        iny
        dex
        bne     :-
        sty     hm_col
        rts
; hx_title_at -- (row 2, column 0) the breakdown's post-it: its title, the
; region and level, in inverse after a space.
hx_title_at:
        jsr     hm_at
        lda     #$80
        sta     hm_inverse
        lda     #' '
        jmp     hm_char
; hx_title_end -- (row 3's hm_at, A/Y kept) the title's last space, then
; '_' to column 39.
hx_title_end:
        pha
        tya
        pha
        jsr     hx_title_fill
        pla
        tay
        pla
        jmp     hm_at
; hx_box -- (hof_top_x) the breakdown's post-it: its bars on rows 3-12, its
; last row the line $4C on row 13.
hx_box: lda     #12
@row:   pha
        ldy     #0
        jsr     hm_at
        lda     #MT_LBAR
        sta     (hm_ptr),y
        ldy     #39
        lda     #MT_RBAR
        sta     (hm_ptr),y
        pla
        sec
        sbc     #1
        cmp     #3
        bcs     @row
        lda     #13
        ldy     #0
        jsr     hm_at
        ldx     #40
        lda     #MT_TOP
        jmp     hx_fill
; hof_top_x -- (row 14 cleared) the box's title starts: in inverse, a space.
hof_top_x:
        jsr     hx_box
        lda     #14
        jsr     hm_clear_row
        lda     #$80
        sta     hm_inverse
        lda     #' '
        jmp     hm_char
; hof_title_x -- (" - TOP 5") the title's end, a space, then '_' to column 39.
hof_title_x:
        jsr     hm_print
hx_title_fill:
        lda     #' '
        jsr     hm_char
        lda     #0
        sta     hm_inverse
        lda     #40
        sec
        sbc     hm_col
        tax
        lda     #MT_BOTTOM
        bne     hx_fill
; hof_row_x -- A = row 15 + k cleared, its bars, the cursor at column 1; on
; the last row, row 20 the bottom line.
hof_row_x:
        pha
        jsr     hm_clear_row
        ldy     #0
        lda     #MT_LBAR
        sta     (hm_ptr),y
        ldy     #39
        lda     #MT_RBAR
        sta     (hm_ptr),y
        pla
        cmp     #19
        bcc     @col
        lda     #20
        ldy     #0
        jsr     hm_at
        ldx     #40
        lda     #MT_TOP
        jsr     hx_fill
        lda     #19
        ldy     #1
        jmp     hm_at
@col:   lda     #1
        sta     hm_col
        rts
endx_end:
.segment "HOF"
.endif
