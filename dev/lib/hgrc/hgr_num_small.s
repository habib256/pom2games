; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_putu8(x, y, value), cc65 fastcall: A/X=value, C stack=y,x low/high.
.export _hgr_putu8
.import hgr_num_prepare, _hgr_puts8, incsp6
.code
_hgr_putu8:
        jsr hgr_num_prepare
        jsr _hgr_puts8
        jmp incsp6              ; puts8 consumed the relocated coordinates
