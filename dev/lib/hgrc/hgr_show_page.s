; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Display current draw page. Every nonzero flag means page 2.
.export _hgr_show_page
.import _hgr_draw_page2, _hgr_ss_sink
.code
_hgr_show_page:
        ldx #0
        lda _hgr_draw_page2
        beq selected
        inx
selected:
        lda $C054,x
        sta _hgr_ss_sink
        rts
