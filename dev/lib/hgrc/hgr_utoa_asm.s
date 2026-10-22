; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_utoa_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
; hgr_utoa: _hgr_u_lo/_hi -> ASCII at (_hgr_u_ptr), no leading zeros, NUL;
; Y = digit count. The conversion is lib/math dec.asm (u16_to_dec), also
; behind gfx_utoa/gfx_itoa (gfx_num_dec.s).
.export _hgr_utoa
.exportzp _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
.importzp tmp1, tmp2

.segment "ZEROPAGE"
_hgr_u_lo:    .res 1        ; value low byte  (consumed by the subtraction)
_hgr_u_hi:    .res 1        ; value high byte
_hgr_u_ptr:   .res 2        ; output buffer pointer
dec_lo  = _hgr_u_lo
dec_hi  = _hgr_u_hi
dec_ptr = _hgr_u_ptr
dec_t   = tmp1
dec_d   = tmp2

.segment "CODE"
_hgr_utoa := u16_to_dec

.include "../math/dec.asm"
