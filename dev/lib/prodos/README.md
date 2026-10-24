# ProDOS 8 for Apple //e enhanced 128 KB games

`prodos.h`, `mli.s`: MLI call at `$BF00`, constants for files, blocks,
prefixes and quitting. Supply `prodos_command` and `prodos_params`, then call
`prodos_call()`; the result is zero or the ProDOS error code. Parameter lists
start with a parameter-count byte, followed by the fields from the manual.
A read buffer must sit in pages that are free in the system
bitmap; this interface does not allocate a buffer and does not change its protection.

`video.s`: explicit takeover of auxiliary memory for
DHGR and rebuilding of the empty `/RAM` disk on exit.
`prodos_video_claim(PD_VIDEO_PRESERVE_RAM)` refuses any installed `/RAM`,
even empty; this policy does not walk its files.
`PD_VIDEO_DISCARD_RAM` explicitly allows their destruction. Call this
service before the first auxiliary drawing and check for `PD_VIDEO_OK`.
The other statuses report a `/RAM` to preserve, an invalid policy or
a malformed device list. A refusal keeps the active
transaction; a repeated claim keeps the unit to restore. Releasing calls
FORMAT only once. ChromaBreak explicitly chooses DISCARD.
The search stays within the 14 entries of `DEVLST` (`$BF32–$BF3F`):
`DEVCNT` holds the number of units minus one, or `$FF` if the list is empty.
Indices above 13 are ignored and trigger no formatting.
`make test-tools` checks these bounds on the cc65 code with a test FORMAT
driver that records the requested unit.

C startup: [`crt0_prodos.s`](../../cc65/crt0_prodos.s) and
[`apple2_dhgr_prodos_c.cfg`](../../cc65/apple2_dhgr_prodos_c.cfg). The binary at
`$6000` uses the main/aux video pages `$2000–$5FFF`. The runtime saves
the zero page, the RESET vector and the system bitmap, then restores them before
the MLI `QUIT` call. The game supplies `game_shutdown()` to stop its mouse,
restore text mode and release video memory. RESET follows this exit path.

Full example: [`chromabreak`](../../../chromabreak/README.md).
The `CHROMA.SYSTEM` loader loads `CHROMA.SYS`, which relocates the program to `$6000`
by copying from the end, including when source and destination overlap.

## The .SYSTEM shim (`sysboot.s`)

ProDOS starts the first `.SYSTEM` file; `sysboot.s` loads the game's SYS
file at `$2000` and jumps there. It first checks the CPU with 6502
instructions only (an NMOS //e gets a message, a key, back to ProDOS), then
from `$0800`: ONLINE on the boot unit, SET_PREFIX to the volume (the game
opens its files by name), OPEN / READ / CLOSE of `/VOLUME/FILE`. Any error:
a message, a key, QUIT. The game's `src/boot.s`:

```asm
.define SYSBOOT_FILE  "WG2.SYS"
.define SYSBOOT_TITLE "WARGALAGA II"
.include "sysboot.s"
```

```make
$(BUILD)/WG2.SYSTEM: src/boot.s $(PRODOS_SYSBOOT_DEPS)
	$(CA65) -I $(PRODOS) -o $(BUILD)/boot.o src/boot.s
	$(LD65) -C $(PRODOS_SYSBOOT_CFG) -o $@ $(BUILD)/boot.o
```

A SYS image in one piece at `$2000` (a startup that relocates the game)
links with `$(PRODOS_SYS_CFG)` (`dev/cc65/prodos_sys.cfg`). Users:
CHROMABREAK, WARGALAGA II.

## Whole files (`file.asm`, `file.s`)

`file.asm`, included at the end of an assembly program (`.ifref`: only what
is called is assembled, 65C02), wraps OPEN / READ / WRITE / CLOSE on one
set of parameter lists. Set `pf_name` (Pascal string, relative to the
prefix or a full path), `pf_iobuf` (1 KB, page aligned, free in the
bitmap), `pf_buf`, `pf_len`; the calls return C = 1 and A = the MLI error
(also in `pf_err`), `pf_got` = bytes moved.

| Routine | Effect |
|---|---|
| `prodos_open`, `prodos_read`, `prodos_write`, `prodos_close` | one MLI call each (`$4C` = end of file from READ) |
| `prodos_read_free` | READ with the destination pages freed in the system bitmap meanwhile (pages a crt0 claimed: HGR/DHGR page 2), the bitmap then put back |
| `prodos_load`, `prodos_load_free` | OPEN, READ, CLOSE (always); the READ's error first |
| `prodos_save` | OPEN, or CREATE a BIN file (access `$C3`, seedling) then OPEN; WRITE; CLOSE; the first error |

C programs link `$(PRODOS_FILE_SRCS)` (`file.s`): `prodos_file_name`,
`prodos_file_iobuf`, `prodos_file_buffer`, `prodos_file_length`,
`prodos_file_actual`, `prodos_load()`, `prodos_load_free()`,
`prodos_save()` (prodos.h). Users: WARGALAGA II (`HIGHSCORES`, from its
title overlay), CHROMABREAK (`HIGHSCORES`, the `ENDING` overlay).

Reference: [ProDOS technical reference, system programs](https://prodos8.com/docs/techref/writing-a-prodos-system-program/).
