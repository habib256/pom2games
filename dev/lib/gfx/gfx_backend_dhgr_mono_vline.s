; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Append the selected monochrome pen to the unchanged GFX argument frame.
.export _gfx_vline
.import _dhgr_vline, _gfx_dhgr_mono_pen, pusha
.code
_gfx_vline:
        jsr pusha
        lda _gfx_dhgr_mono_pen
        jmp _dhgr_vline
