; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_get_draw_page
.import _dhgr_base
.code
; Preserve Y: dhgr_flip keeps the previous display page there.
_dhgr_get_draw_page:
        lda _dhgr_base
        cmp #$20
        bne @two
        ldx #0
        lda #1
        rts
@two:   lda #2
        ldx #0
        rts
