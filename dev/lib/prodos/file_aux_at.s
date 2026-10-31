; VERHILLE Arnaud — GPL-3.0. file_aux.s (prodos_load_aux) plus
; prodos_load_at() (prodos.h): link it INSTEAD of file_aux.s
; (PRODOS_FILE_AUX_AT_SRCS), with $(APPLE2C_AUX_SRCS) for aux_store.
PRODOS_FILE_AT = 1
.include "file_aux.s"
