; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Identical cc65 signatures: resolve the GFX entry directly to HGR.
.import _hgr_hline
.export _gfx_hline := _hgr_hline
