; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR access.
.include "apple2.inc"
RAMWRTON = $C005
.code
.export _dhgr_read_asm
.import dhgr_select, dhgr_read_byte
_dhgr_read_asm:
        php
        sei
        jsr dhgr_select
        jsr dhgr_read_byte
        ldx #0
        plp
        rts
