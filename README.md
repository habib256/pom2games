# pom2games

Apple II programs on DOS 3.3 or ProDOS disks, for
[POM2](https://github.com/habib256/pom2) or a real Apple II. Most of them are
ports of programs from [POM1](https://github.com/habib256/pom1), adapted to
the Apple II's native video.

| Folder | Program | Machine | Disk |
|---|---|---|---|
| [`chromabreak/`](chromabreak/) | 16-colour DHGR brick-breaker, AppleMouse and keyboard | Apple //e enhanced or //c 128 KB / ProDOS | `dist/CHROMABREAK.po` |
| [`arkabreakout/`](arkabreakout/) | HGR brick-breaker: 60 sectors, 6 bonuses, combos, joystick/paddles/AppleMouse II | Apple II+ 48 KB | `dist/ARKABREAKOUT.dsk` |
| [`micro-sokoban/`](micro-sokoban/) | MICRO-SOKOBAN, a 5-level tutorial + 454 Microban I to IV levels, saved Hall of Fame, joystick or keyboard | Apple II+ | `dist/MICRO-SOKOBAN.dsk` |
| [`chess/`](chess/) | Chess against the computer or two players | Apple II+ | `dist/CHESS.dsk` |
| [`maze3d/`](maze3d/) | 3D wireframe dungeon crawler, double-buffered HGR | Apple II+ | `dist/MAZE3D.dsk` |
| [`light3dball/`](light3dball/) | Ball in a 3D HGR corridor, five levels, mouse or keyboard and final targets | Apple II+ 48 KB | `dist/LIGHT3DBALL.dsk` |
| [`pinball/`](pinball/) | Bill Budge's Pinball Construction Set, editor and 6502 engine adapted to ca65/ld65 | Apple II+ 48 KB or //c, mouse or joystick | `dist/PINBALL.dsk` |
| [`wilderness/`](wilderness/) | Reimplementation of Wilderness (Electric Transit, 1985): 3D view, original sprites, walking/swimming, items, load and thermal simulation | Apple II+ 48 KB / DOS 3.3 | `wilderness/build/WILDERNESS.dsk` (not in dist/) |
| [`dirtbike/`](dirtbike/) | Side-view motocross inspired by Dirt Bike (Mac): 30 tracks from very easy to very hard, Verlet physics, pixel-smooth HGR scrolling, joystick or keyboard | Apple II+ 48 KB / DOS 3.3 | `dist/DIRTBIKE.dsk` |
| [`mcs/`](mcs/) | Music editor inspired by Music Construction Set: two HGR staves, keyboard, speaker and saving | Apple II+ 48 KB / DOS 3.3 | `dist/MCS.dsk` |
| [`snake/`](snake/) | Snake in C (cc65) | Apple II+ | `dist/SNAKE.dsk` |
| [`logo/`](logo/) | LOGO V2.6: HGR turtle, text / mixed / graphics, 40 or 80 columns | Apple //e (80 col.) or II+ (40 col.) | `dist/LOGO.dsk` |
| [`dev/examples/hgr/`](dev/examples/hgr/) | Animated HGR example: masked sprite, counter, keyboard, frame pacing | Apple II+ / IIe / IIc | `dist/HGR.dsk` |
| [`dev/examples/dhgr/`](dev/examples/dhgr/) | 16-colour palette and DHGR grid | Apple IIe 128 KB / IIc | `dist/DHGR.dsk` |
| [`dev/examples/hello/`](dev/examples/hello/) | Starter program, assembly and C on the same disk | Apple II+ | `dist/HELLO.dsk` |

Two game profiles are defined: **Apple II+ 48 KB / DOS 3.3** for
Arkabreakout and the classic ports, and **Apple //e enhanced 128 KB / ProDOS**
for CHROMABREAK. The first uses HGR and keyboard/paddle; the second uses
16-colour DHGR and the AppleMouse II, with support for the //c 128 KB's
built-in mouse in the same ProDOS profile.

All the disks are in [`dist/`](dist/), ready to use: boot from one and the
program starts. Each folder has its own `README.md` (controls, differences
from the original) and, for the games, a `TODO.md` of planned improvements.

MICRO-SOKOBAN 1.2 is available in the
[GitHub releases](https://github.com/habib256/pom2games/releases/tag/1.2), with
its bootable disk and the [release notes](docs/releases/1.2.md).
CHROMABREAK 1.0 is too, under the tag
[`chromabreak-1.0`](https://github.com/habib256/pom2games/releases/tag/chromabreak-1.0),
with its ProDOS disk and its [release notes](docs/releases/chromabreak-1.0.md).
DIRTBIKE 1.0 is out under
[`dirtbike-1.0`](https://github.com/habib256/pom2games/releases/tag/dirtbike-1.0),
with its DOS 3.3 disk.

## Building

    make profile-ii-plus # Apple II+ 48 KB / DOS 3.3 games
    make profile-iie-prodos # CHROMABREAK, //e enhanced 128 KB / ProDOS
    make test-chromabreak # ProDOS volume and //e tests when a2shot is available
    make                 # every disk, into dist/
    make -C chess        # just one (it goes into dist/ too)
    make -C chess run    # run it in an installed POM2 (/Applications/POM2.app)
    make test            # fast tier: build everything, then each program's
                         # `make test` and the quick dev/ checks
                         # (HGR, frame pacing, examples, assets, budgets)
    make test-long       # long tier: ARKABREAKOUT campaign, the 454
                         # MICRO-SOKOBAN levels, LIGHT3DBALL campaign, WILDERNESS journeys...
    make test-all        # both tiers (the former `make test`)
    make test-changed    # only what the working tree changes (BASE=<ref>,
                         # default origin/main; LONG=1 adds the long tier)
    make test-arkabreakout # collisions, bonuses, levels, paddle and DOS exit
                           # (test-<game> = fast tier, test-<game>-long = long)
    make test-chess      # castling, promotion, fifty-move rule, dead material
    make test-mcs        # music editor, save/reload and sound
    make test-hgr        # primitives, gfx text, sprite engine and archive
    make test-frame      # frame pacing, delays and fallback when VBL is stuck
    make test-hgr-example # animation, pause/resume and return to DOS
    make test-dhgr       # DHGR validation in a2shot (macOS arm64)
    make test-assets     # font (dev/tools/fonts.py --check) and asset conversion
    make test-techniques # fhpack, fdraw and compiled-sprite comparison (HGR/6502)
    make bench           # measures the primitives (dev/bench); bench-check compares
                         # against the budgets in dev/bench/baseline.json
    make check           # rebuild everything, fail if dist/ does not match
    make clean           # delete the build/ folders (the disks stay)
    make distclean       # also delete dist/*.dsk and dist/*.po

Requirements: [cc65](https://cc65.github.io/) (`brew install cc65`, or
`apt install cc65`) and python3; C/C++ compilers and zlib for `make test`
(C for `dev/tools/a2run`, C++ for the fhpack tests). The //e and DHGR tests go
through `dev/tools/a2shot` (macOS arm64, libslirp via brew): `make test-dhgr`
requires it, `make test` skips them when it is missing.
The repository depends on no other folder. Builds are deterministic: the
`dist/` images, made on macOS, rebuild byte for byte with Ubuntu 24.04's
cc65 2.19.

Continuous integration (`.github/workflows/build.yml`) runs `make check` then
`make test-all` on Ubuntu on every push: a source change committed without
the rebuilt `dist/` fails the build.

## Tests: fast first

Every program has two test tiers:

- `make -C <game> test`: fast (one or two minutes at most), to run after
  every change; it is the reflex of the development loop;
- `make -C <game> test-long`: full campaigns, every level, long playthroughs;
  the target may be empty.

A new game follows the same convention (see `dev/cc65/apple2.mk` and the
`wargalagaii/Makefile` skeleton) and is added to `TESTED` in the root
Makefile. Before shipping, `make test-changed` runs the fast tier of only the
programs affected: those with a changed file in their folder, or whose disk
image, rebuilt from scratch, differs from BASE's (a `dev/lib` change that
reaches their bytes); plus `make test-dev` if `dev/` changed. It prints, for
each program, why it is tested or skipped.
`make test-all` remains the full check (about an hour).

## dev/

[`dev/`](dev/) is the shared toolbox for developing on the Apple II:

- `dev/lib/apple2` and `dev/lib/apple2c`: keyboard, text, HGR, clean return
  to DOS or to a BASIC menu, sound, joystick, DOS commands (BLOAD / BSAVE),
  in assembly and in C;
- `dev/lib/prodos` and `dev/lib/mouse`: ProDOS MLI, SYS exit and AppleMouse II;
- `dev/tools/prodos`: bootable ProDOS volume builder and reader;
- `dev/lib/font`: the Beautiful Boot 8x8 font, one master table sliced on
  demand (assembly, C and `dev/tools/fonts.py`);
- `dev/lib/hgr`: HGR text, sprites and tables (assembly);
- `dev/lib/hgrc` and `dev/lib/gfx`: HGR/DHGR C graphics runtime and geometry;
- `dev/lib/math`: multiply, divide, square root, random numbers and decimal
  conversion (assembly);
- [`dev/examples/hgr`](dev/examples/hgr/): animated example, keyboard, counter,
  masked sprites, double buffering and frame pacing as in the model;
- [`dev/examples/dhgr`](dev/examples/dhgr/): DHGR palette and grid on a
  //e 128 KB or //c;
- `dev/cc65`: linker configurations, C startup and `apple2.mk`, the Makefile
  fragment shared by every program;
- `dev/tools/dos33.py`: builds DOS 3.3 disks and reads their files back;
- `dev/tools/a2test.py`: the shared test harness (ld65 labels, a2run/a2shot
  runs, memory dump decoding);
- `dev/tools/assets`, `dev/tests`, `dev/bench`: PNG/PPM to HGR/DHGR
  conversion, library tests and performance budgets;
- `dev/tools/a2shot`: runs a disk headless on the POM2 core, types on the
  keyboard and takes screenshots — this is how the ports are tested;
- `dev/tools/a2run`: the same in portable C (Linux, macOS), with disk writes
  to check saves;
- `dev/examples/hello`: starter program in assembly and C.

The speed/RAM trade-off switches offered by the libraries (fast variants that
use more RAM, or frugal ones) are listed in [`dev/lib/ABI.md`](dev/lib/ABI.md):
each program picks the variant that fits its goals and memory limits.

## Licences and credits

Code: GPL-3.0 ([LICENSE](LICENSE)), like POM1 and POM2 from which it derives
(VERHILLE Arnaud).

- Microban levels: David W. Skinner.
- Chess pieces: cc65-Chess by Stefan Wessels, Apple II port by Oliver
  Schmidt, drawings by Frank Gebhart.
- Monster sprites and emotes: SCROLL-O-SPRITES by Quale (CC-BY-3.0).
- 8x8 font: Beautiful Boot, Michael Pohoreski.

The Apple II / //e / Disk II ROMs (`dev/tools/a2shot/roms/`) and the DOS 3.3
system tracks (`dev/tools/dos33_system.bin`, also present on every disk) are
works of Apple Computer, Inc. They are taken from POM2, where they are already
published, so that the repository builds and tests on its own.
`dev/tools/a2shot/sdk/` contains the compiled POM2 core (GPL-3.0).
