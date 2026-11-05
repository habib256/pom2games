; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_set_color
.import _dhgr_dot_color
.code
_dhgr_set_color:
        and #15
        sta _dhgr_dot_color
        rts
