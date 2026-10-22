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

Reference: [ProDOS technical reference, system programs](https://prodos8.com/docs/techref/writing-a-prodos-system-program/).
