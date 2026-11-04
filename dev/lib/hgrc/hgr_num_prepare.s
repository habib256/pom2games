; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared unsigned decimal preparation. Input: A/X=value, C stack=y,xlo,xhi.
; Allocate six bytes, move coordinates to the new top, then format into the
; remaining six bytes (including the old argument slots). No global buffer.
; Output: A/X=buffer, C stack=y,xlo,xhi,buffer[6]. The text call consumes
; three bytes; the public number entry subsequently releases the buffer.
.export hgr_num_prepare
.import _hgr_utoa
.importzp sp, _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
.code
hgr_num_prepare:
        sta _hgr_u_lo
        stx _hgr_u_hi
        ; Value bytes are saved; A need not survive the reservation.
        lda sp
        sec
        sbc #6
        sta sp
        bcs allocated
        dec sp+1
allocated:
        .repeat 3, I
        ldy #6+I
        lda (sp),y
        ldy #I
        sta (sp),y
        .endrepeat
        clc
        lda sp
        adc #3
        sta _hgr_u_ptr
        lda sp+1
        adc #0
        sta _hgr_u_ptr+1
        jsr _hgr_utoa
        lda _hgr_u_ptr
        ldx _hgr_u_ptr+1
        rts
