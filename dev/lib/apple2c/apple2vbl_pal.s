; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2vbl_pal.s — 50 or 60 Hz, measured on the clock of apple2vbl.s.
; Count a fixed 16-cycle loop over one video frame, about 1064 turns at
; 60 Hz and 1267 at 50 Hz. Every wait is bounded; with no usable clock
; (mode 0, or a clock that stops) the machine is taken as 60 Hz.
.setcpu "65C02"
.import _a2_vbl_mode, _a2_vbl_count
.export _a2_vbl_measure, _a2_vbl_pal
.bss
_a2_vbl_pal: .res 1             ; 1 after a2_vbl_measure on a 50 Hz machine
turns: .res 2
.code
_a2_vbl_measure:
        stz _a2_vbl_pal
        stz turns
        stz turns+1
        lda _a2_vbl_mode
        beq measured
        cmp #2
        beq measure_irq
        ; //e: from one falling edge of $C019 bit 7 to the next.
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
        ; //c: between two VBL interrupts.
        ldx _a2_vbl_count
:       jsr bounded
        bcs measured
        cpx _a2_vbl_count
        beq :-
        ldx _a2_vbl_count
        stz turns
        stz turns+1
count_irq:
        inc turns
        bne :+
        jsr overflow
        bcs measured
:       cpx _a2_vbl_count
        beq count_irq
judge:  lda turns+1
        cmp #>1166
        bne :+
        lda turns
        cmp #<1166
:       bcc measured
        inc _a2_vbl_pal
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
