# Building a ProDOS disk

    python3 build_volume.py stage dist/GAME.po --volume GAME --boot boot.bin --blocks 280
    python3 read_volume.py dist/GAME.po

Raw image in ProDOS block order, 280 blocks of 512 bytes for a 5.25-inch
floppy. Fixed dates and deterministic allocation. The reader lets you check
the generated contents without mounting the disk.

In `stage`, use for example `PRODOS#FF0000` and
`CHROMA.SYSTEM#FF2000` and `CHROMA.SYS#FF2000`: the `#TTAAAA` suffix gives the
type and the auxiliary address. The suffix is stripped on the volume.
`CHROMA.SYSTEM` is the SYS-type (`$FF`) loader launched automatically by
ProDOS; it then loads the game `CHROMA.SYS`.

`PRODOS` is ProDOS 8 **2.4.3**, redistributed as an Apple system, and
`boot.bin` holds its two boot blocks. Both files come from the local ProDOS
resources used by A2 File Cmd; the system is identical to the one on the
official ProDOS 2.4.3 disk. They keep their Apple rights and their authors'
credits, separate from the licence of the repository's code.
[ProDOS 2.4.3 and its credits](https://prodos8.com/releases/prodos-243/).

Both scripts are adapted from the GPL-3.0 tools of A2 File Cmd, by VERHILLE
Arnaud (`tools/mkvolume.py` and `tools/prodos_read.py`). No dependency on that
project is needed to build a game.
