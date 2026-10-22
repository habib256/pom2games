# DHGR — Apple IIe / IIc

A first page shows the 16 colours, white text and a `gfx` circle. A key then
starts a DHGR animation of three colour balls over a grid, with a frame
counter. They bounce off the edges and off each other, swapping their
directions on contact (distance of 6 pixels).
Arrows: direction of the three balls; space: pause/resume; Escape: DOS
(also from the introduction page).
The masked sprites save and restore the background separately on both
pages, in reverse drawing order to preserve overlaps.
A II/II+ gets a message saying that DHGR is unavailable.

Hardware: IIe **revision B**, **extended** 80-column card with 64 KB of
auxiliary memory and the appropriate DHGR jumper, or IIc. The RAM is probed;
the revision and the video jumper cannot be detected in software. The demo
uses `a2_frame_init` / `a2_frame_wait`: VBLBAR on the IIe, a timed delay on
the IIc. The waits are bounded and the timed delay does not guarantee a
tear-free flip. See the [frame-rate service](../../lib/apple2c/apple2frame.h).

```sh
make -C dev/examples/dhgr
make -C dev/examples/dhgr run
make -C dev/examples/dhgr assets
make -C dev/examples/dhgr test  # primitives and animation on the IIe
make test-dhgr
```

The animation uses the **140 × 192** DHGR colour coordinates, the DHGR
sprites and transfers between main and auxiliary RAM; the HGR primitives are
not used. The sprite and block-transfer modules are already part of
`HGRC_DHGR_SRCS`, linked with the colour DHGR `gfx` backend.

The loop uses `src/ball_render.s`, a specialised assembler renderer for the
three 6 × 6 sprites (5-byte stride), with address and phase tables. Saving
the background and masked drawing are done in a single pass.
The counter uses DHGR digits precomputed from the Beautiful Boot font (`dev/tools/fonts.py`) in
`src/digits.inc` and only rewrites the digits that changed on each page.
The balls must stay entirely on screen: this renderer does no clipping. The
general primitives are still used for the introduction and the grid.

Measured in the POM2 IIe core at about 1 MHz: **299 frames in 10 seconds**,
against 37 before optimisation, i.e. about **30 frames/s and an 8× gain**.
The animation test requires at least 20 frames/s; the rendering test compares
both banks with the general DHGR primitives, with the seven sprite phases,
overlaps, edges and all digits.

The disk is `dist/DHGR.dsk`. `a2shot` for the tests is built with
`make -C dev/tools/a2shot` on macOS arm64 or Linux x86_64, with libslirp and zlib.

```c
#include "dhgr.h"

if (!dhgr_init()) return 1;
dhgr_draw_page(2);
dhgr_clear(DHGR_BLACK);
dhgr_plot(559u, 191u, 1u);                     /* 560×192 bits */
dhgr_fill_rect(10u, 20u, 40u, 30u, DHGR_ORANGE); /* 140×192 colours */
dhgr_puts("APPLE II", 10u, 8u);                /* white colour text */
dhgr_flip();                                  /* wait for VBL first if needed */
dhgr_text_restore();                          /* before ROM text routines */
```

The C configuration places the code at `$6000`, above **both** video pages.
The details of RAMRD/RAMWRT accesses, the ZP trampoline and the backends are
in the [library's memory contract](../../lib/hgrc/README.md#memory-contract-and-transitions).
The archive only loads the families in use; a DHGR `gfx` backend is linked
explicitly. The [converter](../../tools/assets/README.md) produces the banks
and masks of `src/ball.h`; `src/ball.json` gives their size.
The assembler renderer reads the same data from `src/ball.bin`.

Hardware sources: [Apple IIe Technical Note 3, Double High-Resolution Graphics](https://mirrors.apple2.org.za/ftp.apple.asimov.net/documentation/hardware/misc/Apple%20IIe%20Technical%20Notes.pdf)
and [Apple II Miscellaneous 7, Family Identification](https://mirrors.apple2.org.za/apple.cabi.net/FAQs.and.INFO/A2.TECH.NOTES.ETC/A2.CLASSIC.TNTS/a2misc007%281%29.htm).
