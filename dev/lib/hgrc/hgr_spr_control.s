; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Independent sprite controls. No rendering, lookup tables or default pool.
; NMOS6502 / cc65 ABI, main RAM/ZP, D=0; not reentrant/IRQ-callable.
.export _hgr_spr_move,_hgr_spr_hide,_hgr_spr_invalidate
.import _spr_count,_spr_y,_spr_x,_spr_shape,_spr_active,_spr_invalid,incsp3
.importzp sp,tmp1
.code
; y in A, x/id on the cc65 stack. Consume arguments even for invalid ids.
_hgr_spr_move:
        sta tmp1                ; y, needed only while validating id
        ldy #2
        lda (sp),y
        cmp _spr_count
        bcs move_return
        tax
        lda tmp1
        sta _spr_y,x
        txa
        asl
        tax                     ; two-byte slot offset; Y reads C arguments
        ldy #0
        lda (sp),y
        sta _spr_x,x
        iny
        lda (sp),y
        sta _spr_x+1,x
        lda _spr_shape,x
        ora _spr_shape+1,x
        beq inactive
        lda #1
inactive:
        tay
        txa
        lsr
        tax                     ; recover id, preserving visibility in Y
        tya
        sta _spr_active,x
move_return:
        jmp incsp3
move_done:
        rts
_hgr_spr_hide:
        cmp _spr_count
        bcs move_done
        tax
        lda #0
        sta _spr_active,x
        rts
_hgr_spr_invalidate:
        cmp #3
        bcs move_done
        cmp #0
        bne invalidate
        lda #3
invalidate:
        ora _spr_invalid
        sta _spr_invalid
        rts
