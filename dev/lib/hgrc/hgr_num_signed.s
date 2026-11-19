; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_puti(x,y,value), cc65 fastcall: A/X=signed value, C stack=y,xlo,xhi.
; Seven-byte local buffer, including sign and NUL. Relocate the coordinates
; to the new top so the text call consumes them without a second copy.
.include "hgr_num_frame.inc"
.export _hgr_puti
.import addysp, _hgr_utoa, _hgr_puts
.importzp sp, _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr, _hgr_t_s
.code
_hgr_puti:
        hgr_decimal_frame 7, _hgr_t_s
        lda _hgr_u_hi
        bpl convert
        ldy #0
        lda #'-'
        sta (_hgr_u_ptr),y
        inc _hgr_u_ptr
        bne magnitude
        inc _hgr_u_ptr+1
magnitude:
        ; Unsigned two's-complement negation includes -32768 -> 32768.
        lda #0
        sec
        sbc _hgr_u_lo
        sta _hgr_u_lo
        lda #0
        sbc _hgr_u_hi
        sta _hgr_u_hi
convert:
        jsr _hgr_utoa            ; preserves the existing text-source pointer
        lda _hgr_t_s
        ldx _hgr_t_s+1
        hgr_draw_number _hgr_puts, 7
