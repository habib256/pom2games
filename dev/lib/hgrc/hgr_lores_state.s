; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Independent LORES state: plain LORES clients need no HGR tables or page manager.
; BSS is reset on DOS CALL re-entry. Base 0 defaults lazily to $04 (page 1).
; The page manager shifts rowhi only after hgr_lores_build sets ready.
.export _hgr_lo_rowlo, _hgr_lo_rowhi, _hgr_lo_base, _hgr_lo_ready
.bss
_hgr_lo_rowlo: .res 24
_hgr_lo_rowhi: .res 24
_hgr_lo_base:  .res 1
_hgr_lo_ready: .res 1
