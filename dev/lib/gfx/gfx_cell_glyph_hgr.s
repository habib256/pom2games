; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.export _gfx_cell_glyph
.import _hgr_puts8
.importzp sp
.code
; fastcall A=row; caller stack: column, character. Reserve three bytes;
; frame becomes y, x low/high, character, NUL. The old arguments are reused.
_gfx_cell_glyph:
        asl a
        asl a
        asl a                   ; byte y = row * 8, including wrap
        tax
        lda sp
        sec
        sbc #3
        sta sp
        bcs :+
        dec sp+1
:       ldy #0
        txa
        sta (sp),y
        ldy #3
        lda (sp),y
        tax
        asl a
        asl a
        asl a
        ldy #1
        sta (sp),y
        txa
        lsr a
        lsr a
        lsr a
        lsr a
        lsr a                   ; full 16-bit x = column * 8
        iny
        sta (sp),y
        ldy #4
        lda (sp),y
        dey
        sta (sp),y
        iny
        lda #0
        sta (sp),y
        clc
        lda sp
        adc #3
        ldx sp+1
        bcc :+
        inx
:       jsr _hgr_puts8
        ; The text entry consumed y/x; release the two-byte local string.
        lda sp
        clc
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       rts
