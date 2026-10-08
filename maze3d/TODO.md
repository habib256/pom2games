# Maze 3D — roadmap

Validate every gameplay change with `../dev/tools/a2shot` (screenshots,
memory reads, cycle and frame counts) and `make test`
(`tests/check_generation.py`, 100 seeds). A scripted run must still reach the
shop, beat the dragon and win; exits without the relic, and the last one
before the dragon's death, must stay shut.

## Ideas

- Swap the private 8 px font (TMS bit order, 512 bytes) for the shared
  Beautiful Boot font in `../dev/lib/font` and define `HGR_TEXT8_HGR_ORDER`:
  drops `ht_rev` and the 256-byte `rev7_tab` from the text path. A graphic
  choice: the current font is part of the game's look.

## Done

- 2026-10-08: stairs E are visible from the start of every floor, with a map
  legend. The marker remains visible over a seen monster; neighbouring walls
  stay unexplored and relic/dragon exit locks remain intact.

- 2026-10-08: combat and map share HP/30, potion and gold fields. Low-health
  and next-attack bonus indicators persist independently of round feedback;
  failed potions clear stale action text without consuming the bonus or turn.
  Shop statistics show upgrade results immediately. Emulator checks cover
  healing, guard bonus consumption, goblin theft and purchases.

- 2026-10-08: joystick movement, map/potion buttons and all four combat
  actions through `dev/lib/apple2/joy.asm`. Held inputs do not repeat turns;
  keyboard and pause remain available. Emulator checks compare every combat
  mapping against keyboard results and cover holding, rearming and idle RNG.

- 2026-10-08: simplified UI: exploration keeps vitals and a command reminder;
  secondary statistics move to help. Shorter pause/menu labels and a title
  prompt that offers continuation only when the selected profile has a save.

- 2026-10-08: ergonomics: all four boundaries of visited cells appear on the
  progressive map, including north/west neighbours not yet visited. Objectives
  in 3D and map, HP/30 and prominent potions/gold in exploration and shop,
  explicit refusal messages and per-round combat damage/action feedback.
  All 96 narrator lines retained with lossless five-bit packing; checkpoint
  layout unchanged. Emulator regression checks cover map and readable text.

- 2026-10-08: renderer factored into `dev/lib/hgr` (prepacked sprites,
  shared colour attributes, native lines/spans, row and viewport clears),
  LZ4FH decoder into `dev/lib/apple2`, sprite packer into `dev/tools/assets`
  and compressor build rule into `dev/cc65/fhpack.mk`. Game placement,
  virtual coordinates and checkpoint format remain local. Standalone
  two-page library tests complement Maze3D regressions; +17 binary bytes,
  unchanged zero-page footprint, render overhead below 0.21%.

- 2026-10-08: Fdraw-inspired native HGR rendering, ten-cell depth, seven
  prepacked sprite sizes, correct distant monster visibility and near clusters.
  Original A2FC DEMO title with lossless LZ4FH compression and deferred text
  loading. ESC configuration menu with sound/depth, resume and save/quit.
  Three independent profiles, manual saves (ESC then W), combat/shop continuation and
  remembered preferences; real DOS export/reboot tests cover persistence.

- 2026-10-08: `S` opens a four-digit hexadecimal seed editor on the title;
  Return starts, left/Backspace/Delete erases, Escape opens configuration and resumes the editor.
  Lower case accepted; incomplete and zero seeds stay editable. Emulator
  regression tests cover correction, pause/resume, repeatability and parity
  with the best-record replay.

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
