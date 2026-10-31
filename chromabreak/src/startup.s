; ProDOS SYS entry $2000. Relocate backwards: source/destination may overlap.
.setcpu "65C02"
SYSRELOC_DOWN_FAST = 1    ; tail + whole pages: ~0.7 s faster boot
.include "sysreloc.inc"   ; dev/lib/prodos
.include "levels.inc"
.include "duet.inc"
.segment "CODE"
        sysreloc_prologue
        ; The two-voice player goes to page 3 (duet.inc).
        sysreloc_copy_bytes duet_image, DUET_BASE, duet_size
        ; Keep the 2 KiB DHGR table image below graphics, freeing game memory.
        ; Copy it before relocating the overlapping SYS payload.
        sysreloc_copy_pages font_payload, $0800, 8
        ; The level bank and font go to AUX $0A00 before the payload moves
        ; (I stays set up to the game).
        sysreloc_copy_pages_aux levels_payload, LEVELS_AUX, >(AUX_BANK_SIZE+255)
        sysreloc_copy_down payload, $6000, size
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
