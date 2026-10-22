# Audio samples on the Apple II speaker

Optional 6502/cc65 module: `a2_sample_play(sample)` plays a PWM clip on
the native speaker. No extra audio hardware is needed.
The player is derived from Colin Leroy-Mira's generator used by
[Shufflepuck](https://github.com/colinleroy/a2tools/tree/main/src/shufflepuck).
Attribution, revision and adaptations: [NOTICE.txt](../../tools/audio/NOTICE.txt).
Licence of the player and the generator: GPL-3.0-or-later.

```make
include $(DEV)/cc65/apple2.mk
include $(AUDIO)/audio.mk
# Add $(AUDIO_SRCS) to the sources and $(AUDIO_INCS) to the C flags.
```

The common ld65 configurations declare the optional `AUDIOCODE` segment,
aligned on 256 bytes. Without the module, this segment uses no memory.
Any other configuration must declare this segment in writable main RAM,
with `align=$100`. The player allocates no BSS and no new zero page;
it borrows cc65's `ptr1`, `ptr3`, the first byte of `ptr4` and `tmp3`.
Its code costs 1,950 bytes plus alignment: the C configurations
place it right after `STARTUP` (fixed crt0 size), i.e. a constant 93 bytes of
padding instead of 0 to 255 behind a `CODE` of arbitrary
length; `apple2_hgr.cfg` (asm) keeps it after `CODE`.

## Converting and playing

```sh
python3 dev/tools/audio/pack_wav.py effet.wav --out build/effet --name effet
```

Assemble `build/effet.s`, include `build/effet.h`, then:

```c
#include "audio.h"
#include "effet.h"
a2_sample_play(effet);
```

The converter accepts 8/16/24/32-bit PCM WAV files, mixes the channels down,
resamples to a nominal 8 kHz and quantises to 48 levels. Decimation
uses a per-interval average; interpolation when upsampling is linear.
A 2 ms fade softens the ends (`--fade-ms 0` disables it).
Each sample costs one byte; the `$92` terminator adds one byte. The only
valid codes are the even bytes `$32..$90`, followed by `$92`.
An empty clip contains only the terminator and does not touch the speaker.

Playback **blocks the CPU and masks IRQs for the whole clip**; it
then restores the entry mask. The //c's native mouse, an IRQ clock
or serial reception can therefore lose events during playback.
Prefer short effects and jingles outside animation. This player does
not provide mixing or background playback.

Requires D=0, main RAM/ZP and the CPU at its nominal 1 MHz speed.
The module neither detects nor configures accelerators or the IIgs.
No video switch, memory bank or IRQ vector is changed.
A null pointer is accepted; other buffers must be immutable,
terminated and must not cross `$FFFF`. There is no validation of the target stream.

Two PWM periods of 63 cycles give **126 cycles per sample**.
"8 kHz" is the nominal conversion rate; the effective rate
is CPU clock / 126 (about 8.1 kHz on an Apple II). Long clips quickly
fill RAM: one converted second costs about 8 KB.

## Checking and regenerating

```sh
python3 dev/tools/audio/generate_player.py --check
python3 dev/tests/test_audio.py
python3 dev/tests/test_audio.py --iie
make -C dev/examples/perspective run
```

The assemblable player is shipped: a host C compiler is only needed to
regenerate it. The tests exercise the 48 levels, transitions in both
directions, several page crossings, the IRQ masks and the cc65 API.
On a2run, the pulse log is timestamped at the start of instructions;
on POM2/65C02, code visits check the sampling intervals.
Validation is emulated; no test on physical hardware is claimed.
