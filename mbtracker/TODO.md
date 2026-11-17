# MB TRACKER — work plan

Target: Apple //e enhanced and //c with 128 KB, ProDOS 8, 80 columns, Mockingboard
(4c on the //c). Format: AYS v1 ([AYSONG_FORMAT.md](../dev/lib/apple2/AYSONG_FORMAT.md)),
the one the games embed; `dev/tools/audio/aysong.py` is the tests' oracle
(encoder and `Player`, down to the register).

Finished lots are in [CHANGELOG.md](CHANGELOG.md).

## Next

- [ ] Mouse on the //c **with** a 4c: read the IOU's mouse hardware
  (`$C015`/`$C017`, `$C066`/`$C067`, button) without the masked firmware.
- [ ] No mouse wheel: scroll the order list from its edges.
- [ ] AYS: per-tick pitch offset in instruments, channel volume (would
  recover most of the PT3 import's losses).
- [ ] Adjustable step after entry; transposing a whole track.
- [ ] Test on real machines: //e enhanced + Mockingboard + AppleMouse,
  //c + 4c (sound, interrupts during disk accesses, `/RAM` given back on
  exit, ALTZP for the copies to the auxiliary LC).
