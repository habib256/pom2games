; VERHILLE Arnaud — GPL-3.0. Two voices on the one-bit speaker, in page 3.
;
; CHROMA.SYS copies this player to DUET_BASE (startup.s); sound.s calls it
; for every note of a tune. It lives outside the game image because its loop
; counts cycles: here it can never straddle a page, and the game's own
; modules keep their addresses. The player is dev/lib/apple2/duet.asm.
;
; The first include defines the addresses; a second one, with DUET_CODE
; defined and under .org DUET_BASE, assembles the player itself.
.ifndef DUET_BASE
DUET_BASE   = $0310             ; page 3 is free under ProDOS up to $03CF
; The addresses of the sector endings in the AUX bank, low then high bytes,
; fill the end of the free part of page 3 (startup.s writes them).
DUET_JINGLES   = 10
DUET_JINGLE_LO = $03D0-2*DUET_JINGLES
DUET_JINGLE_HI = $03D0-DUET_JINGLES
DUET_END    = DUET_JINGLE_LO
.endif
.include "duet.asm"
