# lib/tms9918 — POM1's TMS9918 drivers on the E-Z Color card (asm)

*[← dev](../../README.md)*

POM1's `dev/lib/tms9918` (the Apple-1 P-LAB card drivers, same author,
GPL-3.0) ported at POM1 commit `e399808` to the Apple II **E-Z Color Graphics
Interface**: the card is found at run time and reached through
[`../apple2/ezcolor.asm`](../apple2/README.md#e-z-color-tms9918a-card).
Each file keeps its POM1 name and says so in its first lines, so code ported
from POM1 (TMS_Rogue) keeps recognisable includes. Rendered pictures:
`dev/tools/tms9918.py`; emulation: `a2run --ezcolor=N`; tests:
`dev/tests/test_ezcolor.py`. Not validated on real hardware.

## Port rules

| POM1 (P-LAB `$CC00`/`$CC01`) | here |
|---|---|
| `STA VDP_DATA` + `JSR tms9918_pad18` | `JSR ez_data_w` (same 22 cycles, 3 bytes, A/X/Y/flags kept) |
| `STA VDP_CTRL` + pad | `JSR ez_ctrl_w` |
| `LDA VDP_DATA` | `JSR ez_data_r` (N/Z as LDA, padded) |
| `LDA` / `BIT VDP_CTRL` | `JSR ez_status` / `JSR ez_status_bit` |
| unpadded fills with the display blanked | `ez_fill_blank` / `ez_copy_blank` (9 / 14 cycles a byte, as POM1's) |
| `WRT_DATA_REG`, `WRT_DATA_VAL`, `WAIT_VBLANK`, `WAIT_VBLANK_SAFE`, `WAIT_5S` | same macros (`tms9918.inc`, on `EZ_*`) |
| `.import` / `.export` of separate objects | one source: `.ifref`-guarded routines, `.include` at the end |

`VDP_DATA` / `VDP_CTRL` are deliberately **not** defined: a forgotten
absolute access fails to link instead of writing to `$CC00`. Never store
to the ports with an index (`STA EZ_DATA,X`): the NMOS dummy read corrupts
the VDP protocol (see the `apple2` README). Each driver routine is one
style, the helper calls: the patched absolute sites live in `ezcolor.asm`
(ca65 ends `@cheap` scopes at any symbol assignment, so sites cannot be
recorded inside the drivers' loops).

The **silicon-strict contract** is POM1's: at least 18 cycles between
back-to-back VRAM accesses while the display is on (22 store to store);
every padded loop here keeps it, and `a2run`'s `vdp_fast_writes` stays 0
in the tests. Bursts run with the display blanked where POM1 did.

## Include order

```asm
.include "apple2.inc"
.include "zp.inc"            ; tmp, tmp2 (name_at_rc, vdp_upload_a, m2, text_bitmap)
.include "tms9918.inc"       ; ezcolor.inc, POM1 macros, driver zero page
        ; ... program ...
.include "tms9918_console.asm"   ; before tms9918_text.asm (it calls it)
.include "text_bitmap.asm"       ; before tms9918m2.asm
.include "tms9918_5strigger.asm"
.include "sprite_helpers.asm"
.include "tms9918m1.asm"         ; or tms9918m2.asm, or tms9918_text.asm
.include "tms9918_helpers.asm"
.include "tms9918_pad.asm"
.include "sprites_outfit.asm"    ; any pattern bank, fonts
.include "ezcolor.asm"           ; LAST
```

`.ifref` only sees references above it, so a caller must precede its callee:
inside each file the routines are ordered callers first. Include path:
`-I dev/lib/apple2 -I dev/lib/tms9918`.

## Files

- **`tms9918.inc`** — includes `ezcolor.inc`; `WRT_DATA_REG`,
  `WRT_DATA_VAL v`, `WAIT_VBLANK`, `WAIT_VBLANK_SAFE`, `WAIT_5S` (A kept);
  reserves the drivers' zero page at the top of the source: options
  `TMS9918_M1_ZP` (default 1: `vdp_lo vdp_hi vdp_src_lo vdp_src_hi vdp_row
  vdp_col`), `TMS9918_M2_ZP` (`pix_* ln_* pen_color`, 17 B),
  `TMS9918_CONSOLE_ZP` (`cur_row cur_col con_tmp`). Each name can be
  aliased by defining it first.
- **`tms9918m1.asm`** — Graphics I (32×24 cells): `init_vdp_g1` (registers,
  16 KB wipe blanked, `disable_sprites`, R1 = `$C0`), `wipe_all_vram`,
  `disable_sprites` (SAT `$D0` + 127 × `$D1`), `clear_name_table`,
  `vdp_set_write` / `vdp_set_read` (at `vdp_lo:hi`), `vdp_upload_a`,
  `name_at_rc`, `print_at_rc`. Tables: patterns `$0000`, names `$1800`, SAT
  `$1B00`, colours `$2000`, sprite patterns `$3800`; R7 = `$01`.
- **`tms9918m2.asm`** — Graphics II bitmap: `init_vdp_g2`, `clear_bitmap`,
  `disable_sprites` (SAT `$3B00`), `vdp_set_write` / `vdp_set_read` (at
  `pix_addr`), `calc_pix_addr`, `plot_set`, `line_xy`; the caller defines
  `plot_mode` (0 = OR, else XOR). Exclusive with m1 / text (same names,
  other tables: an `.error` says so).
- **`tms9918_text.asm`** — Text mode (40×24): `init_vdp_text`,
  `upload_charmap`, `clear_screen_text`, `name_at_rc_text`,
  `print_at_rc_text`; shares `vdp_set_write`/`vdp_set_read` and the ZP
  with m1 (whichever comes first defines them).
- **`tms9918_console.asm`** — `console_init`, `console_putc` (CR, BS,
  scroll), `console_print_ax` on the text driver.
- **`tms9918_5strigger.asm`** — `arm_5s_trigger` (A = trap line),
  `wait_5s_trigger`: a mid-frame trap through the fifth-sprite flag
  (a2run keeps 5S at 0: not testable there).
- **`tms9918_helpers.asm`** — `vdp_write_a` (= `ez_data_w`),
  `vdp_set_write_xy` (X = low, Y = high).
- **`tms9918_pad.asm`** — `tms9918_pad18` (= `ez_pad18`'s 18 cycles,
  flag-transparent), `tms9918_pad12` (alias), `tms9918_pad24`,
  `tms9918_pad40` (legacy, TMS_Rogue), `vdp_display_off` / `vdp_display_on`
  (R1 = `$80` / `$C0`; reset the VRAM address after them).
- **`sprite_helpers.asm`** — `apply_sprite_size`, `heading_to_octant` (no
  VDP access; caller ZP `spr_size spr_xoff spr_yoff spr_r1 th_lo th_hi`).
- **`text_bitmap.asm`** — `text_blit_glyph`: an 8×8 glyph and its colour
  cell on the Graphics II bitmap (caller ZP `mptr_lo/hi`).
- **Fonts** (inline fragments, now include-guarded): `bbfont_tms.inc`
  (`tms_bbfont`, Beautiful Boot, ASCII `$20-$7F`, MSB left),
  `c64font_tms.inc` (`tms_c64font`, the thinner C64-style font POM1
  generates from its own master, shifted for Text mode's 6 px),
  `font_hud8x8.inc` (`tms_hud_font`, 37 HUD glyphs), `font_quale.asm`
  (Quale's font, per-glyph `.ifref`).
- **`sprites_*.asm`** — Quale's 16×16 pattern banks (32 bytes each, left
  half then right half), one `.ifref` block per pattern, RODATA.

### Port differences

- POM1's Text driver and `text_bitmap` read the Apple-1 `charmap.rom`
  (bit-reversed on the fly, 1 KB): here `upload_charmap` uses
  `tms_c64font` (768 B, already in Text mode's 6 visible pixels, chars
  0-31 blank) and `text_blit_glyph` the bolder `tms_bbfont`; codes below
  `$20` blit as `$20..$3F`.
- `init_vdp_g1` / `init_vdp_g2` wipe and fill through `ez_fill_blank`
  (same 9 cycles a byte as POM1's unpadded loops, display blanked).
- `vdp_set_write` / `vdp_set_read` lost their trailing pad: `ez_ctrl_w`
  carries one, so the caller's first data access still comes ≥ 28 cycles
  after the command byte.
- Not ported (no consumer here): `sprite_triangle.asm`, `bubble.asm`,
  `buffer_editor.asm`.

## Attribution

- POM1 `dev/lib/tms9918` — VERHILLE Arnaud, GPL-3.0 (this repository's
  licence); the silicon-strict timing was validated on Claudio Parmigiani's
  Replica-1 with the P-LAB TMS9918 card.
- **SCROLL-O-SPRITES** by **Quale** (May 2013), **CC-BY-3.0**: the
  `sprites_*.asm` banks and `font_quale.asm`. Credit Quale in any program
  that ships them.
- Beautiful Boot font: the repository's `dev/lib/font` master (see its
  README).
