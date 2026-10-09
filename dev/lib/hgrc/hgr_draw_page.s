; VERHILLE Arnaud — GPL-3.0. Query state without linking page-table management.
.export _hgr_get_draw_page
.import _hgr_draw_page2
.code
_hgr_get_draw_page:
        lda _hgr_draw_page2
        beq page1
        lda #2
        ldx #0
        rts
page1:
        lda #1
        ldx #0
        rts
