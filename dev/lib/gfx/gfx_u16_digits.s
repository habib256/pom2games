; VERHILLE Arnaud — GPL-3.0. Optional 65C02-only numeric kernel.
; Unsigned 16-bit to five ASCII digits, using bounded 65C02 decimal doubling.
; CMOS IRQ entry clears decimal mode; RTI restores it. Preserve caller flags.
.setcpu "65C02"
.export _gfx_u16_digits
.importzp ptr1, ptr2, tmp1
; No calls while converting: the input and packed digits may use cc65 scratch.
; Only the returned ASCII buffer has to survive the return.
value_lo = ptr1
value_hi = ptr1+1
packed_bcd = ptr2                 ; the low two packed bytes are contiguous
packed_high = tmp1
.bss
number_buffer: .res 6
.code
_gfx_u16_digits:
        sta value_lo
        stx value_hi
        php
        sed
        stz packed_bcd
        stz packed_bcd+1
        stz packed_high
        ldx #16
bit_loop:
        asl value_lo
        rol value_hi
        lda packed_bcd
        adc packed_bcd
        sta packed_bcd
        lda packed_bcd+1
        adc packed_bcd+1
        sta packed_bcd+1
        lda packed_high
        adc packed_high
        sta packed_high
        dex
        bne bit_loop
        cld
        lda packed_high
        ora #'0'
        sta number_buffer
        ldx #1
        ldy #1
unpack:
        lda packed_bcd,y
        lsr
        lsr
        lsr
        lsr
        ora #'0'
        sta number_buffer,x
        inx
        lda packed_bcd,y
        and #15
        ora #'0'
        sta number_buffer,x
        inx
        dey
        bpl unpack
        stz number_buffer+5
        plp
        lda #<number_buffer
        ldx #>number_buffer
        rts
