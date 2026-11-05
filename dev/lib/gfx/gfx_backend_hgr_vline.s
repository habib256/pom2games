; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Identical cc65 signatures: resolve the GFX entry directly to HGR.
.import _hgr_vline
.export _gfx_vline := _hgr_vline
