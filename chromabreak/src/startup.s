; ProDOS SYS entry $2000. Relocate backwards: source/destination may overlap.
.setcpu "65C02"
.include "levels.inc"
.include "duet.inc"
.segment "CODE"
        cld
        sta $C002
        sta $C004
        sta $C000
        ldx #$FF
        txs
        ; The two-voice player goes to page 3 (duet.inc).
        ldx #duet_size
duet_copy:
        lda duet_image-1,x
        sta DUET_BASE-1,x
        dex
        bne duet_copy
        ; Keep the 2 KiB DHGR table image below graphics, freeing game memory.
        ; Copy it before relocating the overlapping SYS payload.
        lda #<font_payload
        sta $06
        lda #>font_payload
        sta $07
        stz $08
        lda #$08
        sta $09
        ldx #8
        ldy #0
font_copy:
        lda ($06),y
        sta ($08),y
        iny
        bne font_copy
        inc $07
        inc $09
        dex
        bne font_copy
        ; The level bank and font go to AUX $0A00 before the payload moves.
        lda #<levels_payload
        sta $06
        lda #>levels_payload
        sta $07
        lda #<LEVELS_AUX
        sta $08
        lda #>LEVELS_AUX
        sta $09
        ldx #>(AUX_BANK_SIZE+255)
        ldy #0
        sei
        sta $C005
levels_copy:
        lda ($06),y
        sta ($08),y
        iny
        bne levels_copy
        inc $07
        inc $09
        dex
        bne levels_copy
        sta $C004
        lda #<(payload+size-1)
        sta $06
        lda #>(payload+size-1)
        sta $07
        lda #<($6000+size-1)
        sta $08
        lda #>($6000+size-1)
        sta $09
        lda #<size
        sta $0A
        lda #>size
        sta $0B
        ldy #0
copy:   lda ($06),y
        sta ($08),y
        lda $06
        bne :+
        dec $07
:       dec $06
        lda $08
        bne :+
        dec $09
:       dec $08
        lda $0A
        bne :+
        dec $0B
:       dec $0A
        lda $0A
        ora $0B
        bne copy
        jmp $6000
payload: .incbin "game.bin"
size=*-payload
font_payload: .incbin "tables.bin"
.assert *-font_payload=2048, error, "DHGR table image must be 2 KiB"
levels_payload: .incbin "levels.bin"
.assert *-levels_payload=LEVELS_SIZE, error, "level bank size"
; The Beautiful Boot font planes follow the boards in AUX (finetext.s).
.include "fine_font.inc"
; Then the title theme and the sector endings (sound.s play_tune reads them there).
.include "music_offsets.inc"
.assert LEVELS_AUX+*-levels_payload=LEVELS_AUX+LEVELS_SIZE+FINE_COUNT*FINE_HEIGHT, error, "tunes follow the font"
.include "music_aux.inc"
AUX_BANK_SIZE = *-levels_payload
.assert LEVELS_AUX+AUX_BANK_SIZE<=$2000, error, "AUX bank reaches AUX video memory"
; The player of those tunes, assembled for page 3.
duet_image:
DUET_CODE = 1
.org DUET_BASE
.include "duet.inc"
; Then the table of the sector endings, at the end of the free part of page 3.
        .res DUET_JINGLE_LO-*
TUNES_AUX = LEVELS_AUX+LEVELS_SIZE+FINE_COUNT*FINE_HEIGHT
.define ENDINGS TUNES_AUX+TUNE_JINGLE0_OFS, TUNES_AUX+TUNE_JINGLE1_OFS, TUNES_AUX+TUNE_JINGLE2_OFS, TUNES_AUX+TUNE_JINGLE3_OFS, TUNES_AUX+TUNE_JINGLE4_OFS, TUNES_AUX+TUNE_JINGLE5_OFS, TUNES_AUX+TUNE_JINGLE6_OFS, TUNES_AUX+TUNE_JINGLE7_OFS, TUNES_AUX+TUNE_JINGLE8_OFS, TUNES_AUX+TUNE_JINGLE9_OFS
        .lobytes ENDINGS
        .hibytes ENDINGS
duet_size = *-DUET_BASE
.assert duet_size = $03D0-DUET_BASE, error, "ten sector endings fill page 3 up to the ProDOS vectors"
.reloc
.assert duet_size<256, error, "duet_copy moves less than a page"
