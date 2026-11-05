; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Append the selected monochrome pen to the unchanged GFX argument frame.
.export _gfx_hline
.import _dhgr_hline, _gfx_dhgr_mono_pen, pusha
.code
_gfx_hline:
        jsr pusha
        lda _gfx_dhgr_mono_pen
        jmp _dhgr_hline
