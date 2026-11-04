# Current cc65 measurements

Native HGR row construction takes **6,921 cycles** instead of 45,783,
with no C-stack use. Independent row/query/display archive members save
**687 code bytes and 50 RAM bytes** in a point-only client. A display-only
client saves **800 code bytes and 435 RAM bytes**; `hgr_show_page()` takes
29/30 cycles. `hgr_row(191)` takes **52 cycles** instead of 236. Page
selection retains synchronous HGR/LORES table updates. The full HGR/DHGR
comparison and small layout-dependent slowdowns are recorded in
[HISTORY.md](HISTORY.md); `baseline.json` contains current per-case figures.

Native draw-page selection takes **79 cycles** for the already selected
page instead of 246, with no C-stack use. A page-2/page-1 round trip with
LORES ready takes **5,615 cycles** instead of 8,904. Separating LORES state
from the manager removes **388 RAM bytes** and **391–420 loaded bytes**
from default-page read/write/clear clients. Explicit page-selection clients
still import both table families; their isolated manager saves 191 code bytes.

LORES clearing uses eight interleaved native stores and preserves the 64
firmware bytes on each page. The two page cases take **5,442/5,443 cycles**
instead of 50,307 (about −89 %). The clear pass saved **212 loaded bytes**
in each isolated client and all 14 measured C-stack bytes. Lazy LORES address construction
and point writes also use compact native code: the cold/warm point cases
take **821/204 cycles** instead of the original 11,796/806. The LORES
passes alone saved **356 loaded bytes**. Native point reads take **148 cycles**, compared with 318
after the table optimization but before replacing the C reader; that pass
saves another 59 loaded bytes in isolated reader clients. RAM and zero page
are unchanged. `--only lores` measures these
cases and the horizontal line; all are included in the regression gate.

LORES horizontal/vertical runs and rectangles now share a clipped native
kernel. Fully covered vertical pairs use direct byte stores, with masks
only for unmatched edge nibbles. A 40-cell horizontal line takes **1,174
cycles** instead of 5,728; a 48-cell vertical line takes **2,035** instead
of 19,000. A 20×16 rectangle takes **3,265** instead of 51,594, and the
40×48 rectangle **12,367** instead of 280,648 (−95.6 %). The span pass saved
**92/120/308 loaded bytes** in isolated clients for horizontal/vertical/rectangle calls.
Their C-stack peaks fall to 3/3/4 bytes, with unchanged RAM and zero page.
The pixel-address helper is a separate archive member, omitted by these
native clients. Empty/clipped spans and rectangles have their own cases.

Native C-ABI wrappers for byte/pixel rectangles and cells save **78/226/25
loaded bytes** in isolated clients, with no extra RAM or zero page. A
one-byte fill takes **309 cycles** instead of 406; a pixel rectangle clipped
at the lower right takes **665** instead of 1,041. The 140×16 pixel fill
now takes **4,845 cycles** and `hgr_cell(1,4,1)` takes **708**. The pixel
wrapper reduces its C-stack peak from 13 to 4 bytes and hardware peak from
9 to 6. Cold valid/empty/invalid cases preserve lazy table initialization.

Independent HGR column/mask/phase builders fill groups of seven pixels,
saving **54 code bytes** in total. Cold calls take **4,040 / 4,520 / 4,440
cycles** instead of 7,029 / 8,434 / 6,749 (four extra cycles at some table
alignments). The cold pixel rectangle falls from **23,104 to 16,199 cycles**.
RAM, zero page, stack peaks and warm guards stay unchanged. The optional
folded builder now takes **74 bytes / 10,327–10,350 cycles**, down from
77 / 15,084, by removing per-pixel calls and copying the 24-byte tail.
It saves 56 code bytes and cold initialization time when all three tables
are needed, while still reserving all 841 B of table state. The cold folded
HUD/scene calls take **47,085 / 27,734 cycles** (previously 51,853 / 32,491).
The two-table diagonal still uses less RAM and initializes faster with
independent builders. All 256 alignments are verified.

The native math fixtures are measured by `python3 dev/tests/test_math.py`.
Quarter-square table construction takes **37,691 cycles and 110 code bytes**
(−22.6 % and −18 bytes); square-root seed construction takes 24,031 cycles.
The root kernel saves two bytes and two cycles per ordinary candidate step,
with a two-cycle cost increase when returning 255. All 65,536 roots and
every generated table byte are checked at two table placements; details are
in [lib/math](../lib/math/README.md).

General constant multiplication macros save **5 bytes and 8 cycles** per
expansion, signed or unsigned. Zero, one and powers of two now use smaller
table-free paths: ×64 takes **53 cycles and 22 code bytes**, compared with
80 cycles and 44 bytes in the general path (input $FFFF, JSR/RTS included). `mul_acc_shr6` saves **3 bytes and 3 cycles**
by falling through to the shift. `test_math_products.py` checks 1,572,864
products and the optional accumulator/shift inclusion combinations. These
native math costs are separate from the C graphics benchmark gate.

The unsigned 16/8 divider uses two byte stages for long quotients: **51
code bytes** instead of 52 and **92 fewer cycles** on that path, with a
**two-cycle increase** for short quotients. `make test-math-division-full`
checks all 16,777,216 input pairs, including zero divisors and preserved Y.
For 65535/255 the cost is **349 instead of 441 cycles** including JSR/RTS;
RAM, zero page and stack are unchanged.

The corridor kernel extracted from Light3DBall is measured separately with
`python3 dev/bench/corridor_projection.py` (`make bench-corridor`). All
65,536 depth differences and coordinates 0..127 for every admissible factor
are checked with both IRQ masks. Costs include JSR/RTS, with no C arguments:
selection 65..77 cycles, X 135..170, Y 129..164. The extraction keeps the
binaries identical and changes these measurements by 0 %. `--before DIR`
compares an earlier capture containing `game.bin`, `game.lbl` and
`assets.bin`. The addresses of branches and tables affect these costs.

```sh
make bench
make bench-dhgr
make bench-check
python3 dev/bench/run.py --dhgr --check
python3 dev/bench/run.py --dhgr --out /tmp/apple2-metrics.json
make test-dhgr
```

The script compiles one program per workload with `-Oirs`, boots DOS and
measures between two instruction markers. Cycles include C arguments and
calls, and exclude initialisation and the 12 cycles of the markers. Cold
cases include the lazy tables; warm cases prepare both histories. HGR uses
a2run NMOS 6502; the IIe variants use the POM2 65C02 SDK. Older measurements
are collected in [HISTORY.md](HISTORY.md).

Compact DHGR text (`dhgr_small_text`, `dhgr_puts_small("APPLE II",0,0)`)
takes **13,253 cycles**, with a 2,990-byte binary and 326 bytes of RAM.
Preparing the invariant addressing once per glyph and skipping auxiliary
reads for fully covered bytes saves 8.5 % of the cycles, 4 loaded bytes and
2 BSS bytes. The tables, zero page and measured stack peaks are unchanged.

Standard opaque DHGR text (`dhgr_puts("APPLE II",0,0)`) takes **32,246
cycles** instead of 44,259 (−27.1 %), with a **2,852-byte binary** and
336 RAM bytes. Alternating auxiliary/main writes keeps the page column
in Y instead of recomputing it per byte. The row counter uses existing
cc65 scratch and the row buffer only needs six bytes. Each high part of a
pixel pair starts a fresh byte; just one possible gap needs zeroing before
the row. Together these changes save **19 loaded bytes and three BSS
bytes**, with unchanged zero page and stack peaks. Starts at colour x=3/6
take 32,566/32,042 cycles; eight spaces take 32,288. The final buffer pass
alone saves another 13.6..13.9 % and nine loaded bytes (16 code bytes less,
seven more bytes of immutable tables).

DHGR block transfers keep the bank in A while advancing the pointers,
and initialise the address without a nested helper call. Masked sprites
merge with `~(~screen | write_mask)` before adding the source bits. This
saves **15 code bytes and two hardware-stack bytes at the measured peak**,
with unchanged RAM and zero page. Reading/writing an 8×8-byte block takes
6,987/6,615 cycles instead of 7,207/6,839. The 14×8-colour-pixel sprite
with partial masks takes 12,208 instead of 12,683 cycles (−3.7 %);
fully opaque masks take 10,095 instead of 10,315.

Bounded DHGR clearing (`dhgr_clear_rows`) uses a register counter for the
four turns of each pattern pass and passes the row's high address byte in
A. The native row kernel takes **688 cycles** instead of 712, with **12
fewer code bytes**. Including C arguments, one line takes 1,090 cycles,
16 lines take 11,725 and all 192 visible lines take 136,555 (−3.3 %).
RAM, zero page and stack peaks are unchanged; each line still restores
main RAMWRT and the caller's IRQ mask, allowing IRQ servicing between rows.

The warm HGR point cases measure 247/256 cycles for set/clear, including C
arguments. The 7×16 XOR sprite cases `hgr_preshift_phase0/3/6` measure
2,078/2,465/2,540 cycles; phase zero skips the height × stride calculation.
This HGR pass removes 14 code bytes from the point kernel and 6 from the
aligned sprite kernel, with no change to RAM or zero page.

HGR recolouring (`hgr_colorize`, 140×16 pixels starting at x=7) now takes
**8,612 cycles**, with a **980-byte isolated binary**. The native wrapper
alone saves **180 loaded bytes** and 334 cycles versus the preceding
8,946-cycle version. Starting at x=0 takes 8,558 cycles; one byte on one
row takes **450 instead of 788**. Its C-stack peak falls from 10 to 5 bytes,
hardware peak from 7 to 6, with unchanged RAM and zero page. The kernel
retains its alternating even/odd column bodies and shared carrier selector.
Cold tests verify arguments across both normal and folded table builders,
clipping, rejected colors and carrier preservation.

Doubled HGR text skips blank glyph rows, shares the alternating carriers
and simplifies the destination-column shifts. At phase zero, white
`"APPLE II"` takes 15,052 cycles and orange text 15,125. The doubled-kernel
optimization saves **30 code bytes
and 5 zero-page bytes**, without changing other RAM, tables or stack peaks.
Eight spaces take 3,894 cycles; a fully filled native
16×16 glyph at phase six takes 2,641 instead of 2,873 (−8.1 %).

The doubled-text wrapper computes the visible cell count with a bounded
fastcall helper instead of a C subtraction loop on the software stack.
The helper allocates no memory; its independent archive member is omitted
by native-glyph and HUD clients. Isolated C text clients save **71 code
bytes and three C-stack bytes at peak**. White `"APPLE II"` improves from
16,681 to 15,052 cycles (−9.8 %), eight spaces from 5,420 to 3,894
(−28.2 %), and an empty string from 2,153 to 627. RAM and zero page stay
unchanged; the glyph kernel itself has the same cost.

Signed HGR numbers set the conversion destination directly and reuse the
value parameter for its magnitude. Removing two temporary stack variables
saves **40 loaded bytes and four C-stack bytes at peak** in isolated clients,
with unchanged RAM and zero page. Printing −32768/−12345/32767 takes
12,810/12,318/11,800 cycles, about 1 % less than before. The magnitude is
formed by unsigned negation, including −32768.

Unsigned number fields compute their erased width as `width*18-2`, which
fits in one byte after the existing clamp to 14 cells. The width parameter
is then reused for right-alignment padding. This saves **33..50 loaded
bytes and two C-stack bytes at peak**, depending on runtime sharing, with
unchanged RAM and zero page. A padded 14-cell field takes 13,763 instead
of 14,078 cycles; an overflowing one-cell field takes 14,384 instead of
14,695, and a right-clipped field takes 4,239 instead of 4,544. The legacy
warm HUD takes 30,539 instead of 31,213 cycles.

Native-size 8×8 `"APPLE II"` takes **7,886/8,672/8,563 cycles** at phases
0/3/6 (−6.1..6.7 %), with **11 fewer code bytes** and unchanged RAM, zero
page and stack peaks. X counts glyph rows and the upper shifted byte no
longer needs a mask. The shared `glyph_addr` helper contributes 3 of the
saved bytes: splitting the offset into high/low parts takes 54 cycles
instead of 61, including JSR/RTS, while preserving X/Y. Doubled-text and
HUD clients that link this helper also save those 3 bytes.

The pixel-rectangle kernel shares its single-byte and multi-byte edge-mask
setup, removes redundant mask operations and skips the interior counters
for single-byte rectangles. This saves **42 code bytes** in every client
that links it, with unchanged RAM, zero page and measured stack peaks.
With the native wrappers, the 140×16 fill takes 4,845 cycles, and a 6×6
cell takes 708. The single-byte
clear changes from 1,691 to 1,693 cycles. The HGR diagonal client also loses
42 bytes but measures 21,319 cycles instead of 21,171 (+0.7 %); the GFX
diagonal takes 21,323 instead of 21,407. See the measured tradeoffs in
[HISTORY.md](HISTORY.md).

Packed MSB-first bitmap blits (`hgr_blit`, 16×8 pixels) take 5,935..6,320
cycles across SET/CLEAR/XOR and phases 0/3/6. A sentinel bit in the source
shift register replaces the eight-bit countdown; its byte index uses the
unused high byte of `ptr2`. This saves **6 code bytes and one zero-page
byte**, and 9.4..10.0 % of the mixed-bitmap time, beyond the preceding
eight-byte reduction from sharing mode stores and stopping before a final
refill. RAM and stack peaks are unchanged. Empty/solid bitmaps take
4,920/6,592 cycles (previously 5,576/7,248); the bottom/right-clipped XOR
case takes 1,207 instead of 1,249.

Byte rectangles traverse each row backwards, using Y as both the offset
and loop counter. Pairs take 19 instead of 21 cycles and an odd width
enters at the second store. The kernel saves **7 code bytes**, with
unchanged RAM, zero page and stack peaks. A 40×16-byte fill takes
**7,097 cycles** instead of 7,824; a 39×16 fill takes 6,985
instead of 7,568 (−6.5 %). The single-byte and clipped cases take 406/514
cycles. The new cases include fill values with the palette bit set.

## Frame rate and absolute budgets

The target is two refreshes per presentation: nominally 30 FPS NTSC and
25 FPS PAL. The SDK beam measures 17,030/20,280 cycles per refresh, checked
against the VBL edges. Native POM2 profiles use different units
(17,045/20,313): they are not mixed into these budgets.

`budgets.json` sets a limit independent of regressions: two periods, minus
**6,000 cycles reserved** for more logic, sound and IRQs. `--check` fails if
the workload exceeds this limit, even after a baseline reset. The reservation
is a chosen envelope, not a measurement of every possible logic or music. The
report gives limit, cost and margin.

| Current workload | Cycles |
|---|---:|
| 16×16 HUD, value unchanged | 312 |
| 16×16 HUD, one digit changed | 3,926 |
| 16×16 HUD, five digits changed, maximum over seven phases | 15,819 |
| 8×8 HUD, value unchanged | 312 |
| 8×8 HUD, one digit changed | 2,283 |
| 8×8 HUD, five digits changed, maximum over seven phases | 6,663 |
| Compact game: two moving 7×8 sprites, three digits all changed, keyboard, positions, presentation | 15,602..15,865 |
| Four isolated 21×16 sprites, only the first one moving, default engine | 31,031 |
| Same scene, option `HGR_SPR_DAMAGE=1` | 14,662 |
| Stress: four 21×16 sprites all moving + counter + presentation | 38,578 |

The compact game is measured at all seven alignments, in NTSC and PAL. The
limits after the reservation are **28,060/34,560 cycles**; its worst phase
still leaves 12,195/18,695 cycles beyond the reservation. Positions and values
use a period of three so that each page finds a modified state again. The HUD
value does not just alternate with the page: its three digits really change
in the measured case. The modulo shared by the movements and the score is
computed once per frame.

The isolated scene saves 52.8 % with the assembly computation of the
intersections: 437 loaded bytes and 43 extra BSS bytes at eight slots. The
option stays disabled by default. Four large sprites all moving still cost
38,578 cycles: they exceed two NTSC periods and the PAL limit after the
reservation. The overloaded stress cases remain diagnostics.

The native counter uses the cached digits for +1/+2; the 9999 → 10000
transition costs 6,113 cycles in the 8×8 HUD. Its pre-shifted digits take
1,386 bytes of RODATA, shared between fields. A HUD-only client avoids the
mutable row/column LUTs and the general font; a client that also displays
text pays for both banks. The compact game uses 7,083 loaded bytes,
1,618 bytes of RAM and 47 zero-page bytes. Both HUD controllers reuse the conversion's digit
count and finish the origin division in eight bits: 24 fewer code bytes
per format, with unchanged tables, RAM and zero page.

The compact HUD kernel now counts source offsets in X, saving 18 code
bytes and two BSS counters. Separating glyph arguments, string state and
the font-address helper into archive members removes another 26 code
bytes and seven zero-page bytes from HUD8-only clients. Their measured
binary is 3,417 bytes, with 345 RAM bytes and 35 zero-page bytes. Changing
five digits is about 11 % faster; the unchanged-value path stays at 312
cycles. This archive split alone saves five zero-page bytes in HUD16-only
clients without changing their timing.

The 16×16 HUD kernel writes its fully covered second column directly,
assembles the upper pixels with two rotations and expands its three
single-use edge writers in place. It saves **42 code bytes and one BSS
byte**, with unchanged zero page and measured stack peaks. Five changed
digits take 14,974..15,819 cycles (about 17 % less); one changed digit
takes 3,926 instead of 4,495. The unchanged-value path remains at 312.
The isolated client uses 3,623 loaded bytes and 805 RAM bytes. The VBL-paced
loop measures 34,055 instead of 34,048 cycles, including its wait; the
work-only moving scenes all improve. See [HISTORY.md](HISTORY.md).

The optional tilemap backend restores eight 7×8 tiles then draws two masked
sprites without save-under in 6,704 cycles. The map is 960 bytes, supplied by
the application; a full rebuild is not presented as a 30 FPS workload. The
region profiles keep the 6,000-cycle reservation.

Masked HGR sprite kernels share two cc65 scratch bytes for the phase-block
product, omit a row-address carry that cannot occur and count generic
columns backwards in Y. They save **8 code bytes and two zero-page bytes**,
with unchanged RAM and stack peaks. On a 7-byte × 8-row sprite, generic
draw/save/restore/save-and-draw take 2,885/1,791/1,802/3,232 cycles, saving
4.9..8.2 %. The compact game saves 62..70 cycles per frame. The historical
stationary scene with legacy number fields gained 14 cycles (+0.11 %)
during this kernel pass; the subsequent field-wrapper change brings it
to 12,975 cycles. Other affected scenes improved or kept their timing.

`test_cadence.py` tests 1,000 presentations per standard with a VIA IRQ
aligned to the VBL, a variable workload and two deliberate overruns: two
ticks per normal frame, deadline skipped on overload, no burst catch-up. It
also checks the VBL at flip, the wrap, invalid arguments, stopping the clock
and I. The application must provide the IRQ source; the library installs
neither a card nor a vector.

`test_game_cadence.py` also runs a complete game: four moving sprites,
collisions, keyboard, HUD and AY music under IRQ, 1,000 frames per standard.
It checks 2,000 music ticks, zero missed deadlines, the VBL flip, both stacks
and the wrap: 33,972..34,147 / 40,470..40,653 cycles between presentations.
Tables and histories are prepared before the clock starts. The cadence test
also covers sixteen long suspensions: 10,000/32,760 ticks, periods 1..8. The
16-step ASM division avoids the false timeout of the catch-up.

The minimal double-buffer example needs no card: it spreads its drawing and
its 8×8 HUD over two VBL phases. Its 1,000 NTSC/PAL frames cover the counter
65535 → 0, with **34,050..34,070 / 40,550..40,570 cycles** per frame, with no
missed refresh. This result is specific to this workload on POM2 IIe; the
timed fallback on II/II+/IIc adds the rendering to its wait.

## Memory and stacks

The sizes cover the whole measurement program: CRT, cc65 runtime,
CODE/STARTUP/LOWCODE/INIT/ONCE, RODATA, BSS/LOWBSS/DATA/ZPSAVE, ZP and binary.
Code + loaded data are checked against the actual size of the binary. The
video pages and the reserved C stack are kept separate from BSS.

The C counters observe the cc65 pointer at consistent call, return, jump and
`(sp),Y` access boundaries; a2run also observes stack writes. `hwstackwatch`
follows S instruction by instruction; the hardware depth includes the initial
occupancy and the IRQs in the window. `hwstack` reports the maximum `255-S`
and an overflow on wrapping below zero. The probes check 37 pushes and a
deliberate overflow on both runners. These observations cover the executed
paths, without amounting to a universal static analysis. Profiling adds no
emulated CPU cycles.

## References and reproducibility

`baseline.json` records compiler, flags, CPU, model, beam period and SHA256
of the runners, cores and ROM. `--check` rejects a cycle increase above 5 %
(minimum 16), a size increase above 3 % (minimum 16 bytes) or any ZP
increase. The gate checks the CPU, model and beam period; host binaries
may vary between systems. A new emulator core or ROM (a POM2 SDK delivery,
a change to a2run's CPU) is reported, not rejected: the metrics are still
held to the baseline, so a core that counts differently shows up as a
regression, and `--update` records the new hashes. The absolute budgets
remain checked independently.
The historical references, `pre_incremental_references` and `pre_native_references` are kept. The caps of the independent primitives are not reset.

After reviewing an intentional change:

```sh
python3 dev/bench/run.py --dhgr --update
```

This replaces the references for the measured cases. A normal run or `--check`
does not modify them. The bundled SDK requires macOS ARM64; the a2run HGR
cases remain portable. The evaluation of alternative techniques is separate,
in [tests/techniques](../tests/techniques/README.md), via `make test-techniques`.
