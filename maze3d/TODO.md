# Maze 3D — roadmap

Validate every gameplay change with `../dev/tools/a2shot` (screenshots,
memory reads, cycle and frame counts) and `make test`
(`tests/check_generation.py`, 100 seeds). A scripted run must still reach the
shop, beat the dragon and win; exits without the relic, and the last one
before the dragon's death, must stay shut.

## Next up

- [ ] Joystick support with `../dev/lib/apple2/joy.asm` (turn, step, and
  buttons for the combat actions).
- [ ] Manual seed entry on the title screen, next to `R`, so a dungeon can
  be shared by its four hex digits rather than only replayed from the record.
- [ ] Faster 3D rendering. The whole scene is still cleared and redrawn on
  every move; the initial 2-3x target remains open. Measure each routine's
  cost with `a2shot` (`until:` reports cycles) before picking a strategy,
  and compare screenshots before and after.

## Later

- [ ] Save a game in progress, to resume an interrupted campaign. Only the
  record and its seed are kept on the disk today (`MAZESCORE`); a save would
  reuse `dos.asm` and the `disk_protected` check.
- [ ] Faster sprite blits. `hgr_sprite16`'s `sp_pack_row` rebuilds every
  output byte from a bit stream (its header quotes about 130 cycles per
  output byte; a x4 blit is about 80k cycles). Combat screens are full
  redraws, so this is only worth it once the 3D path is measured.

## Ideas

- Swap the private 8 px font (TMS bit order, 512 bytes) for the shared
  Beautiful Boot font in `../dev/lib/font` and define `HGR_TEXT8_HGR_ORDER`:
  drops `ht_rev` and the 256-byte `rev7_tab` from the text path. A graphic
  choice: the current font is part of the game's look.

## Done

- 2026-10-03: loot fix (keep the monster type before marking it dead, cap
  gold at 99 for the two-digit HUD); progressive map (walls and exit after a
  visit, monsters seen from the corridor); three floors with tougher foes,
  mandatory dragon on the last one, floor number in 3D and on the map; shop
  between floors (heal, attack, defence, potions); speaker sounds for wall,
  attack, hit taken, level-up, stairs, victory and death; rendering
  optimisations (HGR addresses and masks kept during slanted lines, unrolled
  40-byte row clear: `render_3d` 188,523 -> 169,842 cycles on a test view,
  about 10 % faster, identical screenshots); richer mazes (2x2 chamber,
  three loops, three caches, mandatory relic; 100 seeds stay connected);
  combat variety (guard, potion, flee to the previous cell, goblin theft,
  armour-piercing magic, telegraphed orc and dragon strikes); gold and
  potions in caches, potions in the shop; seed display, victory score,
  record and seed saved in `MAZESCORE` on the DOS 3.3 disk, `R` replays it;
  narrator moved to `MAZETEXT` on disk, freeing about 2 KB of code; a
  scripted three-floor run completed without touching game memory (relics
  taken, dragon beaten, score 127 written to disk).
