# Wilderness — history

The steps below describe the work present in the working tree. They do not
correspond to released versions. Upcoming tasks are tracked in
[TODO.md](TODO.md) and the limits of the port in
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Unreleased

### Standalone benches: shared loader (22 October 2026)

- `NEODHGR.SYSTEM`, `NEOHOF.SYSTEM` and `NEOSTARS.SYSTEM` come from a single
  source, `src/bench_boot.s` (`-D BENCH_DHGR`, `BENCH_HOF` or `BENCH_STARS`),
  linked by `src/bench_boot.cfg`. The three binaries are byte-for-byte
  identical to the old ones. `bench.mk` groups the loader, the
  `dev/lib/prodos` objects and the ProDOS dependencies of the bench disks.
- `hof.mk` assembles again: `hof.s` on its own (`HOF_BENCH`) loads
  `.macpack longbranch`, which `wild.s` provides to the game.
- `print_byte` (`wild.s`), never called, is removed; `pdec` does the same
  job.

### Followed hunt, camp and interruptions (18 October 2026, XL)

- The hunt summary distinguishes the weapon in use from the proposed
  preparation. Changing weapons and making a spear are reachable with the
  joystick. A preparation returns to the summary before any attack. The
  result keeps the prey: retry or change after a failure, butchering then
  pickup after a success, and the existing cooking and meal follow-ups.
- A camp preparation returns to the chosen step, with an updated state.
  Departure keeps the explicit actions for exit, tent and fire, and adds a
  review of the followed route.
- An encounter dialogue keeps the native result, the real state of the
  weapons and of the fire, then opens an explicitly chosen native response.
  The interrupted route or rest can be reviewed after resolution.
- After a survival action with the joystick, the kept route offers a review
  of the heading or resuming walking/swimming, with native confirmation.
  Re-aiming the heading is also offered far from the target; the dialogue
  stays readable within the four lines of the view.
- Controlled comparison after the same successful hunt: butchering, picking
  up, cooking 8 OZ and eating those 8 OZ takes 27 → 12 joystick gestures
  (−55.6 %). The 1497 savable bytes are identical at the three checkpoints.
  The test time in emulated cycles drops by 11.7 %, joystick pulses
  included; setup and lighting excluded.
- Computing the projection negatively replaces a 256-byte cache to make room
  for these additions. Comparison of six views with the previous image: same
  visible pixels and native state; extra rendering cost measured at 0.23 %
  to 3.99 % depending on the view, with no extra disk read.
- Final validation: 74 XL scripts pass, and FORAGE against the ROM (130
  cases compared, four historical exclusions). Image: 432/1600 blocks.

### Durations per activity, day/night and explicit corrections (18 October 2026, XL)

- Walking/swimming, rest and waiting have three separate memories. Up/down
  step through the quick levels; left/right adjust the minute. A NIGHT
  proposal does not replace the usual rest duration.
- During the day, NIGHT advises 30, 120 or 480 minutes according to the
  native ENERGY thresholds. Preparing the next sunrise is a separate choice.
  After the proposed rest, the result stays visible: reviewing the duration
  until dawn or opening the departure actions asks for confirmation.
- QUICK proposes a correction based on the warning: confirmed DOUSE, native
  DRINK/EAT sources or a GET selection with a FIT preview. In an OBJECTS
  confirmation, UP FIT takes back an admissible portion without losing the
  object, the source or the destination; no transfer is implicit.
- Measurement compared with the frozen previous image: selecting 1 minute
  from 60 takes 5 gestures instead of 17; 1,195,175 cycles instead of
  4,059,789. The savable state and the RNG stay identical before/after
  each selection (`tests/measure_duration.py`).
- Validation: the 71 XL scripts pass, as does FORAGE against the ROM (130
  cases compared, four historical exclusions). XL image: 425/1600 blocks.
- Full visible game on the final image, with the joystick: making a spear,
  hunting, butchering, pickup, cooking, meal, a night interrupted by a
  cougar and a confirmed resume, then victory at the rangers. Sierra
  level 4: 175 steps, final health 89 %, native score 100 %. Captures and
  measurement limits described in MENUS.md; session kept on port 8771.

### Shared durations, camp and QUICK access (18 October 2026, XL)

- WALK, SWIM, REST and WAIT share a duration confirmed in minutes,
  adjustable in steps of 15 or of one minute; typed commands remain
  available. Cancelling leaves the remembered duration and the simulation
  intact.
- NIGHT plans the end of the night, including sunrise after midnight,
  rounds up to the next minute and announces its one-minute margin when
  the date changes. Requests over eight hours are possible.
- QUICK reaches CAMP, NEXT ACTION and MAP without going through the tabs.
  CAMP lets the player prepare the night, leave the shelter, pick up a
  local tent and put out the fire. Each command takes an explicit gesture.
- COOK/BOIL preparations keep the choice of object, source and portion.
  Lighting, fuel and utensils are separate actions.
- Drinking from the canteen's clean supply reuses the landscape; reviewing a
  target keeps the map cells when its framing does not change. Comparisons
  on the same binary: about 80 % and 87 % of emulated cycles saved on these
  transitions, with native state, RNG and compared images identical.
- Validation: 71 XL scripts, FORAGE (130 ROM cases, four historical
  exclusions), a visible demonstration of 157 joystick gestures. The final
  image takes 424 blocks out of 1600.

### Camp, approach and direct dialogues (18 October 2026, XL)

- Pickup and processing results stay readable on the left; the object, the
  ounces, the source and the next action are shown on the right. The
  intermediate acknowledgement and the old footer reminders are removed.
- MENU → NIGHT reviews the six needs of a camp, distinguishes reachable and
  carried bedding, then opens the native forms. The proposed rest depends on
  the time of day; its interruption keeps the native summary. USE exposes
  the tent; the help points out that the sleeping bag has no native
  activation and proposes the clothes that can really be worn.
- MENU → NEXT ACTION chooses a piece of advice according to the observed
  needs, or opens the map. The banners name protection and equipment
  actions.
- The followed route shows the target, the fractional distance and the
  cause of the stop. Nearby, a short native step and a re-aiming of the
  heading are offered explicitly. An exact target blocks a new departure
  without a duration.
- Leaving the advice reuses the kept image and clears the old text
  reminders, instead of computing the landscape again.
- Validation: 66 XL scripts and FORAGE (130 ROM cases). The comparative
  water run goes from 16 to 14 gestures; leaving the guide saves about
  93–95 % of the emulated cycles on the two measured transitions.

### Direct needs and explicit follow-ups (18 October 2026, XL)

- STATUS lets the player select HEALTH, ENERGY, MEAL, WATER and BODY.
  HEALTH leads to the care actions; the other needs open the matching advice.
- After picking up food or water, cooking or boiling, an explicit proposal
  keeps the object, its source and the processed portion. The quantities
  stay editable and no next step is automatic.
- An unavailable intention explains its prerequisites in the result area.
- Object transfers that have no effect on the landscape avoid redrawing it
  completely. Tent changes keep the scene rendering.
- HELP and the advice use separate images loaded on demand.
- Validation: 61 XL scripts and the full FORAGE suite (130 ROM cases).
  The collect/boil/drink run goes from 28 to 16 gestures; the compared AXE
  transfers save about 82 % of the emulated cycles.

### Guided survival, chains and responsiveness (18 October 2026, XL)

- MENU → SURVIVAL: four needs, local resources and prerequisites, portions
  limited to the supply, separate advice for cold and heat.
- Meat and water runs always reachable from the guide, next choice
  remembered, native forms and cancellation without consumption. The texts
  specify the transfer to the ground after COOK and BOIL.
- EQUIPMENT distinguishes the commands of the tab from those of the lists;
  an empty category explains why there is no action. One-ounce provisions
  keep the confirmation but skip a quantity choice that has no alternative.
- MENU drawn in the EQUIPMENT window to free up room in STATUS.
  Returns to REST and EAT correctly ignore an old invalidated interface
  window, instead of trying to load that indicator as a module.
- TRIPUI is split from NAVIGATION: 4 disk reads instead of 22 on the
  comparative WALK scenario, with identical position, supplies, time and RNG.

### Followed destination and pickup after a hunt (18 October 2026, XL)

- MAP remembers a target after a successful orientation, recomputes distance
  and heading, and offers to resume, change or abandon. Abandoning the target
  also clears the pending route; cancelling keeps the previous intentions.
- The choice of an interrupted route also offers to abandon it explicitly.
  The swimming hints recall the native conditions for entering the water.
- Preparing a hunt announces the tool, the native delay and the known
  limits. Attempts with no known chance are flagged before confirmation.
  Effective weapons already active keep the direct path.
- A local carcass gives priority to GET and is preselected in its list,
  even if a route is waiting to be resumed. After pickup, resuming stays
  available. No change to the hunting probabilities.

### Grouped departure and contextual action (18 October 2026, XL)

- MENU → PREPARE: a checklist of fourteen pieces of equipment, local supply
  distinguished from objects already carried, load preview and a shared
  confirmation. The native commands run the transfers in order; a refusal
  stops the sequence, without undoing the transfers that already succeeded.
- The grid suggests resuming, crossing, picking up a catch, then drinking.
  A manual choice stays stable in the same context. A live animal no longer
  triggers the automatic selection of an attack.
- A newly confirmed heading replaces the pending route; cancelling and
  refusing the orientation keep it.

### Resuming routes and explicit actions (18 October 2026, XL)

- An interrupted move keeps its heading and its remaining minutes.
  WALK/SWIM offers to resume or a new duration; the grid skips its
  duration choice when a resume is available. RESTORE clears this
  interface intention, which is separate from the saved state.
- The movement budget can no longer be exceeded by a whole step.
  The report gives the remainder and, if needed, the cost of the next step.
  An extension asks for explicit agreement. The costs and distances of the
  steps remain native; this budget limit is an XL change.
- Preparing a weapon for the hunt is announced and can be cancelled before
  it runs. A weapon that is already ready skips this extra confirmation.
  OBJECTS proposes USE by default for a usable carried object.
- The advice names an action: eat, drink, rest or adapt one's clothes.
  Hunting failures distinguish darkness, a poorly suited weapon and a
  missed attempt; the probabilities are unchanged.

### Fluidity, orientation and survival (18 October 2026, XL)

- EAT/DRINK/BOIL portions shared between the grid and OBJECTS after
  confirmation, recalled within the limits of the source; the grid chooses a
  proposed portion that is less than or equal. OBJECTS shows SOURCE LEFT in
  ounces. WALK/SWIM remembers the last duration chosen in the grid.
- HELP distinguishes GET to PACK/HANDS from USE to activate. OPTIONS names
  STOP FOR FOOD DISCOVERY; the native search and interruption rules are
  still used.
- LOOK offers AZIMUTH, adjustable by 1° horizontally and 10° vertically.
  MAP opens a destination choice, a cursor and a distance/heading review.
  Taking the heading uses the native aids; the movement stays explicit.
  The navigation module is read from disk on demand.
- REST/WAIT accepts cancellation between intervals and reports the duration
  actually spent when it stops. Rest credits its recovery progressively: an
  interrupted request no longer recovers its whole duration. This
  correction deliberately changes the native order of operations.
- Hunger/thirst: softened initial warning, then specific messages when the
  95 % and 50 % health thresholds are crossed. A pickup can cancel a forced
  sleep that has become useless.
- NATIVE JOURNEY RATING identifies the native percentage; POINTS identifies
  the XL ranking calculation. The ranking formulas are kept.
- Regressions adapted to the XL pages and glyphs, with automated checks of
  portions, cancellations, routes, interrupted rests and orientation. These
  checks do not amount to a validation on a physical joystick.

### MouseText actions by intention (17 October 2026)

- OBJECTS, EQUIPMENT and the grid share the preparation of USE: bait before
  trap/fishing, fuel and matches before the stove, lamp before first aid in
  the dark. The previews announce these preparations. A failed step stops
  the sequence; the refusal stays visible and the page gets its selection
  back. An encounter always interrupts the queue.
- CRAFT takes the reachable tool into account in its estimate, then
  prepares it after confirmation. Typed MAKE commands keep their rules.
  An activation on an old cell no longer exempts from preparing here.
- The COOK/CATCH duration entry offers 10, 20, 30, 60, 120, 240 and 480
  minutes on the right; up/down adjust by the minute, Escape cancels.
- The footer distinguishes PAGE and LIST. OBJECTS, HELP, OPTIONS and MENU
  stay on their last entry when moving down further.
- Reorganisation of the fire and GRID windows, with no added resident code.
  The confirmations and the precise targeting of supplies are kept.


### EQUIPMENT in two columns (17 October 2026)

- Balanced list in two columns, up to 28 visible objects, then scrolling.
  Up/down go through the columns; left/right keep the categories. The full
  sheet, the actions and CATCH stay on the right.
- Joystick check of every selection on a list of 59 objects, of the limits,
  of the frames and of the absence of any simulation effect. Fixed the
  erasure of the last three lines of the list.

### Reorganisation of the MouseText pages (17 October 2026)

- STATUS: five compact indicators with distinct MouseText strokes, with no
  merged white block between the lines; MEAL/WATER with no ambiguity about
  hunger, explanations moved to HELP. MEDICAL shows the useful care actions
  and the protections; the full catalogue stays reachable with the
  directions and the button, with an adapted frame and no 0 % severity on
  protections alone.
- EQUIPMENT: categories WORN, HANDS, ACTIVE, PACK reachable with left/right
  in the lists. A single sheet, location and activation distinct; the
  object follows its category change after an action. An empty category is
  navigable, without using the old selection. Mentions of internal flags
  and repeated explanations are removed.
- CRAFT: summary and only the missing prerequisites; right opens the
  factors, left folds them. MAKE durations and follow-ups unchanged.
  OBJECTS keeps the blocks and gauges, with a position in the list instead
  of MORE.
- HELP: four topics, one expanded explanation. OPTIONS: compact list and
  selection help. MENU: objective and a single list of actions. The
  shortcuts still work although their letters were removed from the front
  of the lines. Game introduction shortened, with access to the commands.
- XL image regenerated; new checks of the runs and frames in
  `test_readable_pages.py`. The 47 scripts of the XL suite pass, including
  the transfers replayed after the image build finishes, the native
  comparison and the full joystick run. See MENUS.md § 39 and CRAFT.md
  § 12.

### EQUIPMENT between OBJECTS and CRAFT (17 October 2026)

- Tab order: STATUS, OBJECTS, EQUIPMENT, CRAFT, HELP, OPTIONS, MENU.
  The arrows follow this order and left from CRAFT opens EQUIPMENT.
- Page tables, frames, focus and joystick runs adapted; the last page
  memory and the object selection are kept. I/O stays OBJECTS and E opens
  EQUIPMENT from CRAFT as well.
- Going straight from CRAFT → EQUIPMENT also clears the separator column,
  with no leftover characters from the previous page.
- XL image regenerated in `dist/NEOWILDERNESSXL.po`. The 46 scripts of the
  XL suite pass, with a full joystick run and saves.

### CRAFT: tool preparation and estimated finish (17 October 2026)

- The duration factors distinguish AXE/KNIFE ON and OFF. A line states
  IN USE HERE, AVAILABLE - USE IN EQUIPMENT or MISSING HERE; holding a tool
  does not activate it. An activation flag on another cell is shown as
  inactive without changing the native state.
- A possible recipe shows EST. FINISH as a 24-hour time, with +nD if it
  finishes on another day. The calculation adds the native duration to the
  minutes rounded like the clock; a missing or already finished recipe
  promises no finish. Looking at the page spends no time.
- The ingredient pointers now carry their own high byte, so that they keep
  their labels when they cross a memory page.
- XL: CRAFT ends at $A6A8, CRAFTX tail at $A951; page load goes from nine
  to ten blocks, MAKE keeps its four recipe blocks. New coverage on the
  joystick port: presence/activation, cell left, cancellation, read-only,
  time limits, midnight and two-day jobs. Validation: `make test-xl`, 46
  scripts pass, including the 20 scenarios of the new preview and the run
  CRAFT → EQUIPMENT → USE → CRAFT.

### CRAFT: readable result and joystick follow-up (17 October 2026)

- After MAKE from CRAFT, the native result stays on screen. Left chooses
  RETURN RECIPES, right RETURN OBJECTS or RETURN ENTER for a shelter; the
  main button confirms and ESC VIEW keeps the view. A held button does not
  skip the result and does not repeat the making.
- RECIPES finds the same recipe again and recomputes its state. OBJECTS
  selects the product on its real side and gives its native actions; ENTER
  explicitly runs USE HUT/IGLOO/TRENCH. Nothing is taken, activated or worn
  without the player's choice. An unreachable product is not offered after
  a refusal.
- An encounter ends the queue and keeps the engine's priority. Typed MAKE
  keeps its usual ending; looking at the choices and going back to the
  recipes spends no extra time. The return values are outside SAVE.
- SIM joins the compressed XL modules through the path already used on the
  historical edition, to make room for the navigation. Its decompressed
  image and the simulation state stay identical; INPUT and the RESET path
  stay raw.
- Validation: 45 XL scripts, fifteen scenarios dedicated to the joystick
  port, MAKE durations and state compared with the typed commands; QUIT,
  RESET and restoring the ProDOS state also checked. Audit and TODO
  updated.

### STATUS: gauge meaning readable without a keyboard (17 October 2026)

- The free lines under the indicators explain HEALTH (share of the
  maximum), ENERGY (rest debt scale), HUNGER and THIRST (scales of how
  recent the meal/drink is), BODY (temperature with a 98.6 °F reference).
  A reminder states that fuller bars mean a better state.
- The REST/SLEEP, EAT and DRINK advice stays visible while navigating the
  care actions. The five indicators keep their rows and their calculations;
  the LOCAL/CONDITIONS blocks and the medical focus stay reachable.
- The texts share six existing entries of the bank, with no new ID.
  The old bar body of the removed text edition is deleted; XL keeps its
  MouseText drawing already in use, with a STATUS margin recovered.
- Validation: 44 XL scripts, including 49 value/threshold cases on the
  joystick port, navigation and cancellation without mutation, and a visual
  check of the screen. Rounding, labels, negative debt, fatigue priority
  after 16 hours, meal/drink recency and temperature stay consistent with
  the existing calculations.

### STATUS: USE FIRE conditions and remedies (17 October 2026)

- The preview announces a missing fire to prepare, a fire available to warm
  up, caution in a shelter, immersion or blocking weather. Rain and wind of
  at least 41 MPH show ACTIVATE FUEL FIRST; water says to reach land. The
  priorities follow the native command: shelter before immersion and
  weather, active fuel before the storm refusal.
- The presence check accepts any non-zero fire indicator, like the engine.
  The preview activates neither light, nor heat, nor care; after
  confirmation, the native effects and RETURN CARE stay unchanged, at
  0 MIN.
- The MENU/OPTIONS commands and the OBJECTS group titles join the existing
  entries of the text bank to make room for the check. The texts and
  commands stay identical; the QUIT title of the frame keeps its local
  string.
- Validation: 43 XL scripts; twenty extra scenarios on the joystick port
  cover the 40/41 threshold, strong wind, rain, fuel, shelter, water and
  fine geography. Preview/cancellation without mutation, warnings, refusals
  and real effects are compared; reference simulation unchanged.

### STATUS: water sources for DRINK and WET BODY (17 October 2026)

- The preview distinguishes WATER STOCK HERE; OZ NEXT, RIVER/LAKE HERE,
  ALREADY WET; NO OZ NEEDED and NO WATER HERE; FIND WATER. DRINK favours
  the reachable supply; WET BODY first checks the already-wet state, then
  nearby water. The suspended supply and distant piles stay excluded.
- The check respects the neighbouring banks of the historical maps and the
  exact cell of the fine-geography maps. Looking at or cancelling STATUS
  creates no water and changes neither supplies, time, RNG nor care.
  The ounce choices, effects and refusals stay native after confirmation.
- Labels of the second game's objects and directions grouped into the
  bank; resident area of the XL frame kept explicitly. MEDICAL joins the
  compressed XL modules to free the auxiliary storage.
- Validation: 42 XL scripts, including 43 water scenarios on the joystick
  port: reachable or unreachable supplies, large quantities, cancellation,
  drinking four ounces, weather, immersion, rivers/lakes and source
  priority. Eight goal directions checked after grouping the texts.
  Native simulation comparison unchanged after 24 steps; existing medical
  limit of DRINK (`DRINK_FIDELITY=0`) recorded in the audit.

### STATUS: active blade or blade to prepare for CUT BODY (17 October 2026)

- CUT BODY distinguishes BLADE IN USE, BLADE AVAILABLE; USE KNIFE/AXE FIRST
  and NO BLADE HERE; FIND KNIFE/AXE. Holding a tool does not activate it:
  the preview checks the use, the access and the activation cell without
  writing anything.
- An old use indicator on another cell, or for a tool that has become
  unreachable, no longer blocks the automatic preparation. The knife keeps
  priority over the axe; without a tool, the native refusal stays readable.
  Only the real command clears stale indicators, according to its rules.
- Fixed WARM on a cold body: the conversion to a percentage becomes local
  to the medical module, instead of calling ALERTS, which is not loaded.
- The qualitative words for temperature, altitude and terrain join the text
  bank, with their display and the native scratch kept.
- Validation: 41 XL scripts; sixteen blade scenarios on the joystick port,
  navigation and cancellation without mutation, preparation then care at
  0 MIN, return to the same gesture, five qualitative display cases and a
  simulation state identical to the native reference after 24 steps.

### STATUS: splint and fire availability (17 October 2026)

- USE SPLINT shows HERE/NOT HERE: a splint on the ground is reachable only
  on its cell; a carried or worn splint stays available. The preview and
  the command share the same native check, without mutation.
- USE FIRE shows the presence of a lit fire, which is distinct from putting
  the fire to use. HERE does not guarantee it can be used in the rain or in
  the water; the warnings and refusals remain the engine's.
- Neither the splint nor the fire shows a dose counter. The medicines and
  the glasses keep their indications and usage rules.
- Validation: 40 XL scripts, including fifteen presence scenarios on the
  joystick port: positions and coordinates of the splint, arm/leg, fire
  absent, lit, rain, immersion and shelter. Cancellation and navigation
  stay without effect.

### STATUS: readable result and return to the same care (17 October 2026)

- After a care action, the native result stays visible. RETURN CARE finds
  the same ailment and the same gesture again; ESC VIEW lets the player stay
  in the view. A held button neither confirms this step nor repeats the
  care.
- The ailment is found again by identity if the list changes. If it has
  disappeared, a valid neighbour is selected, or the tab if none is left.
  The lamp/blade preparation stays native. If it fails, the care is skipped
  and its refusal stays readable before the return; an encounter stops the
  queue.
- Cancelling a water quantity also finds the gesture again without changing
  the game. The return selection stays out of the save.
- The tab names and a few STATUS labels move into the bank; the 80 bytes of
  the MouseText frame stay reserved. EQUIPMENT is compressed into the
  auxiliary storage to keep the six regions.
- Fixed the text reader crossing a 256-byte boundary: the alignment no
  longer depends on the carry of the length calculation.
- Validation: 39 XL scripts; returns on the joystick port, refusals,
  cancellations, interruptions, held button and 255 texts, including 26
  page boundaries. Return to ProDOS also checked: banks, zero page, bitmap
  and RESET restored.

### STATUS: meaning of the states and care preview (17 October 2026)

- The MEDICAL legend spells out ACTIVE: NEEDS CARE, TREATED: CARE GIVEN and
  PROTECTED: PREVENTION, keeping the marks and the columns.
- With an ailment selected, row 22 shows the native duration of the chosen
  gesture and its conditions: splint, water, fire, glasses, blade or light.
  Row 23 keeps all the gestures and their inverse selection.
- The glasses and medicines show HERE/NOT HERE; the medicines show the
  remaining doses, first aid LIT/DARK. Zero doses stays informative: the
  native effects of empty kits are not blocked.
- The gestures and advice share the existing entries of the text bank, with
  no new public ID. Navigation and cancellation do not alter the game; the
  commands and the lamp/blade preparation stay native.
- Validation: 38 XL scripts; 19 care choices on the joystick port,
  durations, signed doses, missing kit and the lamp → first aid chain.

### OBJECTS/EQUIPMENT: figures for capacity refusals (17 October 2026)

- At confirmation, left/right go through the summary of the excesses, then
  WEIGHT, PACK, HANDS and WORN. Each detail gives NEED (extra requirement),
  FREE (free before the transfer) and MISSING (excess after the transfer),
  in OZ or IN3. Simultaneous limits stay in the summary.
- An internal move adds zero weight; a drop asks for no extra room. An
  overload already present stays visible in MISSING. Container
  prerequisites and arithmetic overflows keep their priority message.
  Cancelling returns to the summary; confirming from a detail runs the same
  native command.
- The medical names and three OPTIONS descriptions are grouped into the
  text bank to free the dialogue's memory, without changing their display.
- Validation: 37 XL scripts, 16-bit figures, cumulative and atomic
  refusals, accepted transfers, cancellation, detail from EQUIPMENT and page
  texts.

### OBJECTS: explicit carryable maximum (17 October 2026)

- PACK of the first game's local provisions and GET WATER show FIT, the
  maximum compatible with the weight, the volumes and the canteen. Right
  inserts this level into the doubling, then lets the player continue to
  ALL. Opening keeps ALL exact; no automatic reduction of the transfer.
- FIT 0 signals that no unit fits; positive quantities stay reachable to
  see the native refusal. Eating, drinking and the wild piles keep their
  quantity rules.
- Calculation without changing the game, in at most sixteen projections,
  even for a supply of 65,535 units. The water preview now ignores the
  canteen positions that are not carried, avoiding an invalid load index.
  NEED/WT numbers that exceed the 16-bit calculation are hidden; FIT stays
  readable.
- Validation: 36 XL scripts, including sixteen FIT scenarios on the
  joystick port, refusals, cancellations, volume/weight/canteen limits and
  a transfer of 63,669 units; code integrity check with the canteen absent
  or suspended.

### OBJECTS/EQUIPMENT: containers ready before a transfer (17 October 2026)

- PACK explains the backpack that is not carried for equipment, provisions
  and crafted objects. DROP explains the bag that is still occupied or the
  canteen that holds water, with the native remedy before confirmation.
- Messages and remedies fit on one line, keeping the confirmation commands
  visible. Cancelling stays without effect; the native command decides on
  confirmation. The wild piles keep their distinct rule.
- The joystick run checks the refusals, then really empties the canteen and
  the bag with the OBJECTS actions before dropping them. Same warning in
  EQUIPMENT, with the selection kept.
- Fixed the line breaks of the five STATUS gauges recently moved into the
  bank: HEALTH/ENERGY/HUNGER/THIRST/BODY get their rows back. The text
  dictionary now has its own index, without shrinking when labels are
  added; no game state added.
- Validation: `make test-xl`, 35 scripts, including the 254 texts compared
  byte for byte after native decoding, compiler limits and 41 USE choices
  kept. ProDOS checks, exit and restart also verified.

### OBJECTS/EQUIPMENT: precise sources and canteen required (17 October 2026)

- FROM now distinguishes LOCAL, LOCAL HUNG, PACK, HANDS, WORN and CANTEEN.
  The first game's provisions stay in PACK, even with an independent pile on
  the ground; crafted objects follow their own position. The wild piles and
  hides keep their native source CARRIED.
- GET WATER advises carrying a canteen before confirmation if it is on the
  ground, suspended or absent. A carried canteen keeps the destination
  CANTEEN/PACK or CANTEEN/HANDS and its exact free room.
- Same source in EQUIPMENT; preview and cancellation stay without effect.
  The native GET rules and the other uses of the canteen are kept.
- Validation: `make test-xl`, 33 scripts; new run on the joystick port
  checking sources, action changes, cancellations, native refusals without
  mutation and actual collection. LOCAL HUNG checked with the whole bag.

### OBJECTS/EQUIPMENT: weight change before a transfer (17 October 2026)

- The dialogue adds WT with the change in carried weight: positive on
  pickup, negative on drop, zero for a move between PACK, HANDS and
  clothes. It keeps the required volume and the remaining room or
  simultaneous excesses, before confirmation.
- Water: the weight counts the transferred ounces only once, with the
  canteen in PACK or in hand. LOWER FOOD uses the aggregated weight of the
  whole bag. A calculation overflow does not produce a misleading weight.
- The preview stays without effect; accepting runs the native transfer,
  refusing or cancelling preserves supplies and clock. Care, TASTE and USE
  keep their own indications, with no transfer forecast.
- Validation: `make test-xl`, 32 scripts; new joystick run comparing
  forecast and real load, checking the weight/HANDS and weight/PACK
  excesses, and an extended preview of a suspended bag. Targeted checks
  pass on ±40,000 ounces and cancellation in EQUIPMENT.

### OBJECTS/EQUIPMENT: instruments and orientation aid (17 October 2026)

- USE MAP/COMPASS/WATCH/ALTIMETER/CHART explains the result before
  confirmation: TOPO, magnetic aid, watch aid, simply taking it in hand or
  refusal of the star chart. Accepted uses take no time.
- The compass needs no light. The other instruments accept AM/PM, and
  dawn/dusk under a clear sky; the lamp does not lift their native night
  refusal. A refusal also announces that the previous compass/watch is
  deactivated, keeping the shadow stick.
- The preview and the cancellation have no effect on these aids. The
  dialogue reuses the lists' scratch while they are closed, with no new
  resident state and no change to SAVE.
- Validation: `make test-xl`, 31 scripts; 75 preview combinations with the
  joystick, native activations/refusals, return TOPO → OBJECTS and
  EQUIPMENT.

### OBJECTS/EQUIPMENT: lighting and magnifying glass (17 October 2026)

- USE FLASHLIGHT shows the available or exhausted charge before
  confirmation, with one use consumed and zero minutes. The signed counters
  and the activation of the last use keep their native effects.
- USE MAGNF GLASS explains the need to leave the shelter, of daylight and
  of a clear sky. Otherwise, the dialogue announces the 30° solar threshold,
  the 15 minutes and that no fire is produced. No READY is inferred from
  the rounded solar cache; the exact angle is still checked by USE.
- Same preview in both pages, without changing supplies, clock or
  preparation state; return to the selected object after cancellation.
- Validation: `make test-xl` (30 scripts) and `tests/test_camp.py`; new
  joystick run covering empty/negative/257/last-use batteries,
  shelter/night/clouds/rain, low/high Sun and EQUIPMENT.

### OBJECTS/EQUIPMENT: preparing the stove and the matches (17 October 2026)

- USE STOVE distinguishes inactive fuel, missing ignition and a ready
  device; a fire that is merely lit does not replace USE FIRE. Setting up
  announces 30 minutes if the stove is carried, zero if it is on the ground.
- USE MATCHES announces water, rain, wind of at least 41 mph without
  activated fuel, and exhausted matches; use in a shelter stays a native
  warning, with no extra ban.
- USE FUEL shows the available or exhausted fuel; the preview consumes
  nothing. The joystick sequence USE FUEL → USE MATCHES → USE STOVE is
  checked with its native supplies, positions and durations.
- Dialogue verbs and destinations moved into the text bank, resident
  decimal table reused and cell query shared to clear room for the check
  with no new resident or saved state.
- Validation: `make test-xl`, 29 scripts pass, and `tests/test_camp.py`
  passes. Targeted EQUIPMENT checks and a real transfer of 257 ounces pass;
  full joystick run and 163 reference variables kept.

### OBJECTS/EQUIPMENT: USE prerequisites before confirmation (17 October 2026)

- USE TRAP/FISHNG GEAR shows the missing or ready bait, and recalls that
  CATCH prepares the bait first. USE FRSTAID KIT shows the missing or
  available light and offers USE FLASHLIGHT if needed.
- Indication visible when choosing the action and at confirmation,
  recomputed from the same indicators as the engine. Changing the action
  removes the indication; cancelling prepares nothing and spends neither a
  dose nor time.
- The native refusals stay executable and unchanged. Test on the joystick
  port in OBJECTS and EQUIPMENT, bait absent/ready and light absent/ready,
  then real use of the lamp and of the kit (one dose, 30 minutes).
- Dialogue labels placed in the text bank; no resident or saved state
  added.
- Validation: `make test-xl`, 28 scripts pass; targeted prerequisite test
  passes with native consumption of the lamp and the kit. Full joystick run
  and 163 reference variables kept.

### OBJECTS/EQUIPMENT: actions by position (17 October 2026)

- Removed PACK on equipment already in PACK, CARRY on equipment already in
  hand and WEAR on what is already worn. PACK BACKPACK is always removed:
  the bag cannot contain itself.
- The separate LOCAL/CARRIED piles and water keep their actions per source;
  crafted weapons and the splint use their native position. USE stays
  reachable, even on a held or active object: possession, preparation and
  activation stay distinct.
- Recoverable prerequisites stay checked by the engine: for example USE
  TRAP without bait keeps its precise refusal, without mutation, and its
  selection. A proposed action is always chosen explicitly, then confirmed.
- Test on the joystick port: worn/stowed/held positions, bag on the ground
  or in hand, canteen, medicines, crafted objects, double piles and water.
  Going through the actions changes no persistent state range.
- EQUIPMENT recomputes the choices after PACK/USE/CARRY and keeps the
  selected object with its native activation. Validation: `make test-xl`,
  27 scripts pass; extended targeted EQUIPMENT test passes, full run and
  comparison of the 163 simulation variables kept.

### OBJECTS: quick transfer quantities (17 October 2026)

- Right doubles the quantity up to the exact whole supply, then goes back to
  1; left goes back to 1 and up/down keep the unit adjustment. The transfer
  always starts on the whole supply, with confirmation.
- 16-bit doubling without wrapping to zero on overflow; water, provisions
  and piles use the supply of their source. EAT/DRINK keep their protection
  against ALL; care and indivisible objects stay unchanged.
- Joystick test on 1, 3, 14, 257, 32769 and 65535 ounces: selection,
  cycle, cancellation without mutation, real transfer of five ounces and a
  drop of four ounces from CARRIED, exact filling of the canteen,
  consumption without doubling. The FREE labels move into the text bank to
  make room for the shortcut with no resident byte added.
- Validation: `make test-xl`, 26 scripts pass, and a targeted quantity test
  with PACK, DROP, GET WATER and EAT/DRINK; full integrated run and
  comparison of the 163 simulation variables kept.

### Joystick run: care, saves and score (17 October 2026)

- The integrated run continues after the meal: FLAGYL and oxygen from
  OBJECTS, one dose per use, native duration and cancellation without
  mutation.
- MENU with the joystick: cancel SAVE/RESTORE, refuse an empty slot, save
  as game 2, keep the old save on replacement, then restore the persistent
  state ranges after dropping the knife. The same restore is checked after
  an exit and a restart.
- QUIT cancelled then confirmed; zero score not ranked, return to the menu,
  real walk after putting out the fire, ranked score, name AB entered with
  the directions and result read back from disk when the loader restarts.
- The WALK refusal while the fire burns keeps the state; DOUSE unblocks
  walking. The native care actions take the medicine in hand; when it
  leaves LOCAL, OBJECTS keeps a valid neighbouring selection.
- This lot extends the checks and the documentation; no change to the
  engine, the SAVE format or the XL image.
- Validation: `make test-xl`, 25 scripts pass, including the extended run
  and the 163 reference variables identical over 24 steps.

### Joystick run: crafting, hunting and meal (17 October 2026)

- COOK deadlock fixed: the decimal hours question accepts up/down to set
  exactly 0 to 1499 minutes, then confirm or cancel. The displayed unit
  changes explicitly; decimal entry and the native limits stay available.
- New XL run driven by the axes and buttons of the joystick port, from
  startup: make a spear, refuse to take it when overloaded, drop the parka,
  take then activate the spear in EQUIPMENT, prepare CATCH, capture, make a
  fire, cook and eat through OBJECTS.
- Forest map, encounter and capture draw fixed for this test; no command
  typed. Cancelling the cooking without supply, time or draw changed;
  30-minute duration and consumption of one ounce checked.
- Validation: `make test-xl` (25 scripts), `tests/test_forage.py` and the
  joystick run with 0/1499-minute bounds pass; 163 variables identical to
  the reference over the 24 comparison steps.

### OBJECTS: preview of recovering the whole bag (16 October 2026)

- LOWER FOOD shows the required PACK volume and the free capacities after
  recovering all the suspended items. FREE AFTER and FREE NOW explicitly
  distinguish the preview from the current capacity.
- Calculation without mutating the state: canteen/water counted once, the
  bag's volume excluded from its own capacity, suspended provisions kept
  separate from the ground.
- Weight and PACK excesses visible before confirmation; arithmetic overflow
  flagged without a truncated quantity. Atomic native refusal kept.
- Validation: `make test-xl`, 24 scripts pass; preview compared with the
  load after recovery, canteen held/stowed and refusal without mutation.

### OBJECTS: tasting without consuming (16 October 2026)

- TASTE on the provisions and wild foods of the selected source, with
  confirmation, without a quantity or ALL, with no supply consumed and no
  time elapsed. Water keeps DRINK; equipment and medicines are excluded.
- Return to the same object and the same side with the native sensory
  result; cancellation without effect. LOCAL and CARRIED tastes are
  distinct.
- Dialogue helps placed in the text bank, command name kept in the modal
  scratch. The TREE window gets 78 free bytes back.
- Validation: `make test-xl`, 23 scripts pass; LOCAL/CARRIED tastes,
  cancellation, no consumption, no elapsed time and no draw checked.

### OBJECTS: care and suspended bag (16 October 2026)

- Medicines: single use with dose count and native duration; EAT for oral
  medicines, USE for oxygen. No ALL and no ounce quantity for a treatment.
  Simulation rules kept.
- LOCAL HUNG opens the LOWER FOOD confirmation from the bag or its
  contents: full recovery, destination CARRIED, zero minutes and native load
  check; cancellation and refusal without loss of supply.
- Navigation fixed on provisions present on the ground and in the suspended
  bag; Escape no longer goes through a non-existent quantity step for
  indivisible equipment and care.
- Command/confirmation routines redistributed between MEDVIEW and STATUS;
  load multiplication in STATX, resident medical duration shared. The
  current test maps now use the XL edition.
- Validation: `make test-xl`, 22 scripts pass; 163 variables identical to
  the reference after 24 steps, cancellation and refusal tests included.

### EQUIPMENT, quantified water and CRAFT refusals (16 October 2026)

- Seventh tab EQUIPMENT: WORN, HANDS, IN USE and available PACK, real state
  of each object, hand volume and free capacities.
- Actions from the equipment with confirmation and return to the same
  object; owning or holding a tool does not simulate its activation.
  Preparation of the trap, fishing and bait read from the simulation.
- GET/DROP WATER quantified from OBJECTS, required volume and destination
  of the container; atomic refusal if the canteen's 64 OZ are exceeded.
- Preview of the required volume and of the remaining WEAR room. USE
  filtered by the recognised actions. Refusals for crafted objects detail
  weight and PACK/HANDS/WEAR volume separately, with the required quantity
  and the free room.
- Validation: `make test-xl` (21 scripts), plus graphics memory; comparison of 163 simulation variables after
  24 steps identical to the reference. Tests in an emulator; a real
  joystick is still to be checked.
- Directory of 34 modules; EQUIPMENT shares the $5800 window, the TREE
  commands join ORIENT, TAKE OZ joins OUTDOOR. No new saved state and no
  change to the native load rules.

### XL only and OBJECTS transactions (16 October 2026)

- Development of the 140 KB edition stopped at the user's request. Build,
  launch and the current test suite target NeoWildernessXL.
- Enter on an object opens its action menu, then a quantity for provisions
  and piles, then a confirmation. Escape goes back without mutation.
- Partial PACK/CARRY/DROP transfers, 16-bit whole quantities and OZ, atomic
  validation of the units, the supply and indivisible equipment.
- EAT uses the selected source; a meal starts at one ounce and does not
  offer ALL. The actions reload OBJECTS while keeping its context.
- Load preview for the usual transfers, remaining capacities and exact
  excess; the cases that are not projected show the current capacity. The
  special cases still to be done are in the TODO and in MENUS § 11.


### Removal of TMAP and the archipelago (16 October 2026)

- Removal requested by the user: the T entry and its navigation, the
  generator, the archipelago manifest, the NEOWILD.TMP/NEOWILD.SCN files and
  their sources, and the dedicated tools, tests and documentation.
- Removed the specific seabed and the identity checks of generated terrain
  on resume. The six classic scenarios remain available.
- XL rebuilt: 379/1600 blocks used, i.e. 14 blocks recovered; the five save
  slots are kept.
- Validation: six-region menu, joystick, disk contents, SAVE/RESTORE,
  EQUIPMENT, OBJECTS, DHGR rendering and simulation comparison.

### Shared navigation: first lot of the approved audit (16 October 2026)

- Joystick driver in `src/ui_event.s`: simultaneous reading of the axes,
  dead zone, directional repeat, button 0 confirms and button 1 goes back;
  buttons on edge, typing a command protected from the axes. The pages,
  the grid and the usual waits share this input.
- Start menu: choice and level with the directions, then confirm; the
  shortcuts and the Sierra/level 4 default remain. The custom preparation
  questions and the initial /RAM dialogue are still to finish.
- P/G for foods split between ground and bag, Y/N of QUIT, save
  replacement and water search, Y/N and E/W of orientation: choice with the
  directions then confirm; N stays the default for confirmations.
- The numeric prompts accept up/down (integers), in addition to typed
  numbers; SAVE/RESTORE becomes reachable with the directions. WALK/SWIM
  accepts the back button at a step boundary, without reading the axes.
- MAP: confirm enters exploration, directions scroll, confirm recentres,
  back leaves this mode, then returns to the view. The I/J/K/L/C keys and
  the MAP/TOPO navigation are kept outside exploration.
- Score: up/down choose the last letter, right adds an A to edit, left
  erases, confirm records the name, back cancels. Typed letters and the
  other characters of the name are still recognised.
- Room: map row pointers computed, ounce consumption in ITEMS, resident
  number reader moved; new temporary placement of the loader. SIM
  compressed on 140 KB, ORIENT in its RAM storage; the body/weather
  constants are resident and saved. The five saves stay on both volumes;
  the build is refused if a shipped edition loses them. MEMORY.md § 38
  details the placement.
- `tests/test_navigation.py` covers both editions with real game port
  inputs and the blocking dialogues, the map and the score name. The four
  OBJECTS changes, the return after care and the CRAFT/CATCH extensions
  stay in the approved TODO; this lot does not declare them done.


### OBJECTS: remembered selections and volume gauges (16 October 2026)

- The chosen side, the selections of both lists and the scrolling are
  restored after a return to the view, another page or a simulation.
  The selection follows the object's identity if lines are added or removed
  before it; if the object disappears, the cursor picks a neighbour.
  Arriving keeps the focus on the tab; Enter activates the lists.
- LOAD adds two six-cell gauges for the volume used in PACK and HANDS, with
  the exact free volume in IN3. Total weight, walking slowdown and free
  clothing volume stay displayed.
- Two BSS bytes keep the identities, without changing the saves. The
  calculations and small page routines share MEDVIEW, loaded when OBJECTS
  opens; its XL footer moves to $5FC0.


### Page layout and navigation (16 October 2026)

- OBJECTS splits HANDS and PACK into two post-its on XL. The lists gain a
  line (twelve visible entries); CARRYING and LOAD move down one line.
- On opening, the focus stays on the tab: down returns to the view, Enter
  activates the lists, then the arrows go through the objects.
- Up from the view finds the last top page opened again, even after a
  simulation command. The STATUS command always opens STATUS.
- Removed S/O/R/H at the top of the pages and the bar after DRINK in the
  grid. TOPO's distance scale and its digit 4 move to the bottom left.


### CATCH: duration chosen in the grid (16 October 2026)

- After GAME or FISH, CATCH offers `10 MIN`, `20 MIN`, `30 MIN`, `1 H`,
  `2 H`, `4 H`, `8 H`. The queue prepares the bait and the trap or the
  fishing gear, then types for example `CATCH FISH 30 MIN`, with no numeric
  prompt. Escape cancels the choice; a refused prerequisite or a new
  encounter stops the queue as before.
- Direct entry also accepts CATCH with a whole duration in H or MIN,
  strictly below 25 h. CATCH alone with its target keeps the original
  question, fractions of an hour included; the rules and draws are
  unchanged.
- No resident state added: the last slot of the queue keeps the duration
  choice (CATCH uses three steps at most). The stars' time module is now
  compressed in storage (45 bytes gained) to make the addition fit; the
  star rendering is checked on both editions.
- `test_grid_catch.py` compares the grid, the command line and the decimal
  prompt on both editions, with refusal, cancellation and interruption. The
  grid, FORAGE, simulation reference, stars, editions and compression tests
  pass. Images rebuilt: **280/280** and **369/1600** blocks;
  [MEMORY.md](docs/MEMORY.md) § 35.

### Last ounce reachable from the grid (16 October 2026)

- EAT, DRINK and BOIL now offer `1 OZ`, before 2, 4, 8, 12, 16, 24, 32 and
  48 oz. A one-ounce supply can be eaten, drunk or boiled with the arrows
  and RETURN alone; the grid used to offer 2 oz, which exceeded that supply
  and caused a refusal.
- The supply and drinking caps are still applied; TASTE stays EAT's first
  choice. Single-choice lists keep their automatic selection; cancellations
  do not advance time.
- `test_grid_play.py` compares the last one-ounce meals, drinks and boils
  with the typed commands on both editions, with no numeric prompt.
  `test_menu_bar.py`, `test_camp.py`, `test_forage.py` and
  `test_reference_state.py` check the other portions and the simulation.
  Volumes unchanged: 279 and 368 blocks; [MEMORY.md](docs/MEMORY.md) § 34.

### Thermal protection removed with the garment (16 October 2026)

- On a native map, PACK, GET, TAKE and CARRY of a worn garment immediately
  update the heat losses and the insulation, like DROP. The grid's WEAR
  toggle (which types PACK) benefits as well. Previously, the parka was
  still counted in the protection until the next thermal calculation.
- The calculation happens after the transfer is accepted: insufficient bag
  or hand capacity keeps the garment worn and its protection. The message
  keeps the right object and the right destination after the calculation.
- `test_items.py` checks the five destinations/verbs on both editions, the
  rounded losses of the Sierra (torso 14 → 47, insulation 37 → 48), the
  atomic refusals and that no time, disk read or DHGR bank change occurs.
  Additional checks: `test_reference_state.py`, `test_thermal.py`,
  `test_menu_bar.py`, `test_load.py`, `test_objects.py`. Both disks stay
  at 279 and 368 blocks; [MEMORY.md](docs/MEMORY.md) § 33.

### Agreeing messages and incomplete camp commands (16 October 2026)

- The numbers in the results of rest, wait, movement, meal, drink, water
  collection and magnetic heading agree with their unit: `1 HOUR`,
  `1 MINUTE`, `1 OUNCE`, `1 DEGREE`; the other numbers keep the plural.
  The `%` marker takes both bytes of the number into account, including
  257.
- MAKE, BUILD, USE, BOIL, DOUSE and STOP without an object show
  `NAME AN ITEM` with examples, including `MAKE FIRE`, without consuming
  time or supplies. The unknown-verb message keeps the word and
  `TYPE HELP` in less text.
- Checks: `test_feedback.py` (both editions, limit values, state and view
  kept), `test_input.py`, `test_sleep.py`, `test_transitions.py`,
  `test_reference_state.py` and `test_camp.py`. Both disks stay at 279 and
  368 blocks; [MEMORY.md](docs/MEMORY.md) § 32.

### Landscape kept during the simulation (16 October 2026)

- Both editions keep the last full view during the REST, SLEEP and WAIT
  calculations and the SIM loads. The text curtain only starts at the
  redraw, to hide incomplete images; the messages and the cursor are kept.
- No disk access or rule change added. The reference check keeps the 163
  variables (1,324 bytes) over 24 steps.
- Validation: `test_transitions.py` (both editions), `test_sleep.py`,
  `test_reference_state.py`, `test_screen_returns.py`, `test_camp.py` and
  `test_interface.py`. `.po` images rebuilt: 279 and 368 blocks.

### OBJECTS, transfer page; weight of the second game; GET without a question

User requests of 15 October 2026, **both editions** (MouseText post-its on
XL, plain text on 140 KB):

- **OBJECTS** ([MENUS.md](docs/MENUS.md) § 5.1): on the left what is on the
  ground of the cell (LOCAL, then LOCAL HUNG), on the right what is carried
  (HANDS, PACK, WORN), each object with its weight (the remedies with their
  USES), eleven per side, `MORE` under a list that continues. Left and right
  change side, up and down change object; RETURN sends it to the other side
  (`PACK x`, `GET WATER`, `CARRY BACKPACK`/`CANTEEN`; `DROP x` from the
  right), H takes it in hand (`CARRY x`): the command is typed as on the
  keyboard (time, rules and refusals of the original), the page comes back
  with the game's answer (rows 20-22) and the cursor in the same place;
  rows 20-21 say what RETURN and H type. A transfer takes ≈ 1.1 s (XL) to
  1.2 s (140 KB). CARRYING stays; LOAD shows the gauge of the carried
  weight up to the limit (772/815 OZ at the start), the walking slowdown
  (`WALK TIME +28%`) and the free volumes. The groups, their pages and the
  keys 1-5, N, B disappear; the shelters are no longer among the objects
  (the CRAFT page shows them).
- **Load thresholds measured on the ROM** (`tools/re_load_probe.py`):
  walking slows down in proportion to the weight from the first pound
  (100 × pounds / (body + 2) %, T08/S07, already so in TRAVEL); the only
  threshold is the limit (`$4BFA`, 815 oz), beyond which any object taken
  from the ground is refused (msg 7): that is the end of the gauge.
- **The second game has weight** ([CRAFT.md](docs/CRAFT.md) § 8.2): bow and
  spear 50 oz, club and rock 100, splint 50 (and their volumes) count in the
  load, the walking and the effort; taken from the ground beyond the
  limits, they are refused ("TOO MUCH WEIGHT OR VOLUME."): GET ROCK at the
  start is refused, as in the original.
- **GET without a question**: **intended deviation, decision of 15 October
  2026** ([FORAGE.md](docs/FORAGE.md) § 17.3, [CAMP.md](docs/CAMP.md) § 3).
  PACK of a lot 4 pile (the grid's GET: INSECTS, PLANTS…) takes the whole
  pile from the ground; GET from a water source fills the canteen with at
  most what the source, the canteen and the remaining weight allow; the
  message gives the ounces taken ("YOU TOOK n OUNCES."). The probe of the
  original replays the whole pile where the original asks.
- **Fixes**: PACK and DROP of a pile copy the record and the counter of the
  source pile only onto an empty pile (measured on the ROM); USE
  BOW/SPEAR/CLUB/ROCK left the screen in text (the curtain) until the next
  command: the view comes back; DROP of the `2QT CANTEEN` from the grid
  answered "INVALID VALUE OR UNIT" (the digit in the name): the typed name
  is `CANTEEN`.
- **Room** ([MEMORY.md](docs/MEMORY.md) § 30): saved games no longer keep
  the constant weights and volumes of the objects: 1,509 bytes, 4 blocks
  instead of 5 each ([SAVE.md](docs/SAVE.md) § 5); 140 KB: NEOWILD.DAT
  70,628 → 71,915 bytes (142 blocks), CRAFT 9 blocks, GRID compressed in the
  storage (≈ 0.08 s more per grid choice, as on XL), volume **279/280**
  blocks with the five games (280/280 before); XL 368 blocks, STATUS 16
  blocks; not one more resident byte (WILDGAME 11 → 6, WILDERNESS 2 → 22).

### STATUS, MENU and OPTIONS rearranged; severity of the ailments

User requests of 15 October 2026, **both editions** (the post-it on XL, the
same content in plain text on 140 KB; focus and keys unchanged):

- **STATUS**: CONDITIONS moves to the right under LOCAL (rows 11-14, two
  ailments per row); CONDITION takes the full height on the left (2-14), an
  empty row between HEALTH, ENERGY, HUNGER, THIRST and BODY, and the
  percentage comes back after each gauge (`90% OKAY`). The LOCAL situation
  fits in rows 7-9. MEDICAL stays at the bottom across the full width.
- **MEDICAL**: the ailment percentages are shown as severity, `100 − x`: a
  healthy body reads 0 % everywhere (display only: simulation and saves
  unchanged).
- **MENU**: RANGERS first, then SAVE and RESTORE in a single post-it
  (SAVE / RESTORE), then QUIT.
- **OPTIONS**: a single large post-it, one option per row, the state aligned
  (`[X]` / `[ ]`; MouseText check mark on XL; wildlife frequency in
  digits), the focus line in inverse; on XL a sentence describes the chosen
  option at the bottom of the post-it (no room in the 140 KB STATUS
  module). Labels: `PLAYER ON TOPO`, `MAP PAGE`.

Room: STATUS module 6,306 → 6,396 bytes (`$9600-$AEFB`, 5 free below
`$AF00`); 140 KB: NEOWILD.DAT 70,560 → 70,628 bytes, still 280/280 blocks
with the five games; not one more resident byte (the resident `pg_lines` is
no longer used). XL: the STATX tail keeps the options sentence; `mt_skip`,
`pg_lines_x`, `pg_mark_x` removed.

### HERE becomes LOCAL in the labels

User request of 15 October 2026, **both editions**: the displayed labels
that said HERE say LOCAL. CARRYING (OBJECTS): `CARRIED / LOCAL / IN REACH`;
bottom supply line: `FOOD n WATER n LOCAL f/w OZ` (39 columns with four
digits everywhere); OBJECTS groups `4 LOCAL GROUND` and `5 LOCAL HUNG`
(instead of `GROUND HERE`, `HUNG HERE`). The message sentences (`NOT ACCESSIBLE
HERE.`, `STOP HERE. THE MAP ENDS AHEAD.`…) and the typed commands do not
change. Room: the extra byte of MENUSWAP (full) is taken back by a
`BIT abs` in `sum_ground`; not one more resident byte; 140 KB still 280/280
blocks with the five games.

### Top pages restructured, post-its on NeoWildernessXL

User requests of 15 October 2026. **Both editions**: the tabs become
STATUS | OBJECTS | CRAFT | HELP | OPTIONS | MENU. The MEDICAL page disappears:
STATUS shows at the bottom (rows 15-20) the thirteen ailments and altitude
sickness in three columns (percentage, care mark, legend) and carries the
care focus (down on an active ailment, gestures on row 23, RETURN types
them; the grid's CARE opens there); M opens STATUS. INVENTORY is called
OBJECTS (tab, letter O in addition to I) and receives CARRYING (food and
water carried, here, within reach; 33 objects per page). RANGERS (distance,
direction, JOURNEY DONE and its gauge) moves into MENU. HERE and the status
line become LOCAL (date, time, air, wind chill, sky, wind, altitude, ground,
situation). The typed commands do not change. **XL only**: each block of
each page is a post-it (title in inverse on the corner, `_` stroke, bars,
bottom stroke), drawn by the output itself from a table per page (one
shared routine, `src/mt_pages.s`), differential; MENU and OPTIONS one
post-it per line, HELP one per block, CRAFT one per group and one for the
recipe, the end-score detail in a post-it. The tab letters no longer touch
the edge of the screen (the `H` of `S/M/I/R/H` was cut there). XL's STATUS
is read from NEOWILD.BLK (≈ 0.13 s instead of ≈ 0.39 s of LZ decoding); the
frames cost ≈ 0.11 s per page drawing. Room: 140 KB, NEOWILD.DAT
70,587 → 70,561 bytes (95 before one more block), STATUS 6,384 → 6,306;
XL, trunk room 241 → 6,114, 372 blocks; not one more resident byte
([MEMORY.md](docs/MEMORY.md) § 29, [MENUS.md](docs/MENUS.md) § 5, § 9).

### Rotation with an animal: the view scrolls, the animal redrawn alone

User decision of 15 October 2026: optimise the rotation. With an animal on
the cell, an arrow or LOOK R / L redrew the whole view to keep the animal
centred. Now, before drawing it, OUTDOOR (`module_animal_bg`, `ab_copy`)
keeps the background under its columns (rows 16 to 175, two banks) in the
auxiliary language card, bank 1 (`$D000`, the TOPO snapshot area, inherited
maps); the rotation (`turn_view` → `animal_unpan`) puts it back, redoes the
site scene (`module_project`), scrolls the view and draws only the new
columns, then the animal (`animal_view`), on its own columns only. Pixels
identical to the full redraw (`tools/dhgr_ref.py`). TOPO takes the area:
the next rotation redraws; a native map (atlas) always redraws.
Measurements, XL, the bear (right / left arrow, LOOK R / L):
4.55 / 4.16 / 4.95 / 4.20 → **2.38 / 1.99 / 3.35 / 2.59 million
cycles** (without an animal 1.25 / 0.85 / 2.33 / 1.57); 52 rotations of
`test_pan`: 4.17 → 2.37 million on average (−43 %), +86 % over the same
rotation without an animal (+10 % target not reached: see
[MEMORY.md](docs/MEMORY.md) § 28.4). Fire on the cell and night: same
costs. Fix on the way: `animal_fire` left `proj_width` at 28.
Room: PROJECT +35 bytes (compacted calculation of `project_offset`),
OUTDOOR +107, resident +21 (WILDGAME 2 free, WILDERNESS 2, WILDLO 0); the
grid module (32) is LZ-compressed in the storage of the six packs (XL,
comparison disks): XL trunk room 150 → 241, about 0.1 s more per choice in
the grid; 140 KB: NEOWILD.DAT 70,587 bytes (69 before one more block),
280 / 280 blocks, five games. Tests: `test_animal_view.py` (path taken and
pixels at each rotation: site, fire on both sides, DOUSE, TOPO, night,
sunset, crocodile clipped and at negative left, native map), `test_pan.py`
(`scene_drawn` = `$83`, at least −40 % on the forced redraw).

### XL: ALTCHARSET at startup; up arrow for TOPO in the footers

User report of 15 October 2026: at startup, the up arrow led to STATUS
without the MouseText characters. The loader set ALTCHARSET before the
Monitor's SETVID, INIT and HOME; the IIc's SETVID (`$FE93`, which lands on
a `STA $C00E`) clears it: STATUS and the grid showed letters until the
CRAFT page. `start` (`src/boot.s`) sets it again on XL after all the calls
to the Monitor (140 KB: primary set, as before). Not reproducible on the
tests' emulated enhanced IIe: `tests/test_altcharset.py` plays the IIc's
SETVID with a write to `$C00E` at the start menu, then checks `$C01E` and
the MouseText codes of STATUS at startup, after SAVE / RESTORE, after QUIT
and a new journey, after the hall of fame; 140 KB: primary set, no
MouseText code. a2shot captures reviewed: STATUS, MEDICAL, INVENTORY,
CRAFT, HELP, OPTIONS, MENU, grid, curtain (hourglass), QUIT prompt, score.
XL footers: `↑ TOPO` (MouseText `$4B`) instead of `T TOPO` (STATUS,
MEDICAL, HELP, INVENTORY; T still works); 140 KB keeps `T TOPO`
("UP: TOPO" would have grown its image) ([MENUS.md](docs/MENUS.md)
§ 9.2).

### The present animal always visible, except in shelters

User rule of 15 October 2026: "when an animal is there, we must see its
sprite except in our shelters"; its presence guides the player's choices.
Both editions ([LOOK_UPDOWN.md](docs/LOOK_UPDOWN.md) § 4). The cell's
animal is no longer the only sprite of the scene: PROJECT (`module_animal`)
draws it **after the view**, on top of everything, like the original's
second slot (`$0D80`):

- **site and animal on the same cell**: both, the site first (the wreck of
  the starting cell, the shelter, the post, the crafted shelters), the
  animal in front;
- **facing the player** whatever the heading: centred after LOOK R, L,
  BACK, N and the arrows (no more arrival bearing: `animal_bearing`
  removed); a rotation scrolls the view (see below);
- **campfire** on the cell: never any overlap; fire left of centre (lit
  facing the heading included): the animal on its right, clipped at the
  right edge (the crocodile keeps 56 of its 72 columns); fire on the right:
  the animal on its left ([CAMP.md](docs/CAMP.md) § 8);
- **without light** (night without a full Moon, "NOT ENOUGH LIGHT." still;
  sunset and civil twilight in silhouette; nautical twilight and weak
  moonlit night): a night silhouette, dark blue and grey (at sunset and in
  civil twilight too: choice confirmed by the user);
- **ENTER SHELTER** keeps the animal (D4: risk × 0.1, ATTACK and SCARE
  allowed; [CRAFT.md](docs/CRAFT.md) § 3.4); no view in a shelter; EXIT
  shows it in front of the shelter;
- generated map: the record is cleared at the first step off the cell
  (`fauna_age`, checked, no code); native map: moving away remains the
  animal's reaction;
- **intended deviations** ([ORIGINAL_GAP.md](docs/ORIGINAL_GAP.md) D6): the
  rattlesnake and the ground animals are seen at eye level; LOOK UP stays
  without a sprite (faithful), the only view without the animal outside
  shelters and pages.

Pixel-exact references extended: `tests/scene_ref.py`
(`animal_geometry`), `tools/dhgr_ref.py`, `tools/dhgr_palette.py`
(`Lighting.animal`); new `tests/test_animal_view.py` (site and animal,
each direction, LOOK DOWN and UP, fire and MAKE FIRE, crocodile, night,
sunset, twilights, ENTER/EXIT, start on a generated and a native map);
`test_sprites`, `test_pan`, `test_menu`, `test_fauna_steps`,
`test_moonlight`, `test_journey_resident` follow;
`test_reference_state.py` rebased (scene bookkeeping and projection floats
compared without an animal on the cell). Captures:
`build/animal_site.png`, `animal_look_back.png`, `animal_fire.png`,
`animal_night.png`. Cost: PROJECT +180 bytes; resident −11 (WILDGAME 23
free); SIM −12; the Sierra pack no longer writes its colours or its
patches, identical to the trunk (−391 bytes stored): 140 KB,
NEOWILD.DAT 70,365 bytes (291 before one more block), 280 / 280 blocks,
five games; XL: 369 blocks, trunk room 150. Time: without an animal,
less than 0.1 %; with an animal, VIEW +12 % ([MEMORY.md](docs/MEMORY.md)
§ 27).

### TOPO centred, north arrow on the left; up on the tabs opens TOPO

Two user requests of 15 October 2026, both editions. The 112-pixel TOPO
sheet is centred (x 14..125): the left margin carries the N, the north
arrow and the distance scale (4 miles), the right margin the altitude
scale, its bar reduced from 6 to 4 pixels to keep the strokes and digits
(10 fits up to the last pixel). Colours, contours, markers, legend, MAP on
top and the view snapshot unchanged; the reference `tools/topo_dhgr_ref.py`
(`SHEET_X`) follows to the pixel ([TOPO_DHGR.md](docs/TOPO_DHGR.md) § 3).
In the top pages, the up arrow on the tab row opens TOPO (STATUS, MEDICAL,
INVENTORY, CRAFT, HELP, OPTIONS, MENU; [MENUS.md](docs/MENUS.md) § 5): the
vertical navigation wraps around in both directions. Cost: TOPOGEN
+10 bytes (six blocks, `TOPOBSS` unchanged), STATUS +4, CRAFT +2; 140 KB:
NEOWILD.DAT +2 bytes (24 before one more block), still 280 blocks; XL:
storage and volume unchanged (369 blocks).

### NeoWildernessXL: the pages in MouseText

Plan approved by the user on 15 October 2026, and decision of the same
day: "the 140KB one doesn't need mousetext" ([MENUS.md](docs/MENUS.md)
§ 9, [MEMORY.md](docs/MEMORY.md) § 26). On NeoWildernessXL only:
`ALTCHARSET` raised for the whole game; the top pages under folder tabs
(the shown page in inverse, open onto the page) and above a uniform
footer (`←→ PAGE`, the page's keys in glyphs, `ESC VIEW`); STATUS in
boxes (CONDITION with its gauges in blocks and checkerboards and their
percentages, CONDITIONS, CARRYING, RANGERS, HERE) and a status line
(date, time, sky, wind, air, feels-like); MEDICAL, INVENTORY, OPTIONS and
MENU in boxes, the state of the ailments with the CRAFT glyphs; the CRAFT
page one row lower (its bar no longer crosses the tab row); the grid
cells separated by bars; an hourglass on the curtain of long actions; the
score screen in a window (double title rule, total rule, top-five table
framed). Mechanism: image tails and XL-specific bytes, written by
`build_disk.py` onto copies of the images (`src/mousetext.inc`,
`src/mt_pages.s`); not one resident byte more. The 140 KB image is
unchanged apart from the 19 bytes of the down arrow below. XL: 369 blocks
(+4), 315 bytes of trunk room in the stock.

### Neowilderness: down on TOPO or MAP opens the top pages

Request of 15 October 2026: the down arrow closes TOPO or MAP like the
up arrow, then opens STATUS; vertical navigation wraps around (top pages,
view, grid, maps). Both editions: +19 bytes in SITES; 140 KB NEOWILD.DAT
26 bytes away from one more block.

### Neowilderness: the CRAFT page readable

Mock-up approved by the user on 15 October 2026 ([CRAFT.md](docs/CRAFT.md)
§ 8.6, [MENUS.md](docs/MENUS.md) § 5, [MEMORY.md](docs/MEMORY.md) § 25): on
the left the recipes in three groups (SHELTERS, WEAPONS AND TOOLS,
PROTECTION), each with its state in MouseText (check mark: possible;
inverse X: something is missing; diamond: already made) and the time
MAKE would take here, computed by MAKE's own routine (`cr_minutes`) with
the light, the axe or knife in use and the current health; on the right
the chosen recipe: its effect, each of MAKE's checks in its order, the
time and what it depends on, what slows it down; row 23 says what RETURN
types (`RETURN: MAKE HUT`). `ALTCHARSET` is raised only on this page. The
CRAFT module goes from 6 to 8 blocks of NEOWILD.BLK (MAKE still reads 4):
the 140 KB edition is full (280 blocks out of 280), XL 365 blocks.
`tests/test_craft_page.py`: glyphs, one write per changed cell, states
against the typed MAKE in three places, displayed time = clock advance in
five conditions (17 crafts).

### Neowilderness: the fire moved up three rows

Request of 15 October 2026: the animated fire is drawn at rows 125 to
156 instead of 128 to 159 (`TOP` of `tools/genfire.py`, `FIRE_TOP`);
`fm_setrow` computes the address of any row (125 is in a different HGR
third than 128). +18 bytes in the module, nothing resident
([CAMP.md](docs/CAMP.md) § 8, **Height**).

### Neowilderness: the fire burns until DOUSE, like the original

Decision of 15 October 2026, not committed ([CAMP.md](docs/CAMP.md) § 8;
memory: [MEMORY.md](docs/MEMORY.md) § 24).

- **No more lifetime**: the fire burns until DOUSE FIRE (or STOP
  FIRE), in the dry as in the rain, as in the original, where nothing
  else puts it out (new part `LONG_FIRE` of `tools/re_camp_probe.py`:
  five WAIT 4, from 7:30 to 22:30, rain set before the last two, fire
  lit after each). Removed: `FIRE_LIFE` (180 minutes, twice as fast in
  the rain), `fire_life` (GDATA, saved), `fire_clock`, the message "YOUR
  FIRE HAS BURNED OUT." and the small-flames and embers stages. The rest
  of the animated fire does not change (images, place, cell, WALK
  refused by msg 132).
- **Feeding the fire**: decided, no command (there is nothing to
  maintain); the pending decision in TODO.md is closed (CRAFT.md
  § 8.6).
- **Bytes given back**: WILDGAME 6 → 12 free, SIM 74 → 144 below `$B500`,
  ALERT −28, FIRE module 1,993 → 1,683 bytes (still 4 blocks); trunk
  +101 (XL) / +102 (140 KB); 140 KB NEOWILD.DAT 140 → 139 blocks,
  volume **279 → 278 blocks out of 280**. Saved state 1,701 → 1,700 bytes: a
  game saved before is refused like any other build.
- **Tests**: `tests/test_fire.py` replays `LONG_FIRE` (sky held dry then
  rainy, compared with `build/re_camp/results.json`), checks the absence
  of a message, WALK refused, the same image at the same rate hours
  later, SAVE/RESTORE, then DOUSE.

### Neowilderness: CRAFT page, second set in the grid (lot 3, step 2)

The "recipe book" and the rest of the grid; lot 3 is done
([CRAFT.md](docs/CRAFT.md) § 8.6; memory: [MEMORY.md](docs/MEMORY.md)
§ 23). 15 October 2026, not committed.

- **CRAFT page**, between INVENTORY and HELP in the cycle of top pages
  (tab `CRAFT`, letter R; `S/M/I/R/H, LEFT/RIGHT`): the ten MAKE of the
  original that the port executes (HUT, IGLOO, TRENCH, CLUB, SPEAR, BOW,
  AXE, SPLINT, SUNGLASSES, SUNSCREEN), each with the ingredients that
  CRAFT checks (solid ground, neither wreck nor station, forest, snow,
  rope or fishing kit, clear ground; the splint shortcut), present in
  capitals, missing in lowercase; a recipe impossible here, or already
  made ("(YOU HAVE ONE)"), is greyed out. Same focus as the cursor
  pages: tabs, then up/down from recipe to recipe; RETURN types
  `MAKE x` (keyboard path: time, effort, messages), beep on a greyed
  recipe. Neither a 3 × 3 grid nor an invented recipe; the A3 recipes
  (lot 5) are not there; feeding the fire is not a command of the
  original (nothing added, TODO.md).
- **Page memory**: the tail of the CRAFT module (957 bytes,
  NEOWILD.BLK 4 → 6 blocks); no resident byte: STATUS draws the tabs then
  reads CRAFT, whose RTS of `sim_fetch` enters the page; directory entry
  9 keeps the length of the recipes alone, MAKE still reads 4 blocks.
  Tabs without a separating space (seven pages).
- **Grid**: GET (`GET x`, in hand like the original), DROP and USE
  offer the bow, the spear, the club, the rock and the splint; the KILL
  queue takes `USE BOW` or `USE SPEAR` before the axe, and nothing when a
  crafted weapon (or the rock) is in use. On a land cell, the rock makes
  GET and USE active.
- **Panel**: `ITEMS: INV` for the bow, the spear, the splint, the club
  on the ground here (not the rock).
- **ATTACK without a weapon in use**: the reachable axe or knife are
  still enough, deliberate deviation (decision of 15 October 2026,
  CRAFT.md § 8.2).
- **Memory.** MENUSWAP 9 → 0 (`append_space` moves into GRID), MENUCODE
  15 → 4 (`mn_idx` 32 → 27), SUMMARY window 25 → 1 (alerts as offsets);
  GRID 2,456 → 2,676, STATUS + 36; trunk room 1,277 → 990 (XL),
  1,187 → 900 (140 KB); XL volumes 361 → 363 blocks, 140 KB 277 → 279 out
  of 280.
- **Tests.** `tests/test_craft_page.py` (both editions: the page, the
  verdict of each recipe against the typed MAKE, RETURN = keyboard, the
  grid = keyboard, the ITEMS hint); `test_focus.py`,
  `test_interface.py`, `test_screen_returns.py` (tab row, CRAFT
  read), `test_menu_bar.py` (USE greyed without the rock), `test_boot.py`,
  `test_pack_boot.py`, `test_transfers.py` (`fetch` length of entry 9
  in `layout.json`).

### Neowilderness: crafting, rest of step 1 (lot 3)

The four leftovers of step 1, faithful to the ROM ([CRAFT.md](docs/CRAFT.md)
§ 3.3, § 4.1, § 8.5; memory: [MEMORY.md](docs/MEMORY.md) § 22).
15 October 2026, not committed.

- **Probe.** `tools/re_craft_probe.py` part 3: the T0E/S02 transaction of
  the second set in the real game (41 commands: GET, PACK, CARRY, DROP,
  REMOVE, WEAR, USE, MAKE of the wreck's rock, a bow, a spear, a club, a
  splint; a walk, LOOK BACK and the return). Also read from the ROM: the
  rock placed on each arrival on a land cell (T0D/S00 `$585F`), lost on
  leaving (T0C/S0B), the discovery of left objects (T0A/S00 `$5BD0`), the
  weights of the second set, GET AXE in hand.
- **GET, PACK, CARRY, DROP, REMOVE, WEAR** of the bow, the spear, the
  club, the rock and the splint (ITEMS reads CRAFT): GET and CARRY in
  hand, PACK into the bag, DROP on the cell's ground, WEAR the splint
  (care selector 3, cleared when it leaves the body); "YOU ALREADY HAVE.",
  "SORRY, THAT ITEM IS NOT AVAILABLE." like the original.
- **ROCK.** A rock on the ground at the wreck, then on any land cell as
  long as the player is not carrying one: MAKE ROCK (msg 11 or 21), USE
  ROCK (in hand, in use), GET ROCK; means 17 of KILL and of ATTACK with
  the club.
- **One cell per object left on the ground.** The bow, the spear and the
  splint stay on their cell and are found there again; the club is lost
  on leaving; the shared cell `cr_gx/cr_gy` goes away. SAVE/RESTORE keeps
  them (`craft_cells` in `sv_ranges`).
- **Weapons against animals** (brought forward from lot 11): ATTACK takes
  the original's first means in use (rifle, bow, spear, axe or knife in
  use, club or rock), clears it, and draws with the thresholds of that
  means' record; the region packs write them (`fauna_reactions`
  44 → 76 bytes). With no means in use, the reachable axe or knife as
  before. The rifle carcass cases of `test_forage.py` now take means 21.
- **Hazards igloo.** HAZARDS takes 35 °F in the igloo like THERMAL;
  the room comes from a duplicate table in the MEDICAL module
  (`hz_since_lo/hi` = `injury_since_lo/hi`, 30 bytes given back).
- **EXIT SHELTER** still leaves any shelter: deliberate deviation
  (decision of 15 October 2026, CRAFT.md § 8.2).
- **Memory.** LOWPAGE 2 → 1, WILDLO 4 → 2 (`forage_here` hook),
  WILDERNESS 18 → 12 (`craft_cells`), MEDICAL window 1 → 25; CRAFT
  1,653 → 1,855 bytes (4 blocks); XL volumes 360 → 361 blocks, 140 KB
  276 → 277 out of 280 (NEOWILD.DAT takes the announced block); trunk
  room 1,469 → 1,277 (XL), 1,379 → 1,187 (140 KB).
- **Tests.** `tests/test_craft.py`: parts 1 to 3 against the ROM (USE ROCK
  restored, MAKE ROCK, the transaction command by command), part 4:
  real walk, SAVE/RESTORE, ATTACK BEAR with each means;
  `tests/test_exposure.py` `shelters`; `test_forage.py`,
  `test_interface.py` (the rock on the ground), `test_animal_reactions.py`.

### Neowilderness: sprites of the built shelters (lot 3, step 3)

The MAKE shelters and the tent show in the NeoWildernessXL landscape
([CRAFT.md](docs/CRAFT.md) § 8.4, memory: [MEMORY.md](docs/MEMORY.md)
§ 21). 15 October 2026, not committed.

- **Tent, hut, igloo, trench.** The original's four sprites
  (`tent`, `cabin`: the MAKE HUT hut, `igloo`, `trench`) become site
  sprites, like the log, the boulder and the station: local view on
  their cell, panel up to 8 cells. The hut, the igloo and the trench on
  the cell where they were made, the tent where it is pitched (USE TENT,
  DROP TENT), never at the wreck. On a single cell, the original's order
  (SURV3D T0D/SE `$5F4C`): wreck, station, igloo, hut, tent, natural
  shelter, trench. Fixed colours: orange tent, brown hut with green
  thatch, white igloo with light-blue joints, green and brown trench.
- **View up to date.** MAKE of a shelter, USE TENT, DROP and GET drop the
  scene cache: the next view shows the shelter or the tent.
- **On disk, XL only.** 8 blocks of NEOWILD.BLK (2 + 3 + 2 + 1), read
  into the SIM window once per appearance, like the other sites;
  NeoWildernessXL 352 → 360 blocks out of 1,600. PROJECT 1,667 → 1,787
  bytes on XL, all in a tail that the 140 KB edition does not have (seven
  candidates, local order, integer bound that spares the floating-point
  computation for a shelter farther than the best panel: the common part
  keeps its size, its code tightened); nothing resident.
- **140 KB edition unchanged** (decision of 15 October 2026): no built
  shelter sprite, the view does not show them, as before; 276 blocks
  out of 280, PROJECT identical (cut at `project_tail`), trunk room
  1,389 → 1,379 (ITEMS +8 bytes).
- **View cost** (XL, emulated VIEW cycles): with no shelter within
  8 cells, or farther than the nearest site, + 0.01 %; a chosen shelter
  costs the projection of a site, like the wreck or the log.
- **Reference and tests.** `tests/scene_ref.py` (`built_shelters`,
  `select`) and `tools/dhgr_ref.py` draw the shelters;
  `tests/test_sites.py` `built_shelter_sprites` compares pixel for pixel
  each shelter local and in panel, the local order, the wreck's tent,
  the reads, MAKE TRENCH, DROP and GET TENT, and the 140 KB edition.

### Neowilderness: crafting, the MAKE recipes (lot 3, step 1)

The original's MAKE probed on the ROM and ported (records A1, A2 and D4
of [ORIGINAL_GAP.md](docs/ORIGINAL_GAP.md); specification
[CRAFT.md](docs/CRAFT.md); memory [MEMORY.md](docs/MEMORY.md) § 20).
15 October 2026, not committed.

- **Probe.** `tools/re_craft_probe.py` runs on the ROM T10/S00, T10/S05
  and T11/S00 alone (176 cases, the driver of `re_forage_probe.py`) and
  68 commands of the real game: conditions, time formulas, effort,
  messages, objects created, for all the recipes, those of lot 5 (rope,
  raft, canteen, utensils, fish hooks, snowshoes, trap, trinkets, hide
  clothing) included. Results: `build/re_craft/results.json`
  (local), figures in CRAFT.md. Probes 4 and 5 of ORIGINAL_GAP.md
  are done: the shelters' "d" is the light `$0D5D`; `$D8`/`$D9` =
  `$7F` mark the cell of the station and of the wreck ("THINK!").
- **Shelters.** MAKE HUT (forest), IGLOO (snow), TRENCH: 4,000 k /
  ((light + 2)(axe in use + 2) × health) minutes (84, 169, 254 by day
  at the start), effort 0.023, refusals "YOU'RE IN THE WATER ALREADY!" and
  "THINK!"; each shelter stays on its cell; USE, ENTER, EXIT with the
  measured messages (9, 10, 11, 1); USE TENT (30 minutes, the tent
  pitched); inside, air + 15 °F, the igloo 35 °F.
- **Weapons and tools.** MAKE CLUB (60 / √health), SPEAR, AXE (600 /
  (√health (3 knife + 1))), BOW (× 4 / (light + 1)) in forest, rope or
  fishing gear outside Burma, New Guinea and Bolivia; USE BOW,
  SPEAR, CLUB: in hand and in use. KILL GAME and KILL FISH take the bow
  (p = 0.2), the spear (0.1) and the club (never) in the original's
  order; time clears their use. The five cases of means 20, 19,
  17 from `results.json` come back in `test_forage.py`.
- **Splint, visor, mud.** MAKE SPLINT (300 / (√health (light + 1)
  (knife + 1)), shortened by the axe, the spear, the wreck or the station),
  MAKE SUNGLASSES ("GOOD! YOU MADE EYE SHADES FROM SLITTED BARK.") and
  SUNSCREEN ("SMEARING MUD…"), 30 minutes.
- **All the other MAKE** answer like the original's core
  (msg 2, 11, 17, 21, 35, 65, 101); only those of lot 5 (hide clothing,
  T10/S05) and of family 17 (TREE, BAIT, SHADOW) still say
  "NOT IN THIS VERSION YET.".
- **Shelter protection (D4).** In a shelter, found or built, the risk
  of injury from an animal is multiplied by 0.1, ATTACK and SCARE remain
  possible (before: total protection); `test_animal_reactions.py` follows.
  Decision of 15 October 2026: like the original, the natural shelter
  included.
- **INVENTORY** shows the bow, the spear, the club, the splint and the
  shelters of the cell.
- **Memory.** CRAFT module (1,645 bytes) on NEOWILD.BLK, 4 blocks, both
  editions, on directory entry 9 of the old hut; door in CAMP; 11-byte
  state in LOWPAGE (saved); nothing else resident. Trunk room XL
  1,859 → 1,599, 140 KB 1,778 → 1,389; 140 KB volume 276 blocks out of
  280. CRAFT read: ≈ 0.03 s on XL, ≈ 0.3 s on Disk II.
- **Tests.** `tests/test_craft.py` (107 ROM cases, 33 commands of the
  real game, inventory, KILL with the bow, 140 KB edition); `--original`
  and the probe in `make test-original`. Remaining deviations: CRAFT.md
  § 8.2 (TODO.md, lot 3).

### Neowilderness: panel above the view

- **Site above the eye finally drawn** (15 October 2026, not committed).
  A panel (wreck, log, boulder, station) whose cell is above the eye by
  more than 5.3 levels per cell of distance (boulder at level 97 seen
  3 cells from an eye at level 12) left row 0 black where `dhgr_ref`
  shows its bottom row. Cause: `project_ground` (`src/project.s`)
  rejected the site when `3·q/16` exceeded 255, like a site too low,
  instead of anchoring it at row 0; the clipping of `sprite_column` was
  right. Fix: anchor 0 for `dz ≥ 0`, rejection kept below (PROJECT +5
  bytes, nothing resident, view cost unchanged).
  `test_sites.generated_shelter` renders the case at its low ground:
  boulder (depths 2 to 4), log, wreck and station clipped at row 0,
  boulder clipped at the left, right and bottom edges, pixel-exact.

### Neowilderness: site sprites (log, boulder, rangers' station)

Three sprites of the original join the view (lot 6,
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md) "Site sprites", memory:
[MEMORY.md](docs/MEMORY.md) § 19). 15 October 2026, not committed.

- **Log or boulder.** On a native map, the natural shelter found is no
  longer the hut: a log on low ground, a boulder on rocky ground (level 96
  and above, STATUS's ROCKY; original's rule SURV3D `$1CAA`, threshold
  `$60A3`), chosen at discovery and kept in `MAP+16` (1 or 2, saved
  with the game). Seen on its cell and in panel. The fixed cabin of the
  generated maps follows the same rule (the original has no fixed cabin,
  its hut is only a built shelter): `tools/mkmap.py` writes 1 or 2
  according to the level of its cell, with no extra code in the game; the
  shipped maps all have a log. The `H` marker of TOPO, ENTER/EXIT SHELTER
  and their rules do not change. The hut (`cabin.bin`) leaves the stock:
  704 bytes freed on each edition, it will come back with MAKE HUT (lot 3).
- **Rangers' station.** Finally drawn: panel up to 8 cells in the eight
  directions, like the wreck and the cabin, and local view on the goal
  cell, the last view before the end screen.
- **On disk, read on demand.** The three sprites are on NEOWILD.BLK
  (11 blocks, both editions) and are read into the SIM window when a view
  shows them, once per appearance: nothing is reread from one view or
  turn to the next as long as they stay there, nor on return from a
  screen. Station read: 0.04 s on XL, 1.25 s on the Disk II (log,
  boulder: 3 blocks instead of 5).
- **Colours** fixed, the same in all regions: log orange, brown and
  yellow; boulder grey and moss; station white with a brown roof and a
  green door. The reference engine (`tools/dhgr_ref.py`,
  `tests/scene_ref.py`) draws them the same way; tests:
  `test_projection.py` (station, 50 exact views and counted reads),
  `test_sites.py` (log and boulder on a native control map,
  SAVE/RESTORE; fixed cabin of a generated map as log then as boulder,
  and the `mkmap` rule).
- **Memory.** 28 resident bytes (`site_load` relay, colours), taken by
  moving three simulation relays into TEXT; PROJECT +289 bytes; without
  the hut, trunk room XL 1,463 → 1,859, 140 KB 1,382 → 1,778; disk
  347 / 1,600 and 272 / 280 blocks.

### Neowilderness: streamlined action menu

The grid on rows 20 to 23 is now played with the arrows and RETURN
alone, without knowing the original's commands
([MENUS.md](docs/MENUS.md) § 4, memory: [MEMORY.md](docs/MEMORY.md) § 18).

- **Eleven fixed verbs.** WALK (SWIM in the same cell when water is
  there), LOOK, REST, WAIT, EAT, DRINK, GET, WEAR, DROP, USE, MAKE each
  keep their cell; one that can do nothing here is greyed (lowercase) and
  RETURN only beeps. Then come the verbs of the moment, by urgency: the
  animal (KILL, SCARE, IGNORE), DOUSE FIRE, CARE, COOK, BOIL, SKIN, CATCH,
  KILL of game, CLIMB, HANG, LOWER, ENTER, EXIT. TAKE, ATTACK, TASTE and
  MAKE STICKS leave the grid (still typable).
- **Lists.** GET composes `PACK x` or `CARRY x` according to the object
  and the bag; WEAR toggles (a worn garment, preceded by `-`, comes off
  with `PACK x`); EAT shows the found piles first, then TASTE and the
  ounces (at most what there is); DRINK skips the single source and
  bounds the ounces to min(water here, weight ÷ 5); KILL, SKIN, CATCH,
  COOK name their targets; MAKE only offers what can be done here; BOIL
  offers the ounces and types `BOIL WATER n OZ`, which the parser now
  accepts on one line. A list with a single entry is skipped.
- **Prerequisite queue (grid only).** MAKE FIRE first types USE FUEL
  (rain, wind), USE MATCHES, then USE FIRE below 50 °F feels-like; MAKE
  WATER the tarp; BOIL the utensils; CATCH the bait and the trap or the
  tackle; KILL the best weapon; USE STOVE the fuel and the matches; the
  kit in the dark the lamp. Each step is typed as at the keyboard (time,
  draws, state), a step already done is skipped, a failure or an
  encounter stops the queue. Typed commands keep the original's refusals.
- **Care.** CARE opens the MEDICAL page on the first active ailment;
  down moves from one ailment to the next, row 23 shows its actions
  (left/right) and RETURN types them. OPTIONS gains line F (IGNORE
  FOOD / GET FOOD).
- **Memory.** What RETURN does becomes the GRID module (entry 32,
  2,456 bytes, copied to `$A300`); TOPOGEN is read from NEOWILD.BLK on
  both editions, MEDVIEW also on the 140 KB edition. Cost on the
  Disk II of the 140 KB edition: **+0.66 s** when opening TOPO,
  **+0.44 s** on the first care page; on XL, only the TOPOGEN read is
  added (6 blocks, not measured separately). Trunk room: 1,562 bytes (XL),
  1,475 (140 KB); volumes 337/1,600 and 260/280 blocks.
- **Tests.** `tests/test_grid_play.py` plays with the joystick, on both
  editions, a fire, boiled water, a pile of mushrooms and a treated
  bleeding; `test_journey_resident.py` expects the MEDVIEW read on
  SUCK VENOM when the disk has it on NEOWILD.BLK.

### Neowilderness: glued messages, tree triangle, animated fire

- **Glued messages.** The bare "!" of `message` is the journey's stop
  reason: "COUGAR IN YOUR AREA!" during a WAIT after a walk stopped by
  nightfall displayed "COUGAR IN YOUR AREAIT IS TOO DARK…". The literal
  "!" of `cause_area`, `m_fauna_stop` and `ol_long_msg` become
  `'!'|$80`; `test_feedback.py` (`no_glued_reason`) checks the texts,
  including those of FORAGE (`frg.s`, `forage.s`), and replays the
  arrival of the bear, the cougar and the snake.
- **Tree triangle.** One crown, one cell: all the columns of a crown
  take the cell of its centre (base, profile, phase), the sides of the
  triangle no longer drop to the base of the neighbouring cell
  ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md), "Trees and forests"); view
  +0.3 to +2 % cycles; `test_forest.py` (`coherent_crowns`).
- **Animated fire.** An animated campfire (28 × 32 pixels, four images,
  ≈ 4.6 Hz, glow at night) burns at the player's feet while waiting at
  the prompt, on both editions: the module (entry 18, four blocks) is
  read from NEOWILD.BLK when it appears (1.2 s after the prompt on XL,
  2.4 s on 140 KB), after a silent keyboard; a key during the read cuts
  it between two blocks and the command is read whole. The fire is
  **anchored in the world** like the other sprites: MAKE FIRE notes its
  cell and its bearing (the heading at lighting: it is in front of the
  player who lights it), and it is drawn at the column of that bearing
  relative to the heading, with the cabin's projection
  (`project_center`), clipped at the edges of the view, absent outside
  the field: LOOK R or L push it halfway out of the view, an arrow moves
  it by 35 pixels, LOOK BACK puts it behind. It stays on its cell: the
  player who leaves with an animal no longer takes it along. It **burns
  down** (port deviation: the original burns until DOUSE): 180 game
  minutes, twice as fast in rain or snow, small flames in the last hour,
  embers in the last 20 minutes, then it goes out as if by DOUSE with
  "YOUR FIRE HAS BURNED OUT."; MAKE FIRE relights it. Place, bearing
  and remaining time are saved. [CAMP.md](docs/CAMP.md) § 8,
  [MEMORY.md](docs/MEMORY.md) § 17, `tests/test_fire.py`.

### Neowilderness: hunting, fishing, gathering and meals (lot 4)

The original's second set of objects enters the port, on both
editions ([FORAGE.md](docs/FORAGE.md) § 17, memory:
[MEMORY.md](docs/MEMORY.md) § 16). Game and fish found along the way
are caught with the trap or the fishing tackle (USE BAIT, USE TRAP,
USE GEAR, CATCH GAME/FISH and a duration in hours), or killed with the
rifle, the axe or the knife (KILL, ATTACK, CUT); a bear, a cougar or any
animal killed by ATTACK leaves its carcass (65 V² ounces). Meat, fish,
insects, fruit, cactus, mushrooms, plants and nuts discovered stay on
the cell as piles: PACK and DROP move them between ground and bag, TASTE
gives their taste, EAT eats them (calories, water, poisonings, salt), COOK
cooks them on the fire or the stove (spoilage pushed back, detoxification),
SKIN takes the hide. Spoilage follows the original: day factor `$4C48` =
792 / degree-hours above 32 °F, recomputed at midnight, clock at each
health update, ground piles lost on leaving the cell,
"THERE IS A BAD SMELL IN THE AIR.". IGNORE FOOD, FLAG FOOD, GET FOOD.

- The commands are a module read from NEOWILD.BLK at each command
  (FORAGE, 5,822 bytes, 12 blocks, SIM window: 0.1 s on XL, 1.3 s on the
  emulated Disk II); the state (221 bytes) is saved by SAVE (5-block
  saves); the discoveries are stored in ITEMS (where
  `module_resource_results` moves), the carcass in OUTDOOR, the clock, the
  messages and the day factor in ALERT. On the 140 KB edition, TREE
  and ORIENT are read from NEOWILD.BLK to make room in the stock.
- Grid: CATCH and KILL with game or fish present, SKIN with a carcass,
  COOK with food and a fire, TASTE with food
  ([MENUS.md](docs/MENUS.md)); INVENTORY shows the piles and
  `SPOIL`; two lines of HELP.
- Provisions according to the original (step 5) behind `FORAGE_FIDELITY`
  (left at 0: `test_reference_state.py` unchanged).
- `tests/test_forage.py --original` replays 119 cases of
  `build/re_forage/results.json` (15 set aside with their reason: weapons
  of lot 3, fauna of lot 11), the 30 commands of the real game and the
  clock; `test_editions.py` takes, cooks and eats game on both editions;
  `test_save.py` restores piles and counters. Deviations listed in
  § 17.3 of FORAGE.md (daytime ATTACK thresholds, pile weights, clock
  rate).

### Neowilderness: TODO.md reorganised by game lots

- `TODO.md` now follows the lots of ORIGINAL_GAP.md § 3 (table lot /
  state / evidence / resident cost, stock per edition, disk), with a
  "Next lot" line, the exit rule "done → CHANGELOG the same day" and
  the "Done when" items as acceptance tests; three sections outside the
  lots (interface, image, quality) and a "Pending decisions" section
  (review of the verbs of 14 October). Sixteen done entries removed
  (including SAVE/RESTORE, simplified start menu, safeguards of
  `test_prodos.py`, reservations of § 12.8), three obsolete ones (140 KB
  disk policy, SIM copy ruled out in § 12.6, "everything is still not
  committed"); list at the end of the file.

### Neowilderness: focus levels in the pages (tabs, groups, cursor)

In the top pages, up and down now move a focus between levels before
leaving the page, left and right act on the level that has the focus
([MENUS.md](docs/MENUS.md) § top pages). On arrival the focus is on the
tab row (left/right change page, up does nothing); STATUS, MEDICAL and
HELP have no other level, down returns to the view there as before.

- INVENTORY: down puts the focus on the group row, left/right change
  group in a loop; the shown group is in inverse when its row has the
  focus, in brackets otherwise. Down then goes through the group's pages
  (`PAGE 2/2`) and returns to the view after the last one; up goes back.
  1-5, N and B unchanged. Footer: `UP/DOWN: TABS/GROUPS/PAGES  1-5 GROUP  N
  NEXT  B BACK  T TOPO`, `ESC: VIEW`.
- OPTIONS and MENU: a `>` cursor in column 1; up/down move it, down
  below the last line returns to the view, RETURN and space act as the
  line's letter. Footer: `UP/DOWN: CHOOSE  RETURN: SELECT`, `ESC: VIEW`.
- A single state byte (`pg_focus`, reset to 0 on each arrival) handled in
  `page_keys` (`pg_levels`: nothing, INVENTORY's own levels, or the
  number of cursor lines); each move redraws the page differentially,
  only the changed cells are written.
- Memory: the STATUS module goes from 5,435 to 5,563 bytes (4,270 → 4,407
  stored in LZ). The auxiliary store of the 140 KB edition could not take
  everything: `page_foot`, `pg_mark`/`pg_lines` and the two long footers
  are resident (CODE segment, WILDERNESS 659 → 475 bytes free).
- Tests: `tests/test_focus.py` (new: tabs → groups → pages path,
  OPTIONS/MENU cursors, RETURN, Esc; writes = changed cells),
  `tests/test_transitions.py` (differential focus moves),
  `tests/test_interface.py` (brackets, footers).

### Neowilderness: resident RAM freed (relocation lot)

Two measured studies (coverage of twelve games; bank 2 of the main
language card) guided a lot of moves; details and counts in
[MEMORY.md](docs/MEMORY.md) § 15. Free resident main RAM: 1,486 bytes
more (TEXT 149 → 216, WILDLO 7 → 412, WILDGAME 14 → 90,
WILDERNESS 4 → 659, RESIDENT 3 → 129, MENUCODE 9 → 106 after the
navigation fix, which takes 60 of them).

- Startup is no longer resident: `start`, the `native_video` switches
  and the /RAM takeover (that of `dev/lib/prodos/video.s`) move into
  NEOWILD.SYSTEM; the library is no longer linked into the game.
- The exit to ProDOS moves into INPUT (`prodos_restore`, `prodos_quit`,
  the FORMAT of /RAM); RESET keeps a 12-byte resident relay
  (`reset_exit`: stack, direct copy of INPUT, `module_reset_exit`). The
  state found at startup (bitmap, RESET vector, /RAM unit) is no longer in
  RESBSS: the loader writes it when taking the memory into directory
  entry 2 (auxiliary stock, below the sprite area), which the exit copies
  back to `$2000`.
- The stars take `st_inputs` and `st_tugap` back into their module; the
  two-key dialog box of `orient_ask` moves into ORIENT; `select` (RETURN
  in the grid, ≈ 24,000 more cycles per RETURN) and the end of `do_save`
  move into INPUT.
- Bank 2 of the main card: ProDOS's QUIT code (`$D100-$D3FF`) is set
  aside by the loader in the same exit state and put back by every exit
  (QUIT, RESET, Q at the menu: `ld_unquit`); `column_setup`, `scroll`,
  `clear_rows`, `dhgr_pack` and `hud_draw` run there behind a 10-byte
  relay (746 bytes, `B2_ENTRY`). Full view 6,342,285 →
  6,325,006 cycles, LOOK L 1,848,836 → 1,844,305.
- Auxiliary stock: trunk room XL 4,293 → 2,949 bytes, 140 KB 1,761 →
  345. The object name table stays resident (it no longer fits on
  140 KB). The tests' comparison disks have the Sierra sprite area; those
  with a native map read TREE and ORIENT from NEOWILD.BLK.
- Loader: HICODE read at `$5800` (the module window, free during
  loading) instead of `$AA00`, which gives it back a page.
- Tests adapted: `test_boot`, `test_pack_boot` (entry 2, `ld_exit`, bank 2
  code after the takeover), `test_prodos` (bank 2 `$D000`,
  `$D100-$D3FF` identical to the loader's entry at each exit),
  `test_hof_volume`, `test_optimizations` (`b2_clear_rows`).

### Neowilderness: navigation by pages (top / view / bottom)

- The view is in the centre. On an empty line, left and right turn it
  (unchanged), RETURN, TAB or down opens the command grid, up opens the
  top pages. In the grid, down goes down the rows; below the last row of
  verbs, it closes the grid and opens the bottom pages (`grid_bottom`
  types `T`, TOPO; above a shorter last row, it first goes to its last
  cell; in a list, it stops: 60 bytes of MENUCODE). Up on the first row
  returns to the view, Esc goes up one level (unchanged). Fix of the same
  day: down on the view opened TOPO directly.
- Top pages: STATUS → MEDICAL → INVENTORY → HELP → OPTIONS → MENU, in a
  loop with left and right; down or Esc returns to the view. The old
  MENU page is split: OPTIONS (C fauna frequency by `NATURE`, A the
  player on TOPO, P MAP) and MENU (S SAVE, R RESTORE, Q QUIT). The tab row
  keeps `S/M/I/H, LEFT/RIGHT` on the right; MAP switched off answers
  `MAP IS OFF (OPTIONS PAGE).`
- Bottom pages: TOPO first, then left or right switches to MAP and back;
  up (or Esc, RETURN, space) returns to the view, down no longer does
  anything in TOPO. MAP scrolls with I, J, K, L (up, left, down, right)
  and recentres with C; the arrows and WASD no longer scroll it. The
  switch loads nothing: MAP writes its text page over the sheet (TOPOGEN
  stays in the SIM window, `topo_over`), the return to TOPO redisplays
  the mixed mode and the legend (`topo_frame`, taken out of `topo_open`)
  without recomputing the sheet, and up copies back the snapshot of the
  view. Typed MAP (`M`, `MAP`) goes to TOPO by the full path; when the
  option switches MAP off, left and right stay on TOPO. Legend:
  `UP/ESC: VIEW`, `LEFT/RIGHT: THE TEXT MAP`.
- The grid loses STATUS, INVENT, TOPO, MAP, HELP and QUIT, which the
  arrows and the MENU page reach; these commands remain valid at the
  keyboard. On the flat map: 13 verbs on three rows. MENUSWAP: 1,536 →
  1,489 bytes (47 free). HELP describes the navigation (`LEFT/RIGHT: TURN
  RETURN: COMMANDS`, `UP: PAGES  DOWN: COMMANDS, THEN TOPO`, `MAP: IJKL
  SCROLL, C CENTER`).
- Memory: STATUS 5,410 → 5,436 bytes (end `$AB3B`, stored 4,275), SITES
  1,631 → 1,679, TOPOGEN 2,981 → 2,987; free auxiliary stock:
  NeoWildernessXL 5,696 → 5,627 bytes, Neowilderness 140 KB 1,830 → 1,761.
- Tests: `test_menu_bar` (grid verbs, RETURN/TAB/down open it, down
  below the last row opens TOPO, up returns to the view with the grid
  closed), `test_screen_returns` (MAP by I/J/K/L, six pages, case
  "DOWN TOPO → MAP → UP", down until past the grid, and "MAP → RIGHT → UP"
  without module loading), `test_graphical_topo` (exit by up,
  `bottom_pages`: TOPO ↔ MAP without loading or redraw, MAP switched off,
  view intact), `test_interface` (tabs, HELP, `option_pages`, MAP by I/L),
  `test_transitions` (round of the six pages and differential OPTIONS
  toggles), `test_sites` (scrolling by I/J/K/L);
  `tools/topo_dhgr_ref.LEGEND`.

### Neowilderness: third memory recovery

- The module LZ decoder (`lz_unpack`, `lz_guard`, `lz_back`, 251
  bytes) runs in place in `$D001-$D0FF` of bank 2 of the main language
  card, the page that ProDOS 8 does not use (it only reads `$D000`, never
  written, and keeps its QUIT code in `$D100-$D3FF`). A 16-byte relay
  in TEXT selects the bank (read and write: the decoder rewrites its
  operands) then puts the ROM back. TEXT goes from 11 to 246 bytes free.
- NeoWildernessXL reads CAMP, MEDVIEW, TREE and ORIENT from disk when
  they load: new file `NEOWILD.BLK` (signed header block, then each raw
  module aligned on 512 bytes, allocated first: blocks 8 to 20), bank
  code `BANK_DISK = $40` in the directory, resident `disk_fetch`
  (READ_BLOCK on the boot unit, zero page `$3A-$4F` preserved, a beep and
  a key to retry if the disk is missing). The loader checks the signature
  and refuses a file-by-file copy ("NEOWILD.BLK HAS MOVED…"); HICODE is
  read at `$AA00`. Free trunk room in the auxiliary stock: 496 → 4,362
  bytes; CAMP loads in 34,843 cycles instead of 91,364 (LZ decoding).
  The 140 KB edition keeps these modules in the stock. None of these
  modules loads during a view, a walking step or a screen return. Details
  and measurements: docs/MEMORY.md § 14.
- Tests: `test_boot` (`$D000` byte, decoder, NEOWILD.BLK blocks, unit),
  `test_pack_boot` (`ld_blk`, file index, `BANK_DISK` entries),
  `test_transfers` (padding up to the block, cost per block), `test_resident`
  (expected MEDVIEW reads on XL), `test_editions` (NEOWILD.BLK on
  XL only, moved copy refused), `test_prodos` (Bitsy Bye lists
  NEOWILD.BLK), `test_hof_volume` (loader writes at `$D001-$D0FF`),
  `test_save` (the address of `hof_key_wait` is also loader code).

### Neowilderness: the STATUS pages, options, fixed cabin

- STATUS, MEDICAL, INVENTORY, HELP and MENU follow one another in a cycle
  with the left and right arrows (`src/pages.s`): tab row, common
  footer, S/M/I/H to jump to a page, T for TOPO, Esc/down/RETURN/space
  for the view. MEDICAL goes to 80 columns (two columns) in the STATUS
  module (MEDVIEW's old screen disappears); HELP fits on a page of
  four blocks; INVENTORY picks its groups with 1-5.
- MENU page: SAVE, RESTORE, QUIT, the fauna frequency (NATURE) and two
  options: the player on TOPO (hidden by default) and MAP (enabled by
  default; disabled, MAP answers `MAP IS OFF (MENU PAGE).`).
- The cabin no longer teleports: the natural shelter found by TRAVEL's
  resource sweep (species 12) only moves the cabin on a native map; the
  generated maps keep their fixed cabin (header 16-20). The draw is still
  made (random stream unchanged). `test_sites.shelter_fixed`.
- Auxiliary stock: ADVENTURE (21, rarely loaded) is LZ-compressed to
  make room for the pages. `wf_storm`, the precipitation multiplier that
  the preparation patches in the image, moves from ADVENTURE (compressed)
  to the THERMAL segment of SIM (raw image, `pr_patch_sim`). SIM covers
  `$9600-$B452`: `test_stars_game` calls `menu_gather` again after its
  direct call of `env_hour`, without which the rotations ran the end of
  SIM instead of MENUSWAP (`level1`, `$B005`).
- The pages are written top to bottom without clearing the screen (no
  more `t_home`): each cell is written once (carriage return, `tab`,
  `vtab` fill with differential blanks), MEDICAL and HELP row by row on
  their two columns, STATUS by halves (left up to column 42, then right
  by `st_at`). Only the cells that change are stored; nothing of the
  previous page remains.
- LOOK N/E/S/W and LOOK AZ put the carried compass in use (like USE
  COMPASS) instead of answering "FIRST PUT DIRECTION AID IN USE";
  `test_hof_volume` begins its journey with LOOK S (towards the north, the
  walk is blocked).

### Neowilderness: descriptions on the left, grid on the right

- The four 80-column rows are swapped (request of 14 October 2026): the
  result, the stock line and the composed command occupy columns 0 to
  38, the separator column 39, the grid columns 41 to 78 (`MN_RES`,
  `MN_END`, `MN_GRID` in `src/menu.s`). The result column is cleared
  without touching the grid (`res_clear`, bounded `clear_to`); column 79
  is never written.
- Grid: the up arrow on the first row of verbs (WALK…) closes the grid
  and returns to the view, as the down arrow opened it; in a list it
  stays blocked at the top.
- Two editions: Neowilderness (`dist/NEOWILDERNESS.po`, 140 KB, the Sierra
  alone, the preparation, five saves; 221 blocks out of 280) and
  NeoWildernessXL (`dist/NEOWILDERNESSXL.po`, 800 KB, the six scenarios).
  Same game, same loader: `ld_regions` (written by
  `build_disk.py --edition`) chooses the menu pieces (`tools/genmenu.py`),
  refuses keys 2-6, skips the region question of free travel and of the
  preparation, and bounds the hall of fame (`hm_regions`, also in NEOWILD.END). The
  tests run on XL; `tests/test_editions.py` covers both.
- Command grid: SWIM, CLIMB, HANG FOOD and LOWER FOOD only appear where
  they can succeed (water or shore ahead, tree, bag carried or hung),
  like DOUSE with the fire; the grid follows the rotations.
- 800 KB 3.5" disk: the shipped image (`../dist/NEOWILDERNESS.po`,
  296 blocks out of 1,600, the five saved games); `make disk140` keeps
  the 5.25" disk. a2shot boots an 819,200-byte image on the 3.5" SmartPort
  card in slot 5 that POM2 now exposes in `pom2_core` (POM2 commit
  `b93b5f6`, SDK copied into `dev/tools/a2shot/sdk`).
- FORAGE, step 1 (docs/FORAGE.md § 4): food discoveries draw their random
  numbers like the original (third fruit draw for 0.2 ≤ r < 0.5, quality
  draw of the wild nuts, eighth resource); `tests/test_forage.py`.
  `test_save` also removes the journey preparation from its 140 KB copy
  to keep three saves (`--omit preparation`).
- INVENTORY in 80 columns: the five groups as tabs with their object
  count (the shown group in inverse), the objects in three columns of
  sixteen rows (48 per page instead of 12), the four free capacities on
  one line, left/right change group, down returns to the view.
  INVENTORY and HELP join STATUS in a single module (SIM window); the
  SCREENS module (2) disappears, which frees a directory entry.
- LOOK UP on a clear night: the sky above 45° is shown (star list
  recomputed in the perspective of the raised view, 33.7° → zenith;
  docs/STARS.md § 15). VOCAB is stored in LZ to make room.
- One-letter commands: `M` = MAP, `T` = TOPO, `S` = STATUS (alone on the
  line; `fast_words`).
- STATUS in 80 columns: title and progress, on the left BODY (ten-cell
  gauges for HEALTH, ENERGY, HUNGER, THIRST, one row apart; body
  temperature), CONDITIONS (illnesses, hypo/hyperthermia, active injuries
  with their percentage, altitude sickness); on the right PROVISIONS
  (FOOD/WATER × CARRIED/HERE/IN REACH table), ENVIRONMENT, RANGERS
  (distance; direction with the compass), SITUATION. The module now runs
  in the SIM window (`$9600`, loaded by `mem_fetch` like TOPOGEN); its
  small display routines are resident (LOWCODE); the injury names come
  from MEDVIEW; `goal_pct` no longer reloads STATUS.
- TOPO: the player is drawn (white dot, arrow according to the heading,
  over the sites); 4-mile scale bar below the north arrow; 80-column
  legend aligned with the view (`topo_legend`, SITES module); down arrow
  returns to the view.
- STATUS: the down arrow returns to the view (the up arrow opens it from
  the view); the legend becomes `ESC/RETURN/SPACE/DOWN: VIEW`.
- Shortened stock line: `FOOD n WATER n HERE f/w OZ` fits in the result
  column (the old `FOOD n OZ  WATER n OZ  HERE f/w` lost the water on
  the ground, for lack of room).
- MAP: the player and the sites (P, C, H, R) fit in a single character,
  the inverse letter, followed by the terrain symbol of their cell
  (instead of an inverse letter + space block over the whole cell).
- Discovery: "YOU FIND GAME ANIMALS." replaces "YOU FIND GAME."
  (the game animals, not a game being played).

### Neowilderness: integration of lots 2, 7, 9, 13 and LOOK, second memory recovery

- Text bank (`src/textbank.txt`, `tools/gentextbank.py`): 150
  messages out of resident RAM and the modules, in the auxiliary stock,
  read at printing (`message` with X = 0, `text_fetch`) and expanded by
  a 105-word dictionary (5,836 → 3,372 + 286 bytes).
- Modules ORIENT (26) and ALERT (27); LZ images in the stock decoded in
  place by `mem_fetch` (TOPOGEN, SCREENS, STATUS, CAMP, ITEMS, MEDVIEW,
  TREE, ORIENT, ALERT, wreck, cabin, animals).
- ProDOS zero page in auxiliary `$BF00` during the game, `$BE00` resident
  (HICODE); SIM ends at `$B44F`; TOPO snapshot up to `$EBFF`.
- A single data file (trunk, packs, preparation) and a compressed
  loader: −10 blocks; the 140 KB image keeps one saved game (five on
  800 KB).
- Details, measurements and discarded leads: [MEMORY.md](docs/MEMORY.md) § 13.

### Neowilderness: orientation (fidelity lot 7)

- Rules of T$0F/S$0F, T$10/S$0C and T$11/S$00 probed on the ROM
  (`tools/re_orientation_probe.py`: 22 ranges, 14 module runs, three
  typed games) and ported (`src/orient.s`,
  [ORIENTATION.md](docs/ORIENTATION.md)): aid in use for LOOK
  N/E/S/W/AZ (msg 42; none at the start, CARRY is not USE), compass
  (msg 44), watch (msg 189, 13 or 201, estimate), stick (msg 29, 48,
  elapsed time), LOOK SUN (msg 41; visibility ≥ 139, ≥ 163 at dawn and
  dusk), LOOK STARS (msg 52 outside a clear night; pole ±33°, south if
  the latitude is negative), LOOK COMPASS (msg 256), LOOK WATCH/ALTIMETER,
  INSIDE SHELTER, PAN + direction (msg 2), USE MAP/COMPASS/WATCH/
  ALTIMETER/CHART/SHADOW, compass/watch exclusion, light (msg 53),
  watch and stick put away by time.
- Menu: LOOK SUN and LOOK STARS, USE also lists MAP…CHART.
- Tests: `tests/test_orientation.py`; USE COMPASS added to the scripts
  that type LOOK N/E/S/W (`test_compass`, `test_hud`, `test_pan`,
  `test_sites`, `test_play`) with the ±2° error of the original compass;
  LOOK B in `test_tree`; "patchy" map of `test_geo_resident` with two
  raw tiles (the 140 KB volume is full for a level-10 native map).
- Memory: WILDLO 1,718 → 276 bytes free, TREE 916 → 1,926, auxiliary
  stock −1,023 bytes per region, disk 261 → 265 blocks.

### Neowilderness: care, alerts and illnesses (fidelity lot 13)

- Care commands of T11/S00, T12/S08 and T15/S0A: USE SPLINT (selector
  3, splint worn, 30 min; `splint_place` hook for the lot 3 splint),
  USE PRESSURE (selector 2), USE AXE/KNIFE (tool in use),
  CUT/COOL BODY (selector 7 with a tool in use), WET BODY (selector 9:
  weather front, water, river within reach or ounces from the canteen),
  DRY/WARM (messages 117/118), HANG clothes (drying in the sun; fire hook
  for lot 2); automatic placement of used objects (hand, glasses worn).
  Verbs 13, 14, 31 and 33 dispatched without a table entry
  (`verb_more`), HANG goes through `care.s`.
- Original alerts added below the result: hunger 173, thirst 174 and
  fatigue 175 once a day, shivers/sweat 203/204 and deterioration 187
  once per command, serious condition 160, health below 1 (176, replaces
  "YOU ARE VERY WEAK"), drowning 177; forced sleep (message 178) of an
  exhausted player: REST of `180 + INT(RND × 300)` minutes without input.
- Infection (cuts active for 6 h) and malaria (regions 3 to 5) of
  T0B/S07, with the native generator, behind `disease_triggers`.
- `tests/test_care.py --original`: 957 more ROM cases (WET/DRY,
  DRY/COOL/CUT/HANG dispatch, USE, placements, alerts, forced sleep, 528
  infection and malaria draws); `tools/re_event_scan.py` (producers and
  consumer of the conditions). `test_reference_state.py` unchanged and
  green.
- Memory: WILDLO 1,718 → 141 bytes free, WILDMVI 878 → 1,809 bytes,
  SIM 573 → 265 free; volume 261 → 266 blocks. The native-map disks are
  at 278–280 blocks out of 280: `test_geo_resident.py` checks the
  decoding of raw tiles on a lighter map (2 noise tiles).

### Neowilderness: fire, light and water (fidelity lot 2)

- The original's fire (T11/S00): `USE MATCHES` (one match out of 24),
  `USE FUEL`, `USE GLASS` (sun at 30°), `MAKE FIRE` with its refusals
  (water, snowy rocky ground, no kindling, rain or 41 mph wind without
  fuel), 30 minutes of effort, `USE FIRE` (+25 °F in the thermal model,
  127 °F when the byte overflows, like the ROM), `DOUSE FIRE`,
  `MAKE STICKS`; `WALK` and `SWIM` refused while the fire burns ("SMOKEY THE
  BEAR…").
- Light (`$0D5D`) recomputed at each health step; `USE FIRSTAID KIT`
  refused without light; `USE FLASHLIGHT` spends one use of the batteries.
- Water (T0F/S00): `GET RAIN`, `GET SNOW`, `GET ICE`, river or lake
  (160 oz untreated), cactus, timed search, `MAKE WATER` by
  condensation, two-quart canteen, lasting contamination of the canteen,
  `BOIL WATER` (utensils, stove or fire), `DRINK` limited to 0.2 × weight,
  giardiasis when RND ≤ 2 / altitude in hundreds of feet (instead of a
  one-in-eight chance); FILL/REFILL without 10 minutes.
- The original's texts; grid: `MAKE`, `BOIL`, `DOUSE` (fire lit), camp
  objects and `FIRE` in `USE`. CAMP module (1,617 bytes) in place of
  WATER ([CAMP.md](docs/CAMP.md), `tests/test_camp.py`,
  `tools/re_camp_probe.py`).

### Neowilderness: walking MAP, draw only what changes

- During WALK/SWIM, the MAP window stays fixed instead of being
  recentred at each half-step: a half-step only rewrites the cell left,
  P's cell and the changed characters of the label (7 writes instead of
  ~300 on the real map). The window moves by a quarter (10 × 6 cells,
  bounded to the grid) when P comes within 4 cells of an edge: a single
  full, differential draw. One centring if P is outside the window at
  the start; MAP, C and arrows unchanged. SITES +270 bytes (424 free),
  BSS +5 (saved game unchanged), GCODE +5 ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
  "Full-screen MAP 80 × 24", `tests/test_walk.py`,
  `tests/test_sites.py` `full_screen`).

### Neowilderness: SAVE and RESTORE, five games (lot 9)

- `SAVE` and `RESTORE` (until now "NOT IN THIS VERSION YET") keep five
  games, like the original: number asked by the numeric prompt or typed
  after it (`SAVE 2`), question before overwriting an occupied save
  (region and hours), refusal of another region (`GAME 1: SIERRA NEVADA
  ONLY.`), of another build, of an empty or damaged save (Fletcher-16),
  write-protected disk and missing file reported; no refusal changes the
  game ([SAVE.md](docs/SAVE.md)).
- A save = 32 bytes of versioned header + 1,392 bytes of state (GDATA
  without the module cache, the typed line or the constant tables;
  objects on the ground; map header; named species), inventory
  established by sweeping the writes and comparing memory; RESTORE
  redraws the view (mood, stars, scene), puts the menu back on its first
  cell and the rest of the game is identical byte for byte.
- Code in a module read on the command, `NEOWILD.SAV` (1,218 bytes, SIM
  window, I/O buffer `$AB00`, bitmap `$96-$AF` freed then put back);
  237-byte resident relay (WILDLO), +6 bytes of verb tables, +13 in
  INPUT. Fixed-length files `NEOWILD.S1`…`S5` created at build time:
  neither CREATE nor allocation. SAVE: 8 MLI calls, ≈ 4.5 s;
  RESTORE: 6 calls, 6 to 9 s with the redraw. Volume: 24 blocks, 4 free.
- `DISK_BLOCKS=1600` / `make disk800`: the volume on 800 KB; booted and
  tried (SAVE, RESTORE) in POM2 on its SmartPort card, out of reach of
  a2shot (Disk II only): the shipped image stays 140 KB.
- Tests: `tests/test_save.py` (night game, identical continuation,
  identical view, other region, restart, file read back after eject,
  faults, protected WOZ, ProDOS guards), `tests/test_resident.py` (SAVE and
  RESTORE, the only commands allowed to call the MLI),
  `tests/test_prodos.py` and `tests/test_pack_boot.py` (catalog).

### Neowilderness: LOOK UP / LOOK DOWN, up and down arrows

- `LOOK U`/`UP`, `LOOK D`/`DOWN`, `LOOK F`/`AHEAD`/`FORWARD`, `PAN` and
  `SCAN U`/`D`: three view angles like the original (byte `$E7` of
  SURV3D, probed): LOOK sets the angle, PAN moves one notch and stops at
  the end, PAN AHEAD does nothing; no game time; the angle persists
  through LOOK L/R/N/AZ, VIEW, STATUS, REST; WALK, SWIM and LOOK B
  level it again; nothing changes in the cabin; "NOT NOW." refuses
  to look down in front of an animal standing in contact (the bear in
  the Sierra, the original's rule per region and species).
- Rendering: each projected line moves down (up) or up (down) by 96
  lines, measured on the original (the plan expected 64 downwards):
  relief, sky in zones, sun and Moon (a body up to 76° high becomes
  visible when looking up), stars, distant panels, tree feet; looking
  up, neither sprite nor tree; looking down, the wreck and the local
  sprites stay in place (the original shows them there). 96 lines = 512
  slope units: `tilt_row` projects `tinc − 512 × tilt` with the level
  tables, without touching the ray loop (level view bit-identical,
  +0.2 to +0.9 % cycles). Oracles `view_ref`, `forest_ref`, `scene_ref`,
  `dhgr_ref`, `stars_ref` with `tilt`; `tests/test_tilt.py` (six maps ×
  three angles bit-exact, trees, distant panel, sun at 68°, commands,
  refusals, rows 176-191 of the six regions), star bench at three
  angles, `look_tilt` scenario of `test_adventure.py --original`
  (port angle = `$E7` at each step, clock unchanged);
  `tools/re_tilt_probe.py` ([LOOK_UPDOWN.md](docs/LOOK_UPDOWN.md)).
- Grid: `UP` and `DOWN` in the LOOK list. Typed line: **up arrow =
  STATUS, down arrow = grid** (TAB stays an alias);
  [MENUS.md](docs/MENUS.md) § 4, `tests/test_menu_bar.py`.
- `tests/test_sim.py` "Night view": the test assumed the horizon at 95;
  the sky goes down to the last visible sample (rule of the original and
  of the oracle), which the port's fog brings closer (visibility 24:
  11 steps, line 104). The test now computes this limit.

### Neowilderness: full-screen MAP 80 × 24

- MAP, and the animated map of WALK/SWIM, take the whole 80-column text
  screen: 40 × 24 cells instead of 32 × 14; an inverse label at the start
  of row 0 holds cell, magnetic heading, site under P and, during the
  walk, the minutes (which replace `TRAVELLING: # MIN.`); scrolling by a
  quarter window; rows 20 to 23 cleared at the end of the walk, grid
  given back at the prompt; SITES 299 bytes shorter
  ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md) "Full-screen MAP 80 × 24",
  `tests/test_sites.py` `full_screen`).

### Neowilderness: reserves of direction 3 (first memory recovery)

Four gains, one commit each, measured since `b941346` (details and counts
in [MEMORY.md](docs/MEMORY.md) § 12). Free resident main RAM:
375 → 2,282 bytes; auxiliary stock of each region +2,478 bytes
(Burma, worst case: 171 → 2,649).

- Compressed TOPO snapshot (`68543db`): each 40-byte line is predicted
  by the line of the same bank two rows higher (copy / literal tokens,
  60 bytes at most per line); 2,128 to 6,962 bytes over 49 views of the
  six maps instead of 12,800. Auxiliary bank 2 and `$F100-$FFF9` join
  the stock (4,394 bytes). TOPO opening +0.15 s, return 0.36 → 0.48 s; a
  stream that is too long redraws the view as on a native map
  (`test_graphical_topo.py`).
- Unrolled DHGR lines (`drows`, 1,601 bytes) and their tables (322) in
  bank 2 of the main card, `$D400` (`8acedbf`): WILDLO 124 → 1,718 bytes
  free, WILDERNESS 5 → 318; 12 cycles per span, +0.5 to 1.1 % per view.
  Record tables from 128 to 256 bytes.
- Fauna: the reference copies of SITES (249 bytes) are removed;
  `test_fauna.py` tests TRAVEL's production sweep (`ec9ea61`).
- Lunar ephemeris (549 bytes) out of SIM, in the main card
  (`b96dbe5`): SIM 24 → 573 bytes free in its window.
- Leads measured and discarded (§ 12.6): partial copy of SIM
  (≈ 0.45 s per WALK 1 H, at the threshold), `SAVE` page in auxiliary,
  VOCAB in 5 bits. Volume: 30 → 27 blocks free.

### Neowilderness: volume integrity after the hall of fame

- POM2 report of 13 October 2026: after a Sierra journey, the EOF of
  `NEOWILD.DAT` in the directory (block 2, byte `$41`, `$BC` → `$3F`)
  blocked the next boot on `NEOWILD DISK ERROR $4C`. ProDOS rewrites the
  entry of a file opened with write access from its FCB when that FCB is
  marked modified: a corrupted FCB of `NEOWILD.DAT` gives exactly this
  byte (a2shot injection). The stray write itself was not reproduced
  (a2shot and POM2 with the user's profile). Fix: all the files of the
  volume except `NEOWILD.HOF` are locked (access `$01`,
  `tools/build_disk.py` `lock_files`); ProDOS can no longer rewrite their
  entries ([HOF.md](docs/HOF.md) § 10).
- Score: the region and the journey kind were read at `MAP+32` and
  `MAP+33`, which the wild food sweep rewrites at each walk; a scenario
  journey became "FREE JOURNEY: NOT RANKED" from the first walk. The
  module reads `region_number` and `journey_kind` (new resident byte
  written by the loader).
- `tests/test_hof_volume.py` (in `make test`): volume access rights,
  corrupted FCB at the loader's CLOSE, real journey then comparison of the
  whole volume after eject, guard against any write by the game into
  ProDOS memory from QUIT to the next menu. `ld_close` (loader) exported
  for the tests.
- a2shot: step `storewatch:LO:HI` / `unstorewatch` (each processor write
  into the range, with the language card state, ALTZP, RAMRD, RAMWRT),
  compatible with the existing scripts.

### Neowilderness: journey preparation and levels (fidelity lot 1)

- `P` at the menu ("P PREPARATION     QUESTIONS, NOT RANKED"): region,
  level, then the questions of GO1/GO3 (date and time chosen or drawn,
  normal play or research mode, sex, weight 50–350 lb, build, height, age,
  pulse, fauna and storm frequencies) and the fitness verdict of GO2;
  weight, metabolism `w/100`, meals `+0,004 w`, Hmax and health, thermal
  surface Q, overweight factor; research mode: the original's body
  (175 lb), instruments at the wreck, no injury. Journey not ranked.
- Any journey other than a scenario at level 4 (`NEOWILD.PRE`, 5,005
  bytes, 3,702 compressed, decoded at `$2000`, no resident byte in main
  RAM; volume 260/280 blocks): date and time drawn around summer
  according to the level, phase of the temperature wave, crash injury
  `⌊0,45 RND L − 0,3⌋`, wreck kit in nine groups, uses ×1/√L, first
  front `3000/(L F) + 20`, its duration, the wind; words of the
  introduction (terrain, difficulty, time, injury). Formulas checked
  byte for byte against the original with a forced RND
  (`tools/re_prepare_probe.py`, `tests/test_prepare.py --original`,
  eleven cases).
- RETURN, RETURN: first frozen journey unchanged
  (`test_reference_state.py`).

### Neowilderness: the four bottom lines, command surface (lot 8, step 2)

- Rows 20 to 23, columns 0 to 37: verb grid (contextual ones first:
  `EXIT`, `ENTER`, `IGNORE SCARE ATTACK`; a verb with no object to
  name, `USE` without medicine, `DRINK` without reachable water, is not
  offered), six cells per row on four rows, scrolling by row beyond
  (`^`/`V` in column 38), chosen cell in inverse; RETURN, up arrow or
  TAB opens it, TAB closes it, arrows, RETURN, Esc; a verb opens its
  list
  (durations, directions, objects reachable here in 12-character cells,
  ounces) and composes the keyboard command in `inbuf` (`menu_noun`
  passes the chosen object: `GET COTTN SOCKS`). Down arrow on the empty
  line: STATUS. A command issued from the grid leaves it open. Typed
  commands are still accepted ([MENUS.md](docs/MENUS.md) § 4,
  `tests/test_menu_bar.py`).
- Columns 40 to 78, the descriptions: the last message, placed word by
  word on four rows (no more cut text or glued rows); on the last row,
  when the message leaves it free, the stock line
  `FOOD n OZ  WATER n OZ  HERE f/w`, or `> ` and the command as the
  parser will read it while it is typed or composed (without cursor);
  the load report fits there.
- Start message without the command list (the grid shows them);
  `src/menu.s` resident at `$BA00` (842 bytes), 1,474-byte grid
  sleeping in HGR lines 176-191 and copied to `$B000` at each prompt
  ([MEMORY.md](docs/MEMORY.md) § 11); the loader reads with its own
  buffer `$AB00`. Volume 250/280 blocks.
- Scenario menu: Sierra Nevada on the first line (key 1), RETURN
  alone chooses it (`CHOICE (RETURN = 1, 1-7, H, Q)?`), order of
  `tools/genmenu.py` `MENU_ORDER`; the H screen follows the same order;
  the tests answer through `menu_keys` (region number translated).
- Loading page: an empty line below the title.

### Neowilderness: lighter loading page and menu

- Loading page: title, machine, authors, the goal in two lines and
  "HELP LISTS THE COMMANDS."; the eleven command lines are gone (HELP
  gives them in the game).
- Scenario menu: one line per region (number, name, terrain and
  temperature, best score in a `BEST` column) instead of three; no more
  fauna sentence or snow line, no more asterisk; `7 FREE
  JOURNEY`, `H HALL OF FAME`, `Q QUIT TO PRODOS` on two lines; prompts
  on line 12 (`MENU_ROW`). `hm_best` writes the score at column 35 of
  the scenario's line.

### Neowilderness: whole constellations and dark night

- Catalog **by figures**: 42 complete constellations (262 stars, down
  to V 4.95: bowl of the Little Dipper, Hyades, Gemini, Sickle, Lyra,
  Keystone, Corona Borealis…); the 44 added stars replace the 44 faintest
  isolated stars (still 282 stars, 846 bytes).
- Selection class = figure (class 0: figures and V < 2.0; 1 and 2:
  filler): the full Moon shows the whole figures; a full list loses the
  filler first; index compared on 16 bits.
- Magnitude in the pixel: three rows for the first magnitude (two
  entries), two tinted rows below V 3.0, one grey row beyond.
- Compressed projection above 45° (equal in sin h up to 86°): the
  Big Dipper and Cassiopeia stay visible at their culmination; the Moon
  keeps its perspective.
- **Dark blue** sky on a dark night: the ridge stands out in silhouette.
- Rotations **scroll on a dark night** as by day (`turn_view` no longer
  redraws the whole view): 35 columns per 22.5° step.
- Module 2,367 bytes (+30), `SKYRES` 482 (tables in WILDLO); reference,
  IIe bench, in-game tests and [STARS.md](docs/STARS.md) § 14 up to date.

### Neowilderness: reorganised status bar

- Left panel: `HEALTH 100%` alone at the top, the alert or the hint
  (SHIVERING, ITEMS: INV, TOPO / HELP…) below it. Right panel: the time
  (or the period without a watch) followed by the day of the stay
  (`7:00 DAY 1`; STATUS's day of the year minus 125, plus 365 at the turn
  of the year) at the top, the most pressing need below it
  (`HUNGER OKAY`, `THIRST SO-SO`: whichever of the two is worse, hunger on a tie;
  the other stays in STATUS). The right panel starts 4 pixels after the
  ribbon (`UI_GAP`).
- Module `wildhud.bin`: 1,941 → 2,021 bytes (80 fewer in the stock of each region); `tools/dhgr_ui.py` (width
  per panel), `test_interface.py`, `test_clock.py` (day of the stay,
  including the turn of the year) updated.

### Neowilderness: integration of the parallel branch

A second implementation of the port (branch `worktree-neowilderness-lot4`,
same base, 78 textual conflicts) was reviewed; its contributions are
transplanted by hand, without a merge ([IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
"Integration of the parallel branch").

- **Resident fine geography** (the branch's lot 5, `9795a58`): on a
  native map (Sierra comparison, `mkmap.py --native`), a `coarse` atlas
  of 154 16 × 16 tiles (Sierra 6,379 bytes, generated map 6,113) and its
  decoder `src/geoaux.s` (843 bytes) are loaded by `NEOWILD.R2` into the
  auxiliary language card (bank 1 view); 4 tiles in cache; 203 cycles
  per query, ≤ 46.5 ms per decode; Sierra game towards the rangers: 53
  commands, 14 decodes, no MLI call. `NEOWILD.GEO` and `geo_load`
  disappear.
- **Memory verdict** ([GEOGRAPHY.md](docs/GEOGRAPHY.md) § 9): the atlas
  does not fit in the module stock (≤ 1.75 KB free per region); it shares
  the TOPO snapshot area according to the map: the six shipped regions
  (inherited maps) keep the snapshot (return 0.24 s), a native map takes
  the atlas and TOPO redraws the view (6.1 s). Nothing is taken from the
  stars, the regions or the hall of fame. A native map, impossible to
  build before (97 blocks of `NEOWILD.GEO` on top of the packs), fits in
  260/280 blocks; `make test-original` (`test_adventure.py --scenario
  all`, 83 points, 0 deviations) becomes playable again.
- Memory ([MEMORY.md](docs/MEMORY.md) § 9.10): free resident main RAM
  181 → **361 bytes**; auxiliary stock +12 bytes per region (Burma 278);
  shipped disk unchanged, 247/280 blocks.
- Tests added to `make test`: `test_journey_resident` (crash → rangers
  at the keyboard, zero MLI, RAM copies, stack, new day, care, swimming,
  then hall of fame after the end key; replayed on a native map),
  `test_screen_returns` (nine identical screen returns, exact modules),
  `test_geo_resident`, `test_geo_atlas`; `test_prodos` checks zero page,
  bitmap and RESET vector at the final QUIT; `test_resident` and
  `test_graphical_topo` replay on a native map; `test_walk`,
  `test_interface` and `test_weather_front` take over the branch's fixes
  (read of `weather_day_level` by label).
- Tools: `mkmap.py --fine/--native`, `inspect_disk.py` (geography
  area), `profile_actions.py` (queries and decodes),
  `profile_loading.py --map`; `build_disk.py` packs in `lz` by default,
  like the Makefile.
- Discarded: the branch's status bar, TOPO and player P marker (`main`
  has its own and follows the original), the branch's rebaselines and
  README (different architecture).

### Neowilderness: more populated sky (lot 7)

- Catalog of **282 stars down to V = 3.50** (79 Hipparcos unchanged +
  203 from the *Bright Star Catalogue* 5th ed., CDS V/50; T CrB and Mira
  left out), 3 bytes per star (class deduced from the index, right
  ascension in quarters of a view unit); visible list of **160** 2-byte
  entries in 36 buckets of 16 units ([STARS.md](docs/STARS.md) § 13).
- Hourly module in the SIM window (`$97CE`) with the head of the catalog
  (directory entry 24, 462 bytes, in the auxiliary card's hole); quarter
  squares, hour products and line table in BSS; list and drawing in
  bank 2 of the main card (`$DE18-$DFFE`).
- Stars drawn in the `game_stars_*` captures: Sierra north 2 → 10,
  Sierra south 7 → 31, Bolivia 10 → 37; full Moon unchanged (2: Antares,
  Spica, first-magnitude rule kept).
- Costs: hourly computation 0.33–0.34 s in the game (0.38 s in the
  bench's worst case; before 0.17–0.21 s), drawing 1.4–1.5 % of a
  dark-night view.
- Memory: free main RAM 86 → 181 bytes; module stock −1,047 bytes per
  region (Burma 266, Sierra 1,510; MEMORY.md § 9.9); volume
  247/280 blocks.

### Neowilderness: stars, score and hall of fame (lot 7, steps 5–6)

- Night stars in the game ([STARS.md](docs/STARS.md)): hourly module
  `wildsky.bin` (ID 25, 1,984 bytes) recomputed at the first night view
  after each `sky_position` (`stars_stale`); list of 32 stars in
  WILDLO; drawing per column (`stars_frame`, `stars_column`) **run in
  bank 2 of the main language card** (`$DF00`); Polaris in the Sierra,
  Southern Cross in Bolivia. No stars by day, at dusk or under the
  clouds; first magnitude under the full Moon; all of them on a dark
  night. Rotations: only the revealed columns are redrawn.
- Memory: ProDOS 8 only keeps its QUIT code (`$D100-$D3FF`) in main
  bank 2 (measured); `$D400-$DEFF` joins the module stock (new source of
  `mem_fetch`, bit 5 of the loader's record type) and `$DF00` receives
  the drawing code. Free auxiliary RAM: 1,313 bytes with Burma (worst
  case), 2,557 with the Sierra; main RAM 86 bytes (`docs/MEMORY.md`
  § 9.7, § 9.9).
- Measured costs: +1.6 to 1.9 % per dark-night view, 0.1 % by day,
  0.17 to 0.21 s per game hour at night (`BASELINE_DHGR.json`,
  `lot7_stars`).
- Score and hall of fame ([HOF.md](docs/HOF.md)): patch
  `docs/hof_integration.diff` applied. Every ending (death, arrival, QUIT
  then Y) reads `NEOWILD.END` (module `wildhof.bin`, 3,044 bytes,
  `$9600`): summary, score, name entry, write of `NEOWILD.HOF` (one
  block, rewritten in place), then return to the menu; the menu shows the
  `BEST` read from the file and the `H` screen the six tables. The free
  journey is never ranked, nor is a zero score.
- Volume: `lz` packing by default (`BOOT_PACKING`): 246/280 blocks,
  **34 free** (11 with `auto`); choice → first view 9.2 to 9.8 s, menu at
  23.3 s from power-on.
- Tests: `test_stars_game.py` (resident list and views against
  `stars_ref`/`dhgr_ref`, Polaris, clouds, noon, full Moon, rotations,
  zero MLI), `test_stars_ref.py` and `make -f stars.mk test`,
  `test_hof_game.py` and `make -f hof.mk test` in `make test`;
  `dhgr_ref.Sky(stars=...)`; `test_sky.py`, `test_moonlight.py` and
  `test_sprites.py` (the compared night views contain the stars),
  `test_prodos.py` (one key at `hof_key_wait` after QUIT, nine arrows in
  Bitsy Bye), `test_menu.py` (empty hall of fame, six `BEST -`),
  `test_pack_boot.py` (`NEOWILD.END`, `NEOWILD.HOF`, main card),
  `test_boot.py` (source 3, contents of main bank 2 next to ProDOS's
  QUIT code). Captures `build/dhgr/game_stars_*.png`
  (`tools/game_shots.py --stars`).
- Lot 8: requirement noted in [MENUS.md](docs/MENUS.md) § 4 — the
  joystick control will have to make much better use of the four
  80-column text lines.

### Neowilderness: fauna, colours and texts per region (lot 7, step 4)

- Four species loaded: the TRAVEL sweep reads the rates and filters of the
  pack's four records (`fauna_travel`), OUTDOOR their reaction thresholds,
  names and flags (`fauna_reactions`), PROJECT the sprite sizes
  (`proj_sprites`); fourth species of Burma and Bolivia (module 23); order
  of the draws unchanged (`docs/logic/animals.md`).
- Palettes per region (`dhgr_palette.REGIONS`: ground, snow, water, crowns
  per mood; sky and night unchanged) and colours of the 15 new animals,
  tables `dhgr_tables_rN.bin` loaded by the pack ([DHGR.md](docs/DHGR.md)
  § 12).
- Texts: start message with the region and its fauna, species names in
  the reactions ("THE TIGER INJURES YOU AND STAYS.").
- **Named stop cause**: an interrupted walk, swim, rest or wait no longer
  says "A DISCOVERY INTERRUPTS YOUR ACTION." but what happened: the
  region's species ("BEAR IN YOUR AREA!"), the resource found ("YOU FIND
  FISH.", game, insects, fruit, cactus, mushrooms, plants, nuts) or the
  natural shelter ("YOU FIND SHELTER.") (`module_fauna_cause`, PROJECT;
  `test_feedback.py`).
- Memory: −131 auxiliary bytes per region (fauna tables −69, named cause
  +200); volume 246/280 blocks (`docs/MEMORY.md` § 9.6).
- Tests: `test_fauna.py` (filter cases of the five other regions, fourth
  species, trinkets), `test_dhgr_mood.py` (moods of the six regions),
  `test_menu.py` (texts, fixes, colours, each species drawn),
  `test_feedback.py` (named causes). Screenshots
  `build/dhgr/game_region_rN_*.png` (`tools/game_shots.py --regions`).

### Neowilderness: region packs and start menu (lot 7, steps 2–3)

- `NEOWILD.DAT` becomes a common trunk; six packs `NEOWILD.R1`…`R6`
  (15 to 18 blocks) carry the map, the woods, the 2 to 4 animal sprites
  (module 23 for the fourth species), the animal records of the region
  header (in the auxiliary image of SITES), the DHGR tables, the region
  texts (`$5780-$57FF`) and the module directory; only one is read.
  Wreck and cabin stay common. Volume: 37 free blocks.
- Start menu in `NEOWILD.SYSTEM` after the trunk: six scenarios (name,
  terrain, climate, fauna, best score "-"), free journey (region, level,
  fresh randomness; `MAP+33` = 1), hall of fame pending, ProDOS; level
  1–10 (RETURN = 4, written to `MAP+22`). The introduction comes back with
  the region while the pack is read. Choice → first view: 9.5 to 10.2 s;
  menu at 21.4 s from power-on.
- End of game (QUIT, death, arrival): back to the menu by relaunching
  `NEOWILD.SYSTEM` after restoring the system, with no state kept.
- Module directory: 26 entries (23 fourth species, 24 hall of fame, 25
  stars); fine geography native at IDs 32–55. Map longitude bounded to
  ±127 (New Guinea).
- Free auxiliary RAM: 676 bytes with Burma, 1,920 with the Sierra; the
  stars module (1,984) does not fit there yet (`docs/MEMORY.md` § 9.3).
  Main RAM: 340 bytes free.
- Tests: `test_menu.py` (six scenarios from the keyboard, free journey,
  level, `H`, `Q`), `test_boot`, `test_prodos` (back to the menu),
  `test_pack_boot`, `test_transfers`, `test_transitions` adapted;
  `common.py` answers the menu (`MENU_SKIP`). Profiling tools adapted;
  `tools/genmenu.py`.

### Neowilderness: scenario plan (lot 7)

- Survey of 13 October 2026: the six original regions are already on the
  Apple II disks (headers on track 0, sectors 9–14; 27 sprites on the
  Journey); the MS-DOS version only serves for cross-checking.
- Plan of lot 7 in [SCENARIOS.md](docs/SCENARIOS.md): start menu, region
  packs loaded selectively, stars drawn at night, score per scenario,
  hall of fame.

### Neowilderness: DHGR interface, 80-column text and TOPO in RAM (lot 4)

- Native DHGR banner, drawn in whole bytes (`dhgr_pack`): dark blue
  compass ribbon, white marks and ticks, yellow pointer (140-column band,
  4 azimuth units per pixel); black survival panels in a 7-row DHGR font
  (`tools/dhgr_font.py`): grey labels, aqua/yellow values, warnings white
  on a red band instead of HGR inverse, light blue hints. No more doubled
  HGR pixels or fringes; same information and same alert rules.
- The four message lines, the simulation curtain and MAP are in real
  80-column text (game primitives at `$0200-$03CF`, a page free of ProDOS
  and the Monitor during play); a line accepts 79 characters. STATUS,
  INVENTORY, HELP and the end stay in 40 columns. MAP: two characters per
  cell, sites and player in inverse.
- TOPO computed on opening from the resident map (TOPOGEN,
  `src/topo_dhgr.s`, SIM window): hypsometric tints, 400 ft contours and
  2,000 ft index contours, water, shores, woods, landmarks, arrow and
  scale; bit-identical to `tools/topo_dhgr_ref.py`
  (`docs/TOPO_DHGR.md`). The 8 KB TOPO image and `graphical_topo.py`
  leave the volume.
- Screen returns without casting rays: snapshot of the view in the
  auxiliary language card under TOPO (return 0.24 s instead of a full
  render), INVENTORY without curtain (return 6.1 → 0.26 s); STATUS, HELP
  and MAP unchanged (6 ms). No disk read, no time advance.
- Name: introduction "NEOWILDERNESS" (inverse title), help
  "NEOWILDERNESS - HELP".
- Memory (`docs/MEMORY.md` § 8): 528 bytes free in main RAM (128 at lot
  3); auxiliary store 40,246 bytes, 1,738 free, 12,800 reserved for the
  snapshot; `NEOWILD.DAT` 53,847 bytes, 125 blocks free.
- Measurements against lot 3 (`docs/BASELINE_DHGR.json`, key `lot4`):
  VIEW −0.3 %, LOOK R +0.4 %, LOOK B +0.5 %, rotations +0.8/+1.5 %, STATUS
  +1.0 %, WALK 1 H +3.2 % (MAP and messages in 80 columns); TOPO 2.99 s
  on opening, 0.24 s on return; identical states.
- Tests: `common.py` reads both text pages and `RD80VID`
  (`text_screen` in 80 columns, `map_rows`, `text_writes`,
  `text_changes`); `test_hud` against the native ribbon; `test_interface`
  and `test_clock` through `tools/dhgr_ui.py`; `test_graphical_topo`
  against the TOPO reference; `test_reference_state` excludes the
  module-loading counters. Screenshots `build/dhgr/game_ui_*.png`.

### Neowilderness: DHGR landscape (lot 3)

- The landscape is drawn in 16-colour DHGR on a single page
  (`$2000-$3FFF` main and auxiliary, `80STORE`, bank chosen by `PAGE2`):
  same projection, same 140 rays, one ray per colour pixel.
- Ten moods chosen at each frame (`select_mood`) from `sun_alt8`,
  `moon_alt8` and `moon_phase` (new, computed every hour by
  `sky_position` in integers) and the clouds: sky in five dithered zones,
  ground, snow and water in three distance steps, dithered woods,
  coloured sun, white or pale yellow Moon, original sprites coloured and
  shaded.
- Night: the HGR rule (`view_dark`, only the full disc gives light) is
  kept for the game; the light of the full Moon is graded (high, low,
  veiled, below the horizon).
- Read-modify-write passes per column, two OR registers for even/odd
  lines: the dithering costs nothing; checkerboard anchored to the azimuth
  for exact rotations. Scrolling and clearing in bands of eight lines, in
  both banks.
- Compass banner and survival panels: HGR drawings, doubled pixels,
  yellow index. TOPO stays in plain HGR; STATUS, INVENTORY, HELP and MAP
  in 40-column text; the four message lines in 80-column cells, printed
  by the game's own 40-column primitives (the Monitor switches to 80
  columns as soon as `80COL` is active).
- Memory: the removed HGR code (≈ 2.4 KB) pays for the DHGR code; 128
  bytes stay free in main RAM, the auxiliary RAM is unchanged;
  `NEOWILD.DAT` 53,031 bytes, 127 blocks free. Double buffering
  impossible (16 KB required), measurements in `docs/MEMORY.md`.
- Measurements at 1 MHz against HGR 128 KB (`docs/BASELINE_DHGR.json`):
  VIEW +3.6 %, LOOK R +4.3 %, LOOK B +3.0 %, rotations +4.6/+5.4 %, WALK
  1 H +2.2 %, STATUS unchanged; states identical to the HGR reference.
- Tests: all image comparisons read both banks and follow
  `tools/dhgr_ref.py` in the recorded mood; `tools/view_ref.columns`
  and `tools/forest_ref.py` provide the band events and the tree crowns;
  new `test_dhgr_mood.py` and `test_dhgr_video.py`; screenshots
  `tools/game_shots.py` → `build/dhgr/game_*.png`.

### Neowilderness: ProDOS 8, 128 KB and modules in RAM (lots 1–2)

- Sync with the head of `../wilderness` (text/HGR transitions,
  introduction kept during loading, SIM loaded before the SWIM shore
  probes, test expectations updated).
- ProDOS volume `dist/NEOWILDERNESS.po` (280 blocks, 132 free):
  `NEOWILD.SYSTEM` checks for an enhanced IIe/IIc 128 KB, keeps the
  introduction, takes the auxiliary memory (`dev/lib/prodos/video.s`, /RAM
  erased only if it is empty or after Y) and reads `NEOWILD.DAT` in 17 MLI
  calls. Compression chosen by measurement: first playable screen 45.1 →
  28.9 s.
- All modules, the blank simulation and TOPO preloaded in auxiliary RAM;
  `overlay_load` copies the blank image (at most 17.2 cycles per byte);
  WILDSIM leaves `$2000-$3FFF` for `$9600`, reserved for the future DHGR
  page. No more DOS 3.3 calls or disk reads during play.
- QUIT and Ctrl-RESET: text, banks, /RAM reformatted, bitmap, RESET vector
  and zero page restored, back to the ProDOS launcher.
- Counters `mli_calls`, `mli_reads`, `mli_bytes`, `xfer_count`,
  `xfer_bytes`; `overlay_reads` counts the module loads.
- STATUS 8.90 → 0.24 s, LOOK R 7.99 → 1.85 s, WALK 1 H 70.71 → 9.10 s,
  state and image identical to the HGR reference (`docs/BASELINE_128K.json`).
- Tests: boot on //e, zero disk access, transfers, ProDOS cycle, state
  comparison with the HGR reference; memory map `docs/MEMORY.md`.

### Text and HGR transitions

- The HELLO explanation text stays on screen during decompression,
  initialisation and the first render. DOS can no longer scroll the twenty
  welcome lines; the empty curtain starts after this first view.

- Boot, VIEW, full scene changes and the return from TOPO hide the drawing
  until the last column; partial rotations keep their progressive
  scrolling.
- Before a SIM or TOPO load, the top twenty lines are cleared before the
  switch to text. The old STATUS/HELP pages no longer reappear during the
  computations; the command, the results and the cursor stay.
- STATUS, the medical detail, INVENTORY, HELP and the final summary
  prepare their first page behind the landscape. The keyboard reveals the
  finished page.
- The menus share the differential writes of MAP, with clearing of line
  ends, tab spaces and unused lines. An identical page writes no
  character; a short page keeps no old object.
- Returning from the menus clears the four text lines before showing HGR.
  The restore after simulation shares the day/night/cabin render and
  keeps the action results, with no confirmation or extra delay.
- The video initialisation and the projection cache are moved into ADV;
  unused data and the unused screen return are removed to fit in 48 KB.
- `test_transitions.py` checks the screenshots of the intermediate steps,
  the preservation of the state and the exact writes of the menus. The
  test breakpoints now wait for the keyboard after the page is prepared.
- The SLEEP disk contract is corrected to fourteen reads, also measured on
  the local reference before these changes; the transitions add none.

- SWIM loads SIM before its first shore probe, even without movement;
  starting or repeating SWIM on dry land no longer jumps into HGR memory.
- The route, fauna and weight fixtures use the native raster, random
  generator and loads already present.

### First minutes and built-in help

- The welcome suggests INVENTORY, STATUS, TOPO and HELP to join the rangers.
- HELP splits movement, equipment and survival into three pages: command
  examples, slots and a warning about DROP of provisions.
- Selection 1/2/3, circular navigation N/Space/B and return Esc/Return,
  in the 2 KB screen module without changing the simulation rules.


### Visibility at full moon

- Nights when the lunar disc is fully lit keep a black sky, with relief,
  trees, wreck, cabin and animals visible. The other phases keep the
  darkness. The survival computations keep the night.
- Regression independent of the terrain and sprite pixels, under a clear
  or cloudy sky; the woods stay visible at full moon.

### Site direction consistent with TOPO

- Distant projection of the cabin and the wreck: north/south axis
  corrected to follow the terrain, the walk and the TOPO map landmarks.
- Regression independent of the projection model: eight directions per
  site, TOPO landmarks read on screen, compass, visible pixels in front
  and no sprite when looking behind.


### Animal reactions inspired by the original engine

- Sierra noise, injury and combat thresholds checked against ROM: noise
  ineffective on the rattlesnake, bear/cougar sensitive to noise,
  axe/knife grouped as in the native weapon choice.
- Bear/cougar severity checked against ROM: cuts, broken arm/leg and
  shock, linked to the health curves and to the care; higher outcome
  grouped into shock.
- Contamination draw corrected: the state changes at each drink of
  untreated water, without using the animal randomness.
- SCARE and ATTACK can fail; two combat draws allow a successful defence
  with injury. IGNORE can leave the animal present.
- Bear/cougar can steal exposed food: hung stores, water, equipment and
  distant piles kept; load and totals recomputed.
- Injury risks by posture checked against ROM: wait/rest/meal on the
  ground, IGNORE and tree. Climbing no longer prevents injuries; warning
  shown, hung provisions kept and care possible in the tree.
- Cabin protects player/provisions;
  reaction reported and action interrupted after one hour without decision.
- Probes `re_animal_reactions_probe.py`, keyboard scenarios
  `test_animal_reactions.py`; adaptations and limits in `docs/logic/animals.md`.

### Adventure, resupply and summary

- `DONE` and remaining distance replace the ambiguous `GOAL` in STATUS;
  distances with fractions of a cell, bounded progress and native score
  kept.
- `FILL/REFILL CANTEEN`, neighbouring bank, 64 OZ capacity, 10-minute cost
  and atomic refusal of overfilling; contamination of drunk water and
  separate randomness.
- SCARE/IGNORE/ATTACK reactions, targeting by species, tools, cuts/bites
  and attack after one hour without reaction; hung provisions and
  protection by the cabin. These reactions and the contamination are
  documented rules of the port.
- Banner for low water reserve and reaction to an encounter; HELP
  extended.
- Dedicated arrival/death screen: duration, steps, encounters, health,
  provisions and native efficiency score, kept until a key is pressed.
- Two extra disk modules, WILDADV and WILDOUT; simulation and existing
  commands stay in their windows and the boot in two packs.
- Purple/green palette confirmed as the engine's choice, sprite colours
  and terrain render kept.


### Reduction of module transfers

- Simulation and wreck/bear/cabin sprites compressed, resident in-place LZ
  decompression: 32→22, 8→6, 4→2 and 5→3 data sectors read.
- Allocations kept, BLOAD lengths reduced: placement of the following
  files preserved. Small modules kept raw after measuring the native cost.
- Projection tables reduced to one stored table and a cache rebuilt at
  boot; 24,976 resident bytes, a 16,303-byte pack in two files.
- LOOK R at 7.26 s; rest/sleep almost unchanged at 21.11/22.70 s, walk at
  26.96 s. The decompression absorbs almost all the disk gain.
- 20 native loads checked byte by byte, with text, zero page/FAC and
  memory bounds kept; states and images of six commands identical.
- Direct durations 1–255 H/MIN of REST/SLEEP/WALK/SWIM validated in the
  resident code; full reader kept for keyboard input, other forms and
  errors.
- One WILDINP read avoided: REST 1 H at 21.12 s, SLEEP 8 H at 22.71 s,
  WALK 1 H at 26.95 s; states and images identical.
- Two redundant graphics tables removed (280 bytes) to house the resident
  input; extra render cost of 0.004 s.
- Compression dictionary shared between neighbouring regions: boot kept
  in two files (16,369 bytes); resident code reduced by eight bytes.
- 799 native durations and the 140 pixel pairs checked; zero, errors,
  cancellation, general input, DOS memory and full restoration kept.

### Cost audit and native copies

- LZ copies of the loader indexed by Y; pointers and counters updated once
  per sequence. Engine ready at 19.42 s; first prompt at 40.91 s.
- Immediate zero-slope division; removal of the double clear and of the
  second banner during the outdoor night restore.
- VIEW at 5.62 s; night DRINK gains 0.14 s. Resident: 25,261 bytes,
  compressed into 16,276 bytes in two files; four net bytes added.
- Profiling of the commands by memory area: DOS still absorbs 68 % of
  sleep and 77 % of the walk. States and pixels compared without
  difference.
- 8,256 divisions and 40 copies tested natively, as well as the single
  night clear; page crossings and overlaps covered.

### Disk II loading

- LZ compression optimised per block, taking the flags into account, full
  4,095-byte window and removal of the arbitrary output cuts at 4 KB.
  Decompressor and Apple II memory identical.
- Boot packed into 16,272 bytes in two files instead of three;
  nine-sector interleave with a physical skew of one sector between tracks.
- Arrival in the engine: 23.48 → 20.83 seconds; first prompt:
  45.89 → 43.26. LOOK R: 8.08 → 7.36; eight-hour sleep: 25.83 → 25.30.
- Disk II measurements corrected to stop the capture before the first
  BLOAD. 1,023 compression cases compared with an exhaustive search,
  format and window limits, DOS integrity and native restoration checked.

### Memory walk of the render

- Tree search stopped for the rest of the ray after its distance limit or
  the selection of a crown; reactivated at the next ray.
- Clearing by contiguous lines, with HGR addresses computed once per line;
  banner, cache, memory holes and kept columns protected.
- 32 bytes of redundant pointers removed, with no new index computation in
  the unrolled fill; total resident code reduced by 14 bytes.
- VIEW: 6.20 → 5.64 seconds, LOOK R: 8.28 → 8.08, eight-hour sleep:
  26.39 → 25.83. Identical states and pixels, DOS reads unchanged.
- Regressions on each byte of an HGR page, partial/full clears, tree
  search budget and reactivation between frames.

### Speed and lifetime of data in memory

- 170 bytes of an off-screen render table recovered for resident LOOK and
  the screen shortcuts, with the pixels kept. VIEW no longer reloads the
  vocabulary and the sprite: 12.47 → 6.20 seconds. LOOK R goes from 10.43
  to 8.28; STATUS at the start from 12.27 to 3.76.
- Astronomical temporaries reusing 68 bytes of the DOS buffer outside the
  loads; sky outputs always resident. Five-byte insulation cache,
  invalidated by the clothes worn or the wetness mode.
- Reproducible measurements in cycles and reads with profile_actions.py,
  comparison of states and pixels before/after, 76 thermal transitions
  and preservation tests across the loads.
- The Apple II+ 48 KB stays the target; the floating-point routines and
  the roundings of the simulation are kept. Sleep stays close to 26.4
  seconds.

### Survival banner and direct access to the screens

- Danger alerts, VERY hunger/thirst and health under 40 % in inverse
  video; improvements in normal text to tell their importance apart
  without colour.
- TOPO/HELP hints by day, REST/HELP at night and LOWER FOOD near the hung
  bag, after the dangers and the shelter or tree hints.
- Shortcuts shown to go directly between HELP, INVENTORY, STATUS and
  TOPO. STATUS navigation fixed to the last two lines.
- Check of the alert pixels and of the nine direct transitions, with the
  time, the reserves and the visible image kept.

### More readable help and inventory

- HELP shows two pages, movement and survival, with command examples,
  units and navigation keys. Keys 1/2 select a page, N/Space and B change
  page, Esc/Return show the landscape again.
- Help titles and inventory group in inverse video; number of objects,
  FREE capacities and paging commands shown explicitly.
- Browsing checked from the keyboard, without advancing time or changing
  the reserves, the health or the landscape.

### Alerts recovered before display

- An improvement now replaces the worsening alert still pending for the
  same category, instead of showing an outdated warning.
- Regressions for hunger, thirst, health, temperature and immersion; the
  still active alerts of other categories keep their priority. The
  ranking stays without effect on the simulation.

### Result of the waiting commands

- WAIT and PAUSE announce "YOU WAITED" in hours or minutes, instead of
  "YOU RESTED"; their lack of rest credit is kept.
- Regressions on both units, the identical effects of WAIT/PAUSE, the
  separate credit of REST and the cancellation of a zero duration.
- Texts reorganised in memory without an extra disk read for sleep; its
  five reads and its final state stay checked.

### Forest limit in the information screens

- TOPO and STATUS use the map's tree altitude limit, like the 3D view and
  CLIMB TREE, instead of a constant of 11,000 feet.
- The value zero keeps the historical limit of 11,000 feet. Regressions
  below the limit and exactly at it, for three limits, checking the T/t
  symbols, WOODS/SCRUB and access to trees.

### Direct value of NATURE

- `NATURE 0` now disables new encounters, like the value zero typed at
  the prompt; the direct command was refused by the list of numeric
  actions and kept the previous frequency.
- Values 0–100, spaces and input at the prompt checked. Out-of-range
  numbers, decimals and units are refused without changing the player's
  state, the frequency, the landscape or the randomness.

### Objects on the ground in the banner

- "ITEMS: INV" disappears after picking up the last object or consuming
  the last reserve on the ground, as in the inventory.
- The summary no longer takes the rope counters and other equipment for
  reserves on the ground; exhausted foods no longer count either.
- Regressions through real commands on rope, axe, eggs and water.

### Projection of sites at the foot of cliffs

- A cabin far below the view no longer reappears on screen when the
  computation of its height exceeds 16 bits.
- Regression on nine cliff heights and three orientations, compared pixel
  by pixel with the independent projection model.

### Duration of encounters during still actions

- Encounters already present also age during WAIT, meals and sleep; they
  expire at 60 minutes, even without movement.
- No new fauna draw during these actions. Regression on a wait, a meal and
  two rests, with presence at 59 minutes, disappearance at 60 minutes and
  random generator unchanged.
- NATURE joins the input module; this frees the space needed in the
  simulation module and avoids loading it for this setting.

### Alerts after a drink

- DRINK immediately updates the thirst and dehydration state used by the
  banner, without waiting for an action that advances time.
- A dehydration cleared by the drink no longer stays on screen; tests of
  healing, of thirst improvement and of persistent dehydration, with
  stocks debited only once and time/health kept.

### Going back between inventory groups

- From the first page of a group, B goes back to the last page of the
  previous group, instead of jumping directly to its first page.
- Regression on the move bag → ground → back to the bag, with two pages
  of objects in each group; time and stocks kept.

### Illness alert gone stale

- An illness gone before the banner refresh shows "ILL IMPROVED", instead
  of causing a false "EXHAUSTION" alert.
- Regressions on the three healings, a persistent dehydration and the
  illness replacements between two displays.

### Clock minute

- The banner and STATUS round the total of minutes before extracting
  hour/minute: WALK 19 MIN from 7 o'clock now shows 7:19, instead of 7:18
  when the float is slightly below the whole minute.
- Carries to the next hour, noon and midnight handled together, without
  changing the simulated time. Regression on a real walk and seven values
  close to the minute and hour limits.
- Midnight shows as 12:00A in STATUS; the 12-hour format used to show
  0:00A because of the zero flag left by the comparison with 12.

### Exact end of the travel duration

- After the last requested step, WALK/SWIM stop without testing an extra
  step. The result reports the end of the duration rather than an
  obstacle (water, cliff or map edge) lying beyond the finished journey.
- The interruptions of the completed step (animal, night, shore, death,
  arrival) keep their priority. Regressions on three obstacles after
  exactly 19 minutes, on a swim ending at the map edge, on water met with
  one minute left and on animal/night at the last requested step.

### Numeric arguments of medicines

- `EAT FLAGYL 0 OZ` no longer consumes a dose despite the zero quantity.
  Medicines now refuse numbers and units added to EAT/DRINK, instead of
  ignoring them and applying a single dose.
- The refusal keeps stocks, time and medical state; it explains to remove
  the number and the unit. A normal intake stays available after the
  refusal.

### Bug hunt: input and test launch

- Numeric commands accept leading spaces like the ordinary parse:
  `  SLEEP 1 MIN` no longer produces an invalid value refusal.
  Regressions on rest, too-short walk and qualified DRINK WATER.
- `make test` rebuilds a2shot with its Makefile and its SDK paths,
  instead of using the implicit C++ rule that failed on `pom2/core.hpp`.

### Shorter wait during SLEEP

- Removal of the detour through the vocabulary and of the reload of the
  numeric parse for rest commands with a duration, as well as SLEEP alone.
- Eight-hour sleep on the initial scene: 32.1 → 26.8 seconds at
  1.023 MHz, with five disk reads instead of seven.
- Health, weather and simulated duration kept; comparison of the state
  and the landscape with REST, and check of the six rest and wait verbs.

### Fixes on cliffs and entering the cabin

- Overflow of the slope quotient multiplied by three rejected: trees
  lying far below a cliff no longer reappear in the sky.
- ENTER SHELTER refuses entry from a tree; CLIMB DOWN is needed before
  entering the cabin. The refusal keeps time, position and inventory.
- Refusal message in the tree fixed: its exclamation mark was interpreted
  as a substitution of the travel stop pattern. Same fix for the victory
  report without movement.
- Regressions on five rising/falling cliffs and on the chain climb →
  entry refused → climb down → enter → exit.

### Doses and care actions

- Signed count of the uses of the medical products, without overflow of
  zero or negative stocks; quantities shown in INVENTORY.
- Oral intake of FLAGYL, SALT TABLETS and QUININE through EAT/DRINK;
  refusal of oxygen, soap, creams, glasses and kits.
- SHIELD EYES and LOWER HEAD without duration; SUCK VENOM requires an
  active bite and takes 15 minutes. LOWER FOOD/BACKPACK keeps the
  retrieval of the hung bag.
- Commands moved into WILDMVI, with a resident return before the
  computation of care and time; the progressions stay in WILDMED.
- 130 extra cases on ROM: 90 signed counters, 12 care actions, 22 oral
  intakes and 6 USE/inventory/care chains on the last dose or an empty
  stock. The native prerequisite stays selected even without a positive
  dose; this behaviour is kept.
- Oxygen depends on the separate use flag: the last dose protects, but
  reusing an empty bottle disables this protection.
- Still to port: SPLINT, thermal care, placement/sterilisation specific
  to USE and the injury/illness triggers.

### Medical conditions and exposures

- Resident state of the 15 Journey conditions: incubation, health,
  healing with/without care and product of whole percentages.
- Prevention and treatment prerequisites, clothing protection, daily
  reset of temporary care.
- Salt/cold counters, strict thresholds and protected decay; sun and snow
  exposure connected to the port's data.
- Altitude sickness, oxygen and 30-minute ceiling in critical health or
  during the first eight hours of conditions 6–11.
- Medical USE, STOP BLEEDING and medical page of STATUS.
- WILDTRV for swimming, WILDMED for care/exposures, WILDMVI for the
  medical state, load computation moved into WILDSIM.
- Comparisons on ROM: 160 progressions, 66 care combinations, 60
  altitude cases, 80 cadences, 84 clothing protections and 59 salt/cold
  exposures, i.e. 509 cases.
- Still to port: complementary care, triggers by attacks/falls/
  contamination and exact sun/snow selectors.
- TOPO: legend shortened to preserve the progress while walking.
- Banner invalidated when WILDSIM borrows HGR; returning from STATUS
  restores the displayed pixels and the terrain cache. The tests tell this
  drawing apart from the unused graphics bytes used for temporary
  computations.
- Adventure pilot: acknowledgement of the native walking time supported,
  four scenarios completed with gaps always reported; 112 bounded wind
  evolutions compared with the original engine.

### Tree render fix

- Underside of the first profile brought back to the height of the
  central foliage: removal of the black side spikes that went down toward
  the ground.
- Separate crowns, centred in their cells: the native 32-column profile
  no longer covers two whole cells.
- Green/black foliage pattern restored, with opaque pixels and occlusion
  of the sun and moon; the profiles are no longer filled entirely in
  black.
- Black trunks under the centre of the foliage, anchored to the terrain;
  crowns raised by 18 pixels divided by the distance for near trees.
- Continuous black top outline and lower edging of the foliage to set the
  crowns apart from the purple sky and the green terrain.
- Foliage limit kept when the projected base goes past the screen,
  without overflow into a black fill on falling slopes.
- This limit stored outside the Applesoft rounding byte, to keep the
  exact duration computations after the trees are drawn.
- Visual check in the emulator and regression against continuous black
  bands, in addition to the pixel comparisons and the rotations.

### Climbing and hanging food

- `CLIMB TREE` / `CLIMB DOWN`: nearby tree, health > 2.5 to climb, walking
  and swimming refused in the tree; no time added.
- `HANG FOOD` hangs the bag and its contents for 30 minutes, with the
  native cost of 1.65 + 0.02 × body weight kcal/min.
- `GET BACKPACK`, `LOWER FOOD` and `LOWER BACKPACK` retrieve the bag at
  its cell; load checked and atomic restore on refusal.
- INVENTORY shows `HUNG HERE`; STATUS reports the tree and the hung bag.
- Probe of 24 CLIMB cases and 16 HANG cases in the original code on ROM;
  port tests on the shared stocks, the containers, the screens and the
  refusals.

### Trees and forests

- Wooded areas derived from the TMAKE contours and ported Sierra tree profiles.
- Projection attached to the world, clipping by the relief, priority to near sprites.
- TOPO, STATUS and fauna filters recognise woods and high-altitude scrub.
- 294-byte MAP extension, import of the TOPO forests, compatibility with old maps.
- Tests of the drawing, the rotations and the loading.


### Neowilderness lots 4 and 5 Survival, inventory and orientation

- Compass framed over its whole height, kept during rotations.
- Monochrome summary around the compass: time/period, health, hunger,
  thirst, transition alert or thermal state; shelter and objects
  retrievable here.
- Alerts at the existing thresholds, with no repetition while the class is
  unchanged and no change of the rules; long activities keep a priority
  alert.
- STATUS reorganised, with conditions before needs/environment and
  separate CARRIED/HERE reserves; maximal case readable without cutting a
  condition name.
- INVENTORY grouped by location, twelve objects/page, split reserves
  shown separately, permanent capacities and explicit navigation.
- TOPO: C to recentre, eight magnetic headings and the site under the
  player named.
- WILDHUD/WILDSTA in the 2 KB window; banner kept during render and
  rotations, fauna handled before its composition at boot.
- `test_interface.py` checks display, transitions, groups/pages/quantities,
  maximal STATUS, orientation/recentring and consultations without cost.
- Validation: full suite `make -C wilderness test` passed after the frame;
  disk rebuilt, render and memory checks included.


### Sun and moon as geographic landmarks

- Sun computed from latitude, season and solar time, independent of the
  magnetic declination; projected in the terrain axes.
- Night Moon from a 1985 reference ephemeris, with a stylised phase and an
  average parallax correction; an identified extension of the port.
- Masking by clouds, relief and sprites; the partial panorama by day and
  the dark view at night, which does not reveal the terrain, are kept.
- Initialisation moved into WILDSIM to respect the resident memory.
- `test_sky.py` checks positions, hemispheres/seasons, masking and
  rotations.


### Neowilderness lot 2 Readable refusals and results

- Hidden confirmations between messages removed: the next command keeps
  its first key. The result stays readable on returning to the view,
  during input, after Esc and after an empty line.
- Movement: effective duration and stop by water, shore, night, limit,
  animal, Esc, lack of time or terrain/pace combined. Death, victory and
  weakness keep priority; travel results keep their duration.
- Unknown verb reported with HELP; missing object accompanied by
  available examples; inaccessible object told apart from an
  unimplemented command.
- Consumption: stock accessible before the answer, then quantity actually
  consumed and initial stock. Transfers name the object as in INVENTORY
  and its new location, including qualified objects.
- Load refusal: weight, volume or both, excess and capacity after
  cancellation in OZ/IN3; carried, bag and hand volumes told apart.
  Arithmetic overflow told apart from a merely insufficient capacity.
  Missing bag/canteen, non-empty containers and a bag stored inside itself
  separated.
- WILDITM groups the transfers in 2 KB to free resident memory. The
  engine keeps the texts in three lines, without scrolling caused by a
  long name. `test_feedback.py` covers the refusal matrix, the maximal
  values, persistence, stock and the stops for animal/night.
- Validation: full `make -C wilderness test` passed, with the rotation
  optimisations, the TOPO writes and the shore crossings preserved.

### WALK / SWIM shore crossing

- WALK reported the water one cell before it, then SWIM refused its first
  half-step still on land. Two successive SWIMs thus stayed in place.
  This half-step is now allowed if the next one enters the water, with
  the route checked without movement or cost during the check.
- SWIM performs the last half-step toward land and stops on the shore,
  with the summary of the time actually spent and the end of immersion.
  WALK then allows continuing. SWIM without water ahead has no effect.
- `test_shore.py` covers the four directions, a fractional position, a
  diagonal route and two successive SWIMs up to the opposite shore.
- Validation: full suite `make -C wilderness test` passed, including swim
  routes and durations, thermal balance, Esc, TOPO and rotations.

### Neowilderness lot 1 Commands and cancellation

- Esc clears the command or cancels a numeric input, without quitting the
  game; QUIT requires Y after a warning about losing progress.
- The left arrow deletes a single character in quantities and durations.
  An empty or zero input cancels the action; NATURE keeps its zero
  setting.
- Direct arguments and units: WALK 10 MIN, REST 1 H, DRINK WATER 4 OZ and
  EAT CHEESE 8 OZ. The old questions stay usable; no unit = hours or
  ounces. Units, ranges and overflows are checked.
- Esc interrupts WALK and SWIM after a completed step, with position,
  health, reserves and effective time kept. Rest accepts minutes; its
  interruption during the activity stays an optional follow-up.
- Esc leaves each inventory page immediately, without waiting for a
  second key. STATUS and TOPO keep their return to the view.
- Module WILDINP at $5800; word walk moved into WILDVOC and HELP text into
  WILDSCR to stay within 48 KB, with no read added to the path of arrow
  rotations.
- `test_input.py` covers cancellations, atomic refusals, units, digit
  correction, screen exits, QUIT confirmation and walk/swim stops.
- Validation: full `make -C wilderness test` passed.

### TOPO writes only the changed characters

- Removal of HOME and of the systematic rewrite of the map at each step or
  scroll. Direct comparison with the text RAM before each write, for the
  relief, the landmarks, the coordinates, the legends and the spaces.
- Old characters at the end of a line removed without rewriting the
  spaces already present; messages and cursor kept during the walk.
- Tests of the writes actually executed: one write per changed character
  over twelve WALK steps and the scrolls; zero writes if the map does not
  change.

### Presentation during loading

- After the Apple II+ title, the screen presents the crash, the goal of
  reaching the rangers, the survival needs and the main commands.
- Durations in hours, quantities in ounces and rotations on an empty line
  are explained. Loading continues without waiting for a key.
- Presentation entirely in English, limited to twenty lines of under forty
  characters to stay visible during the DOS reads.
- Check of the text at the start and at the end of the loader, of the
  arrival at the playable prompt and of the restoration of the resident
  data by `test_boot.py`.

### Scrolling near sites and faster render

- The 22.5° and 45° rotations now reuse the geometry of a single distant
  site, even out of the field of view. The arrows load no module; only the
  uncovered columns are rendered. Scenes with several potentially
  neighbouring sites keep the selection by reprojection.
- Heading cache invalidated after scrolling to avoid reusing an old
  projection with an already shifted sprite origin.
- Direct walk of the physical lines for clearing and scrolling; removal
  of the useless sprite activation calls in the rays.
- Measurements: 77.0 % fewer cycles over 48 rotations near the cabin,
  compared with the forced full render; 4.7 to 11.5 % gain on the full
  render of the five check maps, with images identical to the reference.
- Rotation tests extended to distant sites, to masking by a ridge, to
  competing sites, to full turns and to the disk read counters.
- Validation: full `make test` passed, plus rotations of the distant
  wreck and selection of two sites at different azimuths; disk rebuilt.

### Sky, orientation and map while walking

- The sky and the relief again fill the sides of the ribbon. The landscape
  under the ribbon is kept in invisible HGR lines to avoid traces during
  rotations, with no extra memory allocation.
- TOPO now shows Y decreasing: north is really at the top, like the
  movements and the compass. The scroll keys follow this orientation.
- At each WALK step, TOPO recentres and refreshes in the first twenty
  lines. The messages, their cursor and the simulation are preserved; no
  reload or key wait between steps.
- Checks: real N/E/S/W movements and twelve consecutive refreshes during
  WALK, with a check of the preserved areas.

### TOPO: update before display

- The map is rebuilt before switching to text mode on opening, to avoid
  the brief appearance of the previous TOPO or STATUS screen.
- Check of reopening after scrolling, walking and rotating: recentring,
  position/heading, relief and landmarks read again from the current
  state; the 3D view and its compass ribbon stay intact on return.

### Permanent compass at the top of the view

- Removal of the `USE COMPASS` activation: the cardinal points are
  available from the start, with no deactivation during object transfers.
- 98-pixel ribbon centred at the top, with N/NE/E/SE/S/SW/W/NW, ticks
  every 22.5° and a fixed cursor. Continuous scrolling at one pixel per
  two azimuth units, taking the magnetic declination into account.
- Header reserved over 16 lines; it stays visible at night and at the
  cabin, and is not carried along by the terrain scrolling. No disk load
  or floating-point computation to update the ribbon during rotations.
- Check of the 560 azimuths, the north seam, the magnetic centring, the
  rotation commands and the returns from STATUS.

### View rotations

- Scrolling of the terrain and of the local sprites for the 22.5° and 45°
  rotations; only the incoming columns are recomputed. Geometry and
  masking of distant sites keep the full render.
- Sprite image restored after loading the LOOK vocabulary; the arrows
  avoid this load when the image is already in memory.
- Scroll loop shortened and a 141-byte sine table removed, with the
  roundings of the directions kept exactly.
- Test of the five sprites, exits/returns into the field of view and full
  turns in both directions. Over 52 rotations around the wreck:
  435,480,947 → 98,301,942 cycles, i.e. 77.4 % saved, identical pixels
  and text.

### Temperature: original slow variation

- Added `INT(5 × SIN(0.0187 × hours elapsed + phase))`, with the saved
  phase of the first Sierra journey and the roundings of the Applesoft
  ROM.
- 405 cases compared with the original T09/S08 routine: phases,
  durations, signed temperatures and crossing of the one-byte limit.
- The air now matches at the six points of the start scenario; the gaps
  go from 13 to 6, still on the wind and the wind chill. The daily cycle,
  the visibility and the weather fronts remain to be ported.

### Walking: wait and disk access

- Fauna grouped with the environment computations: two module reads per
  ordinary step instead of three when the fauna is active.
- Minutes travelled shown after each step, without a key to press.
- Test of a four-hour walk: progress, number of reads, return to the
  command and no extra reads at the stop.

### Terrain: rivers and lakes

- Plateaus now drain toward an outlet instead of triggering artificial
  lakes. Real basins are filled up to the overflow level, with a flat
  surface and a continuous outlet.
- Removal of the fill truncated at 300 units and of the water squares
  erased after generation around the crash and the rangers. A source
  covering these places is rejected before the terrain is changed.
- Conversion 224 × 168 to 112 × 84: each block keeps its water points,
  including at odd coordinates, at the water's height. The cabin also
  avoids these converted cells. The other TOPO markers are no longer
  interpreted as rivers.
- Tests of plateaus, small/large basins, thin rivers and 18 seed/difficulty
  pairs: continuity, descent and reproducibility. The drainage stays a
  reconstruction, to be compared with the original generator.

### Swimming: tracing oblique headings

- Continuous vectors replaced by the original's integer major axis and
  sine accumulator; the duration now tells apart each step that is really
  straight or diagonal. Trace state kept during module changes.
- 2,880 positions over 360 headings compared with the original routines on
  ROM.

### Swimming: effort and load

- The 19 minutes per cell replaced by the original's normal swim
  duration, which depends on health, load and whether the step is
  diagonal. SWIM now advances by half a cell; a last step can exceed the
  requested time if at least half of its duration remains.
- 143 durations identical to the original routines run on ROM; tests of
  the real command, of the duration overrun and of the return to the
  shore. New module `WILDTRV` to preserve the resident memory space.

- SWIM now uses the original cost tied to the total weight: about
  14.43 kcal/min with the initial equipment. The canteen water is no
  longer counted twice in this computation; shivering adds to this effort.
- 81 cases of weight, load and duration check the calorie expenditure;
  the metabolisms are also compared byte by byte with the original helper
  run on the ROM, and the calories with its energy routine. First swim
  health interval restored to 15 minutes. Test of the real command,
  immersion, rest in the water and exit on the shore. The injury/equipment
  modifiers remain to be reproduced.

### Comparison of commands with the original game

- New differential pilot on both Apple II executables: start, equipment,
  drinks, meals, repeated rests, night and first walk. Questions inspected
  before answering; errors and differences fail the test. Dumps, images,
  logs, symbols and reports stay in `build/`.
- Observation of the original state before its paging on Journey T04, to
  avoid mistaking the second HGR page for the physiology.
- Drinking from the canteen no longer takes time; eating takes 16 minutes,
  with the original food and water credits. The shivering of the initial
  save contributes to the first calories spent.
- Adaptive rest after the first 30-minute step; counters and deficits
  updated at the health cadence, whole percentages and initial Hmax kept
  at its original precision.
- Fix of the previous encounter rule: rest and meals draw no fauna. The
  draws and interruptions stay active while walking.
- Cardinal directions corrected by the map's magnetic declination. The
  random precision of the compass remains to be ported.
- `make test-original` still fails on the weather/night/walk gaps. No
  complete adventure up to the rangers is validated yet.

### Encounters during actions

This step came before the differential fixes above; the draws during REST
and its fixed cadence have since been replaced.

- Draw at each simulation step: 30-minute rest, walk/swim according to the
  step duration; removal of the accumulation limited to 255 minutes.
- All species are tested in the Sierra order, even if an animal is
  present; kept or replaced at 50 %, checked in the original.
- An accepted encounter interrupts walk/rest after the elapsed step, with
  exact time and a rest interruption message.
- No outdoor draw under shelter; VIEW/STATUS spend neither time nor
  randomness. The interruptions leave the sprite available for the next
  action.
- Probes of the original flags and deterministic scenarios of long rest,
  interrupted walk, replacements and cabin protection. Presence duration
  of 60 minutes and animal movements stay provisional.

### Sierra fauna and movement limits

- Filters of the three species: season, time, terrain, altitude, maximum
  slope of the 3 × 3 neighbourhood and regional climate index.
- Probability `minutes × NATURE × √difficulty × rate × 10⁻⁵`, with the
  original rates 80/40/100 and a generator independent of the weather.
- NATURE command: integer multiplier 0–100, initial value 1, higher values
  refused; nocturnal animals stay invisible at night.
- Difficulty and Sierra index in the map header; old maps compatible with
  the default values 4 and 31.
- Walk and swim stopped before the outer band of two cells, with an
  explicit message and no time charged for the refused step.
- Probes of the original code, scenarios per species and tests of the four
  sides. Draw cadence, presence duration, movements and reactions stay
  provisional; NATURE does not accept fractional values yet.

### Sites visible from a distance

- Wreck and cabin projected within eight cells: azimuth from their fixed
  coordinates, sizes in steps and anchoring on their altitude.
- Sprite inserted at the ray step matching its distance; the relief in
  front masks it, the relief behind keeps the sprite visible.
- Composition still per column, with no disk load in the rays, with the
  colours, transparency and black pixels of the original streams.
- WILDPRJ module to prepare the geometry and the terrain bounds; cache
  reused when position, heading and encounter stay identical.
- Full rotations near the sites, including when they are out of the field
  of view, to avoid missed appearances and traces of the partial scroll.
- Exact comparisons and approach/return routes on foot. Current limit:
  a single site per view, selected by distance in the field of view; the
  animals stay local and the projection is a rule specific to the port.

### Cabin and TOPO

- `ENTER SHELTER`, `EXIT SHELTER` and `LEAVE SHELTER` at the cabin; inside
  state kept during REST, rotations and STATUS/TOPO screens.
- Thermal protection of the found shelter: ambient air +15 °F, no wind,
  compared with the original branch; HUT stays a separate construction.
- Walk/swim refused inside, no encounters during rest under shelter and
  the outside view restored on exit.
- First text TOPO map of 32 × 14 cells: relief, water and
  player/wreck/cabin/rangers landmarks, with scrolling bounded by arrows
  or WASD.
- New disk module WILDSIT; qualifier resolution moved into WILDVOC to
  preserve the small resident memory margin.
- Route tested without a position change in memory: spotting, walking,
  entering, rest in the cold, exit and return; extra night tests and
  local probes of the original commands and temperatures.

### Per-column render

- Sprite and terrain composed in each column, with no overlay pass after
  the full view; disk load before the render.
- Fill limited to the transparent areas and rays stopped when the maximum
  relief can no longer contribute to the lines still visible.
- Reuse of the BLOAD text buffer for the 160 colours of the column, with
  opaque black pixels and rotations kept.
- Wreck moved down ten lines to recover its original vertical
  coordinates, without overlapping the text.
- Test of the intermediate image, exact comparisons on five maps and
  profiling of the ray steps and cycles outside DOS loading.

### Documentation

- TODO reorganised into ordered lots, with the terrain/sprite render fix
  as the first priority.
- README refocused on the playable state, the commands and the build.
- Porting reference gathered in `docs/IMPLEMENTATION.md`: provisional
  rules, memory, map format, tests and tools.
- Outdated mentions cleaned from the analyses and this history added.

### Original graphics

- Extraction of the Journey streams of the wreck, the cabin and the
  animals, with transparent PNGs and a manifest of positions/footprints.
- Sierra wreck, cabin, bear, cougar and rattlesnake sprites hooked into
  the 2 KB disk loading window.
- Wreck anchored at the start, cabin placed on land and first graphic
  encounters with an independent random generator.
- Colours, black pixels and transparency preserved; clipping, heading
  tracking, night masking and clearing on leaving the cell.
- Pixel-exact tests of the five images and of an encounter after REST.
- The cabin is visual and the animal behaviours remain to be ported.

### Immersion

- SWIM crosses water cells and stops before the shore; WALK reaches land.
- Losses from wet clothes, water temperature tied to altitude and
  immersed thermal balance; no sweat in the water.
- REST keeps the immersion; STATUS shows IMMERSED. A step on land resets
  the selector to dry. The swim cadence stays reconstructed.

### Wind and energy

- Signed wind-chill temperature shown in STATUS and used by the thermal model.
- Integer kcal expenditure per step; shivering supplement according to
  weight, with an effect on the food deficit and the basal metabolism kept.
- Comparisons of the wind and energy formulas with the original routines
  on ROM.

### Dry thermal model

- Body temperature according to air, activity and clothes; recovery
  bounded at 98.6 °F and drift threshold checked on the ROM.
- Deterministic reconstruction of the clothing layers and cold/heat health
  factors; activity stopped when health becomes fatal.
- STATUS shows body temperature, shivering/sweat and hypo/hyperthermia.

### Disk modules

- Vocabulary, screens and environment split into a shared BLOAD window,
  with a cache of the current module.
- Preservation of the zero page, the visible text, HGR and the game state.
- Hourly air and thermal model grouped to limit the reads during REST.

### Objects and load

- WEAR, GET/PACK, CARRY/TAKE and DROP/REMOVE: body, bag, hand and ground.
- Positions on the ground, pick-up on return, accessible quantities and
  qualifiers of shared names; compass disabled when it is put down.
- Weights and volumes per category, atomic refusals of overload/overflow,
  containers emptied before being put down and remaining capacities in
  INVENTORY.
- Model limits calibrated on the original's starting capacities; exact
  accounting of the containers still to be established.

### Playable base

- 3D terrain view, generated maps, rotations and partial scrolling,
  compared bit for bit with a Python reference.
- 280-word parser, walking, resting, meals, drinking, compass, STATUS and
  INVENTORY.
- Clock, date, sun, air, energy, survival deficits, health, death and
  arrival at the ranger station.
- Tests of random commands, night walk refusal and time computation on
  steep slopes.

### Graphical TOPO and local MAP

- TOPO/T shows an HGR sheet of the whole terrain: contour lines
  interpolated every 400 feet, water, woods and C/H/R landmarks, north at
  the top.
- MAP keeps the text window centred on the player, its scrolling, its
  recentring and its differential writes during movements.
- Each disk holds a sheet computed from its own map; closing TOPO
  restores the view without changing time, position or provisions.

### Movement tests aligned on the native rules

- Fix of the expectations gone stale in the input, cabin/orientation and
  long walk tests: half-cells and computed cadence.
- Explicit check of the budgets refused, exact and exceeded by the last
  admitted step, of the return to the cabin after rest and of the disk
  reads.
- Movement documentation updated; the native engine is kept.


## Moved out of TODO.md on 2026-11-16

### Lot 6 — sites

Done on 15 October 2026: the "site sprite" base, the log or the rock of
the natural shelter found on the native map, the ranger station
(CHANGELOG.md, MEMORY.md § 19). Remaining:

### Outside the lots: interface and game experience

- [x] MouseText pages on NeoWildernessXL (15 October 2026,
  [MENUS.md](docs/MENUS.md) § 9, MEMORY.md § 26); the 140 KB edition
  keeps its pages without a frame (user's decision). Still without a
  frame: HELP (tabs and footer only), the H screen of the start menu and
  the ADVENTURE end of game (40 columns, loader and store: no room
  without a tail or a read); the XL store has only 315 bytes left.
- [x] Bottom on TOPO or MAP: the top pages (15 October 2026, both
  editions, MENUS.md § 5).

## Historical margins (before EQUIPMENT; current measurements in MEMORY.md)

| Area | Free |
|---|---:|
| TEXT `$0A00-$0FFF` | 2 |
| WILDLO `$1000-$1FFF` | 0 |
| WILDGAME `$4000-$577F` | **0** |
| WILDERNESS `$6000-$6FFF` | **0** (XL: and 1 in `page_foot`, dead code of XL) |
| RESIDENT `$B600-$B9FF` | 5 |
| MENUCODE `$BA00-$BDFF` | 4 |
| LOWPAGE `$0200-$03CF` / LOWTEXT | 0 / 0 (the CAMP message table is there) |
| HICODE / MENUSWAP / main bank 2 | 3 / 0 / 24 |
| SIM under `$B500` | 107 |
| Auxiliary store, trunk space: XL / 140 KB | 8,833 / **2,239** (Sierra sprites: 192) |
| Disk used: XL / 140 KB | 369 / 1,600; **280 / 280** blocks (`read_volume.py`) |
| 140 KB NEOWILD.DAT before one more block | **360** bytes (122 blocks) |
| PROJECT (window `$5800`, 2,048): XL / 140 KB | **46** / 166 (shelter tail cut) |
| CRAFT (window `$9600-$A6FF`, 9 blocks; MAKE reads 4 of them: 68 free) / MEDICAL (`$5800`) | 167 / 25 |
| Shared STATUS (`$9600-$B0FF`, under STATX) / TOPOGEN (`$9600-$A1FF`, before `TOPOBSS`) | 82 / 75 |
| SUMMARY (`$5800`) / GRID (`$A300-$AFFF`) | 1 / 600 |
| XL tails (MENUS.md § 9.1): STATX (`$B100-$B5FF`) / CRAFTX (`$A700`, up to `$A7FF` for 9 blocks) / MEDVX / ENDX | 64 / 108 / 361 / 320 |
| XL STATUS on NEOWILD.BLK (`$9600-$B5FF`, 16 blocks at most) | 64 bytes (16 blocks) |


## Removed on 15 October 2026

Decided and done, in CHANGELOG.md ("fire until DOUSE"): feeding the fire.
The fire burns until DOUSE as in the original (lifetime `FIRE_LIFE`
removed); there is nothing to maintain, no command is added (CAMP.md § 8,
CRAFT.md § 8.6).

Done, in CHANGELOG.md ("lot 3, step 2"): the CRAFT page, the bow, the
spear, the club, the stone and the splint in the GET, DROP, USE lists and
the KILL queue of the grid, the ITEMS hint of the panel (CRAFT.md § 8.6,
MEMORY.md § 23). ATTACK with no weapon in use: the port's rule (axe or
knife accessible, without USE) is kept, a deliberate gap (decision of
15 October 2026, CRAFT.md § 8.2).

Done, in CHANGELOG.md ("lot 3, rest of step 1"): GET, PACK, CARRY and DROP
of crafted weapons; ROCK; one cell per crafted object left on the ground;
weapons against animals (brought forward from lot 11); the igloo at 35 °F
of the dangers. EXIT SHELTER of a crafted shelter: kept, a deliberate gap
(decision of 15 October 2026, CRAFT.md § 8.2).

Done, in CHANGELOG.md ("streamlined action menu"): the decisions
GET/TAKE, REST/WAIT, OUTFIT page (replaced by the WEAR toggle), MAKE
STICKS and BOIL with a fire from the verb review of 14 October.

## Removed on 14 October 2026

Done, already in CHANGELOG.md: resident crash → rangers route; resident
native fine geography; stars, constellations, populated sky; score and
hall of fame; "FREE JOURNEY: NOT RANKED" anomaly (`103bee3`); simplified
start menu; authors on the loading page; SAVE/RESTORE (lot 9); command
surface (lot 8 of MENUS.md, step 2); reserves of § 12.8 (VOCAB and
ADVENTURE in LZ, SCREENS removed, LZ decoder in bank 2, NEOWILD.BLK);
budget per region; instrumentation; safeguards of `test_prodos.py`;
common draw of the wreck (lot 1); LOOK STARS of the original (lot 7); lot
4 (hunting, fishing, gathering, meals); on 15 October: run-together
messages ("AREAIT IS TOO DARK"), tree triangle, animated fire
(CHANGELOG.md, MEMORY.md § 17).
Done: reserves of direction 3
(MEMORY.md § 12; CHANGELOG.md).

Obsolete: "140 KB only" disk policy (800 KB adopted, two editions);
removal of the SIM copy (set aside, MEMORY.md § 12.6, at the 5 %
threshold); "everything is still uncommitted"; DHGR windows instead of
the 40-column screens (steps 3-4 of MENUS.md, replaced by the 80-column
pages).

Checkpoints of the next lot: CRAFT/CATCH sequences; consistency between
hydration and medical treatment in the water fidelity lot. Returning to
the same care after reading the result is done (17 October). The meaning
of the three states, the duration and the conditions of the actions are
shown (17 October). The cumulative capacity refusals and their
need/available/shortfall figures are done (17 October). The explicit FIT
choice is done for the local provisions of the first game and GET WATER;
examine the other transfer classes. Precise sources, GET WATER
prerequisites, BACKPACK not carried and containers to empty done
(17 October).
The weight added/removed is shown, internal changes stay at zero, and
simultaneous weight/HANDS or weight/PACK overflows are tested with the
joystick (17 October).
The instruments show their light conditions, the compass/watch
replacement and the native effects of USE (17 October).
Bait of the CATCH devices, first-aid light, fuel and lighting of the
stove, weather/water conditions of the matches, lamp charge and
magnifying glass conditions are shown (exact solar angle checked on USE);
the position filter and the impossible actions of the bag
are done (17 October),
then replay on real hardware the joystick route
CRAFT → EQUIPMENT → CATCH → fire → COOK → meal → care →
save/restore → score. It is automated on XL with a deterministic
encounter, overload and walk refusals before the fire goes out,
cancellations and restore after reboot (17 October 2026).
Quick quantities by doubling, fine adjustment and exact ALL are done;
consumption keeps an explicit quantity (17 October).
The medical doses (one use with
stock/duration shown), LOWER FOOD from LOCAL HUNG, the water quantities,
the required volume, the detailed refusals of crafted objects and
EQUIPMENT as well as TASTE from the selected source and the preview of
the whole bag are done (CHANGELOG,
16 October).
