; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; vapor.asm -- vapor lock: find the video beam through the floating bus
; ============================================================================
;   vapor_mark  -- put VAPOR_BYTE in the first 24 bytes of HGR line 191 of
;                  page 1 ($3FD0-$3FE7; page 2 with VAPOR_PAGE = 2). Leave
;                  the rest of the line without it. Clobbers A, X.
;   vapor_sync  -- wait until the beam reads that line, the last one shown:
;                  C = 0 on return, the beam is on line 191 (VBL follows
;                  ~60 cycles later). C = 1 within 65537 polls (~0.8 s at
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
;   vapor_mark_both -- vapor_mark on both HGR pages ($3FD0-$3FE7 and
;                  $5FD0-$5FE7), for a program that flips them: the page
;                  shown always carries it. Clobbers A, X. (.ifref, 14 B)
;   vapor_pace_init -- vapor_count, the frame kept in polls for vapor_pace;
;                  C = 1 when there is no floating bus (then do not call
;                  vapor_pace: run unpaced). Clobbers A, X, Y.
;   vapor_pace  -- a constant tick rate: A = N video frames a tick (1..255),
;                  X / Y = low / high of the work done since the last
;                  return, estimated in polls (cycles / 13). It waits for
;                  line 191, adds the polls that took to the estimate:
;                  k = round((estimate + polls) / frame), the frames gone
;                  since the last return (at least 1); while k < N, waits
;                  for line 191 again and counts k anew with those polls
;                  (the path after the last wait is the same whatever k
;                  was: the return keeps its phase to a cycle). C = 0: the
;                  beam is on line 191, N frames after the last return when
;                  the work took less than N (k frames, the next line 191,
;                  when it took more); flip the pages now. C = 1: no sync
;                  (the first one failed). The estimate may be off by up
;                  to half a frame (+-8,515 cycles at 1 MHz NTSC): a fixed
;                  cost per state of the program does, plus terms for what
;                  varies a lot (a sound, a screen cleared). The frame
;                  being counted in polls by vapor_pace_init, PAL (20,280
;                  cycles) and accelerated machines need no other estimate.
;                  Clobbers A, X, Y. (.ifref; 8 B of BSS)
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
; 191 lands on byte 0-14 (at most 15 cycles) and the second on 9-23, still in
; it; on lines 255 and 261 only bytes 16-23 are marked, and the second read
; falls past them. One lock a frame, on line 191, within one poll. (Ordinary
; polls take 13 cycles. At a counter rollover a separate sample
; splits the gap into 12 and 15 cycles, still within the 15 possible first
; read positions. A 17-cycle gap can miss the marker.)
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

.if .referenced(vapor_sync) .or .referenced(vapor_count) .or .referenced(vapor_pace) .or .referenced(vapor_pace_init)
.segment "CODE"
vapor_sync:
        LDX     #0              ; Y:X counts the polls down from 65536
        LDY     #0
@out:   LDA     TXTCLR          ; first leave the marker (called right after
        CMP     #VAPOR_BYTE     ; a sync, the beam may still be on it)
        BNE     vapor_sync_in
        DEX
        BNE     @out
        DEY
        BNE     @out
        SEC
        RTS
vapor_sync_in:                  ; (vapor_pace, X = Y = 0: the beam may be on it)
@in:    LDA     TXTCLR          ; 13 cycles a poll
        CMP     #VAPOR_BYTE
        BEQ     @hit
@next:  DEX
        BNE     @in
        ; Sample before rolling the high counter. The old DEY/BNE tail
        ; left a 17-cycle gap once per 256 polls: arriving near the end
        ; of the marker could then miss its second confirming read.
        LDA     TXTCLR
        CMP     #VAPOR_BYTE
        BEQ     @hit_wrap
@next_wrap:
        DEX
        DEY
        BNE     @in
        SEC
        RTS
@hit:   LDA     TXTCLR          ; 9 cycles later, the second read must see it too
        CMP     #VAPOR_BYTE
        BNE     @next
        CLC
        RTS
@hit_wrap:
        LDA     TXTCLR          ; same 9-cycle confirmation as the normal path
        CMP     #VAPOR_BYTE
        BNE     @next_wrap
        DEY                     ; account for the previous low-counter wrap
        CLC
        RTS
.if .referenced(vapor_pace)
.assert >vapor_sync_in = >@hit, lderror, "vapor.asm: the poll loop crosses a page (14-cycle polls: vapor_pace's estimate is in 13)"
.endif
.endif

.if .referenced(vapor_count) .or .referenced(vapor_pace_init)
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

.if .referenced(vapor_mark_both)
.segment "CODE"
vapor_mark_both:
        LDA     #VAPOR_BYTE
        LDX     #VAPOR_LEN-1
@lp:    STA     $3FD0,X         ; HGR line 191 of page 1
        STA     $5FD0,X         ; and of page 2
        DEX
        BPL     @lp
        RTS
.endif

.if .referenced(vapor_pace) .or .referenced(vapor_pace_init)
.segment "BSS"
vp_frame: .res 2                ; polls a frame (vapor_count)
vp_half:  .res 2                ; half of it (the rounding)
vp_sum:   .res 2                ; vapor_pace: the estimate + the polls
vp_n:     .res 1                ; N
vp_t:     .res 1
.segment "CODE"
vapor_pace_init:
        JSR     vapor_count
        BCS     @rts
        STA     vp_frame
        STX     vp_frame+1
        STX     vp_half+1
        LSR     vp_half+1
        ROR     A
        STA     vp_half
        CLC
@rts:   RTS

vapor_pace:
        STA     vp_n
        STX     vp_sum
        STY     vp_sum+1
        LDX     #0              ; the first wait: the beam may be on line
        LDY     #0              ; 191 now (vapor_sync would let it go)
        JSR     vapor_sync_in
        BCS     @rts
        BCC     @add
@sync:  JSR     vapor_sync      ; the next line 191
        BCS     @rts
        BCC     @add            ; (5 cycles on both paths: the same phase)
@add:
        TXA                     ; + its polls: -X, -Y, each byte negated
        EOR     #$FF            ; on its own (vapor_count)
        CLC
        ADC     #1
        CLC
        ADC     vp_sum
        STA     vp_sum
        TYA
        EOR     #$FF            ; ~Y + C, then + 1
        ADC     vp_sum+1
        STA     vp_sum+1
        INC     vp_sum+1
        SEC                     ; k = round(sum / frame), at least 1:
        LDA     vp_sum          ; t = sum - frame / 2, then k = 1 + the
        SBC     vp_half         ; frames t holds, counted up to N only
        TAY                     ; (Y = t low, A = t high)
        LDA     vp_sum+1
        SBC     vp_half+1
        LDX     #1
        BCC     @test           ; (t < 0: k = 1)
@more:  CPX     vp_n
        BCS     @done           ; k >= N: the tick's last frame
        STA     vp_t
        TYA
        SEC
        SBC     vp_frame
        TAY
        LDA     vp_t
        SBC     vp_frame+1
        BCC     @test
        INX
        BCS     @more
@test:  CPX     vp_n            ; k < N: wait for one more
        BCC     @sync
@done:  CLC                     ; (the same path after the last sync
@rts:   RTS                     ; whichever it was: a constant phase)
.endif
