; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_puti(x,y,value), cc65 fastcall: A/X=signed value, C stack=y,xlo,xhi.
; Seven-byte local buffer, including sign and NUL. Relocate the coordinates
; to the new top so the text call consumes them without a second copy.
.export _hgr_puti
.import decsp7, incsp7, _hgr_utoa, _hgr_puts
.importzp sp, _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr, _hgr_t_s
.code
_hgr_puti:
        sta _hgr_u_lo
        stx _hgr_u_hi
        jsr decsp7
        .repeat 3, I
        ldy #7+I
        lda (sp),y
        ldy #I
        sta (sp),y
        .endrepeat
        clc
        lda sp
        adc #3
        sta _hgr_u_ptr
        sta _hgr_t_s             ; retain the buffer start if digits follow '-'
        lda sp+1
        adc #0
        sta _hgr_u_ptr+1
        sta _hgr_t_s+1
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
        jsr _hgr_puts
        jmp incsp7              ; text already consumed the three coordinates
