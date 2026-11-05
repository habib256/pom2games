; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Every nonzero color maps to DHGR white, independently from the drawing pen.
.export _gfx_clear
.import _dhgr_clear
.code
_gfx_clear:
        cmp #0
        beq clear
        lda #15
clear:
        jmp _dhgr_clear
