; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_putu(x, y, value), cc65 fastcall: A/X=value, C stack=y,x low/high.
.export _hgr_putu
.import hgr_num_prepare, _hgr_puts, addysp
.code
_hgr_putu:
        jsr hgr_num_prepare
        jsr _hgr_puts
        ldy #6
        jmp addysp              ; puts consumed the relocated coordinates
