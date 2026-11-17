# DIRTBIKE — changelog

Finished lots, moved out of [TODO.md](TODO.md) on 2026-11-16.

Lot 1 (done): 6502 Verlet physics identical to the model, track 1, byte
scrolling, bike drawn with lines and sprites, joystick and keyboard, timer,
crash, finish.

Lot 1 ter (done): menu of 30 courses proven feasible, loaded through RWTS
from LZ4FH files, session records.

Lot 1 quater (done, 2026-10-21): speed x2, stiffer suspension (fewer
crashes), points for jumps and flips, title page, demo in attract mode,
hall of fame (times and points, initials) saved on the disk.

Lot 1 quinquies (done, 2026-10-21): 3-lap circuits, restart after a
crash, countdown, event sounds, title music, finish jingle (and record
jingle), speed x3 of the first tuning (18 px/tick).

Lot 2a (done, 2026-10-21): ~420 bytes freed (text page 1 in BSS, hall
of fame in LOWBSS), flag on the finish and lap line, points for
wheelies.

Lot 2b (done, 2026-10-22): mouse removed; joystick: X = analog lean,
button 0 = throttle, button 1 = brake, menus with the stick (one step per
push); brake reworked (it cuts the throttle, ~1 g instead of ~0.6 g, a wheel
stopped by the brake holds: the bike no longer rolls back); 30 courses solved
again. Then the brake in the air: it now only stops the wheels' rotation
(a small finite torque, ~12°), no more endless rotation.
Lean on 8 levels (fine in the middle, up to 6 px backwards) for
wheelies. Then 6 px forwards too: forward of the middle the rider
moves without velocity (no more kick that threw the bike in the air or
crushed the rider when the stick went from one end to the other).
