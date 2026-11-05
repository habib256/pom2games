; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_read_block
.import dhgr_transfer
.code
_dhgr_read_block:
        ldx #$80
        jmp dhgr_transfer
