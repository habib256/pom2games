# CUTROPE — TODO

Done (2026-11-06): bubbles, air cushions, the level solver
(`tools/cutrope.py --solve`) and the search that made the levels
(`tools/design.py`), the levels on the disk (a sector each), the level menu
with the stars won kept in CUTSAVE. What a full game would add, roughly in
order.

## Play

* **More kinds of levels.** Moving pins (a pin on a rail, `vl_pin` points
  moved by the program, x = ox), ropes that attach when the candy passes
  near a pin (a new rope at that tick: its points placed on the segment),
  several candies, a bubble per rope. `tools/design.py` takes a template
  per kind: one for each.
* **Hand-made levels.** The generated ones put the stars on the path of one
  plan; a designer's level (stars that ask for a detour, a cushion used
  twice) is a dict in `tools/levels.py` checked by `--solve`.
* **A title page** (the font's x2 text) and the frog's eating animation
  (two frog sprites).
* **The loose rope ends.** A cut rope disappears (cheaper, see README);
  the pin side could stay as a short dangling stub (its points still
  integrated, the link at the cut dropped) where the budget allows (one
  rope levels).
* **The menu on the stick**: a push moves the choice one cell; holding it
  could repeat.

## Speed and the budget

* **The bench** (one 10-link rope and two of 6) costs 70,000 cycles a tick:
  it needs either 20 Hz (3 frames a tick: `TICK_HZ` 20, the constants
  retuned, the estimate refitted) or cheaper ropes. Ideas, cheapest
  first: draw a rope's lines by bytes for steep links (a vertical line
  is 1 bit per row: a `pl_vline` that writes the byte and its history
  entry without the Bresenham steps, ~45 cycles a pixel instead of ~90);
  integrate only the points of the ropes still on (a list instead of
  `vl_integrate_all` over 23 points: ~17 cycles each pinned point today);
  `VL_CON_SKIP_ZERO` gains more when links rest: a candy at rest costs
  ~280 a link.
* **One pass is fragile** for long ropes (README: 6+ links at a gain near
  1 explode). A lib switch for a rope that only pulls (`VL_CON_MAX_ONLY`:
  no correction while q² ≤ l2, the opposite of `VL_CON_MIN_ONLY`) would
  let a slack rope fold without pushing, and long ropes stay stable in one
  pass with a softer gain; measure the energy probe again with it.
* **Level 3 hanging is the worst tick** (31,117: two ropes of 4 links,
  ~100 px of line). Computing each rope point's screen pixel once (not
  per link end: `pt_xy` twice per point) saves ~600 cycles.

## Sound

* **Sounds across the wait.** The snip, the blip and the jingle's ticks
  are `tone` calls inside the tick (1,300-17,000 cycles, counted in the
  pace estimate). They could play during `vapor_pace`'s wait instead: a
  `vapor_pace` hook (or a variant of its poll loop) that toggles the
  speaker every n polls for the time the tick leaves free — the pitch
  then in polls (13 cycles), the length bounded by the wait.
* A different jingle per star count; a squelch when the candy is lost on
  spikes.

## PAL

* On a PAL II+/IIe a video frame is 20,280 cycles (50 Hz): `vapor_pace`
  finds it (`vp_frame` in polls), 2 frames a tick are then 25 ticks a
  second and the game runs 17 % slower. Either `TICK_FRAMES` stays 2 and
  the physics constants are derived for 25 Hz when `vp_frame` says PAL (a
  second constant set, as the examples' `TUNED_HZ` derivation does for
  one rate, chosen at start). The tick's work fits better at 25 Hz
  (40,560 cycles a tick): the 10-link rope alone would fit there.
* POM2's PAL II+ (`a2shot --pal`) to measure it.
