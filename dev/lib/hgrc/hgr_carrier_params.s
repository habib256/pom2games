; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_carrier_params.s — Apple II HGR kernel; linked independently from hgrc.lib.
.exportzp _hgr_z_ce, _hgr_z_co, _hgr_z_hi

.segment "ZEROPAGE"
_hgr_z_ce:    .res 1        ; carrier mask for EVEN byte columns
_hgr_z_co:    .res 1        ; carrier mask for ODD  byte columns
_hgr_z_hi:    .res 1        ; high bit to OR in ($00 green/violet, $80 orange/blue)
