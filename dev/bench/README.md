# Current cc65 measurements

The twenty-fifth-session gate passes **793 cases and 16 frame budgets**.
Nine tile-restoration clients save **ten code/loaded bytes and two RAM
bytes**; seven accelerate and two keep their timing. All 784 other metric
dictionaries are identical; **34 limits are lowered**, none raised. A full
page takes **181,665 instead of 268,169 cycles** (−32.3%). Dedicated profiles
also validate smaller keyboard entries, signed constant products and a
257-byte native projection. See [the twenty-fifth-session audit](HISTORY.md#audit-de-la-vingt-cinquième-session-du-6-novembre-2026--tuiles-clavier-et-produits).

The twenty-fourth-session gate passes **793 cases and 16 frame budgets**,
with **every timing identical**. Eight HGR controls save 48 RAM bytes;
22 text clients save two or four loaded/code bytes. All 763 other
metric dictionaries are identical, and **52 limits are lowered**. Dedicated
profiles cover 72-byte sprite-init RAM savings, a native projection saving
444 loaded bytes and 613..1,000 cycles per call, and a 25.1% faster math
initializer. Shared archive ordering preserves the full HGR demo byte for
byte. See [the twenty-fourth-session audit](HISTORY.md#audit-de-la-vingt-quatrième-session-du-6-novembre-2026--état-hgr-projection-et-initialisation).

The twenty-third-session gate passes **793 cases and 16 frame budgets**.
Splitting sprite archive members saves **1,538..1,775 loaded bytes,
571..1,009 RAM bytes and 11 ZP bytes** in eight move clients, with identical
call times. Three rendering timings improve by one cycle; seven cost
1..15 extra placement cycles (at most 0.27%); 775 dictionaries are unchanged.
**44 limits are lowered**, none raised. Separate profiles also cover smaller
ProDOS LOAD tails, projection clients saving 31 loaded bytes and improved
CUTROPE/CATAPULT integration. See [the twenty-third-session audit](HISTORY.md#audit-de-la-vingt-troisième-session-du-6-novembre-2026--membres-darchive-et-chemins-communs).

The twenty-second-session gate passes **793 cases and 16 frame budgets**.
HGR scratch reuse and T80 inversion shrink **88 clients**; **67 timings
improve, 18 are equal**, with three placement costs of 3..19 cycles (at
most 0.27%). All 705 other dictionaries are identical. **389 limits are
lowered**, none raised. Dedicated helpers also shrink ProDOS reads by two
bytes; a ten-byte pinned-pair precheck cuts CATAPULT's median flying work
from 11,339 to 10,294 cycles. Six rebuilt games, CATAPULT and all 18 WOZ
pairs pass. See [the twenty-second-session audit](HISTORY.md#audit-de-la-vingt-deuxième-session-du-6-novembre-2026--temporaires-hgr-texte-et-collisions).

The twenty-first-session gate passes **793 cases and 16 frame budgets**.
Masked save/restore setup and row carries improve **51 timings**, with
every footprint/stack metric unchanged and no regression; 742 dictionaries
are identical and 49 cycle limits tighten. Four moving sprites take
**37,115 instead of 37,531 cycles**. Separate measured passes save 10..12
bytes in generic physics constraints, 21 in directory clients and two in
DOS command preparation; the existing low-gain correction is preserved.
See [the twenty-first-session audit](HISTORY.md#audit-de-la-vingt-et-unième-session-du-6-novembre-2026--sprites-masqués-décalages-et-commandes).

The twentieth-session gate passes **793 cases and 16 frame budgets**.
Independent native HGR sprite entries shrink **56 clients by 356..949
loaded bytes**. Eighteen timings improve, eight stay equal and thirty rise
by 2..206 cycles (at most 0.685%); 737 dictionaries are unchanged and 130
reference fields tighten. Separate initialization/definition profiles all
accelerate, saving 522..729 loaded bytes; valid definition takes **388
instead of 1,362 cycles** with lower stack peaks. Original C entries remain
available and reproduce the original benchmarks. See [the twentieth-session audit](HISTORY.md#audit-de-la-vingtième-session-du-6-novembre-2026--entrées-natives-du-moteur-hgr).

The nineteenth-session gate reproduces **all 793 cases and 16 frame
budgets unchanged**. Separate directory benchmarks save **94 loaded
bytes and five RAM bytes** in all 56 profiles: 54 calls accelerate,
two empty-geometry calls rise by 25 cycles (0.121%). The 51-byte divider
saves up to 35 cycles on representative long divisions; both CPUs pass
the full 16,777,216-pair domain and all 256 code alignments. MBTRACKER
uses the native directory in its existing overlay placement and passes
its full integration suite. See [the nineteenth-session audit](HISTORY.md#audit-de-la-dix-neuvième-session-du-6-novembre-2026--répertoire-natif-et-division).

The eighteenth-session gate passes **793 cases and 16 frame budgets**.
Overlay row reuse and unrolled byte operations make the tall overlay
**33.7% faster**, adding 17 code bytes and freeing five BSS bytes in 35
clients. Sixteen timings improve, seven stay equal, and twelve rise by
1..144 cycles (at most 0.766%); previous limits are retained. The other
758 dictionaries are identical and 49 reference fields tighten.
Separate focused tests show **18 code/three RAM bytes and 24 cycles saved
per MLI call**, and **25 code bytes plus 95..106 cycles saved per ground
call**. See [the eighteenth-session audit](HISTORY.md#audit-de-la-dix-huitième-session-du-6-novembre-2026--mli-sondes-du-terrain-et-overlay).

The seventeenth-session gate passes **793 cases**. Compact DHGR packing
shrinks 35 clients by five loaded bytes: 24 timings improve, four stay
equal and seven rise by at most 0.175%; previous limits are retained.
758 dictionaries are unchanged, all 16 frame budgets pass and 90 reference
fields tighten. Separate measured DOS wrappers save eleven code/five RAM
bytes; physics helpers save ten code bytes in generic clients and three
in FAST clients, with no measured constraint slowdown. See [the seventeenth-session audit](HISTORY.md#audit-de-la-dix-septième-session-du-6-novembre-2026--commandes-dos-packing-dhgr-et-arithmétique).

The sixteenth-session gate covers **793 cases**. Running cursor row pointers
make a supported tall DHGR move **82.4% faster**, costing four code bytes.
T80 character/fill register reuse saves one code byte in 22 clients and one
hardware-stack byte in twenty. **33 timings improve**; fifteen rise by
1..16 cycles (under 0.2%), with previous limits retained. 736 dictionaries
are unchanged, all 16 frame budgets pass, and 97 reference fields tighten.
Separately, generic physics constraints save 16 loaded bytes and 71..99
cycles per measured call; FAST variants remain byte-identical. See [the sixteenth-session audit](HISTORY.md#audit-de-la-seizième-session-du-6-novembre-2026--curseur-dhgr-texte-80-colonnes-et-contraintes).

The fifteenth-session benchmark covers **759 cases**, including 17 new
workloads measured against the old kernels. Backward HGR byte blits,
indexed DHGR sprite sources and native ellipses shrink **106 clients**
by 3..272 bytes. **61 timings improve**; three gain one cycle and one
rejected ellipse gains six. The other 653 result dictionaries are identical.
RAM and zero page stay unchanged; 18 ellipse clients save 7..19 C-stack
bytes. Full-page HGR SET takes **172,739 instead of 195,299 cycles**;
a small HGR ellipse takes **105,892 instead of 151,671**. All 16 frame
budgets pass and 293 reference fields are tightened. See [the fifteenth-session audit](HISTORY.md#audit-de-la-quinzième-session-du-6-novembre-2026--blits-par-octets-et-ellipses-natives).

The fourteenth-session benchmark has **742 cases**, including 35 workloads
measured with the old kernels first. Bitmap endings, DHGR damage merging
and CMOS decimal scratch improve **63 timings**, with **no metric increase**;
677 result dictionaries are identical and two affected timings are unchanged.
38 clients shrink by 4 or 17 loaded bytes, fifteen save five RAM bytes,
and zero page/stacks stay unchanged. Merging 22 disjoint rectangles takes
**29,156 instead of 35,693 cycles**; CMOS conversion takes **873 instead
of 1,055**. All 16 frame budgets pass and 149 reference fields are tightened.
See [the fourteenth-session audit](HISTORY.md#audit-de-la-quatorzième-session-du-5-novembre-2026--bitmaps-zones-sales-et-décimal-cmos).

The thirteenth-session gate passes **707 cases and 16 frame budgets**.
Tile restoration, DHGR span scratch and GFX arithmetic shrink **108 clients**
by 4..37 loaded bytes; 94 use less RAM and fourteen diagonals save one
C-stack byte. **84 timings improve**, 23 affected timings are unchanged,
and one monochrome circle rises by 28 cycles (+0.076%). The other **599
result dictionaries are identical**, with unchanged zero page and hardware
stack. A full tile page takes **268,169 instead of 271,192 cycles**; a
monochrome diagonal takes **296,767 instead of 300,683**. All 407 reference
updates tighten limits. Pixel, bank, IRQ and stack oracles pass, as do
library and game integration checks. See [the thirteenth-session audit](HISTORY.md#audit-de-la-treizième-session-du-5-novembre-2026--tuiles-remplissages-et-géométrie).

The twelfth-session gate passes **707 cases**, including ten text alignments
measured before optimization. Reusing existing cc65 scratch shrinks all
**20 affected clients**: twelve compact-text clients save **19 loaded bytes
and four RAM bytes**, eight standard-text clients save **six loaded bytes
and two RAM bytes**. **17 timings improve**, three are unchanged, with no
metric increase. The other **687 result dictionaries are identical**;
zero page and stacks are unchanged. Compact `"APPLE II"` takes **12,552
instead of 13,186 cycles**; standard text **31,648 instead of 32,080**.
All frame budgets pass and 77 reference fields are tightened without raising
limits. Character/bank/IRQ oracles and game integration tests pass, including
relocated fonts and IIe/IIc consumers. DHGR/ROBOTSTATION disks and WOZ twins
are rebuilt; all 18 pairs match. See [the twelfth-session audit](HISTORY.md#audit-de-la-douzième-session-du-5-novembre-2026--texte-dhgr).

The eleventh-session gate passes **697 cases**. Shared cc65 scratch reduces
zero page in **132 profiles**, code in **84**, and other RAM in **27**.
Text-only clients save four zero-page bytes and one code byte; pixel
rectangles save six zero-page bytes. The line kernel saves five code bytes
and one BSS byte; clients combining text and rectangles free ten zero-page
bytes. **64 timings improve**; the only increases are a point (+2 cycles,
0.311%) and a wide ellipse (+36 cycles, 0.022%). **565 result dictionaries
are identical**, and stack peaks stay unchanged. The HGR diagonal takes
**20,729 instead of 20,927 cycles**, the dense doubled glyph **2,641 instead
of 2,657**. All frame budgets pass; 388 reference fields are tightened.
Pixel oracles pass on both CPUs, including folded-table lines and cold
rectangle calls. HGR/SNAKE disks and WOZ twins are rebuilt, all 18 pairs
match, and integration tests pass. See [the eleventh-session audit](HISTORY.md#audit-de-la-onzième-session-du-5-novembre-2026--scratch-des-primitives-hgr).

The tenth-session gate passes **697 cases**. Reusing existing cc65 scratch
for numeric HUD kernels shrinks **55 clients**: 30 save **28 loaded bytes
and seven RAM bytes** (16×16), 25 save **six loaded bytes and three RAM
bytes** (8×8). **52 timings improve**; two are unchanged, and the VBL-paced
loop rises by three cycles out of about 34,000 (less than 0.01%). The other
**642 result dictionaries are identical**; zero page and stacks are unchanged.
A changed 16×16 digit takes **3,770 instead of 3,930 cycles**; an 8×8 digit
**2,255 instead of 2,282**. All frame budgets pass and 217 reference fields
are tightened without raising limits. Pixel/history oracles pass on both
CPUs, as do library and integration tests. HGR disk/WOZ are rebuilt, all
18 WOZ twins match, and the minimal example keeps its PAL/NTSC cadence over
1,000 frames. See [the tenth-session audit](HISTORY.md#audit-de-la-dixième-session-du-5-novembre-2026--compteurs-hgr).

The ninth-session gate passes **697 cases**, including eight damage-worker
workloads measured before optimization. Existing cc65 scratch replaces the
private geometry, index and flag storage in `HGR_SPR_DAMAGE`: **43 loaded
bytes and eleven RAM bytes saved in all ten affected clients**. All ten
timings improve; **687 dictionaries are unchanged**, with no regression or
extra zero page/stack use. The eight-sprite reverse chain takes **18,624
instead of 20,604 cycles**; integrated isolated damage takes **13,890 instead
of 14,092**. 40 reference fields are tightened without raising limits.
The 512-state graph oracle passes on both CPUs, as do integration checks.
Rebuilt disks remain identical and all 18 WOZ twins match. The option stays
off by default. See [the ninth-session audit](HISTORY.md#audit-de-la-neuvième-session-du-5-novembre-2026--propagation-des-dommages-hgr).

The eighth-session gate passes **689 cases**, including eight isolated move
calls measured before optimization. HGR engine scratch, direct movement
arguments and grouped save-under advances save **17 loaded bytes and four
RAM bytes in 48 clients**. **45 timings improve**; three increase by only
two to five cycles (less than 0.02%). All frame budgets pass. Valid moves
save 29 cycles, rejected IDs 44; the four-sprite stress frame falls from
**37,855 to 37,577 cycles**. The eight move clients use one fewer hardware-stack
byte; zero page and C stack are unchanged. 188 reference fields are tightened.
Both CPU oracles and engine integration pass. The HGR disk/WOZ are rebuilt,
HGR and LIGHT3DBALL tests pass, and all 18 disk/WOZ pairs match. See
[the eighth-session audit](HISTORY.md#audit-de-la-huitième-session-du-5-novembre-2026--moteur-de-sprites-hgr).

The seventh-session gate passes **681 cases**, including 15 workloads
measured before optimization. DHGR bitmap/overlay address accumulation
and the direct C PRNG shrink **25 clients** (15 by **3 loaded bytes**,
10 by **8**). **21 timings improve, none regress**; 656 result dictionaries
are unchanged. A 4×31-byte overlay takes **28,080 instead of 30,882 cycles**.
The C PRNG takes **45/46 instead of 55/64 cycles**, including a volatile
result store, and uses two fewer hardware-stack bytes. RAM and zero page
are unchanged. 77 reference fields are tightened without raising limits.
See [the seventh-session audit](HISTORY.md#audit-de-la-septième-session-du-5-novembre-2026--dhgr-et-générateur-aléatoire).

The sixth-session gate passes **666 cases**. Clipping against remaining
screen space and removing a redundant stride copy shrink **80 clients**:
61 by **16 loaded bytes**, 19 by **14**. RAM, zero page and stacks are
unchanged. A clipped preshifted XOR takes **678 instead of 695 cycles**;
the tall phase-zero masked case takes **389 instead of 399**. 47 timings
improve and 30 increase by less than 0.60%; all frame budgets pass.
204 reference fields are tightened without raising any prior limit.
Exhaustive setup and rendering checks pass on both CPUs, including separate
and folded tables for preshifted rendering. HGR/LIGHT3DBALL disks and their
WOZ twins are rebuilt and tested; all 18 disk/WOZ pairs match. See
[the sixth-session audit](HISTORY.md#audit-de-la-sixième-session-du-5-novembre-2026--découpage-des-sprites).

The fifth-session gate passes **666 cases**, including 15 new masked-sprite
workloads measured before and after. **61 clients shrink by 25 loaded bytes**;
RAM, zero page and stacks are unchanged. 141 reference fields are tightened.
The 33 timing increases stay below 0.36%, with prior limits preserved and
all frame budgets met. Exhaustive setup checks pass on both CPUs, as do
engine integration and the rebuilt HGR/LIGHT3DBALL disks; all 18 WOZ twins
match. See [the fifth-session audit](HISTORY.md#audit-de-la-cinquième-session-du-5-novembre-2026--sprites-masqués).

Keeping the masked-sprite product and hint in registers saves another
**5 code bytes**, for **25 loaded bytes across all three passes**. Generic
drawing takes **2,836 instead of 2,876 cycles**; a height-255 sprite clipped
to one row takes **399 instead of 5,251** in phase zero and **3,862 instead
of 5,384** in phase three. Four one-row phase-3/6 cases cost two extra cycles;
their prior references remain. RAM, zero page and stack usage are unchanged.

Phase-zero masked draws skip the unused height/stride product while still
consuming their one-call hint. This saves another **4 code bytes**. A tall
sprite clipped to the bottom row takes **402 instead of 5,251 cycles** in
phase zero. All setup dimensions, phases and hint values pass on both CPUs.

Masked-sprite row advancement shares its save-under tail, saving **16 loaded
bytes** without extra instructions, RAM or stack. The four generic drawing,
saving and restoration cases retain their cycle counts. A new setup oracle
covers all dimensions, phases, placements and one-call cache values
(1,827,868 calls with `--full`).

The fourth session measures three passes on text and tile restoration.
The expanded gate passes **651 cases**: **32 smaller clients**, 619 unchanged
measurements, and nine new cases measured before and after. 125 reference
fields are tightened; no existing limit or absolute budget is raised.
The text stack tradeoff and four cycle increases below 0.85% are recorded in
[the fourth-session audit](HISTORY.md#audit-de-la-quatrième-session-du-5-novembre-2026--texte-et-tuiles).
Rebuilt disks remain identical and all 18 WOZ twins match.

Two tile-restoration passes save **11 loaded bytes and 3 RAM bytes**.
A full page takes **271,192 instead of 278,943 cycles**; a single corner
tile **989 instead of 1,014**. The eight-tile background with two sprites
takes **6,623 instead of 6,703**. Seven new cases isolate restoration and
rejection costs; both CPUs pass the exact framebuffer and atomic-failure tests.

The text iterator now saves **44 loaded bytes** in string-only clients and
**18** in numeric clients, with **two fewer C-stack bytes**. Unsigned zero
takes **1,750 instead of 1,825 cycles**; empty strings **32 instead of 115**.
Rendered strings use two more hardware-stack bytes. A 128-character string
costs 0.84% more cycles, within its original reference. Nested callbacks,
scratch clobbers and all pointer alignments are checked on both CPUs.

The third session keeps **642 passing benchmark cases**: **119 clients shrink
by 2–9 bytes**, 523 measurements stay identical, with no extra RAM, zero page
or stack. 314 improved reference fields are tightened; all older limits and
absolute budgets are retained. Cycle increases remain below 0.8%.
Affected games/examples pass, five disks are rebuilt, and all 18 WOZ twins
are verified; see [the third-session audit](HISTORY.md#audit-de-la-troisième-session-du-5-novembre-2026--3-séries).

Math-table initialization saves **2 code bytes and 516 cycles** across
`mul_init`/`sqrt_init`: **61,206 instead of 61,722 cycles** including calls.
All table bytes, seeds and 65,536 roots pass at two table placements on
6502 and 65C02; the runtime square-root kernel and its timing stay unchanged.

Decimal conversion saves **2 loaded bytes** in unsigned clients and **4**
in signed clients, with no extra RAM or stack. GFX unsigned zero takes
**1,825 instead of 1,833 cycles**, signed −1 **3,008 instead of 3,024**.
All 131,072 signed/unsigned strings pass on both 6502 and 65C02.

LORES row-page switching now uses a fixed XOR mask, saving **7 loaded bytes**.
A page-2/page-1 round trip with LORES ready takes **5,487 instead of 5,615
cycles**. The HGR-only round trip costs 34 extra layout cycles (+0.73%);
its old limit is retained. All page arguments pass with cold/ready LORES
on 6502 and 65C02.

Three follow-up series after the morning audit keep **642 benchmark cases**:
**58 smaller binaries**, 584 entirely unchanged measurements, and all gates
passed. 169 improved reference fields are tightened; no limits are raised.
The small cycle and hardware-stack tradeoffs are recorded in
[the follow-up audit](HISTORY.md#audit-complémentaire-du-5-novembre-2026--3-séries).
Rebuilt disks remain identical and all 18 WOZ twins are verified.

The follow-up ellipse pass saves another **24 loaded bytes** and reduces
ordinary C-stack peaks **28 → 24**. A small ellipse takes **151,885 cycles**
(formerly 156,385); the widest box **167,148** (formerly 171,778).
The vertical degenerate case costs 92 more cycles (+0.72%); its old budget
is retained. Exact chord traces cover 126 boxes per CPU, and the signed
scaler passes all 4,227,072 legal pairs on both 6502 and 65C02.

Cursor control removes **two bytes each** from position and character members.
Clamping takes **99 instead of 103 cycles**; newline **43 instead of 45**.
All byte coordinates and controls pass on both CPUs, including empty grids.

The follow-up hexadecimal pass reduces the converter from **68 to 64 bytes**.
Zero takes **207 instead of 308 cycles**, and 65535 **306 instead of 326**.
Two- to four-digit isolated conversions use **two more hardware-stack bytes**;
RAM, zero page and C-stack use stay unchanged. All 65,536 values and the
numeric-text wrappers pass on 6502 and 65C02; details are in [HISTORY.md](HISTORY.md).

The 5 November morning session contains **13 optimization series and 642
benchmark cases**, reproduced exactly from a clean checkout. Original
reference limits and fixed frame budgets are retained. Full HGR/DHGR and
tool checks, rebuilt disks and 18 WOZ twins are covered by the
[session audit](HISTORY.md#audit-de-la-session-du-5-novembre-2026--13-séries).

Independent native ProDOS name validation saves **1,404 loaded bytes** and
**547 RAM bytes** in name-only clients, without directory or MLI imports.
`DEMO.AYS` takes **265 cycles instead of 980**; a valid 15-character name
takes **435 instead of 1,830**, with no C-stack use. MB Tracker keeps the
validator in its file overlay and saves **64 bytes there plus 2 BSS bytes**.

Native ellipse scaling saves **272 loaded bytes** per client and reduces
C-stack peaks from 33 to **28 bytes** for ordinary ellipses. A small ellipse
takes **156,385 cycles instead of 205,861**; a very wide box takes
**171,778 instead of 257,622**. All **4,227,072** legal radius/coefficient
pairs are checked, with signed truncation and no additional RAM or zero page.

Native midpoint circles save **263 loaded bytes** in HGR/color clients
and **241** in DHGR mono. A corner-clipped HGR circle takes **23,331 cycles
instead of 61,494**; radius 255 takes **87,406 instead of 401,954**. Interior
circles also improve. HGR C-stack peaks fall from 14/18 to **9 bytes** for
interior/clipped circles. The exact ordered oracle checks 13 million pixels.

Native generic Bresenham lines save **251 loaded bytes** per client. The
DHGR mono/color diagonals take **300,683/106,646 cycles**, down from
433,885/152,003; their C-stack peaks fall from 29/28 to **17/16 bytes**.
Exact ordered traces cover 3.6 million pixels, with exhaustive axis/rejection
coordinates and hostile backend scratch. HGR keeps its specialized line path.

Native generic outlines save **249 loaded bytes** in HGR clients and **244**
in either DHGR backend. A clipped HGR outline takes **2,207 cycles instead
of 2,573**; point/axis C-stack peaks fall from 9–10 to **6 bytes**. Exact
span order is checked across full coordinates, nine grids and hostile
backend scratch. Small DHGR layout costs retain their older cycle limits.

Independent native DHGR color adapters reduce a point-only client from
**3,052 to 1,781 loaded bytes** and **330 to 264 cycles**. Axis C-stack peaks
fall from **18–19 to 5 bytes**. Pen-only clients save **2,241 loaded bytes**;
clear-only clients save **2,050**. The DHGR demo and Robot Station explicitly
select these native sources, with object-export/build-preservation checks.

Independent native DHGR monochrome adapters reduce a point-only client
from **3,256 to 1,672 loaded bytes**, and the point from **432 to 322 cycles**.
A pen-only client saves **2,439 loaded bytes**. Generic diagonal/circle
workloads also improve: **496,434 → 433,885** and **47,424 → 37,419 cycles**.
The benchmark selects each explicit backend in its own archive, including
both monochrome and color cases in the DHGR gate.

The native inflate-and-blit entry saves another **36 loaded bytes** and
reduces valid/rejected C-stack peaks from 18/11 to **14/8 bytes**. An
oversized source is rejected in **152 cycles instead of 570**; drawing a
white 3×16 source now takes **13,698 cycles**. Its private 256-byte buffer
and all color/mode forwarding remain unchanged.

Native doubled-sprite conversion saves **391 loaded bytes** and reduces
C/hardware-stack peaks from 23/8 to **5/6 bytes**, with unchanged RAM and
zero page. Inflating a white 3×16 source takes **10,604 cycles instead of
52,824**; a 255×2 source takes **100,146 instead of 524,594**. The same
16-byte spreading table is retained, and all source/color byte pairs are checked.

Independent native GFX cursor/text members save **1,548 loaded bytes**,
**950 RAM bytes** and **12 zero-page bytes** for position-only clients.
Positioning takes **91/103 cycles** for valid/clamped coordinates, formerly
153/177. Numeric text clients save **99 bytes** and one C-stack byte;
unsigned 65535 takes **8,681 cycles instead of 9,247**, signed −32768
**10,292 instead of 10,880**. String iterators remain private across backend calls.

Native GFX filled rectangles save **256 loaded bytes** and reduce C-stack
use to **5 bytes**. A clipped rectangle takes **4,549 cycles instead of
4,944**, a rejected y range **139 instead of 327**. Independent `gfx_clear`
linking saves **709 loaded bytes**, **947 RAM bytes** and **14 zero-page
bytes** in the clear-only client, whose C-stack use falls to zero.

Native GFX HGR line dispatch saves **147 loaded bytes** and reduces the
C-stack peak from 9–11 to **5 bytes**, without extra RAM or zero page.
A clipped horizontal line takes **986 cycles instead of 1,115**, a rejected
diagonal **190 instead of 383**. The large diagonal's changed code placement
costs 0.64 % (21,310 → 21,447 cycles); its older cycle gate remains in force.

Independent GFX HGR aliases resolve points and axis spans directly to the
matching HGR entries, without copying C arguments or adding a call frame.
A point takes **249 cycles instead of 382**, saving **623 loaded bytes**,
14 zero-page bytes and three C-stack bytes in its isolated client.
Horizontal/vertical clients save **396/430 loaded bytes**; dimension-only
queries import no drawing primitives. The C backend remains a portable reference.

Native HGR row construction takes **6,921 cycles** instead of 45,783,
with no C-stack use. Independent row/query/display archive members save
**687 code bytes and 50 RAM bytes** in a point-only client. A display-only
client saves **800 code bytes and 435 RAM bytes**; `hgr_show_page()` takes
29/30 cycles. `hgr_row(191)` takes **52 cycles** instead of 236. Page
selection retains synchronous HGR/LORES table updates. The full HGR/DHGR
comparison and small layout-dependent slowdowns are recorded in
[HISTORY.md](HISTORY.md); `baseline.json` contains the regression references.

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

Native preshifted-sprite entries plus the faster phase product save
**142/119 loaded bytes** for XOR-only/general-only clients, or 87 when both
are used, compared with the earlier C entries and linear product. XOR
C-stack use falls **5 → 3 bytes**, its hardware-stack peak **10 → 8**;
the general entry's C stack falls 6 → 5. A 7×16 XOR at phases 0/3/6 takes
**1,986 / 2,107 / 2,187 cycles**, previously 2,080 / 2,468 / 2,546.

The stride × height product uses at most eight additions or binary steps. This speed
tradeoff adds **39 code bytes** compared with the native entries alone,
without extra RAM, zero page or stack. Setup of stride 3 / height 255 /
phase 6 falls from **5,196 to 402 cycles**; 255×255 falls from **6,210 to
530**. A one-row setup takes four extra cycles (228 → 232). The exhaustive
arithmetic fixture covers 910,350 combinations on II+ and IIe; the normal
suite samples 18 heights and checks all strides, phases and two placements.

The native `hgr_blit7` entry saves **92 loaded bytes** in isolated clients
and reduces C-stack use from **9 to 7 bytes**. A 4-byte × 8-row SET sprite
takes **1,525 cycles** instead of 1,646; a clipped one-byte XOR takes
**434 instead of 578**, including C argument setup. Rejected calls still
initialize the row/column tables. Full source strides survive clipping,
without additional RAM, zero page or hardware stack.

Independent HGR column/mask/phase builders fill groups of seven pixels,
saving **54 code bytes** in total. Cold calls take **4,040 / 4,520 / 4,440
cycles** instead of 7,029 / 8,434 / 6,749 (four extra cycles at some table
alignments). The cold pixel rectangle falls from **23,104 to 16,199 cycles**.
RAM, zero page, stack peaks and warm guards stay unchanged. The optional
folded builder now takes **74 bytes / 10,327–10,350 cycles**, down from
77 / 15,084, by removing per-pixel calls and copying the 24-byte tail.
It saves 56 code bytes and cold initialization time when all three tables
are needed, while still reserving all 841 B of table state. The cold folded
HUD/scene calls take **45,531 / 27,015 cycles** (previously 51,853 / 32,491).
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
takes **13,186 cycles**, with a 2,864-byte binary and 326 bytes of RAM.
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

The block transfer controller now uses the caller's six argument bytes
throughout. After validation, the width slot stores stride and the byte-x
slot stores a column plus the read/write flag. Each row loads its address
directly from the immutable row tables, with no extra local frame or
per-row argument push. Read and write have separate native archive entries;
a block-only client does not import the byte-address C-ABI helper.
Isolated clients save **323 loaded bytes**, C-stack peak **18 → 6**
(rejections **16 → 6**), hardware peak **11 → 9**; empty/rejected calls fall
to **4 hardware-stack bytes**. RAM and zero page are unchanged.
Reading/writing 8×8 bytes takes **5,664 / 5,328 instead of 6,990 / 6,678
cycles**. Single-byte calls take **500 / 487 instead of 1,132 / 1,115**;
192-row strips **52,440 / 53,592 instead of 71,731 / 72,115**.
`test_dhgr_transfer_entry.py` verifies **526,336 calls per CPU**, including
all bx/width, width/stride and y/height pairs, all pointers, every row's
address/bank/count/buffer, rejection and zero-height side effects, hostile
scratch registers and 2,048 stack placements. The C reference passes the
same fixture. Eighteen new cases bring the benchmark to **418 cases**:
21 improve and 397 remain identical.

The sprite controller is native too. It validates the full color-pixel
extent against stride before right clipping, computes the bank from the
original height, then clips the visible rows. An eight-step product gives
`height * stride`; phase zero skips it. The total phase offset is formed
once and added once to each pointer. Row addresses and pointer advances use
only the nine argument bytes, including the fastcall mask saved on entry.
Isolated clients save **320 loaded bytes** (226 in the partial/opaque
fixtures that already link other runtime helpers), C-stack peak **18 → 9**
(rejections **16 → 9**), with unchanged RAM, zero page and hardware peaks.
The small sprite takes **1,205 instead of 2,272 cycles**; partial/opaque
14×8 sprites **10,442 / 8,331 instead of 12,210 / 10,105**. Phase-0/6
8-row cases fall **5,839 / 6,525 → 4,062 / 4,435**, and a height-255 sprite
clipped to one row **1,999 → 987**.
`test_dhgr_sprite_entry.py` checks **787,456 calls per CPU**: all x/width,
width/stride and y/height pairs, all data/mask pointers, every height/stride
product at all seven phases, every row address/bank/count/pointer, rejected
state, scratch clobbers, guards and 1,024 stack placements. The original C
passes the same fixture. Fourteen new cases bring the benchmark to **432**;
17 improve and 415 remain identical.

DHGR point address/mask calculation is a separate archive member shared
by plotting and readback. A read-only client no longer links the writer.
The wrappers pass coordinates through existing scratch and release their
arguments directly; readback preserves A/X while incrementing the stack
pointer twice. Isolated readers save **99 loaded bytes**, writers **8**,
with unchanged RAM, zero page and measured stack peaks. Auxiliary/main-bank
reads take **279 / 259 instead of 285 / 265 cycles**; writes of a set bit
**305 / 277 instead of 318 / 293**. Offscreen reads/writes improve too.
The shared locator body is unchanged. `test_dhgr_points.py` checks
**694,336 calls on each IIe/IIc**: every pixel on both pages, all selector
bytes, every invalid 16-bit x and y byte, bank/IRQ restoration, video holes,
byte return values and 2,048 stack placements. It passes before and after
the change. Twenty-one new cases bring the benchmark to **453**; all improve
and the previous 432 remain identical.

The GFX unsigned/signed/hexadecimal text entries use native cc65 wrappers;
the matching C files remain portable references. The value is saved on the
hardware stack only while reserving and passing the 6/7/5-byte local buffer,
then restored before conversion. No persistent buffer or new state is used.
Measured clients save **6 / 3 / 6 loaded bytes** and **two C-stack bytes**,
with unchanged RAM, zero page and hardware-stack peaks. Printing unsigned
zero takes **2,056 instead of 2,129 cycles**, signed −32768 **11,601 instead
of 11,630**, and hex FFFF **7,087 instead of 7,185**. All 17 new cases improve;
the previous 453 remain identical, for **470 cases** in total.
`test_gfx_number_entries.py` checks **199,680 calls per CPU**: every 16-bit
value in all three formats, NUL termination, caller guards, arbitrary text
scratch clobbers and 3,072 stack placements. The C entries pass the same
fixture; the integration fixture renders all formats with the real backend.

The HGR cell backend now has separate native members for dimensions,
glyph forwarding and the color no-op; the single C backend remains a
portable reference. Glyph forwarding reuses the two caller argument bytes
for its character/NUL buffer, reserving only three extra bytes for pixel
coordinates. Full 16-bit `column * 8` and wrapped byte `row * 8` preserve
the C behavior even outside the normal grid. Isolated glyph clients save
**43 loaded bytes**, numeric clients **25**, with **three fewer C-stack
bytes** and unchanged RAM, zero page and hardware peaks. An origin glyph
takes **1,195 instead of 1,301 cycles**; signed −32768 **10,880 instead of
11,601**, hex FFFF **6,635 instead of 7,087**.
The color-only benchmark no longer imports the renderer: **1,874 → 519
loaded bytes**, **1,247 → 297 RAM bytes**, **38 → 26 zero-page bytes**,
**63 → 14 cycles**, C-stack **1 → 0**, hardware peak **6 → 4**.
`test_gfx_glyph_entry.py` checks **197,632 calls per CPU**, all col/row,
char/col and char/row pairs, exact coordinates and two-byte strings,
color no-ops, scratch clobbers, guards and 1,024 stack placements; the C
reference passes too. Minimal clients independently exclude glyph code
from dimensions-only and color-only links. Nine new cases bring the
benchmark to **479**: 26 improve and 453 remain identical.

The common DHGR rectangle preparation now validates and clips directly
from its five argument bytes, using the carry out of `x+width` to saturate
large widths safely. It releases the arguments before tail-calling the
span kernel. Isolated helper clients save **142 loaded bytes**, C-stack
peak **9 → 5**, with unchanged RAM and zero page. Small/last-pixel cases
fall **1,291 / 988 → 1,023 / 671 cycles**; rejected/empty calls also improve.
The public colour rectangle, including its native entry, saves **312 bytes**,
**12,267 → 11,809 cycles**;
with native monochrome forwarding and axis preparation, the line saves
**466 bytes**, **2,796 → 2,208 cycles**. The helper’s
hardware-stack peaks fall by one or two bytes. Nine new helper cases run
after `dhgr_init`, including full-width, 16-bit wrap, clipping and rejections.

The monochrome `dhgr_fill_bits` entry prepares its four identical pattern
bytes, consumes height and tail-calls the rectangle helper using the five
argument bytes already in place. It saves **63 loaded bytes**, C-stack
peak **12 → 6**, hardware peak **9 → 7** (rejections **7 → 5**), with
unchanged RAM and zero page. Small set/clear calls fall **1,244 / 1,245 →
1,071 / 1,072 cycles**, the last pixel **890 → 721**, a rejected origin
**361 → 190**. The line client saves another 50 bytes, **2,514 → 2,340
cycles**, C-stack peak **20 → 14**. All nine affected cases improve;
eight new direct cases include zero/255 selectors and rejected geometry.

The colour `dhgr_fill_rect` entry clips width before multiplying it by
four, prepares the pattern and expands four argument bytes into five.
Height stays in X; one scratch byte holds the low halves of the two shifts.
It saves **75 loaded bytes**, C-stack peak **12 → 5** (invalid x **7 → 4**),
hardware peak **9 → 7**, with unchanged RAM and zero page. Small/last-pixel
cases fall **1,355 / 1,124 → 1,143 / 898 cycles**, the 16-row rectangle
**12,016 → 11,790**. All eleven affected cases improve; ten new cases cover
byte boundaries, clipping, all-bits-set colours and empty/offscreen calls.

Separate native `dhgr_hline`/`dhgr_vline` entries sort and clip endpoints,
then expand their arguments into one six-byte fill frame. Isolated clients
save **188 / 248 loaded bytes**, C-stack peaks **14 / 12 → 6**, hardware
peaks **9 → 7** (rejections **7 → 5**), with unchanged RAM and zero page.
Forward/reversed short horizontal lines fall **1,323 / 1,478 → 1,191 /
1,213 cycles**; vertical lines **3,123 / 3,164 → 2,983 / 2,992**. The full
horizontal line falls **2,340 → 2,226**. All eleven affected cases improve;
ten new direct axis cases cover reversal, clipping and offscreen calls.

DHGR state and its four page functions occupy independent archive members.
Draw-page selection takes **25 / 31 cycles** for pages 1 / 2 and **23** for
an invalid selector (previously 93 / 95 / 78), without C-stack use.
Flip retains the old displayed page in Y across two internal calls that
preserve Y, then tail-calls selection: **211 → 88 cycles**, C-stack peak
**2 → 0**, hardware peak **8 → 6**. The two queries retain their original
24 / 25 / 18-cycle paths. Isolated page clients save **63–105 loaded bytes**;
other measured DHGR clients save **41–111**. Clearing rows before mode
initialization saves **409 loaded bytes and 9 zero-page bytes** because it
no longer imports the mode manager. RAM is unchanged. Code placement shifts
some rendering timings: block writing rises **6,615 → 6,678 cycles** and
the colour rectangle **11,790 → 11,809**; the old cycle references remain
in the regression gate. `test_dhgr_pages.py` checks 131,328 state combinations
on both CPU models, initial state, invalid selectors, flip ordering and the
real show/query register contracts. Minimal clients exclude unused page
functions. The full benchmark has **392 cases**, with 78 changed and 314
identical in this pass.

The full-clear and compact-text C entries are now native. `dhgr_clear`
forwards color to pattern preparation and tail-calls clearing without a
local slot: **39 loaded bytes saved**, **112,456 → 112,391 cycles**, C-stack
peak **1 → 0**, hardware peak **11 → 9**. `dhgr_puts_small` stores the two
coordinates, loads the pointer, releases its three argument bytes directly
and tail-calls the string kernel. Its isolated client saves **37 loaded
bytes**; "APPLE II" takes **13,186 instead of 13,220 cycles**, an empty
string **159 instead of 216**, and the last cell **1,499 instead of 1,555**.
C-stack peak falls **4 → 3**; hardware peaks fall by two bytes, including
empty/rejected calls **6 → 4**. RAM and zero page are unchanged.
`test_dhgr_thin_entries.py` checks **132,352 calls per CPU**: all pointers,
x/y pairs and colors, call ordering, callee coordinate changes, scratch
clobbers, guards and 1,024 stack placements. The original C passes the same
fixture. Eight new cases bring the benchmark to **400 cases**; ten change
and 390 remain identical.

Bounded DHGR clearing (`dhgr_clear_rows`) uses a register counter for the
four turns of each pattern pass and passes the row's high address byte in
A. The native row kernel takes **688 cycles** instead of 712, with **12
fewer code bytes** in that kernel change. The public entry now validates
and clips the two argument slots, prepares the pattern and releases the
slots before tail-calling the kernel. This saves another **94 loaded bytes**,
C-stack peak **5 → 2**, hardware peak **11 → 9**, with unchanged RAM and
zero page. Including C arguments, one line takes **929 instead of 1,090
cycles** (−14.8%), 16 lines **11,549 instead of 11,725**, all 192 visible
lines **136,214 instead of 136,555**. Empty/rejected calls fall **145/136 →
103/114 cycles**. Each line still restores main RAMWRT and the caller's IRQ
mask, allowing IRQ servicing between rows. The nine cases include clipping,
empty/offscreen calls and color bytes above 15; all improve.

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
`"APPLE II"` takes 14,720 cycles and orange text 14,839 with the native
entries. The earlier doubled-kernel optimization saved **30 code bytes
and 5 zero-page bytes**, without changing other RAM, tables or stack peaks.
Eight spaces take 3,545 cycles; a fully filled native
16×16 glyph at phase six takes 2,641 instead of 2,873 (−8.1 %).

The doubled-text entries prepare the cc65 arguments directly and compute
the cell count with bounded subtractions, specializing x=0..8 and x=256..264.
They save **201 white / 214 color loaded bytes**, reduce C-stack peaks
**10 → 3 / 11 → 5**, and reduce the rendered calls' hardware-stack peak
**10 → 8**. The empty white call falls **627 → 278 cycles** (hardware stack
9 → 6); an unknown-color fallback falls **15,530 → 15,084 cycles** and
C stack 16 → 5. RAM and zero page are unchanged. The previous standalone
count helper remains available but is no longer needed by these entries.
Both wrappers retain table initialization on rejected coordinates and
all color values outside 1..4 fall back to white. The entry test sweeps
all x/y/color values with a kernel sink; separate pixel oracles cover
rendering, carriers, clipping, pages and screen holes.

The hexadecimal converter extracts each nibble directly and switches source
bytes once, reducing its code **71 → 68 bytes**. Direct C calls take
**308 / 312 / 323 / 334 / 326 cycles** for 0 / 16 / 256 / 4096 / 65535,
previously 398 / 404 / 417 / 430 / 422 (about **22–23 % less**).
RAM, zero page and both stack peaks stay unchanged. The exhaustive
65,536-value fixture checks strings, lengths, NULs and guards on II+/IIe,
including buffers that cross a page. With the native HGR entry, hexadecimal rendering of 65535 takes **8,682 cycles**.

The native HGR hexadecimal entry reserves its conversion argument, x/y and
five-byte buffer together, avoiding separate push/allocation helpers. It
keeps the value in tmp3/X and reuses the converter's destination pointer.
Clients save **38 loaded bytes**, C-stack peak **13 → 10**, with unchanged
RAM, zero page and hardware-stack peaks. FFFF takes **8,682 instead of
8,826 cycles**, zero **2,647 instead of 2,781**, and clipping **2,819 instead
of 2,954**. Rejected calls fall **716 → 582**; cold calls **24,147 → 24,013**.

Unsigned HGR number entries share one preparation routine, with separate
archive members for the two fonts. Their six-byte buffer stays on the
software stack, reusing the old argument slots after moving x/y to the new
top. Isolated clients save **41 loaded bytes**, C-stack peak **14 → 9**,
with unchanged RAM, zero page and hardware-stack peaks. Doubled/native-size
65535 calls take **11,319 / 6,226 cycles** (previously 11,429 / 6,318), zero
**2,621 / 1,423** (2,715 / 1,522), and rejected origins **1,248 / 1,235**
(1,340 / 1,327). The conversion and rendering kernels are unchanged.

Signed HGR numbers use a native seven-byte local buffer, relocating the
coordinates to its front and preserving the buffer start in the existing
text-source pointer. Only the conversion pointer advances past a minus sign;
unsigned negation includes −32768. This saves **74 loaded bytes**, C-stack
peak **15 → 10**, with unchanged RAM, zero page and hardware-stack peaks.
Printing −32768/−12345/32767 takes **12,325 / 11,844 / 11,358 cycles**
(12,469 / 11,987 / 11,445 before); zero falls **2,728 → 2,622**, −1
**3,583 → 3,432**, and a rejected origin **1,408 → 1,250**.

Decimal entries reserve their local frame directly after saving the value
and release it through `addysp`. This follow-up saves another eight bytes
per isolated client and 11–31 cycles on measured warm calls, without
changing stack peaks. The doubled-font unsigned cold call rises from
26,664 to 26,697 cycles (+0.12%); its existing cycle reference is retained.

The native unsigned-field entry reuses the consumed value slots for width
and digit count, keeps a six-byte local buffer and prepares erase/text
arguments directly. It saves **157 loaded bytes** in isolated clients,
C-stack peak **17 → 15**, with unchanged RAM and zero page. Rejections need
only **5 C-stack bytes instead of 13**, and 5 hardware bytes instead of 6.
The padded/overflow/clipped calls take **12,654 / 13,439 / 3,276 cycles**
(13,022 / 13,660 / 3,639 before). The legacy HUD saves **144 loaded bytes**:
cold **49,102 → 48,164**, warm **29,029 → 28,372 cycles**. The legacy scene
saves 79 bytes, cold **30,048 → 29,633**, warm **11,783 → 11,380**.

Native-size 8×8 `"APPLE II"` now takes **7,751 / 8,498 / 8,389 cycles** at
phases 0/3/6, previously 7,886 / 8,672 / 8,563. Its native argument entry
saves **74 loaded bytes** in isolated clients and reduces the C-stack peak
from **5 to 3 bytes**. The fitting count is `(281-x)>>3` after rejecting
x>273 or y>184. Empty calls take **287 instead of 461 cycles**, and a final
screen-edge glyph takes **1,090 instead of 1,246**. RAM and zero page stay
unchanged; empty/rejected hardware-stack peaks fall 7 → 6.

The earlier glyph-kernel pass saved 11 code bytes by counting rows in X
and removing an unnecessary upper-byte mask. The shared `glyph_addr`
helper contributes three of those bytes: splitting the offset into
high/low parts takes 54 cycles instead of 61, including JSR/RTS, while
preserving X/Y. The glyph kernel and this helper are unchanged by the
native-entry conversion.

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

The native line and separate axis entries together save **238 loaded bytes**
in isolated HGR line clients (**162** through GFX), compared with the C
entries before these two passes. Short lines take **709 instead of 811 cycles**,
reversed horizontal **1,083 instead of 1,445**, and forward/reverse diagonals
**20,927 / 20,835 instead of 21,009 / 21,005**. The long vertical through
`hgr_line` takes **11,738 instead of 11,618 (+1.03 %)**. Individual passes
also change layout-sensitive timings; the full before/after tables and
retained cycle references are recorded in [HISTORY.md](HISTORY.md).

Standalone horizontal/vertical clients save **235 / 269 loaded bytes** by
using the separate native entries. Reversed spans use **4 / 3 C-stack bytes**
instead of 7 / 5; RAM, zero page and rendering hardware-stack peaks stay
unchanged. A full-width horizontal takes **893 instead of 984 cycles**,
reversed **918 instead of 1,175**, clipped **912 instead of 1,181**.
The full-height vertical takes **11,302 instead of 11,401**, reversed
**11,311 instead of 11,485**, clipped **11,312 instead of 11,492**. Point
spans take **479 / 441 cycles** (549 / 525). Every direct axis case improves.

Packed MSB-first bitmap blits (`hgr_blit`, 16×8 pixels) now take
**5,686–6,071 cycles** across SET/CLEAR/XOR and phases 0/3/6. The native
argument/clipping entry saves **193 loaded bytes** in isolated clients
and reduces C-stack use from **10 to 7 bytes**, with unchanged RAM, zero
page and hardware stack. It keeps the original source stride using
`((width-1)>>3)+1` after rejecting zero width. The bottom/right-clipped
XOR takes **930 instead of 1,206 cycles**; empty/solid bitmaps take
**4,671/6,343**, previously 4,925/6,597.

The earlier kernel changes used a sentinel bit in the source shift
register and `ptr2`'s high byte as the source index, saving six code bytes
and one zero-page byte. Sharing mode stores and stopping before a final
refill had already saved eight code bytes. These kernels are unchanged
by the native-entry conversion.

Byte rectangles traverse each row backwards, using Y as both the offset
and loop counter. Pairs take 19 instead of 21 cycles and an odd width
enters at the second store. The kernel saves **7 code bytes**, with
unchanged RAM, zero page and stack peaks. A 40×16-byte fill takes
**7,097 cycles** instead of 7,824; a 39×16 fill takes 6,985
instead of 7,568 (−6.5 %). The single-byte and clipped cases take 406/514
cycles. The new cases include fill values with the palette bit set.

The two HUD initializers now share a native bounds/store routine, with
separate font-specific entries. Their isolated clients save **287 / 160
loaded bytes**, valid calls fall **870 / 563 → 301 / 290 cycles**, C-stack
peaks **10 / 8 → 5**, and hardware peaks **8 / 7 → 5**. RAM and zero page
stay unchanged. The entries reject NULL and invalid width/y before checking
the 16-bit horizontal extent; only the five common state bytes are written.
Eighteen isolated cases cover valid/edge/single-cell and rejected calls.
HUD update clients save **239 / 134 bytes**; the compact game saves 66.
Some composed workloads cost up to 0.54% more cycles through code placement;
their earlier cycle references are retained. No rendering kernel changed.

Native tile-map initialization validates three 256-byte blocks and a
192-byte tail with `count-1` held in A; 256 tiles require no scan. It writes
the six-byte borrowed context only after all checks succeed. A full scan
falls **129,734 → 13,145 cycles** (−89.9%), the 256-ID shortcut **478 → 317**,
and the isolated client saves **127 loaded bytes**. C-stack peak falls
**10 → 6**, hardware peak **7 → 5**, with unchanged RAM and zero page.
Ten isolated cases cover full scans, first/last invalid IDs, counts and NULL.
The background scene saves 101 bytes; its rendering costs **6,692 → 6,701
cycles** (+0.13%) after code placement changes, with the old reference kept.

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
| 16×16 HUD, one digit changed | 3,940 |
| 16×16 HUD, five digits changed, maximum over seven phases | 15,888 |
| 8×8 HUD, value unchanged | 312 |
| 8×8 HUD, one digit changed | 2,282 |
| 8×8 HUD, five digits changed, maximum over seven phases | 6,652 |
| Compact game: two moving 7×8 sprites, three digits all changed, keyboard, positions, presentation | 15,100..15,367 |
| Four isolated 21×16 sprites, only the first one moving, default engine | 30,305 |
| Same scene, option `HGR_SPR_DAMAGE=1` | 14,100 |
| Stress: four 21×16 sprites all moving + counter + presentation | 37,914 |

The compact game is measured at all seven alignments, in NTSC and PAL. The
limits after the reservation are **28,060/34,560 cycles**; its worst phase
still leaves 12,693/19,193 cycles beyond the reservation. Positions and values
use a period of three so that each page finds a modified state again. The HUD
value does not just alternate with the page: its three digits really change
in the measured case. The modulo shared by the movements and the score is
computed once per frame.

The isolated scene saves 53.5 % with the assembly computation of the
intersections: 437 loaded bytes and 43 extra BSS bytes at eight slots. The
option stays disabled by default. Four large sprites all moving still cost
37,914 cycles: they exceed two NTSC periods and the PAL limit after the
reservation. The overloaded stress cases remain diagnostics.

The native counter uses the cached digits for +1/+2; the 9999 → 10000
transition costs 6,112 cycles in the 8×8 HUD. Its pre-shifted digits take
1,386 bytes of RODATA, shared between fields. A HUD-only client avoids the
mutable row/column LUTs and the general font; a client that also displays
text pays for both banks. The compact game uses 6,584 loaded bytes,
1,618 bytes of RAM and 47 zero-page bytes. Both HUD controllers reuse the conversion's digit
count and finish the origin division in eight bits: 24 fewer code bytes
per format, with unchanged tables, RAM and zero page.

The compact HUD kernel now counts source offsets in X, saving 18 code
bytes and two BSS counters. Separating glyph arguments, string state and
the font-address helper into archive members removes another 26 code
bytes and seven zero-page bytes from HUD8-only clients. Their measured
binary is 3,283 bytes, with 345 RAM bytes and 35 zero-page bytes. Changing
five digits is about 11 % faster; the unchanged-value path stays at 312
cycles. This archive split alone saves five zero-page bytes in HUD16-only
clients without changing their timing.

The 16×16 HUD kernel writes its fully covered second column directly,
assembles the upper pixels with two rotations and expands its three
single-use edge writers in place. It saves **42 code bytes and one BSS
byte**, with unchanged zero page and measured stack peaks. Five changed
digits take 15,032..15,888 cycles (about 17 % less); one changed digit
takes 3,940 instead of 4,495. The unchanged-value path remains at 312.
The isolated client uses 2,805 loaded bytes and 755 RAM bytes. The VBL-paced
loop currently measures 34,044 cycles including its wait. The per-series
tradeoffs are recorded in [HISTORY.md](HISTORY.md).

The optional tilemap backend restores eight 7×8 tiles then draws two masked
sprites without save-under in 5,802 cycles. The map is 960 bytes, supplied by
the application; a full rebuild is not presented as a 30 FPS workload. The
region profiles keep the 6,000-cycle reservation.

Masked HGR sprite kernels share two cc65 scratch bytes for the phase-block
product, omit a row-address carry that cannot occur and count generic
columns backwards in Y. They save **8 code bytes and two zero-page bytes**,
with unchanged RAM and stack peaks. On a 7-byte × 8-row sprite, generic
draw/save/restore/save-and-draw take 2,885/1,791/1,802/3,232 cycles, saving
4.9..8.2 %. The compact game saves 62..70 cycles per frame. The historical
stationary scene with legacy number fields gained 14 cycles (+0.11 %)
during this kernel pass; the subsequent entry/kernel passes now bring it
to 11,380 cycles. Other affected scenes improved or kept their timing.

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
