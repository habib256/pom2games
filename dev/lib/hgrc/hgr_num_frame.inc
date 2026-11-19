; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Reserve bytes on the cc65 stack. Clobbers A and flags, preserves X/Y.
.macro hgr_reserve_stack count
        .local allocated
        lda sp
        sec
        sbc #count
        sta sp
        bcs allocated
        dec sp+1
allocated:
.endmacro

; Relocate the three stacked coordinate bytes (y, x low/high).
.macro hgr_move_coords source, dest
        .repeat 3, I
        ldy #source+I
        lda (sp),y
        ldy #dest+I
        sta (sp),y
        .endrepeat
.endmacro

; Save the fastcall value, move y/x ahead of the local decimal buffer and
; point u_ptr at its first byte. Signed output also keeps the start for '-'.
.macro hgr_decimal_frame size, buffer_start
        sta _hgr_u_lo
        stx _hgr_u_hi
        hgr_reserve_stack size
        hgr_move_coords size, 0
        clc
        lda sp
        adc #3
        sta _hgr_u_ptr
        .ifnblank buffer_start
        sta buffer_start
        .endif
        lda sp+1
        adc #0
        sta _hgr_u_ptr+1
        .ifnblank buffer_start
        sta buffer_start+1
        .endif
.endmacro

; A/X points at the string. The renderer consumes y/x, then release
; the bytes remaining in the number entry's stack frame.
.macro hgr_draw_number renderer, remaining
        jsr renderer
        ldy #remaining
        jmp addysp
.endmacro
