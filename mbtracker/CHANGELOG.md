# MB TRACKER — changelog

Finished lots, moved out of [TODO.md](TODO.md) on 2026-11-16.

## Lot 1 — the editor (done, 2026-10-31)

- [x] Pattern grid: 3 voices shown (grid planned for 6, columns 4-6 by
  moving right for a 6-voice file), 64 rows, note / instrument / effect +
  parameter, two-row piano, octave, note off, clear, row insert / delete,
  speed, rows.
- [x] Order list: entries, pattern number, new pattern / copy, insert /
  delete, loop or stop at the end.
- [x] Instrument editor: ticks (volume, tone, noise, envelope, noise
  period), loop, envelope shape and period, name, preview.
- [x] Playback: `mb_irq` 50 Hz + `ays_tick`, song / pattern loop, cursor
  follow, mutes, re-encoding during playback; without a card: a message,
  editing and files only.
- [x] `.AYS` files: catalog, typed name, save, `DEMO.AYS` shipped; tests on
  //e, //c and without a card.

## Lot M1 — mouse (done, 2026-10-31)

- [x] Pointer (inverted cell, the text is drawn under it), clicks in the
  grid (field), the row numbers (pages), the order list, the instruments
  (two clicks: the editor), the voice names (mute), the bottom bar, the
  instrument editor, the file list; drag = block.
- [x] Mockingboard detected **before** the mouse. On the //c, the 4c once
  woken masks the mouse firmware (POM2 and the real card): keyboard only
  with a 4c; the //c's mouse without a card.
- [x] Memory: overlays OVL1 (instrument editor) and OVL2 (files + decoder),
  kept in the auxiliary LC; file names in the work pattern; paged help
  (offset header).
- [x] a2shot `--mouse-slot=N` (mouse card outside the Mockingboard's slot 4).

## Lot M2 — blocks (done)

- [x] `^B` mark, `^C` `^X` `^V` (across patterns, clipboard in aux),
  `;` `'` `:` `"` transpose, `^Z` undo / redo (cell or pattern).
- [x] Order list: `I` insert a new pattern, `C` clone, `D` delete a
  pattern (renumbering).

## Lot M3 — 6 voices (done)

- [x] Player `AYSONG_VOICES=6`, `MB_IRQ_HUSH_BOTH=1` (and the fix to
  `mb_hush` in this mode: a `beq :++` that aimed at the wrong label);
  tick ≤ 5,309 cycles.
- [x] `^N`: 3 or 6 voices; grid of 6 columns of 8 characters.

## Lot M4 — PT3 import (done)

- [x] `dev/tools/audio/pt3play.py` (= `pt3/` under a2run, register for
  register), `pt3import.py` (report of what is lost), `aysong.py
  --import-pt3`, `--to-50hz`; `WG.AYS` on the disk.

## Lot M5 — 3 ↔ 6 voice conversion (done, 2026-10-31)

- [x] `^W`: 3 → 6 (voices 4-6 empty, refused beyond 32 patterns), 6 → 3
  (confirmation if voices 4-6 are in use); the aux pattern store
  repacked (upwards starting from the last one, downwards from the first),
  in OVL1 (`voices.c`, `song_voices`); `^Z` forgotten.
- [x] `aysong.py`: `Song.with_voices(n)`, `--voices N` (and a `.AYS` as
  input); tests `test_aysong.py` and `test_mbt.py`.
