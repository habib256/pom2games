; MBT.SYSTEM: the ProDOS shim (dev/lib/prodos/sysboot.s) that loads MBT.SYS.
.define SYSBOOT_FILE  "MBT.SYS"
.define SYSBOOT_TITLE "MB TRACKER"
SYSBOOT_NEED_128K = 1                     ; MACHID check: 64 KB machines refused
.include "sysboot.s"
