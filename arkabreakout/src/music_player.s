; Two-voice NMOS player and tunes loaded once, below the DOS sector pack.
.segment "CODE"
.org $1300
.include "duet.inc"
DUET_CODE = 1
.include "duet.inc"
.align $100
.assert * = $1400, error, "tune bank address"
.include "music_aux.inc"
.include "music_fanfare.inc"
.assert * <= $1800, error, "music overlaps the sector pack"
