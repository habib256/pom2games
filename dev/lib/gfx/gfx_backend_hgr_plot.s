; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Identical cc65 signatures: resolve the GFX entry directly to HGR.
.import _hgr_plot
.export _gfx_plot := _hgr_plot
