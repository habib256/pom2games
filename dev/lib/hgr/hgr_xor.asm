; VERHILLE Arnaud — GPL-3.0. Native HGR XOR rectangles and pre-shifted sprites.
; hx_x/y/w/h: 8-bit pixels; x+w<=256, y+h<=192, w/h>0.
; hx_page = 0 ($2000) or $60 ($4000); hgr_lo/hi are page-1 tables.
; HGR_XOR_DIV7/MOD7 alias caller tables (256 entries). No colour bit touched.
; hgr_xor_sprite: hx_data points to 8 rows of two seven-bit bytes, hx_x/y.
; Caller pre-shifts hx_data for x modulo seven. A/X/Y and scratch destroyed.
.ifndef _HGR_XOR_LOADED_
_HGR_XOR_LOADED_ = 1
.zeropage
hx_ptr: .res 2
hx_data: .res 2
hx_x: .res 1
hx_y: .res 1
hx_w: .res 1
hx_h: .res 1
hx_page: .res 1
hx_first: .res 1
hx_last: .res 1
hx_lm: .res 1
hx_rm: .res 1
hx_row: .res 1
hx_index: .res 1
.code
hgr_xor_rect:
        ldx hx_x
        lda HGR_XOR_DIV7,x
        sta hx_first
        lda HGR_XOR_MOD7,x
        tax
        lda hx_left_masks,x
        sta hx_lm
        lda hx_x
        clc
        adc hx_w
        sec
        sbc #1
        tax
        lda HGR_XOR_DIV7,x
        sta hx_last
        lda HGR_XOR_MOD7,x
        tax
        lda hx_right_masks,x
        sta hx_rm
        lda hx_y
        sta hx_row
@line:  ldx hx_row
        lda hgr_lo,x
        sta hx_ptr
        lda hgr_hi,x
        eor hx_page
        sta hx_ptr+1
        ldy hx_first
@byte:  lda #$7f
        cpy hx_first
        bne :+
        and hx_lm
:       cpy hx_last
        bne :+
        and hx_rm
:       eor (hx_ptr),y
        sta (hx_ptr),y
        cpy hx_last
        beq @line_end
        iny
        bne @byte
@line_end:
        inc hx_row
        dec hx_h
        bne @line
        rts

hgr_xor_sprite:
        ldx hx_x
        lda HGR_XOR_DIV7,x
        sta hx_first
        lda hx_y
        sta hx_row
        lda #0
        sta hx_index
@line:  ldx hx_row
        lda hgr_lo,x
        sta hx_ptr
        lda hgr_hi,x
        eor hx_page
        sta hx_ptr+1
        ldy hx_index
        lda (hx_data),y
        ldy hx_first
        eor (hx_ptr),y
        sta (hx_ptr),y
        inc hx_index
        ldy hx_index
        lda (hx_data),y
        ldy hx_first
        iny
        eor (hx_ptr),y
        sta (hx_ptr),y
        inc hx_index
        inc hx_row
        lda hx_index
        cmp #16
        bne @line
        rts
.rodata
hx_left_masks: .byte $7f,$7e,$7c,$78,$70,$60,$40
hx_right_masks: .byte $01,$03,$07,$0f,$1f,$3f,$7f
.endif
