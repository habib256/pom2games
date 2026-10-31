; WARGALAGA II -- the PT3 player and its song, in aux memory.
; dev/lib/apple2/pt3 (Vince Weaver's pt3_lib, 0BSD) and build/song.pt3
; (tools/pt3.py) are linked at aux $2000 (segment AUXMUS, memory AUXM:
; build/game.bin.mus, appended to WG2.AUX by the Makefile), so the main
; memory keeps its room for the later lots. sound.s calls them through
; tramp.s's bank-switching trampolines from the timer 1 interrupt.
; Separate module: the player's labels stay out of game.s's.
.setcpu "6502"
.export pt3_init_song, pt3_tick
.exportzp AY_REGISTERS

PT3_ZP = $D0                    ; $D0-$EF (game.cfg leaves $D0-$FF to this)

.segment "AUXMUS"
.include "pt3/pt3.s"

.segment "AUXSONG"              ; (page aligned: the decoder wants it)
PT3_LOC:
.incbin "song.pt3"
