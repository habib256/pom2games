; WARGALAGA II -- sound: Mockingboard if there is one, else the speaker.
; Included by game.s. Data: src/sound.inc (tools/sound.py).
;
; logic.s only raises event bits in snd_ev (logic state is untouched: the
; model ignores sound). Once a frame, after the flip, sound_frame starts the
; most important new effect (unless a more important one is playing) and
; moves the effect one step:
;   - Mockingboard: on the second AY (voice A, tone or noise);
;   - speaker: spk_period = the step's half-period in turns of timing.s's
;     wait loop, which toggles the speaker while a frame waits for its flip
;     (no music in play: decision of 2026-10-22).
; Music (Mockingboard only, first AY) is a PT3 module (tools/pt3.py) played
; by Vince Weaver's decoder (dev/lib/apple2/pt3), both in aux memory
; (src/music.s), one tick per interrupt of the VIA's timer 1 at MUS_HZ
; through a ProDOS ALLOC_INTERRUPT handler: notes on time whatever the
; frame rate, NTSC or PAL. (Lot 4 first stepped it once a frame: the rhythm
; wobbled with the frame rate, heard by the user on 2026-10-23.) The handler
; enters aux memory by tr_tick, then writes the registers that changed
; (shadows: chip 1 belongs to the handler, chip 2 to sound_frame); it keeps
; mb_chip. A tick takes ~1 500-3 000 cycles: the handler scans the //e VBL
; on entry and on exit (timing_scan, atomic) so no blank goes unseen.
; S mutes / unmutes (the song pauses).

MUS_PERIOD = 1020484 / MUS_HZ - 2   ; T1 latch (free run: latch + 2 cycles)

.importzp AY_REGISTERS
.import pt3_init_song, pt3_tick

.bss
audio_slot:  .res 1             ; Mockingboard slot, 0 = speaker
snd_ev:      .res 1             ; event bits raised by logic.s
sfx_ptr:     .res 2             ; current effect step, hi 0 = none
sfx_rank:    .res 1             ; its rank (0 = most important)
spk_period:  .res 1             ; speaker half-period for this frame, 0 = off
ay_shadow:   .res 32            ; both chips' registers as last written
mus_irq_n:   .res 1             ; ProDOS interrupt number, 0 = none
mus_ticks:   .res 1             ; music interrupts served (timing.s's paddle
                                 ; reading, tests)
.data
sound_on:    .byte 1

.code
; Before the //c clock: waking a Mockingboard 4c may hide the slot 4 mouse.
sound_init:
        jsr mb_detect
        sta audio_slot
        stz sfx_ptr+1
        stz spk_period
        lda audio_slot
        beq si_done
        jsr ay_forget
        php                      ; the song: tables built in aux memory
        sei
        jsr tr_init
        plp
        lda #1                   ; chip 2: effects on voice A
        sta mb_chip
        ldx #7
        lda #$3E
        jsr ay_put
        ldx #6                   ; noise period
        lda #12
        jsr ay_put
        lda audio_slot           ; patch the handler's VIA addresses
        ora #$C0
        sta irq_ifr+2
        sta irq_ack+2
        sta ptr+1
        stz ptr
        php
        sei
        jsr $BF00
        .byte $40                ; ALLOC_INTERRUPT
        .word mus_alloc
        bcs si_noirq
        lda mus_alloc+1
        sta mus_irq_n
        lda #<MUS_PERIOD         ; T1 free running at MUS_HZ...
        ldx #>MUS_PERIOD
        jsr mb_timer_start
        ldy #$0E                 ; ...and its interrupt on (IER: set bit 6)
        lda #$C0
        sta (ptr),y
        plp
        cli
        rts
si_noirq:
        plp
si_done:
        rts

; Shadows unknown: the next write of every register goes out.
ay_forget:
        lda #$FF
        ldx #31
:       sta ay_shadow,x
        dex
        bpl :-
        rts

; X = register, A = value, mb_chip = chip: write if it changed. Keeps X.
ay_put: phx
        pha
        txa
        ldy mb_chip
        beq :+
        ora #16
:       tay
        pla
        cmp ay_shadow,y
        beq :+
        sta ay_shadow,y
        jsr mb_write
:       plx
        rts

; S: sound off (silence now) / on (registers rewritten as they come).
sound_toggle:
        php
        sei                      ; (the music handler writes too)
        lda sound_on
        eor #1
        sta sound_on
        bne :+
        stz spk_period
        stz sfx_ptr+1
        jsr mb_silence
        jsr ay_forget
:       plp
        rts

sound_shutdown:
        stz spk_period
        php
        sei
        jsr mb_stop              ; silence, timer 1 and its interrupt off
        lda mus_irq_n
        beq :+
        sta mus_dealloc+1
        stz mus_irq_n
        jsr $BF00
        .byte $41                ; DEALLOC_INTERRUPT
        .word mus_dealloc
:       plp
        rts

; Once a frame, after the flip.
sound_frame:
        lda sound_on
        bne :+
        stz snd_ev
        rts
:       lda snd_ev               ; the most important new event
        stz snd_ev
        beq sf_step
        ldx #0
:       lsr
        bcs :+
        inx
        bra :-
:       lda sfx_ptr+1            ; a more important effect is playing?
        beq :+
        cpx sfx_rank             ; (the same one starts again)
        beq :+
        bcs sf_step
:       stx sfx_rank
        lda sfx_lo,x
        sta sfx_ptr
        lda sfx_hi,x
        sta sfx_ptr+1
sf_step:
        lda sfx_ptr+1            ; effect step -> ptr
        beq sf_none
        sta ptr+1
        lda sfx_ptr
        sta ptr
        ldy #3
        lda (ptr),y
        cmp #$FF
        bne :+
        stz sfx_ptr+1            ; ended
        bra sf_none
:       lda sfx_ptr              ; next step for the next frame
        clc
        adc #5
        sta sfx_ptr
        bcc :+
        inc sfx_ptr+1
:       lda audio_slot           ; the speaker only without a card
        bne :+
        ldy #4
        lda (ptr),y
        sta spk_period
        rts
:
        lda #1                   ; chip 2, voice A
        sta mb_chip
        ldy #0
        lda (ptr),y
        ldx #0
        jsr ay_put
        ldy #1
        lda (ptr),y
        ldx #1
        jsr ay_put
        ldy #2
        lda (ptr),y
        ldx #7
        jsr ay_put
        ldy #3
        lda (ptr),y
        ldx #8
        jsr ay_put
        bra sf_music
sf_none:
        stz spk_period
        lda audio_slot
        jeq sf_done
        lda #1                   ; effect over: voice A of chip 2 silent
        sta mb_chip
        lda #0
        ldx #8
        jsr ay_put
sf_music:
sf_done:
        rts

; ProDOS interrupt handler: C = 0 if timer 1 of the Mockingboard's VIA
; fired. One PT3 tick (aux memory), the changed registers of chip 1 written.
mus_irq:
        cld
irq_ifr:
        lda $C40D                ; IFR (slot patched by sound_init)
        and #$40
        bne :+
        sec                      ; not ours
        rts
:
irq_ack:
        lda $C404                ; T1 low: acknowledges
        jsr timing_scan          ; (a long handler: see the header)
        inc mus_ticks
        lda sound_on
        beq mi_done
        lda mb_chip              ; the main code may be about to write chip 2
        pha
        jsr tr_tick
        stz mb_chip              ; (chip 1's shadows: ay_shadow+0..15)
        ldx #12
mi_reg: lda AY_REGISTERS,x       ; inline ay_put: most are unchanged
        cmp ay_shadow,x
        beq :+
        sta ay_shadow,x
        phx
        jsr mb_write
        plx
:       dex
        bpl mi_reg
        lda AY_REGISTERS+13      ; envelope shape: $FF = unchanged (a write
        cmp #$FF                 ; restarts the envelope, shadow or not)
        beq :+
        ldx #13
        jsr mb_write
:       pla
        sta mb_chip
        jsr timing_scan
mi_done:
        clc
        rts
mus_alloc:   .byte 2, 0
        .word mus_irq
mus_dealloc: .byte 1, 0

; Trampolines into aux memory (copied to $1FE0 of both banks by
; tramp_install): reads and writes switch to aux, the next fetch comes
; from the aux copy, the same bytes. IRQs off; zero page and stack stay
; main (no ALTZP).
.segment "TRAMP"
tr_init:
        sta $C005                ; RAMWRT aux
        sta $C003                ; RAMRD aux
        jsr pt3_init_song
        bra tr_main
tr_tick:
        sta $C005
        sta $C003
        jsr pt3_tick
tr_main:
        sta $C002                ; back to main
        sta $C004
        rts
.code

; After aux_load: the trampolines to $1FE0, main and aux.
tramp_install:
        ldx #<(__TRAMP_SIZE__-1)
:       lda __TRAMP_LOAD__,x
        sta __TRAMP_RUN__,x
        dex
        bpl :-
        lda #<__TRAMP_RUN__
        sta $3C
        sta $42
        lda #>__TRAMP_RUN__
        sta $3D
        sta $43
        lda #<(__TRAMP_RUN__+__TRAMP_SIZE__-1)
        sta $3E
        lda #>(__TRAMP_RUN__+__TRAMP_SIZE__-1)
        sta $3F
        sec                      ; main -> aux
        jmp $C311                ; AUXMOVE
