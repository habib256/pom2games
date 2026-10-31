; VERHILLE Arnaud — GPL-3.0. file.s plus prodos_load_at() (a record at an
; offset, prodos.h) for cc65 C programs: link it INSTEAD of file.s
; (PRODOS_FILE_AT_SRCS). file.s alone stays byte-identical without it.
PRODOS_FILE_AT = 1
.include "file.s"
