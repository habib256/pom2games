; VERHILLE Arnaud — GPL-3.0. Sprite engine frame path, NMOS 6502 / cc65 ABI.
; Main RAM/ZP, D=0, not reentrant/IRQ-callable. Caller-owned pools per page.
.export _hgr_spr_render, _hgr_spr_present, _hgr_spr_update
.import spr_visible,spr_changed,spr_bits,spr_pgbase
.import _hgr_set_draw_page, _hgr_show_page
.import _spr_shape, _spr_x, _spr_y, _spr_active, _spr_px, _spr_py, _spr_drawn
.import _spr_under, _spr_count, _spr_capacity, _spr_invalid, _spr_dbuf, _spr_drawpage
.import _spr_slots, _spr_block, _spr_dirty, _spr_damage_fn
.import _hgr_ms_restore_run, _hgr_msu_run, _hgr_ms_block
.importzp _hgr_ms_x, _hgr_ms_y, _hgr_ms_spr, _hgr_ms_under
.bss
pagebit: .res 1
first: .res 1
id: .res 1
pool: .res 2
under: .res 2
.code
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
        jsr add_under_n
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
        jsr add_under_n
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
        ldx #1
; X positive slots: accumulate the low pointer in A and store it once.
; All callers discard X; first=0 bypasses this entry in the draw setup.
add_under_n:
        lda under
@slot:  clc
        adc _spr_capacity
        bcc @next
        inc under+1
@next:  dex
        bne @slot
        sta under
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
