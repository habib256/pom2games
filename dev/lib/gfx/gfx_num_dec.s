; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; gfx_num_dec.s — unsigned decimal -> ASCII (gfx_utoa).
; See gfx.h. cc65 wrapper around hgr_utoa (lib/math u16_to_dec): repeated
; subtraction of powers of ten, no cc65 udiv16 runtime. A HEX-only program
; (gfx_hexstr) links neither this member nor the conversion.
.export _gfx_utoa, gfx_num_buffer
.import _hgr_utoa, popax
.importzp _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr

.code
; unsigned char gfx_utoa(char *buf, unsigned value): digit count.
_gfx_utoa:
        sta _hgr_u_lo
        stx _hgr_u_hi
        jsr gfx_num_buffer
        jsr _hgr_utoa
        tya
        ldx #0
        rts

gfx_num_buffer: jsr popax
        sta _hgr_u_ptr
        stx _hgr_u_ptr+1
        rts
