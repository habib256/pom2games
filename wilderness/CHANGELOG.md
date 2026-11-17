# Wilderness — history

The steps below describe the work present in the working tree.
They do not correspond to released versions. Upcoming tasks are
tracked in [TODO.md](TODO.md) and the limits of the port in
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Unreleased

### Text and HGR transitions

- The HELLO explanation text stays on screen during decompression,
  initialisation and the first render. DOS can no longer scroll
  the twenty welcome lines; the blank curtain starts after this first view.

- Startup, VIEW, full scene changes and the return from TOPO
  hide the drawing until the last column; partial rotations
  keep their progressive scrolling.
- Before a SIM or TOPO load, the top twenty lines are cleared
  before the switch to text. The old STATUS/HELP pages no longer reappear
  during the computations; the command, the results and the cursor stay.
- STATUS, the medical detail, INVENTORY, HELP and the final summary prepare
  their first page behind the landscape. The keyboard reveals the finished
  page.
- The menus share MAP's differential writes, with clearing of
  line ends, tab spaces and unused lines. An identical
  page writes no character; a short page keeps no old object.
- Returning from the menus clears the four text lines before showing HGR.
  The restore after simulation shares the day/night/cabin rendering and
  preserves the action results, without extra confirmation or delay.
- Video initialisation and the projection cache are moved into ADV;
  unused data and screen return are removed to fit in 48 KB.
- `test_transitions.py` checks the captures of the intermediate steps,
  the preservation of the state and the exact writes of the menus. The test
  breakpoints now wait for the keyboard after the page is prepared.
- The SLEEP disk contract is corrected to fourteen reads, also measured
  on the local reference before these changes; the transitions add none.

- SWIM loads SIM before its first bank probe, including without a move;
  starting or repeating SWIM on dry land no longer jumps into HGR memory.
- The route, wildlife and weight fixtures use the native raster,
  random generator and loads already present.

### First minutes and built-in help

- The welcome screen suggests INVENTORY, STATUS, TOPO and HELP to reach the
  rangers.
- HELP splits movement, equipment and survival into three pages: command
  examples, locations and a warning about DROP of the provisions.
- 1/2/3 selection, circular N/Space/B navigation and Esc/Return to go back,
  in the 2 KB screen module without changing the simulation rules.


### Visibility at full moon

- Nights when the lunar disc is fully lit keep a black
  sky, with relief, trees, wreck, cabin and animals visible. The other
  phases keep the darkness. The survival computations keep the night.
- Regression independent of the terrain and sprite pixels, under a clear or
  cloudy sky; the woods stay visible at full moon.

### Site direction consistent with TOPO

- Distant projection of the cabin and the wreck: north/south axis corrected
  to follow the terrain, the walk and the TOPO map landmarks.
- Regression independent of the projection model: eight directions per
  site, TOPO landmarks read on screen, compass, pixels visible in front
  and no sprite when looking behind.


### Animal reactions inspired by the original engine

- Sierra noise, injury and combat thresholds checked on ROM: noise has no
  effect on the rattlesnake, bear/cougar sensitive to noise, axe/knife grouped
  as in the native weapon choice.
- Bear/cougar severity checked on ROM: cuts, broken arm/leg and shock,
  linked to the health curves and treatments; higher outcome grouped as shock.
- Contamination draw corrected: the state changes on each consumption
  of untreated water, without using the animal random generator.
- SCARE and ATTACK can fail; two combat draws allow a
  successful defence with an injury. IGNORE can leave the animal present.
- Bear/cougar can steal exposed food: hung stocks, water,
  equipment and distant piles kept; load and totals recalculated.
- Injury risks by posture checked on ROM: waiting/resting/eating
  on the ground, IGNORE and tree. Climbing no longer prevents injuries; warning
  shown, hung provisions kept and treatment possible in the tree.
- Cabin protects the player/provisions;
  reaction reported and action interrupted after an hour without a decision.
- Probes `re_animal_reactions_probe.py`, keyboard scenarios
  `test_animal_reactions.py`; adaptations and limits in `docs/logic/animals.md`.

### Adventure, resupply and summary

- `DONE` and remaining distance replace the ambiguous `GOAL` in STATUS;
  distances with cell fractions, bounded progress and native score kept.
- `FILL/REFILL CANTEEN`, neighbouring bank, 64 OZ capacity, 10-minute cost
  and atomic overload refusal; contamination of drunk water and separate
  random generator.
- SCARE/IGNORE/ATTACK reactions, targeting by species, tools, cuts/bites
  and attack after an hour without a reaction; hung provisions and
  protection by the cabin.
  These reactions and the contamination are documented rules of the port.
- Banner for a low water reserve and a reaction to an encounter; HELP
  expanded.
- Dedicated arrival/death screen: duration, steps, encounters, health,
  provisions and native efficiency score, kept until a key is pressed.
- Two extra disk modules, WILDADV and WILDOUT; the simulation and
  existing commands stay in their windows and the startup in two packets.
- Purple/green palette confirmed as the engine's choice, sprite colours
  and terrain rendering kept.


### Fewer module transfers

- Simulation and wreck/bear/cabin sprites compressed, resident in-place LZ
  decompression: 32→22, 8→6, 4→2 and 5→3 data sectors read.
- Allocations kept, BLOAD lengths reduced: placement of the following
  files preserved. Small modules kept raw after measuring the native cost.
- Projection tables reduced to one stored table and a cache rebuilt
  at startup; 24,976 resident bytes, 16,303-byte packet in two files.
- LOOK R at 7.26 s; rest/sleep almost unchanged at 21.11/22.70 s,
  walk at 26.96 s. Decompression absorbs almost all of the disk gain.
- 20 native loads checked byte by byte, with text, zero page/FAC
  and memory bounds kept; states and images of six commands identical.
- Direct 1–255 H/MIN durations of REST/SLEEP/WALK/SWIM validated in
  resident code; full reader kept for keyboard input, other forms and
  errors.
- One WILDINP read avoided: REST 1 H at 21.12 s, SLEEP 8 H at 22.71 s,
  WALK 1 H at 26.95 s; states and images identical.
- Two redundant graphics tables removed (280 bytes) to make room for the
  resident input; extra rendering cost of 0.004 s.
- Compression dictionary shared between neighbouring regions: startup
  kept in two files (16,369 bytes); resident reduced by eight bytes.
- 799 native durations and the 140 pixel pairs checked; zero, errors,
  cancellation, general input, DOS memory and full restore kept.

### Audit of costs and native copies

- Loader LZ copies indexed by Y; pointers and counters updated
  once per sequence. Engine ready at 19.42 s; first prompt at 40.91 s.
- Immediate zero-slope division; removal of the double clear and
  of the second banner during the outdoor night restore.
- VIEW at 5.62 s; night DRINK gains 0.14 s. Resident: 25,261 bytes,
  compressed to 16,276 bytes in two files; four net bytes added.
- Profiling of commands by memory area: DOS still absorbs 68 % of
  sleep and 77 % of walking. States and pixels compared with no difference.
- 8,256 divisions and 40 copies tested natively, as well as the single
  night clear; page crossings and overlaps covered.

### Disk II loading

- LZ compression optimised per block taking the flags into account,
  full 4,095-byte window and removal of the arbitrary output cuts
  at 4 KB. Decompressor and Apple II memory identical.
- Startup packed into 16,272 bytes in two files instead of three;
  nine-sector interleave with a one-sector physical skew between tracks.
- Arrival in the engine: 23.48 → 20.83 seconds; first prompt:
  45.89 → 43.26. LOOK R: 8.08 → 7.36; eight-hour sleep: 25.83 → 25.30.
- Disk II measurements corrected to stop the capture before the first BLOAD.
  1,023 compression cases compared with an exhaustive search; format and
  window limits, DOS integrity and native restore checked.

### Render memory traversal

- Tree search stopped for the rest of the ray after its distance
  limit or the selection of a crown; reactivated on the next ray.
- Clearing by contiguous lines, with HGR addresses computed once
  per line; banner, cache, memory holes and kept columns protected.
- 32 bytes of redundant pointers removed, without a new index computation
  in the unrolled fill; total resident reduced by 14 bytes.
- VIEW: 6.20 → 5.64 seconds, LOOK R: 8.28 → 8.08, eight-hour sleep:
  26.39 → 25.83. States and pixels identical, DOS reads unchanged.
- Regressions on every byte of an HGR page, partial/full clears,
  tree search budget and reactivation between images.

### Speed and lifetime of data in memory

- 170 bytes of an off-screen rendering table recovered for resident LOOK
  and the screen shortcuts, with the pixels kept. VIEW no longer reloads
  the vocabulary and the sprite: 12.47 → 6.20 seconds. LOOK R goes
  from 10.43 to 8.28; STATUS at the start from 12.27 to 3.76.
- Astronomical temporaries reusing 68 bytes of the DOS buffer outside
  loads; sky outputs always resident. Five-byte insulation
  cache, invalidated by the clothes worn or the wetness mode.
- Reproducible measurements in cycles and reads with profile_actions.py,
  comparison of states and pixels before/after, 76 thermal transitions
  and preservation tests across loads.
- The 48 KB Apple II+ stays the target; the floating-point routines and
  rounding of the simulation are kept. Sleep stays close to 26.4 seconds.

### Survival banner and direct access to screens

- Danger alerts, VERY hunger/thirst and health under 40 % in inverse video;
  improvements in normal text to tell their importance apart without colour.
- TOPO/HELP hints by day, REST/HELP at night and LOWER FOOD near the hung
  bag, after the dangers and the shelter or tree hints.
- Shortcuts shown to move directly between HELP, INVENTORY,
  STATUS and TOPO. STATUS navigation fixed to the last two lines.
- Check of the alert pixels and the nine direct transitions,
  with time, reserves and the visible image kept.

### More readable help and inventory

- HELP shows two pages, movement and survival, with command examples,
  units and navigation keys. Keys 1/2 select a page,
  N/Space and B change page, Esc/Return show the landscape again.
- Help titles and inventory group in inverse video; object count,
  FREE capacities and paging commands shown explicitly.
- Browsing checked with the keyboard, without advancing time or changing
  the reserves, the health or the landscape.

### Alerts restored before display

- An improvement now replaces the worsening alert still
  pending for the same category, instead of showing an outdated warning.
- Regressions for hunger, thirst, health, temperature and immersion; alerts
  still active in other categories keep their priority. The ranking
  has no effect on the simulation.

### Result of the waiting commands

- WAIT and PAUSE announce "YOU WAITED" in hours or minutes, instead of
  "YOU RESTED"; their lack of rest credit is kept.
- Regressions on both units, the identical effects of WAIT/PAUSE,
  the separate credit of REST and the cancellation of a zero duration.
- Texts reorganised in memory without an extra disk read
  for sleep; its five reads and its final state are still checked.

### Forest limit in the information screens

- TOPO and STATUS use the map's tree altitude limit,
  like the 3D view and CLIMB TREE, instead of an 11,000-foot constant.
- The value zero keeps the historical 11,000-foot limit.
  Regressions below the limit and exactly at it, for three limits,
  checking the T/t symbols, WOODS/SCRUB and access to the trees.

### Direct NATURE value

- `NATURE 0` now disables new encounters, like the value
  zero entered at the prompt; the direct command was refused by the list
  of numeric actions and kept the previous frequency.
- Values 0–100, spaces and input at the prompt checked. Out-of-range
  numbers, decimals and units are refused without changing the player's
  state, the frequency, the landscape or the random generator.

### Objects on the ground in the banner

- "ITEMS: INV" disappears after picking up the last object or
  consuming the last reserve on the ground, as in the inventory.
- The summary no longer takes the rope counters and other equipment
  for reserves on the ground; exhausted foods no longer count either.
- Regressions through real commands on rope, axe, eggs and water.

### Projection of sites at the foot of cliffs

- A cabin far below the view no longer reappears on screen
  when the computation of its height exceeds 16 bits.
- Regression on nine cliff heights and three orientations, compared
  pixel by pixel with the independent projection model.

### Duration of encounters during stationary actions

- Encounters already present also age during WAIT,
  meals and sleep; they expire at 60 minutes, even without a move.
- No new wildlife draw during these actions. Regression on a
  wait, a meal and two rests, with presence at 59 minutes, disappearance
  at 60 minutes and random generator unchanged.
- NATURE joins the input module; this frees the space needed
  in the simulation module and avoids loading it for this setting.

### Alerts after a drink

- DRINK immediately updates the thirst and dehydration state used
  by the banner, without waiting for an action that advances time.
- A dehydration cleared by the drink no longer stays displayed; tests
  of healing, of thirst improvement and of persistent dehydration,
  with stocks debited only once and time/health kept.

### Going back between inventory groups

- From the first page of a group, B goes back to the last page of the
  previous group, instead of jumping directly to its first page.
- Regression on the bag → ground → back to the bag path, with two pages
  of objects in each group; time and stocks kept.

### Outdated illness alert

- An illness that disappeared before the banner refresh shows
  "ILL IMPROVED", instead of causing a false "EXHAUSTION" alert.
- Regressions on the three recoveries, a persistent dehydration and
  illness replacements between two displays.

### Clock minute

- The banner and STATUS round the total minutes before extracting
  hour/minute: WALK 19 MIN from 7:00 now shows 7:19, instead
  of 7:18 when the float is slightly below the whole minute.
- Carries into the next hour, noon and midnight handled together, without
  changing the simulated time. Regression on a real walk and seven
  values close to the minute and hour limits.
- Midnight shows as 12:00A in STATUS; the 12-hour format used to show
  0:00A because of the zero flag left by the comparison with 12.

### Exact end of the travel duration

- After the last requested step, WALK/SWIM stop without testing an extra
  step. The result reports the end of the duration rather than an
  obstacle (water, cliff or map edge) lying beyond the finished journey.
- Interruptions of the completed step (animal, night, bank, death, arrival)
  keep their priority. Regressions on three obstacles after exactly
  19 minutes, on a swim ending at the map edge, on water met
  with one minute left and on animal/night at the last requested step.

### Numeric arguments of medicines

- `EAT FLAGYL 0 OZ` no longer consumes a dose despite the zero quantity.
  Medicines now refuse numbers and units added to
  EAT/DRINK, instead of ignoring them and applying a single dose.
- The refusal keeps stocks, time and medical state; it explains to remove
  the number and the unit. A normal intake stays available after the
  refusal.

### Bug hunt: input and test launch

- Numeric commands accept leading spaces like ordinary
  parsing: `  SLEEP 1 MIN` no longer produces an invalid-value refusal.
  Regressions on rest, too-short walk and qualified DRINK WATER.
- `make test` rebuilds a2shot with its Makefile and its SDK paths,
  instead of using the implicit C++ rule that failed on `pom2/core.hpp`.

### Shorter wait during SLEEP

- Removal of the detour through the vocabulary and of the reload of numeric
  parsing for rest commands with a duration, as well as SLEEP alone.
- Eight-hour sleep on the initial scene: 32.1 → 26.8 seconds at
  1.023 MHz, with five floppy reads instead of seven.
- Health, weather and simulated duration kept; comparison of the state and
  the landscape with REST, and check of the six rest and wait verbs.

### Fixes on cliffs and entering the cabin

- Rejection of the overflow of the slope quotient multiplied by three:
  trees lying far below a cliff no longer reappear in the sky.
- ENTER SHELTER refuses entry from a tree; CLIMB DOWN is needed before
  entering the cabin. The refusal keeps time, position and inventory.
- Refusal message in the tree corrected: its exclamation mark was
  interpreted as a substitution of the travel-stop pattern. Same
  fix for the victory report without a move.
- Regressions on five rising/falling cliffs and on the chain
  climb → entry refused → climb down → enter → exit.

### Doses and first-aid actions

- Signed count of the uses of medical products, without overflow
  of zero or negative stocks; quantities shown in INVENTORY.
- Oral intake of FLAGYL, SALT TABLETS and QUININE through EAT/DRINK;
  refusal of oxygen, soap, creams, glasses and kits.
- SHIELD EYES and LOWER HEAD without a duration; SUCK VENOM requires an
  active bite and takes 15 minutes. LOWER FOOD/BACKPACK keeps the recovery
  of the hung bag.
- Commands moved into WILDMVI, with a resident return before the computation
  of treatments and time; the progressions stay in WILDMED.
- 130 extra cases on ROM: 90 signed counters, 12 first-aid actions,
  22 oral intakes and 6 USE/inventory/treatment chains on the last dose
  or an empty stock. The native prerequisite stays selected even without a
  positive dose; this behaviour is kept.
- Oxygen depends on the separate use flag: the last dose
  protects, but reusing an empty bottle disables this protection.
- Still to port: SPLINT, thermal treatments, placement/sterilisation
  specific to USE and the injury/illness triggers.

### Medical conditions and exposures

- Resident state of the 15 Journey conditions: incubation, health, healing
  with/without treatment and product of whole percentages.
- Prevention and treatment prerequisites, clothing protection,
  daily reset of temporary treatments.
- Salt/cold counters, strict thresholds and protected decay; solar
  and snow exposure connected to the port's data.
- Altitude sickness, oxygen and 30-minute cap in critical health or
  during the first eight hours of conditions 6–11.
- Medical USE, STOP BLEEDING and STATUS medical page.
- WILDTRV for swimming, WILDMED for treatments/exposures, WILDMVI for
  the medical state, load computation moved into WILDSIM.
- Comparisons on ROM: 160 progressions, 66 treatment combinations,
  60 altitude cases, 80 rates, 84 clothing protections and
  59 salt/cold exposures, i.e. 509 cases.
- Still to port: complementary treatments, triggers by
  attacks/falls/contamination and exact solar/snow selectors.
- TOPO: shortened legend to preserve progress while walking.
- Banner invalidated when WILDSIM borrows HGR; returning from STATUS restores
  the displayed pixels and the terrain cache. The tests tell this drawing
  apart from the unused graphics bytes serving for temporary computations.
- Adventure driver: acknowledgement of the native walking time supported,
  four scenarios finished with differences still reported; 112 bounded
  wind evolutions compared with the original engine.

### Tree rendering fix

- Underside of the first profile brought back to the height of the central
  foliage: removal of the black side spikes that went down towards the
  ground.
- Separate crowns, centred in their cells: the native 32-column
  profile no longer covers two whole cells.
- Green/black foliage pattern restored, with opaque pixels and occlusion
  of the celestial bodies; the profiles are no longer filled entirely in
  black.
- Black trunks under the centre of the foliage, anchored to the terrain;
  crowns raised by 18 pixels divided by the distance for nearby trees.
- Continuous black top outline and lower edging of the foliage to
  set the crowns apart from the purple sky and the green terrain.
- Foliage limit kept when the projected base goes beyond the screen,
  without overflowing into a black fill on downward slopes.
- This limit is stored outside the Applesoft rounding byte, to
  keep the exact duration computations after the trees are displayed.
- Visual check in the emulator and regression against continuous black
  bands, in addition to the pixel and rotation comparisons.

### Climbing and hanging food

- `CLIMB TREE` / `CLIMB DOWN`: nearby tree, health > 2.5 to climb up,
  walking and swimming refused in the tree; no time added.
- `HANG FOOD` hangs the bag and its contents for 30 minutes, with
  the native cost of 1.65 + 0.02 × body weight kcal/min.
- `GET BACKPACK`, `LOWER FOOD` and `LOWER BACKPACK` recover the bag in its
  cell; load checked and atomic restore on refusal.
- INVENTORY shows `HUNG HERE`; STATUS reports the tree and the hung bag.
- Probe of 24 CLIMB cases and 16 HANG cases in the original code on ROM;
  port tests on shared stocks, containers, screens and refusals.

### Trees and forests

- Wooded areas from the TMAKE contours and Sierra tree profiles ported.
- Projection attached to the world, clipping by the relief, priority to
  nearby sprites.
- TOPO, STATUS and the wildlife filters recognise high-altitude woods and
  scrub.
- 294-byte MAP extension, import of the TOPO forests, compatibility with
  old maps.
- Tests of the drawing, rotations and loading.


### Neowilderness lots 4 and 5 Survival, inventory and orientation

- Compass framed over its full height, kept during rotations.
- Monochrome summary around the compass: time/period, health, hunger,
  thirst, transition alert or thermal state; shelter and objects that can
  be picked up here.
- Alerts at the existing thresholds, without repetition for an unchanged
  class nor a change of rules; long activities keep a priority alert.
- STATUS reorganised, with conditions before needs/environment and separate
  CARRIED/HERE reserves; maximal case readable without cutting a condition
  name.
- INVENTORY grouped by location, twelve objects/page, split reserves
  shown separately, permanent capacities and explicit navigation.
- TOPO: C to recentre, eight magnetic headings and the site under the
  player named.
- WILDHUD/WILDSTA in the 2 KB window; banner kept during rendering
  and rotations, wildlife handled before its composition at startup.
- `test_interface.py` checks display, transitions, groups/pages/quantities,
  maximal STATUS, orientation/recentring and free browsing.
- Validation: full suite `make -C wilderness test` passed after the frame;
  disk rebuilt, rendering and memory checks included.


### Sun and moon as geographic landmarks

- Sun computed from latitude, season and solar time, independent of
  the magnetic declination; projection in the terrain axes.
- Night moon from a 1985 reference ephemeris, with stylised
  phase and average parallax correction; identified extension of the port.
- Masking by clouds, relief and sprites; the partial panorama is kept
  by day and the dark view at night, which does not reveal the terrain.
- Initialisation moved into WILDSIM to respect resident memory.
- `test_sky.py` checks positions, hemispheres/seasons, masking and
  rotations.


### Neowilderness lot 2 Readable refusals and results

- Removal of the hidden confirmations between messages: the next command
  keeps its first key. The result stays readable on returning to the view,
  during input, after Esc and after an empty line.
- Movement: effective duration and stop by water, bank, night, limit,
  animal, Esc, lack of time or terrain/pace combined. Death, victory and
  weakness keep priority; travel results keep their duration.
- Unknown verb reported with HELP; missing object accompanied by available
  examples; inaccessible object told apart from an unimplemented command.
- Consumption: accessible stock before the answer, then the quantity
  actually consumed and the initial stock. Transfers name the object as in
  INVENTORY and its new location, including qualified objects.
- Load refusals: weight, volume or both, excess and capacity after
  cancellation in OZ/IN3; distinction between worn volumes, the bag and the
  hand. Arithmetic overflow told apart from a merely insufficient capacity.
  Missing bag/canteen, non-empty containers and bag stored inside itself
  separated.
- WILDITM groups the transfers in 2 KB to free resident memory.
  The engine keeps the texts in three lines, without scrolling caused by
  a long name. `test_feedback.py` covers the refusal matrix, the maximal
  values, persistence, stock and the stops for animal/night.
- Validation: full `make -C wilderness test` passed, with the rotation
  optimisations, TOPO writes and bank crossings preserved.

### WALK / SWIM bank crossing

- WALK reported the water one cell before it, then SWIM refused its first
  half-step still on land. Two successive SWIMs therefore stayed in place.
  This half-step is now allowed if the next one enters the water, with
  the path checked without moving or spending during the check.
- SWIM makes the last half-step towards land and stops on the bank,
  with the summary of the time actually spent and the end of the immersion.
  WALK then allows continuing. SWIM without water ahead still has no effect.
- `test_shore.py` covers the four directions, a fractional position,
  a diagonal path and two successive SWIMs up to the opposite bank.
- Validation: full suite `make -C wilderness test` passed, including
  swim paths and durations, thermal balance, Esc, TOPO and rotations.

### Neowilderness lot 1 Commands and cancellation

- Esc clears the command or cancels a numeric input, without quitting the
  game; QUIT requires Y after a warning about losing progress.
- The left arrow deletes a single character in quantities and durations.
  An empty or zero input cancels the action; NATURE keeps its zero setting.
- Direct arguments and units: WALK 10 MIN, REST 1 H, DRINK WATER 4 OZ and
  EAT CHEESE 8 OZ. The old questions stay usable; no
  unit = hours or ounces. Units, ranges and overflows are checked.
- Esc interrupts WALK and SWIM after a finished step, with position, health,
  reserves and effective time kept. Rest accepts minutes; its
  interruption during the activity stays an optional follow-up.
- Esc leaves each inventory page immediately, without waiting for a
  second key. STATUS and TOPO keep their return to the view.
- WILDINP module at $5800; the word walk moved into WILDVOC and
  the HELP text into WILDSCR to stay within 48 KB, with no read added
  to the arrow rotation path.
- `test_input.py` covers cancellations, atomic refusals, units, digit
  correction, screen exits, QUIT confirmation and walk/swim stops.
- Validation: full `make -C wilderness test` passed.

### TOPO writes only the changed characters

- Removal of HOME and of the systematic rewrite of the map on every
  step or scroll. Direct comparison with the text RAM before each write,
  for the relief, the landmarks, the coordinates, the legends and the
  spaces.
- Old characters at the end of a line removed without rewriting the spaces
  already present; messages and cursor kept during the walk.
- Tests of the writes actually executed: one write per changed character
  over twelve WALK steps and the scrolls; zero writes if the map does not
  change.

### Presentation during loading

- After the Apple II+ title, the screen presents the crash, the goal of
  reaching the rangers, the survival needs and the main commands.
- Durations in hours, quantities in ounces and rotations on an empty
  line are explained. Loading continues without waiting for a key.
- Presentation entirely in English, limited to twenty lines of fewer than
  forty characters to stay visible during the DOS reads.
- Check of the text at the start and end of the loader, of the arrival at
  the playable prompt and of the restore of the resident data by
  `test_boot.py`.

### Scrolling near sites and faster rendering

- The 22.5° and 45° rotations now reuse the geometry of a single distant
  site, even off-field. The arrows load no module;
  only the uncovered columns are rendered. Scenes with several potentially
  neighbouring sites keep the selection by reprojection.
- Heading cache invalidated after scrolling to avoid reusing an
  old projection with an already shifted sprite origin.
- Direct walk of the physical lines for clearing and scrolling;
  removal of the unneeded sprite activation calls in the rays.
- Measurements: 77.0 % fewer cycles over 48 rotations near the cabin,
  compared with the forced full render; 4.7 to 11.5 % gain on the full
  render of the five control maps, with images identical to the reference.
- Rotation tests extended to distant sites, masking by a ridge,
  competing sites, full turns and the disk read counters.
- Validation: full `make test` passed, plus rotations of the distant wreck
  and selection of two sites at different azimuths; disk rebuilt.

### Sky, orientation and map during the walk

- The sky and the relief occupy the sides of the strip again. The landscape
  under the strip is kept in invisible HGR lines to avoid
  trails during rotations, without extra memory allocation.
- TOPO now shows decreasing Y: north really is at the
  top, like the moves and the compass. The scroll keys
  follow this orientation.
- On each WALK step, TOPO recentres and refreshes in the first twenty
  lines. The messages, their cursor and the simulation are preserved;
  no reload nor waiting for a key between steps.
- Checks: real N/E/S/W moves and twelve consecutive refreshes
  during WALK, with a check of the preserved areas.

### TOPO: refresh before display

- The map is rebuilt before switching to text mode on opening,
  to avoid the brief appearance of the previous TOPO or STATUS screen.
- Check of reopening after scrolling, walking and rotating:
  recentring, position/heading, relief and landmarks reread from the
  current state; the 3D view and its compass strip stay intact on return.

### Permanent compass at the top of the view

- Removal of the `USE COMPASS` activation: the cardinal points are
  available from the start, without deactivation during object transfers.
- 98-pixel strip centred at the top, with N/NE/E/SE/S/SW/W/NW, ticks
  every 22.5° and a fixed cursor. Continuous scrolling at one pixel per two
  azimuth units, taking the magnetic declination into account.
- Header reserved over 16 lines; it stays visible at night and in the
  cabin, and is not dragged along by the terrain scrolling. No disk load
  nor floating-point computation to update the strip during rotations.
- Check of the 560 azimuths, the north join, the magnetic centring,
  the rotation commands and the returns from STATUS.

### View rotations

- Scrolling of the terrain and local sprites for the 22.5° and 45°
  rotations; only the incoming columns are recomputed. Geometry and
  masking of distant sites keep the full render.
- Restore of the sprite image after loading the LOOK
  vocabulary; the arrows avoid this load when the image is already in
  memory.
- Shortened scroll loop and removal of a 141-byte sine
  table, with the direction rounding kept exactly.
- Test of the five sprites, exits/returns into the field and full turns
  in both directions. Over 52 rotations around the wreck: 435,480,947 →
  98,301,942 cycles, i.e. 77.4 % saved, pixels and text identical.

### Temperature: original slow variation

- Addition of `INT(5 × SIN(0.0187 × hours elapsed + phase))`, with the
  saved phase of the first Sierra journey and the Applesoft ROM rounding.
- 405 cases compared with the original T09/S08 routine: phases, durations,
  signed temperatures and crossing the one-byte limit.
- The air now matches at the six points of the starting scenario; the
  differences go from 13 to 6, still on the wind and the felt temperature.
  The daily cycle, visibility and weather fronts are still to port.

### Walking: waiting and disk access

- Wildlife grouped with the environment computations: two module
  reads per ordinary step instead of three when the wildlife is active.
- Minutes travelled shown after each step, without a key to press.
- Test of a four-hour walk: progress, number of reads,
  return to the command and no extra reads at the stop.

### Terrain: rivers and lakes

- Plateaus now drain towards an outlet instead of triggering
  artificial lakes. Real basins are filled up to the
  overflow level, with a flat surface and a continuous outlet.
- Removal of the fill truncated at 300 units and of the water squares
  erased after generation around the crash and the rangers. A source
  covering these places is rejected before the terrain is modified.
- 224 × 168 to 112 × 84 conversion: each block keeps its water points,
  including at odd coordinates, at the water height. The cabin
  also avoids these converted cells. The other TOPO markers are no
  longer interpreted as rivers.
- Tests of plateaus, small/large basins, thin rivers and
  18 seed/difficulty pairs: continuity, descent and reproducibility.
  The drainage stays a reconstruction, to be compared with the original
  generator.

### Swimming: tracing oblique headings

- Continuous vectors replaced by the original's integer major axis and
  sinusoidal accumulator; the duration now tells apart each step that is
  actually straight or diagonal. Trace state kept across module changes.
- 2,880 positions over 360 headings compared with the original routines on
  ROM.

### Swimming: effort and load

- The 19 minutes per cell replaced by the original's normal swimming
  duration, which depends on health, load and whether the step is
  diagonal. SWIM now advances by half a cell; a last step can
  exceed the requested time if at least half of its duration remains.
- 143 durations identical to the original routines run on ROM; tests
  of the real command, the duration overrun and the return to the bank.
  New `WILDTRV` module to preserve the resident memory space.

- SWIM now uses the original cost linked to the total weight: about
  14.43 kcal/min with the initial equipment. The canteen water is no longer
  counted twice in this computation; shivering adds to this effort.
- 81 weight, load and duration cases check the calorie expenditure; the
  metabolisms are also compared byte by byte with the original helper
  run on the ROM, and the calories with its energy routine. First
  swimming health interval restored to 15 minutes. Test of the real
  command, immersion, rest in the water and exit onto the bank. The
  injury/equipment modifiers are still to reproduce.

### Comparing commands with the original game

- New differential driver on the two Apple II executables: start,
  equipment, drinks, meals, repeated rests, night and first walk.
  Questions inspected before answering; errors and differences make the
  test fail. Dumps, images, logs, symbols and reports stay in `build/`.
- Observation of the original state before its paging on Journey T04,
  to avoid mistaking the second HGR page for the physiology.
- Drinking from the canteen no longer takes time; eating takes 16 minutes,
  with the original food and water credits. The shivering of the
  initial save contributes to the first calories spent.
- Adaptive rest after the first 30-minute step; counters and
  deficits updated at the health rate, whole percentages and initial Hmax
  kept at its original precision.
- Fix of the previous encounter rule: rest and meals
  draw no wildlife. Draws and interruptions stay active while walking.
- Cardinal directions corrected by the map's magnetic declination.
  The compass's random accuracy is still to port.
- `make test-original` still fails on the weather/night/walk differences.
  No complete adventure up to the rangers is validated yet.

### Encounters during actions

This step came before the differential fixes above; the
draws during REST and its fixed rate have since been replaced.

- Draw on each simulation step: 30-minute rest, walk/swim
  according to the step duration; removal of the sum capped at 255 minutes.
- All species are tested in Sierra order, even if an animal
  is present; kept or replaced at 50 %, checked in the original.
- An accepted encounter interrupts walking/resting after the elapsed step,
  with exact time and a rest-interruption message.
- No outdoor draw under shelter; VIEW/STATUS spend neither time
  nor randomness. Interruptions leave the sprite available for the next
  action.
- Probes of the original flags and deterministic scenarios of long rest,
  interrupted walk, replacements and protection by the cabin.
  The 60-minute presence duration and the animals' movements are still
  provisional.

### Sierra wildlife and movement limits

- Filters of the three species: season, time, terrain, altitude, maximum
  slope of the 3 × 3 neighbourhood and regional climate index.
- Probability `minutes × NATURE × √difficulty × rate × 10⁻⁵`, with the
  original rates 80/40/100 and a generator independent of the weather.
- NATURE command: integer multiplier 0–100, initial value 1, refusal
  of higher values; nocturnal animals stay invisible at night.
- Difficulty and Sierra index in the map header; old maps
  compatible with the default values 4 and 31.
- Walking and swimming stopped before the outer two-cell band, with
  an explicit message and no time charged for the refused step.
- Probes of the original code, scenarios per species and tests of the four
  sides. Draw rate, presence duration, movements and reactions are still
  provisional; NATURE does not accept fractional values yet.

### Sites visible from a distance

- Wreck and cabin projected within eight cells: azimuth from their
  fixed coordinates, stepped sizes and anchoring on their altitude.
- Sprite inserted at the ray step matching its distance; the relief
  lying in front masks it, the relief lying behind keeps the sprite visible.
- Composition always per column, without a disk load in the rays,
  with the colours, transparency and black pixels of the original streams.
- WILDPRJ module to prepare the geometry and the terrain bounds; cache
  reused when position, heading and encounter stay identical.
- Full rotations near the sites, including when they are off-field,
  to avoid missed appearances and trails from partial scrolling.
- Exact comparisons and approach/return routes on foot. Current limit:
  a single site per view, selected by distance in the field; the animals
  stay local and the projection is a rule specific to the port.

### Cabin and TOPO

- `ENTER SHELTER`, `EXIT SHELTER` and `LEAVE SHELTER` at the cabin; indoor
  state kept during REST, rotations and STATUS/TOPO screens.
- Thermal protection of the found shelter: ambient air +15 °F, no wind,
  compared with the original branch; HUT stays a separate craft.
- Walking/swimming refused indoors, no encounters during
  rest under shelter and the outdoor view restored on exit.
- First 32 × 14-cell text TOPO map: relief, water and
  player/wreck/cabin/rangers landmarks, with bounded scrolling by arrows or
  WASD.
- New WILDSIT disk module; qualifier resolution moved
  into WILDVOC to preserve the small resident memory margin.
- Route tested without changing the position in memory: spotting, walking,
  entering, resting in the cold, exiting and returning; extra night tests
  and local probes of the original commands and temperatures.

### Per-column rendering

- Composition of the sprite and the terrain in each column, without an
  overlay pass after the full view; disk load before rendering.
- Fill limited to the transparent areas and rays stopped when
  the maximal relief can no longer contribute to the lines still visible.
- Reuse of the BLOAD text buffer for the column's 160 colours,
  with the opaque black pixels and the rotations kept.
- Wreck moved down by ten lines to recover its original vertical
  coordinates, without encroaching on the text.
- Test of the intermediate image, exact comparisons on five maps and
  profiling of the ray steps and cycles outside DOS loading.

### Documentation

- TODO reorganised into ordered lots, with the fix of the terrain/sprite
  rendering as the first priority.
- README refocused on the playable state, the commands and the build.
- Port reference gathered in `docs/IMPLEMENTATION.md`: provisional
  rules, memory, map format, tests and tools.
- Cleanup of outdated mentions in the analyses and addition of this history.

### Original graphics

- Extraction of the Journey streams of the wreck, the cabin and the animals,
  with transparent PNGs and a manifest of positions/footprints.
- Wreck, cabin, bear, cougar and Sierra rattlesnake sprites hooked
  into the 2 KB disk load window.
- Wreck anchored at the start, cabin placed on land and first graphical
  encounters with an independent random generator.
- Colours, black pixels and transparency preserved;
  clipping, heading tracking, night masking and clearing when leaving the
  cell.
- Pixel-exact tests of the five images and of an encounter after REST.
- The cabin is visual only and the animals' behaviours are still to port.

### Immersion

- SWIM crosses water cells and stops before the bank; WALK reaches land.
- Losses from wet clothes, water temperature linked to the altitude and
  immersed thermal balance; sweat removed in the water.
- REST keeps the immersion; STATUS shows IMMERSED. A step on land
  resets the selector to dry. The swimming rate stays reconstructed.

### Wind and energy

- Signed felt temperature shown in STATUS and used by the thermals.
- Integer kcal expenditure per step; shivering supplement according to the
  weight, with an effect on the food deficit and the basal metabolism kept.
- Wind and energy formulas compared with the original routines on ROM.

### Dry thermals

- Body temperature according to air, activity and clothing; recovery
  capped at 98.6 °F and drift threshold checked on the ROM.
- Deterministic reconstruction of the clothing layers and of the cold/heat
  health factors; activity stopped when health becomes fatal.
- STATUS shows body temperature, shivering/sweat and hypo/hyperthermia.

### Disk modules

- Vocabulary, screens and environment split into a shared BLOAD
  window, with a cache of the current module.
- Zero page, visible text, HGR and game state preserved.
- Hourly air and thermals grouped to limit the reads during REST.

### Objects and load

- WEAR, GET/PACK, CARRY/TAKE and DROP/REMOVE: body, bag, hand and ground.
- Positions on the ground, pickup on return, accessible quantities and
  qualifiers for shared names; compass disabled when it is dropped.
- Weights and volumes per category, atomic overload/overflow refusals,
  containers emptied before dropping and remaining capacities in INVENTORY.
- Model limits calibrated on the original's starting capacities;
  exact accounting of the containers still to establish.

### Playable base

- 3D terrain view, generated maps, rotations and partial scrolling,
  compared bit-exact with a Python reference.
- 280-word parser, walking, resting, meals, drinking, compass,
  STATUS and INVENTORY.
- Clock, date, sun, air, energy, survival deficits, health, death
  and arrival at the ranger station.
- Tests of random commands, refusal of night walking and time computation
  on steep slopes.

### Graphical TOPO and local MAP

- TOPO/T shows an HGR sheet of the whole terrain: contour lines
  interpolated every 400 feet, water, woods and C/H/R landmarks, north at
  the top.
- MAP keeps the text window centred on the player, its scrolling,
  its recentring and its differential writes during moves.
- Each disk holds a sheet computed from its own map; closing
  TOPO restores the view without changing the time, position or provisions.

### Movement tests aligned with the native rules

- Fix of the expectations that had become obsolete in the input,
  cabin/orientation and long walk tests: half-cells and computed rate.
- Explicit check of the budgets that are refused, exact and exceeded by
  the last admitted step, of the return to the cabin after a rest and of
  the disk reads.
- Movement documentation updated; the native engine is kept.


## Moved out of TODO.md on 2026-11-16

### Priority: a complete adventure compared with the original

- [x] Compare start, compass, parka, drinks, meals and repeated rests;
  fix action times, credits, counter rate, calories and
  whole health percentages.
- [x] Observe the original state paged on Journey before its reuse
  as a graphics page, without modifying the game or adding a command.
- [x] Port the slow temperature wave and its initial Sierra phase;
  compare 405 cases with T09/S08 on ROM. The air matches at the six start
  points.
- [x] Port the daily/hourly temperatures, weather fronts, randomness
  and health step caps; compare their routines on ROM.
- [x] Make the wind and the felt temperature match in the short scenarios,
  including the night, and in the native walk to x70/y86.
- [x] Check full-moon nights: black sky, relief, trees, sites and
  animals visible; keep the night for the survival computations.

### 3. Replace the provisional encounters with the original wildlife

- [x] Port the Sierra criteria: season, time, altitude, terrain,
  difficulty and frequency set by `NATURE`.
- [x] Draw encounters on each simulation step rather than on returning
  to the view; remove the sum capped at 255 minutes for long actions.
- [x] Test all species even with an animal present, port its
  50 % keep/replacement and interrupt the walk on acceptance.
- [x] Make the encounters playable: SCARE/IGNORE/ATTACK, tools,
  cuts/bites, protection by tree/cabin and encounter summary.
- [x] Probe the Sierra noise, injury, combat tool and theft thresholds
  on ROM; replace the automatic successes and give the provisions an effect.
- [x] Check the bear/cougar severity distribution on ROM and trigger
  cuts, fractures or shock with the existing conditions and treatments.
- [x] Probe the native postures and shelters on ROM: separate risk on the
  ground, IGNORE and tree; remove the player's invulnerability in the tree.

### 5. Complete the survival actions and risks

- [x] Stop walking and swimming two cells from the map limits; keep
  the position and charge only the accepted steps (`test_boundary.py`).
- [x] Port the swimming effort according to the total weight and check 81
  metabolisms on the original ROM; keep the immersion and bank exit tests.
- [x] Port the normal swimming duration according to health/load, check 143
  steps on ROM, advance by half-cells and admit the last step at half
  duration.
- [x] Port the integer tracing of oblique headings; compare 2,880 positions
  for the 360 headings with the original routines on ROM.
- [x] Port the curves and prerequisites of injuries/illnesses 1–15;
  compare progression, prevention, treatment and altitude with the original.
- [x] Connect the salt/cold counters, medical USE, STOP BLEEDING
  and the paged medical state.
- [x] Count the positive doses, show the remaining uses,
  port oral intake, SHIELD EYES, LOWER HEAD and SUCK VENOM;
  check the refusals and the native behaviour of exhausted stocks on ROM.
- [x] Collect water at the bank with canteen, capacity and load;
  trigger giardiasis from an untreated reserve that is consumed.

### Rendering and map improvements

- [x] Replace the fake plateau lakes with drainage towards the outlets;
  fill the basins at a constant level and keep the thin rivers
  in the 2 × 2 blocks, without erasing stretches around the sites.
- [x] Add the forests to the map and the view with a suitable data format.
- [x] Port the interactions with the trees: climbing and hanging food,
  recovering the bag in its cell and checking capacities without losing
  stock.

## Before the next lot: memory space

- [x] Consult `build/wild.map` and measure the available space before adding
  resident code. The `$4000-$57FF`, `$6000-$6FFF` and `$1000-$1FFF` areas
  have been almost full since the sprites were hooked in.
- [x] Move the new rules and screens into disk modules;
  keep a limited, explicit resident state for the sites and shelters.
- [x] Check module changes with active sprites: zero page,
  text, HGR, objects, clock and cache must be preserved.

## 1. Terrain and sprite rendering — done

- [x] Replace the full view followed by an overlay with a terrain/sprite
  composition during the rendering of each column.
- [x] Use the opaque coverage of the sprites to avoid the rays and
  fills that can no longer contribute to the image; take into account the
  transparent holes and the opaque black pixels.
- [x] Adapt scrolling and rotations without trails or a change in the
  apparent position of the sprites.
- [x] Measure the cycles and the number of ray steps with and without a
  sprite, separating out the cost of disk loads.

**Validation:** `test_scene_render.py` checks an intermediate image,
the final pixels and the ray steps on five maps, one of them without a
declared ceiling. `test_sprites.py` covers the five sprites at the edges
and the rotations. The wreck gets back its original height, ten lines lower.

## 2. Sites, cabin and orientation — done

Cabin, TOPO and projection of neighbouring sites integrated. The next lot
covers the original wildlife rules.

- [x] Establish the commands and the indoor/outdoor state of the cabin in
  the original; tell a found cabin apart from a built shelter (`HUT`).
- [x] Allow entering and exiting, with useful refusals away from the site.
- [x] Apply the thermal protection during rest and restore the
  outdoor environment on exit; refuse walking/swimming while inside.
- [x] Make the sites identifiable from neighbouring cells: distance,
  orientation, size and occlusion of the sprites; keep their position
  during moves and returns.
- [x] Add a first usable TOPO screen: relief, water, position,
  wreck, cabin and ranger station, with scrolling.

**Validation:** find the cabin without modifying memory, enter,
rest in the cold, exit and return; compare indoor/outdoor and check
the clearing of the sprites during rotations and cell changes.
`test_projection.py` compares the images with an independent reference:
directions, cell fractions, sizes, clipping, relief in front/behind,
cache and approach/return by WALK. The first version shows a single site
at a time, within a radius of eight cells; the projection is a rule of the
port.
