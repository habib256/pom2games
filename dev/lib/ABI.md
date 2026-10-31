# 6502 / cc65 integration contracts

The public headers describe each function's coordinates, buffers and return
values. The assembly kernels describe their registers and their scratch.
This document sets the common preconditions.

## Entry and memory

- D=0 (binary arithmetic), code and hardware stack in main RAM.
- On IIe/IIc: main zero page, ROM visible, RAMRD/RAMWRT main,
  80STORE off on entry to the banked primitives.
- Self-modifying code must be loaded into writable memory. The
  `type=ro` property of an ld65 segment does not prevent executing it from RAM.
- Sources, buffers, C stack and save pools live outside the video
  pages in use. Their pointers and contents stay valid during
  the operations and the deferred sprite restores.
- The CRT saves the borrowed ZP and initialises BSS. LOWBSS must be
  initialised explicitly by the application. In a
  `load==run` configuration, `copydata` does not keep a copy of the initial values
  for a new BASIC call without reloading.

## Calls, state and interrupts

The APIs use the cc65 fastcall convention (the compiler default):
the rightmost argument arrives in A or A/X, the others on the C stack. A
one-byte result is in A, with X=0. From assembly, use the
kernel's contract rather than assuming the other C arguments are in registers.

The drawing primitives share their parameters and their scratch; they
are not reentrant and must not be called from an IRQ. An
application IRQ handler must preserve the registers and ZP it
uses, without calling these primitives or changing their banks.

| Family | State effect and caller obligation |
|---|---|
| HGR C | Tables built on demand; drawing on the chosen page; no implicit VBL wait |
| gfx lines | HGR: ASM kernel; DHGR: C fallback selected explicitly at link time; no dynamic allocation |
| HGR C ASM kernels | Prepare all tables with `hgr_build_tables` before direct access; Light3dball's native renderer follows this contract |
| Included HGR ASM | `.ifref` requires the references before the include; scratch possibly aliased; kernel bounds must be respected |
| DHGR | I state preserved; exit in main RAM; displayed page preserved unless explicitly presented |
| `dhgr_clear` | Both banks, holes included; IRQs masked for the whole operation (~189,000 cycles) |
| `dhgr_clear_rows` | Visible lines; main banks and IRQ mask restored between lines; kernel <1,300 cycles per line |
| Saved sprites | Restore before changing the background or redefining a shape; keep one background per page |
| DHGR compositor (`dhgr_spr_*`, `dhgr_cursor`) | Opt-in `HGRC_DHGR_SPR_SRCS`; each changed byte of the area written once with its final value; IRQs masked only around each group's two aux stores (~30 cycles); borrowed canvas used only inside the update; invalidate background changes in the area; overlay hidden while the screen outside the area changes |
| DHGR compositor, two pages (`DHGR_SPR_DOUBLE`) | Updates store only into the hidden (draw) page, each byte once; `dhgr_spr_present` flips at a VBL edge (bounded wait, IRQs enabled on the //c) and swaps the draw page; start with draw page ≠ shown page and invalidate the area |
| Frame pacing | IIe VBL or delay added to drawing; bounded fallback if the signal is stuck; IRQ mask preserved |
| Optional PWM audio | Nominal 1 MHz CPU, encoded clip terminated by `$92`; blocking playback, IRQs masked then mask restored; borrows cc65 ptr1/ptr3/ptr4 low/tmp3; AUDIOCODE segment aligned to $100 in RAM (after STARTUP in the C cfgs) |
| Perspective | X 0..279, depth in the borrowed tables; output outside HGR rejected; no video/bank state changed, outside IRQ |
| Native corridor | World X/Y 0..127, unsigned 16-bit depth; two borrowed 256-byte tables, centres/steps fixed at compile time; shared state 5 BSS + 1 ZP or caller alias; no clipping, no I/bank changes |
| ProDOS video | Explicit policy for `/RAM` before auxiliary drawing; released on exit |

The displayed page and the drawing page are distinct. Waiting for a VBL edge
before presenting synchronises the flip on IIe. On II/II+, the fallback
delay does not provide that synchronisation.

## Building

Link the application objects before the archives. The name of each member of
`hgrc.lib` encodes its directory and extension to avoid collisions.
The signature covers the C/ASM flags, the tools and the sources; a change
invalidates the objects even with GNU make 3.81 and within the same second.

`make test-tools` checks incremental builds and the ProDOS
policies; `make test-hgr` checks bounds, lines, tables and sprite pools;
`make test-dhgr` checks the banks and the per-line kernel duration.

## Units and lifetime

| Inputs | Units, bounds and behaviour |
|---|---|
| HGR pixels | X 0..279, Y 0..191; dimensions in pixels unless the API is explicitly in bytes |
| `hgr_line` | Two inclusive endpoints; rejects any off-screen endpoint, even for axis-aligned lines |
| `gfx_line` | Backend pixels; axis-aligned lines sorted/clipped by the spans, off-screen diagonals rejected |
| `gfx` rectangles | Two inclusive corners, sorted and clipped; the full backend width is reachable |
| Low-level HGR rectangles | `hgr_fill_rect` in byte columns; `*_pixrect` in pixels with an 8-bit width; zero draws nothing |
| DHGR mono / colour | X 0..559 bits / X 0..139 colour pixels; Y 0..191; colours masked to 0..15 |
| DHGR blocks | X in interleaved bytes 0..79; stride >= width; valid buffer of stride×height bytes, even if part of it is clipped |
| DHGR sprite | Colour X; seven data/mask banks of stride×height each; mask 1 keeps the background |
| DHGR compositor | Slots/area/cells in colour pixels (groups of 7 = 4 bytes at x/7); overlay/cursor in interleaved bytes 0..79, w×h ≤ 127, `under` 2×w×h bytes; shapes and maps borrowed and immutable while used, RECTS rectangles inside the shape's w×h; canvas ≥ 7×groups bytes outside $2000-$5FFF (at most 255 used) |
| Saved HGR sprite | Dimensions stride×height in bytes; per-sprite/per-page capacity supplied at init, 96 for the legacy API |

Strings are NUL-terminated; sources are borrowed, and the library does not copy
their contents. An HGR sprite source must stay
valid and immutable as long as an associated background must be restored, including on
the other page. A valid reinitialisation forgets the backgrounds: clean both
pages before reinitialising. Buffers must not overlap the active video
pages or the engine's scratch. No memory guard is allocated on target.

C drawing calls may destroy the shared cc65 scratch and their
private parameters; a direct ASM call must follow the kernel header for
A/X/Y and the ZP bytes involved. An IRQ handler must preserve everything
it uses; the VIA test checks the real service during `dhgr_clear_rows`,
with bank checks on IRQ entry and a comparison of both pages.

`make test-minimal` checks the DOS HGR integrations; `make test-dhgr` adds
the IIe/ProDOS integrations. Physical tests are tracked separately in
[HARDWARE.md](HARDWARE.md), without turning an emulated success into a certification.


## Differential HUD fields

`hgr_hud_field_t` fields belong to the caller and own a black
box on each page. Their structure must not be modified during rendering.
After an outside write into the box, invalidate that page's history.
A value that is too wide is rejected with 255, without changing the field. The legacy
`hgr_putu_field` API keeps no history and allows its old overflow to the right.
Double buffering keeps both values and digit contents separately.

The HGR tables keep their format and address; the flip is unrolled
over eight groups of lines, with no scratch change. The fixed-base strategy
is tested as a prototype, without changing the contract of the current ASM kernels.

The maximum number of sprites can be set with `HGR_SPR_MAX` (1..8).
Compile the application and its library with the same value; the default
value keeps eight slots and the engine remains non-reentrant.

## Incremental rendering and explicit addressing

The compact `hgr_hud8_field_t` HUD has 19 bytes of cc65 state and at most five
cells, each 8×8 with a pitch of 8. It shares the return,
per-page cache and invalidation contracts of the 16×16 HUD; each family lives in
separate archive members. The kernels share the text scratch, with no new ZP.

`APPLE2C_CADENCE_SRCS` adds an optional deadline scheduler, fed
by `a2_cadence_tick` from the IRQ owned by the application. It installs
no vector or peripheral. The tick preserves A/X/Y and modifies NZ; the IRQ must
restore the flags. `init`/`wait` require D=0 and preserve I. The source must
advance during the wait and be synchronised to VBL to avoid tearing.
Late deadlines are skipped, and the return value is their count; $FFFF
signals a timeout and disables the scheduler until the next `init`.
16-bit reads of the IRQ counter must be atomic. Do not let
32767 ticks go by without calling `wait`. Drawing functions stay out of IRQs.

`HGR_SPR_DAMAGE=1` is a compile-time option of the engine: it adds
4×HGR_SPR_MAX+11 bytes of BSS for a conservative closure of the intersections
of the old/new byte rectangles. The order (reverse restore, then
direct draw) is preserved. The default still uses the simple prefix/suffix.

The sprite engine keeps a prefix of unchanged layers per page; it
restores and redraws the whole suffix from the first modified layer.
Shape contents must stay immutable, even for a still sprite.
`hgr_spr_invalidate` forces a redraw, without allowing writes under the
sprites. Presentation explicitly takes back the page owned by the engine.

`hgr_row_on_page` is independent of global state. Its immutable tables
cost 384 loaded bytes, no BSS; masked sprites and the 8×8 HUD
use these offsets with the selected base. The other legacy kernels
keep their mutable tables. The HUD kernel uses the shared text
parameters and remains non-reentrant. Prepare the HUD on each page before animating.

The sprite engine computes stride×height when a shape is defined, then uses
assembly controllers; its `spr_*` symbols serve only for internal C/ASM
linking. Shape contents stay immutable. The HUD controllers accept
+1/+2 steps via the cached digits; other values use the 16-bit
conversion. An overflow keeps the pixels and the histories.

`hgr_tile_restore` is optional, fastcall, non-reentrant and outside IRQs. It writes
directly to the requested page without changing the global pages or the banks.
The 40×24 map and the 7×8 glyphs live outside both video pages. The region
is clipped before a full validation of the IDs, then rebuilt in ASM.
The application owns the dirty regions, the layer order and the histories
of its pages; this path does not change the existing save-under engine.

The hardware stack is observed separately from the cc65 stack. The
hardware depth also counts the bytes already in use on entry to the workload.
The detector reports S going below $00 across the observed
instructions; this profile is not a static proof covering all IRQs,
explicit changes of S or paths that were not executed.

## Speed/RAM options

A library does not impose one trade-off on every program: when two
variants of a module are justified (faster or smaller code against
more RAM, tables in the file against tables built at startup),
both stay available and each program chooses at compile time.

Convention for any new option (existing names stay as they are):

- Name `<MODULE>_<FUNCTION>_<VARIANT>` in upper case: `<MODULE>` is the
  prefix of the module or archive (`HGR_` for lib/hgr, `HGRC_` for an
  option of the cc65 hgrc archive, `MUL_`, `DOS_`…), `<VARIANT>` names the
  chosen technique (`TABLES`, `RAM`, `ORA`, `FOLDED`, `IFREF`…), not a
  `FAST`/`SMALL` judgement: a variant is often faster for one
  program and bigger for another.
- Undefined = the default, the one existing programs already use.
  Adding an option changes no existing binary and no bench baseline.
- Assembly: `NAME = 1` (or the expected address/table) before the `.include`.
  hgrc archive: `HGRC_DEFINES := -D NAME=1` in the program's Makefile,
  before `hgrc_build.mk`; passed to the C and assembly members, it rebuilds
  the archive. An option visible in a header also goes into the program's
  CFLAGS.
- The module's header comment gives the cost of both variants;
  the bench measures the non-default variant when it covers the module (case
  `<case>_<variant>`, `variant` option of `dev/bench/run.py`).

Options of this kind (measurements: hgrc bench, or the commit that introduced the option):

| Option | Module | Effect of the option (against the default) | Programs |
|---|---|---|---|
| `HGRC_X7_FOLDED` | hgrc `hgr_columns.s` | A single builder for `hgr_col7`/`hgr_mask7`/`hgr_phase7`: code −107 B, first use −7,000 cycles (text, sprites: 97,462 instead of 104,439, 35,526 instead of 42,598); but all three tables (841 B BSS) always reserved: +279 B for a program that uses only two of them (lines and pixels: code −49 B, −360 cycles) | none (bench `*_x7folded`) |
| `HGR_PAGES_ORA` | `hgr_pages.inc/.asm` | No `hgr_hi2` (−192 B BSS); +2 cycles per line read, ~4 per site on page selection | light3dball (dirtbike: default) |
| `HGR_LINE_DIV7` / `HGR_LINE_MOD7` | `hgr_line.asm` | Two reads from the program's 256 B tables instead of two 32 B tables and a correction; use it when the program already has these tables | dirtbike |
| `HGR_FULL_WIDTH_TABLES` | `hgr_plot_tables.inc` | Columns 0..279 instead of 0..255: +48 B of tables; required by `hgr_plot16`/`hgr_line16` | logo |
| `HGR_PLOT_TABLES_RAM` | `hgr_plot_tables.inc` | Tables in BSS + `hgr_plot_tables_init` (39 B): file −513 B for LOGO, same RAM, built once at startup | logo |
| `hgr_div7_ram.asm` (include) | lib/hgr | `div7`/`mod7` in BSS, `hgr_div7_init` (28 B, ~6,000 cycles once): file −482 B, RAM +28 B | arkabreakout |
| `hgr_scanline_ram.asm` (include) | lib/hgr | Line tables in RAM, `hgr_scanline_init` (~50 B): 384 B less in the file | dirtbike |
| `HGR_TEXT8_HGR_ORDER` | `hgr_text8.asm` | Font in HGR order: no more `rev7_tab` (−256 B) nor reversal path | arkabreakout, dirtbike |
| `HGR_TEXT8_NO_PUTS` | `hgr_text8.asm` | No `hgr_puts8` (less code) | maze3d |
| `HG_STORE_ONLY` / `HG_STORE_UNCLIPPED` | `hgr_glyph8.asm` | Without the unaligned entry points / without STORE checks (shorter and faster; the caller guarantees `hg_col<40`, `hg_y<=184`) | chess / chess, micro-sokoban |
| `HGR_SPR_DAMAGE` | hgrc sprite engine | +4×`HGR_SPR_MAX`+11 B BSS: closure of the intersection rectangles instead of the simple prefix/suffix | none (bench `hgr_isolated_damage`) |
| `DHGR_SPR_PACK_TABLES` | hgrc DHGR compositor `dhgr_spr_asm.s` | Accepted, no effect since 2026-10-31: one 16-byte table is the default packing (faster than the former nine tables) | none (bench `dhgr_spr_move_tables` = `dhgr_spr_move`) |
| `DHGR_SPR_CODE_SEGMENT` | hgrc DHGR compositor | Code and tables in segment `DHGRSPRCODE` (an overlay window) instead of CODE/RODATA; BSS stays resident | robotspacestation (update, write, painters, tiles in the PLAY overlay) |
| `DHGR_SPR_RECTS_ONLY` | hgrc DHGR compositor `dhgr_cv_asm.s` | No CHUNKY/TILE shapes: `dhgr_cv_bitmap.s` not linked, −392 B | robotspacestation |
| `DHGR_SPR_OVERLAY_INSIDE` | hgrc DHGR compositor `dhgr_spr_overlay.s` | The overlay is drawn only inside the area, `under` unused: the save-under `dhgr_spr_cursor.s` is not linked, −764 B | robotspacestation (its `pointer.s` draws the pointer's rows outside the room) |
| `DHGR_SPR_MAX` (placement) | hgrc DHGR compositor | Slots 1..8 (default 8), 24 B BSS each; compile the program's C and the library alike. `DHGR_SPR_VBL` and `DHGR_SPR_DOUBLE` have their own rows below | — |
| `DHGR_SPR_DOUBLE` (implemented 2026-10-31) | hgrc DHGR compositor `dhgr_spr_update.s`, `dhgr_spr_cursor.s`, `dhgr_spr_present.s` | Two pages: each update draws on the hidden page what changed since that page was drawn (its own damage + the damage the other page received meanwhile, a 22-rectangle list), `dhgr_spr_present()` flips at the next VBL edge (apple2vbl: //e `$C019`, //c mouse VBL interrupt, else `a2_frame_wait`, bounded); overlay saved per page (`under` 254 + 2×w×h). +198 B code, +106 B BSS, present 111 B; bench `dhgr_spr_double_move` 16,697 cycles (one-page move 15,939) | dev/examples/dhgr_action |
| `DHGR_SPR_VBL` (implemented 2026-10-31) | hgrc DHGR compositor `dhgr_spr_update.s` | One page: an update whose damage is one piece that the write finishes ahead of the beam (`100 + k(95 + 165 groups) ≤ 4,550 + 65(y + k − 1)`, //c latency 1,200) is composed, then written right after the next VBL edge; else the plain order. +260 B code, apple2vbl linked; bench `dhgr_spr_vbl_move` 21,871 cycles from an edge (one refresh waited + the write) | none |
| `MUL_ACC` | `math.inc`/`mul.asm` | `mul_acc0..2` accumulator: +3 B of ZP | dirtbike |
| `VL_INTEGRATE_LEFTWALL` | lib/physics `verlet.asm` | `vl_integrate` stops points left of a wall (x = ox = wall): +32 B, +~15 cycles per point | dirtbike |
| `VL_CEILING_CLAMP` | lib/physics `verlet.inc` | The ceiling of `VL_CEILING` / `vl_ceiling` (y = old y = it) | dirtbike |
| `VL_CON_VARIANTS` | lib/physics `verlet_con.asm` | Rest length and gain per variant row (`vl_cur·V + vl_con_row`): +11 B code, +N B table, V× the constraint tables, 2 B BSS | dirtbike |
| `VL_CON_HEAVY_POINT` / `_SHIFT` | lib/physics `verlet_con.asm` | Links ending on that point move it less (c − c>>n toward 0) than their other end: `vl_heavy` + tests, ~+250 cycles per heavy link | dirtbike |
| `VL_CON_MINLEN_POINT` / `VL_CON_MINLEN` | lib/physics `verlet_con.asm` | Links ending on that point shorter than the minimum set `vl_squashed`: +25 B, 1 B BSS | dirtbike |
| `VL_PAIR_DAMP` | lib/physics `verlet.asm` | Assembles `vl_pair_damp` (the relative speed of two points fades by 1/2ⁿ) | dirtbike |
| `VL_ROT_SEG` / `VL_MULTURN_SEG` (`.define`) | lib/physics `verlet_rot.asm` | `vl_shift_point`+`vl_axis` / `vl_mul_turn` in that segment instead of CODE | dirtbike (`TXTC4` / `TXTC7`) |
| `VL_PIN` | lib/physics `verlet.inc`/`verlet.asm`/`verlet_con.asm` | `vl_pin` (N B BSS): pinned points skipped by `vl_integrate`/`vl_push_all`, a link moves only its free end (2c): +101 B, +7 cycles an integration, +27 a link | dev/examples/lander (rope test) |
| `VL_CON_FIXED_K` = s | lib/physics `verlet_con.asm` | Every link's gain is 2ˢ, f = (q² − l2) / 2¹¹⁻ˢ toward zero by shifts: no product, no `vl_con_k8` table, −34 B, −169 cycles a link (1,155 → 986) | dev/examples/lander |
| `VL_CON_MIN_ONLY` | lib/physics `verlet_con.asm` | Links flagged in bit 7 of `vl_con_b` only push (minimum distance): +12 B, +13 cycles a link | — (dev/tests/test_verlet.py) |
| `VL_THRUST` = n | lib/physics `verlet_rot.asm`/`verlet.asm` | Assembles `vl_thrust_axis`/`_perp` (push vector = axis · `vl_turn` >> (8+n)), `vl_push`, `vl_push_all`: +4 B ZP, 162 B (perp + push_all), 620 + 397 cycles for 3 points | dev/examples/lander |
| `VL_Y_HIGH` / `VL_GROUND_BASE` | lib/physics (all files) | y in 16.8 (`vl_yu`, `vl_oyu`: +2N B BSS), the ground row = height + base: +80 B, +28 cycles an integration, +70 a ground contact | dev/examples/lander |
| `VL_GROUND_SEGMENTS` = n / `VL_SEG_DEPTH` | lib/physics `verlet.inc`/`verlet_seg.asm` | `vl_seg_ground`: a ground of n line segments (walls, overhangs, loops), the `vl_sg_*` tables from `dev/tools/verlet/segments.py` (14 B a segment, 16 with `VL_Y_HIGH`), `vl_sgi` (VL_GROUND B BSS), no zero page of its own: 803 B (835 with `VL_Y_HIGH`); ~30 cycles a segment out of its box, 2,600-5,600 in contact | dev/examples/halfpipe |
| `VL_SEG_CACHE` = margin | lib/physics `verlet_seg.asm` | A point still on its last segment, `margin` (8.8) or more from its ends, is taken without the scan: +270 B, −500 to −1,500 cycles a contact there, +~1,000 at a joint | dev/examples/halfpipe |
| `VL_GROUND_KIND` = table | lib/physics `verlet_seg.asm` | `vl_ground_any`: point X on the height map (table byte 0) or the segments: 9 B | — (dev/tests/test_verlet_seg.py) |
| `VL_CIRC` = n / `VL_CIRC_Q` | lib/physics `verlet.inc`/`verlet_circ.asm` | Points 0..n−1 are circles (`vl_rad`, units of 2^Q/256 px, Q = 4..6, default 5): `vl_contact_pair`, `vl_contact_all`, `vl_contact_box` (needs `isqrt16`, `MUL_ACC`): +10 B ZP (+4 without a ground), n+1 B BSS; 941 B pairs, 1,039 B boxes, 1,762 B both, + 256 B reciprocals; ~52 cycles a pair rejected, 2,300-3,600 in contact | dev/examples/catapult |
| `VL_CIRC_BOUNCE` / `VL_CIRC_VMIN` | lib/physics `verlet_circ.asm` | Restitution e/256 (0..255) of a closing speed above VMIN (8.8), else inelastic: `MUL_K16`, +~60 B, +~80 cycles an impulse | dev/examples/catapult |
| `VL_CIRC_HEAVY` = n | lib/physics `verlet_circ.asm` | `vl_cheavy` (n B BSS): a heavy point against a light one takes half − half>>n of each share (the `VL_CON_HEAVY` rule) | dev/examples/catapult (the projectile) |
| `VL_CIRC_FRICTION` = f | lib/physics `verlet_circ.asm` | `vl_contact_box`: the tangential speed loses vt>>f (`vl_damp`) | dev/examples/catapult |
| `VL_CIRC_SLEEP` = v / `_TICKS` | lib/physics `verlet_circ.asm` (with `VL_PIN`) | `vl_circ_sleep`: a free point slow (\|vx\|, \|vy\| ≤ v) for 16 ticks gets `vl_pin` = $80 (asleep: skipped, pinned in a pair); a closing speed > v wakes it. `vl_still` (n B BSS), +~170 B | dev/examples/catapult |
| `MUL_INIT_BOOT` / `MOUSE_INIT_BOOT` | `mul.asm` / `mouse.s` | Initialisation code in the `INIT` segment, reusable after startup | dirtbike / dirtbike |
| `STICK_KEY_FAST` | `joy.asm` | `stick_key` samples with `read_stick_fast` (0.1-2.8 ms instead of 6 ms; its count scale: retune `JOY_LO`/`JOY_HI`) | none (dev/tests/test_stick_key.py) |
| `DOS_CMD_HEX_IFREF` | `dos.asm` | `dos_cmd_hex` assembled only if referenced: −48 B | arkabreakout, maze3d |
| `EXIT_USE_NATIVE_VIDEO` | `exit.asm` | Reuses `native_video` from `hgr.asm`: −21 B | arkabreakout, maze3d, micro-sokoban |
| `SOUND_GATE` | `sound.asm` | Sound muted by one byte: −7 B and −10 cycles per note against an envelope in the program | maze3d |
| `SYSRELOC_DOWN_FAST` | `prodos/sysreloc.inc` | Downward copy as the `len&$FF` tail then whole pages (`dey`/`lda (),y`/`sta (),y`/`cpy #0`): 18 cycles per byte instead of 53, 40 B inline instead of 60, still in descending address order (overlap-safe); lengths below `$8000` | chromabreak, robotspacestation, wargalagaii (boot ~0.7 s faster) |
| `AUXMEM_FETCH_CHUNK` / `AUXMEM_FETCH_SCAN` | `apple2/auxmem.asm` | `aux_fetch_chunked`: chunk size (default 64 B, ~2,300 cycles masked each; bigger = fewer ~60-cycle AUXMOVE setups, longer masked windows) / `jsr _a2_vbl_scan` between chunks (+3 B, ~30 cycles a chunk) | wargalagaii (`SCAN`) |
| `MB_IRQ_PRODOS` / `MB_IRQ_VECTOR` | `apple2/mb_irq.asm` | The interrupt through ProDOS `ALLOC_INTERRUPT` (1, default) or an own vector: `$03FE` behind the ROM's handler (A at `$45`; DOS 3.3, bare programs) or `$FFFE` with the language card's RAM in (raw entry, A/X/Y saved): +16 B (65C02) to +22 B (NMOS) | wargalagaii (ProDOS) |
| `MB_IRQ_SCAN` | `apple2/mb_irq.asm` | `jsr _a2_vbl_scan` on the handler's entry and exit (a long tick hides no //e VBL edge): +6 B, ~60 cycles a tick | wargalagaii |
| `MB_IRQ_FRAME` / `MB_IRQ_GATE` | `apple2/mb_irq.asm` | The tick's 14-byte frame flushed to chip 1 inline by the handler (~16 cycles a register unchanged, R13 when not `$FF`) instead of the tick writing through `mb_put` / a byte that pauses the tick (+5 B) | wargalagaii (PT3 frame, `music_on`) |
| `MB_IRQ_HUSH_BOTH` / `MB_IRQ_SPLIT` | `apple2/mb_irq.asm` | `mb_hush` silences both chips (6-voice songs) / the handler assembled only where the program references `mb_irq_handler` (placement) | mbtracker / wargalagaii |
| `AYSONG_VOICES` | `apple2/aysong.asm` | 6: both chips: 3 more voices of 19 B and 32 B more of registers in BSS, the second chip's mixer and write loop (+78 B code) | — (dev/tests/test_aysong.py) |
| `AYSONG_FAST_PERIODS` | `apple2/aysong.asm` | A 96-note period table instead of 12 notes + octave shifts with a per-voice cache: +112 B code/table, −3 B BSS a voice, ~230 cycles less on a row of three new notes (~25 a tick on average) | — (dev/tests/test_aysong.py) |
| `AYSONG_CPU65C02` | `apple2/aysong.asm` | `stz` forms: −4 B (assemble for the 65C02) | — (dev/tests/test_mb_irq.py) |
| `EZ_ZP` | `apple2/ezcolor.inc` | `ez_slot`/`ez_slotx` in zero page instead of BSS (2 B ZP): −1 cycle and −1 B for each `LDX ez_slotx` | — (dev/tests/test_ezcolor.py) |
| `EZ_PAIR_SEI` | `apple2/ezcolor.asm` | `ez_set_reg`/`ez_vram_addr_*` mask IRQs around their two control bytes (for an IRQ handler that reads the VDP status, which resets the byte flip-flop): +4 B and +7 cycles each | — |
| `EZ_DETECT_SKIP3` / `EZ_DETECT_ORDER` / `EZ_DETECT_BOOT_SLOT` | `apple2/ezcolor.asm` | Probe slot 3 last (0; default 1 = skipped) / your own zero-terminated slot list / skip the slot in bits 4-6 of that byte (`$B7E9` DOS 3.3, `$BF30` ProDOS); placement, not speed | — (dev/tests/test_ezcolor.py) |
| `TMS9918_M1_ZP` / `TMS9918_M2_ZP` / `TMS9918_CONSOLE_ZP` | `tms9918/tms9918.inc` | Reserve the drivers' zero page at the top of the source (6 / 17 / 3 B; M1 default on) so code above the drivers uses zero-page addressing; off: the driver reserves it later (absolute operands before, ca65 warnings) | — (dev/tests/test_ezcolor.py) |

The modules' other definitions (ZP addresses, `DOS_ZP_*`, `RWTS_*`,
`HGR_SPR_MAX`, `HG_HOOK_*`/`HP_OR_PLOT` hooks, `WF_*_TABLE` tables…)
place or wire the code: they are not speed/RAM trade-offs.
