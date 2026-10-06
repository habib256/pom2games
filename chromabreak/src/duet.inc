; VERHILLE Arnaud — GPL-3.0. Two voices on the one-bit speaker, in page 3.
;
; CHROMA.SYS copies this player to DUET_BASE (startup.s); sound.s calls it
; for every note of a tune. It lives outside the game image because its loop
; counts cycles: here it can never straddle a page, and the game's own
; modules keep their addresses.
;
; Two square waves share the speaker by time division. Each turn of the loop
; looks at the bass, then at the melody. While both are at the same level the
; speaker rests there; while they differ it flips at both looks and follows
; the bass for 13 cycles, the melody for 20, at 31 kHz: too fast to hear, and
; what is left is the sum of the two waves, the melody a little louder.
; Every path through a turn takes DUET_CYCLES, so a half-period is a whole
; count of turns whatever the other voice does. tools/generate_music.py picks
; just-intonation counts (C4 = 60 turns).
;
; The first include defines the addresses; a second one, with DUET_CODE
; defined and under .org DUET_BASE, assembles the player itself.
.ifndef DUET_BASE
DUET_BASE   = $0310             ; page 3 is free under ProDOS up to $03CF
DUET_KEYS   = DUET_BASE         ; $80: a key press stops the note; 0: it cannot
DUET_PLAY   = DUET_BASE+2       ; A = melody count (0: silence), X = bass
                                ; count, Y = slices
DUET_CYCLES = 33                ; one turn
DUET_TURNS  = 255               ; turns between two looks at the keyboard
DUET_SLICE  = DUET_TURNS*DUET_CYCLES+34 ; a slice with that look: ~8.3 ms
.endif

.ifdef DUET_CODE
duet_keys: .byte 0
duet_left: .byte 0              ; slices left to play
.assert * = DUET_PLAY, error, "DUET_PLAY is not the player's entry"
        php                             ; no interrupt inside a note: the //c
        sei                             ; mouse's sixty a second would smear
        jsr duet_note                   ; both voices. They are served between
        plp                             ; two notes.
        rts
duet_note:
        sty duet_left
        stx duet_bass_a+1               ; the counts are the operands of the
        stx duet_bass_b+1               ; four reloads
        sta duet_mel_a+1
        sta duet_mel_b+1
        tay
        beq :+                          ; silence: the flips go to $0030,
        lda #$C0                        ; a harmless read, in the same time
:       sta duet_flip_bass+2
        sta duet_flip_mel+2
        lda #DUET_TURNS
        sec                             ; SBC #1 never borrows: C stays set
; --- both voices at the same level: the speaker rests ---
duet_same:
        dex                             ; 2
        bne duet_same_bass                       ; 3  (2)
duet_bass_a:
        ldx #0                          ;    (2)
        jmp duet_flip_bass              ;    (3)  the bass flips
duet_same_bass:
        nop                             ; 2
        nop                             ; 2
duet_rest_bass:
        nop                             ; 4
        nop
        dey                             ; the melody, likewise
        bne duet_same_mel
duet_mel_a:
        ldy #0
        jmp duet_flip_mel
duet_same_mel:
        nop
        nop
duet_rest_mel:
        nop
        nop
        sbc #1                          ; 2
        nop                             ; 2
        bne duet_same                   ; 3: DUET_CYCLES in all
        jsr duet_slice
        bne duet_same
        rts
; --- they differ: the speaker goes to the voice just looked at ---
duet_differ:
        dex
        bne duet_differ_bass
duet_bass_b:
        ldx #0
        jmp duet_rest_bass              ; the bass joins the melody
duet_differ_bass:
        nop
        nop
duet_flip_bass:
        bit $C030
        dey
        bne duet_differ_mel
duet_mel_b:
        ldy #0
        jmp duet_rest_mel
duet_differ_mel:
        nop
        nop
duet_flip_mel:
        bit $C030
        sbc #1
        nop
        bne duet_differ
        jsr duet_slice
        bne duet_differ
        rts
; Between two slices. Z set = stop: the note is over, or a key is down and
; duet_keys lets it cut the tune. Otherwise A = the turns of the next slice.
duet_slice:
        dec duet_left
        beq @stop
        lda $C000
        and duet_keys
        bmi @key
        lda #DUET_TURNS
@stop:  rts
@key:   lda #0
        rts
.assert * <= $03D0, error, "the duet player runs into the ProDOS vectors"
.endif
