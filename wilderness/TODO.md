# Wilderness — next development steps

The game has the terrain engine, the basic commands, the simulation, object
and load management, dry/immersed thermals and the five original Sierra
Nevada sprites. The cabin is usable and TOPO shows the sites; the Sierra
wildlife filters and rates are ported, but its movements, how long it stays
and its reactions are still provisional.

The current state and its limits are described in the [README](README.md).
Porting details and tests are in
[IMPLEMENTATION.md](docs/IMPLEMENTATION.md); the evidence on the original
stays in [ANALYSE.md](docs/ANALYSE.md) and [docs/logic/](docs/logic/ENGINE.md).
The history of the steps is in [CHANGELOG.md](CHANGELOG.md).
The lots below give the proposed order of work.

## Priority: a complete adventure compared with the original

The `make test-original` driver runs the original on ROM and the port with
the same commands. It keeps the observations and fails on every
difference, without ignoring an unfinished command. The five short scenarios
and the native walk to x70/y86 match; they do not yet cover
an arrival at the rangers.
See [ADVENTURE_TESTS.md](docs/ADVENTURE_TESTS.md).

- [ ] Port the compass's random accuracy, the walking steps and costs;
  distinguish the remembered ground stock from the accessible quantities in
  the reports.
- [ ] Keep the geography and sites of the original map without losing
  the odd cells; establish a replayable crash → rangers route.
- [ ] Compare this route up to the victory, with meals, hydration,
  nights, cabin, encounters and a swim crossing with a return to the bank,
  without any movement forced in memory.
- [ ] Add variants for death, injuries/treatment and resuming a save.

The Python model suite (`make test`) is still needed, but its passing
does not validate that the two games are identical.

## 3. Replace the provisional encounters with the original wildlife

- [ ] Establish the animals' position, duration and movements;
  replace their arbitrary 60-minute expiry.
- [ ] Complete the native reactions: movement, delays, other means,
  critical fifth-degree branch, duration of bites, hunting/carcass
  and indoor/search context.
- [ ] Link the consequences to the health conditions and treatments:
  FIRSTAID KIT, SNAKEBITE KIT and the injuries concerned.

**Validation:** deterministic scenarios for each species, no
encounter outside the criteria, state kept across loads,
and transitions between observation, action, injury and treatment.
`re_fauna_probe.py` runs 162 filtering cases and 45 probabilities in the
original code. `test_fauna.py` checks them in the port and covers the
exclusions, the diagonal slope, the three species and the NATURE setting.
`re_fauna_accept_probe.py` checks 36 keeps/replacements and the original
interruption flags. `test_fauna_steps.py` checks the steps of a
rest without a draw, walking interruptions, replacement refusals and the shelter.

## 4. Complete the thermal environment: weather, rain and fire

- [ ] Port the weather fronts: sky, rain, snow, wind, trend and frost.
  The felt wind is already integrated; the full evolution of the fronts is
  missing.
- [ ] Link the rain to the wetness selector and to the protection worn;
  establish the transitions out of the rain without inventing a gradual
  drying.
- [ ] Port the lighting, fuel, duration and extinction of the fire.
- [ ] Combine air, wind, immersion, shelter and fire correctly; complete
  the triggers and treatments of thermal conditions 20–21.
- [ ] Adapt the view's visibility to the weather and show the sun
  according to the time. The weather ray budget, the masking by clouds and
  the seasonal sun are present; their full fidelity to the original
  remains to be compared. The night-time moon dated 1985 is a documented
  extension.

**Validation:** the same dry, rain, immersed, sheltered and near-fire
scenarios; compare with the original routines and keep the cold/heat tests,
the shivering calories and the recovery towards 98.6 °F.

## 5. Complete the survival actions and risks

- [ ] Terrain: forests, banks, slope (`SLOPE`), falls and dangerous moves.
- [ ] Establish the original's walking speeds and early stops,
  the injury/equipment modifiers when swimming and the timing
  of the load recalculation.
- [ ] Establish the exact accounting of containers, the load limits
  and their effect on walking; replace the calibrated additive model.
- [ ] Complete the triggers from injuries, contamination and malaria,
  SPLINT, the thermal treatments and the transactions specific to USE
  (placing objects, sterilising the kit).
- [ ] Compare collection/contamination with the original and port water
  treatment; add hunting, fishing and gathering.
- [ ] Port crafting by object family: shelters, tools and weapons
  (HUT, IGLOO, TRENCH, BOW, SPEAR…), with consumption and action times.
- [ ] Complete HELP, the messages and the inputs specific to the new actions.

**Validation:** each action respects time, load, accessibility
and quantities; refusals keep the state and the health effects are
checked with and without treatment.

## 6. Allow long games and several regions

- [ ] SAVE / RESTORE: define a versioned format including map, objects
  on the ground, simulation, weather, sites, wildlife and random generators.
- [ ] Check an identical resume after a save, and the read errors.
- [ ] Integrate the six regions: climate parameters, wildlife, sprites and maps.
- [ ] Complete the effects of the ten difficulty levels.
- [ ] Evaluate the second scenario and CLUE once the
  crash → ranger station route is stable.

## Rendering and map improvements

This work can go along with the previous lots once its benefit is measured.

- [ ] Compare the hydrological generation with the original TMAKE; keep
  the fine detail of the banks with a full-resolution map format.
- [ ] Extend the sprites to the other sites/objects and the other regions.
- [ ] Show several sites in the same view and smooth the size steps,
  measuring the memory and disk reads needed.
- [ ] Profile representative views and moves with `tools/profile.py`,
  separating rendering and disk reads; keep the rendering bit-exact.
- [ ] Reassess the unrolled division called as a subroutine if a memory
  margin becomes available. Earlier measurements and leads are kept in
  [IMPLEMENTATION.md](docs/IMPLEMENTATION.md#performance).

## Checks to keep

`make test` covers the sprites, the terrain, the random commands,
the simulation, the objects, the load, the disk modules and the thermals.
Extend the tests of the modified subsystem, then run the full suite
before considering a lot done. The reconstructed rules must stay
identified as such until they are compared with the original.
