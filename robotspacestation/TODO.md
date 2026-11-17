# ROBOT SPACE STATION — to do

*[← README](README.md)* · rules: [docs/SPEC.md](docs/SPEC.md) · done: [CHANGELOG.md](CHANGELOG.md)

## Real hardware

- [ ] Try it on a real //e enhanced with an AppleMouse card, then on a //c:
      mouse (pointer speed, clicks during large drawings), saving
      `RSS.SAVE`, reading `RSS.ROOMS`.
- [ ] On the //c, a very short click during a large drawing can be lost
      (the built-in mouse counts through interrupts, masked during
      auxiliary memory accesses): measure it on the machine.

## Content

- [ ] Chips supplied by the station (a starter library).
      Not done on 2026-10-30: ready-made chips would give away half the
      solutions; to be decided (for example a single one, the bump flip-flop).

## Interface

- [ ] A test by a player who discovers the game: are the briefings and
      hints enough? (especially missions 7, 15, 16, 20)

## Memory (as of 2026-10-31: overlays)

Done: page 2 (`$4000-$5FFF`) is an overlay window (PLAY = room and drones,
FRONT = title, help, briefing, reading the save), stored in auxiliary
memory (`RSS.OVL`) and copied back in 0.11 s on a screen change
(docs/SPEC.md, "Memory"). Free: main 775 B, PLAY 225 B (with
DHGRSPRCODE), FRONT ~5.6 KB, L8 ~260 B; `sprbuf.s` (unused) removed.

Reserves still unused, should more ever be needed:
- [ ] auxiliary `$0800-$1FFF` (6 KB) and `$905E-$9FFF` (~4 KB): a third
      overlay (the lab: burning, opening a chip, erasing) or data;
- [ ] auxiliary language card (16 KB + 4 KB): only as a data reserve
      (it needs ALTZP, hence a copy, no execution);
- [ ] the save (`persist`, 2.1 KB at `$1400`) in auxiliary memory would
      free low memory for resident code, but compiling the boards reads
      the chips every time: to be measured.
