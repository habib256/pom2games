; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; save.s -- SAVE and RESTORE, five games on the disk (lot 9, docs/SAVE.md)
; ============================================================================
; The only disk accesses of a journey besides its end (NEOWILD.END/.HOF).
; Resident part (WILDLO): do_save, reached by the verbs SAVE (41) and
; RESTORE (42), frees pages $96-$AF in the ProDOS bitmap, reads NEOWILD.SAV
; (this file's SAVEMOD segment, build/wildsav.bin) into the SIM window at
; $9600 with an I/O buffer at $AB00, and calls it. The module asks for the
; game number (get_number, INPUT), opens NEOWILD.Sn (one fixed-length file
; per game, created by tools/build_disk.py: no CREATE, no block allocated)
; and writes or reads the image of the journey in SV_BUF. Back in the
; resident part: bitmap bytes put back, SIM marked as not loaded (the window
; holds the module), and after a restore the view rebuilt from the restored
; state (show_view: it may run the star module in the SIM window, so the
; module must have returned first) and "GAME n RESTORED.".
;
; Slot file: SV_HEAD bytes of header, then the state ranges of sv_ranges,
; back to back (SV_STATE bytes):
;   0  'N','W'        magic          8  state length (u16)
;   2  1              version       10  Fletcher-16 of the state
;   3  region 1..6    (region_number)12  elapsed hours (u16)
;   4  level, 5 kind  (MAP+22, +33) 14  0, 0
;   6  build id (u16, patched into NEOWILD.SAV by tools/build_disk.py)
;  16  region name (16 bytes, REGIONTEXT region_name)
; A file whose magic is absent is an empty game. RESTORE refuses another
; region (the original's C$(IC)" ONLY!", with a full stop: "!" is a
; placeholder of message), another build, a bad length or
; checksum, and changes nothing then.
; ============================================================================
SV_RUN    = $9600               ; module (SIM window, free between commands)
SV_BUF    = $9C00               ; slot image (header + state)
SV_IOBUF  = $AB00               ; ProDOS I/O buffer of both files
SV_PATH   = $AF00               ; "/VOLUME/NEOWILD.Sn"
SV_MSG    = $AF40               ; messages built by the module
SV_HEAD   = 32
SV_GAMES  = 5
.import __BSS_RUN__

.segment "LOWCODE"
; do_save -- verbs SAVE and RESTORE (verb = 41 or 42).
do_save:
        ldx     #3              ; pages $90-$AF of the bitmap
:       lda     $BF58+18,x
        sta     sl_bitmap,x
        dex
        bpl     :-
        lda     $BF58+18
        and     #$FC            ; $96-$97
        sta     $BF58+18
        lda     #0              ; $98-$AF: module, image, I/O buffer, path
        sta     $BF58+19
        sta     $BF58+20
        sta     $BF58+21
        sta     sl_slot
        ldy     geo_path        ; "/VOLUME/NEOWILD.GEO" -> ".SAV"
:       lda     geo_path,y
        sta     SV_PATH,y
        dey
        bpl     :-
        ldx     geo_path
        ldy     #2
:       lda     sl_suffix,y
        sta     SV_PATH,x
        dex
        dey
        bpl     :-
        lda     #$C8            ; OPEN
        ldx     #<sl_open
        ldy     #>sl_open
        jsr     mli_call
        bcs     @missing
        lda     sl_open+5
        sta     sl_read+1
        sta     sl_close+1
        lda     #$CA            ; READ
        ldx     #<sl_read
        ldy     #>sl_read
        jsr     mli_call
        php
        lda     #$CC            ; CLOSE
        ldx     #<sl_close
        ldy     #>sl_close
        jsr     mli_call
        plp
        bcs     @missing
        jsr     SV_RUN          ; sl_slot <> 0: a game was restored
        jmp     @back
@missing:
        lda     #<m_save_missing
        ldx     #>m_save_missing
        jsr     message
@back:  ldx     #3
:       lda     sl_bitmap,x
        sta     $BF58+18,x
        dex
        bpl     :-
        lda     #0
        sta     sim_loaded      ; the window holds the module
        lda     sl_slot
        beq     @done
        lda     #1
        sta     stars_stale     ; the star list of the restored hour
        lda     #0
        sta     scene_cache_valid
        jsr     show_view
        lda     sl_slot
        sta     msgnum
        lda     #0
        sta     msgnum+1
        sta     shown
        lda     #<m_restored
        ldx     #>m_restored
        jmp     message
@done:  rts

.segment "LOWTEXT"
sl_slot:   .byte 0              ; the game restored (module), else 0
sl_bitmap: .res 4
sl_suffix: .byte "SAV"
sl_open:   .byte 3
           .word SV_PATH, SV_IOBUF
           .byte 0
sl_read:   .byte 4, 0
           .word SV_RUN, SV_IOBUF-SV_RUN, 0
sl_close:  .byte 1, 0
m_save_missing: .byte "NEOWILD.SAV CANNOT BE READ.", 0
m_restored: .byte "GAME # RESTORED.", 0
.export do_save, sl_slot

; ----------------------------------------------------------------------------
; NEOWILD.SAV, run at $9600
; ----------------------------------------------------------------------------
.segment "SAVEMOD"
sv_entry:
        lda     verb
        sta     sv_verb
        lda     #<sv_ask_save
        ldx     #>sv_ask_save
        ldy     verb
        cpy     #41
        beq     :+
        lda     #<sv_ask_restore
        ldx     #>sv_ask_restore
:       jsr     get_number      ; C: cancelled, message shown
        bcc     :+
        rts
:       lda     msgnum+1
        bne     @range
        lda     msgnum
        beq     @range
        cmp     #SV_GAMES+1
        bcc     @slot
@range: lda     #<sv_m_range
        ldx     #>sv_m_range
        jmp     sv_message
@slot:  sta     sv_slot
        ora     #'0'
        sta     sv_digit
        ldy     SV_PATH         ; "/VOLUME/NEOWILD.SAV" -> ".Sn"
        sta     SV_PATH-1,y
        dey
        sty     SV_PATH
        lda     #$C8            ; OPEN
        ldx     #<sv_open
        ldy     #>sv_open
        jsr     mli_call
        bcc     :+
        jmp     sv_error
:       lda     sv_open+5
        sta     sv_read+1
        sta     sv_mark+1
        sta     sv_write+1
        sta     sv_close+1
        lda     sv_verb
        cmp     #41
        beq     sv_save
        jmp     sv_restore

; ---------------------------------------------------------------- SAVE
sv_save:
        lda     #SV_HEAD        ; the header: is the game taken?
        sta     sv_read+4
        lda     #0
        sta     sv_read+5
        jsr     sv_do_read
        bcs     sv_fail
        jsr     sv_taken
        bne     @write
        jsr     sv_describe     ; "GAME n: REGION, h H." + the question
        ldy     #0
:       lda     sv_m_replace,y
        sta     SV_MSG,x
        beq     :+
        inx
        iny
        bne     :-
:       jsr     sv_show
        jsr     prompt
        jsr     wait_key
        jsr     kbd_upcase
        cmp     #'Y'
        beq     @write
        jsr     sv_close_file
        lda     #<sv_m_kept
        ldx     #>sv_m_kept
        jmp     sv_message
@write: jsr     sv_gather
        lda     #$CE            ; SET_MARK 0
        ldx     #<sv_mark
        ldy     #>sv_mark
        jsr     mli_call
        bcs     sv_fail
        lda     #$CB            ; WRITE
        ldx     #<sv_write
        ldy     #>sv_write
        jsr     mli_call
        bcs     sv_fail
        jsr     sv_close_file
        bcs     sv_error
        lda     #<sv_m_saved
        ldx     #>sv_m_saved
        jmp     sv_message

; sv_fail -- A = MLI error with the file open: close, then report.
sv_fail:
        pha
        jsr     sv_close_file
        bcc     :+
        lda     #$CC            ; CLOSE of reference 0: every file
        ldx     #<sv_close_all
        ldy     #>sv_close_all
        jsr     mli_call
:       pla
; sv_error -- A = MLI error: "DISK WRITE-PROTECTED" ($2B), "NEOWILD.Sn IS
; MISSING" ($46), else "DISK ERROR xxH". Nothing changed.
sv_error:
        cmp     #$2B
        bne     :+
        lda     #<sv_m_protected
        ldx     #>sv_m_protected
        jmp     sv_message
:       cmp     #$46
        bne     :+
        lda     #<sv_m_nofile
        ldx     #>sv_m_nofile
        jmp     sv_message
:       pha
        lsr
        lsr
        lsr
        lsr
        jsr     sv_hex
        sta     sv_m_hex
        pla
        and     #15
        jsr     sv_hex
        sta     sv_m_hex+1
        lda     #<sv_m_disk
        ldx     #>sv_m_disk
        jmp     sv_message
sv_hex: cmp     #10
        bcc     :+
        adc     #6              ; C set: +7
:       adc     #'0'
        rts

; ------------------------------------------------------------- RESTORE
sv_restore:
        lda     #<(SV_HEAD+SV_STATE)
        sta     sv_read+4
        lda     #>(SV_HEAD+SV_STATE)
        sta     sv_read+5
        jsr     sv_do_read
        bcs     sv_fail
        jsr     sv_close_file
        bcs     sv_error
        jsr     sv_taken
        beq     :+
        lda     #<sv_m_empty
        ldx     #>sv_m_empty
        jmp     sv_message
:       lda     SV_BUF+2        ; version, build, length
        cmp     #1
        bne     @other
        lda     SV_BUF+6
        cmp     sv_build
        bne     @other
        lda     SV_BUF+7
        cmp     sv_build+1
        bne     @other
        lda     SV_BUF+8
        cmp     #<SV_STATE
        bne     @other
        lda     SV_BUF+9
        cmp     #>SV_STATE
        bne     @other
        jsr     sv_checksum
        cmp     SV_BUF+11
        bne     @damaged
        cpx     SV_BUF+10
        bne     @damaged
        lda     SV_BUF+3        ; the region of the loaded pack only
        cmp     region_number
        beq     @scatter
        ldx     #0              ; "BURMA ONLY!"
        jsr     sv_name
        ldy     #0
:       lda     sv_m_only,y
        sta     SV_MSG,x
        beq     :+
        inx
        iny
        bne     :-
:       jmp     sv_show
@other: lda     #<sv_m_other
        ldx     #>sv_m_other
        jmp     sv_message
@damaged:
        lda     #<sv_m_damaged
        ldx     #>sv_m_damaged
        jmp     sv_message
@scatter:
        lda     #1              ; image -> state
        jsr     sv_copy
        lda     #0              ; the menu starts again from its first cell
        sta     mn_cur
        sta     mn_top
        sta     mn_verb
        sta     menu_noun
        lda     sv_slot
        sta     sl_slot         ; do_save rebuilds the view
        rts

; ------------------------------------------------------------- helpers
sv_do_read:
        lda     #$CA
        ldx     #<sv_read
        ldy     #>sv_read
        jmp     mli_call
sv_close_file:
        lda     #$CC
        ldx     #<sv_close
        ldy     #>sv_close
        jmp     mli_call

; sv_taken -- Z set if the header in SV_BUF is a saved game's.
sv_taken:
        lda     SV_BUF
        cmp     #'N'
        bne     :+
        lda     SV_BUF+1
        cmp     #'W'
:       rts

; sv_describe -- SV_MSG = "GAME n: REGION, # H.|", msgnum = the hours of the
; header in SV_BUF; X = end of the text.
sv_describe:
        lda     SV_BUF+12
        sta     msgnum
        lda     SV_BUF+13
        sta     msgnum+1
        ldx     #0
; sv_name -- SV_MSG+X = "GAME n: " + the region name of SV_BUF; X = end.
sv_name:
        ldy     #0
:       lda     sv_m_game,y
        sta     SV_MSG,x
        inx
        iny
        cpy     #8
        bcc     :-
        ldy     #0
:       lda     SV_BUF+16,y
        beq     :+
        sta     SV_MSG,x
        inx
        iny
        cpy     #16
        bcc     :-
:       rts

; sv_gather -- header and state into SV_BUF.
sv_gather:
        lda     #'N'
        sta     SV_BUF
        lda     #'W'
        sta     SV_BUF+1
        lda     #1
        sta     SV_BUF+2
        lda     region_number
        sta     SV_BUF+3
        lda     MAP+22
        sta     SV_BUF+4
        lda     MAP+33
        sta     SV_BUF+5
        lda     sv_build
        sta     SV_BUF+6
        lda     sv_build+1
        sta     SV_BUF+7
        lda     #<SV_STATE
        sta     SV_BUF+8
        lda     #>SV_STATE
        sta     SV_BUF+9
        fld     s_elap          ; whole hours
        jsr     AYINT
        lda     $A1
        sta     SV_BUF+12
        lda     $A0
        sta     SV_BUF+13
        lda     #0
        sta     SV_BUF+14
        sta     SV_BUF+15
        ldx     #15
:       lda     region_name,x
        sta     SV_BUF+16,x
        dex
        bpl     :-
        lda     #0              ; state -> image
        jsr     sv_copy
        jsr     sv_checksum
        stx     SV_BUF+10
        sta     SV_BUF+11
        rts

; sv_copy -- A = 0: the ranges of sv_ranges into the image; A = 1: back.
sv_copy:
        sta     sv_dir
        lda     #<(SV_BUF+SV_HEAD)
        sta     gp2
        lda     #>(SV_BUF+SV_HEAD)
        sta     gp2+1
        ldx     #0
@range: lda     sv_ranges,x
        sta     gp1
        lda     sv_ranges+1,x
        sta     gp1+1
        ora     gp1
        beq     @done
        lda     sv_ranges+2,x
        sta     g0              ; length
        lda     sv_ranges+3,x
        sta     g1
        ldy     #0
@byte:  lda     g0
        ora     g1
        beq     @next
        lda     sv_dir
        bne     @back
        lda     (gp1),y
        sta     (gp2),y
        jmp     @step
@back:  lda     (gp2),y
        sta     (gp1),y
@step:  inc     gp1
        bne     :+
        inc     gp1+1
:       inc     gp2
        bne     :+
        inc     gp2+1
:       lda     g0
        bne     :+
        dec     g1
:       dec     g0
        jmp     @byte
@next:  inx
        inx
        inx
        inx
        bne     @range
@done:  rts

; sv_checksum -- Fletcher-16 of the state in SV_BUF: X = sum, A = sum of sums.
sv_checksum:
        lda     #<(SV_BUF+SV_HEAD)
        sta     gp1
        lda     #>(SV_BUF+SV_HEAD)
        sta     gp1+1
        lda     #<SV_STATE
        sta     g0
        lda     #>SV_STATE
        sta     g1
        lda     #0
        sta     g2
        tax
        ldy     #0
@byte:  lda     g0
        ora     g1
        beq     @done
        txa
        clc
        adc     (gp1),y
        adc     #0              ; end-around carry (modulo 255)
        tax
        clc
        adc     g2
        adc     #0
        sta     g2
        inc     gp1
        bne     :+
        inc     gp1+1
:       lda     g0
        bne     :+
        dec     g1
:       dec     g0
        jmp     @byte
@done:  lda     g2
        rts

; sv_message -- A/X: a text of the module ('#' = the game number).
sv_message:
        ldy     sv_slot
        sty     msgnum
        ldy     #0
        sty     msgnum+1
        sty     shown
        jmp     message
; sv_show -- the text built in SV_MSG (msgnum as left by sv_describe).
sv_show:
        lda     #0
        sta     shown
        lda     #<SV_MSG
        ldx     #>SV_MSG
        jmp     message

; The journey: every byte a later command can read (docs/SAVE.md section 3).
; GDATA minus the module cache (overlay_*, sim_*), the parser's line, and the
; constant tables (it_kcal, verbs, verb_lo/hi, card_*, cdef_*, ctol_*, the
; three travel reports); the ground positions it_x/it_y (WILDLO), the map
; header (shelter found, discoveries, level), fauna_named (TEXT).
sv_ranges:
        .word   sun_alt8, overlay_current-sun_alt8
        .word   tree_in, inbuf-tree_in
        .word   s_hour, it_kcal-s_hour
        .word   resource_seen, __BSS_RUN__-resource_seen
        .word   it_x, it_name_lo-it_x
        .word   MAP, 64
        .word   fauna_named, 1
        .word   sky_hy, 3       ; Sun/Moon row and bearing as drawn (LOOK UP/DOWN)
        .word   tilt, 1         ; the view's tilt (zero page)
        .word   0
SV_STATE = (overlay_current-sun_alt8) + (inbuf-tree_in) + (it_kcal-s_hour) + (__BSS_RUN__-resource_seen) + (it_name_lo-it_x) + 64 + 1 + 3 + 1
.assert SV_BUF + SV_HEAD + SV_STATE <= SV_IOBUF, error, "slot image overlaps the I/O buffer"
.assert sv_end <= SV_BUF, error, "NEOWILD.SAV overlaps its slot image"

sv_open:   .byte 3
           .word SV_PATH, SV_IOBUF
           .byte 0
sv_read:   .byte 4, 0
           .word SV_BUF, 0, 0
sv_mark:   .byte 2, 0, 0, 0, 0
sv_write:  .byte 4, 0
           .word SV_BUF, SV_HEAD+SV_STATE, 0
sv_close:  .byte 1, 0
sv_close_all: .byte 1, 0
sv_build:  .word 0              ; tools/build_disk.py: the build of the disk
sv_slot:   .byte 0
sv_dir:    .byte 0
sv_verb:   .byte 0
sv_size:   .word SV_HEAD+SV_STATE ; length of a NEOWILD.Sn file (tools/build_disk.py)

sv_ask_save:    .byte "SAVE THE JOURNEY AS GAME 1-5?|ESC CANCELS.", 0
sv_ask_restore: .byte "RESTORE WHICH GAME, 1-5?|ESC CANCELS.", 0
sv_m_range:     .byte "GAMES ARE NUMBERED 1 TO 5.", 0
sv_m_game:      .byte "GAME "
sv_digit:       .byte "0: "
sv_m_replace:   .byte ", # H.|REPLACE IT? Y: YES   N/ESC: NO", 0
sv_m_kept:      .byte "GAME # KEPT. NOT SAVED.", 0
sv_m_saved:     .byte "GAME # SAVED.", 0
sv_m_protected: .byte "DISK WRITE-PROTECTED: NOT SAVED.", 0
sv_m_nofile:    .byte "NEOWILD.S# IS MISSING.", 0
sv_m_disk:      .byte "DISK ERROR "  ; message: "$" is the stock
sv_m_hex:       .byte "00H. NOTHING CHANGED.", 0
sv_m_empty:     .byte "GAME # IS EMPTY.", 0
sv_m_other:     .byte "GAME # WAS SAVED BY ANOTHER VERSION.", 0
sv_m_damaged:   .byte "GAME # IS DAMAGED.", 0
sv_m_only:      .byte " ONLY.", 0     ; message: "!" names a travel reason
sv_end:
.export sv_entry, sv_build, sv_ranges, sv_slot, sv_size, sv_end
