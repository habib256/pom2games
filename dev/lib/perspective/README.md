# Plane and corridor projection

Two independent modules: `perspective.c` projects an HGR plane onto 280
pixels; `corridor.asm`, extracted from Light3DBall, projects both axes of a
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
sources and `$(PERSPECTIVE_INCS)` to the C flags. The generated file belongs to
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

The extraction keeps Light3DBall's binary and resources byte-for-byte
identical. The costs measured at this placement are 65..77 cycles for
select, 135..170 for X, 129..164 for Y, JSR/RTS included: a change of
**0 %** compared with the local code. Page crossings in the tables
and branches make the costs vary; these ranges are not a
universal budget for other placements of the kernel.
