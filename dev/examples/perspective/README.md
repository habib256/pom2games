# Perspective grid and PWM sample

```sh
make -C dev/examples/perspective
make -C dev/examples/perspective run
make -C dev/examples/perspective test
```

The DOS 3.3 disk is `build/PERSPECTIVE.dsk`; it runs on the Apple II+ 48 KB
profile and on the IIe. A grid illustrates the full projection across 280
pixels. Space plays a 40 ms synthetic effect; ESC returns to DOS. The sound
masks IRQs and suspends the program while it plays.

The camera and the WAV are generated in `build/`. No external audio file is
required. Change the parameters of the `camera.h` rule to adjust the
perspective; replace the WAV to try another effect. The
[perspective](../../lib/perspective/README.md) and
[audio](../../lib/audio/README.md) libraries remain independent and optional.
