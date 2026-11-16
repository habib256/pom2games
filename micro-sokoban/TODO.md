# MICRO-SOKOBAN — TODO

Status on 2026-10-07: **no open task**. Controls and technical details are in
the [README](README.md); level sources and solutions in
[levels/README.md](levels/README.md).

What is done is in [CHANGELOG.md](CHANGELOG.md).

## Next up / ideas

None of these is started. Each is grounded in a comment, a release note or a
known limit; the resident budget (about 155 bytes free, 230 in `BOOTCODE`)
means any addition must first free memory.

- **Real-hardware check.** Every release note says the tests validate
  emulated execution only; the two-voice title music "has not yet been heard
  on real hardware" (1.2 notes), and the disk timings are POM2 cycles, not a
  physical Disk II. Boot the image on an Apple II+ or //e, listen to the duet
  and the game sounds, and time the boot.
- **Freeze deadlocks.** The DEADLOCK warning covers dead squares only; a crate
  frozen against another (a 2 × 2 block, for example) is not detected, while
  `tools/solver.py` already has the freeze rule. Worth porting only if it fits
  the budget.
- **Partial recovery of a records file.** A file with one unreadable sector is
  dropped whole (empty profile, rewritten at the next save); the records of
  its readable sectors could be kept instead.
- **More collections.** The build pipeline is generic (`COLLS` in the
  Makefile, `PREFIX:HUD:FILE` arguments of `tools/micro_sokoban_levels.py`),
  but the SOK2 file, the fingerprints and the demo table are sized for the
  four current collections, so a fifth one means a new save format.

## Constraints and known limits

- Apple II+ 48 KB, HGR, DOS 3.3; keyboard and joystick.
- No scrolling: every level fits in 20 × 12 cells, clear of the HUD corners.
  Levels too tall are turned when that lets them fit; the others are left out.
  Their original numbers are kept.
- The DEADLOCK alert detects the dead squares computed from the goals,
  including corners and wall edges without a goal. Blocks between crates
  (a 2 × 2 freeze, for example) stay outside this detection; the solver
  detects them.
- Undo/Redo keeps the last 1024 moves in memory only. The history starts empty
  after a reboot, a profile change or a tutorial replayed during a game
  (position and counters are given back). If the start of the level has been
  forgotten, RESTART reloads the level instead of rewinding it.
- A records file with one unreadable sector is dropped whole (empty profile,
  rewritten at the next save): the records in the sectors still readable are
  not recovered.
- With the same number of solved levels, the ranking compares the total of
  best moves; the result therefore depends on the levels chosen.

## Verification

`make test` builds the disk and checks in a2run the exit to BASIC, the HGR
pages and monochrome silhouettes, the menu texts, resume, the tutorial, the
options, the profiles, the ranking, the returns to a game (tutorial,
SOLUTION, profiles, joystick, "SAVING", counters, typed-ahead keys), the
damaged files (impossible length, missing or short file, inconsistent
ranking) and the solutions of the 454 levels. The tests also cover corrupted
saves, migrations, write-protected disks and writes that change nothing.

Screenshots and joystick scenarios use the shared a2run/a2shot tools. The
disk timings in POM2 are described in the README; they measure the emulated
processor and are not measurements on a physical machine.
