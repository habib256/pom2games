; Keep catalog code/parameter lists in the file overlay, buffers in low RAM.
PRODOS_DIR_CUSTOM_SEGMENTS = 1
.define PRODOS_DIR_CODE_SEGMENT "OVL2"
.define PRODOS_DIR_DATA_SEGMENT "OVL2"
.define PRODOS_DIR_BSS_SEGMENT "LOWBSS"
.include "dir_list.s"
