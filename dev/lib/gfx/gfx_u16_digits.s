; VERHILLE Arnaud — GPL-3.0. Optional 65C02-only numeric kernel.
; Unsigned 16-bit to five ASCII digits, using bounded 65C02 decimal doubling.
; CMOS IRQ entry clears decimal mode; RTI restores it. Preserve caller flags.
.setcpu "65C02"
.export _gfx_u16_digits
.bss
value_lo: .res 1
value_hi: .res 1
packed_bcd: .res 3
number_buffer: .res 6
.code
_gfx_u16_digits:
        sta value_lo
        stx value_hi
        php
        sed
        stz packed_bcd
        stz packed_bcd+1
        stz packed_bcd+2
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
        lda packed_bcd+2
        adc packed_bcd+2
        sta packed_bcd+2
        dex
        bne bit_loop
        cld
        lda packed_bcd+2
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
