# Robot Space Station on the DHGR compositor — migration record

*[← hgrc](README.md)* · planned 2026-10-31, applied the same day. What
was done, what differs from the plan, the measurements.

Goal (reached): the room, the drones, the objects, the technician and the
pointer drawn by `dhgr_spr_*` (README, "Flicker-free sprites"): every
changed byte of the room written once, no erase-then-draw, no black box,
no hide/show of the pointer around the room's drawing.

## Measurements

| | Before | After |
|---|---:|---:|
| Drone 10×12 moved one pixel (dev/bench `dhgr_spr_move`) | 35,000-45,000 cycles | 15,910 |
| Frames per drone turn, //e, missions 1 / 4 / 7 (`tests/speed.py`) | 5.00 / 8.00 / 11.43 | 4.05 / 4.21 / 6.32 |
| Same, //c | 4.29 / 6.67 / 10.00 | 3.00 / 3.33 / 5.22 |
| Free: resident / PLAY / L8 (`build/game.map`) | 1,520 / 585 / 262 B | 448 / 162 / 262 B |

A turn of mission 1 is now about 22,000 cycles of game logic (`zone_tick`,
the boards) and 19,000 of drawing.

## What was done

- **Build** (`robotspacestation/Makefile`): `HGRC_DHGR_SPR_SRCS` in the
  platform library, assembled with `DHGR_SPR_MAX=7 DHGR_SPR_RECTS_ONLY=1
  DHGR_SPR_OVERLAY_INSIDE=1`; update, write, painters and tiles with
  `DHGR_SPR_CODE_SEGMENT=1` in the PLAY window (`src/game.cfg`:
  `DHGRSPRCODE` between PLAYCODE and PLAYDATA, which stays last because
  `src/overlay.s` copies up to its end); the calls (`dhgr_spr_api.s`) and
  the overlay (`dhgr_spr_overlay.s`) resident. `-D DHGR_SPR_MAX=7` in
  CFLAGS too.
- **Room = tile map**: `tile_s[]` in `src/sprites.c` transcribes the old
  `draw_tile()` (11 RECTS shapes, door and plate variants share their
  rectangle tables); `tiles[]` is the map. `zone_draw()` starts the
  compositor (`sprites_room()`), sets the sprites, then invalidates and
  updates one row of tiles at a time with `ui_latch()` between them:
  `draw_tile()` is gone. `zone_draw_doors()` swaps the door and plate
  entries (`sprites_doors()`) and invalidates their cells, an update every
  16 cells. This fixed the drone parked on a plate being drawn over by the
  plate (mission 7's drone B was invisible on its plate, mission 6's
  partly covered).
- **Sprites = slots** (`src/sprites_asm.s` `zone_sprites()`): objects 0-3,
  drones 4-5 (colours 16-19 through `dhgr_spr_palette`, facing =
  `DHGR_SPR_MIRROR`, `drone_jet_s` = the 9 rectangles + the exhaust), the
  technician 6 (`tech_s` / `tech_step_s` share one table: legs apart,
  body, legs together). **No black box**: the drone is composed over its
  tile (the charger or a plate shows through). `zone_frame()` =
  `zone_sprites()` + `dhgr_spr_update()`, after each turn (`step()`) and
  each walk step (`walk()`). Deleted: `drone_draw`, `uncover`, `erase_box`,
  `touched`, `draw_object`, `draw_hull`, `drawn_*`, `ex0..ey1`,
  `begin_draw_box`, `drone_paint`, the `zone_tick()` redraw mask; `div7[]`
  became `dhgr_cellbyte[x] >> 2` (−140 B resident BSS).
- **Pointer**: in the room its rows inside the room are the overlay
  (one pass with the room's update; `DHGR_SPR_OVERLAY_INSIDE`: nothing
  outside the area), its rows above or below the room stay with
  `src/pointer.s` (save-under); `hide()` hides only those. Other screens:
  `pointer.s` as before (`dhgr_cursor`, 9,000 cycles a move against about
  4,500 for `pointer.s`'s restore + draw, was not a net win; its 764 B are
  not linked). `screen_clear()` forgets the pointer (a screen change while
  it was kept no longer restores stale bytes on the new screen).
- **Board screen** (S_DRONE): the technician keeps `actor_show` /
  `actor_hide` (now no-ops elsewhere); in a walk-only frame he is hidden
  after `walk()`, just before he is drawn again.
- Stale comments fixed (`ui.h` "inverting pixels", `main.c`).

Differences from the plan: the save-under member did not fit (PLAY was
913 B short at first): `DHGR_SPR_OVERLAY_INSIDE` was added to the library
and the outside rows left to `pointer.s`; the sprite setup is assembly
(the C version took 1,053 B of PLAY); the calls and the overlay moved to
resident memory.

## Tests

- `make test`: 132 checks on //e and //c (the 128 before, plus
  `tests/test_zone.py` `write_once`: missions 4 and 7 running with their
  solutions while the technician walks and the pointer moves, 120 updates
  each under a2shot `storewatch`: every page-1 byte stored at most once
  per update, auxiliary stores with IRQs masked, nothing else storing into
  the room's rows), 37 model tests. The overlay test leaves out
  `DHGRSPRCODE` (self-modifying).
- `make test-long`: campaign 91 + 91, fuzz 12 + 12, zone fuzz 10 + 10.

## Left

- `DHGR_SPR_VBL` / `DHGR_SPR_DOUBLE` (library, planned): VBL-paced
  updates on the //c, page flipping.
- The board screen's technician still hides and shows (no background
  source for the compositor there).
