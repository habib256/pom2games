; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; tune.asm -- one-voice speaker music, one tick per ~1/60 s
; ============================================================================
;   tune_start -- A/Y = a tune (lo/hi): play it from its first note, looping.
;   tune_stop  -- silence: tune_tick only waits from now on.
;   tune_tick  -- one tick, ~1/60 s: a slice of the current note (sound.asm's
;                 tone), or a rest through the Monitor's WAIT. The last tick
;                 of every note is silent, which separates repeated notes.
;                 Without a tune (stopped, or a tune_play that ended) it is
;                 a rest too: a game loop can call it every frame as its
;                 clock. Clobbers A, X, Y.
;   tune_play  -- A/Y = a tune, played once to its end (blocking).
;
; A tune is a list of 3-byte events, ended by a 0:
;   .byte ticks, half_period, toggles
;     ticks        length in ticks (1..255; the last one is silent)
;     half_period  tone's X (0: a rest)
;     toggles      tone's A, speaker flips per tick: ~1/60 s of the pitch,
;                  toggles * (12 + 5 * half_period) ~ 17,000 cycles
; dev/tools/audio/tune.py encodes them from note text ('A4:1 R:1', unit
; ticks); DIRTBIKE's tools/music.py holds its songs and imports it.
;
; Options (define before the include):
;   TUNE_MUTE       label of a byte: while it is 0, notes are rests (the
;                   tune keeps its tempo). Default: never muted.
;   TUNE_REST_WAIT  WAIT's A for a silent tick (default 79, ~17,000 cycles)
;
; Zero page: tune_ptr (2), skipped if defined before the include.
; BSS: tune_loop (2), tune_t (1). Call tune_stop (or tune_start) once
; before the first tune_tick: zero page and BSS start as garbage.
; Code 116 B (+5 with TUNE_MUTE). .ifref: include after the callers. Needs sound.asm (tone) and
; apple2.inc (WAIT). From DIRTBIKE's title.inc (music_start, music_tick);
; DIRTBIKE uses it (TUNE_MUTE = snd_on).
; ============================================================================

.ifndef _TUNE_ASM_LOADED_
.if .referenced(tune_start) .or .referenced(tune_stop) .or .referenced(tune_tick) .or .referenced(tune_play)
_TUNE_ASM_LOADED_ = 1

.ifndef TUNE_REST_WAIT
TUNE_REST_WAIT = 79
.endif

.ifndef tune_ptr
.zeropage
tune_ptr:       .res 2
.endif
.segment "BSS"
tune_loop:      .res 2
tune_t:         .res 1

.segment "CODE"
; tune_start -- A/Y = a tune, from its first note, looping
tune_start:
        STA     tune_ptr
        STA     tune_loop
        STY     tune_ptr+1
        STY     tune_loop+1
        LDA     #0
        STA     tune_t
        RTS

tune_stop:
        LDA     #0
        STA     tune_ptr+1
        RTS

; tune_play -- A/Y = a tune, played once
tune_play:
        JSR     tune_start
        LDA     #0
        STA     tune_loop+1     ; the end: no loop, tune_ptr+1 = 0
@n:     JSR     tune_tick
        LDA     tune_ptr+1
        BNE     @n
        RTS

; tune_tick -- one ~1/60 s tick (see the header)
tune_tick:
        LDA     tune_ptr+1
        BEQ     @wait
        LDY     #0
        LDX     tune_t
        INX
        TXA
        CMP     (tune_ptr),Y
        BEQ     @rest           ; the note's last tick: silent
.ifdef TUNE_MUTE
        LDA     TUNE_MUTE
        BEQ     @rest
.endif
        INY
        LDA     (tune_ptr),Y    ; half period (0: a rest)
        BEQ     @rest
        TAX
        INY
        LDA     (tune_ptr),Y    ; flips in a tick
        JSR     tone
        JMP     @next
@rest:  JSR     @wait
@next:  INC     tune_t
        LDY     #0
        LDA     tune_t
        CMP     (tune_ptr),Y
        BCC     @rts
        STY     tune_t          ; the next note
        CLC
        LDA     tune_ptr
        ADC     #3
        STA     tune_ptr
        BCC     @n1
        INC     tune_ptr+1
@n1:    LDA     (tune_ptr),Y
        BNE     @rts
        LDA     tune_loop       ; the end: again, or stop
        STA     tune_ptr
        LDA     tune_loop+1
        STA     tune_ptr+1
@rts:   RTS
@wait:  LDA     #TUNE_REST_WAIT
        JMP     WAIT

.endif  ; referenced
.endif  ; _TUNE_ASM_LOADED_
