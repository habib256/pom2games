# PHYSICS — reconstructed source

Commented ca65 source for the Apple //e program on `physics.dsk`
(143 360-byte DOS-order image, custom boot loader, no DOS catalog).
Every byte was regenerated from the disk. `make` reassembles it and rebuilds
a disk that is **byte-identical** to the original:

```
$ make
...
build/physics.dsk: 107 sectors from the load table + 4 boot sectors
IDENTICAL: build/physics.dsk == orig/physics.dsk
```

The program: up to three spinning balls fall under gravity, roll and bounce
off each other, off the screen walls and off seven boxes. The boxes dent where
they are hit and spring back with a damped wobble. Two 7-tick sliders at the
top of the screen set how soft the boxes are and how long they wobble.

## Files

| File | What |
|---|---|
| `src/boot.s` | Boot sector + fast loader (track 0, 4 sectors) |
| `src/main.s` | Main program, `$0800-$1CFF`: main loop, physics, ball rendering, maths |
| `src/boxes.s` | `$9400-$9AFF`: box dents, sliders, dirty rectangles |
| `src/tables.s` | `$6000-$7DFF`: maths tables, HGR row tables, box geometry, box artwork |
| `src/lcdata.s` | Ball sprites + reciprocal table (loaded `$A000`, runs at `$D000` in the language card) |
| `src/data/background.hgr` | The 8 KB HGR background picture (walls + seven boxes), `.incbin`'d |
| `src/physics.s` | The assembly unit: includes the parts above, one segment per load region |
| `src/hw.inc`, `src/zp_main.inc`, `src/zp_boot.inc` | Soft switches, zero page and page-2/3 variables, with comments |
| `src/physics.cfg`, `src/boot.cfg` | ld65 configs: one output file per load region |
| `tools/mkdisk.py` | Builds the `.dsk` by walking the loader's own `load_table` |
| `tools/extract.py` | Rebuilds the memory image from the disk (same table), writes `work/loadmap.txt` |
| `tools/gen.py`, `tools/annotations.py` | Source generator, and every name/comment/table layout |
| [`../dev/tools/re6502/`](../dev/tools/re6502/) | Shared opcode tables, code tracer, da65 info writer, physical-sector access; `cli.py trace / listing / refs` to explore the image |
| `tools/mkinfo.py`, `tools/da65check.sh` | Independent da65 cross-check (info file → da65 → ca65 → compare) |
| `tools/compare_ram.py` | Compares the loaded pages with a RAM dump of the running program |
| `orig/physics.dsk` | Copy of the original disk, used for the comparison |

## Build

Needs `ca65`/`ld65` (cc65 2.18 was used) and Python 3.

```
make             # assemble, link, build build/physics.dsk, cmp against orig/physics.dsk
make da65check   # da65 disassembly of both code segments, reassembled, compared
make ramcheck RAM=path/to/ram.bin
make regen       # regenerate src/*.s, src/*.inc and src/data from orig/physics.dsk
```

`make regen` rewrites the sources from `tools/annotations.py`. If you edit
the `.s` files by hand, stop using `regen`. The `.s` files are the source.
The generator is only how they were produced.

## Load map

The Disk II PROM reads T0 physical sector 0 to `$0800`. The boot code at
`$0801` calls the PROM's read routine (`$Cn5C`) again for physical sectors 2, 4
and 6. Those are DOS-order logical sectors 14, 13 and 12 in the `.dsk` file.
It copies `$0800-$0BFF` to `$9000-$93FF` and jumps to `$9045`. The loader then
reads whole tracks. It takes sectors in whatever order they pass under the
head, and physical sector *n* of a track goes to page (first page + *n*):

| Disk (physical sectors) | Memory | Contents |
|---|---|---|
| T0 s0,2,4,6 | `$0800-$0BFF`, relocated to `$9000-$93FF` | boot + loader |
| T1-T2 s0-15 | `$2000-$3FFF` | HGR background picture |
| T3 s0-15, T4 s0-13 | `$6000-$7DFF` | tables + box artwork |
| T5 s0-6 | `$9400-$9AFF` | box / dirty-rect module |
| T6 s0-15, T7 s0 | `$A000-$B0FF` | sprites + reciprocals (copied to `$D000`) |
| T8 s0-15, T9 s0-4 | `$0800-$1CFF` | main program; entry `$0800` |

These are all 111 non-empty sectors of the disk. Every other sector is zero.
While loading, the screen shows " P H Y S I C S ", "Loading, please wait...",
the track, the pages left, an estimated elapsed time and a 14-character
progress bar. The time is counted in sector-times: 80 make one second, at
5 revolutions per second.

**Proof against a running machine.** `tools/compare_ram.py` compares the
reconstructed image with the RAM dump taken after 30 s on a //e:

```
$0800-$1CFF main program        26 bytes differ  (exactly the 26 self-modified operand bytes)
$2000-$3FFF HGR page 1          98 bytes differ  (balls drawn on the displayed page)
$6000-$7DFF tables               0
$9400-$9AFF box module           0
$A000-$B0FF sprite data       3216 bytes differ  (init reuses $A000-$BFFF as the clean
                                                  background copy: it equals the picture
                                                  except for the 28 slider bytes on rows 6-7)
```

The dump does not include language-card RAM, so the `$D000` copy of the
sprite data was **not** checked against a live machine. It was checked only
through the code that reads it.

## Memory map at run time

| Range | Use |
|---|---|
| `$0200-$026E` | ball state, 3 entries per field (`ob_*`), drawn-sprite records per page (`dr_*`, 6 = 3 balls × 2 pages), new positions (`nw_*`) |
| `$030C-$036D` | per-box arrays, 7 entries, indexed by box 4-10: hit this step, spring displacement/velocity, dent drawn (`bx_*`) |
| `$0380-$03BF` | dirty-rectangle lists, 8 per display page (`dl_*`) |
| `$0800-$1CFF` | main program |
| `$2000-$3FFF` / `$4000-$5FFF` | HGR pages 1 / 2, both used for display (double buffering) |
| `$6000-$7DFF` | tables (see `tables.s`) |
| `$9000-$93FF` | loader (dead after boot) |
| `$9400-$9AFF` | box module |
| `$A000-$BFFF` | clean background (an HGR page that is never displayed): source for erasing; dents are drawn here |
| `$D000-$E0FF` | language card bank 1: ball sprites (16 rotations × 7 pixel shifts) + 65536/n table |

The zero page is listed with comments in `src/zp_main.inc`. Main groups:
`$10-$17` the current ball (x, y, vx, vy, all 8.8 fixed point in pixels),
`$18-$3F` the collision work area (closest point, normal `nx/ny` with
`$40` = 1.0, normal/tangential speed, spin, angle), `$42-$52` multiply,
divide and square-root arguments, `$5D/$5E` the two sliders, `$60` the
random seed, `$65` the page being drawn, `$74-$9E` dent and dirty-rect
drawing, and `$A0-$B3` frame timing, loop indices and the per-page pointers.

## How it works

**Frame loop** (`main_loop`). The main loop reads the keyboard, runs
`steps` physics ticks, draws the hidden page (`render_frame`), then waits
and flips (`wait_and_flip`).

**Timing** (`wait_vbl`). Vertical blanks are counted by watching bit 7 of
`$C019` (RDVBLBAR) for 1→0 edges. On the //e that bit is 0 during vertical
blank. A drawing routine never knows when it will finish, so the edge test
is copied into almost every long loop, including the physics. This keeps
blanks from being missed. `wait_and_flip` waits for the next blank, and for at
least two since the last flip, then flips: at most 30 fps on NTSC and 25 on
PAL. The number of blanks that elapsed (2-4) becomes the next frame's tick
count, so the simulation advances one tick per field at any frame rate.

**Page flipping.** `drawpg` (`$65`) selects the page being drawn. `pgoff`
(`$73`) is `$00` or `$20` and is added to row high bytes. `rowhi_tab` points
at the page's row-address table. After drawing, the page just drawn is shown
(`$C054`/`$C055`) and `drawpg` toggles.

**Physics tick** (`physics_step`):
1. `integrate_ball`: gravity `vy += $18/256` px/step², both speeds clamped
   to ±4 px/step, position += velocity, angle += angle rate.
2. `collide_pair` for every pair: contact under 12 px. Each ball is pushed
   apart by half the overlap along the normal. Approaching balls get an
   equal-and-opposite impulse of −vn×200/256, or −vn×128/256 when slow.
3. `collide_boxes`: the ball's 16×16 grid cell selects a short list of
   candidates (`grid_cell` → `grid_lists`). Boxes 0-3 are the walls, 4-10
   the boxes. `collide_box` finds the closest point and measures the distance
   with quarter-square tables. A contact (under 6 px, the ball radius) gives
   a unit normal from `isqrt16` and `div16by8`.
   * `hard_contact` (walls, or any box while the softness slider is 0):
     push out to 6 px, reflect the normal speed ×144/256 (or zero it below
     about 0.18 px/step), then `friction`.
   * `soft_contact` (boxes when softness > 0): spring force =
     penetration × `soft_tab[soft]`, losses ×230/256. `record_hit` stores the
     side, position and depth (0-4 px) so the box can be drawn dented.
   * `friction`: slip = tangential speed − spin. The tangential speed loses
     73/256 of the slip and the spin gains 183/256 of it. Both then decay
     ×252/256. This is what makes the balls roll and spin. `spin_to_rate`
     turns spin into the sprite's rotation speed.
4. `check_ball_life`: 30 nearly-still ticks put a ball to sleep (it is no
   longer integrated, but its box stays pressed). After 90 still ticks, or
   1500 ticks of age, the ball is respawned at the top.
5. `box_spring` for each box: a hit sets the dent to the hit depth. Otherwise
   the displacement relaxes: vel = vel×`damp_tab[wobble]` −
   disp×`stiff_tab[soft]`.
6. Fewer than 3 balls: a new one spawns every 90 ticks (SPACE spawns one
   now, or recycles the oldest).

**Drawing** (`render_frame`, `boxes.s`):
* `update_boxes` compares each box's current dent with the one drawn. On a
  change it restores the box's pristine image (`restore_box`, from `box_img*`)
  into the `$A000` background, draws the bent side (`draw_dent`), and queues
  a dirty rectangle for *both* display pages (`add_dirty`). Slider changes
  are handled the same way.
* For each ball: frame = (angle+8)/16 (16 rotations of 22.5°), byte column
  and pixel shift from `x_col`/`x_shift`, top row = y−6. A sprite that is
  unchanged on this page and not touched by a dirty rect is left as it is.
* `restore_dirty` copies this page's dirty rects from `$A000`. `erase_ball`
  copies each moved ball's old 3×12-byte area back from `$A000`. `draw_ball`
  ORs the pre-shifted, pre-rotated sprite in. The row and sprite addresses
  are patched into the instructions (self-modifying code).

**Maths.** `mul8x8` is quarter-square multiplication,
A·X = ⌊(X+A)²/4⌋ − ⌊(X−A)²/4⌋. The table bases are patched with A.
`mul8x16`, `mul_frac`, `mul_dir` (by a ±$40-scaled direction),
`mul_k73/183/252/230` (fixed constants through pre-offset tables), `mul_int`,
`isqrt16` (seed table + step), `div16by8` (reciprocal table + correction),
and `random` (16-bit Galois LFSR, taps `$B400`, fixed seed `$AD3C`, so every
run is the same).

**Keys.** ↑/↓: softness slider −/+ (wakes all balls). ←/→: wobble slider −/+.
SPACE: spawn. P: pause.

## Why it freezes on a //c

`wait_vbl` (`$0E2C`) loops until `vblcount` reaches `vblwant`. `vblcount`
only grows when bit 7 of `$C019` changes from 1 to 0. On the //e, `$C019`
is RDVBLBAR, a live signal that toggles every frame. On the //c the same
address is VBLINT: a flag that latches only when the VBL interrupt has been
enabled through the IOU. This program never enables it, and it runs with
interrupts masked (`SEI` in `init`). So the bit never changes, `vblcount`
stays 0, and the first `wait_and_flip` never returns. The POM2 //c run shows
exactly this: after loading, the PC stays in `$0E2C-$0E41` for the whole run.
Nothing else in the program is //e-specific. It uses only NMOS 6502 opcodes,
writes to language-card bank 1 and main RAM, and touches no auxiliary memory.

## Certainty

* **Code and data split.** This is verified. A recursive trace from `$0800`
  reaches every byte of `$0800-$1CC7` and `$9400-$9A0C` as code, with no
  65C02 opcodes, no indirect jumps and no calls outside the loaded image. Two
  disassemblers agree (`gen.py` and da65 driven by an info file), and both
  reassemble to identical bytes.
* **Unexplained bytes.** Three bytes at `$99AF` (`20 A0 99`, a JSR to
  `bg_row_ptr`) are never reached and are kept as data. The byte at `$928D`
  (a `$00` after the text-record terminator) and the zero tails of the last
  sectors have no use.
* **Semantics that are only partly understood.** These tables are reproduced
  exactly, and their role is clear from the code, but the exact geometry of
  each entry was not worked out:
  * the dent-drawing profiles: `dent_rows`, `dent_cornA/B`, `dent_halfw`,
    `vdent_col`;
  * the left/right-side dent shapes (`vdent_shapes`, 176 pointers);
  * the box artwork (`box_img4-10`).
* **Names are mine.** The original names are unknown. "softness" and "wobble"
  for the sliders describe which tables the two settings index; the screen
  has no labels. Several small physics constants (73, 183, 252 and 230 out of
  256) are named after their values, not their intent.
* **Not checked against a live machine.** The language-card copy at `$D000`
  (the RAM dump does not include it).
