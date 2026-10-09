; VERHILLE Arnaud — GPL-3.0. Sprite engine frame path, NMOS 6502 / cc65 ABI.
; Main RAM/ZP, D=0, not reentrant/IRQ-callable. Caller-owned pools per page.
.export _hgr_spr_move, _hgr_spr_hide, _hgr_spr_render, _hgr_spr_present
.export _hgr_spr_update, _hgr_spr_invalidate
.export spr_visible, spr_changed, spr_bits, spr_pgbase
.import popax, popa, _hgr_set_draw_page, _hgr_show_page
.import _spr_shape, _spr_x, _spr_y, _spr_active, _spr_px, _spr_py, _spr_drawn
.import _spr_under, _spr_count, _spr_capacity, _spr_invalid, _spr_dbuf, _spr_drawpage
.import _spr_slots, _spr_block, _spr_dirty, _spr_damage_fn
.import _hgr_ms_restore_run, _hgr_msu_run, _hgr_ms_block
.importzp _hgr_ms_x, _hgr_ms_y, _hgr_ms_spr, _hgr_ms_under
.bss
spr_pgbase: .res 1
pagebit: .res 1
first: .res 1
id: .res 1
visible: .res 1
pool: .res 2
under: .res 2
newx: .res 2
newy: .res 1
.rodata
spr_bits: .byte 1,2,4,8,16,32,64,128
.code
; y in A, x/id on the cc65 stack. Consume arguments even for invalid ids.
_hgr_spr_move:
        sta newy
        jsr popax
        sta newx
        stx newx+1
        jsr popa
        cmp _spr_count
        bcs move_done
        tax
        lda newy
        sta _spr_y,x
        txa
        asl
        tay
        lda newx
        sta _spr_x,y
        lda newx+1
        sta _spr_x+1,y
        lda _spr_shape,y
        ora _spr_shape+1,y
        beq inactive
        lda #1
inactive:
        sta _spr_active,x
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
; X=id, A=visibility, preserves X, destroys Y/flags.
spr_visible:
        lda _spr_active,x
        beq no
        txa
        asl
        tay
        lda _spr_shape,y
        ora _spr_shape+1,y
        beq no
        lda _spr_x+1,y
        cmp #1
        bcc within
        bne no
        lda _spr_x,y
        cmp #24
        bcs no
within:
        lda _spr_y,x
        cmp #192
        bcs no
        lda #1
        rts
no:
        lda #0
        rts
; X=id, A=changed vs this page. Destroys X/Y/flags.
spr_changed:
        jsr spr_visible
        sta visible
        txa
        clc
        adc spr_pgbase
        tay
        lda _spr_drawn,y
        cmp visible
        bne yes
        lda visible
        beq no
        lda _spr_py,y
        cmp _spr_y,x
        bne yes
        tya
        asl
        tay
        txa
        asl
        tax
        lda _spr_px,y
        cmp _spr_x,x
        bne yes
        lda _spr_px+1,y
        cmp _spr_x+1,x
        bne yes
        jmp no
yes:
        lda #1
        rts
_hgr_spr_render:
        lda _spr_count
        bne initialized
        rts
initialized:
        lda _spr_drawpage
        ldx #0
        jsr _hgr_set_draw_page
        lda #0
        sta spr_pgbase
        sta first
        ldy #0
        lda #1
        sta pagebit
        lda _spr_drawpage
        cmp #2
        bne page_selected
        lda _spr_slots
        sta spr_pgbase
        ldy #2
        lda #2
        sta pagebit
page_selected:
        lda _spr_under,y
        sta pool
        lda _spr_under+1,y
        sta pool+1
        lda _spr_invalid
        and pagebit
        bne dirty
prefix:
        ldx first
        jsr spr_changed
        bne dirty
        inc first
        lda first
        cmp _spr_count
        bcc prefix
        rts
dirty:
        lda _spr_damage_fn
        ora _spr_damage_fn+1
        beq ready
        jsr damage_call
        lda #0
        sta first
ready:
        lda pagebit
        eor #$ff
        and _spr_invalid
        sta _spr_invalid
        lda pool
        sta under
        lda pool+1
        sta under+1
        ldx _spr_count
end_pool:
        jsr add_under
        dex
        bne end_pool
        lda _spr_count
        sta id
restore:
        dec id
        sec
        lda under
        sbc _spr_capacity
        sta under
        bcs restored_pointer
        dec under+1
restored_pointer:
        jsr is_dirty
        beq restored
        lda id
        clc
        adc spr_pgbase
        tay
        lda _spr_drawn,y
        beq restored
        lda _spr_py,y
        sta _hgr_ms_y
        tya
        asl
        tay
        lda _spr_px,y
        sta _hgr_ms_x
        lda _spr_px+1,y
        sta _hgr_ms_x+1
        jsr parameters
        jsr _hgr_ms_restore_run
        lda id
        clc
        adc spr_pgbase
        tay
        lda #0
        sta _spr_drawn,y
restored:
        lda id
        cmp first
        bne restore
        lda pool
        sta under
        lda pool+1
        sta under+1
        ldx first
        beq draw_start
start_pool:
        jsr add_under
        dex
        bne start_pool
draw_start:
        lda first
        sta id
draw:
        jsr is_dirty
        beq drawn
        ldx id
        jsr spr_visible
        beq drawn
        lda _spr_y,x
        sta _hgr_ms_y
        lda _spr_block,x
        sta _hgr_ms_block
        txa
        asl
        tay
        lda _spr_x,y
        sta _hgr_ms_x
        lda _spr_x+1,y
        sta _hgr_ms_x+1
        jsr parameters
        jsr _hgr_msu_run
        lda id
        clc
        adc spr_pgbase
        tay
        lda #1
        sta _spr_drawn,y
        ldx id
        lda _spr_y,x
        sta _spr_py,y
        tya
        asl
        tay
        txa
        asl
        tax
        lda _spr_x,x
        sta _spr_px,y
        lda _spr_x+1,x
        sta _spr_px+1,y
drawn:
        jsr add_under
        inc id
        lda id
        cmp _spr_count
        bcc draw
        rts
is_dirty:
        lda _spr_damage_fn
        ora _spr_damage_fn+1
        bne optional_dirty
        lda #1
        rts
optional_dirty:
        ldx id
        lda _spr_dirty
        and spr_bits,x
        rts
parameters:
        lda id
        asl
        tay
        lda _spr_shape,y
        sta _hgr_ms_spr
        lda _spr_shape+1,y
        sta _hgr_ms_spr+1
        lda under
        sta _hgr_ms_under
        lda under+1
        sta _hgr_ms_under+1
        rts
add_under:
        clc
        lda under
        adc _spr_capacity
        sta under
        bcc added
        inc under+1
added:
        rts
damage_call:
        jmp (_spr_damage_fn)
_hgr_spr_present:
        lda _spr_dbuf
        beq added
        lda _spr_drawpage
        ldx #0
        jsr _hgr_set_draw_page
        jsr _hgr_show_page
        lda _spr_drawpage
        eor #3
        sta _spr_drawpage
        ldx #0
        jmp _hgr_set_draw_page
_hgr_spr_update:
        jsr _hgr_spr_render
        jmp _hgr_spr_present
