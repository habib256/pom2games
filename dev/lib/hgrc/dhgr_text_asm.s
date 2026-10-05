; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _dhgr_glyph_row_asm
.import _dhgr_text_phase, _dhgr_text_row
.importzp tmp1, tmp2, tmp3, tmp4
.segment "CODE"
; Expand 8 glyph bits into 32 white/black bits, prefixed by 0..6 bits.
_dhgr_glyph_row_asm:
        sta tmp1
        lda #0
        ldx #5
@zero:  sta _dhgr_text_row,x
        dex
        bpl @zero
        lda #1
        ldx _dhgr_text_phase
        beq @phase_done
@phase: asl
        dex
        bne @phase
@phase_done:
        tay
        ldx #0
        lda #8
        sta tmp2
@pixel: lsr tmp1
        lda #0
        bcc @off
        lda #$FF
@off:   sta tmp4
        lda #4
        sta tmp3
@bit:   lda tmp4
        beq @advance
        tya
        ora _dhgr_text_row,x
        sta _dhgr_text_row,x
@advance:
        tya
        asl
        tay
        cpy #$80
        bne @same
        ldy #1
        inx
@same:  dec tmp3
        bne @bit
        dec tmp2
        bne @pixel
        rts
