; Game presentation: live VBL edge polling on IIe, native mouse VBL IRQ on IIc.
; Present once per two video refreshes (30 Hz NTSC / 25 Hz PAL).
; IRQ handler uses neither cc65's stack nor zero page; mouse ROM remains active.
.setcpu "65C02"
.import _a2_frame_init, _a2_frame_wait, _a2_frame_mode, _dhgr_flip
.import _dhgr_base, _dhgr_display
.import _mouse_timing_mode, _mouse_serve_irq, _mouse_slot
.export _timing_init, _timing_close, _timing_present, _timing_mode, _timing_ticks, _timing_scan
.export _joy_x, _joy_y
.import _mode
.bss
_timing_mode: .res 1
_timing_ticks: .res 1
beam: .res 1
edges: .res 1
ready: .res 1
phase: .res 1
wanted: .res 1
previous: .res 1
.data
; Paddle 0 / stick X as the paddle centre (8..130), paddle 1 / stick Y as
; its top row (100..183); mid-field until read.
_joy_x: .byte 69
_joy_y: .byte 142
.data
allocate: .byte 2,0
          .word vbl_irq
release: .byte 1,0
.code
_timing_init:
        stz edges
        stz ready
        stz phase
        jsr _a2_frame_init
        cmp #1
        bne :+
        sta _timing_mode
        lda $C019
        and #$80
        sta beam
        rts
:       lda _mouse_slot
        beq done
        php
        sei
        jsr $BF00
        .byte $40
        .word allocate
        bcs failed
        lda allocate+1
        sta release+1
        lda #2
        sta _timing_mode
        lda #9
        jsr _mouse_timing_mode
        plp
        cli
        rts
failed: plp
done:   rts
vbl_irq:
        cld
        jsr _mouse_serve_irq
        bcs unclaimed
        inc _timing_ticks
        lda phase
        eor #1
        sta phase
        bne claimed
        lda ready
        beq claimed
        lda wanted
        cmp #1
        bne page_two
        bit $C054
        bra shown
page_two:
        bit $C055
shown:  sta _dhgr_display
        stz ready
claimed:
        clc
        rts
unclaimed:
        sec
        rts
_timing_present:
        lda _timing_mode
        cmp #2
        bne polling
        lda _dhgr_display
        sta previous
        lda #1
        ldx _dhgr_base
        cpx #$40
        bne :+
        lda #2
:       sta wanted
        lda #$80                 ; bit 7: joy_read stops when the IRQ clears it
        sta ready
        lda #<ready
        ldx #>ready
        jsr joy_read
        ldx #0
        ldy #0
wait_irq:
        lda ready
        beq presented
        dex
        bne wait_irq
        dey
        bne wait_irq
        ; Bounded fallback if an IRQ source disappears.
        jsr _timing_close
polling:
        jsr _timing_scan
        lda _timing_mode
        cmp #1
        bne fallback
        lda edges                ; already late: no paddle read
        cmp #2
        bcs :+
        lda #<$C019              ; stop at vertical blank (bit 7 clear)
        ldx #>$C019
        jsr joy_read
:
        ; A long level build may end near the trailing edge of VBL.
        ; If both deadlines already passed, synchronize to a fresh blank.
        lda edges
        cmp #2
        bcc fresh_poll
wait_active:
        bit $C019
        bpl wait_active
fresh_poll:
        ldx #0
        ldy #0
poll_clock:
        jsr _timing_scan
        lda edges
        cmp #2
        bcc poll_more
        bit $C019
        bpl flip_poll
poll_more:
        dex
        bne poll_clock
        dey
        bne poll_clock
        stz _timing_mode
        bra fallback
flip_poll:
        php
        sei
        bit $C019
        bmi flip_retry
        stz edges
        stz beam
        jsr _dhgr_flip
        plp
        rts
flip_retry:
        plp
        jmp poll_clock
fallback:
        lda #<joy_always
        ldx #>joy_always
        jsr joy_read
        jsr _a2_frame_wait
        jsr _a2_frame_wait
        jmp _dhgr_flip
presented:
        lda #$20
        ldx previous
        cpx #2
        bne :+
        lda #$40
:       sta _dhgr_base
        rts
; Joystick/paddles, read in the time left before presentation. Both RC
; timers start together; each loop takes 23 cycles, one count per two
; paddle units (255 = 122 counts). A/X = a byte whose bit 7 clears when the
; wait is over (VBL on the //e, the flip IRQ on the //c): the read stops
; there and an axis not finished keeps its previous value, so the frame
; rate never depends on the stick. On the //c, $C070 also acknowledges a
; VBL interrupt: one arriving during that very access is lost and that
; frame shows one refresh late.
joy_always: .byte $80
joy_read:
        ldy _mode                ; 2 = joystick/paddles
        cpy #2
        bne joy_done
        sta joy_a+1
        sta joy_x+1
        sta joy_y+1
        stx joy_a+2
        stx joy_x+2
        stx joy_y+2
        ldx #$FF                 ; first pass counts 0
        lda $C070
joy_a:  bit $C019                ; both timers running
        bpl joy_done
        inx
        lda $C064
        bpl joy_x_low
        lda $C065
        bpl joy_y_low
        bra joy_a
joy_x_low:
        jsr joy_store_x
joy_y:  bit $C019                ; only Y still running
        bpl joy_done
        inx
        nop
        nop
        nop
        nop
        lda $C065
        bmi joy_y
        bra joy_store_y
joy_y_low:
        jsr joy_store_y
joy_x:  bit $C019                ; only X still running
        bpl joy_done
        inx
        nop
        nop
        nop
        nop
        lda $C064
        bmi joy_x
joy_store_x:                     ; centre = 8 + count
        txa
        clc
        adc #8
        sta _joy_x
joy_done:
        rts
joy_store_y:                     ; top = 100 + count * 11/16
        txa
        lsr
        sta _joy_y
        lsr
        lsr
        pha
        lsr
        clc
        adc _joy_y
        sta _joy_y
        pla
        adc _joy_y
        adc #100
        sta _joy_y
        rts
_timing_close:
        lda _timing_mode
        cmp #2
        beq :+
        stz _timing_mode
        rts
:
        php
        sei
        lda #1
        jsr _mouse_timing_mode
        jsr $BF00
        .byte $41
        .word release
        stz _timing_mode
        stz ready
        plp
        rts

; Called between bounded work chunks (sprites, paddle rows, ball substeps),
; never more than ~2000 cycles apart, well inside one vertical blank.
; Counts live IIe VBL edges during rendering, so short/long frames share
; the same two-refresh deadline. Native IIc uses its IRQ clock instead.
.export _dhgr_small_progress
_dhgr_small_progress:
_timing_scan:
        lda _timing_mode
        cmp #1
        bne scan_done
        lda $C019
        and #$80
        cmp beam
        beq scan_done
        sta beam
        cmp #0
        bne scan_done
        inc edges
        inc _timing_ticks
scan_done:
        rts

; Detect a 50 Hz machine: count a fixed 16-cycle loop over one video frame,
; about 1064 turns at 60 Hz and 1267 at 50 Hz. Every wait is bounded; with
; no usable clock the machine is taken as 60 Hz.
.export _timing_measure, _video_pal
.bss
_video_pal: .res 1
turns: .res 2
.code
_timing_measure:
        stz _video_pal
        stz turns
        stz turns+1
        lda _timing_mode
        beq measured
        cmp #2
        beq measure_irq
        ; IIe: from one falling edge of $C019 bit 7 to the next.
:       jsr bounded
        bcs measured
        bit $C019
        bpl :-
:       jsr bounded
        bcs measured
        bit $C019
        bmi :-
        stz turns
        stz turns+1
count_high:
        inc turns
        bne :+
        jsr overflow
        bcs measured
:       bit $C019
        bpl count_high
count_low:
        inc turns
        bne :+
        jsr overflow
        bcs measured
:       bit $C019
        bmi count_low
        bra judge
measure_irq:
        ; IIc: between two VBL interrupts.
        ldx _timing_ticks
:       jsr bounded
        bcs measured
        cpx _timing_ticks
        beq :-
        ldx _timing_ticks
        stz turns
        stz turns+1
count_irq:
        inc turns
        bne :+
        jsr overflow
        bcs measured
:       cpx _timing_ticks
        beq count_irq
judge:  lda turns+1
        cmp #>1166
        bne :+
        lda turns
        cmp #<1166
:       bcc measured
        inc _video_pal
measured:
        rts
; Waits before counting: give up after 65536 turns.
bounded:
        inc turns
        bne :+
        inc turns+1
        bne :+
        sec
        rts
:       clc
        rts
; Counting: past 2048 turns no video clock is running.
overflow:
        inc turns+1
        lda turns+1
        cmp #8
        rts
