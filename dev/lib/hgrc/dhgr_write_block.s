; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_write_block
.import dhgr_transfer
.code
_dhgr_write_block:
        ldx #0
        jmp dhgr_transfer
