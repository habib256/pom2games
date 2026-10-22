# Apple II assets

Converter with no external Python dependency: non-interlaced 8-bit PNG
(grey, RGB, palette or RGBA) and PPM P3/P6. The image must fit in 280×192
for monochrome HGR or 140×192 for colour DHGR. No implicit resizing.
Alpha < 128 = transparent; a full-screen image is composited over black. The
HGR conversion is a monochrome threshold, with no colour palette or
dithering. DHGR picks the closest LORES colour in RGB; the two identical
greys are represented by number 5.

```sh
python3 dev/tools/assets/convert.py image.png --mode dhgr --kind sprite --out build/ship --name ship
python3 dev/tools/assets/convert.py image.ppm --mode hgr --kind frame --out build/screen
```

## Outputs

| File | Contents |
|---|---|
| `.h` (sprite) | WIDTH/HEIGHT/STRIDE constants, `<name>_data` and `<name>_mask` arrays |
| `.bin` (sprite) | The seven data banks, then the seven mask banks |
| `.bin` (image) | HGR: 8 KB; DHGR: 8 KB main then 8 KB auxiliary, addresses relative to the page |
| `.png` | Quantised preview; the actual NTSC fringes depend on the monitor |
| `.json` | Dimensions, stride, total ROM, mask and save-under buffer size |

The arrays have seven consecutive `stride * height` banks, for phases 0..6.
Each byte represents seven bits, bit 0 on the left; mask 1 = keep the
background. Edges and transparency are masked. Bit 7 of the mask stays at 1
and that of the data at 0.

- HGR: create `hgr_mspr_t {data, mask, stride, height}` and use it with
  the `hgr_spr_define` API; the plain banks suit `hgr_sprite_t`.
- DHGR: pass WIDTH, HEIGHT, STRIDE and the two arrays to `dhgr_sprite`.
  x is a **colour** pixel; the routine picks `(x * 4) % 7`.
- A phase bank larger than 65,535 bytes is rejected. The program's actual
  ROM budget is usually much smaller; check the JSON and split large images
  into tiles.

Choose an output prefix different from the source image to keep the
original. The declarations of the old ×2 reference conversions are in
`dev/lib/hgrc/hgr_host.h`, outside the target API.

`make test-assets` checks the five PNG filters, PPM, the framebuffer layouts
and the masks of all phases. The DHGR test uses a sprite produced by this
converter and compares it with the expected drawing.

## Pre-packed TMS sprites for HGR (assembler)

`pack_hgr_sprites.py` turns 16×16 TMS patterns (32 bytes, left column then
right, bit 7 on the left) into seven sizes: 8, 16, 32, 64, 4, 2 and 1 pixels.
The generated ca65 file contains the pointers and the `_width`, `_height`,
`_source_rows`, `_vertical` and `_last_mask` tables. Vertically repeated rows
are stored only once; the small sizes use the maximum of the source blocks to
keep the silhouettes.

```sh
python3 dev/tools/assets/pack_hgr_sprites.py --out build/ship.inc --prefix ship art.asm:ship_pattern
```

The runtime `dev/lib/hgr/hgr_sprite_packed.asm` draws this data on a
byte-aligned HGR column. This format does not contain the seven phases of the
PNG/PPM converter: choose the runtime that matches the format produced. The
pattern credits stay in their original sources.

## LZ4FH HGR compression

Include `dev/cc65/fhpack.mk` after `apple2.mk` to get the `$(FHPACK)` target
(a C++ compiler is required). The upstream sources and licences stay pinned
in `dev/tests/techniques/upstream/fhpack`.

```sh
build/fhpack -c -9 -h title.hgr build/title.lz4fh
build/fhpack -d build/title.lz4fh build/title.roundtrip.hgr
cmp title.hgr build/title.roundtrip.hgr
```

Keep `-h` so that the holes of the HGR page are restored too. The shared
6502 decompressor is in `dev/lib/apple2/lz4fh.asm`. The compressed buffer
limit, disk loading and addresses remain specific to each program.

The converter offers automatic selection for HGR images:

```sh
python3 dev/tools/assets/convert.py title.png --mode hgr --kind frame \
    --out build/title --fhpack build/fhpack
```

The raw `.bin` is kept. `.load.bin` contains the LZ4FH stream only if it is
smaller; otherwise it contains the raw data. The JSON gives `load_file`,
`load_encoding` (`lz4fh` or `raw`) and `load_bytes`. Each compressed stream
is decompressed and compared with the original 8,192 bytes before selection.
This option rejects sprites and DHGR: the target decoder works on an aligned
8 KB HGR page. The application loader chooses its source buffer and must only
call the decoder for `load_encoding=lz4fh`.

## Shared HGR tables

`dev/tools/hgr_tables.py` provides `hgr_offset(y)`, `scanline_tables(page)`,
`division_tables(width)` and `shift_tables()`. The PNG/PPM converter, the
`a2test` harness and the Pinball builder share the HGR address computation.
The shift tables contain six phases of 256 entries, keeping the palette bit
and removing isolated `$80` bytes, per the PCS contract. Placing the tables
in the game's memory is left to the caller.
