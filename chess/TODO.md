# Chess — roadmap

Each step is checked with the engine bench in `test/` (`make best`, `make
play`, `make exact`: the chosen moves must not change unless intended) and
on the disk with `make test` (`tests/test_game.py` drives the cursor in a2run
and reads the board and the game state through `build/chess.lbl`; a2shot
`shot:` captures the screen). Measured figures below come from
`test/` (12 positions, cycles at 1 020 484 Hz) unless stated otherwise.

What is done is in [CHANGELOG.md](CHANGELOG.md).

## Next up

Nothing scheduled: see Later and Ideas.

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
