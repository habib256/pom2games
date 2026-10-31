; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; MBT.SYS entry at $2000 (sysboot.s jumps there): on to crt0. RODATA comes
; next (src/mbt.cfg): at the exit, prodos_video_release() rebuilds /RAM
; with $2000-$21FF as its buffer, so no code the exit runs may live there.
.import __STARTUP_LOAD__, __RODATA_SIZE__
.segment "ENTRY"
        jmp __STARTUP_LOAD__
.assert __RODATA_SIZE__ >= 512 - 3, ldwarning, "code within /RAM's FORMAT buffer ($2000-$21FF)"
