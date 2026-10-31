; WARGALAGA II -- video clock and page presentation (HGR).
; //e enhanced: the VBL edge of $C019 (bit 7 clear in the blank), polled.
; //c: the VBL interrupt of the built-in mouse firmware (mode 9), served by a
; ProDOS ALLOC_INTERRUPT handler: a time source only, the mouse is never read.
; Anything else: Monitor WAIT delays (a2_frame_wait).
; A page is shown once per two refreshes (30 Hz NTSC / 25 Hz PAL). The game
; counts refreshes between flips (timing_refreshes) and advances its logic by
; refresh pairs, so the speed never depends on the drawing time.
; The clock is dev/lib/apple2c/apple2vbl.s (_a2_vbl_mode: 0 delay, 1 //e
; VBL polling, 2 //c VBL IRQ; _a2_vbl_count, refreshes seen), assembled with
; A2_VBL_SCAN_SEI=1: the music interrupt scans too (see _a2_vbl_scan below).
; The IRQ hook (flip_irq) uses neither cc65's zero page nor its stack.
.setcpu "65C02"
.import _a2_frame_wait, _a2_frame_set_delay
.import spk_period, mus_ticks
.import _mouse_init, _mouse_close
.import _a2_vbl_init, _a2_vbl_irq_init, _a2_vbl_close, _a2_vbl_scan
.import _a2_vbl_mode, _a2_vbl_count, _a2_vbl_beam, _a2_vbl_hook
.export timing_init, timing_close, timing_present
JOY_CENTRE = 83
.export timing_refreshes, late_count, joy_x, joy_mode

.bss
flip_count: .res 1              ; _a2_vbl_count at the last flip
last_flip: .res 1               ; flip_count of the flip before
timing_refreshes: .res 1        ; refreshes between the last two flips
late_count: .res 2              ; frames presented after their deadline
ready: .res 1                   ; //c: bit 7 = a page waits for the IRQ
wanted: .res 1                  ; page to show: 0 = page 1, 1 = page 2
joy_mode: .res 1                ; nonzero: read paddle 0 while waiting
from: .res 1
spk_cnt: .res 1                 ; turns to the next speaker toggle
joy_irq: .res 1                 ; mus_ticks when the paddle count started
.data
joy_x: .byte JOY_CENTRE         ; paddle 0 count (0..~165), centre until read

; Linked first after crt0 (game.cfg TIMING): the wait loops below stay where
; they are whatever the game's code grows to (a page crossed costs a cycle).
.segment "TIMING"
; Select the clock. //e: VBL polling. Otherwise a mouse firmware (the //c's
; built-in one) gives the VBL interrupt; without one, delays.
timing_init:
        stz ready
        lda #<flip_irq
        sta _a2_vbl_hook
        lda #>flip_irq
        sta _a2_vbl_hook+1
        jsr _a2_vbl_init
        pha
        lda #DELAY               ; fallback: one WAIT a frame (see present_delay)
        jsr _a2_frame_set_delay
        pla
        bne synced
        jsr _mouse_init
        jsr _a2_vbl_irq_init
synced: lda _a2_vbl_count
        sta flip_count
        sta last_flip
        rts

timing_close:
        jsr _a2_vbl_close
        stz ready
        jmp _mouse_close

; _a2_vbl_scan counts the //e VBL edges. Call it at most ~4 000 cycles
; apart while drawing (the blank lasts ~4 550): no edge is then missed;
; 33 cycles with the JSR when nothing changed. The music interrupt (sound.s,
; a PT3 tick of up to ~3 000 cycles) scans too, on entry and on exit: an
; edge seen there is read again under SEI (A2_VBL_SCAN_SEI), or an
; interrupt between the read and the store would count it twice. (SEI on
; every scan cost 9 cycles a call: ~2 % more late frames, and longer
; speaker turns; bug hunt 6.)

; Show the page just drawn (A = 0: page 1, 1: page 2) at the first blank at
; least two refreshes after the previous flip; a late frame goes out at the
; next blank (late_count). Sets timing_refreshes. Clobbers A, X, Y.
timing_present:
        sta wanted
        lda _a2_vbl_mode
        cmp #2
        beq present_irq
        cmp #1
        bne present_delay
        jsr _a2_vbl_scan
        lda _a2_vbl_count
        sec
        sbc flip_count
        cmp #2
        bcc early
        jsr late
        jsr next_edge
        bcs present_delay
        bra show
early:  cmp #1
        beq last_refresh
        jsr next_edge
        bcs present_delay
last_refresh:
        jsr joy_read_vbl
        jsr next_edge
        bcs present_delay
show:   ldx wanted
        lda $C054,x
        lda _a2_vbl_count
        sta flip_count
shown:  sec
        sbc last_flip
        sta timing_refreshes
        lda flip_count
        sta last_flip
        rts

; No video clock: one WAIT, after a frame's drawing and logic (~24 000
; cycles), stands for the rest of two refreshes (34 060). WAIT(60) is ~9 800
; cycles: the game keeps ~its speed (two WAIT(80), ~34 000 on top of the
; drawing, made it run at ~57 %, bug hunt 2026-10-23).
DELAY = 60
present_delay:
        jsr joy_read_delay       ; (the stick was dead here, bug hunt 5)
        jsr _a2_frame_wait
        ldx wanted
        lda $C054,x
        lda _a2_vbl_count
        clc
        adc #2
        sta _a2_vbl_count
        sta flip_count
        bra shown

; //c: the interrupt shows the page; read the stick until it has.
present_irq:
        lda _a2_vbl_count
        sec
        sbc flip_count
        cmp #2
        bcc :+
        jsr late
:       lda #$80
        sta ready
        jsr joy_read_irq
        lda spk_period
        sta spk_cnt
        ldx #0
        ldy #>WAIT_TURNS
wait_irq:
        bit ready                ; 6
        bpl irq_shown
        jsr spk_pad              ; 37: the //e turn's length
        lda spk_period           ; 15 (silent: 7)
        beq wi_count
        dec spk_cnt
        bne wi_count
        sta spk_cnt
        sta $C030
wi_count:
        dex                      ; 5
        bne wait_irq
        dey
        bne wait_irq
        jsr timing_close         ; the interrupt stopped: fall back to delays
        bra present_delay
irq_shown:
        lda flip_count
        bra shown

; Wait for the next //e VBL edge, toggling the speaker every spk_period
; turns (sound.s's effects: they only sound in this spare time, never
; delaying a frame). A turn is SPK_TURN cycles (sound.inc), as in the //c
; loop below. C = 1 (and delays from now on) if no edge comes within
; WAIT_TURNS turns (~0.5 s; a refresh is ~270 turns).
WAIT_TURNS = 8192               ; (a multiple of 256: X counts the low byte)
next_edge:
        lda _a2_vbl_count
        sta from
        lda spk_period
        sta spk_cnt
        ldx #0
        ldy #>WAIT_TURNS
ne_turn:
        jsr _a2_vbl_scan          ; 33 (no edge)
        lda _a2_vbl_count            ; 10
        cmp from
        bne ne_edge
        lda spk_period           ; 15 (silent: 7)
        beq ne_count
        dec spk_cnt
        bne ne_count
        sta spk_cnt
        sta $C030                ; a store: one toggle, seen by storewatch
ne_count:
        dex                      ; 5
        bne ne_turn
        dey
        bne ne_turn
        stz _a2_vbl_mode
        sec
        rts
ne_edge:
        clc
        rts
; (a branch across a page costs a cycle: every turn 2 cycles long, every
; effect flat; 2026-10-30, code grown under these loops)
.assert >wait_irq = >(wi_count + 3), error, "the //c wait loop crosses a page"
.assert >ne_turn = >(ne_count + 3), error, "the //e wait loop crosses a page"

spk_pad:                         ; 12 + 25 cycles (_a2_vbl_scan's 33, less
        bit $00                  ; bit ready's 6, plus the 10 after it)
.repeat 11
        nop
.endrepeat
        rts

late:   inc late_count
        bne :+
        inc late_count+1
:       rts

; IRQ hook (//c, after the count): show the page waiting, two refreshes
; or more after the previous flip.
flip_irq:
        bit ready
        bpl claimed
        lda _a2_vbl_count
        sec
        sbc flip_count
        cmp #2
        bcc claimed
        ldx wanted
        lda $C054,x
        lda _a2_vbl_count
        sta flip_count
        stz ready
claimed:
        rts

; Paddle 0 in the time left before the flip: 17 cycles a count, ~165 for a
; full turn. Stops at the deadline (the blank on the //e, the flip on the
; //c) or after 255 counts (no stick: the timer never ends; without that
; bound a //c whose interrupt stopped spun here forever, bug hunt
; 2026-10-23); an unfinished read keeps the previous value, so the frame
; rate never depends on the stick.
joy_read_vbl:
        lda joy_mode
        beq joy_done
        ldx #0                   ; still in the blank of the first refresh:
:       jsr _a2_vbl_scan          ; wait for the picture (bounded)
        bit _a2_vbl_beam
        bmi :+
        dex
        bne :-
        rts
:       jsr joy_start
:       bit $C019
        bpl joy_done
        inx
        beq joy_done
        lda $C064
        bmi :-
joy_store:                       ; a music interrupt during the count stopped
        lda mus_ticks            ; X, not the paddle timer: reading too low
        cmp joy_irq              ; (bug hunt 5), dropped
        bne joy_done
        stx joy_x
joy_done:
        rts
; No clock to stop at: the full count (at most 255 x 17 cycles).
joy_read_delay:
        lda joy_mode
        beq joy_done
        jsr joy_start
:       nop                      ; 6: the other loops' bit/branch (17 a
        nop                      ; count, the scale game.s expects)
        nop
        inx
        beq joy_done
        lda $C064
        bmi :-
        bra joy_store
joy_start:
        lda mus_ticks
        sta joy_irq
        ldx #0
        lda $C070
        rts
joy_read_irq:
        lda joy_mode
        beq joy_done
        jsr joy_start
:       bit ready
        bpl joy_done
        inx
        beq joy_done
        lda $C064
        bmi :-
        bra joy_store
