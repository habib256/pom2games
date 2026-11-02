; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Same fastcall signature: alias the shared rectangle implementation without
; copying the C-stack arguments through a forwarding wrapper.
.import _gfx_rect
.export _hgr_rect := _gfx_rect
