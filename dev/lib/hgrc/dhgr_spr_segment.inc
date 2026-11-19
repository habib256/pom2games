; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; An overlay build keeps the compositor instructions and their lookup tables
; together so one load restores both. State stays in the caller's BSS/ZP.
.ifndef DHGR_SPR_CODE_SEGMENT
DHGR_SPR_CODE_SEGMENT = 0
.endif
.macro dhgr_spr_segment resident_segment
        .if DHGR_SPR_CODE_SEGMENT
        .segment "DHGRSPRCODE"
        .else
        .segment resident_segment
        .endif
.endmacro
