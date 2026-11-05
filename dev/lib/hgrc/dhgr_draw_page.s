; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_draw_page
.import _dhgr_base
.code
_dhgr_draw_page:
        cmp #1
        beq @one
        cmp #2
        bne @done
        lda #$40
        bne @store
@one:   lda #$20
@store: sta _dhgr_base
@done:  rts
