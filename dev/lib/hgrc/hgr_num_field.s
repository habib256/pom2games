; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_putu_field(x,y,value,width), cc65 fastcall: A=width,
; C stack=value low/high,y,x low/high. Reject before alignment can wrap x.
; Local frame: buffer[6],width,length,y,x low/high. Width/length reuse the
; consumed value slots, surviving the erase call's cc65 scratch clobbers.
.include "hgr_num_frame.inc"
.export _hgr_putu_field
.import _hgr_utoa, _hgr_clear_pixrect, _hgr_puts, incsp5, addysp
.importzp sp, tmp3, tmp4, _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
; A = 0..14 cells. Return the 18-pixel pitch times A, with carry clear.
.macro field_pixels
        asl a
        sta tmp3
        asl a
        asl a
        asl a
        clc
        adc tmp3
.endmacro
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
        hgr_reserve_stack 6
        lda sp
        sta _hgr_u_ptr
        lda sp+1
        sta _hgr_u_ptr+1
        jsr _hgr_utoa
        tya
        ldy #7
        sta (sp),y              ; replace value high with digit count
        ; Four C arguments for clear_pixrect; height=16 stays in A.
        hgr_reserve_stack 4
        ldy #10
        lda (sp),y
        field_pixels                ; 18*width <=252, hence C=0
        sbc #1                  ; C=0 subtracts two: 18*width-2 pixels
        ldy #0
        sta (sp),y
        hgr_move_coords 12, 1
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
        field_pixels                ; 18*padding <=234, C=0 for the x addition
        ldy #9
        adc (sp),y
        sta (sp),y
        bcc text_frame
        iny
        lda (sp),y
        adc #0
        sta (sp),y
text_frame:
        hgr_reserve_stack 3
        hgr_move_coords 11, 0
        lda _hgr_u_ptr           ; erase preserves the conversion parameters
        ldx _hgr_u_ptr+1
        hgr_draw_number _hgr_puts, 11
