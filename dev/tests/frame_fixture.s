; VERHILLE Arnaud — GPL-3.0. Cadence timing and IRQ-mask fixture.
.export _main, _frame_begin, _frame_end
.import _a2_frame_init, _a2_frame_wait, _a2_frame_mode, _a2_frame_set_delay
.segment "CODE"
_main:
        jsr _a2_frame_init
        sta $1000
        sei
        jsr measure
        lda #10
        jsr _a2_frame_set_delay
        jsr measure
        lda #0
        jsr _a2_frame_set_delay
        jsr measure
        cli
        jsr measure
@done:  jmp @done
measure:
        jsr _frame_begin
        jsr _a2_frame_wait
        sta $1001
        php
        pla
        and #$04
        sta $1002
        jsr _frame_end
        rts
_frame_begin: rts
_frame_end: rts
