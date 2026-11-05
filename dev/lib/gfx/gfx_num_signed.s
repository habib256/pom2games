; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Signed decimal wrapper, separate so unsigned-only clients do not link it.
.export _gfx_itoa
.import _gfx_utoa, _hgr_utoa, gfx_num_buffer
.importzp _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
.code
; unsigned char gfx_itoa(char *buf, int value): '-' then the magnitude.
_gfx_itoa:
        cpx #$80
        bcc positive
        eor #$FF                ; 0 - value (-32768 stays 32768)
        adc #0                  ; CPX left C=1; complement plus one
        sta _hgr_u_lo
        txa
        eor #$FF
        adc #0                  ; propagate the low-byte carry
        sta _hgr_u_hi
        jsr gfx_num_buffer
        lda #'-'
        ldy #0
        sta (_hgr_u_ptr),y
        inc _hgr_u_ptr
        bne :+
        inc _hgr_u_ptr+1
:       jsr _hgr_utoa
        iny                     ; the sign counts
        tya
        ldx #0
        rts

positive:
        jmp _gfx_utoa
