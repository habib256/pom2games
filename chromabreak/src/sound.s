.setcpu "65C02"
; Apple II one-bit speaker. Bounded bursts leave the mouse ROM IRQ enabled.
; No ROM WAIT or zero-page workspace. Each burst ends at its original polarity.
.export _sound_event, _sound_tick, _sound_stop
.import _timing_scan
.bss
_sound_active: .res 1
.export _sound_active
remaining: .res 1
elapsed: .res 1
pitch: .res 1
.rodata
periods: .byte 0,35,24,15,29,21,30,34,28,32,30,30
lengths: .byte 0,2,3,3,3,5,5,9,10,12,12,18
.code
_sound_event:
        cmp _sound_active
        bcc done
        sta _sound_active
        tax
        lda lengths,x
        sta remaining
        stz elapsed
 done:  rts
_sound_stop:
        stz _sound_active
        stz remaining
        rts
_sound_tick:
        ldx _sound_active
        beq done
        lda periods,x
        ; Falling loss tone; rising launch/bonus and ascending level arpeggios.
        cpx #10
        beq falling
        cpx #6
        bcc pitched
        sec
        sbc elapsed
        bra pitched
falling:
        clc
        adc elapsed
pitched:
        sta pitch
        ldy #8                   ; four cycles for impacts, launch and menu cues
        cpx #10
        bne pulse
        ldy #4                   ; two cycles for the long falling loss cue
pulse:
        jsr _timing_scan          ; low tones can span a whole vertical blank
        bit $C030
        ldx pitch
half_period:
        dex
        bne half_period
        dey
        bne pulse
        inc elapsed
        dec remaining
        bne done
        stz _sound_active
        rts
