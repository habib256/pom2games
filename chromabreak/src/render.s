.include "layout.inc"
; VERHILLE Arnaud — GPL-3.0. DHGR rectangle sprites with per-page save-under.
; Main RAM/ZP on entry and exit. The sprite loop is mirrored in AUX RAM.
.setcpu "65C02"
.macpack longbranch
.include "apple2.inc"
.importzp ptr1, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4, aux_read
.import _dhgr_base, _timing_scan
.export _fast_draw, _fast_restore, _fast_reset, _fast_fill
.export _render_x, _render_y, _render_w, _render_h, _render_color, _render_style
.bss
black_last: .res 1
black_end: .res 1
restore_two: .res 1
.zeropage
_render_x: .res 1
_render_y: .res 1
_render_w: .res 1
_render_h: .res 1
_render_color: .res 1
_render_style: .res 1
sprite_base: .res 1
sprite_half: .res 1
slot: .res 1
bx: .res 1
row: .res 1
rows: .res 1
width: .res 1
column: .res 1
leftmask: .res 1
rightmask: .res 1
colorindex: .res 1
saving: .res 1
zero_fill: .res 1
sprite_i: .res 1
tip_left: .res 1
tip_right: .res 1
tip_lmask: .res 1
tip_rmask: .res 1
restore_main: .res 1
restore_aux: .res 1
sprite_special: .res 1
main_count: .res 1
aux_count: .res 1
sprite_inverse: .res 8
sprite_ink: .res 8
.code
; Instructions have identical addresses in main and auxiliary RAM.
; Masks and loop state stay in zero page while RAMRD switches banks.
; Save-under writes use main RAM, pixel writes use auxiliary RAM.
shader_template:
shader_row:
        ldx restore_main
        lda _render_style
        beq shader_pixels
        lda row
        cmp _render_y
        beq shader_tip
        lda _render_style
        cmp #2
        bne shader_pixels
        lda rows
        cmp #1
        bne shader_pixels
shader_tip:
        txa
        ora #4
        tax
shader_pixels:
        ldy #0
        lda main_count
        beq @aux
        lda (ptr1),y
        sta (ptr4),y
        and sprite_inverse,x
        ora sprite_ink,x
        sta (ptr1),y
        lda main_count
        dec
        beq @aux
        iny
        lda (ptr1),y
        sta (ptr4),y
        and sprite_inverse+2,x
        ora sprite_ink+2,x
        sta (ptr1),y
@aux:  lda aux_count
        beq shader_next
        txa
        eor #1
        tax
        ldy restore_aux
        sta $C003
        lda (ptr1),y
        sta (ptr3),y
        and sprite_inverse,x
        ora sprite_ink,x
        sta $C005
        sta (ptr1),y
        sta $C004
        lda aux_count
        dec
        beq @finish
        iny
        lda (ptr1),y
        sta (ptr3),y
        and sprite_inverse+2,x
        ora sprite_ink+2,x
        sta $C005
        sta (ptr1),y
        sta $C004
@finish:
        sta $C002
shader_next:
        inc row
        dec rows
        beq shader_done
        ; Slots are aligned to 32 bytes; both halves stay in one page.
        inc ptr4
        inc ptr4
        inc ptr3
        inc ptr3
        ldx row
        lda row_lo,x
        clc
        adc sprite_half
        sta ptr1
        lda row_hi,x
        adc sprite_base
        sta ptr1+1
        jmp shader_row
shader_done:
        rts
shader_end:
.assert shader_end-shader_template<256, error, "Mirrored shader exceeds one page"
.bss
SPRITES=11
SLOT_SIZE=32
old_x: .res SPRITES*2
old_pixels: .res SPRITES*2
old_bx: .res SPRITES*2
old_y: .res SPRITES*2
old_w: .res SPRITES*2
old_h: .res SPRITES*2
valid: .res SPRITES*2
.segment "LOWBSS"
.align 32
under: .res SPRITES*2*SLOT_SIZE
.rodata
.include "dhgr_layout.inc"
.import _dhgr_row_lo, _dhgr_row_hi, _dhgr_color_byte
row_lo = _dhgr_row_lo
row_hi = _dhgr_row_hi
xbyte = _dhgr_color_byte
dhgr_end_table endbyte,141
dhgr_left_table leftm,141
dhgr_right_table rightm,141
under_lo:
.repeat SPRITES*2,I
.byte <(under+I*SLOT_SIZE)
.endrepeat
under_hi:
.repeat SPRITES*2,I
.byte >(under+I*SLOT_SIZE)
.endrepeat
.export _tile_x, _tile_y
_tile_x:
.repeat 96,I
.byte 5+(I .mod 12)*11
.endrepeat
_tile_y:
.repeat 96,I
.byte CB_TILE_TOP+(I/12)*12
.endrepeat
patterns:
.repeat 16,C
.repeat 4,P
.byte (((((C>>1)|(C<<3))&15)*$1111)>>((P*7)&3))&$7F
.endrepeat
.endrepeat
ball_phase:
.repeat 141,I
.byte (I .mod 7)*8
.endrepeat
ball_masks:
.byte 0,96,127,127,15,126,127,127
.byte 15,0,124,127,127,97,127,127
.byte 1,64,127,127,31,124,127,127
.byte 31,0,120,127,127,67,127,127
.byte 3,0,127,127,63,120,127,127
.byte 63,0,112,127,127,7,127,127
.byte 7,0,126,127,127,112,127,127
small_inverse_1:
.byte 112,127,127,127,15,126,127,127,97,127,127,127,31,124,127,127,67,127,127,127,63,120,127,127,7,127,127,127
small_ink_1:
.byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
.byte 8,0,0,0,0,1,0,0,16,0,0,0,0,2,0,0,32,0,0,0,0,4,0,0,64,0,0,0
.byte 1,0,0,0,16,0,0,0,2,0,0,0,32,0,0,0,4,0,0,0,64,0,0,0,8,0,0,0
.byte 9,0,0,0,16,1,0,0,18,0,0,0,32,2,0,0,36,0,0,0,64,4,0,0,72,0,0,0
.byte 2,0,0,0,32,0,0,0,4,0,0,0,64,0,0,0,8,0,0,0,0,1,0,0,16,0,0,0
.byte 10,0,0,0,32,1,0,0,20,0,0,0,64,2,0,0,40,0,0,0,0,5,0,0,80,0,0,0
.byte 3,0,0,0,48,0,0,0,6,0,0,0,96,0,0,0,12,0,0,0,64,1,0,0,24,0,0,0
.byte 11,0,0,0,48,1,0,0,22,0,0,0,96,2,0,0,44,0,0,0,64,5,0,0,88,0,0,0
.byte 4,0,0,0,64,0,0,0,8,0,0,0,0,1,0,0,16,0,0,0,0,2,0,0,32,0,0,0
.byte 12,0,0,0,64,1,0,0,24,0,0,0,0,3,0,0,48,0,0,0,0,6,0,0,96,0,0,0
.byte 5,0,0,0,80,0,0,0,10,0,0,0,32,1,0,0,20,0,0,0,64,2,0,0,40,0,0,0
.byte 13,0,0,0,80,1,0,0,26,0,0,0,32,3,0,0,52,0,0,0,64,6,0,0,104,0,0,0
.byte 6,0,0,0,96,0,0,0,12,0,0,0,64,1,0,0,24,0,0,0,0,3,0,0,48,0,0,0
.byte 14,0,0,0,96,1,0,0,28,0,0,0,64,3,0,0,56,0,0,0,0,7,0,0,112,0,0,0
.byte 7,0,0,0,112,0,0,0,14,0,0,0,96,1,0,0,28,0,0,0,64,3,0,0,56,0,0,0
.byte 15,0,0,0,112,1,0,0,30,0,0,0,96,3,0,0,60,0,0,0,64,7,0,0,120,0,0,0
small_inverse_4:
.byte 0,0,124,127,15,0,64,127,1,0,120,127,31,0,0,127,3,0,112,127,63,0,0,126,7,0,96,127
small_ink_4:
.byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
.byte 8,17,2,0,0,17,34,0,16,34,4,0,0,34,68,0,32,68,8,0,0,68,8,1,64,8,17,0
.byte 17,34,0,0,16,34,4,0,34,68,0,0,32,68,8,0,68,8,1,0,64,8,17,0,8,17,2,0
.byte 25,51,2,0,16,51,38,0,50,102,4,0,32,102,76,0,100,76,9,0,64,76,25,1,72,25,19,0
.byte 34,68,0,0,32,68,8,0,68,8,1,0,64,8,17,0,8,17,2,0,0,17,34,0,16,34,4,0
.byte 42,85,2,0,32,85,42,0,84,42,5,0,64,42,85,0,40,85,10,0,0,85,42,1,80,42,21,0
.byte 51,102,0,0,48,102,12,0,102,76,1,0,96,76,25,0,76,25,3,0,64,25,51,0,24,51,6,0
.byte 59,119,2,0,48,119,46,0,118,110,5,0,96,110,93,0,108,93,11,0,64,93,59,1,88,59,23,0
.byte 68,8,1,0,64,8,17,0,8,17,2,0,0,17,34,0,16,34,4,0,0,34,68,0,32,68,8,0
.byte 76,25,3,0,64,25,51,0,24,51,6,0,0,51,102,0,48,102,12,0,0,102,76,1,96,76,25,0
.byte 85,42,1,0,80,42,21,0,42,85,2,0,32,85,42,0,84,42,5,0,64,42,85,0,40,85,10,0
.byte 93,59,3,0,80,59,55,0,58,119,6,0,32,119,110,0,116,110,13,0,64,110,93,1,104,93,27,0
.byte 102,76,1,0,96,76,25,0,76,25,3,0,64,25,51,0,24,51,6,0,0,51,102,0,48,102,12,0
.byte 110,93,3,0,96,93,59,0,92,59,7,0,64,59,119,0,56,119,14,0,0,119,110,1,112,110,29,0
.byte 119,110,1,0,112,110,29,0,110,93,3,0,96,93,59,0,92,59,7,0,64,59,119,0,56,119,14,0
.byte 127,127,3,0,112,127,63,0,126,127,7,0,96,127,127,0,124,127,15,0,64,127,127,1,120,127,31,0
small_ink_lo:
.repeat 16,C
.byte <(small_ink_1+C*28)
.endrepeat
.repeat 16,C
.byte <(small_ink_4+C*28)
.endrepeat
small_ink_hi:
.repeat 16,C
.byte >(small_ink_1+C*28)
.endrepeat
.repeat 16,C
.byte >(small_ink_4+C*28)
.endrepeat
.code
setup:
        bit _dhgr_base
        bvc :+
        clc
        adc #SPRITES
:       tax
        stx slot
        lda under_lo,x
        sta ptr4
        lda under_hi,x
        sta ptr4+1
        rts
_fast_reset:
        ; AUX instruction fetch and row tables match main RAM while RAMRD
        ; changes. IRQs stay masked only during installation or one sprite.
        php
        sei
        lda #<shader_template
        sta ptr3
        sta ptr4
        lda #>shader_template
        sta ptr3+1
        sta ptr4+1
        sta $C005
        ldy #0
:       lda (ptr3),y
        sta (ptr4),y
        iny
        cpy #shader_end-shader_template
        bne :-
        sta $C004
        lda #<row_lo
        sta ptr3
        sta ptr4
        lda #>row_lo
        sta ptr3+1
        sta ptr4+1
        sta $C005
        ldy #0
:       lda (ptr3),y
        sta (ptr4),y
        iny
        bne :-
        inc ptr3+1
        inc ptr4+1
        ldy #0
:       lda (ptr3),y
        sta (ptr4),y
        iny
        cpy #128
        bne :-
        sta $C004
        plp
        lda #0
        jsr setup
        lda #0
        ldy #SPRITES
:       sta valid,x
        inx
        dey
        bne :-
        rts
scanline:
        ldx row
        lda bx
        lsr
        clc
        adc row_lo,x
        sta ptr1
        lda row_hi,x
        adc _dhgr_base
        sta ptr1+1
        lda bx
        sta column
        lda width
        sta tmp2
        ldy #0
        rts
sprite_scanline:
        ldx row
        lda bx
        lsr
        clc
        adc row_lo,x
        sta ptr1
        lda row_hi,x
        adc _dhgr_base
        sta ptr1+1
        ldy #0
        rts
next_byte:
        lda column
        and #1
        beq :+
        inc ptr1
        bne :+
        inc ptr1+1
:       inc column
        inc ptr4
        bne :+
        inc ptr4+1
:       dec tmp2
        rts
_fast_restore:
        pha
        jsr _timing_scan
        pla
        php
        jsr setup
        lda valid,x
        jeq restore_done
        lda #0
        sta valid,x
        lda old_bx,x
        sta bx
        lda old_y,x
        sta row
        lda old_w,x
        sta width
        lda old_h,x
        sta rows
        lda bx
        and #1
        sta restore_aux
        eor #1
        sta restore_main
        jsr sprite_counts
        clc
        lda ptr4
        adc #16
        sta ptr3
        lda ptr4+1
        adc #0
        sta ptr3+1
        lda ptr3
        sec
        sbc restore_aux
        sta ptr3
        bcs :+
        dec ptr3+1
:       jsr sprite_scanline
        sei
restore_row:
        ldy #0
        lda main_count
        beq restore_aux_row
        lda (ptr4),y
        sta (ptr1),y
        lda main_count
        cmp #2
        bne restore_aux_row
        iny
        lda (ptr4),y
        sta (ptr1),y
restore_aux_row:
        lda aux_count
        beq restore_next_row
        sta $C005
        ldy restore_aux
        lda (ptr3),y
        sta (ptr1),y
        lda aux_count
        dec
        beq :+
        iny
        lda (ptr3),y
        sta (ptr1),y
:       sta $C004
restore_next_row:
        inc ptr3
        inc ptr3
        inc ptr4
        inc ptr4
        inc row
        dec rows
        beq restore_done
        lda row
        and #7
        beq restore_wrap
        lda ptr1+1
        clc
        adc #4
        sta ptr1+1
        bra restore_row
restore_wrap:
        jsr sprite_scanline
        bra restore_row
restore_done:
        plp
        rts
_fast_draw:
        pha
        jsr _timing_scan
        pla
        php
        jsr setup
        lda #1
        sta valid,x
        ldy _render_x
        lda xbyte,y
        sta bx
        sta old_bx,x
        tya
        clc
        adc _render_w
        tay
        lda endbyte,y
        sec
        sbc bx
        sta width
        sta old_w,x
        lda _render_y
        sta row
        sta old_y,x
        lda _render_h
        sta rows
        sta old_h,x
        jmp sprite_prepare
_fast_fill:
        php
        lda #0
        sta saving
prepare:
        lda saving
        ora _render_color
        ora _render_style
        sta zero_fill
        ldx _render_x
        lda xbyte,x
        sta bx
        lda leftm,x
        sta leftmask
        txa
        clc
        adc _render_w
        tax
        lda endbyte,x
        sec
        sbc bx
        sta width
        lda rightm,x
        sta rightmask
        lda _render_y
        sta row
        lda _render_h
        sta rows
        lda saving
        bne :+
        lda zero_fill
        jeq black_rectangle
        jmp draw_row
:
        ldx slot
        lda bx
        sta old_bx,x
        lda row
        sta old_y,x
        lda width
        sta old_w,x
        lda rows
        sta old_h,x
        jmp sprite_prepare
draw_row:
        jsr _timing_scan
        ; Style 2: the top and bottom tips occupy only the central pixel.
        lda #255
        sta tip_left
        lda _render_style
        cmp #2
        bne regular_row
        lda row
        sec
        sbc _render_y
        beq round_tip
        cmp #5
        bne regular_row
round_tip:
        ldx _render_x
        inx
        lda xbyte,x
        sta tip_left
        lda leftm,x
        sta tip_lmask
        inx
        lda endbyte,x
        sta tip_right
        lda rightm,x
        sta tip_rmask
regular_row:
        lda _render_style
        cmp #3
        beq paddle_body
        cmp #4
        beq paddle_cap
        lda _render_color
        ldx _render_style
        beq row_color
        ldx row
        cpx _render_y
        bne row_color
        lda #15
        bra row_color
paddle_body:
        lda row
        sec
        sbc _render_y
        beq paddle_white
        cmp #4
        beq paddle_shadow
        lda #14
        bra row_color
paddle_white:
        lda #15
        bra row_color
paddle_shadow:
        lda #2
        bra row_color
paddle_cap:
        lda row
        sec
        sbc _render_y
        beq paddle_black
        cmp #4
        beq paddle_black
        lda #5
        bra row_color
paddle_black:
        lda #0
row_color:
        asl
        asl
        sta colorindex
        jsr scanline
draw_byte:
        lda #$7F
        ldx column
        cpx bx
        bne :+
        and leftmask
:       ldx tmp2
        cpx #1
        bne :+
        and rightmask
:       ldx tip_left
        cpx #255
        beq mask_ready
        lda column
        cmp tip_left
        bcc empty_tip
        cmp tip_right
        bcs empty_tip
        lda #$7F
        ldx column
        cpx tip_left
        bne :+
        and tip_lmask
:       inx
        cpx tip_right
        bne mask_ready
        and tip_rmask
        jmp mask_ready
empty_tip:
        lda #0
mask_ready:
        sta tmp3
        ldx zero_fill
        bne read_background
        cmp #$7F
        bne read_background
        lda #0
        sta tmp4
        jmp write_color
read_background:
        ; Load background once; preserve partial-byte boundaries.
        lda column
        and #1
        bne read_main
        php
        sei
        jsr aux_read
        plp
        jmp saved
read_main:
        lda (ptr1),y
saved:  sta tmp1
        ldx saving
        beq :+
        sta (ptr4),y
:       lda column
        and #3
        ora colorindex
        tax
        lda patterns,x
apply_color:
        and tmp3
        sta tmp4
        lda tmp3
        eor #$7F
        and tmp1
        ora tmp4
        sta tmp4
write_color:
        lda column
        and #1
        bne :+
        php
        sei
        sta $C005
        lda tmp4
        sta (ptr1),y
        sta $C004
        plp
        jmp :++
:       lda tmp4
        sta (ptr1),y
:
        jsr next_byte
        beq :+
        jmp draw_byte
:
        inc row
        dec rows
        beq :+
        jmp draw_row
:       plp
        rts
; Small sprites: cache body and highlighted/round-tip masks, read/save
; each byte once, then write each bank as one short row transaction.
sprite_prepare:
        lda _render_color
        asl
        asl
        sta colorindex
        lda bx
        and #1
        sta restore_aux
        eor #1
        sta restore_main
        jsr sprite_counts
        lda _render_w
        cmp #3
        bne sprite_generic_masks
        lda _render_style
        cmp #2
        bne sprite_generic_masks
        lda _render_color
        cmp #15
        bne sprite_generic_masks
        ldx _render_x
        lda ball_phase,x
        tax
        ldy #0
sprite_ball_masks:
        lda ball_masks,x
        sta sprite_inverse,y
        eor #$7F
        sta sprite_ink,y
        lda ball_masks+4,x
        sta sprite_inverse+4,y
        eor #$7F
        sta sprite_ink+4,y
        inx
        iny
        cpy width
        bne sprite_ball_masks
        jmp sprite_pointer
sprite_generic_masks:
        lda _render_w
        cmp #1
        bne sprite_check_capsule
        lda _render_style
        bne sprite_uncached_masks
        lda #<small_inverse_1
        sta ptr3
        lda #>small_inverse_1
        sta ptr3+1
        ldx _render_color
        bra sprite_small_pointer
sprite_check_capsule:
        cmp #4
        bne sprite_uncached_masks
        lda _render_style
        cmp #1
        bne sprite_uncached_masks
        lda #<small_inverse_4
        sta ptr3
        lda #>small_inverse_4
        sta ptr3+1
        lda _render_color
        ora #16
        tax
sprite_small_pointer:
        lda small_ink_lo,x
        sta ptr1
        lda small_ink_hi,x
        sta ptr1+1
        ldx _render_x
        lda ball_phase,x
        lsr
        tay
        ldx #0
        lda _render_style
        beq sprite_small_plain
sprite_small_copy:
        lda (ptr3),y
        sta sprite_inverse,x
        sta sprite_inverse+4,x
        eor #$7F
        sta sprite_ink+4,x
        lda (ptr1),y
        sta sprite_ink,x
        iny
        inx
        cpx width
        bne sprite_small_copy
        jmp sprite_pointer
sprite_small_plain:
        lda (ptr3),y
        sta sprite_inverse,x
        lda (ptr1),y
        sta sprite_ink,x
        iny
        inx
        cpx width
        bne sprite_small_plain
        jmp sprite_pointer
sprite_uncached_masks:
        ldx _render_x
        lda leftm,x
        sta leftmask
        txa
        clc
        adc _render_w
        tax
        lda rightm,x
        sta rightmask

        ldx _render_x
        inx
        lda xbyte,x
        sta tip_left
        lda leftm,x
        sta tip_lmask
        inx
        lda endbyte,x
        sta tip_right
        lda rightm,x
        sta tip_rmask
        lda bx
        sta column
        stz sprite_i
sprite_masks:
        lda #$7F
        ldx sprite_i
        bne :+
        and leftmask
:       inx
        cpx width
        bne :+
        and rightmask
:       sta tmp3
        ldx sprite_i
        eor #$7F
        sta sprite_inverse,x
        lda column
        and #3
        ora colorindex
        tay
        lda patterns,y
        and tmp3
        sta sprite_ink,x
        lda _render_style
        cmp #2
        bne sprite_full_special
        lda column
        cmp tip_left
        bcc sprite_empty_special
        cmp tip_right
        bcs sprite_empty_special
        lda #$7F
        ldy column
        cpy tip_left
        bne :+
        and tip_lmask
:       iny
        cpy tip_right
        bne sprite_save_special
        and tip_rmask
        bra sprite_save_special
sprite_empty_special:
        lda #0
        bra sprite_save_special
sprite_full_special:
        lda tmp3
sprite_save_special:
        sta sprite_ink+4,x
        eor #$7F
        sta sprite_inverse+4,x
        inc column
        inc sprite_i
        lda sprite_i
        cmp width
        bcc sprite_masks
sprite_pointer:
        ; Separate auxiliary save-under pointer retains the video Y offset.
        lda ptr4
        clc
        adc #16
        sta ptr3
        lda ptr4+1
        adc #0
        sta ptr3+1
        lda ptr3
        sec
        sbc restore_aux
        sta ptr3
        bcs :+
        dec ptr3+1
:       lda _dhgr_base
        sta sprite_base
        lda bx
        lsr
        sta sprite_half
        jsr sprite_scanline
        php
        sei
        jsr shader_template
        plp
        plp
        rts

; Saved rows occupy two main bytes and two auxiliary bytes at offset 16.
; Each half of the 32-byte slot uses a fixed stride of two bytes.
sprite_counts:
        lda width
        sec
        sbc restore_main
        inc
        lsr
        sta main_count
        lda width
        sec
        sbc restore_aux
        inc
        lsr
        sta aux_count
        rts

; Fast masked black rectangles: bank loops replace generic per-byte style,
; save-under and bank setup. Partial edge bytes retain neighbouring pixels.
black_rectangle:
        clc
        lda bx
        adc width
        sta black_end
        dec
        sta black_last
black_row:
        jsr _timing_scan
        jsr scanline
        lda bx
        ora #1
        tax
        ldy #0
        cpx black_end
        bcs black_aux
black_main_loop:
        lda #$7F
        cpx bx
        bne :+
        and leftmask
:       cpx black_last
        bne :+
        and rightmask
:       cmp #$7F
        beq black_main_zero
        eor #$7F
        sta tmp3
        lda (ptr1),y
        and tmp3
        bra black_main_store
black_main_zero:
        lda #0
black_main_store:
        sta (ptr1),y
        iny
        inx
        inx
        cpx black_end
        bcc black_main_loop
black_aux:
        lda bx
        and #1
        tay
        clc
        adc bx
        tax
        cpx black_end
        bcs black_next
        php
        sei
        sta $C005
black_aux_loop:
        lda #$7F
        cpx bx
        bne :+
        and leftmask
:       cpx black_last
        bne :+
        and rightmask
:       cmp #$7F
        beq black_aux_zero
        eor #$7F
        sta tmp3
        jsr aux_read
        and tmp3
        bra black_aux_store
black_aux_zero:
        lda #0
black_aux_store:
        sta (ptr1),y
        iny
        inx
        inx
        cpx black_end
        bcc black_aux_loop
        sta $C004
        plp
black_next:
        inc row
        dec rows
        jne black_row
        plp
        rts
; Compatibility bridge: the text engine and progress hook live in the library.
.import _dhgr_small_x, _dhgr_small_y, _dhgr_small_char, _dhgr_small_string
.export _fast_text
.code
_fast_text:
        pha
        lda _render_x
        sta _dhgr_small_x
        lda _render_y
        sta _dhgr_small_y
        pla
        jmp _dhgr_small_string

; Return/update one changed HUD character, without a C scan of both lines.
.import _hud_wanted, _hud_previous
.export _hud_next
_hud_next:
        tax
        beq :+
        ldx #CB_HUD_COLS
:       ldy #0
hud_scan:
        lda _hud_wanted,y
        cmp _hud_previous,x
        bne hud_found
        inx
        iny
        cpy #CB_HUD_COLS
        bne hud_scan
        lda #255
        ldx #0
        rts
hud_found:
        sta _hud_previous,x
        tya
        ldx #0
        rts

; Cached five-row paddle. Its whole-byte footprint lies strictly between
; the border bytes and below the brick field. After sprite restoration the
; background is black: erase the previous footprint and write the packed
; cyan/silver paddle in two short bank loops per row.
.export _fast_paddle
.bss
pad_left: .res 1
pad_right: .res 1
pad_slot: .res 1
pad_cache_x: .res 1
pad_cache_w: .res 1
pad_cached: .res 1
pad_phase_slot: .res 1
pad_phase_width: .res 14
pad_inner_left: .res 1
pad_inner_right: .res 1
pad_inner_lmask: .res 1
pad_inner_rmask: .res 1
pad_begin_mask: .res 1
pad_end_mask: .res 1
pad_body_mask: .res 1
pad_count: .res 1
pad_offset: .res 1
pad_new_begin: .res 1
pad_new_end: .res 1
pad_old_end: .res 1
.segment "LOWBSS"
pad_top: .res 22
pad_middle: .res 22
pad_bottom: .res 22
pad_phase_cache: .res 14*66
.rodata
pad_phase_lo:
.repeat 14,I
.byte <(pad_phase_cache+I*66)
.endrepeat
pad_phase_hi:
.repeat 14,I
.byte >(pad_phase_cache+I*66)
.endrepeat
.code
_fast_paddle:
        lda #0
        jsr setup
        stx pad_slot
        lda _render_x
        sta pad_left
        clc
        adc _render_w
        sta pad_right
        lda valid,x
        beq pad_prepare
        lda old_x,x
        cmp pad_left
        bne pad_erase
        lda old_pixels,x
        cmp _render_w
        bne pad_erase
        rts
pad_erase:
        ldy pad_left
        lda xbyte,y
        sta pad_new_begin
        ldy pad_right
        lda endbyte,y
        sta pad_new_end
        lda old_bx,x
        clc
        adc old_w,x
        sta pad_old_end
        lda old_bx,x
        sta bx
        cmp pad_new_begin
        bcs pad_erase_right
        lda pad_new_begin
        cmp pad_old_end
        bcc :+
        lda pad_old_end
:       sec
        sbc bx
        sta width
        jsr pad_clear
pad_erase_right:
        ldx pad_slot
        lda pad_new_end
        cmp pad_old_end
        bcs pad_prepare
        cmp old_bx,x
        bcs :+
        lda old_bx,x
:       sta bx
        lda pad_old_end
        sec
        sbc bx
        sta width
        jsr pad_clear
pad_prepare:
        ldx pad_left
        lda xbyte,x
        sta bx
        ldx pad_right
        lda endbyte,x
        sec
        sbc bx
        sta width
        ldx pad_left
        lda ball_phase,x
        lsr
        lsr
        lsr
        tax
        lda _render_w
        cmp #27
        bcc :+
        txa
        clc
        adc #7
        tax
:       stx pad_phase_slot
        lda pad_phase_lo,x
        sta ptr4
        lda pad_phase_hi,x
        sta ptr4+1
        lda pad_phase_width,x
        cmp _render_w
        bne pad_build
        jmp pad_ready
pad_build:
        ldx pad_left
        lda leftm,x
        sta pad_begin_mask
        inx
        lda xbyte,x
        sta pad_inner_left
        lda leftm,x
        sta pad_inner_lmask
        ldx pad_right
        lda rightm,x
        sta pad_end_mask
        dex
        lda endbyte,x
        sta pad_inner_right
        lda rightm,x
        sta pad_inner_rmask

        lda pad_left
        sta pad_cache_x
        lda _render_w
        sta pad_cache_w
        lda #1
        sta pad_cached
        lda bx
        sta column
        stz pad_offset
pad_pattern:
        lda #$7F
        ldx column
        cpx bx
        bne :+
        and pad_begin_mask
:       txa
        sec
        sbc bx
        inc
        cmp width
        bne :+
        lda pad_end_mask
        bra :++
:       lda #$7F
:       sta tmp3
        ; Combine the first/last full masks (minimum game width is 18).
        ldx column
        cpx bx
        bne :+
        lda tmp3
        and pad_begin_mask
        sta tmp3
:       lda #$7F
        cpx pad_inner_left
        bcc pad_empty_body
        cpx pad_inner_right
        bcs pad_empty_body
        cpx pad_inner_left
        bne :+
        and pad_inner_lmask
:       inx
        cpx pad_inner_right
        bne pad_body
        and pad_inner_rmask
        bra pad_body
pad_empty_body:
        lda #0
pad_body:
        sta pad_body_mask
        ldy pad_offset
        sta pad_top,y
        lda column
        and #3
        tax
        lda patterns+8,x
        and pad_body_mask
        sta pad_bottom,y
        lda patterns+56,x
        and pad_body_mask
        sta tmp4
        lda tmp3
        eor pad_body_mask
        and patterns+20,x
        ora tmp4
        sta pad_middle,y
        inc column
        inc pad_offset
        lda pad_offset
        cmp width
        jcc pad_pattern
        ldx pad_phase_slot
        lda _render_w
        sta pad_phase_width,x
        ; Cache each row in main/aux planes, eleven bytes per bank.
.repeat 3,R
        lda bx
        and #1
        eor #1
        tax
        ldy #R*22
:       lda pad_top+R*22,x
        sta (ptr4),y
        iny
        inx
        inx
        cpx width
        bcc :-
        lda bx
        and #1
        tax
        ldy #R*22+11
:       lda pad_top+R*22,x
        sta (ptr4),y
        iny
        inx
        inx
        cpx width
        bcc :-
.endrepeat
pad_ready:
        lda bx
        and #1
        sta restore_aux
        clc
        adc width
        lsr
        tax
        lda pad_copy_lo,x
        sta pad_main_call+1
        lda pad_copy_hi,x
        sta pad_main_call+2
        lda restore_aux
        eor #1
        clc
        adc width
        lsr
        tax
        lda pad_copy_lo,x
        sta pad_aux_call+1
        lda pad_copy_hi,x
        sta pad_aux_call+2
        jsr pad_blit
        ldx pad_slot
        lda #1
        sta valid,x
        lda pad_left
        sta old_x,x
        lda _render_w
        sta old_pixels,x
        lda bx
        sta old_bx,x
        lda width
        sta old_w,x
        rts
.rodata
pad_copy_lo:
.repeat 12,N
.byte <(pad_pixels+(11-N)*5)
.endrepeat
pad_copy_hi:
.repeat 12,N
.byte >(pad_pixels+(11-N)*5)
.endrepeat
.code
pad_pixels:
.repeat 11
        lda (ptr3),y
        sta (ptr1),y
        iny
.endrepeat
        rts
pad_blit:
        lda #CB_PAD_Y
        sta row
        lda #5
        sta rows
pad_row:
        jsr _timing_scan
        lda ptr4
        ldx ptr4+1
        ldy row
        cpy #CB_PAD_Y
        beq pad_source_ready
        lda #22
        cpy #CB_PAD_Y+4
        bne :+
        lda #44
:       clc
        adc ptr4
        bcc :+
        inx
:
pad_source_ready:
        sta ptr3
        stx ptr3+1
        jsr sprite_scanline
        ldy #0
pad_main_call:
        jsr pad_pixels
        lda #11
        sec
        sbc restore_aux
        clc
        adc ptr3
        sta ptr3
        bcc :+
        inc ptr3+1
:       ldy restore_aux
        php
        sei
        sta $C005
pad_aux_call:
        jsr pad_pixels
        sta $C004
        plp
        inc row
        dec rows
        bne pad_row
        rts

 ; Clear whole-byte fringes outside the new paddle footprint.
pad_clear:
        lda bx
        and #1
        sta restore_aux
        clc
        adc width
        lsr
        tax
        lda pad_zero_lo,x
        sta pad_clear_main+1
        lda pad_zero_hi,x
        sta pad_clear_main+2
        lda restore_aux
        eor #1
        clc
        adc width
        lsr
        tax
        lda pad_zero_lo,x
        sta pad_clear_aux+1
        lda pad_zero_hi,x
        sta pad_clear_aux+2
        lda #CB_PAD_Y
        sta row
        lda #5
        sta rows
pad_clear_row:
        jsr _timing_scan
        jsr sprite_scanline
        lda #0
pad_clear_main:
        jsr pad_zero_pixels
        ldy restore_aux
        php
        sei
        sta $C005
pad_clear_aux:
        jsr pad_zero_pixels
        sta $C004
        plp
        inc row
        dec rows
        bne pad_clear_row
        rts
.rodata
pad_zero_lo:
.repeat 12,N
.byte <(pad_zero_pixels+(11-N)*3)
.endrepeat
pad_zero_hi:
.repeat 12,N
.byte >(pad_zero_pixels+(11-N)*3)
.endrepeat
.code
pad_zero_pixels:
.repeat 11
        sta (ptr1),y
        iny
.endrepeat
        rts

; Copy the complete displayed frame to the hidden page, in both banks.
; This replaces drawing a new board twice. Aux executes from ZP; IRQs are
; masked for one 256-byte copy only, then the native mouse can run again.
.import _dhgr_display
.export _fast_clone_page
.zeropage
copy_aux: .res 17
.bss
copy_pages: .res 1
clone_source: .res 1
clone_dest: .res 1
.rodata
copy_template:
        sta $C003
copy_bytes:
        lda (ptr1),y
        sta (ptr3),y
        iny
        bne copy_bytes
        sta $C002
        sta $C004
        rts
.code
_fast_clone_page:
        ldx #16
:       lda copy_template,x
        sta copy_aux,x
        dex
        bpl :-
        lda _dhgr_base
        sta ptr3+1
        eor #$60
        sta ptr1+1
        stz ptr1
        stz ptr3
        lda #32
        sta copy_pages
copy_main_page:
        ldy #0
:       lda (ptr1),y
        sta (ptr3),y
        iny
        bne :-
        inc ptr1+1
        inc ptr3+1
        dec copy_pages
        bne copy_main_page
        lda _dhgr_base
        sta ptr3+1
        eor #$60
        sta ptr1+1
        lda #32
        sta copy_pages
copy_aux_page:
        php
        sei
        ldy #0
        sta $C005
        jsr copy_aux
        plp
        inc ptr1+1
        inc ptr3+1
        dec copy_pages
        bne copy_aux_page
        lda #0
        ldx #SPRITES
        ldy _dhgr_display
        cpy #1
        beq :+
        lda #SPRITES
        ldx #0
:       sta clone_source
        stx clone_dest
        tay
        lda under_lo,y
        sta ptr1
        lda under_hi,y
        sta ptr1+1
        lda under_lo,x
        sta ptr3
        lda under_hi,x
        sta ptr3+1
        ldy #0
:       lda (ptr1),y
        sta (ptr3),y
        iny
        bne :-
        inc ptr1+1
        inc ptr3+1
        ldy #SPRITES*SLOT_SIZE-257
:       lda (ptr1),y
        sta (ptr3),y
        dey
        cpy #255
        bne :-
        ldx clone_source
        ldy clone_dest
        lda #SPRITES
        sta copy_pages
clone_metadata:
        lda valid,x
        sta valid,y
        lda old_x,x
        sta old_x,y
        lda old_pixels,x
        sta old_pixels,y
        lda old_bx,x
        sta old_bx,y
        lda old_y,x
        sta old_y,y
        lda old_w,x
        sta old_w,y
        lda old_h,x
        sta old_h,y
        inx
        iny
        dec copy_pages
        bne clone_metadata
        rts

; Actor dispatch has fixed sprite IDs and fixed sizes; keep it off the C stack.
.export _draw_actors
.importzp _ball_x, _ball_y, _ball_live
.import _pad_x, _pad_width, _round_live
.import _extra_ball, _capsule, _cap_x, _cap_y
.import _shot_live, _shot_x, _shot_y
.import _particle_life, _particle_x, _particle_y, _particle_color
.bss
actor_index: .res 1
.rodata
actor_capsule_colors: .byte 13,9,11,1,3,6,7
.code
_draw_actors:
        lda _pad_x
        sta _render_x
        lda _pad_width
        sta _render_w
        lda #CB_PAD_Y
        sta _render_y
        lda #5
        sta _render_h
        lda #14
        sta _render_color
        lda #3
        sta _render_style
        jsr _fast_paddle
        lda #3
        sta _render_w
        lda #6
        sta _render_h
        lda #15
        sta _render_color
        lda #2
        sta _render_style
        lda _ball_live
        bne @primary
        lda _round_live
        bne @extra
@primary:
        lda _ball_x
        sta _render_x
        lda _ball_y
        sta _render_y
        lda #1
        jsr _fast_draw
@extra:
.repeat 2,I
        lda _extra_ball+I*9+2
        beq :+
        lda _extra_ball+I*9
        sta _render_x
        lda _extra_ball+I*9+1
        sta _render_y
        lda #I+2
        jsr _fast_draw
:
.endrepeat
        ldx _capsule
        beq @shots
        lda _cap_x
        sta _render_x
        lda _cap_y
        sta _render_y
        lda actor_capsule_colors,x
        sta _render_color
        lda #4
        sta _render_w
        lda #1
        sta _render_style
        lda #4
        jsr _fast_draw
@shots:
        lda #1
        sta _render_w
        lda #4
        sta _render_h
        stz _render_style
        lda #13
        sta _render_color
.repeat 2,I
        lda _shot_live+I
        beq :+
        lda _shot_x+I
        sta _render_x
        lda _shot_y+I
        sta _render_y
        lda #I+5
        jsr _fast_draw
:
.endrepeat
        lda #2
        sta _render_h
        stz actor_index
@particle:
        ldx actor_index
        lda _particle_life,x
        beq @next
        lda _particle_x,x
        sta _render_x
        lda _particle_y,x
        sta _render_y
        lda _particle_color,x
        sta _render_color
        txa
        clc
        adc #7
        jsr _fast_draw
@next: inc actor_index
        lda actor_index
        cmp #4
        bcc @particle
        rts

; A HUD character uses fixed columns and white ink; avoid C multiply/setup.
.export _hud_glyph
.import _page_id
.bss
hud_glyph_text: .res 2
.rodata
hud_column_x:
.repeat CB_HUD_COLS,I
.byte 5+I*5
.endrepeat
.code
_hud_glyph:
        lda _page_id
        jsr _hud_next
        cmp #255
        beq @done
        tay
        lda hud_column_x,y
        sta _dhgr_small_x
        lda #CB_HUD_Y
        sta _dhgr_small_y
        lda _hud_wanted,y
        jmp _dhgr_small_char
@done: rts
