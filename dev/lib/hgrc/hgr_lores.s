; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; LORES shares the text-page layout: two vertical colour cells per byte.
; Build its 24 row addresses lazily; hgr_set_draw_page shifts their high
; bytes when changing pages. State remains in hgr_init.c, shared with HIRES.
; Internal build ABI: clobbers A/X/Y/tmp1 only (used by hgr_lores_draw).
.export _hgr_lores_build
.import _hgr_lo_base, _hgr_lo_ready, _hgr_lo_rowlo, _hgr_lo_rowhi
.importzp tmp1

.code
_hgr_lores_build:
        lda _hgr_lo_ready
        bne done
        lda _hgr_lo_base
        bne base_ready
        lda #4
        sta _hgr_lo_base
base_ready:
        ldx #0                  ; row index, 0..23
        lda #0
        sta tmp1                ; third offset: $00, $28, $50
third:
        ldy _hgr_lo_base         ; current high address, base..base+3
pair:
        lda tmp1
        sta _hgr_lo_rowlo,x
        tya
        sta _hgr_lo_rowhi,x
        inx
        lda tmp1
        ora #$80
        sta _hgr_lo_rowlo,x
        tya
        sta _hgr_lo_rowhi,x
        iny
        inx
        txa
        and #7
        bne pair
        lda tmp1
        clc
        adc #40
        sta tmp1
        cmp #120
        bne third
        lda #1
        sta _hgr_lo_ready
done:   rts
