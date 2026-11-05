; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_set_color
.import _gfx_dhgr_mono_pen
.code
_dhgr_set_color:
        cmp #0
        beq store
        lda #1
store:
        sta _gfx_dhgr_mono_pen
        rts
