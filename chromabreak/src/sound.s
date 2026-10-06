.setcpu "65C02"
SOUND_SPARE = 27
; Apple II one-bit speaker. Bounded bursts leave the mouse ROM IRQ enabled.
; No ROM WAIT or zero-page workspace. Each burst ends at its original polarity.
.export _sound_event, _sound_tick, _sound_stop
.import _timing_scan
.bss
_sound_active: .res 1
.export _sound_active
_sound_muted: .res 1
.export _sound_muted
remaining: .res 1
elapsed: .res 1
pitch: .res 1
.rodata
periods: .byte 0,35,24,15,29,21,30,34,28,32,30,30
lengths: .byte 0,2,3,3,3,5,5,9,10,12,12,18
.code
_sound_event:
        ldy _sound_muted
        bne done
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

; Play a tune (A/X = events from tools/generate_music.py) on the speaker,
; blocking: two voices, by the player in page 3 (duet.inc). An event is
; three bytes: melody count (0 = silence), bass count, slices; a zero third
; byte ends the tune. IRQs are masked inside a note and served between two;
; when muted the tune is silent but timed. Tunes below $2000 are in the AUX bank (title theme, jingles),
; others in main RAM (the overlay fanfare). play_title stops at a key press
; (the key stays for the title loop).
.export _play_tune, _play_title, _play_jingle
.importzp ptr1, aux_read
.include "levels.inc"
FINE_FONT_CONSTANTS_ONLY = 1
.include "fine_font.inc"
.include "music_offsets.inc"
.include "duet.inc"
TUNES_AUX = LEVELS_AUX+LEVELS_SIZE+FINE_COUNT*FINE_HEIGHT
.export _tunes_aux := TUNES_AUX       ; for the tests
.rodata
; Sector-cleared jingles, one per decade of sectors (generate_music.py).
.define JINGLES TUNES_AUX+TUNE_JINGLE0_OFS, TUNES_AUX+TUNE_JINGLE1_OFS, TUNES_AUX+TUNE_JINGLE2_OFS, TUNES_AUX+TUNE_JINGLE3_OFS, TUNES_AUX+TUNE_JINGLE4_OFS, TUNES_AUX+TUNE_JINGLE5_OFS
jingle_lo: .lobytes JINGLES
jingle_hi: .hibytes JINGLES
.bss
tune_note: .res 3                ; melody, bass, slices
        .res 1                   ; spare: the variables after it stay put
.code
; A = decade (0..5) of the sector just cleared.
_play_jingle:
        tay
        lda jingle_hi,y
        tax
        lda jingle_lo,y
        bra _play_tune
_play_title:
        lda #<(TUNES_AUX+TUNE_TITLE_OFS)
        ldx #>(TUNES_AUX+TUNE_TITLE_OFS)
        ldy #$80
        bra tune_start
_play_tune:
        ldy #0
tune_start:
        sty DUET_KEYS
        sta ptr1
        stx ptr1+1
@note:  lda $C000
        and DUET_KEYS
        bmi @done
        ldy #2
@fetch: lda ptr1+1
        cmp #$20
        bcs @main
        php
        sei
        jsr aux_read
        plp
        bra @got
@main:  lda (ptr1),y
@got:   sta tune_note,y
        dey
        bpl @fetch
        ldy tune_note+2
        beq @done
        lda _sound_muted
        beq :+
        lda #$FF                 ; muted: every event is a silence
:       eor #$FF
        and tune_note
        ldx tune_note+1
        jsr DUET_PLAY
        lda ptr1
        clc
        adc #3
        sta ptr1
        bcc @note
        inc ptr1+1
        bra @note
@done:  rts
; The modules after this one are sensitive to their addresses (spare.s):
; the player left for page 3, these bytes keep them where they were.
        .res SOUND_SPARE
.assert * = $9F5D, lderror, "timing.s moved: adjust SOUND_SPARE (see spare.s)"
