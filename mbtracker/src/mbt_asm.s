; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; mbt_asm.s — MB TRACKER's assembly side, called from C (mbt.h):
;   - the Mockingboard: mb_detect, the mb_irq.asm service at 50 Hz (ProDOS
;     ALLOC_INTERRUPT) whose tick is aysong.asm's ays_tick, gated by
;     snd_gate; play / stop / mute / the position for the cursor;
;   - the 80-column text screen, written directly (80STORE: even columns in
;     aux $0400-$07FF through PAGE2, odd ones in main), ALTCHARSET on
;     (inverse lower case, MouseText);
;   - the keyboard latch; main <-> aux copies (the ROM's AUXMOVE, in
;     chunks under SEI so the music interrupt waits at most ~5 000 cycles).
.setcpu "65C02"
.importzp ptr1, ptr2, tmp1, tmp2
.import popa
MB_FAST_WRITE   = 1
MB_IRQ_TICK     = mbt_tick
MB_IRQ_GATE     = _snd_gate
AYSONG_CPU65C02 = 1

.export _snd_detect, _snd_start, _snd_shutdown, _snd_play, _snd_stop, _snd_mute_set
.export _snd_gate, _snd_loop, _snd_song, _snd_order0, _snd_row0, _snd_mute
.export _snd_ticks := mb_irq_ticks
.export _ays_order := ays_order, _ays_row := ays_row, _ays_play := ays_play
.export _txt_x, _txt_y, _txt_mode, _txt_init, _txt_putc, _txt_puts, _txt_fill, _txt_scroll
.export _kbd_get, kbd_idle
.export _ax_main, _ax_aux, _ax_len, _aux_put, _aux_get

.bss
_snd_gate:   .res 1             ; 0: no ays_tick (the ticks are still counted)
_snd_loop:   .res 1             ; $FF, else the order entry played again and again
_snd_song:   .res 2             ; the song snd_play starts
_snd_order0: .res 1             ; ...at this order entry
_snd_row0:   .res 1             ; ...and row
_snd_mute:   .res 1
_txt_x:      .res 1
_txt_y:      .res 1
_txt_mode:   .res 1             ; 0 normal, 1 inverse, 2 raw screen codes
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

; ------------------------------------------------------------ text, 80 columns
_txt_init:
        sta $C001                ; 80STORE
        sta $C00D                ; 80COL
        sta $C00F                ; ALTCHARSET
        bit $C051                ; TEXT
        bit $C052                ; full screen
        bit $C054                ; PAGE1
        stz _txt_mode
        ldx #0
        lda #$A0
@clr:   sta $0400,x
        sta $0500,x
        sta $0600,x
        sta $0700,x
        inx
        bne @clr
        bit $C055
@clra:  sta $0400,x
        sta $0500,x
        sta $0600,x
        sta $0700,x
        inx
        bne @clra
        bit $C054
        rts

; ptr1 = the row txt_y.
setrow:
        ldy _txt_y
        lda rowlo,y
        sta ptr1
        lda rowhi,y
        sta ptr1+1
        rts

; A = ASCII -> the screen code for txt_mode, written at (txt_x, txt_y) of
; the row in ptr1; txt_x + 1.
put:    ldx _txt_mode
        beq @norm
        dex
        bne @raw
        cmp #$40                 ; inverse: @..Z[\]^_ -> $00-$1F
        bcc @raw
        cmp #$60
        bcs @raw                 ; lower case: $60-$7F, inverse with ALTCHAR
        and #$1F
        bra @raw
@norm:  ora #$80
@raw:   tax
        lda _txt_x
        cmp #80
        bcs @out
        lsr a
        tay
        txa
        bcs @main
        bit $C055                ; even column: aux
        sta (ptr1),y
        bit $C054
        bra @out
@main:  sta (ptr1),y
@out:   inc _txt_x
        rts

_txt_putc:
        pha
        jsr setrow
        pla
        jmp put

; A/X = a NUL-terminated string.
_txt_puts:
        sta ptr2
        stx ptr2+1
        jsr setrow
        ldy #0
@next:  lda (ptr2),y
        beq @end
        phy
        jsr put
        ply
        iny
        bne @next
@end:   rts

; txt_fill(char, count).
_txt_fill:
        sta tmp2
        jsr popa
        sta tmp1
        jsr setrow
        ldx tmp2
        beq @end
@next:  lda tmp1
        phx
        jsr put
        plx
        dex
        bne @next
@end:   rts

; Columns 0-39 of the rows txt_y .. txt_y + txt_x - 1 one row up (A = 0:
; the last row keeps its text, to be redrawn) or down (A != 0: the first).
_txt_scroll:
        sta tmp1
        lda _txt_x
        dec a
        sta tmp2                 ; rows to copy
        beq @end
        lda tmp1
        bne @down
@up:    jsr @pair                ; dst = txt_y, src = txt_y + 1
        inc _txt_y
        dec tmp2
        bne @up
        rts
@down:  lda _txt_y               ; from the bottom: dst = last, src = last - 1
        clc
        adc tmp2
        sta _txt_y
@dn:    dec _txt_y
        jsr @pair2
        dec tmp2
        bne @dn
@end:   rts
@pair:  ldy _txt_y               ; row y + 1 -> row y
        lda rowlo+1,y
        sta ptr2
        lda rowhi+1,y
        sta ptr2+1
        bra @copy
@pair2: ldy _txt_y               ; row y -> row y + 1
        lda rowlo,y
        sta ptr2
        lda rowhi,y
        sta ptr2+1
        iny
@copy:  lda rowlo,y
        sta ptr1
        lda rowhi,y
        sta ptr1+1
        ldy #19
:       lda (ptr2),y
        sta (ptr1),y
        dey
        bpl :-
        bit $C055
        ldy #19
:       lda (ptr2),y
        sta (ptr1),y
        dey
        bpl :-
        bit $C054
        rts

rowlo:
.repeat 24, r
        .byte <($0400 + (r .mod 8) * 128 + (r / 8) * 40)
.endrepeat
rowhi:
.repeat 24, r
        .byte >($0400 + (r .mod 8) * 128 + (r / 8) * 40)
.endrepeat

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
; ax_len bytes between main ax_main and aux ax_aux (both advanced).
_aux_put:
        sec
        bra auxcopy
_aux_get:
        clc
auxcopy:
        ror tmp2                 ; bit 7: main -> aux
@chunk: lda _ax_len
        ora _ax_len+1
        bne :+
        rts
:
        lda _ax_len+1            ; n = min(len, 128)
        bne @full
        lda _ax_len
        cmp #128
        bcc @n
@full:  lda #128
@n:     sta tmp1
        bit tmp2
        bmi @toaux
        lda _ax_aux              ; aux -> main
        sta $3C
        lda _ax_aux+1
        sta $3D
        lda _ax_main
        sta $42
        lda _ax_main+1
        sta $43
        bra @a2
@toaux: lda _ax_main             ; main -> aux
        sta $3C
        lda _ax_main+1
        sta $3D
        lda _ax_aux
        sta $42
        lda _ax_aux+1
        sta $43
@a2:    clc                      ; A2 = the source's last byte
        lda $3C
        adc tmp1
        sta $3E
        lda $3D
        adc #0
        sta $3F
        lda $3E
        bne :+
        dec $3F
:       dec $3E
        php
        sei
        lda tmp2
        asl a                    ; C = 1: main -> aux
        jsr $C311                ; AUXMOVE
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
