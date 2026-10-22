; VERHILLE Arnaud — GPL-3.0. Two voices on the one-bit speaker, aligned at $1300.
;
; DOS loads MUSIC once at $1300. music.inc calls each event in main RAM.
; The counted hot loop stays wholly inside an aligned page; DOS page 3
; vectors are preserved. The player is dev/lib/apple2/duet.asm (NMOS 6502);
; tools/generate_music.py picks its just-intonation counts (C4 = 60 turns).
;
; The first include defines the addresses; a second one, with DUET_CODE
; defined and under .org DUET_BASE, assembles the player itself.
.ifndef DUET_BASE
DUET_BASE   = $1300
 ; End of the aligned $1300 player page; tunes begin at $1400.
DUET_JINGLE_LO = $1400
DUET_END    = DUET_JINGLE_LO
.endif
.include "duet.asm"
