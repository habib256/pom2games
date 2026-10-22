; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_circle.s — hgr_circle is gfx_circle (same signature): an alias, no
; forwarding code. Its own archive member, like the C file it replaces.
.import _gfx_circle
.export _hgr_circle := _gfx_circle
