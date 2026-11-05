; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; dhgr_fill_bits(x,y,width,height,set): A=set; stack=height,width,y,x.
; The five remaining bytes already form dhgr_bit_rect's argument frame.
.export _dhgr_fill_bits
.import _dhgr_pattern, _dhgr_bit_rect
.importzp sp
.code
_dhgr_fill_bits:
        cmp #0
        beq pattern
        lda #$7f
pattern:
        sta _dhgr_pattern
        sta _dhgr_pattern+1
        sta _dhgr_pattern+2
        sta _dhgr_pattern+3
        ldy #0
        lda (sp),y             ; height is the helper's fastcall argument
        inc sp
        bne forward
        inc sp+1
forward:
        jmp _dhgr_bit_rect
