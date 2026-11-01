; CHROMA.SYSTEM: the ProDOS shim (dev/lib/prodos/sysboot.s) that loads CHROMA.SYS.
.define SYSBOOT_FILE  "CHROMA.SYS"
.define SYSBOOT_TITLE "CHROMABREAK"
SYSBOOT_NEED_128K = 1                     ; MACHID check: 64 KB machines refused
.include "sysboot.s"
