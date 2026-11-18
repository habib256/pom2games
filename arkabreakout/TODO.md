# ARKABREAKOUT — remaining work

The HGR / 48 KB / DOS 3.3 adaptation now includes ChromaBreak's 60 boards,
difficulties, combo, six capsules, multiball, laser, piercing, two enemies,
vertical paddle and spin, disk scores/progression, Escape selector, demo,
help and two-voice music. Automated coverage runs the NMOS binary and real
AppleMouse II ROMs; a complete Relax campaign is played by paddle steering.

- Validate joystick, separate paddles and AppleMouse II on a physical II+.
- Measure the heaviest Expert frames on hardware; tune the CPU delay budget
  for maximum speed, mouse firmware, repeated lasers and HUD updates together.
- Play full Arcade and Expert campaigns by hand and tune HGR paddle widths,
  rebound feel, bonus frequency and total campaign duration.
- Check HGR fringes and sprite visibility on composite and monochrome monitors.
- Add the graphical fireworks finale and brick-hit particles if the remaining
  48 KB budget permits; the victory text and two-voice fanfare already exist.
- Improve miniature brick visibility on physical composite displays; sector
  previews, names and mouse navigation are implemented.
- Show a message when a level pack or the music cannot be read (disk
  removed or damaged): files now go through DOS's file manager
  (`fm_bload` / `fm_bsave`), which returns an error code instead of
  stopping at the `]` prompt; only the records use it so far (missing
  file: empty table; any write error: "NOT SAVED").
