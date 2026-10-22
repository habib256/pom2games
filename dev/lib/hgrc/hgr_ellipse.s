; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_ellipse.s — hgr_ellipse is gfx_ellipse (same signature): an alias, no
; forwarding code. Its own archive member, like the C file it replaces.
.import _gfx_ellipse
.export _hgr_ellipse := _gfx_ellipse
