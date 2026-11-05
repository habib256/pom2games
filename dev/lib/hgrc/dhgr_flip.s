; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_flip
.import _dhgr_display, _dhgr_get_draw_page, _dhgr_show_page, _dhgr_draw_page
.code
_dhgr_flip:
        ; Both callees preserve Y; retain the old display without a stack slot.
        ldy _dhgr_display
        jsr _dhgr_get_draw_page
        jsr _dhgr_show_page
        tya
        jmp _dhgr_draw_page
