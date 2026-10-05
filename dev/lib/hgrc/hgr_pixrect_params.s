; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_pixrect_params.s — Apple II HGR kernel; linked independently from hgrc.lib.
.exportzp _hgr_r_x, _hgr_r_xr, _hgr_r_y0, _hgr_r_rows, _hgr_r_mode

.segment "ZEROPAGE"
_hgr_r_x:     .res 2        ; left pixel x (0..279)
_hgr_r_xr:    .res 2        ; right pixel x (0..279, clipped)
_hgr_r_y0:    .res 1        ; top scanline
_hgr_r_rows:  .res 1        ; number of scanlines (>= 1)
_hgr_r_mode:  .res 1        ; 1 = fill (white), 0 = clear (black)
