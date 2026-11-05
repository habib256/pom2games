; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Independent native definition entry for the masked save-under engine.
.export _hgr_spr_define
.import _spr_count,_spr_slots,_spr_drawn,_spr_capacity,_spr_block,_spr_shape,_spr_active
.import incsp1
.importzp sp,ptr1,tmp1,tmp2,tmp4
.code
; fastcall: AX=shape; one-byte frame=id. Return AX=0/1 and consume id.
; Scratch: ptr1=shape, tmp1=stride, tmp2=product, tmp4=id. IRQ state is untouched.
; Reject invalid IDs/drawn sprites before reading any shape-header bytes.
_hgr_spr_define:
 sta ptr1
 stx ptr1+1
 ldy #0
 lda (sp),y
 cmp _spr_count
 bcs @reject
 tax
 sta tmp4
 lda _spr_drawn,x
 bne @reject
 txa
 clc
 adc _spr_slots
 tay
 lda _spr_drawn,y
 bne @reject
 lda ptr1
 ora ptr1+1
 bne @shape
 sta tmp2
 jmp @save
@reject:
 lda #0
 ldx #0
 jmp incsp1
@shape:
 ldy #0
 lda (ptr1),y
 iny
 ora (ptr1),y
 beq @invalid
 iny
 lda (ptr1),y
 iny
 ora (ptr1),y
 beq @invalid
 iny
 lda (ptr1),y
 beq @invalid
 cmp #41
 bcs @invalid
 sta tmp1
 iny
 lda (ptr1),y
 beq @invalid
 cmp #193
 bcs @invalid
 sta tmp2
 lda #0
; Unsigned 8x8 product. Carry from ROR selects the next multiplier bit;
; a nonzero high byte cannot fit the byte-sized save-under capacity.
 ldy #8
 lsr tmp2
@multiply:
 bcc @no_add
 clc
 adc tmp1
@no_add:
 ror a
 ror tmp2
 dey
 bne @multiply
 cmp #0
 bne @invalid
 lda tmp2
 cmp _spr_capacity
 bcc @save
 beq @save
; An invalid non-null definition clears shape/active but preserves block.
; Null definitions reach @save and clear block as in the C implementation.
@invalid:
 ldx tmp4
 lda #0
 sta _spr_active,x
 txa
 asl a
 tax
 lda #0
 sta _spr_shape,x
 sta _spr_shape+1,x
 jmp @reject
@save:
 ldx tmp4
 lda tmp2
 sta _spr_block,x
 lda ptr1
 ora ptr1+1
 beq @active
 lda #1
@active:
 sta _spr_active,x
 txa
 asl a
 tax
 lda ptr1
 sta _spr_shape,x
 lda ptr1+1
 sta _spr_shape+1,x
 lda #1
 ldx #0
 jmp incsp1
