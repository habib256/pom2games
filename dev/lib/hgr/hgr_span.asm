; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native byte spans through hgr_lo/hi. No clipping; not reentrant.
; hgr_hspan: hs_ptr points to row, Y=start byte, hs_end_col=end inclusive,
; hs_left_mask/right_mask select edge pixels. Require 0<=start<=end<=39.
; ORs edges, writes $7F in full bytes (including clearing palette bit).
; hgr_vspan: Y=byte column 0..39, X=start row, A=end row exclusive,
; hs_left_mask=pixel mask. Require 0<=start<end<=192. OR preserves bit 7.
; Clobbers A,X,Y, hs_ptr; writable CODE for vertical loop end operand.
; Define hs_* aliases before inclusion to share caller ZP scratch.
.ifndef _HGR_SPAN_LOADED_
_HGR_SPAN_LOADED_ = 1
.zeropage
.ifndef hs_ptr
hs_ptr: .res 2
.endif
.ifndef hs_end_col
hs_end_col: .res 1
.endif
.ifndef hs_left_mask
hs_left_mask: .res 1
hs_right_mask: .res 1
.endif
.code
hgr_hspan:
        CPY hs_end_col
        BNE @first
        LDA hs_left_mask
        AND hs_right_mask
        ORA (hs_ptr),Y
        STA (hs_ptr),Y
        RTS
@first: LDA hs_left_mask
        ORA (hs_ptr),Y
        STA (hs_ptr),Y
        INY
@whole: CPY hs_end_col
        BEQ @last
        LDA #$7F
        STA (hs_ptr),Y
        INY
        BNE @whole
@last:  LDA hs_right_mask
        ORA (hs_ptr),Y
        STA (hs_ptr),Y
        RTS

hgr_vspan:
        STA @end+1
@row:   LDA hgr_lo,X
        STA hs_ptr
        LDA hgr_hi,X
        STA hs_ptr+1
        LDA (hs_ptr),Y
        ORA hs_left_mask
        STA (hs_ptr),Y
        INX
@end:   CPX #0
        BNE @row
        RTS


.endif
