; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_num_dec.s — unsigned/signed decimal -> ASCII (gfx_utoa, gfx_itoa).
; See gfx.h. cc65 wrappers around hgr_utoa (lib/math u16_to_dec): repeated
; subtraction of powers of ten, no cc65 udiv16 runtime. A HEX-only program
; (gfx_hexstr) links neither this member nor the conversion.
.export _gfx_utoa, _gfx_itoa
.import _hgr_utoa, popax
.importzp _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr

.code
; unsigned char gfx_itoa(char *buf, int value): '-' then the magnitude.
_gfx_itoa:
        cpx #$80
        bcc _gfx_utoa
        eor #$FF                ; 0 - value (-32768 stays 32768)
        sta _hgr_u_lo
        txa
        eor #$FF
        sta _hgr_u_hi
        inc _hgr_u_lo
        bne :+
        inc _hgr_u_hi
:       jsr buffer
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

; unsigned char gfx_utoa(char *buf, unsigned value): digit count.
_gfx_utoa:
        sta _hgr_u_lo
        stx _hgr_u_hi
        jsr buffer
        jsr _hgr_utoa
        tya
        ldx #0
        rts

buffer: jsr popax
        sta _hgr_u_ptr
        stx _hgr_u_ptr+1
        rts
