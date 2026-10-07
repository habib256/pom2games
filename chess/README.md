# Chess — Apple II+ / DOS 3.3

Chess on an Apple II+, in HGR: castling, en passant, promotion with a choice
of piece, check, checkmate, stalemate and draws, against the computer (1, 2 or 3 plies)
or between two players. An Apple II port of the `sketchs/gen2/game_chess` sketch of
[POM1](https://github.com/habib256/pom1) (GEN2_Chess, VERHILLE Arnaud) and of
its engine `dev/lib/games/chess`, with the piece bitmaps of cc65-Chess.

    make            # -> ../dist/CHESS.dsk  (bootable 5.25" DOS 3.3 image)
    make run        # boot it in POM2 (Apple ][+ profile)

## Features

- **Four game modes**, chosen from a text-screen menu at start-up and after
  `N`: `1` two human players (HVH), `2` you as White against the computer
  (WAI), `3` you as Black (BAI), `4` computer against computer (AVA, stops
  with `DRAW` after 200 computer moves).
- **Draws by rule**: 50 moves without a capture or a pawn move, and dead
  material (king against king, king and one minor piece against king) end
  the game with `DRAW`.
- **Three AI levels**, cycled with `P` and shown on the panel (`W WAI L2`):
  L1 = 1 ply (material after its move), L2 = 2 plies (sees your reply, so it
  stops hanging pieces and refuses mate-in-one), L3 = 3 plies. L2 is the
  default and is kept across `N`. Measured response times on the 12 test
  positions: L1 under 1 s; L2 0.1 to 1.5 s; L3 0.2 to 10 s (4 s after 1.e4).
- **Negamax search with cutoffs**: material-changing moves are tried first,
  the root is sorted at L3, and a cut root move is always strictly worse than
  the best one, so the move played is the one a full search would pick
  (`make exact` in `test/` checks it). Ties between equal moves are broken by
  a positional score (doubled and isolated pawns, open files, bishop pair)
  and an 8-bit LFSR seeded from how long you took at the menu, so
  computer-vs-computer games differ from one game to the next.
- **HGR board and pieces**: the 21x22-pixel squares and the outline/solid
  piece bitmaps of cc65-Chess, drawn with the same copy/invert raster
  operation so both sides read correctly on both square colours. Rank digits
  and file letters frame the board.
- **Right-hand panel** in the Beautiful Boot font: side to move, mode and
  level on row 0; `YOUR MOVE`, `THINKING...`, `CHECK!` and the result
  (`MATE: W WINS`, `MATE: B WINS`, `STALEMATE`, `DRAW`) on row 1; a move list
  (`W E2E4`, one move per row) that wraps when the column is full, re-printing
  the last two moves; `N = NEW GAME` on row 23 once the game is over.
- **Cursor and selection** as XOR overlays: blinking corner ticks mark the
  cursor (on your turn only), a frame marks the selected piece — visible on
  black and white squares alike.
- **Undo** of the last move with `U`.

## How to play

Pick a mode with `1`-`4` on the menu, then the board on HGR page 1 takes over.

| Key                 | Action                                                |
|---------------------|-------------------------------------------------------|
| `I` `J` `K` `L`, arrows | move the cursor (up, left, down, right)          |
| `SPACE` or `RETURN` | pick the piece under the cursor, then its destination |
| `ESC`               | cancel the selection                                  |
| `U`                 | undo the last move                                    |
| `M`                 | cycle the mode: HVH, WAI, BAI, AVA                    |
| `P`                 | cycle the AI level: L1, L2, L3                        |
| `N`                 | new game (back to the menu)                           |
| `S`                 | speaker on / off                                      |
| joystick            | stick = cursor (one step per deflection), button 0 = `SPACE`, button 1 = `ESC` |

- The cursor starts on e2. A piece is only selectable if it belongs to the
  side to move; pressing `SPACE` again on the selected square deselects it.
- An illegal move (wrong geometry, king left in check, ...) simply cancels
  the selection — pick again.
- En passant is entered as the capturing pawn's diagonal move. A pawn
  reaching the last rank asks `PROMOTE Q R B N` on the status row: press the
  letter (ESC cancels the move).
- Castling: move the king two squares towards the rook (e1-g1, e1-c1, e8-g8,
  e8-c8). The engine checks the rights, the empty squares and the attacked
  squares, and refuses otherwise. The computer castles the same way.
- Against the computer, `U` takes back the computer's last move only, and
  the computer moves again at once; the undo is one move deep.
- A II+ only has left/right arrows; up/down arrows work on a //e (on a II+
  they are Ctrl-K / Ctrl-J).
- Mode `3` (you play Black) turns the board round: Black at the bottom, the
  cursor starts on e7 and the arrows follow the screen.
- Sounds: a click per move, a lower thud for a capture, two blips on
  `CHECK!`, a short tune on mate and a low note on a draw. `S` silences them.
- During a computer-vs-computer game, `N` and `M` are still read between
  moves. After a result, press `N` to start again.

Planned improvements: see [`TODO.md`](TODO.md).

## Build and run

Needs cc65 (`brew install cc65`) and python3; everything else is in `../dev`,
including the DOS 3.3 system tracks. The Makefile includes
`../dev/cc65/apple2.mk` for the shared tool variables and targets.

| Target           | Effect                                                   |
|------------------|----------------------------------------------------------|
| `make`           | assemble, link and write `../dist/CHESS.dsk`             |
| `make run`       | boot the disk in POM2 (`/Applications/POM2.app`, or `make run POM2=path/to/POM2`) |
| `make clean`     | remove `build/` (the disk stays)                         |
| `make distclean` | remove `build/` and the disk                             |

The engine is assembled with `-D CHESS_SMART_EVAL` (positional tie-breaks).
The link prints the binary size: `9,609 bytes at 0x6000`. On the disk,
`HELLO` is one line, `10 PRINT CHR$(4);"BRUN CHESS"`.

## Tests and benchmarks

`make test` plays the rules the front end handles itself in a2run
(`tests/test_game.py`, on `../dev/tools/a2test.py`): a king-side castle after
1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6, a castle refused once the rook has moved, the
promotion prompt (queen, rook, knight, ESC), the 50-move rule, a
king-against-king draw, the turned board of mode 3, joystick input and the
speaker toggle. It needs the label file the build writes
(`build/chess.lbl`).

`test/` runs the engine alone — no screen, no keyboard — on the POM2 core
with exact 6502 cycle counts, through a small host program (`bench.cpp`,
C++17, linked against the core SDK shipped with `../dev/tools/a2shot` and
the II+ ROM). `bench.s` is linked first so the host can patch a `JSR`, point
the soft-reset vector at it and step until the routine returns. Twelve
positions (the start position, the reply to 1.e4, the classic perft
positions, endgames, a promotion and an en-passant case) are loaded from FEN.

| Target       | What it measures                                                    |
|--------------|---------------------------------------------------------------------|
| `make perft` | legal-move count (perft 1) and `game_status` per position, with cycles |
| `make best`  | the move chosen by each level on each position, cycles and seconds; `LEVELS=3` adds L3 |
| `make undo`  | an AI move then `undo_last_move`: board, material totals and king caches must come back |
| `make play`  | computer-vs-computer games from the start position, three seeds per level (`PLIES=40`, `LEVELS=2`), checking the running material and king caches after every move |
| `make prof`  | per-routine cycle share of one `ai_play_move` (`FEN=...`, `STRAT=0|1|2`) |
| `make exact` | builds the engine with `CHESS_NO_CUTOFF` and diffs best moves and games at all three levels against the normal build: the cutoffs must change no move |

Output is plain text, so two engine versions compare with a `diff` (cycle
counts aside). Seconds are computed at 1 020 484 cycles per second.

## Under the hood

    src/chess.s            HGR front-end and game loop (ca65), BRUN at $6000
    src/chess_engine.asm   the engine: rules, move generation, search, undo
    src/chess_common.inc   shared constants (board, pieces, moves, strategies)
    src/chess_tables.inc   engine tables
    src/chess.cfg          ld65 configuration
    src/hello.bas          HELLO: 10 PRINT CHR$(4);"BRUN CHESS"
    test/                  engine bench (see above)
    ../dist/CHESS.dsk      the disk image

**Memory map** (`src/chess.cfg`):

| Range           | Use                                                        |
|-----------------|------------------------------------------------------------|
| `$0050-$00FF`   | zero page (front-end pointers + engine slots); `$00-$4F` is left to the Monitor so `COUT` / `HOME` work for the menu |
| `$0800-$0FFF`   | the BASIC `HELLO` program, kept intact                     |
| `$1000-$13FF`   | BSS: renderer and game-loop scratch                        |
| `$1400-$14FF`   | BOARDST: 0x88 board, game state, AI and search scratch     |
| `$2000-$3FFF`   | HGR page 1                                                 |
| `$6000-$95FF`   | CODE + ENGINE, the single 8 942-byte BRUN file             |
| `$9600-$BFFF`   | DOS 3.3                                                    |

**Engine.** `chess_engine.asm` comes from POM1's `dev/lib/games/chess`: the
rules code is unchanged, the move generator and the search were reworked here
for speed (see `TODO.md`, Done). The board is a 0x88 mailbox (`sq = rank*16 +
file`, one byte per square, bit 7 = black), a move is three bytes (from, to,
flags: promotion piece, capture, double push, en passant, castle side). Move
generation is per piece (`gen_targets`), attack detection starts from the
target square (`is_attacked_runner`), and the material of both sides is kept
up to date by `make_move` / `unmake_move` (`mat_tot`). The front-end talks to
the engine through `init_board`, `apply_user_move`, `ai_play_move`,
`game_status`, `in_check`, `piece_at` and `undo_last_move`.

**Shared libraries** from `../dev`:

- `lib/apple2`: `kbd.asm` (`wait_key` / `poll_key`, latch `$C000` + strobe
  `$C010`, arrow codes), `hgr.asm` (`hgr_init_clear`), `print.asm`
  (`print_str_ax` for the text-screen menu), `joy.asm` (`read_stick` /
  `stick_dir`, with the empty-port detection), `sound.asm` (`tone`) and
  `delay.asm` (`delay_ms_a` between the notes).
- `lib/hgr`: `sprites/chess_cc65_pieces.asm` (6 pieces x 2 variants x 22
  rows x 3 bytes) and `hgr_scanline.inc` (`hgr_lo` / `hgr_hi` base-address
  tables).
- `lib/font`: `bbfont.inc`, the Beautiful Boot 8x8 font, ASCII `$20-$5F`
  (64 glyphs, 512 bytes) for the panel.
- `tools/dos33.py` builds the bootable disk.

## Differences from the POM1 original

- No second terminal: the game-mode menu is shown on the Apple II text
  screen (the board waits on HGR page 1), and the turn, check and game-over
  messages move onto the right-hand panel of the HGR screen (row 1; row 23
  carries `N = NEW GAME` once the game is over).
- Apple II keyboard (`$C000` + `$C010`), arrow keys in addition to IJKL.
- One binary at `$6000`; zero page at `$50` so the Monitor's `COUT` keeps
  working; game state in `$1000-$14FF`; the BASIC `HELLO` at `$0800` stays
  intact.
- The engine's `is_pseudo_legal` / `make_move` / `unmake_move` are still
  exported for POM1's text front-end (its list-moves and hint commands);
  this port does not use them.

## Credits and licence

- Code: VERHILLE Arnaud, 2026 — GPL-3.0 ([LICENSE](../LICENSE) at the
  repository root), like POM1 and POM2 it derives from.
- Board and pieces: [cc65-Chess](https://github.com/StewBC/cc65-Chess) by
  Stefan Wessels, Apple II port by Oliver Schmidt, piece art by Frank Gebhart.
- 8x8 font: Beautiful Boot, Michael Pohoreski.
