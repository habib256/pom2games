; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hof_load.inc -- module_end and module_restart (INPUT, lot 7 step 6)
; ============================================================================
; Included by input.s in the INPUT module, where it replaces the former
; module_restart and its data (one routine, hl_load, now reads both files).
; `quit` (wild.s) loads INPUT and jumps to module_end:
;   module_end     reads NEOWILD.END (wildhof.bin, src/hof.s) into the SIM
;                  window at $9600, free once the journey is over, and enters
;                  it at its first byte. The module shows the score and the
;                  hall of fame, reloads INPUT and jumps to module_restart.
;                  If NEOWILD.END cannot be read: module_restart directly.
;   module_restart restores the system as for ProDOS (prodos_restore: text,
;                  /RAM, bitmap, RESET vector, zero page), then reads
;                  NEOWILD.SYSTEM again to $2000 and runs it: a fresh loader
;                  and its start menu, no state kept. An MLI error leaves to
;                  ProDOS (prodos_quit).
; Both paths are NEOWILD.GEO's (geo_path, built by the loader) with GEO
; replaced. The game protects $9600-$B5FF in the ProDOS bitmap and READ
; refuses a buffer there (error $56, measured): module_end releases those 32
; pages first; prodos_restore puts the saved bitmap back.
; Runs in the $5800 window: neither file reaches it. No zero page.
; Needs: geo_path, mli_call, io_buffer, prodos_restore, prodos_quit.
; HL_BENCH (src/hof_test.s): module_end only; the bench has its own
; module_restart.
; ============================================================================
HOF_RUN   = $9600
HL_BITMAP = $BF58               ; ProDOS bitmap (memory.s PD_BITMAP)

module_end:
        lda     HL_BITMAP+18    ; pages $96-$97
        and     #$FC
        sta     HL_BITMAP+18
        lda     #0              ; $98-$AF
        sta     HL_BITMAP+19
        sta     HL_BITMAP+20
        sta     HL_BITMAP+21
        lda     HL_BITMAP+22    ; $B0-$B5
        and     #$03
        sta     HL_BITMAP+22
        ldx     #hl_end-hl_suffixes
        lda     #>HOF_RUN
        ldy     #>($B600-HOF_RUN)
        jsr     hl_load
        bcc     :+
        jmp     module_restart
:       jmp     HOF_RUN

.ifndef HL_BENCH
module_restart:
        jsr     prodos_restore
        ldx     #$FF
        txs
        ldx     #hl_system-hl_suffixes
        lda     #$20
        ldy     #>($5800-$2000)
        jsr     hl_load
        bcs     :+
        jmp     $2000
:       jmp     prodos_quit
.export module_restart, module_end
.endif

; hl_load -- X = suffix offset in hl_suffixes, A = destination page, Y =
; pages requested (the file is shorter): OPEN, READ, CLOSE. C set: error.
hl_load:
        sta     hl_read+3
        sty     hl_read+5
        ldy     geo_path        ; "/VOLUME/NEOWILD.GEO"
        cpy     #4
        bcc     @error
:       lda     geo_path,y
        sta     hl_path,y
        dey
        bpl     :-
        ldy     geo_path        ; the suffix replaces "GEO"
        dey
        dey
:       lda     hl_suffixes,x
        beq     :+
        sta     hl_path,y
        iny
        inx
        bne     :-
:       dey
        sty     hl_path
        lda     #$C8            ; OPEN
        ldx     #<hl_open
        ldy     #>hl_open
        jsr     mli_call
        bcs     @rts
        lda     hl_open+5
        sta     hl_read+1
        sta     hl_close+1
        lda     #$CA            ; READ
        ldx     #<hl_read
        ldy     #>hl_read
        jsr     mli_call
        php
        lda     #$CC            ; CLOSE
        ldx     #<hl_close
        ldy     #>hl_close
        jsr     mli_call
        plp
@rts:   rts
@error: sec
        rts

hl_suffixes:
hl_system: .byte "SYSTEM", 0
hl_end:    .byte "END", 0
hl_open:   .byte 3
           .word hl_path, io_buffer
           .byte 0
hl_read:   .byte 4, 0
           .word 0, 0, 0
hl_close:  .byte 1, 0
hl_path:   .res 44
