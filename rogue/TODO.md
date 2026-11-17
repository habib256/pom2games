# ROGUE — next lots

What is done is in [CHANGELOG.md](CHANGELOG.md).

- **DHGR version**, what remains: the scroll shows only the window (like
  ROGUE X2; the whole map in small, while the key is held, would be more
  useful); the //c flips pages without waiting for the beam (a picture can
  tear: its mouse's VBL interrupt would allow it); the lit floor is black as
  on the TMS (a discreet pattern would show the torch's light); the HUD does
  not have ROGUE X2's per-line colours.
- **Mockingboard**, what remains: tunes written for three voices (today the
  melody and the same line an octave lower); a test on a real card (with the
  E-Z Color next to it on a II+, the 4c on a //c).
- **Saved game**: write the state (the game's zero page + LOWBSS, ~600 bytes)
  to a file through RWTS (`rwts_sectors`, `dos33patch.py --sectors`).
- **Real hardware**: try an E-Z Color (or a replica) on a II+ and a //e,
  slot 3 included; check the notice on the Apple screen.
- Optional step click (off by default); ZQSD / HJKL keys as an option (today
  IJKL and the arrows, H = help as in POM1).
