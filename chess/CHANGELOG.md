# Chess — changelog

Finished work, moved out of [TODO.md](TODO.md) on 2026-11-16.

## Done

- **2026-10-07 (later)** — Board turned round in mode 3 (`flipped`:
  `draw_square`, `draw_coords` and the cursor keys mirror rank and file, the
  cursor starts on e7), joystick through `dev/lib/apple2/joy.asm` (`joy_poll`
  every 16 polls of the wait loop: one cursor step per deflection, button 0 =
  SPACE, button 1 = ESC; `read_stick` now reports an empty game port), sounds
  through `sound.asm` (move, capture, CHECK!, mate tune, draw note, `S`
  toggles). Each covered in `tests/test_game.py`. Binary 9 119 -> 9 609 bytes.
- **2026-10-07** — Rules the front end handles itself, each with an a2run
  check in `tests/test_game.py` (`make test`, part of the root `make test`):
  - the player castles by moving the king two squares (`do_confirm` sets
    `MV_FLAG_CASTLE_K/Q`; the engine's `castle_try` validates), and
    `mv_flags` is cleared for every other move so a castle left by the
    computer no longer leaks into the next move;
  - promotion prompt `PROMOTE Q R B N` (`ask_promotion`, ESC cancels);
  - `game_status` returns 4 (`DRAW`) after 100 quiet half-moves and for dead
    material (K vs K, K + minor vs K: `mat_tot` total of 3 or less with no
    pawn on the board), checked at the start of every turn (`gs_ongoing`);
  - the build writes `build/chess.lbl` (`-g`, `-Ln`). Binary 8 942 ->
    9 119 bytes.

- **2026-09-15** — Apple II port of POM1's GEN2_Chess: HGR board with the
  cc65-Chess pieces, text-screen mode menu, HGR panel (status, move list),
  keyboard latch/strobe and arrow keys, single BRUN binary at `$6000`, zero
  page at `$50`, state in `$1000-$14FF`. Measured then: reply to 1.e4
  about 14.5 s at STRONG (2 plies), about 1 s at FAST.
- **2026-09-29** — Faster engine and deeper search, moves played unchanged
  at each step (12 positions + 6 computer-vs-computer games):
  - per-piece move generation (`gen_targets`) instead of testing 64
    squares with `is_pseudo_legal`; `is_attacked_runner` starts from the
    attacked square (pawns, knights, king, 8 rays) instead of scanning the
    board; running material (`mat_tot`) maintained by `make_move` /
    `unmake_move`. Reply to 1.e4 14.5 s -> 1.6 s, worst position 45 s ->
    4.7 s, STRONG total 216 s -> 24 s.
  - generic negamax `search_node` with cutoffs (a node's bound comes from
    its parent's best; a cut root move is always strictly worse than the
    best, so L2 plays the same moves as before); material-changing moves
    first; at the leaves one legal quiet move stands for the static
    material; level L3 = 3 plies (`P`: L1 -> L2 -> L3) with a sorted root;
    `make exact` checks that the cutoffs change no move at the three
    levels. L2 reply to 1.e4 1.6 s -> 0.6 s, 1.5 s worst; L3 0.2 to 10 s
    (4 s after 1.e4), 34 s for the 12 positions.
  - level shown on the panel (`W WAI L2`), L2 by default and kept after `N`.
- **2026-10-06** — Build rules (`../dev/cc65/apple2.mk`), the Beautiful Boot
  font (`bbfont.inc`) and the test harness shared in `../dev`. Binary
  8 942 bytes.
