; VERHILLE Arnaud — GPL-3.0. file.s plus prodos_load_aux() for cc65 C
; programs (prodos.h): link it INSTEAD of file.s (PRODOS_FILE_AUX_SRCS),
; with dev/lib/apple2c/apple2aux.s for aux_store (APPLE2C_AUX_SRCS).
PRODOS_FILE_AUX = 1
.include "file.s"
