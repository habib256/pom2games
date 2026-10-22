# Evaluating HGR techniques

This suite compares **fhpack**, **fdraw** and a prototype of **compiled
sprites** with the existing `pom2games` code paths. The prototypes stay in the
tests; no production library uses them.

```sh
make test-techniques
python3 dev/tests/techniques/run.py --suite graphics
python3 dev/tests/techniques/run.py --suite sprites
python3 dev/tests/techniques/run.py --suite compression --out /tmp/compression.json
```

`make test` includes `test-techniques`. The dedicated command rebuilds the two
disks used for the captures. Prerequisites: cc65, Python 3, a C compiler for
a2run and a C++ compiler for fhpack. No download or external Python module is
needed. The generated programs, disks and measurements are in `build/`,
ignored by Git.

## Results and decisions

Measurements of 7 October 2026: cc65 V2.18, `-Oirs`, CPU **NMOS 6502 in a2run**.
The detailed data are in [RESULTS.json](RESULTS.json).
The suite validated **123 comparison scenarios, i.e. 304 measured runs**.
Times in milliseconds are emulated cycles converted at 1,020,484 Hz, not run
times on the Mac.

| Technique | Result | Proposed decision for `dev` |
|---|---|---|
| fhpack | Four game captures: 8 KB become 637–1,747 bytes; DOS loading with decompression 2.57–3.19 times faster | **To integrate as an option of the asset pipeline**, keeping the raw file if compression makes it larger |
| fdraw lines | 10.4–14.4 times faster on the long diagonals of the C API; 2.4–2.7 times against maze3d's assembler | **Targeted port of the lines worth considering**; check the pixel choices and preserve the coordinate contract |
| fdraw rectangles and clear | About 1.3–1.4 times faster; full FAST package of 5,108 bytes | **Does not justify a global replacement** of the current primitives |
| Compiled sprites, drawing only | About 2.6–4.4 times faster at the representative position; +1.3 to +4.6 KB per shape with seven phases | **Option for a few very frequent sprites**, when the memory budget allows |
| Compiled sprites with save/draw/restore | Speed ratio 0.95–1.01 on the three synthetic shapes; 0.99 on the demos' ship | **Keep the current masked engine** for animation over a background |

### Compression and loading

| HGR capture | Raw | fhpack `-9 -h` | Raw BLOAD | BLOAD + decompression |
|---|---:|---:|---:|---:|
| Arkabreakout, title | 8,192 B | 1,373 B | 5,036 ms | 1,826 ms |
| Arkabreakout, after space | 8,192 B | 637 B | 5,036 ms | 1,654 ms |
| Micro-sokoban, title | 8,192 B | 1,747 B | 5,036 ms | 1,961 ms |
| Micro-sokoban, after space | 8,192 B | 785 B | 5,036 ms | 1,580 ms |

The captures come from the HGR memory of the current disks, after
`wait:1100`, or `wait:1100 key:" " wait:60`. Their SHA-256 hashes are
recorded. "After space" means this exact sequence, without assuming any game
state. The corpus adds an empty image, a repetitive pattern and deterministic
noise. The noise grows to **8,292 bytes**: a future tool must keep the raw
file in this case.

The FAST decompressor takes **194 bytes**, against **186** for SMALL. On the
game captures, decompression alone takes about 158–173 ms. An unrolled RAM
copy of the raw image takes about **74 ms** (75,520 cycles). Compression
therefore speeds up **disk loading** and reduces storage; it does not replace
a fast RAM copy for each frame of an animation.

The disk tests really use the DOS 3.3 BLOAD, with a boot binary of the same
size in both variants to keep the placement of the IMAGE file. The compressed
path loads into page 1, then decompresses into page 2. It therefore uses a
video page as a temporary buffer. An integration must choose a source buffer
compatible with the game and double buffering. The times apply to a2run's
Disk II and this file layout; they do not predict the times of a ProDOS hard
disk or another loader.

### Graphics primitives

| Operation, page 1 | Current | fdraw FAST | Ratio |
|---|---:|---:|---:|
| Horizontal line 280 px | 3,771 cycles | 903 | 4.18 |
| Vertical line 192 px | 13,215 | 8,581 | 1.54 |
| Diagonal (0,0) → (279,191), C API | 270,506 | 25,981 | 10.41 |
| Rectangle 140 × 16 | 6,867 | 5,317 | 1.29 |
| HGR clear | 53,561 | 39,789 | 1.35 |
| Long maze3d diagonal, extracted assembler | 45,419 | 16,771 | 2.71 |

fdraw FAST and SMALL are compiled from the pinned Merlin sources. `merlin.py`
adapts the directives, local labels and placement to ca65. The instructions
and algorithms are kept. fdraw's 16 private scratch bytes are allocated
outside the cc65 scratch, and the segment is aligned. Both variants include
**the whole package** here: 5,108 bytes for FAST, 4,352 for SMALL. A port of
a single family could reduce this cost; that potential gain is not measured
here.

Lines are checked for their endpoints, their number of points, their
connectivity and their distance to the ideal line. Some rounding choices
differ from the current Bresenham: the reversed case produces six different
pixels. The tests record this difference without mistaking it for an
incorrect line. Rectangles are compared byte by byte on the visible lines.
The fdraw clear does not treat the memory holes like `hgr_clear`: the visible
result is identical, but 512 bytes of holes differ in FAST.

The maze3d comparison extracts **the routine actually used by the game**. It
is also checked against an independent Bresenham. The game converts its
virtual coordinates of eight pixels into HGR groups of seven pixels; fdraw
works directly in HGR coordinates. The plots therefore differ more: a
replacement in the game needs visual validation, even when the endpoints
match.

### Compiled sprites

| Shape / operation, x=45 | Current | Compiled | Ratio | Extra binary |
|---|---:|---:|---:|---:|
| Ship 8 × 8, XOR | 1,198 cycles | 461 | 2.60 | 1,336 B |
| Ship 16 × 16, masked | 4,173 | 943 | 4.43 | 3,516 B |
| Tile 16 × 16, masked | 4,173 | 1,208 | 3.45 | 4,572 B |
| Real ship from the demos 21 × 9, XOR | 1,759 | 584 | 3.01 | 1,821 B |
| Ship 16 × 16, save/draw/restore | 8,090 | 8,007 | 1.01 | 3,519 B |

The prototype generates seven unrolled routines, with immediate data and masks
and transparent bytes skipped. It is an **original implementation of the
HiSprite technique**, adapted to our ABI; HiSprite's Python 2 generator is
neither copied nor run.

The reference is the fast assembler kernel of the current pre-shifted sprites,
with the same parameter preparation. For the cycle over a background, the
reference uses `hgr_msu_run`, which combines save and draw, then restores the
background. The prototype has to save separately, draw, then restore: this
work wipes out almost all the gain of compiled drawing.

The seven phases, coordinates beyond 255, both pages, preservation of the
palette bit and right/bottom clipping are checked. At the edges, the
prototype falls back to the generic kernel: these cases gain no speed. The
quoted gains concern drawing alone, without managing a complete multi-sprite
engine, page flipping or waiting for VBL.

## Checks and limits

- The markers exclude initialisation and the twelve cycles of the measurement
  calls. The costs of parameters and calls remain included.
- The tests check the framebuffer, the inactive page and, except for the
  fdraw clear, the memory holes. Compression with `-h` must restore the
  8,192 bytes exactly, in page 1 and in page 2.
- The reports keep cycles, linked sizes, RAM and zero page, compiler,
  revisions and hashes of the upstream sources. The sizes are those of the
  complete test programs; they do not count the video pages or the reserved C
  stack. The `code_bytes` field includes the whole FDRAW segment, so its
  internal tables and buffers too.
- The tests fail on an incorrect result. They set no automatic speed
  threshold: this suite is for evaluating candidates, while
  `make bench-check` guards the budgets of the production libraries.
- This evaluation covers HGR / 6502. No result is extrapolated to DHGR, the
  65C02 or the IIgs.

The qboot/prorwts loaders and the a2render prototype are not included: the
three priorities chosen are HGR compression, fast primitives and compiled
sprites. Evaluating the loaders would require a disk format and a precise
loading contract; a2render would require a separate textured-rendering
prototype.

## DHGR research — 8 October 2026

A separate exploration compared these techniques with the repository's DHGR
code. The prototypes stayed in `/tmp/pom2-dhgr-research`, without changing
the libraries or the performance references. The measurements below use
cc65 `-Oirs` and the 65C02 of a2shot's IIe core.

### Clearing: measured gain

A prototype unrolls the writes over the 32 blocks of 256 bytes of a bank,
with absolute indexed addressing and two paths for the two video pages. It
keeps the four bytes of the colour pattern and treats the memory holes like
the current routine. Like it, it masks interrupts during the operation.

| Clear, colour 9 | Current | Prototype | Ratio |
|---|---:|---:|---:|
| Page 1, main + aux | 207,861 cycles | 88,171 cycles | 2.36 |
| Page 2, main + aux | 207,861 cycles | 88,169 cycles | 2.36 |

The linked program gains 393 bytes of code, with no increase in RAM or zero
page. Each variant passed 33 checks: the 16 colours on each of the two pages,
then a `$FF` pattern keeping bit 7. The checks compare the 32 KB of video
(active and inactive pages, main and aux, holes included) and verify that
RAMRD/RAMWRT return to main. This gain concerns clearing, not the full frame
rate of a game; CHROMABREAK does not redraw its whole screen every frame.

### fhpack: compression possible, loading not measured

Each 16 KB DHGR capture was split into two 8 KB banks, compressed with
`fhpack -c -9 -h`, then decompressed on the host and compared byte by byte,
bit 7 and holes included.

| Capture of the displayed page | Raw | Two compressed streams |
|---|---:|---:|
| DHGR.dsk introduction | 16,384 B | 1,212 B |
| DHGR.dsk animation | 16,384 B | 1,490 B |
| CHROMABREAK.po title | 16,384 B | 2,511 B |
| CHROMABREAK after space | 16,384 B | 3,559 B |

Sequences: `wait:2600`, then for the animation `key:" " wait:1800`, and for
CHROMABREAK after space `key:" " wait:600`. The page is selected according to
the PAGE2 softswitch. These names describe the sequences, without checking
the internal state of the game.

The upstream 6502 decoder reads LZ references from the destination: enabling
only aux RAMWRT is therefore not enough. A first integration could decompress
each bank into a main buffer compatible with `$2000` or `$4000`, then transfer
the auxiliary bank. A direct aux decoder would require separate handling of
source reads, reference reads and writes, as well as safe execution during
RAMRD switches. The complete ProDOS load, the buffer and the aux transfer
remain to be measured. These screens are currently built by code: compressing
them would be a new presentation strategy, not the speed-up of a raw image
load already present in CHROMABREAK.

### Lines, rectangles and sprites: porting leads

fdraw targets 280 × 192 HGR. Its principles (incremental addresses, prepared
masks, specialised loops) can guide a DHGR engine, but its routines do not
directly replace ours. The DHGR fallback `gfx_line.c` goes through `gfx_plot`
for each diagonal point; the colour backend then goes through a 1 × 1
rectangle. The HGR backend now selects `gfx_line_hgr.c` and its assembler
kernel; this finding therefore concerns DHGR. It is a plausible target, with
no measured speed factor.
The generic spans also switch aux writes byte by byte: handling main and aux
separately deserves a prototype that preserves the edges.

Compiled sprites could specialise data and masks and group the writes by
bank. Their benefit must be measured with save, draw and restore. CHROMABREAK
already has an assembler engine with a mirrored main/aux loop, precomputed
masks and save combined with drawing: the HGR gains do not carry over
automatically. Its fixed-address constraints and its bit 7 for mixed RGB
mode must be preserved.

Technical sources: [fdraw manual](https://github.com/fadden/fdraw/blob/master/docs/manual.md),
[fhpack](https://github.com/fadden/fhpack),
[Bmp2DHR DHGR sprite format](https://www.appleoldies.ca/bmp2dhr/sprites/).

## Provenance

- [fdraw](https://github.com/fadden/fdraw/tree/a1657e8e4d4b19f62497228d070c699c19e96cde),
  Andy McFadden, Apache-2.0, sources and licence kept in `upstream/fdraw`.
- [fhpack](https://github.com/fadden/fhpack/tree/18988e93ea7da79f837453e361b84395c4bd06a1),
  Andy McFadden; decompressor optimised by Peter Ferrie, Apache-2.0, sources
  and licence kept in `upstream/fhpack`.
- [HiSprite](https://github.com/blondie7575/HiSprite), Quinn Dunki: reference
  for the principle of compiled sprites. No explicit licence found in that
  repository; none of its files is reused.
- The demo shapes and the maze3d routine come from this repository, GPL-3.0.
  The new scripts and prototypes follow the GPL-3.0 licence of pom2games.
