; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Byte-aligned, prepacked seven-pixel HGR rows; draws through hgr_lo/hi.
; Inputs: sp_ptr, hsp_col (byte column), sp_yy (scanline), sp_wout (1..10),
; packed_rows (1..192 source rows), packed_repeat (1..192), packed_tail
; (low valid bits in last byte), sp_cm_ev/od and sp_cbit (colour attributes).
; Caller guarantees col+width<=40 and y+rows*repeat<=192; no clipping.
; Overwrites the rectangle including zero pixels; preserves trailing pixels.
; Mutates sp_ptr, sp_yy, packed_rows; clobbers A,X,Y and scratch below.
; Writable code required by shared scanline/page conventions; not reentrant.
.ifndef _HGR_SPRITE_PACKED_LOADED_
_HGR_SPRITE_PACKED_LOADED_ = 1
.zeropage
.ifndef sp_ptr
sp_ptr: .res 2
.endif
.ifndef sp_cm_ev
sp_cm_ev: .res 1
.endif
.ifndef sp_cm_od
sp_cm_od: .res 1
.endif
.ifndef sp_cbit
sp_cbit: .res 1
.endif
.ifndef sp_wout
sp_wout: .res 1
.endif
.ifndef sp_yy
sp_yy: .res 1
.endif
.ifndef sp_lin_lo
sp_lin_lo: .res 1
.endif
.ifndef sp_lin_hi
sp_lin_hi: .res 1
.endif
.segment "BSS"
.ifndef hsp_col
hsp_col: .res 1
.endif
packed_row: .res 10
packed_rows: .res 1
packed_repeat: .res 1
packed_repeat_left: .res 1
packed_tail: .res 1
.code
.include "hgr_sprite_color.inc"
hgr_sprite_packed:
@source:
        LDY #0
        LDX hsp_col
@pack:  TXA
        AND #1
        BNE @odd
        LDA sp_cm_ev
        JMP @mask
@odd:   LDA sp_cm_od
@mask:  AND (sp_ptr),Y
        ORA sp_cbit
        STA packed_row,Y
        INX
        INY
        CPY sp_wout
        BCC @pack
        LDA packed_repeat
        STA packed_repeat_left
@copy:  LDY sp_yy
        LDA hgr_lo,Y
        STA sp_lin_lo
        LDA hgr_hi,Y
        STA sp_lin_hi
        LDX #0
        LDY hsp_col
@byte:  INX
        CPX sp_wout
        BEQ @tail
        LDA packed_row-1,X
        STA (sp_lin_lo),Y
        INY
        BNE @byte
@tail:  ; Preserve pixels outside the sprite's trailing edge.
        LDA packed_tail
        EOR #$7F
        AND (sp_lin_lo),Y
        ORA packed_row-1,X
        STA (sp_lin_lo),Y
        INC sp_yy
        DEC packed_repeat_left
        BNE @copy
        CLC
        LDA sp_ptr
        ADC sp_wout
        STA sp_ptr
        BCC @advanced
        INC sp_ptr+1
@advanced:
        DEC packed_rows
        BNE @source
        RTS

.endif
