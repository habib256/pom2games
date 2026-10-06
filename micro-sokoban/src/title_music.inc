; Title music: two voices on the one-bit speaker. MENU SOUND switches it.
;
; Ten bars of calm swung jazz at ~100 BPM, in F: the ii-V-I arpeggios of the
; first, one-voice tune (Gm9 / C13 / Fmaj9), now over a walking bass, then a
; turn through Am7 and Dm7 back to the cadence. ~24 s, then it loops.
;
; title_duet mixes two square waves by time division. Each turn of its loop
; looks at the bass, then at the melody. While both are at the same level the
; speaker rests there. While they differ it flips at both looks: the cone
; follows the bass for 14 cycles and the melody for 19, at 31 kHz, too fast to
; hear, and what is left is the sum of the two waves, the melody a little
; louder. (Flipping the speaker for each voice on its own would multiply the
; waves instead: the sum and difference tones, not the notes.)
;
; Every path through a turn takes DUET_CYCLES, so a half-period is a count of
; turns whatever the other voice does. Counts are whole numbers, so the tune
; uses the just scale of F, whose periods are whole (F3 = 90 turns, a third of
; a semitone under concert pitch); only B flat falls between two counts.
; The same count in both voices is one voice alone, at full level.
;
; This file is included at $6003: the loop must not cross a page boundary (a
; taken branch would cost one more cycle), and nothing can move it from here.
.zeropage                       ; after DOS_ZP_LEN: not kept across RWTS, no need
duet_bass:       .res 1          ; half-periods, in turns
duet_mel:        .res 1
duet_left:       .res 1          ; slices left to play
duet_btn0:       .res 1          ; the buttons when the note began
duet_btn1:       .res 1
.segment "WORKBSS"
title_music_index: .res 1        ; next event of the score
title_music_wait:  .res 1        ; polls before it
title_due:         .res 1        ; 1 = the corridor steps after this beat
.code

DUET_CYCLES = 33                ; one turn
DUET_TURNS  = 255               ; turns between two looks at the keyboard
DUET_SLICE  = DUET_TURNS*DUET_CYCLES+47 ; a slice with that look: ~8.3 ms

; title_duet: play duet_bass under duet_mel for duet_left slices, or until a
; key is down or a button changes (Z set either way; duet_left = 0 if the
; note played to its end). X and Y count the half-periods, A the turns.
title_duet:
        LDX duet_bass
        LDY duet_mel
        LDA #DUET_TURNS
        SEC                             ; SBC #1 never borrows: C stays set
; --- both voices at the same level: the speaker rests ---
@same:  DEX                             ; 2
        BNE @same_bass                  ; 3  (2)
        LDX duet_bass                   ;    (3)
        JMP @differ_bass_out            ;    (3)  the bass flips
@same_bass:
        NOP                             ; 2
        BIT duet_left                   ; 3       only its cycles matter
@same_bass_out:
        NOP                             ; 4
        NOP
        DEY                             ; the melody, likewise
        BNE @same_mel
        LDY duet_mel
        JMP @differ_mel_out
@same_mel:
        NOP
        BIT duet_left
@same_mel_out:
        NOP
        NOP
        SBC #1                          ; 2
        BNE @same                       ; 3: DUET_CYCLES in all
        JSR duet_slice
        BNE @same
        RTS
; --- they differ: the speaker goes to the voice just looked at ---
@differ:
        DEX
        BNE @differ_bass
        LDX duet_bass
        JMP @same_bass_out              ; the bass joins the melody
@differ_bass:
        NOP
        BIT duet_left
@differ_bass_out:
        BIT SPKR
        DEY
        BNE @differ_mel
        LDY duet_mel
        JMP @same_mel_out
@differ_mel:
        NOP
        BIT duet_left
@differ_mel_out:
        BIT SPKR
        SBC #1
        BNE @differ
        JSR duet_slice
        BNE @differ
        RTS
.assert >title_duet = >(*-1), error, "title_duet crosses a page: its branches would lose their timing"

; duet_slice: between two slices. Z set = stop: the note is over, or a key or
; a button needs the poll loop. Otherwise A = the turns of the next slice.
; C is left set. The buttons are compared with their state at the start of
; the note: an input left unconnected reads as held.
duet_slice:
        DEC duet_left
        BEQ @stop
        BIT KBD
        BMI @hit
        LDA BUTN0
        EOR duet_btn0
        BMI @hit
        LDA BUTN1
        EOR duet_btn1
        BMI @hit
        LDA #DUET_TURNS
@stop:  RTS
@hit:   LDA #0
        RTS

title_music_reset:
        LDA #0
        STA title_music_index
        STA title_due
        LDA #1
        STA title_music_wait
        RTS

; title_music: called once per poll of title_wait. Plays the next event when
; its time has come: one beat at most, so input and the corridor wait a beat
; at worst, and a key or a button cuts the note short.
title_music:
        LDA hof_buf+HOF_SOUND
        AND #OPT_MENU
        BEQ @done
        DEC title_music_wait
        BNE @done
@event: LDX title_music_index
        LDA title_bass,X
        STA duet_bass
        LDA title_mel,X
        STA duet_mel
        LDY title_len,X
        INX
        CPX #TITLE_EVENTS
        BCC @index
        LDX #0
@index: STX title_music_index
        TYA
        LDX duet_mel
        BNE @note
        STA title_music_wait            ; a rest: that many silent polls
@done:  RTS
@note:  PHA                             ; bit 7: tied to the next event
        AND #$7F
        STA duet_left
        LSR A                           ; the polls it lasts, for the clocks
        LSR A                           ; below: slices * 1.3125
        STA temp
        LSR A
        LSR A
        CLC
        ADC temp
        ADC duet_left
        STA temp
        LDA BUTN0
        STA duet_btn0
        LDA BUTN1
        STA duet_btn1
        JSR title_duet
        ; The attract countdown and the corridor count polls: charge them
        ; the polls spent in the note.
        LDA idle_lo
        ORA idle_hi
        BEQ @clock
        LDA idle_lo
        SEC
        SBC temp
        STA idle_lo
        BCS @clock
        DEC idle_hi
        BPL @clock
        LDA #0
        STA idle_lo
        STA idle_hi
@clock: LDA title_tick
        BNE @left
        LDA #$FF                        ; zero is a fresh 256-poll tick
@left:  SEC
        SBC temp
        BCC @due                        ; passed: the byte wrapped to the next step
        CMP #TITLE_GAP+1
        BCS @tick
        LDA #0                          ; due during the coming rest: step now
@due:   INC title_due
@tick:  STA title_tick
        PLA
        BPL @gap
        LDA duet_left
        BNE @gap
        JMP @event                      ; tied, and played to its end
@gap:   LDA #TITLE_GAP
        STA title_music_wait
        LDA title_due
        BEQ @done
        LDA #0
        STA title_due

; title_animate: one step of the corridor. Drawing it takes TITLE_STEP_POLLS
; polls: the rest in progress gives them back, and the music keeps its beat.
title_animate:
        JSR title_step
        LDA title_music_wait
        CMP #TITLE_STEP_POLLS+1
        BCC @done
        SBC #TITLE_STEP_POLLS
        STA title_music_wait
@done:  RTS

.rodata
; One poll of title_wait is ~6.3 ms (TITLE_POLL_CYCLES). A beat is 72 slices,
; ~0.6 s; swung eighths share it 2:1. A detached note leaves the end of its
; slot to a rest of TITLE_GAP polls, the same time as TITLE_GAP_SLICES.
TITLE_POLL_CYCLES = 6426
TITLE_BEAT  = 72
TITLE_LONG  = 48
TITLE_SHORT = TITLE_BEAT-TITLE_LONG
TITLE_GAP   = 8
TITLE_GAP_SLICES = (TITLE_GAP*TITLE_POLL_CYCLES+DUET_SLICE/2)/DUET_SLICE
TITLE_BEAT_POLLS = (TITLE_BEAT*DUET_SLICE+TITLE_POLL_CYCLES/2)/TITLE_POLL_CYCLES
TITLE_STEP_POLLS = 7

; Half-periods in turns. G is the low one of the two just Gs (10/9), a pure
; fifth under D for the Gm9 bars; B flat is the nearest count to 67.5 / 33.75.
N_E2 = 192
N_F2 = 180
N_G2 = 162
N_A2 = 144
N_Bb2 = 135
N_C3 = 120
N_D3 = 108
N_E3 = 96
N_G3 = 81
N_A3 = 72
N_Bb3 = 68
N_C4 = 60
N_D4 = 54
N_E4 = 48
N_F4 = 45
N_G4 = 40
N_A4 = 36
N_Bb4 = 34
N_C5 = 30
N_D5 = 27
N_E5 = 24

; One event: field 0 = melody count (0 = a rest), 1 = bass count, 2 = slices
; (bit 7: the next event follows at once), or the polls of a rest.
.macro DUET field, melody, bass, length
        .if field = 0
                .byte melody
        .elseif field = 1
                .byte bass
        .else
                .assert (length & $7F) > 0 .and length < 256, error, "Title event length out of range"
                .byte length
        .endif
.endmacro

; NOTE: a detached beat. PAIR: two swung eighths over one bass note, slurred.
; REST: a silent beat.
.macro NOTE field, melody, bass
        DUET field, melody, bass, TITLE_BEAT-TITLE_GAP_SLICES
.endmacro
.macro PAIR field, first, second, bass
        DUET field, first, bass, TITLE_LONG|$80
        DUET field, second, bass, TITLE_SHORT-TITLE_GAP_SLICES
.endmacro
.macro REST field
        DUET field, 0, 0, TITLE_BEAT_POLLS
.endmacro

.macro TITLE_SCORE field
        ; Gm9: the first tune's rising arpeggio, G Bb D F A F.
        NOTE field, N_G3, N_G2
        PAIR field, N_Bb3, N_D4, N_G2
        PAIR field, N_F4, N_A4, N_D3
        NOTE field, N_F4, N_Bb2
        ; C13: four relaxed quarters, F falls to E and B flat will fall to A.
        NOTE field, N_E4, N_C3
        NOTE field, N_A4, N_E3
        NOTE field, N_D5, N_G2
        NOTE field, N_Bb4, N_C3
        ; Fmaj9: down the chord while the bass climbs it.
        NOTE field, N_A4, N_F2
        PAIR field, N_G4, N_E4, N_A2
        PAIR field, N_C4, N_A3, N_C3
        NOTE field, N_C4, N_E3
        ; Dm7: up again over a bass walking down to G.
        NOTE field, N_D4, N_D3
        PAIR field, N_F4, N_A4, N_C3
        NOTE field, N_C5, N_Bb2
        PAIR field, N_A4, N_G4, N_A2
        ; Gm9, from the top this time.
        NOTE field, N_D5, N_G2
        PAIR field, N_Bb4, N_A4, N_D3
        PAIR field, N_F4, N_D4, N_Bb2
        NOTE field, N_F4, N_D3
        ; C13.
        NOTE field, N_E4, N_C3
        PAIR field, N_G4, N_A4, N_E3
        NOTE field, N_D5, N_G2
        PAIR field, N_C5, N_Bb4, N_E2
        ; Am7 where F was expected: the line climbs to its highest note.
        NOTE field, N_A4, N_A2
        PAIR field, N_C5, N_E5, N_E3
        NOTE field, N_D5, N_G2
        NOTE field, N_E5, N_C3
        ; Dm7.
        NOTE field, N_C5, N_D3
        PAIR field, N_A4, N_F4, N_C3
        NOTE field, N_D4, N_Bb2
        PAIR field, N_F4, N_A4, N_A2
        ; Gm9 and C13, two beats each.
        NOTE field, N_Bb4, N_G2
        PAIR field, N_A4, N_F4, N_D3
        NOTE field, N_E4, N_C3
        PAIR field, N_G4, N_Bb4, N_E2
        ; Fmaj9: home, a breath, and the bass alone leads back to G.
        PAIR field, N_A4, N_G4, N_F2
        NOTE field, N_C5, N_F2
        REST field
        DUET field, N_D3, N_D3, TITLE_LONG|$80
        DUET field, N_A2, N_A2, TITLE_SHORT-TITLE_GAP_SLICES
.endmacro

title_mel:  TITLE_SCORE 0
title_bass: TITLE_SCORE 1
title_len:  TITLE_SCORE 2
TITLE_EVENTS = title_bass-title_mel
.code
