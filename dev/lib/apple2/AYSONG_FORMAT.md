# AYS song format, version 1

A compact Mockingboard song for games: 3 voices (one AY) or 6 (both),
patterns of up to 64 rows, up to 15 instruments, a handful of effects.
Played by [`aysong.asm`](aysong.asm) (one `ays_tick` per 50 Hz tick,
usually from [`mb_irq.asm`](mb_irq.asm)); written by
[`dev/tools/audio/aysong.py`](../../tools/audio/aysong.py) (encoder, decoder,
text/JSON import, `--asm` emitter) and by the native tracker (`mbtracker/`). The
Python module's docstring is the reference text; its `Player.tick()` is
the bit-exact model of the asm (`dev/tests/test_aysong.py` compares them
register for register).

Size: the demo song (3 voices, 4 patterns of 16 rows, 6 instruments) is
353 bytes; a 3-voice song of 8 different 64-row patterns with a note every
two rows is 1,574 bytes.

## Layout

All words little endian; every offset is from the song's first byte, so a
song loads anywhere (the player adds its address).

| Offset | Size | Field |
|---|---|---|
| 0 | 3 | `'AYS'` |
| 3 | 1 | version = 1 |
| 4 | 1 | voices: 3 or 6 (voices 3-5 on the second chip) |
| 5 | 1 | rows of every pattern, 1..64 |
| 6 | 1 | speed: ticks per row, 1..255 |
| 7 | 1 | rate: ticks a second the song expects (50); informative, the caller's timer sets it |
| 8 | 1 | order length, 1..255 |
| 9 | 1 | loop: order index played after the last entry; `$FF` = stop (silence) |
| 10 | 1 | instruments, 1..15 |
| 11 | 1 | patterns, 1..255 |
| 12 | 2 | offset of the order list (one pattern number a byte) |
| 14 | 2 | offset of the pattern table: a word a pattern → its block of `voices` words, each the offset of that voice's track (identical tracks are shared) |
| 16 | 2 | offset of the instrument table: a word an instrument, instrument 1 first |
| 18 | 2 | offset of the texts, 0 = none: NUL-terminated ASCII song name, author, then one name an instrument (the player never reads them) |

The encoder places, after the header: the order list, the tracks, the
pattern blocks, the pattern table, the instruments, the instrument table,
the texts. Only the offsets matter to the player.

### Tracks

One voice of one pattern: a byte stream of exactly `rows` rows. A row is
zero or more prefixes, then one row byte.

| Byte | Kind | Meaning |
|---|---|---|
| `$00-$5F` | row | note 0..95: C0..B7 (note = MIDI − 12; 57 = A4 = 440 Hz) |
| `$60` | row | note off: the voice is silent |
| `$61-$6F` | prefix | instrument 1..15 for the following notes |
| `$70` | prefix | effect off |
| `$71-$77` | prefix | effect 1..7, followed by its parameter byte |
| `$80-$BF` | row | 1..64 empty rows (the voice goes on: hold) |
| `$C0-$FF` | — | reserved |

### Effects

One per voice. It runs every tick the voice is on, until the next note or
effect prefix. A note without an effect prefix on its row has none; a note
resets the slide and the volume offset. An effect prefix restarts its
counter; on an empty row it replaces the effect and keeps the slide and
the volume offset.

| # | Text | Parameter | Each tick |
|---|---|---|---|
| 1 | `A` arpeggio | `$xy` | note, note + x, note + y (cycle of 3; capped at 95) |
| 2 | `U` slide up | p | slide −= p (16 bits; period register = (table + slide) & `$FFF`) |
| 3 | `D` slide down | p | slide += p |
| 4 | `F` fade | p ≥ 1 | volume offset −1 every p-th tick, down to −15 |
| 5 | `S` swell | p ≥ 1 | volume offset +1 every p-th tick, up to +15 |
| 6 | `N` noise | p | the chip's noise period R6 = p & 31 |
| 7 | `E` env period | p | the chip's envelope period R12 = p, R11 = 0 |

### Instruments

A 4-byte header, then one or two bytes a tick. Offsets are within the
instrument's block.

| Offset | Field |
|---|---|
| 0 | end: 4 + the tick data's length (5..254) |
| 1 | loop: the offset the macro continues at after its last tick (4..end−1; the last tick's own offset = hold it) |
| 2 | envelope shape 0..15 written to R13 when a note starts, `$FF` = none |
| 3 | envelope period: R12 (R11 = 0) set with that shape |
| 4.. | ticks: `%XENTVVVV` — V volume 0..15, T tone on, N noise on, E hardware envelope (volume register `$10`), X: one more byte follows, the chip's noise period (bits 0-4) from this tick on |

## Playing

`ays_tick`, and `Player.tick()`, do this every tick:

1. R13 = `$FF` on every chip. If the song plays and its row is due (the
   first tick after `ays_init` / `ays_set_pos`, then every `speed` ticks):
   past the last row, the next order entry (after the last: the loop
   entry, or the end: every voice off, stopped, order 0); then every voice
   reads its row (a voice inside an empty run counts it down) and the row
   advances.
2. Every voice, in order: its effect, its instrument tick, its registers.
   An off voice: volume 0, its tone and noise bits set (off), its period
   registers kept. A voice on: period = (table(note + arpeggio) + slide) &
   `$FFF`; volume = `$10` with E, else clamp(V + offset, 0, 15), 0 when its
   mute bit is set; tone bit = not T, noise bit = not N. A note's first
   tick with a shaped instrument sets R11 = 0, R12, R13 = shape. Noise and
   envelope registers are the chip's: the last voice that set them wins,
   they persist.
3. The frame (R0..R13 of each chip) goes out: the registers that differ
   from the last written ones, R13 whenever it is not `$FF` (a write
   restarts the envelope).

Periods: octave 0 (C0..B0) = round(1,020,484 / (16 f)), equal
temperament, A4 = 440 Hz, for the NTSC Apple II clock that drives the
Mockingboard: 3901 3682 3475 3280 3096 2922 2758 2603 2457 2319 2189 2066.
Octave k = (p + 2^(k−1)) >> k, so B7 = 16. A PAL Apple II (1,015,657 Hz)
plays 8 cents flat.

`ays_init` resets the registers (0, R7 = `$3F`, R13 = `$FF`), sets every
voice off with instrument 1, the mute mask to 0, and starts at order 0
row 0. `ays_set_pos(order, row)` turns every voice off until its next note
and walks the rows before `row` reading only instrument prefixes; the next
tick reads `row`. `ays_pos` returns the next row to be read.

## For an editor

- Patterns of up to 64 rows, all of the song's length (`rows`); the order
  list is a plain byte list (insert, delete, repeat a pattern freely); up
  to 15 instruments; names live in the optional text block.
- `aysong.py` gives `Song` / `Pattern` / `Cell` / `Instrument` / `Tick`
  dataclasses, `encode` / `decode` (round trip exact), `to_json` /
  `from_json`, `load_text` (hand-written songs), and `--asm` for games.
- On the Apple II, `ays_pos` / `ays_set_pos` follow and move the cursor,
  `ays_mute` solos or mutes voices; the song bytes can be rebuilt in RAM and
  `ays_set_pos` called again (under SEI, or with the tick stopped).
- Vortex Tracker II modules: `dev/tools/audio/pt3import.py IN.pt3 -o OUT.AYS`
  (or `aysong.py --import-pt3 IN.pt3`). Samples become tick-macro
  instruments (one per sample × channel volume × envelope / noise use, up to
  15), ornaments of the form 0, x, y the `A` effect, the speed the gcd of
  the line durations, patterns cut to a common row count; what cannot map
  (portamento, vibrato, envelope slides, sample pitch offsets, other
  ornaments, mid-note volume changes) is listed with counts in `--report`.
  Pitch: `--clock apple` (what `pt3/` plays on the Mockingboard) or
  `native` (the composer's 1.77 / 2 MHz); `--rate 25 --to-50hz` retimes a
  25 Hz song (WARGALAGA II's) for a 50 Hz player.
