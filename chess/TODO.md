# Chess — roadmap

Each step is checked with the engine bench in `test/` (`make best`, `make
play`, `make exact`: the chosen moves must not change unless intended) and
on the disk with `make test` (`tests/test_game.py` drives the cursor in a2run
and reads the board and the game state through `build/chess.lbl`; a2shot
`shot:` captures the screen). Measured figures below come from
`test/` (12 positions, cycles at 1 020 484 Hz) unless stated otherwise.

## Next up

1. **Flip the board when you play Black** (menu `3`, mode BAI): White is
   always at the bottom. `draw_square` reads `topsl_tab[frank]` and
   `bcol_tab[ffile]`, `draw_coords` prints the rank digits and file letters,
   `cur_up/down/left/right` move in board coordinates, the cursor starts on
   e2 (`$14`). A `flipped` flag that mirrors rank and file in those five
   places (and starts the cursor on e7) is enough.
2. **Sounds**: move, capture, check, result. Use `tone` from
   `../dev/lib/apple2/sound.asm` (shared with MICRO-SOKOBAN) rather than a
   new speaker routine; hooks are `print_move_hgr` (a move was made),
   `a1_turn_status` (`CHECK!`) and `a1_result`.
3. **Joystick**: stick = cursor, button 0 = select / confirm, button 1 =
   cancel. `read_stick` / `stick_dir` from `../dev/lib/apple2/joy.asm`,
   polled next to `poll_key` in the `@wait` loop of `human_turn`.

## Later

- **Undo more than one move.** The engine keeps a single `user_*` snapshot
  (16 bytes, `save_user_state` / `undo_last_move`, `undo_avail` forbids a
  second undo). Against the computer, `U` takes back only the computer's
  reply and the computer moves again at once, so the player's own move can
  never be taken back. A small stack of snapshots, and `U` popping two
  entries when the opponent is the computer.
- **Full move list in algebraic notation.** `print_move_hgr` prints
  `W E2E4` in a 9-character column (`MLCOL` 31..39, rows 2..22) and, when
  the column is full, clears it and re-prints only the last two moves
  (`p1_*` / `p2_*`). Piece letters, captures, `O-O`, `+` / `#`, and either a
  scrolling column or move pairs per row.
- **Thinking indicator at L3.** Quiet middlegame positions take up to 10 s
  at 3 plies with the panel frozen on `THINKING...`; a dot that advances
  needs a hook inside `ai_play_move`'s root loop.
- **Highlight the last move** (from and to squares), the XOR overlay
  machinery of `draw_sel_frame` already does this kind of marking; mainly
  useful to see what the computer just played.
- **Faster L3.** `make prof FEN=... STRAT=2` shows where the cycles go.
  Candidates: a killer move per ply, captures ordered by victim value,
  iterative deepening (an L2 pass to order the L3 root). `make exact` must
  keep passing.
- **Threefold repetition**: a ring of position signatures, if the 256-byte
  `BOARDST` segment (currently `$CA` bytes used) or BSS can hold it.
- **Save the game to the disk**: current position and move list in a DOS 3.3
  file, resumed at start-up, through `dos_cmd_new` / `dos_cmd_add` /
  `dos_cmd_run` and `disk_protected` from `../dev/lib/apple2/dos.asm`.

## Ideas

- A **hint** key: the engine exports `is_pseudo_legal`, `make_move`,
  `unmake_move` for POM1's text front-end (its list-moves and hint
  commands); `ai_play_move` on the player's side followed by
  `undo_last_move` would do.
- Replace the 200-computer-move cap of computer-vs-computer games by the
  real draw rules once item 2 is in.
- Housekeeping: `chess_common.inc` still describes a planned "v1.2
  alpha-beta" layout and BOARDST at `$1F00/$4000/$5F00`; `ai_best_mvvlva` is
  an unused slot kept "for layout stability"; `ERR_NOT_IMPL` is never
  returned. The splash still says `V0.7`.

## Done

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
