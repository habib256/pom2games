; Blocking only on static screens / sector transitions, never during play.
.include "music_offsets.inc"
.include "duet.inc"
MUSIC_BANK = $1400
.code
music_load:
        jsr dos_cmd_new
        lda #<music_load_command
        ldy #>music_load_command
        jsr dos_cmd_add
        jmp dos_cmd_run
music_title:
        lda #$80
        sta DUET_KEYS
        lda #<MUSIC_BANK
        ldx #>MUSIC_BANK
        jmp music_play
music_jingle:
        lda demo
        bne music_done
        lda level
@decade:cmp #10
        bcc @pick
        sec
        sbc #10
        bcs @decade
@pick:  tax
        lda #0
        sta DUET_KEYS
        lda jingle_lo,x
        pha
        lda jingle_hi,x
        tax
        pla
        jmp music_play
music_victory:
        lda #0
        sta DUET_KEYS
        lda #<(MUSIC_BANK+TUNES_SIZE)
        ldx #>(MUSIC_BANK+TUNES_SIZE)
music_play:
        sta asset_ptr
        stx asset_ptr+1
        lda sound_muted
        ora demo
        bne music_done
@note:  lda KBD
        and DUET_KEYS
        bmi music_done
        ldy #2
        lda (asset_ptr),y
        beq music_done
        pha
        dey
        lda (asset_ptr),y
        tax
        dey
        lda (asset_ptr),y
        sta scratch
        pla
        tay
        lda scratch
        jsr DUET_PLAY
        lda asset_ptr
        clc
        adc #3
        sta asset_ptr
        bcc @note
        inc asset_ptr+1
        bne @note
music_done:
        rts
.rodata
music_load_command: .asciiz "BLOAD MUSIC,A$1300"
jingle_lo:
.byte <(MUSIC_BANK+TUNE_JINGLE0_OFS),<(MUSIC_BANK+TUNE_JINGLE1_OFS),<(MUSIC_BANK+TUNE_JINGLE2_OFS),<(MUSIC_BANK+TUNE_JINGLE3_OFS),<(MUSIC_BANK+TUNE_JINGLE4_OFS)
.byte <(MUSIC_BANK+TUNE_JINGLE5_OFS),<(MUSIC_BANK+TUNE_JINGLE6_OFS),<(MUSIC_BANK+TUNE_JINGLE7_OFS),<(MUSIC_BANK+TUNE_JINGLE8_OFS),<(MUSIC_BANK+TUNE_JINGLE9_OFS)
jingle_hi:
.byte >(MUSIC_BANK+TUNE_JINGLE0_OFS),>(MUSIC_BANK+TUNE_JINGLE1_OFS),>(MUSIC_BANK+TUNE_JINGLE2_OFS),>(MUSIC_BANK+TUNE_JINGLE3_OFS),>(MUSIC_BANK+TUNE_JINGLE4_OFS)
.byte >(MUSIC_BANK+TUNE_JINGLE5_OFS),>(MUSIC_BANK+TUNE_JINGLE6_OFS),>(MUSIC_BANK+TUNE_JINGLE7_OFS),>(MUSIC_BANK+TUNE_JINGLE8_OFS),>(MUSIC_BANK+TUNE_JINGLE9_OFS)
