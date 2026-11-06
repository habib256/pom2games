# Plane and corridor projection

Two independent modules: `perspective_asm.s` projects an HGR plane onto
280 pixels (with `perspective.c` retained as a C reference); `corridor.asm`, extracted from Light3DBall, projects both axes of a
corridor cross-section according to depth. Each client picks its module.

## HGR plane

`a2_perspective_project(camera,x,y,&point)` projects a point of the playfield
onto the 280×192 HGR screen. The target computation uses tables and a 16-bit
product; no perspective division or floating point is needed.
The approach is inspired by the tables of
[Shufflepuck](https://github.com/colinleroy/a2tools/blob/main/src/shufflepuck/generators/gen_transform.c).
The generator and the runtime are a new GPL-3.0 implementation.

```sh
python3 dev/tools/perspective.py --out build/camera.h --name camera \
  --rows 192 --focal 78 --center 140 --horizon 31 --bottom 191
```

Include `perspective.mk` after `apple2.mk`, add `$(PERSPECTIVE_SRCS)` to the
sources and `$(PERSPECTIVE_INCS)` to the C flags. Use `$(PERSPECTIVE_C_SRCS)`
instead for the retained C target implementation; host builds can compile
`perspective.c` directly. The generated file belongs to
the application; include it in a single C unit to avoid duplicating
the tables. A 192-row camera costs 768 bytes of tables and a
7-byte descriptor on cc65. The runtime allocates no pool and no BSS.

```c
#include "perspective.h"
#include "camera.h"
a2_projected_t point;
if (a2_perspective_project(&camera,279,96,&point))
    hgr_plot(point.x,point.y);
```

The input abscissa is 0..279; depth runs from 0 (far) to rows-1
(near). `focal` is a positive distance, in the same units as the
depth. The horizon and the bottom are HGR lines. `center` is the horizontal
projection centre, on screen. The ratio at row y is:

```
r = focal / (focal + rows - 1 - y)
q = max(1, floor(256*r))
screen_x = floor(x*q/256) + floor(center*(256-q)/256)
screen_y = horizon + floor((bottom-horizon)*r)
```

The tables store q in one byte: zero stands for 256, hence the identity
on the last row. The X computation handles the 255→256 transition without a
32-bit product. Quantisation can merge distant points or rows.
This module projects a plane, not an arbitrary 3D scene; it does not scale
sprites and does not handle depth ordering.

The default native entry occupies **257 code bytes**, with no private RAM,
zero page, tables or self modification. It consumes the five argument bytes
on every path, returns normalized 0/1 in AX, and shares cc65's `ptr1..ptr4`
and `tmp1..tmp4`. Output is written only after every check succeeds.
Its eight-step multiply computes the high byte of the low-X product, then
adds the high-X contribution. Depths 128..191 carry into the shift-table
pointer explicitly. Bank selection and the IRQ mask remain unchanged.

Compared with the retained C entry, an isolated linked client saves **456
loaded bytes**. The x=279, scale=255, shift=0 wrapper takes **631 instead of
1,543 cycles**; all 7,167 boundary profiles improve by 616..1,002 cycles.
C stack peaks drop from 15 to five bytes and hardware peaks by two or three,
with unchanged RAM and zero page. `test_perspective_entry.py` checks **71,680
public products plus 196,608 parameter-domain calls per CPU**, with independent
integer arithmetic, output guards, C/hardware stack restoration, IRQ states
and bank selection. `--reference PATH` selects the same harness's C entry;
`--iie` selects the 65C02 and `--out PATH` records identities and snapshots.
The older rational-camera grid also runs both native and C target entries.

Centering the rejection return makes all branches short and saves another
12 code bytes and 2..5 cycles in the 7,167 profiles. Of 14 dedicated early
rejections, 13 improve; a NULL output costs two extra cycles (167 → 169).
`test_perspective_bounds.py --invalid` exposes these paths separately.

The retained C entry was first simplified as follows:
After validating the shift, projection adds it once and checks the sum.
Each term is at most 279, so this addition cannot wrap the 16-bit target
integer. This removes three bytes from the C function and an unused runtime
comparison helper: an isolated linked client saves **31 loaded bytes**.
At x=279, scale=255, shift=0, the complete C wrapper takes **1,543 instead
of 1,659 cycles**, with the same RAM, zero page and stack peaks.
`test_perspective_bounds.py --full` checks all 256 scale bytes at the input
and output boundaries (7,167 calls per CPU), including shift=65535 and
untouched rejected outputs. `--reference PATH --out PATH` records source,
compiler and emulator identities with the costs; `--iie` selects the 65C02.

The tables are borrowed and must stay valid during the call.
Null pointers, out-of-range X, depth outside the table, an invalid row
count and a result outside HGR are rejected with zero, without modifying the
output point. Success returns one. Call outside IRQ, in main RAM/ZP and with D=0.
Display, banks and the IRQ mask remain the caller's.

```sh
python3 dev/tests/test_perspective.py
python3 dev/tests/test_perspective.py --iie
make -C dev/examples/perspective run
```

## 6502 / cc65 corridor

`corridor.asm` shares the Light3DBall kernel and `corridor.h` exposes its C API.
The world cross-section uses X/Y from 0 to 127. Depth is an unsigned
16-bit distance in front of the camera; compute this distance before the call.
The result is one byte per axis: screen X/Y 0..255. The application keeps
HGR clipping to 192 lines, occlusion, sprite sizes and
collisions. The library knows nothing about the game's levels or objects.

```sh
python3 dev/tools/perspective.py --kind corridor --name corridor \
  --span-x 252 --span-y 148 --focal 32 --center-x 128 --center-y 80 \
  --out build/corridor_tables.h
```

Include the generated tables in a single C unit. Add an assembler file
to the program, with the `PERSPECTIVE_CORRIDOR_INCS` path:

```asm
PC_CENTER_X = 128
PC_CENTER_Y = 80
PC_DEPTH_SHIFT = 1
.include "corridor.asm"
```

Declare `PERSPECTIVE_CORRIDOR_DEPS` among the dependencies of this unit and
of the clients of `corridor.h`. The centres and the depth step are fixed at
compile time; the tables are supplied by the application. Their default
names are `corridor_scale_x/y`. The runtime borrows their immutable contents.

```c
#include "corridor.h"
#include "corridor_tables.h" /* A single C unit defines both tables. */

a2_corridor_select(distance);
screen_x = a2_corridor_x(world_x);
screen_y = a2_corridor_y(world_y);
```

The exact formulas are:

```
depth = min(distance >> PC_DEPTH_SHIFT, 255)
span_x = table_x[depth]
span_y = table_y[depth]
left = PC_CENTER_X - floor(span_x/2)
top  = PC_CENTER_Y - floor(span_y/2)
screen_x = left + floor(world_x*span_x/128)
screen_y = top  + floor(world_y*span_y/128)
```

The generator fills each table with `floor(span*focal/(focal+depth))`.
`focal` is expressed in **table entries**: with `PC_DEPTH_SHIFT=1`, one
entry corresponds to two world units. The step can range from 0 to 8; beyond
the last entry, the projection keeps that entry's factors.
A negative depth must be handled by the client before conversion.

The active state holds five BSS bytes (`a2_corridor_sx/sy/left/top/depth`) and
the computation borrows one ZP byte. Always call `select` before projecting.
Two 256-byte tables cost 512 bytes. To reuse existing allocations,
define the assembler aliases `PC_BITS`, `PC_SX`, `PC_SY`, `PC_LEFT`,
`PC_TOP`, `PC_DEPTH`, `PC_TABLE_X` and `PC_TABLE_Y` before the include. This is
what Light3DBall does, with no extra allocation and no call trampoline.

The product is exact in seven shift/add steps, with no C helper or
32-bit product. No video state, bank or IRQ mask is modified.
Calls are non-reentrant, outside IRQ, D=0, in main RAM/ZP. The kernel
validates neither the coordinates nor the tables: the factors must keep
`center - floor(span/2)` and the projected points within 0..255.

```sh
python3 dev/tests/test_corridor.py
python3 dev/bench/corridor_projection.py
make -C light3dball test
```

The initial extraction kept Light3DBall's binary and resources byte-for-byte
identical. For the common depth shift of one, the validated high byte is
0 or 1: `CPX #1` supplies its bit as carry directly, replacing a scratch
store/shift. This saves **two code/loaded bytes and six cycles** for near
depths with ZP scratch (four bytes/eight cycles with an absolute alias).
Other depth shifts retain their instruction sequences. Scratch allocation,
public state, Y, IRQ mask, decimal state and assets are unchanged.

Actual Light3DBall select costs **65..71 instead of 65..77 cycles**;
X and Y keep 135..170 and 129..164, JSR/RTS included. The linked game is
10,753 instead of 10,755 bytes. All 26 isolated render cases per CPU save
36..75 cycles with identical HGR pages and public game state. These runs
bypass frame waits equally; table/branch placement still affects costs.
`test_corridor.py --guarded` adds both CPUs and default, ZP, absolute and
mixed aliases, complete RAM/code/table/bank guards and exact public state.
Each of its eight profiles checks 131,072 depth calls, all admissible
span/coordinate combinations and 65,536 D=1 equivalence calls (the public
arithmetic contract remains D=0). `--reference REV_OR_PATH --out PATH`
records comparisons. `corridor_projection.py --before DIR --current DIR
--out PATH` checks two captured game builds and reports timing deltas.
