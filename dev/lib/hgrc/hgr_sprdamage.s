; VERHILLE Arnaud — GPL-3.0. Optional save-under byte-overlap closure, NMOS.
; Extracted only when the C engine config enables HGR_SPR_DAMAGE.
; Non-reentrant C-callable worker: A/X/Y, ptr1..ptr4 and tmp1..tmp4 destroyed.
.export _hgr_spr_damage
.import _spr_box, _spr_dirty, _spr_count, _spr_invalid, _spr_shape
.import _spr_drawn, _spr_px, _spr_py, _spr_x, _spr_y
.import spr_pgbase, spr_changed, spr_visible, spr_bits
.import _hgr_col7, _hgr_build_columns
.importzp ptr1, ptr2, ptr3, ptr4, tmp2, tmp3, tmp4
; spr_changed only borrows tmp1; spr_visible does not write scratch.
id = tmp2
other = tmp3
id_offset = tmp4
; The column builder finishes before these flags are initialized. No
; subsequent callee touches ptr1, and the closure itself makes no calls.
all = ptr1
changed = ptr1+1
; Geometry survives only spr_visible (no scratch writes) and add_box.
; The shape pointer in ptr3 is dead once width/height have been read;
; the same pair then holds the old or new x coordinate.
width = ptr2
height = ptr2+1
xpos = ptr3
ypos = ptr4
left = ptr4+1
.code
_hgr_spr_damage:
        jsr _hgr_build_columns
        lda #0
        sta _spr_dirty
        sta id
        lda spr_pgbase
        beq page1
        lda #2
        bne page
page1:
        lda #1
page:
        and _spr_invalid
        sta all
boxes:
        ldx id
        lda all
        bne mark
        jsr spr_changed
        beq initialize_box
mark:
        ldx id
        lda spr_bits,x
        ora _spr_dirty
        sta _spr_dirty
initialize_box:
        lda id
        asl
        asl
        tay
        lda #40
        sta _spr_box,y
        lda #192
        sta _spr_box+1,y
        lda #0
        sta _spr_box+2,y
        sta _spr_box+3,y
        lda id
        asl
        tay
        lda _spr_shape,y
        sta ptr3
        lda _spr_shape+1,y
        sta ptr3+1
        ora ptr3
        beq next_box
        ldy #4
        lda (ptr3),y
        sta width
        iny
        lda (ptr3),y
        sta height
        lda id
        clc
        adc spr_pgbase
        tay
        lda _spr_drawn,y
        beq new_box
        lda _spr_py,y
        sta ypos
        tya
        asl
        tay
        lda _spr_px,y
        sta xpos
        lda _spr_px+1,y
        sta xpos+1
        jsr add_box
new_box:
        ldx id
        jsr spr_visible
        beq next_box
        lda _spr_y,x
        sta ypos
        txa
        asl
        tay
        lda _spr_x,y
        sta xpos
        lda _spr_x+1,y
        sta xpos+1
        jsr add_box
next_box:
        inc id
        lda id
        cmp _spr_count
        bcs closure
        jmp boxes
closure:
        lda #0
        sta changed
        sta id
outer:
        ldx id
        lda _spr_dirty
        and spr_bits,x
        beq next_id
        txa
        asl
        asl
        tax
        stx id_offset
        lda _spr_box,x
        cmp _spr_box+2,x
        bcs next_id
        lda #0
        sta other
inner:
        ldx other
        lda _spr_dirty
        and spr_bits,x
        bne next_other
        txa
        asl
        asl
        tay
        lda _spr_box,y
        cmp _spr_box+2,y
        bcs next_other
        ldx id_offset
        lda _spr_box,x
        cmp _spr_box+2,y
        bcs next_other
        lda _spr_box,y
        cmp _spr_box+2,x
        bcs next_other
        lda _spr_box+1,x
        cmp _spr_box+3,y
        bcs next_other
        lda _spr_box+1,y
        cmp _spr_box+3,x
        bcs next_other
        ldx other
        lda spr_bits,x
        ora _spr_dirty
        sta _spr_dirty
        lda #1
        sta changed
next_other:
        inc other
        lda other
        cmp _spr_count
        bcc inner
next_id:
        inc id
        lda id
        cmp _spr_count
        bcs closure_pass_done
        jmp outer
closure_pass_done:
        lda changed
        beq complete
        jmp closure
complete:
        rts
add_box:
        ldx xpos
        lda xpos+1
        bne high_x
        lda _hgr_col7,x
        jmp column
high_x:
        lda _hgr_col7+256,x
column:
        sta left
        lda id
        asl
        asl
        tay
        lda left
        cmp _spr_box,y
        bcs top
        sta _spr_box,y
top:
        lda ypos
        cmp _spr_box+1,y
        bcs right
        sta _spr_box+1,y
right:
        clc
        lda left
        adc width
        cmp #41
        bcc compare_right
        lda #40
compare_right:
        cmp _spr_box+2,y
        bcc bottom
        sta _spr_box+2,y
bottom:
        clc
        lda ypos
        adc height
        bcs clip_bottom
        cmp #193
        bcc compare_bottom
clip_bottom:
        lda #192
compare_bottom:
        cmp _spr_box+3,y
        bcc added
        sta _spr_box+3,y
added:
        rts
