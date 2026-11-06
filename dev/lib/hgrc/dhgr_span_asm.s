; VERHILLE Arnaud — GPL-3.0. Bank-safe optional DHGR primitive.
.include "apple2.inc"
.code
.export _dhgr_span_asm, _dhgr_span_x, _dhgr_span_end
.import _dhgr_base, _dhgr_pattern, dhgr_rowlo, dhgr_rowhi
.import _dhgr_cellbyte, _dhgr_cellphase
.import _dhgr_first, _dhgr_last, _dhgr_first_mask, _dhgr_last_mask
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4, aux_read
; Private row geometry survives split/prepare and aux_read in cc65 scratch.
; The public rectangle/axis entries tail-call this kernel after releasing
; their frames; none retain these volatile pointers across it.
row = ptr2
rows = ptr2+1
start = ptr3                    ; first page column in aux/main, or $FF
pairs = ptr4                    ; interior byte-pair count in aux/main
.bss
_dhgr_span_x: .res 2            ; first bit, 0..559
_dhgr_span_end: .res 2          ; last bit, x..559
edges: .res 1                   ; partial edge bytes, 0..2
edge_col: .res 2
edge_main: .res 2
edge_keep: .res 2
edge_bits: .res 2
; Interior of each bank (index 0 aux, 1 main): first page column or $FF
; when empty, byte pairs from there, the odd last column or $FF, and the
; pattern bytes of the first column and of the next one.
tail: .res 2
; Both prepare calls finish before rows consume these pattern bytes.
; tmp3/tmp4 are otherwise dead after the last add_edge.
pa = tmp3
.assert tmp4 = tmp3 + 1, lderror, "cc65 tmp3/tmp4 must be consecutive"
pb: .res 2
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
; IRQs are masked one scanline at a time. A/X/Y, ptr1-ptr4, tmp1-tmp4 destroyed.
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
        jmp @edges_only
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
        stx edges
        lda tmp2
        cmp tmp1
        bcc @empty
        ; Aux bytes are even: columns (i0+1)/2..i1/2.
        lda tmp2
        lsr
        tay
        lda tmp1
        clc
        adc #1
        lsr
        ldx #0
        jsr prepare
        ; Main bytes are odd: columns i0/2..(i1+1)/2-1.
        lda tmp2
        clc
        adc #1
        lsr
        beq @main_empty         ; i1 = 0: no odd byte
        tay
        dey
        lda tmp1
        lsr
        ldx #1
        jsr prepare
        jmp @row
@edges_only:
        stx edges
@empty: lda #$FF
        sta start
@main_empty:
        lda #$FF
        sta start+1
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
@aux:   ldy start
        bmi @main_bank
        sta RAMWRTON
        ldx pairs
        beq @aux_tail
@aux_pair:
        lda pa
        sta (ptr1),y
        iny
        lda pb
        sta (ptr1),y
        iny
        dex
        bne @aux_pair
@aux_tail:
        ldy tail
        bmi @aux_done
        lda pa
        sta (ptr1),y
@aux_done:
        sta RAMWRTOFF
@main_bank:
        ldy start+1
        bmi @row_done
        ldx pairs+1
        beq @main_tail
@main_pair:
        lda pa+1
        sta (ptr1),y
        iny
        lda pb+1
        sta (ptr1),y
        iny
        dex
        bne @main_pair
@main_tail:
        ldy tail+1
        bmi @row_done
        lda pa+1
        sta (ptr1),y
@row_done:
        plp
        inc row
        dec rows
        beq @done
        jmp @row
@done:  rts

; Interior of bank X (0 aux, 1 main): columns A..Y of the page, in the
; patterns of that bank (even column: bank, odd: bank+2); Y < A is empty.
prepare:
        sta start,x
        tya
        sec
        sbc start,x             ; columns - 1
        bcc @empty
        lsr                     ; C = 1: an even count, no odd column
        bcs @even
        sta pairs,x
        tya                     ; the last column is odd, past the pairs
        bcc @tail
@even:  adc #0                  ; one more pair (C = 1)
        sta pairs,x
        lda #$FF
@tail:  sta tail,x
        lda start,x
        and #1
        asl
        stx ptr1+1
        ora ptr1+1              ; bank + 2 for an odd first column
        tay
        lda _dhgr_pattern,y
        sta pa,x
        tya
        eor #2
        tay
        lda _dhgr_pattern,y
        sta pb,x
        rts
@empty: lda #$FF
        sta start,x
        rts

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
