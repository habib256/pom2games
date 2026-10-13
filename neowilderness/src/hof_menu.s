; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hof_menu.s -- NEOWILD.HOF access and text drawing (lot 7, step 6)
; ============================================================================
; An includable fragment, shared by two programs:
;   - the loader NEOWILD.SYSTEM (src/boot.s), with HOF_LOADER defined: reads
;     the file once before the menu, writes "BEST nnnnn" over the menu's
;     "BEST -" placeholders and draws the H screen;
;   - the end-of-game module wildhof.bin (src/hof.s), without HOF_LOADER:
;     reads and writes the file, shares the text primitives.
; It declares no segment and exports nothing: its code goes in the segment
; that is current at the .include, and every name starts with hm_ / HM_.
; Code and variables are mixed (self-modified operands): the segment must be
; writable RAM, as LOADER and the module windows are.
;
; Configuration, defined before the .include:
;   HOF_ZP     4 free zero-page bytes: hm_ptr (screen row), hm_ent (entry)
;   HOF_BUF    512-byte buffer holding the file (loader: STAGE = $2000;
;              module: $5800, the module window, free at the end of a game)
;   HOF_MLI    MLI entry: A = command, X/Y = parameters, returns C and A
;              (loader: ld_mli, module: mli_call)
;   HOF_IOBUF  ProDOS 1 KB I/O buffer for OPEN (io_buffer = $BA00)
;   HOF_PATH   length-prefixed "/VOLUME/NEOWILD.GEO" (geo_path, RESBSS):
;              the last three characters are replaced by HOF
;   HOF_PATHBUF optional: 65 bytes of free RAM for the pathname (default:
;              a .res in the including segment)
;   HOF_READ_PARMS  optional: an 8-byte READ/WRITE parameter block to use
;              instead of the fragment's own (the loader passes `read`, whose
;              transfer count ld_mli adds to mli_bytes)
;   HOF_LOADER defined: assemble hm_best and hm_hall (they need
;              HOF_NAMES_LO / HOF_NAMES_HI: six pointers to ASCIIZ names);
;              not defined: assemble hm_save
;
; Entry points (all preserve nothing but the stack; D = 0, text page 1 main):
;   hm_load    OPEN, READ 512, CLOSE into HOF_BUF; checks 512 bytes, 'H' and
;              version 1. C clear: valid. C set: A = MLI error, or
;              HM_INVALID ($01) for a short or unknown file; the buffer then
;              holds an empty table. hm_status keeps A (0 when valid).
;   hm_save    OPEN, WRITE 512 from HOF_BUF, CLOSE. C set: A = first MLI
;              error ($2B: write-protected); a failed CLOSE is retried with
;              reference 0 so no file stays open.
;   hm_best    (loader) "BEST nnnnn" at columns 29-38 of rows 2, 5 ... 17 for
;              each scenario whose first entry is used; others keep "BEST -".
;   hm_hall    (loader) clears the screen and draws the six tables (two
;              columns of three blocks), the journey count or the read
;              error, and "PRESS A KEY FOR THE MENU." The caller waits.
;   hm_clear   clear page 1 (normal spaces).
;   hm_at      A = row, Y = column.   hm_char  A = ASCII $20-$5F at the cursor.
;   hm_print   A/Y = ASCIIZ.          hm_num   A/X = u16, Y = width 1-5
;              (right-aligned) or 0 (no padding).   hm_hex  A as 2 digits.
;   hm_entry   A = scenario 1-6, X = rank 0-4 -> hm_ent.
;   hm_rank_head  X = rank: "k " then "-" (C set, empty entry) or the name
;              and the score (C clear).
;   hm_inverse $80: inverse characters, 0: normal.
; File layout and drawing: tools/score_ref.py (the oracle), docs/HOF.md.
; ============================================================================

hm_ptr   = HOF_ZP
hm_ent   = HOF_ZP + 2
HM_MAGIC   = 'H'
HM_VERSION = 1
HM_HEADER  = 32
HM_ESIZE   = 16
HM_RANKS   = 5
HM_BLOCK   = HM_RANKS * HM_ESIZE
HM_INVALID = $01                ; status: short file, bad magic or version
HM_E_SCORE = 8                  ; entry offsets
HM_E_HOURS = 10
HM_E_LEVEL = 12
HM_E_OUTCOME = 13

.ifdef HOF_READ_PARMS
hm_rw    = HOF_READ_PARMS
.endif

; ----------------------------------------------------------------------------
hm_load:
        jsr     hm_open_file
        bcs     @fail
        lda     #$CA            ; READ
        jsr     hm_transfer
        php
        pha
        jsr     hm_close_file
        pla
        plp
        bcs     @fail
        lda     hm_rw+6         ; exactly 512 bytes
        ora     hm_rw+7
        cmp     #2
        bne     @invalid
        lda     hm_rw+6
        bne     @invalid
        lda     HOF_BUF
        cmp     #HM_MAGIC
        bne     @invalid
        lda     HOF_BUF+1
        cmp     #HM_VERSION
        bne     @invalid
        lda     #0
        sta     hm_status
        clc
        rts
@invalid:
        lda     #HM_INVALID
@fail:  sta     hm_status
        ldx     #0              ; an empty table for the drawing
        txa
:       sta     HOF_BUF,x
        sta     HOF_BUF+256,x
        inx
        bne     :-
        lda     #HM_MAGIC
        sta     HOF_BUF
        lda     #HM_VERSION
        sta     HOF_BUF+1
        lda     hm_status
        sec
        rts

.ifndef HOF_LOADER
hm_save:
        jsr     hm_open_file
        bcs     @rts
        lda     #$CB            ; WRITE
        jsr     hm_transfer
        bcc     @close
        sta     hm_tmp          ; keep the WRITE error, close anyway
        jsr     hm_close_file
        lda     hm_tmp
        sta     hm_status
        sec
@rts:   rts
@close: jmp     hm_close_file   ; its C and A
.endif

; hm_open_file -- path from HOF_PATH, then OPEN. C set: A = error.
hm_open_file:
        ldx     HOF_PATH
        cpx     #4
        bcs     :+
        lda     #$40            ; ProDOS "invalid pathname"
        sec
        rts
:       stx     hm_path
:       lda     HOF_PATH,x
        sta     hm_path,x
        dex
        bne     :-
        ldx     HOF_PATH        ; ".GEO" -> ".HOF"
        lda     #'F'
        sta     hm_path,x
        lda     #'O'
        sta     hm_path-1,x
        lda     #'H'
        sta     hm_path-2,x
        lda     #$C8            ; OPEN
        ldx     #<hm_open
        ldy     #>hm_open
        jsr     HOF_MLI
        bcs     :+
        lda     hm_open+5
        sta     hm_rw+1
        sta     hm_close+1
:       rts

; hm_transfer -- A = READ ($CA) or WRITE ($CB) of 512 bytes at HOF_BUF.
hm_transfer:
        ldx     #4
        stx     hm_rw
        ldx     #<HOF_BUF
        stx     hm_rw+2
        ldx     #>HOF_BUF
        stx     hm_rw+3
        ldx     #0
        stx     hm_rw+4
        stx     hm_rw+6
        stx     hm_rw+7
        ldx     #2
        stx     hm_rw+5
        ldx     #<hm_rw
        ldy     #>hm_rw
        jmp     HOF_MLI

; hm_close_file -- CLOSE; on an error, CLOSE 0 (every file) and keep the
; first error in hm_status / A with C set.
hm_close_file:
        lda     #$CC
        ldx     #<hm_close
        ldy     #>hm_close
        jsr     HOF_MLI
        bcc     @rts
        sta     hm_status
        lda     #0
        sta     hm_close+1
        lda     #$CC
        ldx     #<hm_close
        ldy     #>hm_close
        jsr     HOF_MLI
        lda     hm_status
        sec
@rts:   rts

; ----------------------------------------------------------------------------
; Text page 1, 40 columns: base = $400 + $80 * (row & 7) + 40 * (row >> 3).
hm_at:  sty     hm_col
        tax
        lsr     a               ; C = row & 1
        and     #3
        ora     #4
        sta     hm_ptr+1
        lda     #0
        ror     a
        sta     hm_ptr
        txa
        lsr     a
        lsr     a
        lsr     a
        tax
        lda     hm_ptr
        clc
        adc     hm_row40,x
        sta     hm_ptr
        rts
hm_row40: .byte 0, 40, 80

; hm_char -- A = ASCII $20-$5F; keeps X.
hm_char:
        bit     hm_inverse
        bmi     @inv
        ora     #$80
        bne     @put
@inv:   and     #$3F
@put:   ldy     hm_col
        sta     (hm_ptr),y
        inc     hm_col
        rts

; hm_print -- A/Y = ASCIIZ (plain ASCII).
hm_print:
        sta     @src+1
        sty     @src+2
        ldx     #0
@src:   lda     $FFFF,x
        beq     @done
        jsr     hm_char
        inx
        bne     @src
@done:  rts

; hm_spaces -- X = count of spaces (current attribute).
hm_spaces:
        lda     #' '
        jsr     hm_char
        dex
        bne     hm_spaces
        rts

; hm_clear_row -- A = row: 40 normal spaces, cursor at column 0.
hm_clear_row:
        ldy     #0
        jsr     hm_at
        lda     #' '|$80
        ldy     #39
:       sta     (hm_ptr),y
        dey
        bpl     :-
        rts

hm_clear:
        lda     #0
        sta     hm_inverse
        lda     #23
        sta     hm_row
:       lda     hm_row
        jsr     hm_clear_row
        dec     hm_row
        bpl     :-
        rts

; hm_title -- A/Y = text, X = column: row 0 as an inverse band.
hm_title:
        sta     hm_tmp
        sty     hm_tmp+1
        stx     hm_col0
        lda     #$80
        sta     hm_inverse
        lda     #0
        tay
        jsr     hm_at
        ldx     #40
        jsr     hm_spaces
        lda     #0
        ldy     hm_col0
        jsr     hm_at
        lda     hm_tmp
        ldy     hm_tmp+1
        jsr     hm_print
        lda     #0
        sta     hm_inverse
        rts

; hm_num -- A/X = value, Y = width 1..5 (right-aligned) or 0 (no padding).
hm_num: sta     hm_val
        stx     hm_val+1
        sty     hm_width
        ldx     #0
        stx     hm_lead
@digit: ldy     #'0'
@sub:   lda     hm_val
        sec
        sbc     hm_pow_lo,x
        pha
        lda     hm_val+1
        sbc     hm_pow_hi,x
        bcc     @less
        sta     hm_val+1
        pla
        sta     hm_val
        iny
        bne     @sub
@less:  pla
        tya
        cpx     #4
        beq     @store          ; units: always a digit
        cmp     #'0'
        bne     @nonzero
        ldy     hm_lead
        bne     @store
        lda     #' '
        bne     @store
@nonzero:
        inc     hm_lead
@store: sta     hm_digits,x
        inx
        cpx     #5
        bne     @digit
        ldy     hm_width
        beq     @trim
        lda     #5
        sec
        sbc     hm_width
        tax
        bpl     @out
@trim:  ldx     #0
:       lda     hm_digits,x
        cmp     #' '
        bne     @out
        inx
        bne     :-
@out:   lda     hm_digits,x
        jsr     hm_char
        inx
        cpx     #5
        bne     @out
        rts
hm_pow_lo: .byte <10000, <1000, <100, <10, <1
hm_pow_hi: .byte >10000, >1000, >100, >10, >1

; hm_hex -- A as two hexadecimal digits.
hm_hex: pha
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        jsr     @nibble
        pla
        and     #$0F
@nibble:
        cmp     #10
        bcc     :+
        adc     #6              ; C set: + 7
:       adc     #'0'
        jmp     hm_char

; hm_entry -- A = scenario 1..6, X = rank 0..4: hm_ent = its 16 bytes.
hm_entry:
        sec
        sbc     #1
        sta     hm_ent
        asl     a
        asl     a
        adc     hm_ent          ; * 5
        stx     hm_ent
        adc     hm_ent          ; + rank
        sta     hm_ent
        lda     #0
        sta     hm_ent+1
        ldx     #4
:       asl     hm_ent
        rol     hm_ent+1
        dex
        bne     :-
        clc
        lda     hm_ent
        adc     #<(HOF_BUF + HM_HEADER)
        sta     hm_ent
        lda     hm_ent+1
        adc     #>(HOF_BUF + HM_HEADER)
        sta     hm_ent+1
        rts

; hm_rank_head -- X = rank 0..4, hm_ent set: "k -" (C set) or
; "k NAMENAME nnnnn" (C clear).
hm_rank_head:
        txa
        clc
        adc     #'1'
        jsr     hm_char
        lda     #' '
        jsr     hm_char
        ldy     #HM_E_OUTCOME
        lda     (hm_ent),y
        bne     @full
        lda     #'-'
        jsr     hm_char
        sec
        rts
@full:  lda     #0
        sta     hm_idx
:       ldy     hm_idx
        lda     (hm_ent),y
        and     #$7F
        jsr     hm_char
        inc     hm_idx
        lda     hm_idx
        cmp     #8
        bne     :-
        lda     #' '
        jsr     hm_char
        ldy     #HM_E_SCORE+1
        lda     (hm_ent),y
        tax
        dey
        lda     (hm_ent),y
        ldy     #5
        jsr     hm_num
        clc
        rts

; hm_unreadable -- A = error: "HALL OF FAME UNREADABLE, ERROR $xx." or, for
; HM_INVALID, "HALL OF FAME FILE NOT RECOGNISED." at the cursor.
hm_unreadable:
        cmp     #HM_INVALID
        bne     :+
        lda     #<hm_m_invalid
        ldy     #>hm_m_invalid
        jmp     hm_print
:       pha
        lda     #<hm_m_unreadable
        ldy     #>hm_m_unreadable
        jsr     hm_print
        pla
        jsr     hm_hex
        lda     #'.'
        jmp     hm_char

; ----------------------------------------------------------------------------
.ifdef HOF_LOADER
BEST_ROW0 = 2                   ; genmenu.py: rows 2, 5 ... 17, "BEST -" at 33
BEST_COL  = 29

hm_best:
        lda     #0
        sta     hm_inverse
        lda     #1
        sta     hm_scen
@scen:  lda     hm_scen
        ldx     #0
        jsr     hm_entry
        ldy     #HM_E_OUTCOME
        lda     (hm_ent),y
        beq     @next
        lda     hm_scen         ; row = 3 * scenario - 1
        asl     a
        adc     hm_scen
        sbc     #0              ; C clear: - 1
        ldy     #BEST_COL
        jsr     hm_at
        lda     #<hm_m_best
        ldy     #>hm_m_best
        jsr     hm_print
        ldy     #HM_E_SCORE+1
        lda     (hm_ent),y
        tax
        dey
        lda     (hm_ent),y
        ldy     #5
        jsr     hm_num
@next:  inc     hm_scen
        lda     hm_scen
        cmp     #7
        bne     @scen
        rts

; Blocks: scenario s at row 2 + 7 * ((s - 1) / 2), column 0 (odd) or 20.
hm_hall:
        jsr     hm_clear
        lda     #<hm_m_hall
        ldy     #>hm_m_hall
        ldx     #14
        jsr     hm_title
        lda     #1
        sta     hm_scen
@scen:  lda     hm_scen
        sec
        sbc     #1
        lsr     a
        sta     hm_row          ; (s - 1) / 2
        asl     a
        asl     a
        asl     a
        sec
        sbc     hm_row          ; * 7
        clc
        adc     #2
        sta     hm_row
        lda     hm_scen
        and     #1
        eor     #1
        beq     :+
        lda     #20
:       sta     hm_col0
        lda     #$80            ; header "s NAME", inverse
        sta     hm_inverse
        lda     hm_row
        ldy     hm_col0
        jsr     hm_at
        lda     hm_scen
        ora     #'0'
        jsr     hm_char
        lda     #' '
        jsr     hm_char
        ldx     hm_scen
        lda     HOF_NAMES_LO-1,x
        ldy     HOF_NAMES_HI-1,x
        jsr     hm_print
        lda     #0
        sta     hm_inverse
        lda     #0
        sta     hm_rank
@rank:  inc     hm_row
        lda     hm_row
        ldy     hm_col0
        jsr     hm_at
        lda     hm_scen
        ldx     hm_rank
        jsr     hm_entry
        ldx     hm_rank
        jsr     hm_rank_head
        inc     hm_rank
        lda     hm_rank
        cmp     #HM_RANKS
        bne     @rank
        inc     hm_scen
        lda     hm_scen
        cmp     #7
        beq     :+
        jmp     @scen
:       lda     #22
        ldy     #0
        jsr     hm_at
        lda     hm_status
        beq     :+
        jsr     hm_unreadable
        jmp     @key
:       lda     #<hm_m_journeys
        ldy     #>hm_m_journeys
        jsr     hm_print
        lda     HOF_BUF+2
        ldx     HOF_BUF+3
        ldy     #0
        jsr     hm_num
@key:   lda     #23
        ldy     #0
        jsr     hm_at
        lda     #<hm_m_key
        ldy     #>hm_m_key
        jmp     hm_print

hm_m_best:     .byte "BEST ", 0
hm_m_hall:     .byte "HALL OF FAME", 0
hm_m_journeys: .byte "SCENARIO JOURNEYS: ", 0
hm_scen:  .byte 0
hm_rank:  .byte 0
.endif

hm_m_key:        .byte "PRESS A KEY FOR THE MENU.", 0
hm_m_invalid:    .byte "HALL OF FAME FILE NOT RECOGNISED.", 0
hm_m_unreadable: .byte "HALL OF FAME UNREADABLE, ERROR $", 0

; Variables and parameter blocks (in the including segment).
hm_status:  .byte 0
hm_inverse: .byte 0
hm_col:     .byte 0
hm_col0:    .byte 0
hm_row:     .byte 0
hm_idx:     .byte 0
hm_tmp:     .word 0
hm_val:     .word 0
hm_width:   .byte 0
hm_lead:    .byte 0
hm_digits:  .res 5
hm_open:    .byte 3
            .word hm_path, HOF_IOBUF
            .byte 0
.ifndef HOF_READ_PARMS
hm_rw:      .byte 4, 0
            .word 0, 0, 0
.endif
hm_close:   .byte 1, 0
.ifdef HOF_PATHBUF
hm_path = HOF_PATHBUF
.else
hm_path:    .res 65
.endif
