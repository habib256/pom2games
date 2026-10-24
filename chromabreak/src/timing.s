; Game presentation on the video clock of dev/lib/apple2c/apple2vbl.s: live
; VBL edge polling on IIe, native mouse VBL IRQ on IIc (the flip is the IRQ
; hook below). Present once per two video refreshes (30 Hz NTSC / 25 Hz PAL).
; IRQ handler uses neither cc65's stack nor zero page; mouse ROM remains active.
.setcpu "65C02"
.import _a2_frame_wait, _dhgr_flip
.import _dhgr_base, _dhgr_display
.import _a2_vbl_init, _a2_vbl_irq_init, _a2_vbl_close, _a2_vbl_scan
.import _a2_vbl_mode, _a2_vbl_count, _a2_vbl_beam, _a2_vbl_hook
.export _timing_init, _timing_close, _timing_present
.export _joy_x, _joy_y
; The DHGR small text calls it between characters (DHGR_SMALL_USE_PROGRESS).
.export _dhgr_small_progress := _a2_vbl_scan
.import _mode
.bss
flipped: .res 1                 ; a2_vbl_count at the last //e flip
ready: .res 1
phase: .res 1
wanted: .res 1
previous: .res 1
.data
; Paddle 0 / stick X as the paddle centre (8..130), paddle 1 / stick Y as
; its top row (100..183); mid-field until read.
_joy_x: .byte 69
_joy_y: .byte 142
.code
_timing_init:
        lda _a2_vbl_count
        sta flipped
        stz ready
        stz phase
        lda #<flip_irq
        sta _a2_vbl_hook
        lda #>flip_irq
        sta _a2_vbl_hook+1
        jsr _a2_vbl_init
        bne :+
        jmp _a2_vbl_irq_init
:       rts
; IRQ hook (//c): every other refresh, show the page waiting.
flip_irq:
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
        rts
_timing_present:
        lda _a2_vbl_mode
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
        jsr _a2_vbl_scan
        lda _a2_vbl_mode
        cmp #1
        bne fallback
        jsr edges                ; already late: no paddle read
        cmp #2
        bcs :+
        lda #<$C019              ; stop at vertical blank (bit 7 clear)
        ldx #>$C019
        jsr joy_read
:
        ; A long level build may end near the trailing edge of VBL.
        ; If both deadlines already passed, synchronize to a fresh blank.
        jsr edges
        cmp #2
        bcc fresh_poll
wait_active:
        bit $C019
        bpl wait_active
fresh_poll:
        ldx #0
        ldy #0
poll_clock:
        jsr _a2_vbl_scan
        jsr edges
        cmp #2
        bcc poll_more
        bit $C019
        bpl flip_poll
poll_more:
        dex
        bne poll_clock
        dey
        bne poll_clock
        stz _a2_vbl_mode
        bra fallback
flip_poll:
        php
        sei
        bit $C019
        bmi flip_retry
        lda _a2_vbl_count
        sta flipped
        stz _a2_vbl_beam
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
        stz ready
        jmp _a2_vbl_close
; //e: refreshes since the last flip.
edges:  lda _a2_vbl_count
        sec
        sbc flipped
        rts
