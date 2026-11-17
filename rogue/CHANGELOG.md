# ROGUE — changelog

Finished lots, moved out of [TODO.md](TODO.md) on 2026-11-16 (newest first).

## Mockingboard (2026-11-16)

Both binaries play their 14 sounds and 3 tunes on a Mockingboard when one
is present (the E-Z Color card in another slot; the //c's 4c in slot 4):
AYS songs made by `tools/music.py` from the speaker's notes (an effect is
one voice, a tune its melody plus the same line an octave lower), played by
`aysong.asm` on `mb_irq.asm`'s 50 Hz timer interrupt through the ROM's
`$03FE` vector. Nothing waits for a sound any more (the next one replaces
it); S mutes the voices; ESC and Ctrl-RESET stop the service first.
`ROGUE.DHGR` loads at `$2400` and moves its constants and songs to
`$9E8D-$B38C` at start-up (its main RAM had ~400 bytes free).
`tests/test_mockingboard.py`: detection, `$03FE`, 50 Hz ticks, the songs,
the silent speaker, S, the ways out, and on the //e and the //c both DHGR
pages (main and auxiliary banks) equal to the model under the interrupts.

## Way out (2026-11-01)

ESC and Ctrl-RESET go through the library's `apple2_reboot`, which boots the
boot drive's slot read from `$B7E9` (no fixed `$C600` any more;
`tests/test_dhgr.py`: `$B7E9` = `$50` -> `JMP $C500`).

## DHGR version (2026-10-31; ROGUE X2 game view 2026-11-01)

`ROGUE.DHGR` for the //e 128 KB and the //c when no E-Z Color card is
found; the game view the ROGUE X2 way: a 9 × 5 window of large cells
centred on the hero, double buffered.

## Lot 1 (2026-10-31)

POM1's TMS_Rogue ported to the Apple II + E-Z Color card: detection in any
slot (but 3 and the boot drive's), a clear message without the card, sounds
and tunes on the speaker, the core separated from the display
(docs/VIDEO_API.md), the TMS / DHGR / error launcher, a2run --ezcolor tests.
