; VERHILLE Arnaud — GPL-3.0. Deadline cadence driven by application refresh IRQ.
; Main RAM/ZP, D=0; caller owns the IRQ source. No vectors/banks installed.
; tick: single producer (IRQ), preserves A/X/Y, alters NZ only.
; init/wait: main thread only, preserve caller I, destroy A/X/Y and flags.
.export _a2_cadence_tick, _a2_cadence_ticks, _a2_cadence_missed
.export _a2_cadence_init, _a2_cadence_wait
.bss
_a2_cadence_ticks: .res 2
_a2_cadence_missed: .res 2
period: .res 1
early: .res 1
active: .res 1
deadline: .res 2
now: .res 2
misses: .res 2
watchdog: .res 2
quotient: .res 2
remainder: .res 1
.code
_a2_cadence_tick:
        inc _a2_cadence_ticks
        bne tick_done
        inc _a2_cadence_ticks+1
tick_done:
        rts
snapshot:
        php
        sei
        lda _a2_cadence_ticks
        sta now
        lda _a2_cadence_ticks+1
        sta now+1
        plp
        rts
; fastcall A=1..8 refreshes; invalid input preserves the previous schedule.
_a2_cadence_init:
        cmp #1
        bcc invalid
        cmp #9
        bcs invalid
        sta period
        jsr snapshot
        clc
        lda now
        adc period
        sta deadline
        lda now+1
        adc #0
        sta deadline+1
        lda #0
        sta _a2_cadence_missed
        sta _a2_cadence_missed+1
        lda #1
        sta active
        ldx #0
        rts
invalid:
        lda #0
        tax
        rts
advance:
        clc
        lda deadline
        adc period
        sta deadline
        bcc advanced
        inc deadline+1
advanced:
        rts
; Return missed presentation deadlines this call (A/X), $FFFF on stopped clock.
; If late, skip that deadline and wait for the next original-grid boundary.
; Never present a burst of catch-up frames. Work must resume within 32767 ticks.
_a2_cadence_wait:
        lda active
        bne started
        jmp timeout
started:
        lda #0
        sta early
        sta misses
        sta misses+1
        sta watchdog
        lda #$10             ; 4096 polls, finite even with disabled/stopped IRQ
        sta watchdog+1
poll:
        jsr snapshot
        sec
        lda now
        sbc deadline
        tay
        lda now+1
        sbc deadline+1
        sta quotient+1
        bmi before
        bne overdue
        tya
        bne overdue
        lda early
        beq overdue
        jsr advance
        lda misses
        ldx misses+1
        rts
before:
        lda #1
        sta early
count_poll:
        lda watchdog
        bne decrement
        dec watchdog+1
decrement:
        dec watchdog
        lda watchdog
        ora watchdog+1
        bne poll
        beq timeout
overdue:
        ; quotient high/Y = now-deadline (modulo 65536, <32768).
        ; Divide in exactly 16 steps, independent of the pause duration.
        sty quotient
        lda #0
        sta early
        sta remainder
        ldx #16
divide:
        asl quotient
        rol quotient+1
        rol remainder
        lda remainder
        cmp period
        bcc next_bit
        sbc period
        sta remainder
        inc quotient
next_bit:
        dex
        bne divide
        ; Skip floor(delta/period)+1 boundaries, including an entry exactly
        ; on the deadline. Preserve the original grid without a catch-up burst.
        inc quotient
        bne add_misses
        inc quotient+1
add_misses:
        clc
        lda misses
        adc quotient
        sta misses
        lda misses+1
        adc quotient+1
        sta misses+1
        clc
        lda _a2_cadence_missed
        adc quotient
        sta _a2_cadence_missed
        lda _a2_cadence_missed+1
        adc quotient+1
        sta _a2_cadence_missed+1
        ; next deadline = snapshot + period - remainder (all modulo 65536).
        sec
        lda period
        sbc remainder
        clc
        adc now
        sta deadline
        lda now+1
        adc #0
        sta deadline+1
        ; Catch-up work must not consume the stopped-clock poll watchdog.
        jmp poll
timeout:
        lda #0
        sta active
        lda #$ff
        tax
        rts
