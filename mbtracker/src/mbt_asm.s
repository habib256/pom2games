; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; mbt_asm.s — MB TRACKER's assembly side, called from C (mbt.h):
;   - the Mockingboard: mb_detect, the mb_irq.asm service at 50 Hz (ProDOS
;     ALLOC_INTERRUPT) whose tick is aysong.asm's ays_tick, gated by
;     snd_gate; play / stop / mute / the position for the cursor;
;   - the mouse (dev/lib/mouse): X clamped to 0-159 (a column = X / 2),
;     read with 80STORE off;
;   - the keyboard latch; main <-> aux copies (auxmem.asm's chunked ROM
;     AUXMOVE, chunks under SEI so the music interrupt waits at most ~5 000
;     cycles), main <-> the aux language card (ALTZP, bank 1; chunks under
;     SEI).
; The 80-column text and the mouse pointer: dev/lib/apple2c's apple2t80.s
; (assembled with T80_PTR=1) and apple2t80_ptr.s (mbt.h, the Makefile).
.setcpu "65C02"
.importzp ptr1, tmp1, tmp2
.import _mouse_slot, _mouse_poll
MB_FAST_WRITE   = 1
MB_IRQ_HUSH_BOTH = 1            ; 6-voice songs: both chips
AYSONG_VOICES   = 6
MB_IRQ_TICK     = mbt_tick
MB_IRQ_GATE     = _snd_gate
AYSONG_CPU65C02 = 1

.export _snd_detect, _snd_start, _snd_shutdown, _snd_play, _snd_stop, _snd_mute_set
.export _snd_gate, _snd_loop, _snd_song, _snd_order0, _snd_row0, _snd_mute
.export _snd_ticks := mb_irq_ticks
.export _ays_order := ays_order, _ays_row := ays_row, _ays_play := ays_play
.export _mouse_read
.export _kbd_get, kbd_idle, mbt_tick      ; (mbt_tick: tests time it)
.export mouse_read_done                 ; (tests: a mouse move starts there)
.export _ax_main, _ax_aux, _ax_len, _aux_put, _aux_get, _lc_put, _lc_get

.bss
_snd_gate:   .res 1             ; 0: no ays_tick (the ticks are still counted)
_snd_loop:   .res 1             ; $FF, else the order entry played again and again
_snd_song:   .res 2             ; the song snd_play starts
_snd_order0: .res 1             ; ...at this order entry
_snd_row0:   .res 1             ; ...and row
_snd_mute:   .res 1
_ax_main:    .res 2
_ax_aux:     .res 2
_ax_len:     .res 2
.code

; ------------------------------------------------------------ sound
; A = the Mockingboard's slot, 0 = none (the //c's 4c woken at $C403).
_snd_detect:
        jsr mb_detect
        ldx #0
        rts

; The interrupt service on (call only with a card): A = its ProDOS number,
; 0 = ALLOC_INTERRUPT failed.
_snd_start:
        lda #$FF
        sta _snd_loop
        stz _snd_gate
        jsr mb_forget
        jsr mb_irq_start
        lda mb_irq_n
        ldx #0
        rts

_snd_shutdown:
        stz _snd_gate
        jmp mb_irq_stop

; ays_init(snd_song), then ays_set_pos(snd_order0, snd_row0) unless both
; are 0, the mute mask, the gate open.
_snd_play:
        php
        sei
        stz _snd_gate
        lda _snd_song
        ldy _snd_song+1
        jsr ays_init
        lda _snd_order0
        ora _snd_row0
        beq :+
        lda _snd_order0
        ldx _snd_row0
        jsr ays_set_pos
:       lda _snd_mute
        jsr ays_mute
        lda #1
        sta _snd_gate
        plp
        rts

; Silence: no more ticks, every voice off, chip 1's volumes 0 (mb_hush).
_snd_stop:
        php
        sei
        stz _snd_gate
        jsr ays_stop
        plp
        jmp mb_hush

_snd_mute_set:
        sta _snd_mute
        jmp ays_mute

; The interrupt's tick. Pattern loop: when the row after the pattern's last
; one is due, the order entry goes back to snd_loop (ays_tick increments it).
mbt_tick:
        lda _snd_loop
        cmp #$FF
        beq @tick
        ldx ays_play
        beq @tick
        ldx ays_row
        cpx ays_rows
        bne @tick
        ldx ays_count
        cpx #1
        bne @tick
        dec a
        sta ays_order
@tick:  jmp ays_tick

; ------------------------------------------------------------ the mouse
; mouse_poll with 80STORE off (the firmware's screen holes in main).
_mouse_read:
        sta $C000
        jsr _mouse_poll
mouse_read_done:
        sta $C001
        rts

; ------------------------------------------------------------ keyboard
; A = the key (7 bits), 0 = none. kbd_idle: no key waiting (tests stop
; there: every key before was handled).
_kbd_get:
        lda $C000
        bpl kbd_idle
        bit $C010
        and #$7F
        ldx #0
        rts
kbd_idle:
        lda #0
        tax
        rts

; ------------------------------------------------------------ aux memory
; ax_len bytes between main ax_main and aux ax_aux: dev/lib/apple2/auxmem.asm's
; aux_store_chunked / aux_fetch_chunked (the ROM's AUXMOVE, 128-byte chunks
; under SEI), on these variables (ax_aux, ax_len, consumed; the music
; interrupt touches none of them).
AUXMEM_FETCH_CHUNK = 128
auxmem_fsrc = ptr1
auxmem_fdst = _ax_aux            ; aux_put: the aux destination
auxmem_flen = _ax_len
auxmem_fn   = tmp1
_aux_put:
        lda _ax_main
        ldy _ax_main+1
        jmp aux_store_chunked
_aux_get:                        ; the destination is main: ax_aux <-> ax_main
        ldx _ax_main
        lda _ax_aux
        stx _ax_aux
        ldx _ax_main+1
        ldy _ax_aux+1
        stx _ax_aux+1
        jmp aux_fetch_chunked

; ax_len bytes between main ax_main and the aux language card's bank 1 at
; ax_aux ($D000-$FFF9; /RAM disconnected), 128 at a time under SEI: ALTZP
; on (aux zero page and stack: none used meanwhile), LC RAM read / write,
; then ROM and main ZP back.
_lc_put:
        sec
        bra lccopy
_lc_get:
        clc
lccopy: ror tmp2                 ; bit 7: main -> LC
@chunk: lda _ax_len
        ora _ax_len+1
        bne :+
        rts
:       lda _ax_len+1            ; n = min(len, 128)
        bne @full
        lda _ax_len
        cmp #128
        bcc @n
@full:  lda #128
@n:     sta tmp1
        bit tmp2
        bmi @tolc
        lda _ax_aux
        ldx _ax_aux+1
        ldy _ax_main
        sty @dst+1
        ldy _ax_main+1
        bra @pt
@tolc:  lda _ax_main
        ldx _ax_main+1
        ldy _ax_aux
        sty @dst+1
        ldy _ax_aux+1
@pt:    sta @src+1
        stx @src+2
        sty @dst+2
        ldx tmp1
        ldy #0
        php
        sei
        sta $C009                ; ALTZP
        lda $C08B
        lda $C08B                ; LC RAM bank 1, read and write
@src:   lda $FFFF,y
@dst:   sta $FFFF,y
        iny
        dex
        bne @src
        lda $C082                ; ROM, LC write-protected
        sta $C008                ; main ZP and stack
        plp
        clc                      ; both pointers + n, len - n
        lda _ax_main
        adc tmp1
        sta _ax_main
        bcc :+
        inc _ax_main+1
:       clc
        lda _ax_aux
        adc tmp1
        sta _ax_aux
        bcc :+
        inc _ax_aux+1
:       sec
        lda _ax_len
        sbc tmp1
        sta _ax_len
        bcs :+
        dec _ax_len+1
:       jmp @chunk

.include "mb_irq.asm"
.include "aysong.asm"
.include "mockingboard.asm"
.include "auxmem.asm"             ; aux_store_chunked, aux_fetch_chunked
