; WARGALAGA II -- video clock and page presentation (HGR).
; //e enhanced: the VBL edge of $C019 (bit 7 clear in the blank), polled.
; //c: the VBL interrupt of the built-in mouse firmware (mode 9), served by a
; ProDOS ALLOC_INTERRUPT handler: a time source only, the mouse is never read.
; Anything else: Monitor WAIT delays (a2_frame_wait).
; A page is shown once per two refreshes (30 Hz NTSC / 25 Hz PAL). The game
; counts refreshes between flips (timing_refreshes) and advances its logic by
; refresh pairs, so the speed never depends on the drawing time.
; Derived from chromabreak/src/timing.s (DHGR); candidate for dev/lib/apple2c.
; The IRQ handler uses neither cc65's zero page nor its stack.
.setcpu "65C02"
.import _a2_frame_init, _a2_frame_wait
.import _mouse_init, _mouse_close, _mouse_timing_mode, _mouse_serve_irq, _mouse_slot
.export timing_init, timing_close, timing_present, timing_scan
.export timing_mode, timing_refreshes, vbl_count, late_count, joy_x, joy_mode

.bss
timing_mode: .res 1             ; 0 delay, 1 //e VBL polling, 2 //c VBL IRQ
vbl_count: .res 1               ; refreshes seen
flip_count: .res 1              ; vbl_count at the last flip
last_flip: .res 1               ; flip_count of the flip before
timing_refreshes: .res 1        ; refreshes between the last two flips
beam: .res 1                    ; last $C019 bit 7 (//e)
late_count: .res 2              ; frames presented after their deadline
ready: .res 1                   ; //c: bit 7 = a page waits for the IRQ
wanted: .res 1                  ; page to show: 0 = page 1, 1 = page 2
joy_mode: .res 1                ; nonzero: read paddle 0 while waiting
from: .res 1
.data
joy_x: .byte 94                 ; paddle 0 count (0..~188), centre until read
allocate: .byte 2,0
        .word vbl_irq
release: .byte 1,0

.code
; Select the clock. //e: VBL polling. Otherwise a mouse firmware (the //c's
; built-in one) gives the VBL interrupt; without one, delays.
timing_init:
        stz ready
        jsr _a2_frame_init
        cmp #1
        bne irq
        sta timing_mode
        lda $C019
        and #$80
        sta beam
        bra synced
irq:    stz timing_mode
        jsr _mouse_init
        lda _mouse_slot
        beq synced
        php
        sei
        jsr $BF00
        .byte $40                ; ALLOC_INTERRUPT
        .word allocate
        bcs failed
        lda allocate+1
        sta release+1
        lda #2
        sta timing_mode
        lda #9                   ; mouse firmware: VBL interrupts
        jsr _mouse_timing_mode
        plp
        cli
        bra synced
failed: plp
synced: lda vbl_count
        sta flip_count
        sta last_flip
        rts

timing_close:
        lda timing_mode
        cmp #2
        bne closed
        php
        sei
        lda #1
        jsr _mouse_timing_mode
        jsr $BF00
        .byte $41                ; DEALLOC_INTERRUPT
        .word release
        plp
closed: stz timing_mode
        stz ready
        jmp _mouse_close

; Count //e VBL edges. Call at most ~4 000 cycles apart while drawing (the
; blank lasts ~4 550): no edge is then missed. ~25 cycles; A clobbered.
timing_scan:
        lda timing_mode
        cmp #1
        bne scanned
        lda $C019
        and #$80
        cmp beam
        beq scanned
        sta beam
        cmp #$80
        beq scanned              ; blank -> picture: nothing
        inc vbl_count
scanned:
        rts

; Show the page just drawn (A = 0: page 1, 1: page 2) at the first blank at
; least two refreshes after the previous flip; a late frame goes out at the
; next blank (late_count). Sets timing_refreshes. Clobbers A, X, Y.
timing_present:
        sta wanted
        lda timing_mode
        cmp #2
        beq present_irq
        cmp #1
        bne present_delay
        jsr timing_scan
        lda vbl_count
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
        lda vbl_count
        sta flip_count
shown:  sec
        sbc last_flip
        sta timing_refreshes
        lda flip_count
        sta last_flip
        rts

; No video clock: two WAIT delays stand for two refreshes.
present_delay:
        jsr _a2_frame_wait
        jsr _a2_frame_wait
        ldx wanted
        lda $C054,x
        lda vbl_count
        clc
        adc #2
        sta vbl_count
        sta flip_count
        bra shown

; //c: the interrupt shows the page; read the stick until it has.
present_irq:
        lda vbl_count
        sec
        sbc flip_count
        cmp #2
        bcc :+
        jsr late
:       lda #$80
        sta ready
        jsr joy_read_irq
        ldx #0
        ldy #0
wait_irq:
        bit ready
        bpl irq_shown
        dex
        bne wait_irq
        dey
        bne wait_irq
        jsr timing_close         ; the interrupt stopped: fall back to delays
        bra present_delay
irq_shown:
        lda flip_count
        bra shown

late:   inc late_count
        bne :+
        inc late_count+1
:       rts

; Wait for the next //e VBL edge. C = 1 (and delays from now on) if none
; comes within ~2.5 s.
next_edge:
        lda vbl_count
        sta from
        ldx #0
        ldy #0
:       jsr timing_scan
        lda vbl_count
        cmp from
        bne :+
        dex
        bne :-
        dey
        bne :-
        stz timing_mode
        sec
        rts
:       clc
        rts

; ProDOS interrupt handler: C = 0 if it was the mouse firmware's VBL.
vbl_irq:
        cld
        jsr _mouse_serve_irq
        bcs not_ours
        inc vbl_count
        bit ready
        bpl claimed
        lda vbl_count
        sec
        sbc flip_count
        cmp #2
        bcc claimed
        ldx wanted
        lda $C054,x
        lda vbl_count
        sta flip_count
        stz ready
claimed:
        clc
        rts
not_ours:
        sec
        rts

; Paddle 0 in the time left before the flip: 15 cycles a count, ~188 for a
; full turn. Stops at the deadline (the blank on the //e, the flip on the
; //c); an unfinished read keeps the previous value, so the frame rate never
; depends on the stick.
joy_read_vbl:
        lda joy_mode
        beq joy_done
        ldx #0                   ; still in the blank of the first refresh:
:       jsr timing_scan          ; wait for the picture (bounded)
        bit beam
        bmi :+
        dex
        bne :-
        rts
:       ldx #0
        lda $C070
:       bit $C019
        bpl joy_done
        inx
        lda $C064
        bmi :-
        stx joy_x
joy_done:
        rts
joy_read_irq:
        lda joy_mode
        beq joy_done
        ldx #0
        lda $C070
:       bit ready
        bpl joy_done
        inx
        lda $C064
        bmi :-
        stx joy_x
        rts
