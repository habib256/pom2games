; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_putu_field(x,y,value,width), cc65 fastcall: A=width,
; C stack=value low/high,y,x low/high. Reject before alignment can wrap x.
; Local frame: buffer[6],width,length,y,x low/high. Width/length reuse the
; consumed value slots, surviving the erase call's cc65 scratch clobbers.
.export _hgr_putu_field
.import _hgr_utoa, _hgr_clear_pixrect, _hgr_puts, incsp5, addysp
.importzp sp, tmp3, tmp4, _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
.code
rejected:
        jmp incsp5
_hgr_putu_field:
        cmp #0
        beq rejected
        cmp #15
        bcc width_ready
        lda #14
width_ready:
        sta tmp4
        ldy #4
        lda (sp),y
        cmp #2
        bcs rejected
        tax
        dey
        lda (sp),y
        cpx #0
        beq x_ready
        cmp #24
        bcs rejected
x_ready:
        dey
        lda (sp),y
        cmp #192
        bcs rejected
        ldy #0
        lda (sp),y
        sta _hgr_u_lo
        iny
        lda (sp),y
        sta _hgr_u_hi
        dey
        lda tmp4
        sta (sp),y              ; replace value low with clamped width
        lda sp
        sec
        sbc #6
        sta sp
        bcs buffer_ready
        dec sp+1
buffer_ready:
        lda sp
        sta _hgr_u_ptr
        lda sp+1
        sta _hgr_u_ptr+1
        jsr _hgr_utoa
        tya
        ldy #7
        sta (sp),y              ; replace value high with digit count
        ; Four C arguments for clear_pixrect; height=16 stays in A.
        lda sp
        sec
        sbc #4
        sta sp
        bcs erase_frame
        dec sp+1
erase_frame:
        ldy #10
        lda (sp),y
        asl a
        sta tmp3
        asl a
        asl a
        asl a
        clc
        adc tmp3                ; 18*width <=252, hence C=0
        sbc #1                  ; C=0 subtracts two: 18*width-2 pixels
        ldy #0
        sta (sp),y
        .repeat 3, I
        ldy #12+I
        lda (sp),y
        ldy #1+I
        sta (sp),y
        .endrepeat
        lda #16
        jsr _hgr_clear_pixrect
        ; Erase consumed four bytes. Compute padding from saved metadata.
        ldy #6
        lda (sp),y
        iny
        sec
        sbc (sp),y
        bcc text_frame
        beq text_frame
        asl a
        sta tmp3
        asl a
        asl a
        asl a
        clc
        adc tmp3                ; 18*padding <=234, C=0 for the x addition
        ldy #9
        adc (sp),y
        sta (sp),y
        bcc text_frame
        iny
        lda (sp),y
        adc #0
        sta (sp),y
text_frame:
        lda sp
        sec
        sbc #3
        sta sp
        bcs text_args
        dec sp+1
text_args:
        .repeat 3, I
        ldy #11+I
        lda (sp),y
        ldy #I
        sta (sp),y
        .endrepeat
        lda _hgr_u_ptr           ; erase preserves the conversion parameters
        ldx _hgr_u_ptr+1
        jsr _hgr_puts
        ldy #11                 ; buffer plus the original five argument bytes
        jmp addysp
