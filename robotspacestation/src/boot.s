; RSS.SYSTEM: the ProDOS shim (dev/lib/prodos/sysboot.s) that loads RSS.SYS.
.define SYSBOOT_FILE  "RSS.SYS"
.define SYSBOOT_TITLE "ROBOT SPACE STATION"
SYSBOOT_NEED_128K = 1                     ; MACHID check: 64 KB machines refused
.include "sysboot.s"
