# HGR — animated starter example

*[← dev](../../README.md)*

C program for the Apple II/II+ 48 KB under DOS 3.3, also usable on the IIe
and IIc. It shows three masked balls over a grid, a frame counter,
non-blocking keyboard input and the two HGR pages. Its archive only loads the
families in use. Author: VERHILLE Arnaud; licence [GPL-3.0](../../../../LICENSE).

```sh
make -C dev/examples/hgr
make -C dev/examples/hgr run
make -C dev/examples/hgr test
```

The balls start at different positions and in different directions, and
bounce off the edges and off each other. A collision swaps the directions of
the two balls when they get close; detection uses a distance of 7 pixels
between their centres.
The disk is `dist/HGR.dsk`. Arrows: direction of the three balls; space:
pause/resume; Escape: back to DOS. On the II+, Ctrl-K/Ctrl-J replace the
up/down arrows. Ctrl-RESET also goes through the CRT restore.

## Animation loop

1. Initialise the video and `a2_frame_init()`.
2. Draw the background on **both pages**, then `hgr_spr_init_pool` with a
   pool sized for the three sprites and their two backgrounds.
3. Define the three sprites and check the result of `hgr_spr_define`.
4. Read the keyboard and compute the position of each ball.
5. `hgr_spr_render()` restores the old position and draws on the hidden page.
6. Draw the counter on that same page, outside the sprite area.
7. `a2_frame_wait()` waits; `hgr_spr_present()` displays and selects the
   other page for the next drawing.

Do not change the background under a sprite already drawn: its saved copy
must stay valid until it is restored. To change its shape, hide it and update
each page before redefining it. ×1 text stays white.

## Frame rate by model

| Model | Behaviour |
|---|---|
| IIe / IIe enhanced | Waits for the next start of VBL via `$C019`, then flips |
| II / II+ | CPU timed delay; no readable VBL |
| IIc / IIc Plus | Timed delay; no change to the interrupt sources |
| IIgs | Timed delay; its different VBL polarity is not used |

The timed delay adds to the drawing time. The example uses WAIT(70), about
13 ms at 1.02 MHz, to be adjusted for the program and any accelerator. It
guarantees neither 60 frames/s nor a tear-free flip. On the IIe, a frame that
costs too much can miss a VBL and lower the frame rate. The VBL waits are
bounded: if the signal stays stuck, the service switches to the timed delay
until it is initialised again.

## Adapting and checking

Copy the folder; to place it next to the games, set `DEV ?= ../dev` and
`DIST ?= ../dist`. Keep `crt0_apple2.o` first at link time. The Makefile adds
`APPLE2C_FRAME_SRCS` to the archive for the frame-rate service. The sprite and
its masks are precomputed, with no conversion during the animation.

```sh
make -C dev/examples/hgr assets  # regenerates ball.h/.bin/.png/.json from ball_source.png
make test-hgr                  # primitives, archive and sprite engine
make test-frame                # timed delay and bounded fallback, portable
make test-hgr-example          # animation, pause/resume, controls and exit
python3 dev/tests/test_frame.py --iie
python3 dev/tests/test_hgr_example.py --iie
```

The last two commands require `a2shot` (POM2 SDK, macOS arm64 or Linux x86_64). The tests
with IIc/IIgs ROM signatures only check the mode selection; they are not a
validation on IIc/IIgs hardware.

Apple references: [Family identification, Miscellaneous note #7](https://mirrors.apple2.org.za/apple.cabi.net/FAQs.and.INFO/A2.TECH.NOTES.ETC/A2.CLASSIC.TNTS/a2misc007%281%29.htm),
[VBL polarity, IIGS note #40](https://apple2.gs/technotes/tn-iigs-040/),
[IIc #9, Detecting VBL](https://mirrors.apple2.org.za/Apple%20II%20Documentation%20Project/Computers/Apple%20II/Apple%20IIc/Documentation/Apple%20IIc%20Technical%20Notes.pdf).

The counter uses `hgr_hud_field_t`, with one history per page: only the
changed cells are erased/redrawn. Invalidate this field after any external
change to its background.

The program and its archive use `HGR_SPR_MAX=3`, which also shrinks the
engine's metadata, on top of the 84-byte external pool.
