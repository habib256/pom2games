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
; on entry and on exit (_a2_vbl_scan, atomic) so no blank goes unseen.
; S turns the music off / on (the song pauses), never the effects.
; The interrupt service is dev/lib/apple2/mb_irq.asm (extracted from here,
; 2026-10-31), included four times so each routine stays where it was.

MUS_PERIOD = 1020484 / MUS_HZ - 2   ; T1 latch (free run: latch + 2 cycles)
MB_IRQ_PERIOD = MUS_PERIOD
MB_IRQ_TICK = tr_tick            ; one PT3 tick in aux memory...
MB_IRQ_FRAME = AY_REGISTERS      ; ...then its frame out to chip 1
MB_IRQ_GATE = music_on           ; S: the song pauses
MB_IRQ_SCAN = 1
MB_IRQ_SPLIT = 1                 ; the handler after sound_frame
mb_irq_slot = audio_slot
mb_irq_ticks = mus_ticks
mb_irq_ptr = ptr

.importzp AY_REGISTERS
.import pt3_init_song, pt3_tick

.bss
audio_slot:  .res 1             ; Mockingboard slot, 0 = speaker
spk_period:  .res 1             ; speaker half-period for this frame, 0 = off
mb_shadow:   .res 32            ; both chips' registers as last written
mb_irq_n:    .res 1             ; ProDOS interrupt number, 0 = none
mus_ticks:   .res 1             ; music interrupts served (timing.s's paddle
                                 ; reading, tests)
.data
music_on:    .byte 1

.code
; Before the //c clock: waking a Mockingboard 4c may hide the slot 4 mouse.
sound_init:
        jsr mb_detect
        sta audio_slot
        stz sfx_ptr+1
        stz spk_period
        lda audio_slot
        beq mb_irq_rts
        jsr mb_forget
        php                      ; the song: tables built in aux memory
        sei
        jsr tr_init
        plp
        lda #1                   ; chip 2: effects on voice A
        sta mb_chip
        ldx #7
        lda #$3E
        jsr mb_put
        ldx #6                   ; noise period
        lda #12
        jsr mb_put
sound_irq := mb_irq_start        ; falls into it (mb_irq.asm: the ProDOS
                                 ; interrupt, T1 at MUS_HZ), then mb_forget
.include "mb_irq.asm"            ; and mb_put (shadowed AY write, keeps X)

; S: the music off (its chip silent now) / on (registers rewritten as they
; come); the effects play either way (2026-10-30: S muted everything).
sound_toggle:
        lda music_on
        eor #1
        sta music_on
        beq mb_hush
        rts

; mb_hush: the music's chip silent, its shadows forgotten: the next tick
; writes every register again. Also before a disk access (front.s): ProDOS's
; Disk II driver masks interrupts the whole time, a note held ~1 s otherwise.
.include "mb_irq.asm"
mus_hush := mb_hush

sound_shutdown:
        stz spk_period           ; falls into mb_irq_stop: silence, timer 1
mus_stop := mb_irq_stop          ; and its interrupt off, DEALLOC_INTERRUPT
.include "mb_irq.asm"

; Once a frame, after the flip.
sound_frame:
        lda snd_ev               ; the most important new event
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
        jsr mb_put
        ldy #1
        lda (ptr),y
        ldx #1
        jsr mb_put
        ldy #2
        lda (ptr),y
        ldx #7
        jsr mb_put
        ldy #3
        lda (ptr),y
        ldx #8
        jsr mb_put
        bra sf_music
sf_none:
        stz spk_period
        lda audio_slot
        jeq sf_done
        lda #1                   ; effect over: voice A of chip 2 silent
        sta mb_chip
        lda #0
        ldx #8
        jsr mb_put
sf_music:
sf_done:
        rts

; ProDOS interrupt handler (mb_irq.asm): C = 0 if timer 1 of the
; Mockingboard's VIA fired. One PT3 tick (aux memory), the changed registers
; of chip 1 written.
mus_irq := mb_irq_handler
.include "mb_irq.asm"
irq_ack := mb_irq_ack            ; (tests: the ticks by their PC)

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

.pushseg
.segment "BOOT"
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
.popseg
