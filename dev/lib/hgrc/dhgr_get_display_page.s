; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_get_display_page
.import _dhgr_display
.code
_dhgr_get_display_page:
        ldx #0
        lda _dhgr_display
        rts
