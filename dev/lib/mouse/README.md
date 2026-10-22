# AppleMouse II

cc65/6502 driver for the AppleMouse firmware in slots 1 to 7. `mouse_init()` detects
the card, initialises polled mode 1, clamps X to 0–139 and Y to 0–191,
and positions the mouse at the centre. It returns the slot, or zero if there is none.

`mouse_poll()` provides `mouse_x`, `mouse_y` and `mouse_buttons` (bit 7: main
button pressed). The game computes the rising edge to tell a click
from a held button. `mouse_close()` disables the card on exit.

On //e, the driver does not request mouse interrupts and preserves the IRQ
mask. On //c, it enables the native interrupts needed to count
movements, while still reading the position by polling. In both cases, it
copies the READMOUSE results before restoring that mask. The caller must
use main RAM and main zero page, 80STORE off, ROM visible.
Coordinates correspond to DHGR colour pixels; the paddle follows
X and no extra software cursor is drawn.

Validated with both POM2 cards `mouse` (MC68705) and `mouseaw` (AppleWin),
both running the Apple slot ROM. Also validated with the **native built-in
//c mouse**, without ROM substitution, 16 and 32 KB versions.
The //c+ is not validated yet.

Reference: [Apple II Mouse Technical Notes, notes 1 and 5](https://mirrors.apple2.org.za/Apple%20II%20Documentation%20Project/Interface%20Cards/Digitizers/Apple%20Mouse%20Interface%20Card/Documentation/Apple%20II%20Mouse%20Technical%20Notes.pdf).

The ChromaBreak client also uses `_mouse_timing_mode` and `_mouse_serve_irq`
for the //c's mode 9 (VBL), with a handler allocated through ProDOS.
Closing disables this mode before releasing the handler. Without a mouse
(`mouse_slot` = 0, or before `mouse_init`), both return C = 1 immediately,
without calling the firmware.

`ca65 -D MOUSE_INIT_BOOT` puts `mouse_init` (detection and settings) in the
`INIT` segment: startup code that a buffer can later overwrite
(DIRTBIKE, where the driver otherwise stays resident). With the //c mouse, which
enables interrupts, a DOS 3.3 program must mask them during
RWTS (`RWTS_SEI`, `apple2/rwts.asm`; `DOS_SEI` for the commands of
`apple2/dos.asm`).

## Optional context for legacy assembly programs

`mouse_context.asm`, extracted from Pinball, protects the whole zero page and the
64 bytes of mailboxes in the text page holes.
The `mouse.s` driver stays independent: include this module only in
programs that reuse those areas. `mouse.mk` provides the
`MOUSE_CONTEXT_SRCS` dependency and the `MOUSE_INCS` path.

Initialise `mouse_context_native_mouse` to zero before detection, then
set it to a non-zero value for the native //c firmware. The functions
`mouse_context_save_workspace` and `mouse_context_restore_workspace`
wrap the firmware call; the caller masks IRQs for the whole
transaction. On a slot card, the mailbox copy is reinstalled;
on //c, the coordinates updated by the IRQs stay in RAM.
`mouse_context_capture_holes` / `mouse_context_install_holes` also
make it possible to protect these mailboxes around another user of the text page.

The DOS client is optional and is configured before the include:

```asm
MOUSE_CONTEXT_DOS_ENTRY = $AAFD
MOUSE_CONTEXT_DOS_ROWS = 6
MOUSE_CONTEXT_CLEAR_BASE = $0400
MOUSE_CONTEXT_CLEAR_PAGES = 3
.include "mouse_context.asm"
```

These values are PCS's; another client supplies its own.
`mouse_context_clear_buffers` clears the requested pages and keeps the
native //c mailboxes. `mouse_context_file_manager` atomically swaps the
DOS/mouse copies on //c around the configured entry point and keeps the
caller's A/X/Y results, error flags and IRQ mask.
The entry point receives X/Y, and A holding the native flag, following PCS's
legacy ABI. The calls are not reentrant.

Without a DOS client, the module reserves 321 bytes of BSS and no zero page;
the PCS client adds 53 bytes of BSS. The caller keeps these buffers and the
code resident, initialises their contents and keeps its own tables out of the
hardware mailboxes. The PCS addresses, the choice of paddles, the
coordinate conversion and the drag anchoring stay in Pinball.

`python3 dev/tests/test_mouse_context.py` tests the module without a DOS client.
`make -C pinball test-mouse` validates the integration with the `mouse` and
`mouseaw` cards, slots 4/5 and the native 16/32 KB //c ROMs.
