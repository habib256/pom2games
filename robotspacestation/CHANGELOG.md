# ROBOT SPACE STATION — changelog

*[← TODO](TODO.md)* · the checked boxes, moved out of TODO.md on 2026-11-16.

## Content

- [x] Missions 8-14 (2026-10-30): LE ZIGZAG, LE COLIS, LE GARDIEN, LA RONDE,
      LE SAS, LA CAISSE, LE TANDEM, proven by the model and played in C
      (`make test-long`); title in two columns, key 0 for the tenth
      (11-14: on the title). Missions 15 LE COMPTEUR (edges of the O sensor),
      16 LA SPIRALE (four headings), 17 LE CONVOI (grabber in the turns), 18 DEUX
      CLES (reuse the chip from LA CAISSE), 19 LA PASSE (grabber, radio, slot), 20 LES
      ETAGES (T flip-flop: an OX looped back)
      on a second title page (PAGE; RECORDS follows the page).
      `best` has 28 slots (two title pages).
- [x] Sound (2026-10-30): contact, grabber (grab, release), radio, chip
      burned, mission complete; S mutes.

## Interface

- [x] Usability overhaul (2026-10-30, evening): everything in English, a
      briefing per mission (goal, what is new, two hints), the bottom line
      describes what the pointer shows or says what to do next, thrusters
      named by the drone's direction, texts in auxiliary memory
      (`tools/gen_text.py`, `RSS.TEXT1/2`). Then: the + terminal (power,
      always 1), the labelled toolbox, a six-page electronics course
      (truth tables), GATES on the briefing.
      Then: exit behind the drone (its board played 4 turns ahead),
      you only enter by clicking the drone, side-view sprites (drone and
      technician), redraw of the uncovered strips only (previous speed
      within 5-8 %).
- [x] Two wires leaving neighbouring terminals shared their vertical
      segment: the free column nearest the middle (2026-10-30).
- [x] A part in hand shows on the pointer (a block under the arrow).
- [x] One hint per mission (key H), on the disk after the room.
- [x] A help page (AIDE or H on the title): terminals, parts, keys; then
      the room legend (grid, tunnel, doors and plates, charger...).
- [x] Records: the fewest gates per mission (save RSS3, RSS1/2
      migrated), recalled on entering the mission, RECORDS page on the title.
- [x] V: fast speed (×1.5 on the //e, ×1.2 on the //c: a turn there already
      takes almost all the time).
- [x] `make test-long`: 12 random boards (loops included) turn by
      turn == the model's `Sim`; 10 random drones in random rooms
      == `Zone`; the whole campaign, each mission played in C with
      the model's solution (board in `RSS.SAVE`), //e and //c.
