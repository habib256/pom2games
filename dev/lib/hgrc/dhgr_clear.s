; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_clear
.import _dhgr_prepare_pattern, _dhgr_clear_asm
.code
; fastcall color in A; no argument or local software-stack slots.
_dhgr_clear:
        jsr _dhgr_prepare_pattern
        jmp _dhgr_clear_asm
