# Current cc65 measurements

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
| 16×16 HUD, one digit changed | 4,739 |
| 16×16 HUD, five digits changed, maximum over seven phases | 22,235 |
| 8×8 HUD, value unchanged | 312 |
| 8×8 HUD, five digits changed, maximum over seven phases | 7,850 |
| Compact game: two moving 7×8 sprites, three digits all changed, keyboard, positions, presentation | 16,774..17,040 |
| Four isolated 21×16 sprites, only the first one moving, default engine | 31,031 |
| Same scene, option `HGR_SPR_DAMAGE=1` | 14,662 |
| Stress: four 21×16 sprites all moving + counter + presentation | 39,217 |

The compact game is measured at all seven alignments, in NTSC and PAL. The
limits after the reservation are **28,060/34,560 cycles**; its worst phase
still leaves 11,020/17,520 cycles beyond the reservation. Positions and values
use a period of three so that each page finds a modified state again. The HUD
value does not just alternate with the page: its three digits really change
in the measured case. The modulo shared by the movements and the score is
computed once per frame.

The isolated scene saves 52.8 % with the assembly computation of the
intersections: 437 loaded bytes and 43 extra BSS bytes at eight slots. The
option stays disabled by default. Four large sprites all moving still cost
39,217 cycles: they exceed two NTSC periods and the PAL limit after the
reservation. The overloaded stress cases remain diagnostics.

The native counter uses the cached digits for +1/+2; the 9999 → 10000
transition costs 7,109 cycles in the 8×8 HUD. Its pre-shifted digits take
1,386 bytes of RODATA, shared between fields. A HUD-only client avoids the
mutable row/column LUTs and the general font; a client that also displays
text pays for both banks. The compact game thus goes from 6,895 to 7,231
loaded bytes and from 1,571 to 1,620 bytes of RAM, with no ZP increase.

The optional tilemap backend restores eight 7×8 tiles then draws two masked
sprites without save-under in 9,546 cycles. The map is 960 bytes, supplied by
the application; a full rebuild is not presented as a 30 FPS workload. The
region profiles keep the 6,000-cycle reservation.

`test_cadence.py` tests 1,000 presentations per standard with a VIA IRQ
aligned to the VBL, a variable workload and two deliberate overruns: two
ticks per normal frame, deadline skipped on overload, no burst catch-up. It
also checks the VBL at flip, the wrap, invalid arguments, stopping the clock
and I. The application must provide the IRQ source; the library installs
neither a card nor a vector.

`test_game_cadence.py` also runs a complete game: four moving sprites,
collisions, keyboard, HUD and AY music under IRQ, 1,000 frames per standard.
It checks 2,000 music ticks, zero missed deadlines, the VBL flip, both stacks
and the wrap: 33,969..34,151 / 40,468..40,647 cycles between presentations.
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
increase. The gate checks core/ROM/model; host binaries may vary between
systems. The absolute budgets remain checked independently.
The historical references, `pre_incremental_references` and `pre_native_references` are kept. The caps of the independent primitives are not reset.

After reviewing an intentional change:

```sh
python3 dev/bench/run.py --dhgr --update
```

This replaces the references for the measured cases. A normal run or `--check`
does not modify them. The bundled SDK requires macOS ARM64; the a2run HGR
cases remain portable. The evaluation of alternative techniques is separate,
in [tests/techniques](../tests/techniques/README.md), via `make test-techniques`.
