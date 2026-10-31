# ProDOS 8 for Apple //e enhanced 128 KB games

`prodos.h`, `mli.s`: MLI call at `$BF00`, constants for files, blocks,
prefixes and quitting. Supply `prodos_command` and `prodos_params`, then call
`prodos_call()`; the result is zero or the ProDOS error code. Parameter lists
start with a parameter-count byte, followed by the fields from the manual.
A read buffer must sit in pages that are free in the system
bitmap; this interface does not allocate a buffer and does not change its protection.
`prodos_mli(command, params)` (`mli_cmd.s`, in `PRODOS_SRCS`, its own
module: 15 bytes, linked only when called) does both in one call.

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

`prodos.mk` holds that rule as a pattern (`$(BUILD)/%.SYSTEM` from
`src/boot.s`): a game names `$(BUILD)/NAME.SYSTEM` as a prerequisite and
writes no recipe. The bootable volume, without a stage directory:

```make
$(DISK): $(BUILD)/WG2.SYSTEM $(BUILD)/WG2.SYS ... $(PRODOS_VOLUME_DEPS)
	$(call prodos_volume,$@,WARGALAGAII,$(BUILD)/WG2.SYSTEM=WG2.SYSTEM#FF2000 \
		$(BUILD)/WG2.SYS=WG2.SYS#FF2000 ...[,BLOCKS])
```

`PRODOS` comes first by itself; each `SRC=NAME#TTAAAA` is a
`build_volume.py --file` (repeatable, instead of the STAGE folder, still
supported): the same image as a stage holding those names (alphabetical
entries, fixed date). 280 blocks unless BLOCKS is given. `make run-iic`
(POM2 as a //c, `APPLE2_RUN_IIC_FLAGS ?= --slot 4=iicmouse`) is in
`dev/lib/mouse/mouse.mk` for every mouse game; it could join `run` in
`apple2.mk`.

A SYS image in one piece at `$2000` (a startup that relocates the game)
links with `$(PRODOS_SYS_CFG)` (`dev/cc65/prodos_sys.cfg`). Users:
CHROMABREAK, WARGALAGA II, ROBOT SPACE STATION.

## The SYS relocator (`sysreloc.inc`)

ca65 macros for that startup (65C02), on the zero page `$06/$07` (source),
`$08/$09` (destination), `$0A/$0B` (length), free under ProDOS then:

| Macro | Effect |
|---|---|
| `sysreloc_prologue` | `cld`, RAMRD/RAMWRT main, 80STORE off, `S = $FF` |
| `sysreloc_copy_bytes src, dst, n` | 1..255 bytes, X-indexed from the end (CHROMABREAK's duet player to page 3) |
| `sysreloc_copy_pages src, dst, pages` | whole pages forwards; `stz $08` when `dst`'s low byte is a constant 0 |
| `sysreloc_copy_pages_aux src, dst, pages` | the same into AUX (`sei`, RAMWRT aux … main); I stays set up to the game; the destination low byte is always loaded |
| `sysreloc_copy_down src, dst, len` | inline downward copy from the last byte: safe when `dst` overlaps above `src` (the game image to `$6000`) |
| `sysreloc_down_args src, dst, len` + `jsr name` / `sysreloc_down_sub name` | the same as a subroutine, for several downward copies (ROBOT SPACE STATION: the program, then its L8 part) |

```asm
.setcpu "65C02"
SYSRELOC_DOWN_FAST = 1          ; optional (below)
.include "sysreloc.inc"
.segment "CODE"
        sysreloc_prologue
        sysreloc_copy_pages boot, $1700, >bsize + 1
        sysreloc_copy_down payload, $6000, size
        jmp $6000
payload: .incbin "game.bin"
size = *-payload
```

```make
$(BUILD)/GAME.SYS: $(BUILD)/game.bin src/startup.s $(PRODOS_SYS_CFG) $(PRODOS_SYSRELOC_DEPS)
	$(CA65) --bin-include-dir $(BUILD) -I $(PRODOS) -o $(BUILD)/startup.o src/startup.s
	$(LD65) -C $(PRODOS_SYS_CFG) -o $@ $(BUILD)/startup.o
```

The default downward loop is the historic one (a 16-bit counter, 34
bytes, ~53 cycles a byte). `SYSRELOC_DOWN_FAST = 1` (ABI.md, "Speed/RAM
options") copies the `len & $FF` tail then whole pages with
`dey / lda (),y / sta (),y / cpy #0 / bne`: ~18 cycles a byte, 40 bytes
for the inline form instead of 60, every byte still moved in descending
address order (overlap stays safe); lengths below `$8000`, page count in X
and tail in Y for the subroutine. A 20 KB game boots ~0.7 s sooner. All
three users set it. Without the option, CHROMA.SYS and RSS.SYS are
byte-identical to their former hand-written startups (WG2.SYS: 2 bytes
less, the `stz $08`). `test_prodos_sysreloc.py` (`make test-tools`) runs
both variants, inline and subroutine, on overlapping, disjoint, tail-only
and page-only ranges against a memmove model, plus the forward copies.

## Whole files (`file.asm`, `file.s`)

`file.asm`, included at the end of an assembly program (`.ifref`: only what
is called is assembled, 65C02), wraps OPEN / READ / WRITE / SET_EOF / CLOSE on one
set of parameter lists. Set `pf_name` (Pascal string, relative to the
prefix or a full path), `pf_iobuf` (1 KB, page aligned, free in the
bitmap), `pf_buf`, `pf_len`; the calls return C = 1 and A = the MLI error
(also in `pf_err`), or C = 0 and A = `pf_err` = 0 on success. Y is
preserved. `pf_got` records bytes moved; it resets before OPEN and every
transfer, so a failed OPEN or a rejected range reports zero rather than
the previous operation's count. A failed transfer can report partial data.

| Routine | Effect |
|---|---|
| `prodos_open`, `prodos_read`, `prodos_write`, `prodos_close` | one MLI call each (`$4C` = end of file from READ) |
| `prodos_read_free` | READ with the destination pages freed in the system bitmap meanwhile (pages a crt0 claimed: HGR/DHGR page 2), the bitmap then put back even after a READ error |
| `prodos_load`, `prodos_load_free` | OPEN, READ, CLOSE after successful OPEN; READ error, otherwise CLOSE error |
| `prodos_save` | OPEN, or CREATE a BIN file (access `$C3`, seedling) then OPEN; WRITE; SET_EOF to bytes written; CLOSE; the first error |
| `prodos_load_aux` | OPEN; READ (`read_free`) `pf_len` bytes at a time into the page-aligned main window `pf_buf`, each chunk stored to aux from `pa_dst` (page aligned) with `aux_store` (`dev/lib/apple2/auxmem.asm`, included after `file.asm`); stops at a short chunk or end of file; CLOSE. `pa_max` = largest accepted file: a longer one stops with `$56` before that chunk is stored. `pf_got` = bytes moved to aux |

For a nonempty `read_free`, the entire range must fit below `$C000` without
16-bit wrap. An invalid range returns `$56` (bad buffer address), with no
READ or bitmap change. An exclusive end of `$C000` is valid; zero length
uses ordinary READ without changing the bitmap. Buffers must still avoid
the program, its scratch and ProDOS's own state. The helper only manages
allocation bits; it does not make overlapping memory safe.

A save replaces the complete file: a shorter write truncates the old tail,
and length zero produces an empty file. SET_EOF runs only after a successful
WRITE. CLOSE is attempted after every successful OPEN, including when
WRITE or SET_EOF fails. Saves are not atomic: a failure may leave partial
data in the file.

`prodos_load_aux` stores whole pages: aux bytes after the file's end, up to
the next page boundary, take the staging window's contents. Interrupts are
masked during each store (~3,600 cycles a page). The window's pages are
freed in the bitmap during each READ, like `prodos_read_free`. It costs
143 bytes plus 7 of parameters, with `read_free` and `aux_store` (35 B,
2+2 ZP bytes: alias `auxmem_src`/`auxmem_dst` to free scratch). WARGALAGA II
includes `file.asm` a second time inside `.scope wgaux` in its transient
BOOT segment for it (the records' copy lives in the SHOPM overlay).

C programs link `$(PRODOS_FILE_SRCS)` (`file.s`): `prodos_file_name`,
`prodos_file_iobuf`, `prodos_file_buffer`, `prodos_file_length`,
`prodos_file_actual`, `prodos_load()`, `prodos_load_free()`,
`prodos_save()` (prodos.h). Users: WARGALAGA II (`HIGHSCORES`, from its
title overlay), CHROMABREAK (`HIGHSCORES`, the `ENDING` overlay).
Make the C object's prerequisites include `$(PRODOS_FILE_DEPS)` so changes
to the included assembly rebuild `file.s` too.
`$(PRODOS_FILE_AUX_SRCS)` (`file_aux.s`, instead of `file.s`, deps
`$(PRODOS_FILE_AUX_DEPS)`) adds `prodos_load_aux(aux_dst, max)` (prodos.h,
21 B more); link `$(APPLE2C_AUX_SRCS)` with it for `aux_store`. User:
ROBOT SPACE STATION (its text bank, RSS.TEXT1/2 to aux `$6000`/`$8000`).

A record at an offset: `prodos_load_at` (`file.asm`, `.ifref`: OPEN,
SET_MARK to the 24-bit `pf_mark`, READ `pf_len` bytes at `pf_buf`, CLOSE;
SET_MARK's error, `$4D` past the end, else READ's, else CLOSE's; a short
READ is no error, compare `pf_got`). 24 bytes of code and 7 of parameter
list. C: `prodos_file_mark` (an `unsigned long`, low 24 bits) then
`prodos_load_at()`, from `$(PRODOS_FILE_AT_SRCS)` (`file_at.s`) or
`$(PRODOS_FILE_AUX_AT_SRCS)` (`file_aux_at.s`) instead of `file.s` /
`file_aux.s` (deps `$(PRODOS_FILE_AT_DEPS)` / `$(PRODOS_FILE_AUX_AT_DEPS)`),
so `file.s` alone stays byte-identical. User: ROBOT SPACE STATION
(`read_room`: mission m's record of RSS.ROOMS at m × 256).

All three C entrypoints cost 367 loaded bytes (formerly 314), including
the parameters and bitmap scratch; no zero-page bytes are allocated or
modified by the helpers. In isolation, assembly load/load_free/save cost
97/244/171 bytes (formerly 85/215/130). `test_prodos_file.py`, part of
`make test-tools`, executes the ASM and C binaries on a 65C02 with injected
MLI results: error priority, actual counts, bitmap guards, Y/ZP and each
independent `.ifref` route. A real ProDOS volume checks truncation to a
shorter/empty file, missing-file creation, GET_EOF and loaded contents;
a second one loads files into aux with `prodos_load_aux` (several chunks,
the `$56` limit, an exact multiple of the window, missing and empty files)
and reads them back with `aux_fetch_pages`, `aux_fetch_chunked` and
`AUXMOVE`.

Measured with the same injected MLI, successful load (256 B), load_free
(8192 B) and save (38 B) take 1232/3564/1611 cycles versus 1218/3536/1227
before these checks. These include the test stub, including the added
SET_EOF call; they exclude disk latency and are not real I/O timings.

Reference: [ProDOS technical reference, system programs](https://prodos8.com/docs/techref/writing-a-prodos-system-program/).
