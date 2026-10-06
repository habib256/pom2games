; Game presentation: live VBL edge polling on IIe, native mouse VBL IRQ on IIc.
; Present once per two video refreshes (30 Hz NTSC / 25 Hz PAL).
; IRQ handler uses neither cc65's stack nor zero page; mouse ROM remains active.
.setcpu "65C02"
.import _a2_frame_init, _a2_frame_wait, _a2_frame_mode, _dhgr_flip
.import _dhgr_base, _dhgr_display
.import _mouse_timing_mode, _mouse_serve_irq, _mouse_slot
.export _timing_init, _timing_close, _timing_present, _timing_mode, _timing_ticks, _timing_scan
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
        lda #1
        sta ready
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

; Called between bounded work chunks and once per renderer scanline.
; Counts live IIe VBL edges during rendering, so short/long frames share
; the same two-refresh deadline. Native IIc uses its IRQ clock instead.
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
