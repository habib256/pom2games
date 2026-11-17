# Neowilderness — remaining work

Port of Wilderness (Electric Transit, 1985) to the Apple IIe enhanced 128 KB
and the IIc, ProDOS 8, DHGR landscape: NeoWildernessXL
(`dist/NEOWILDERNESSXL.po`, 3.5 inch, 800 KB, the six scenarios; the 140 KB
edition `NEOWILDERNESS.po` has been archived since 16 October 2026). This
file keeps only what remains. It follows the game lots of
[ORIGINAL_GAP.md](docs/ORIGINAL_GAP.md) § 3 (numbers, sizes, nature
"addition" or "fidelity"), then three sections outside the lots: interface,
picture, quality. What is done is described in [CHANGELOG.md](CHANGELOG.md).

**Active edition: NeoWildernessXL only.** On 16 October 2026 the user asked
to stop the 140 KB version. Building and validating it are no longer part
of the current work; the older measurements below are historical.

**Current priority: full navigation without a keyboard**, audit approved
on 16 October 2026; the common inputs and the first action/quantity editor
of OBJECTS are done, the special cases then CRAFT/CATCH are to be continued
(interface section below; what was delivered from 16 to 18 October 2026 is
in CHANGELOG.md, "Unreleased").

**Next game lot: 6, sites (remaining)**, the first open lot of the proposed
order below; it is an "addition" lot (ORIGINAL_GAP.md § 3), the fidelity
lots 12 and 14 come last. Lots 3 and 4, the rationalised grid and part of
lot 6 are done (CHANGELOG.md; [CRAFT.md](docs/CRAFT.md),
[FORAGE.md](docs/FORAGE.md) § 17, [MENUS.md](docs/MENUS.md) § 4). TEXT,
RESIDENT, LOWPAGE and MENUCODE are full (0 bytes), WILDGAME has 1 free,
MENUSWAP 8, WILDLO 20 and WILDERNESS 42 (build/wild.map, 6 November 2026,
unchanged on 16 November): the state of a future lot will go into a module
or will need a recovery ([MEMORY.md](docs/MEMORY.md) § 16 to 39). The XL
volume uses 432 / 1,600 blocks (`read_volume.py`, 16 November 2026). The
figures of the archived 140 KB edition (280 / 280 blocks, NEOWILD.DAT, its
auxiliary stock) are in CHANGELOG.md ("Historical margins").

**Exit rule.** An entry is done when its "Done when" is true, backed by
tests; the same day it leaves this file and becomes a bullet of
CHANGELOG.md ("Unreleased", with the commit or the date). No ticked box
stays here. "In progress": two lots at most (one agent per lot, a single
one building in the tree). What left this file on 16 November 2026 (ticked
boxes, the historical margins, the "Removed" sections of 14 and 15 October
2026) is at the end of CHANGELOG.md: "Moved out of TODO.md on 2026-11-16",
"Historical margins", "Removed on 15 October 2026" and "Removed on
14 October 2026".

The costs in the table below come from ORIGINAL_GAP.md § 3 and
FORAGE.md § 15; "to be costed" means that no measurement exists. A lot
that touches the reference path first rebases `test_reference_state.py`.

## Game lots

| Lot | Content | State | Evidence | Resident | 140 KB stock | XL stock | Disk |
|---|---|---|---|---:|---:|---:|---|
| 0 | Room | done (§ 12 to 15); historical margins: CHANGELOG.md ("Historical margins") | MEMORY.md § 15 | — | — | — | — |
| 1 | Preparation and levels | done; remaining: relief per level, STATUS verdict, in-game research mode | `9642e39`, `test_prepare.py --original` | ≈ 60 (SIM) | 0 | 0 | XL: one map per level, to be costed |
| 2 | Fire, light, water | done | `d0aebf5`, `test_camp.py` | — | — | — | — |
| 3 | Crafting: MAKE recipes (A1, A2, D4), CRAFT page, shelter sprites | done (15 October 2026) | `test_craft.py --original`, `test_craft_page.py`, `test_sites.py`, CRAFT.md § 8 | 12 bytes (LOWPAGE) + 6 (WILDERNESS) + 3 (WILDLO); page: 0 | grid and panel: 287 bytes; no shelter sprite | 287 bytes; shelter sprites: 0 (NEOWILD.BLK) | CRAFT: 8 blocks on both (readable page, MEMORY.md § 25); shelters: 8 blocks on XL |
| 4 | Hunting, fishing, gathering, meals | done; remaining: the ATTACK thresholds by light (lot 11); bow, spear, club, stone done (lot 3), against animals too | `test_forage.py --original`, FORAGE.md § 17 | 989 | +1.4 KB (TREE, ORIENT on disk) | +1.4 KB | FORAGE: 12 blocks on both |
| 5 | Crafting 2 and raft | open; recipes measured (CRAFT.md § 6) | — | to be costed | no | to be costed | in CRAFT (2 KB of room in its window) or CRAFT2; RIVER |
| 6 | Sites ("site sprite" base, outpost, log, rock), terrain messages, JUNGLE | partly (15 October 2026: "site sprite" base, log and rock, ranger outpost) | sprites extracted | to be costed | no (sprites) | 2.4 to 4.7 KB of sprites: partly | to be costed |
| 7 | Orientation | done | `5126d5b`, `test_orientation.py` | — | — | — | — |
| 8 | Ranked HELP, resurrection, original score (E1, E2), per-region help | open | — | to be costed | 0 if HELP is read on command | same | ≈ 3.5 KB |
| 9 | SAVE / RESTORE | done | `640e6e0`, `test_save.py` | — | — | — | — |
| 10 | Lost city (CLUE, remains, statue) | open | — | to be costed | XL only | sprite 2.4 KB | ≈ 3 KB |
| 11 | Complete wildlife (duration, movements, RUN, fire and animals) | open | — | 0.6 KB (WILDOUT split) | to be costed | to be costed | — |
| 12 | Terrain, slopes, risks, REST interrupted by the weather | open, **fidelity** | — | 1.0 KB (TRAVEL, SIM) | to be costed | to be costed | — |
| 13 | Medicine | done; remaining: falls | `868d9fa`, `test_care.py --original` | — | — | — | — |
| 14 | Containers and load (P3) | partly (16 October 2026: weight of the second set, refusal from the ground, LOAD gauge at the measured thresholds); remaining: the container formulas | `re_load_probe.py`, `test_objects.py --original` | 0.3 KB (ITM, GDATA) | — | — | — |
| 15 | Regions: R1, R2, fine geography (R3) | open | REGIONS.md § 7 | 0.1 KB | Sierra only | atlas: shares `$D000-$F0FF` with the TOPO snapshot | XL: ≈ 13 blocks per atlas |

Proposed order: 6 → 8 → 5 → 10 → 11 → 15 → 12 → 14 (lot 3, which came
first, is done; ORIGINAL_GAP.md § 3). The fidelity lots 12 and 14 come
together, last, on a reference rebased only once.

### Lot 1 — remaining: levels

- [ ] Relief per level: one map per region and per level on XL, chosen
  by the loader (`mkmap.py --level` already applies TMAKE).
- [ ] Level factor of the STATUS verdict (×0.85 from 3, ×0.7 from 8);
  in-game effects of the research mode (SCENARIOS.md § 11.4).

**Done when:** a journey at level 1 and at level 10 has the relief, the
verdict and the score of the original (`test_prepare.py --original`
extended).

### Lot 6 — sites (remaining)

- [ ] Several sites projected per view (today only the nearest one), one
  sprite per site code (SURV3D table `$1D0D`): the tent, the hut, the
  igloo and the trench came with lot 3 (XL), the lost city will come with
  lot 10 (same path: NEOWILD.BLK, SIM window); the downward view on
  arriving on a site without bit 7 (`$E7` = −1, CRAFT.md § 8.4).
- [ ] Terrain messages and the word JUNGLE (regions 3 to 5).

**Done when:** the original's sites are visible in the view and on TOPO
in the six regions (`test_sites.py`, `test_sprites.py`).

### Lot 8 — HELP, original score, per-region help

- [ ] The original's ranked HELP (msg 223, 249, 224…), isolated penalty;
  wildlife sentence and species names per region.
- [ ] Resurrection and original score (E2), beside the port's score.

**Done when:** HELP renders the original's messages in the six regions
(ROM probe), the original score is shown at the end.

### Lots 5, 10, 11, 12, 14, 15 and TMAKE

- [ ] Lot 5: crafting 2 (recipes measured: [CRAFT.md](docs/CRAFT.md)
  § 6, A3 cases of `results.json` left out of `test_craft.py`), raft,
  PADDLE/ROW.
- [ ] Lot 10: the lost city scenario (CLUE, remains, statue,
  introduction, hall of fame with 12 tables); XL only.
- [ ] Lot 11: the animals' ATTACK thresholds by light (`$19` = 2 −
  `$0D5D`, FORAGE.md § 3.4: wound ÷ 2 and success × 2 by day; OUTDOOR
  keeps the night ones, for the five means: the lot 3 weapons and the gun
  already arm ATTACK, CRAFT.md § 8.5); SCARE and food theft from the cases
  `scare bear`, `kill bear gun light 1 rnd 0.3501` of `results.json`.
- [ ] Lot 11: complete wildlife (presence duration, movements, RUN);
  **to check** first: fire has no effect on animals in the port
  (animals.md, "Adaptations explicites"); probe
  `re_animal_reactions_probe.py` with B1[FIRE] = 0.
- [ ] Lot 12: slopes, movement risks, REST interrupted by the weather
  (**fidelity**).
- [ ] Lot 14: container capacities by weight (`$4BF8`, `$4BEE`,
  `$4BF2`) (**fidelity**). Done on 16 October 2026: the weight of the
  second set (CRAFT.md § 8.2) and its refusal from the ground (GET ROCK
  refused at the start, as in the original); the OBJECTS LOAD gauge
  (MENUS.md § 5.1) at the thresholds measured on the ROM
  (`tools/re_load_probe.py`): walking slows down in proportion to the
  weight from the first pound (T08/S07, already carried by TRAVEL), the
  only threshold is the limit `$4BFA` (815 oz for the Sierra), beyond
  which any object taken from the ground is refused. Remaining: the limit
  and the volumes by character (`$4BFA` and the capacities computed by the
  loader: today the constants of `load_limits`), the original accounting
  of the pack and the canteen (state.md § Réimplémentation : charge), the
  volume of a second-set object that changes place without leaving the
  player (not checked), the weight of the lot 4 piles (none,
  FORAGE.md § 17.3).
- [ ] Lot 15: base terrain and altitude per region, severity of the
  injuries, unprobed branches (raft, cannibals; REGIONS.md § 7); fine
  geography of the six regions — a game decision (the simulation of the
  legacy maps would change); leads: reduced resolution (1–2 KB) or an
  atlas of the Sierra only.
- [ ] Lot 13, remaining: falls (IMPLEMENTATION.md, "Conditions
  médicales").

**Done when (fidelity, together):** a complete crash → rangers route
agrees with the original in the Sierra (`make test-original`, with meals,
water, rest, cabin, encounters, care, swimming and return to the bank,
death and injury variants; ADVENTURE_TESTS.md), the five other regions
follow their probed sheets, and the chosen geography is documented with
its measured differences. Permanent rule: the order of the draws, the
half-steps and their costs stay those of the original
(`test_reference_state.py` green at every engine change).

## Outside the lots: interface and game experience

### Full navigation without a keyboard — audit approved on 16 October 2026

Priority asked by the user: complete the whole run with the directions,
confirm and back, from start-up to the end of the game, on
NeoWildernessXL. Keep the typed commands, the decisions of AGENTS.md, the
five saves and the existing simulation rules.

- [ ] **In progress — events and dialogues.** Unify keyboard and joystick
  inputs (dead zone, repeat, button edges, release between two steps);
  turn PACK/GROUND (P/G), Y/N confirmations, E/W, quantities, durations
  and azimuths into navigable choices. Include the messages that wait for
  a key and the interruption of WALK/SWIM.
  The second batch is in place (CHANGELOG.md, "XL only and OBJECTS
  transactions", 16 October 2026): action menu, directional quantity and
  confirmation, load preview of the usual transfers, consumption from the
  selected source; `test_object_actions.py` checks the transaction without
  mutation and the 16-bit quantities. The points below stay open for the
  special cases; they are not declared done.

- [ ] **OBJECTS — actions.** Enter in the lists kept; a selected object
  gives access to use, taste/eat, drink, put on/take off, take in hand,
  stow and drop according to its nature. Keep its identity and its source
  (LOCAL/PACK/HANDS/WORN), the selections and the scrolling; return to
  the context with the answer after an action. Done on 17 October 2026
  (CHANGELOG.md, "OBJECTS/EQUIPMENT" sections of that day): the position
  filter, the USE prerequisites (bait, first-aid light, stove and
  matches), lamp and magnifying glass, the instruments. The native
  refusals stay reachable.
- [ ] **OBJECTS — preview to complete.** Before confirmation: source, real
  destination, quantity, added weight, needed volume and room left after
  the transfer; water/canteen, pack, clothes and crafted objects included.
  No temporary change of the real state to compute the preview. Done on
  17 October 2026 (CHANGELOG.md, "OBJECTS/EQUIPMENT": weight change,
  precise sources, ready containers): signed WT, LOCAL/HUNG/PACK/HANDS/
  WORN/CANTEEN sources, crafted objects and wild piles told apart, pack
  carried for PACK and contents to empty for DROP, with joystick remedies.
- [ ] **OBJECTS — refusals to complete.** Precise and cumulated causes:
  weight exceeded, PACK full, HANDS full, container missing, hung pack,
  container to empty; show need/available/missing. Reduce the quantity or
  explicitly choose the carriable maximum, without a hidden partial
  transfer. Harmonise the messages of crafted objects with those of the
  equipment without implicitly changing their load rules. Done on
  17 October 2026 (CHANGELOG.md, "OBJECTS/EQUIPMENT" and "OBJECTS:
  explicit carryable maximum"): canteen and BACKPACK not carried, pack in
  use and canteen to empty, FIT for the local provisions of the first set
  and GET WATER, the NEED/FREE/MISSING figures. FIT 0 stays informative;
  no quantity is reduced behind the player's back. Remaining: the review
  of the other transfer classes for FIT and the harmonisation of the
  native exceptions that do not apply the same load model.
- [ ] **STATUS — care by drinking.** A fidelity blocker to solve after the
  rebase: `DRINK_FIDELITY=0` improves hydration but leaves medical
  selector 6 disabled; a DRINK advised by STATUS therefore does not mark
  this treatment. Keep the reference calculations until the matching
  fidelity lot; the other explanations of the gauges, states and care are
  done (17 October, CHANGELOG and MENUS.md § 29–35).
- [ ] **CRAFT.** Make the link with FIRE/WATER of the grid understandable.
  The distinction between tool available/in use and the estimated end
  time are done (17 October, CRAFT.md § 11); summary and foldable details
  are done (CRAFT.md § 12). The readable result and the joystick
  follow-ups to the same recipe, the selected object or entering the
  shelter are done (17 October, MENUS.md § 36 and CRAFT.md § 10).
- [ ] **CATCH.** Tell capture, active hunting and combat apart; show
  target, bait, gear, duration and expected yield before confirmation;
  readable prerequisite refusals; result with the quantity on the ground
  and access to pick up, skin if applicable, cook or eat.
- [ ] **Peripheral runs.** MAP: directional exploration mode and
  recentring; start-up, region/level, custom preparation, SAVE/RESTORE
  and replacement, QUIT, score and hall of fame name. The integrated run
  now covers care, SAVE/RESTORE with refusal and cancel, restore after a
  restart, QUIT and the score name on the joystick port. Remaining: the
  custom preparation, the peripheral errors and validation on a physical
  controller.
- [ ] **Visual feedback.** Explicit tab focus, current step of the
  choices, activity during waits and protection against a held confirm;
  keep inverse/symbols/labels independent of colour. The page
  reorganisation is done (17 October, MENUS.md § 39): distinct compact
  gauges, folded medical catalogue, equipment categories, help by topic,
  CRAFT details and simplified lists.
- [ ] **Memory and disk.** Measure each lot; recover room in the resident
  code before adding; develop XL only and publish the real margins and
  latencies.

**Done when:** a test runs start-up → equipment → crafting → capture →
consumption/care → save/restore → end of game with directions and buttons
only, on NeoWildernessXL, with simultaneous ground and pack stocks,
overload, missing gear, cancel at every level and interruption. The same
actions keep the simulation state of the typed commands; no time and no
draw during navigation. Replay the OBJECTS, CRAFT, CATCH, grid, focus,
maps, saves tests and the comparison of the 163 variables with the
reference.

- [ ] Finish wiring the common inputs: questions of the custom
  preparation, confirmation of erasing /RAM before loading the trunk and
  disk errors. The decimal reader inherited from CATCH/COOK now offers the
  minutes on the directions, with a cancel without effect. The joystick
  driver, the start menu, the pages, P/G, the in-game confirmations, the
  number reader, MAP and the score name are done: CHANGELOG.md ("Shared
  navigation", 16 October 2026).
- [ ] Observation of a new player with the joystick only (step 6), after
  the automated integrated run; finish the contextual filtering of the
  actions per object (step 5).
- [ ] End of game: do not rewrite the hall of fame when nothing changes
  (1.9 s; a message on every journey on a write-protected disk; HOF.md
  § 8).
- [ ] Messages: precise refusals, persistent feedback, named stop causes
  for all actions (NEOWILDERNESS_ERGONOMIE.md).
- [ ] MouseText frames for the two XL screens still without one: the
  start menu's H screen (`hm_hall`, `src/hof_menu.s`, drawn by the loader
  in 40 columns) and ADVENTURE's end of game (`module_ending`,
  `src/adventure.s`: ASCII `+---+` rules), in the post-it convention of
  the NEOWILD.END score screen (MENUS.md § 9.3–9.4), XL only (macros of
  `src/mousetext.inc`, MENUS.md § 9.1). HELP has had its post-its since
  (`pf_help`, `src/mt_pages.s`). Memory: the ADVENTURE window has
  255 bytes free (`$5F01-$5FFF`, build/wild.map of 16 November 2026) and
  the module is stored LZ in the auxiliary stock; the loader and its BSS
  end at `$ABB8`, below its ProDOS buffer at `$B000` (MEMORY.md § 38; is
  that gap free while the menu runs?). On 15 October the verdict was "no
  room without a tail or a disk read" (CHANGELOG.md, "Out of TODO.md on
  2026-11-16").
- [ ] Update the verb table of ORIGINAL_GAP.md § 1.2, then list all the
  commands that end in `m_notyet` (exhaustive list, with figures).

**Done when:** a complete game is played with the joystick only, from the
menu to the end; no interface command shows the text curtain; the
`m_notyet` list is published and holds only open lots.

## Outside the lots: picture and atmosphere

- [ ] Optional: enriched `LOOK STARS` (named landmarks, azimuth and
  height; STARS.md § 11, Python reference ready); the original's LOOK
  STARS is ported (lot 7).
- [ ] Moon visible by day and at twilight (the engine computes only one
  body); graduated gibbous moon if the compared state allows it.
- [ ] Moods and palettes per region after viewing on the six maps
  (nights too green, dark blue too bright, gradients).
- [ ] Real composite monitor: fringes, one-pixel strokes, 80-column text,
  POM2's grey.
- [ ] Rendering: cost of a view (0.5 to 0.9 s), rotations, TOPO in 3 s;
  double buffering only if 16 KB become free.
- [ ] Reference captures per region and per mood in `build/dhgr/`,
  compared by the picture tests (`test_dhgr_ref.py --refs` produces the
  PNGs, nothing compares them).

**Done when:** the six regions have their palette validated on screen, the
stars are tested on both banks, and no display command is slower than the
published measurement by more than 5 %.

## Outside the lots: memory, quality and delivery

- [ ] Start-up: reduce the 21 s up to the menu and the 10 s from the
  choice to the first view (figures of 13 October, Disk II); measure again
  on the XL edition, on SmartPort.
- [ ] **to check** — bank 2 of the main card (`$D001-$D0FF` LZ decoder,
  `$D100-$D3FF` B2 relay, `$D400-$DFFF` DHGR rows) under other versions of
  ProDOS and on the IIc (`test_prodos.py` with another PRODOS).
- [ ] **to check** — stack and interrupt safeguards (zero page, banks,
  RESET, QUIT, incompatible machine, `/RAM`: `test_prodos.py`).
- [ ] Test suite in tiers: fast (Python models and benches, under two
  minutes), full (emulator, ≈ 83 steps), original (`test-original`); what
  each test guarantees.
- [ ] Machines: IIc (a2shot --iic, 3.5" SmartPort in slot 5), real machine
  with a DHGR card and a 3.5" drive, `make run` of the XL edition in POM2.
- [ ] Possible latent bug: when the image of the ALERT module exceeded $700
  bytes, test_care (WARM PARKA) crashed into the Monitor (path MVI
  care_dry → have → t_update then BRK), even with the added routine
  reduced to RTS: cause not found; ALERT is $788 today (beyond $700: to
  check again).
- [ ] Delivery: README, CHANGELOG, final memory survey, credits of the
  original data, remaining limits; the XL `.po`.

**Done when:** the fast suite passes in under two minutes, the full suite
is green, the XL `.po` boots on IIe and IIc, every region starts with a
documented auxiliary margin, the XL volume keeps at least ten free blocks
after the saves, and the repository holds the history of the lots.

## Pending decisions

Verb review of 14 October 2026; the rationalised grid of 15 October
settled GET/TAKE (a single GET, automatic destination), REST/WAIT (both
kept), WEAR (a toggle instead of an OUTFIT page), MAKE STICKS (outside the
grid) and BOIL (offered only with a fire or the stove): CHANGELOG.md,
MENUS.md § 4. Each remaining answer becomes a lot line or a "Removed"
entry of CHANGELOG.md.

- **ROM probes of the verb review.** `WEAR SLPNG BAG`, `WEAR TENT`,
  `WEAR GND COVER`: the medical model assumes them worn
  (`med_full_cover`, `game.s:1939-1952`) while WEAR refuses them;
  destination of GET in the original (`GET AXE` then B1[58]: hand or
  pack?, `parser.md:148`; measured on 15 October in the real game:
  B1[58] = 3, in hand, like GET of the second set, CRAFT.md § 4.1; the
  port puts the axe in the pack); BOIL: does a single boiling protect from
  giardiasis for the whole journey (selector 22 never reset while the
  iodine one is; then +1 byte in `hz_daily`)?
- **140 KB edition full (16 October 2026).** Moot while that edition
  stays archived. CATCH with its duration takes the last free block:
  280/280, five saves of four blocks. The next disk addition needs room
  to be recovered. Lead: reduce FIRE below 1,536 bytes to go from four to
  three blocks; reducing the number of saves would need a game decision.
- **Grid leftovers.** Keep the FORAGE module between two steps of the
  queue (today read again at every step: 12 blocks on 140 KB); DRY and
  HANG gestures in the MEDICAL page (`WET`, wet clothes); COOK ounces in
  the lists, like `BOIL WATER n OZ` (today the number prompt asks for
  them).
- **Small defects noted on 14 October.** The prompt of a typed
  `BOIL WATER` announces 128 oz for 64 available (`w_avail`, CAMP +10);
  to check again since the WEAR toggle: the list omits SUNGLASSES and
  WATCH, REMOVE throws to the ground.
- **Duplicate alert.** "YOU ARE HUNGRY ENOUGH TO EAT A HORSE." twice
  after two `REST 8 H` (lot 13, to examine).
- **ROM probes still to run** (ORIGINAL_GAP.md § 3): animal presence
  duration (D1, relay `$4D56`), outpost equipment in scenario 2. The
  crafting time formulas (A1–A3) and the meaning of `$D8`/`$D9` = `$7F`
  (shelters, tent) were probed on 15 October 2026 (CHANGELOG.md,
  "Neowilderness: crafting, the MAKE recipes (lot 3, step 1)"). Which
  ones before lots 6 and 11?
- **Lot 4, provisions.** `FORAGE_FIDELITY` (`src/forage.s`, the byte
  `fg_fidelity`) routes EAT of the provisions through the module (expiry,
  P/G question, salt of BACON and BOLOGNA); left at 0: the reference
  script eats cheese from the pack and the ground and would break on the
  question. Turn it on and rebase `test_reference_state.py` once, with
  lots 12 and 14?
- **Lot 4 on 140 KB.** Moot while that edition stays archived. Every
  command of the lot reads FORAGE (12 blocks, 1.3 s on the emulated
  Disk II, 0.1 s on XL); TREE and ORIENT are also read from the disk
  there. Keep, or split FORAGE (meals / hunting) to read less?
- **Lot numbers.** "Lot 8" means both the joystick (MENUS.md) and
  HELP/score (ORIGINAL_GAP.md); "lot 7" both the scenarios and stars
  (CHANGELOG) and orientation. This file follows ORIGINAL_GAP.md; rename
  the joystick one "interface"?
