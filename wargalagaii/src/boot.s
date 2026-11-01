; WG2.SYSTEM: the ProDOS shim (dev/lib/prodos/sysboot.s) that loads WG2.SYS.
.define SYSBOOT_FILE  "WG2.SYS"
.define SYSBOOT_TITLE "WARGALAGA II"
SYSBOOT_NEED_128K = 1                     ; MACHID check: 64 KB machines refused
.include "sysboot.s"
