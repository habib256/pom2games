; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR primitive.
.include "apple2.inc"
RAMWRTON = $C005
.code
.export _dhgr_span_asm, _dhgr_span_x, _dhgr_span_end
.import _dhgr_base, _dhgr_pattern, dhgr_rowlo, dhgr_rowhi
.import _dhgr_cellbyte, _dhgr_cellphase
.import _dhgr_first, _dhgr_last, _dhgr_first_mask, _dhgr_last_mask
.importzp ptr1, tmp1, tmp2, tmp3, tmp4, aux_read
.bss
_dhgr_span_x: .res 2            ; first bit, 0..559
_dhgr_span_end: .res 2          ; last bit, x..559
row: .res 1
rows: .res 1
edges: .res 1                   ; partial edge bytes, 0..2
edge_col: .res 2
edge_main: .res 2
edge_keep: .res 2
edge_bits: .res 2
aux_c0: .res 1                  ; interior page columns, $FF when empty
aux_c1: .res 1
main_c0: .res 1
main_c1: .res 1
.rodata
; Bit 0..9 (cell phase + x&3; 7..9 lie in the next byte) -> the bits from
; there to the end of its byte, and from its byte start up to there.
from_bit:
.repeat 10,T
.byte ($7F<<(T .mod 7))&$7F
.endrepeat
to_bit:
.repeat 10,T
.byte (2<<(T .mod 7))-1
.endrepeat
.code
; Bit x in A/X -> interleaved byte in A, Y = bit 0..9 (see from_bit).
split:  sta tmp1
        and #3
        sta tmp2
        txa
        lsr
        ror tmp1
        lsr
        ror tmp1
        ldx tmp1
        lda _dhgr_cellphase,x
        clc
        adc tmp2
        tay
        cpy #7
        lda _dhgr_cellbyte,x
        adc #0
        rts

; void __fastcall__ dhgr_span_asm(unsigned rows_y): Y = low byte, row count
; (>=1, clipped) = high byte; bits dhgr_span_x..dhgr_span_end in dhgr_pattern.
; Edge bytes are read/modified/written, interior bytes stored bank by bank.
; IRQs are masked one scanline at a time. A/X/Y, ptr1, tmp1-tmp4 destroyed.
_dhgr_span_asm:
        sta row
        stx rows
        lda _dhgr_span_x
        ldx _dhgr_span_x+1
        jsr split
        sta _dhgr_first
        lda from_bit,y
        sta _dhgr_first_mask
        lda _dhgr_span_end
        ldx _dhgr_span_end+1
        jsr split
        sta _dhgr_last
        lda to_bit,y
        sta _dhgr_last_mask
        ldx #0
        lda _dhgr_first
        sta tmp1                ; interior first byte
        lda _dhgr_last
        sta tmp2                ; interior last byte
        lda _dhgr_first_mask
        ldy _dhgr_first
        cpy _dhgr_last
        bne @two
        and _dhgr_last_mask
        cmp #$7F
        beq @interior
        jsr add_edge
        jmp @empty
@two:   cmp #$7F
        beq @right_edge
        jsr add_edge
        inc tmp1
@right_edge:
        lda _dhgr_last_mask
        cmp #$7F
        beq @interior
        ldy _dhgr_last
        jsr add_edge
        dec tmp2
@interior:
        lda tmp2
        cmp tmp1
        bcc @empty
        ; Aux bytes are even: columns (i0+1)/2..i1/2.
        lda tmp1
        clc
        adc #1
        lsr
        sta aux_c0
        lda tmp2
        lsr
        sta aux_c1
        cmp aux_c0
        bcs @main
        lda #$FF
        sta aux_c0
@main:  ; Main bytes are odd: columns i0/2..(i1+1)/2-1.
        lda tmp2
        clc
        adc #1
        lsr
        sta main_c1
        lda tmp1
        lsr
        sta main_c0
        cmp main_c1
        bcc @main_used
        lda #$FF
        sta main_c0
        bne @rows
@main_used:
        dec main_c1
        jmp @rows
@empty: lda #$FF
        sta aux_c0
        sta main_c0
@rows:  stx edges
@row:   php
        sei
        ldy row
        lda dhgr_rowlo,y
        sta ptr1
        lda dhgr_rowhi,y
        ora _dhgr_base
        sta ptr1+1
        ldx edges
        beq @aux
@edge:  dex
        ldy edge_col,x
        lda edge_main,x
        bne @edge_main
        jsr aux_read
        and edge_keep,x
        ora edge_bits,x
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        txa
        bne @edge
        beq @aux
@edge_main:
        lda (ptr1),y
        and edge_keep,x
        ora edge_bits,x
        sta (ptr1),y
        txa
        bne @edge
@aux:   ; Aux column c holds byte 2c: pattern 0 (c even) or 2 (c odd).
        ldy aux_c0
        bmi @main_bank
        sta RAMWRTON
        tya
        lsr
        bcs @aux_odd
@aux_even:
        lda _dhgr_pattern
        sta (ptr1),y
        cpy aux_c1
        beq @aux_done
        iny
@aux_odd:
        lda _dhgr_pattern+2
        sta (ptr1),y
        cpy aux_c1
        beq @aux_done
        iny
        bne @aux_even
@aux_done:
        sta RAMWRTOFF
@main_bank:
        ; Main column c holds byte 2c+1: pattern 1 (c even) or 3 (c odd).
        ldy main_c0
        bmi @row_done
        tya
        lsr
        bcs @main_odd
@main_even:
        lda _dhgr_pattern+1
        sta (ptr1),y
        cpy main_c1
        beq @row_done
        iny
@main_odd:
        lda _dhgr_pattern+3
        sta (ptr1),y
        cpy main_c1
        beq @row_done
        iny
        bne @main_even
@row_done:
        plp
        inc row
        dec rows
        beq @done
        jmp @row
@done:  rts

; Byte Y with mask A: edge X, merged pattern bits; X advances.
add_edge:
        sta tmp3
        eor #$FF
        sta edge_keep,x
        tya
        lsr
        sta edge_col,x
        lda #0
        rol
        sta edge_main,x
        tya
        and #3
        tay
        lda _dhgr_pattern,y
        and tmp3
        sta edge_bits,x
        inx
        rts
