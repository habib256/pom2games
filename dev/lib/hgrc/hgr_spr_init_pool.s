; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Native save-under initialization. State/configuration remain in the C
; archive member; no assembler HGR_SPR_MAX/DAMAGE setting is required.
.export _hgr_spr_init_pool
.import _spr_under,_spr_count,_spr_capacity,_spr_invalid,_spr_dbuf,_spr_drawpage
.import _spr_shape,_spr_active,_spr_drawn,_spr_slots,_spr_damage_fn,_spr_damage_default
.import _hgr_set_draw_page,_hgr_show_page,incsp6
.importzp sp,ptr1,ptr2,tmp1,tmp2,tmp3
.code
; fastcall: A=capacity; six-byte frame=count,byteslo,byteshi,poollo,poolhi,dbuf.
; Return AX=0/1; consume the frame, preserve IRQ state. Rejection is atomic.
; Scratch: ptr1=page bytes, ptr2=pool, tmp1=capacity, tmp2=count, tmp3=raw dbuf.
_hgr_spr_init_pool:
 sta tmp1
 ldy #3
 lda (sp),y
 sta ptr2
 iny
 lda (sp),y
 sta ptr2+1
 ora ptr2
 beq @reject
 ldy #0
 lda (sp),y
 beq @reject
 cmp _spr_slots
 beq @count_ok
 bcs @reject
@count_ok:
 sta tmp2
 lda tmp1
 beq @reject
 lda #0
 sta ptr1+1
 ldx tmp2
@multiply:
 clc
 adc tmp1
 bcc :+
 inc ptr1+1
: dex
 bne @multiply
 sta ptr1
 ldy #5
 lda (sp),y
 sta tmp3
 beq @single
 lda ptr1
 asl a
 tax
 lda ptr1+1
 rol a
 jmp @compare
@single:
 ldx ptr1
 lda ptr1+1
@compare:
 ldy #2
 cmp (sp),y
 bcc @valid
 bne @reject
 txa
 dey
 cmp (sp),y
 bcc @valid
 beq @valid
@reject:
 lda #0
 ldx #0
 jmp incsp6
; Commit only after all validation. Clear exactly the original arrays;
; positions, block sizes, dirty/box state and unused bytes remain untouched.
@valid:
 lda ptr2
 sta _spr_under
 sta _spr_under+2
 lda ptr2+1
 sta _spr_under+1
 sta _spr_under+3
 lda tmp3
 beq @under_ready
 lda ptr2
 clc
 adc ptr1
 sta _spr_under+2
 lda ptr2+1
 adc ptr1+1
 sta _spr_under+3
@under_ready:
 lda #0
 sta _spr_invalid
 lda _spr_damage_default
 sta _spr_damage_fn
 lda _spr_damage_default+1
 sta _spr_damage_fn+1
 lda tmp2
 sta _spr_count
 lda tmp1
 sta _spr_capacity
 lda tmp3
 sta _spr_dbuf
 lda _spr_slots
 asl a
 tax
 lda #0
@clear_words:
 dex
 sta _spr_shape,x
 sta _spr_drawn,x
 bne @clear_words
 ldx _spr_slots
@clear_active:
 dex
 sta _spr_active,x
 bne @clear_active
 lda #1
 ldx #0
 jsr _hgr_set_draw_page
 jsr _hgr_show_page
; The page callbacks may destroy every cc65 scratch register. Reload the
; original flag from its still-live argument byte instead of retaining scratch.
 ldy #5
 lda (sp),y
 tax
 lda #1
 cpx #0
 beq @draw_ready
 lda #2
@draw_ready:
 sta _spr_drawpage
 cpx #0
 beq @done
 ldx #0
 jsr _hgr_set_draw_page
@done:
 lda #1
 ldx #0
 jmp incsp6
