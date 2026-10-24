; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; vapor.asm -- vapor lock: find the video beam through the floating bus
; ============================================================================
;   vapor_mark  -- put VAPOR_BYTE in the first 24 bytes of HGR line 191 of
;                  page 1 ($3FD0-$3FE7; page 2 with VAPOR_PAGE = 2). Leave
;                  the rest of the line without it. Clobbers A, X.
;   vapor_sync  -- wait until the beam reads that line, the last one shown:
;                  C = 0 on return, the beam is on line 191 (VBL follows
;                  ~60 cycles later). C = 1 after 65536 polls (~0.8 s at
;                  1 MHz) without it: no floating bus (//c, IIgs) or no
;                  marker on the screen. (Long enough for a frame of an
;                  accelerated machine: ~1310 polls at 1 MHz, ~10000 at 8.)
;                  Clobbers A, X, Y.
;   vapor_count -- one frame measured in vapor_sync's 13-cycle polls: two
;                  syncs, the polls of the second. A = low, X = high byte;
;                  C = 1 (A = X = 0) when either sync fails. A 1 MHz NTSC
;                  machine gives ~VAPOR_NTSC_COUNT (~1310), a PAL one
;                  (20280-cycle frames) 1.19 times that, an accelerator card
;                  several times more.
;                  Clobbers A, X, Y.
;
; The floating bus: a soft switch that drives no data ($C050-$C05F) reads back
; the byte the video scanner fetched on that cycle (Sather, Understanding the
; Apple II, ch. 3). Polling it for a byte found only on line 191 finds the
; beam there, once per frame: the II and II+ have no VBL flag, and on a //e
; this needs no $C019. The marker is VAPOR_BYTE ($80 by default: no pixel lit,
; black), and two reads 9 cycles apart (9 bytes of the scan) must both see it,
; so a lone $80 elsewhere on the screen cannot fake a sync.
; Why 24 bytes and not the whole line: the scanner also fetches memory during
; blanking (MAME's scanner_address, as POM2 and a2run have it), and the
; horizontal blanking of lines 255 and 261 (in VBL) reads bytes 16-39 of line
; 191, that of line 63 its bytes 24-39. Bytes 0-15 are read only on line 191
; itself. With bytes 0-23 marked, the first read that sees the marker on line
; 191 lands on byte 0-12 (a 13-cycle poll) and the second on 9-21, still in
; it; on lines 255 and 261 only bytes 16-23 are marked, and the second read
; falls past them. One lock a frame, on line 191, within one poll. (The poll
; must stay at most 13 cycles for that: a 17-cycle one, tried for counting,
; missed one frame in eight.)
;
; The read is TXTCLR ($C050): the program shows HGR, so it is already set.
; The scanner shows the displayed page: mark the page on screen (and mark it
; again after clearing it). The poll loop must not straddle a page boundary
; (a taken branch across one costs a cycle): it does not care, a sync only
; drifts by that cycle.
;
; Caller responsibility: .include "apple2.inc" first (TXTCLR).
; Assembled only if referenced before the include (.ifref). From SNAKE.
; ============================================================================

.ifndef VAPOR_BYTE
VAPOR_BYTE = $80
.endif
.ifndef VAPOR_PAGE
VAPOR_PAGE = 1
.endif
VAPOR_LINE191 = VAPOR_PAGE * $2000 + $1FD0     ; HGR line 191
VAPOR_LEN = 24                  ; marked bytes at its start (see above)
VAPOR_NTSC_COUNT = 17030 / 13   ; vapor_count at 1 MHz NTSC (~1310)

.if .referenced(vapor_mark)
.segment "CODE"
vapor_mark:
        LDA     #VAPOR_BYTE
        LDX     #VAPOR_LEN-1
@lp:    STA     VAPOR_LINE191,X
        DEX
        BPL     @lp
        RTS
.endif

.if .referenced(vapor_sync) .or .referenced(vapor_count)
.segment "CODE"
vapor_sync:
        LDX     #0              ; Y:X counts the polls down from 65536
        LDY     #0
@out:   LDA     TXTCLR          ; first leave the marker (called right after
        CMP     #VAPOR_BYTE     ; a sync, the beam may still be on it)
        BNE     @in
        DEX
        BNE     @out
        DEY
        BNE     @out
        SEC
        RTS
@in:    LDA     TXTCLR          ; 13 cycles a poll
        CMP     #VAPOR_BYTE
        BEQ     @hit
@next:  DEX
        BNE     @in
        DEY
        BNE     @in
        SEC
        RTS
@hit:   LDA     TXTCLR          ; 9 cycles later, the second read must see it too
        CMP     #VAPOR_BYTE
        BNE     @next
        CLC
        RTS
.endif

.if .referenced(vapor_count)
.segment "CODE"
vapor_count:
        JSR     vapor_sync
        BCS     @fail
        JSR     vapor_sync      ; the polls of one frame: X counted down
        BCS     @fail           ; from 0 each poll, Y each time X reached
        TYA                     ; 0, so polls = 256 * -Y + -X (each byte
        EOR     #$FF            ; negated on its own: no borrow between)
        CLC
        ADC     #1
        PHA                     ; high byte (-Y)
        TXA
        EOR     #$FF
        CLC
        ADC     #1
        TAY                     ; low byte (-X)
        PLA
        TAX                     ; X = high
        TYA                     ; A = low
        CLC
        RTS
@fail:  LDA     #0
        TAX
        SEC
        RTS
.endif
