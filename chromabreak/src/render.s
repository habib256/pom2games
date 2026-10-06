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
; Row kinds of four bytes: 0 normal, 1 tip/highlight; capsules use 0..5.
sprite_inverse: .res 24
sprite_ink: .res 24
.code
; Instructions have identical addresses in main and auxiliary RAM.
; Masks and loop state stay in zero page while RAMRD switches banks.
; Save-under writes use main RAM, pixel writes use auxiliary RAM.
; Colour bytes always keep bit 7 set (Chat Mauve mixed DHGR: 140 colour);
; preserve masks carry bit 7, so drawing never clears it. Only text may.
shader_template:
shader_row:
        ldx restore_main
        lda _render_style
        beq shader_pixels
        cmp #5
        bne shader_kind
        ; Capsule: every row has its own masks, four bytes per row.
        lda row
        sec
        sbc _render_y
        asl
        asl
        ora restore_main
        tax
        bra shader_pixels
shader_kind:
        lda row
        cmp _render_y
        beq shader_tip
        ; Styles 2 (round), 6 and 14 (enemies) use the special masks on the last
        ; row too; style 1 (bolt head) only on the first.
        lda _render_style
        and #2
        beq shader_pixels
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
        ; Inside a group of eight scanlines only the high byte moves (+$04).
        lda row
        and #7
        beq shader_group
        lda ptr1+1
        clc
        adc #4
        sta ptr1+1
        jmp shader_row
shader_group:
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
SPRITES=13
SLOT_SIZE=32
valid: .res SPRITES*2
; Per-page sprite metadata and save-under live below the video pages.
.segment "LOWBSS"
.align 32
under: .res SPRITES*2*SLOT_SIZE
old_x: .res SPRITES*2
old_pixels: .res SPRITES*2
old_bx: .res SPRITES*2
old_y: .res SPRITES*2
old_w: .res SPRITES*2
old_h: .res SPRITES*2
.rodata
.include "dhgr_layout.inc"
.import _dhgr_row_lo, _dhgr_row_hi, _dhgr_color_byte
row_lo = _dhgr_row_lo
row_hi = _dhgr_row_hi
xbyte = _dhgr_color_byte
.import _dhgr_end_byte, _dhgr_left_mask, _dhgr_right_mask
endbyte = _dhgr_end_byte
leftm = _dhgr_left_mask
rightm = _dhgr_right_mask
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
.byte 128,224,255,255,143,254,255,255
.byte 143,128,252,255,255,225,255,255
.byte 129,192,255,255,159,252,255,255
.byte 159,128,248,255,255,195,255,255
.byte 131,128,255,255,191,248,255,255
.byte 191,128,240,255,255,135,255,255
.byte 135,128,254,255,255,240,255,255
small_inverse_1:
.byte 240,255,255,255,143,254,255,255,225,255,255,255,159,252,255,255,195,255,255,255,191,248,255,255,135,255,255,255
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
small_ink_lo:
.repeat 16,C
.byte <(small_ink_1+C*28)
.endrepeat
small_ink_hi:
.repeat 16,C
.byte >(small_ink_1+C*28)
.endrepeat
.include "sprite_tables.inc"
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
        ; An empty slot costs no timing scan or interrupt-state work.
        jsr setup
        lda valid,x
        bne :+
        rts
:       jsr _timing_scan
        php
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
        lda _render_style
        cmp #7
        jeq bg_rectangle
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
        lda #$80
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
        eor #$FF
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
        lda _render_style
        cmp #5
        jeq capsule_draw
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
        cmp #4
        beq sprite_round4
        cmp #1
        jne sprite_uncached_masks
        lda _render_style
        cmp #2
        jcs sprite_uncached_masks
        lda #<small_inverse_1
        sta ptr3
        lda #>small_inverse_1
        sta ptr3+1
        ldx _render_color
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
        jeq sprite_small_plain
        ; Style 1 (laser bolt): the first row is white over the same mask.
sprite_small_head:
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
        bne sprite_small_head
        jmp sprite_pointer
sprite_round4:
        lda _render_style
        and #4
        jne sprite_spool
        lda _render_style
        cmp #2
        jne sprite_uncached_masks
        ldx _render_x
        lda ball_phase,x
        tax
        lda _render_color
        cmp #16
        bne sprite_round4_plain
        ; Colour 16: the shaded piercing ball, ink from red_ball_ink.
        lda _render_x
:       cmp #28
        bcc :+
        sbc #28
        bra :-
:       asl
        asl
        asl
        sta tmp4
        ldy #0
sprite_red_byte:
        lda round4_masks,x
        sta sprite_inverse,y
        lda round4_masks+4,x
        sta sprite_inverse+4,y
        phx
        ldx tmp4
        lda red_ball_ink,x
        sta sprite_ink,y
        lda red_ball_ink+4,x
        sta sprite_ink+4,y
        inc tmp4
        plx
        inx
        iny
        cpy width
        bne sprite_red_byte
        jmp sprite_pointer
sprite_round4_plain:
        ldy #0
sprite_round4_byte:
        tya
        clc
        adc bx
        and #3
        ora colorindex
        phx
        tax
        lda patterns,x
        plx
        sta tip_ink
        lda round4_masks,x
        sta sprite_inverse,y
        eor #$7F
        and tip_ink
        sta sprite_ink,y
        lda round4_masks+4,x
        sta sprite_inverse+4,y
        eor #$7F
        and tip_ink
        sta sprite_ink+4,y
        inx
        iny
        cpy width
        bne sprite_round4_byte
        jmp sprite_pointer
; Enemies. Style 6, a spool: full-width bars in the enemy colour on the
; first and last rows, a narrow white core between them (unlike any ball).
; Style 14, a TIE fighter: wings (pixels 0 and 3) in the enemy colour on
; every row, a white core (pixels 1-2) between the end rows.
sprite_spool:
        ldx _render_x
        lda ball_phase,x
        tax
        ldy #0
sprite_spool_byte:
        tya
        clc
        adc bx
        and #3
        ora colorindex
        phx
        tax
        lda patterns,x
        plx
        sta tip_ink
        lda _render_style
        cmp #6
        bne sprite_tie
        lda TABLES_BASE+T_SPOOL,x
        sta sprite_inverse,y
        eor #$7F
        sta sprite_ink,y
        lda TABLES_BASE+T_SPOOL+4,x
        sta sprite_inverse+4,y
        eor #$7F
        and tip_ink
        sta sprite_ink+4,y
        bra sprite_spool_next
sprite_tie:
        ; Wings = whole sprite minus the core: keep the core and the outside.
        lda round4_masks+4,x
        eor #$FF
        ora round4_masks,x
        sta sprite_inverse+4,y
        eor #$7F
        and tip_ink
        sta sprite_ink+4,y
        sta tip_ink
        lda round4_masks+4,x
        eor #$7F
        ora tip_ink
        sta sprite_ink,y
        lda round4_masks,x
        sta sprite_inverse,y
sprite_spool_next:
        inx
        iny
        cpy width
        bne sprite_spool_byte
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
        eor #$FF
        sta sprite_inverse,x
        lda column
        and #3
        ora colorindex
        tay
        lda patterns,y
        sta tip_ink
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
        bne :+
        and tip_rmask
        ; Round tips keep the sprite colour (red piercing ball, enemies).
:       sta tmp4
        and tip_ink
        sta sprite_ink+4,x
        lda tmp4
        bra sprite_save_inverse
sprite_empty_special:
        lda #0
        bra sprite_save_special
sprite_full_special:
        lda tmp3
sprite_save_special:
        sta sprite_ink+4,x
sprite_save_inverse:
        eor #$FF
        sta sprite_inverse+4,x
        inc column
        inc sprite_i
        lda sprite_i
        cmp width
        bcc sprite_masks
sprite_pointer:
        jsr sprite_setup
        php
        sei
        jsr shader_template
        plp
        plp
        rts
sprite_setup:
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
        jmp sprite_scanline

; Bonus capsule, style 5: a 5x6 block, a lit white top over the bonus letter
; in black. Six distinct rows exceed the shader's two row kinds, so style 5
; gives each row its own four mask bytes in zero page. They depend only on
; the column and the kind: rows 2..5 stay there between frames (no other
; sprite uses them), rows 0..1 are restored from cap_save.
.bss
cap_save: .res 16
cap_key_x: .res 1
cap_key_kind: .res 1
cap_full: .res 4
cap_top: .res 4
cap_pb: .res 4
.zeropage
cap_ptr: .res 2
cap_row: .res 1
cap_g: .res 1
cap_n: .res 1
cap_t: .res 1
.rodata
; Body colors by kind 1..6: ENLARGE SLOW CATCH DISRUPT LASER PIERCE.
cap_body: .byte 0,9,11,1,3,6,7
; Arkanoid letters E S C D L P, 3x5, bit 0 = left.
cap_letters:
.byte 7,1,3,1,7
.byte 7,1,7,4,7
.byte 7,1,1,1,7
.byte 3,5,5,5,3
.byte 1,1,1,1,7
.byte 7,5,7,1,1
.import _dhgr_dot_phase, _dhgr_dot_masks
.code
capsule_draw:
        lda _render_color
        ldx _render_x
        cpx cap_key_x
        bne cap_build
        cmp cap_key_kind
        jeq cap_ready
cap_build:
        sta cap_key_kind
        stx cap_key_x
        ; Pixel-to-dot masks for this dot phase: _dhgr_dot_masks+phase*64.
        lda _dhgr_dot_phase,x
        stz cap_ptr+1
        ldy #6
:       asl
        rol cap_ptr+1
        dey
        bne :-
        clc
        adc #<_dhgr_dot_masks
        sta cap_ptr
        lda cap_ptr+1
        adc #>_dhgr_dot_masks
        sta cap_ptr+1
        ldy #15*4
        ldx #0
:       lda (cap_ptr),y
        sta cap_full,x
        lda #0
        sta cap_top,x
        iny
        inx
        cpx #4
        bne :-
        ldy #14*4
        ldx #0
:       lda (cap_ptr),y
        sta cap_top,x
        iny
        inx
        cpx #4
        bne :-
        ; Fifth pixel: dots 16..19 after the phase, i.e. byte 2 or 3.
        ldx cap_key_x
        lda _dhgr_dot_phase,x
        clc
        adc #2
        ldx #2
        cmp #7
        bcc :+
        sbc #7
        inx
:       tay
        stz cap_t
        lda #$0F
        cpy #0
        beq :++
:       asl
        rol cap_t
        dey
        bne :-
:       pha
        and #$7F
        ora cap_full,x
        sta cap_full,x
        pla
        asl
        lda cap_t
        rol
        beq :+
        ora cap_full+1,x
        sta cap_full+1,x
:       ; Body color byte at each sprite byte column.
        ldx cap_key_kind
        lda cap_body,x
        asl
        asl
        sta cap_g
        ldx #0
:       txa
        clc
        adc bx
        and #3
        ora cap_g
        tay
        lda patterns,y
        sta cap_pb,x
        inx
        cpx #4
        bne :-
        ; Row 0: white top over the three middle pixels.
        ldx #0
:       lda cap_top,x
        sta sprite_ink,x
        eor #$FF
        sta sprite_inverse,x
        inx
        cpx #4
        bne :-
        ; Rows 1..5: the body color, with the letter left black.
        lda cap_key_kind
        dec
        sta cap_t
        asl
        asl
        adc cap_t
        sta cap_t
        lda #5
        sta cap_row
cap_letter_row:
        ldy cap_t
        lda cap_letters,y
        asl
        asl
        asl
        sta cap_g
        lda #4
        sta cap_n
cap_letter_byte:
        ldy cap_g
        lda (cap_ptr),y
        inc cap_g
        pha
        txa
        and #3
        tay
        pla
        eor cap_full,y
        and cap_pb,y
        sta sprite_ink,x
        lda cap_full,y
        eor #$FF
        sta sprite_inverse,x
        inx
        dec cap_n
        bne cap_letter_byte
        inc cap_t
        dec cap_row
        bne cap_letter_row
        ; Keep rows 0..1, which other sprites overwrite every frame.
        ldx #3
:       lda sprite_inverse,x
        sta cap_save,x
        lda sprite_inverse+4,x
        sta cap_save+4,x
        lda sprite_ink,x
        sta cap_save+8,x
        lda sprite_ink+4,x
        sta cap_save+12,x
        dex
        bpl :-
        jmp sprite_pointer
cap_ready:
        ldx #3
:       lda cap_save,x
        sta sprite_inverse,x
        lda cap_save+4,x
        sta sprite_inverse+4,x
        lda cap_save+8,x
        sta sprite_ink,x
        lda cap_save+12,x
        sta sprite_ink+4,x
        dex
        bpl :-
        jmp sprite_pointer

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

; Style 7: erase a rectangle back to the level background (a destroyed
; tile). Partial edge bytes keep their neighbours; bit 7 is kept.
bg_rectangle:
        lda _bg_on
        jeq black_rectangle
        jsr bg_setup
bg_rect_row:
        jsr _timing_scan
        jsr bg_tile_row
        jsr scanline
bg_rect_byte:
        lda #$7F
        ldx column
        cpx bx
        bne :+
        and leftmask
:       ldx tmp2
        cpx #1
        bne :+
        and rightmask
:       sta tmp3
        lda column
        and #3
        tay
        lda (ptr3),y
        and tmp3
        sta tmp4
        lda tmp3
        eor #$FF
        sta tmp3
        ldy #0
        lda column
        and #1
        bne bg_rect_main
        php
        sei
        jsr aux_read
        and tmp3
        ora tmp4
        sta $C005
        sta (ptr1),y
        sta $C004
        plp
        bra bg_rect_next
bg_rect_main:
        lda (ptr1),y
        and tmp3
        ora tmp4
        sta (ptr1),y
bg_rect_next:
        jsr next_byte
        bne bg_rect_byte
        inc row
        dec rows
        bne bg_rect_row
        plp
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
        eor #$FF
        sta tmp3
        lda (ptr1),y
        and tmp3
        bra black_main_store
black_main_zero:
        lda #$80
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
        eor #$FF
        sta tmp3
        jsr aux_read
        and tmp3
        bra black_aux_store
black_aux_zero:
        lda #$80
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
; Beautiful Boot text: render_x counts 7-dot units, render_y is the top row.
.import _fine_x, _fine_y, _fine_char, _fine_text
.export _fast_text
.code
_fast_text:
        pha
        lda _render_x
        sta _fine_x
        lda _render_y
        sta _fine_y
        pla
        jmp _fine_text

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

; Cached five-row paddle at pad_y. Its whole-byte footprint lies strictly
; between the border bytes, and the game keeps it two pixels clear of any
; tile. After sprite restoration the background is black: erase the previous
; footprint (all of it after a vertical move) and write the packed
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
pad_clear_y: .res 1
tip_ink: .res 1
pad_first_row: .res 1
pad_last_row: .res 1
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
        jeq pad_prepare
        lda old_y,x
        cmp _render_y
        bne pad_moved
        sta pad_clear_y
        lda old_x,x
        cmp pad_left
        bne pad_erase
        lda old_pixels,x
        cmp _render_w
        bne pad_erase
        rts
pad_moved:
        ; A vertical move erases the whole previous footprint on this page.
        sta pad_clear_y
        lda old_bx,x
        sta bx
        lda old_w,x
        sta width
        jsr pad_clear
        jmp pad_prepare
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
        ora #$80
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
        ora #$80
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
        lda _render_y
        sta old_y,x
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
        lda _render_y
        sta row
        sta pad_first_row
        clc
        adc #4
        sta pad_last_row
        lda #5
        sta rows
pad_row:
        jsr _timing_scan
        lda ptr4
        ldx ptr4+1
        ldy row
        cpy pad_first_row
        beq pad_source_ready
        lda #22
        cpy pad_last_row
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
        lda pad_clear_y
        sta row
        lda #5
        sta rows
        ; Five short rows: one blank scan covers the whole strip.
        jsr _timing_scan
pad_clear_row:
        jsr sprite_scanline
        lda #$80
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

; Clear the draw page to black with bit 7 set: colour cells for the Chat
; Mauve mixed mode (composite video ignores bit 7 in DHGR).
.export _screen_clear
.import _dhgr_pattern, _dhgr_clear_asm
_screen_clear:
        stz _bg_on
        lda #$80
        sta _dhgr_pattern
        sta _dhgr_pattern+1
        sta _dhgr_pattern+2
        sta _dhgr_pattern+3
        jmp _dhgr_clear_asm

; Level backgrounds (bg_tiles in the $0800 image): bg_on = 0 for none, else
; tile 1..6. They cover the field above CB_BG_END, where the paddle never
; goes, so only save-under sprites move over them.
.include "tables.inc"
.export _bg_on, _bg_fill
.bss
_bg_on: .res 1
bg_base: .res 2
.rodata
bg_black: .byte $80,$80,$80,$80
.code
; ptr3 = the tile row for `row` (black from CB_BG_END on).
bg_tile_row:
        lda row
        cmp #CB_BG_END
        bcc :+
        lda #<bg_black
        sta ptr3
        lda #>bg_black
        sta ptr3+1
        rts
:       and #7
        asl
        asl
        clc
        adc bg_base
        sta ptr3
        lda bg_base+1
        adc #0
        sta ptr3+1
        rts
bg_setup:
        lda _bg_on
        dec
        asl
        asl
        asl
        asl
        asl
        clc
        adc #<(TABLES_BASE+T_BG)
        sta bg_base
        lda #>(TABLES_BASE+T_BG)
        adc #0
        sta bg_base+1
        rts
; Fill the field rows CB_FIELD_TOP..CB_BG_END-1 of the draw page, byte
; columns 1..78 (the frame is drawn over the edges afterwards).
_bg_fill:
        lda _bg_on
        beq @done
        jsr bg_setup
        lda #CB_FIELD_TOP
        sta row
@row:   ldx row
        lda row_lo,x
        sta ptr1
        lda row_hi,x
        clc
        adc _dhgr_base
        sta ptr1+1
        jsr bg_tile_row
        ; MAIN offsets 0..38 are columns 1, 3, ... 77: tile bytes 1 and 3.
        ldy #1
        lda (ptr3),y
        sta tmp1
        ldy #3
        lda (ptr3),y
        sta tmp2
        ldy #0
:       lda tmp1
        sta (ptr1),y
        iny
        lda tmp2
        sta (ptr1),y
        iny
        cpy #38
        bcc :-
        lda tmp1
        sta (ptr1),y
        ; AUX offsets 1..39 are columns 2, 4, ... 78: tile bytes 2 and 0.
        ldy #2
        lda (ptr3),y
        sta tmp1
        lda (ptr3)
        sta tmp2
        php
        sei
        sta $C005
        ldy #1
:       lda tmp1
        sta (ptr1),y
        iny
        lda tmp2
        sta (ptr1),y
        iny
        cpy #39
        bcc :-
        lda tmp1
        sta (ptr1),y
        sta $C004
        plp
        inc row
        lda row
        cmp #CB_BG_END
        bne @row
@done:  rts

; RGB mode latch of Le Chat Mauve Feline, the //c RGB adapter and Video-7
; cards (US 4,631,692): each $C05E->$C05F edge samples 80COL. A=1: off then
; on = mixed DHGR, where a byte with bit 7 clear shows seven 560-dot mono
; dots and bit 7 set four-dot colour; A=0: on, on = 140 colour (power-on).
; Those cards have nothing to read, so the game always selects mixed mode:
; elsewhere (composite, Eve) the picture is unchanged. On the //c the pair
; is AN3 only with IOUDIS on ($C07E); otherwise it sets the mouse Y edges,
; so IOUDIS is turned on around the sequence and then restored.
.export _video_mixed
_video_mixed:
        php
        sei
        tax
        ldy #0
        lda $FBC0
        bne :+
        lda $C07E
        tay
        sta $C07E
:       txa
        beq :+
        sta $C00C
        bra :++
:       sta $C00D
:       sta $C05E
        sta $C05F
        sta $C00D
        sta $C05E
        sta $C05F
        sta $C05E
        tya
        bmi :+
        lda $FBC0
        bne :+
        sta $C07F
:       plp
        rts

.include "levels.inc"
; Level bank in AUX (startup.s): copy board A, 48 packed bytes, and its
; name, right-aligned on 10 cells, into main RAM. IRQs stay masked while
; AUX is read: an interrupt there would fetch from AUX.
.export _level_fetch, _level_packed, _level_name
.bss
_level_packed: .res LEVEL_BYTES
_level_name: .res 11
.code
_level_fetch:
        sta tmp1
        asl
        adc tmp1
        stz ptr1+1
        asl
        rol ptr1+1
        asl
        rol ptr1+1
        asl
        rol ptr1+1
        asl
        rol ptr1+1
        clc
        adc #<LEVELS_AUX
        sta ptr1
        lda ptr1+1
        adc #>LEVELS_AUX
        sta ptr1+1
        php
        sei
        ldy #LEVEL_BYTES-1
:       jsr aux_read
        sta _level_packed,y
        dey
        bpl :-
        ; Name: LEVEL_NAMES + A*10.
        lda tmp1
        asl
        sta tmp2
        stz ptr1+1
        asl
        rol ptr1+1
        asl
        rol ptr1+1
        clc
        adc tmp2
        bcc :+
        inc ptr1+1
:       clc
        adc #<LEVEL_NAMES
        sta ptr1
        lda ptr1+1
        adc #>LEVEL_NAMES
        sta ptr1+1
        ldy #9
:       jsr aux_read
        sta _level_name,y
        dey
        bpl :-
        plp
        stz _level_name+10
        rts

; Restore every actor sprite of the draw page, newest first (12..1).
.export _restore_actors
_restore_actors:
        lda #12
@next:  pha
        jsr _fast_restore
        pla
        dec
        bne @next
        rts

; Actor dispatch has fixed sprite IDs and fixed sizes; keep it off the C stack.
.export _draw_actors
.importzp _ball_x, _ball_y, _ball_live, _pad_y, _effect
.import _pad_x, _pad_width, _round_live
.import _extra_ball, _capsule, _cap_x, _cap_y
.import _shot_live, _shot_x, _shot_y
.import _particle_life, _particle_x, _particle_y, _particle_color
.import _enemy_live, _enemy_x, _enemy_y, _enemy_color
.bss
actor_index: .res 1
ball_lift: .res 1
.code
_draw_actors:
        lda _pad_x
        sta _render_x
        lda _pad_width
        sta _render_w
        lda _pad_y
        sta _render_y
        lda #5
        sta _render_h
        lda #14
        sta _render_color
        lda #3
        sta _render_style
        jsr _fast_paddle
        ; White 3x6 balls; with the P bonus, red 4x7 balls drawn one line
        ; higher (the collision silhouette stays the 3x6 one).
        lda #3
        sta _render_w
        lda #6
        sta _render_h
        lda #15
        sta _render_color
        stz ball_lift
        lda _effect
        cmp #6
        bne :+
        lda #4
        sta _render_w
        lda #7
        sta _render_h
        lda #16
        sta _render_color
        inc ball_lift
:       lda #2
        sta _render_style
        lda _ball_live
        bne @primary
        lda _round_live
        bne @extra
@primary:
        lda _ball_x
        sta _render_x
        lda _ball_y
        sec
        sbc ball_lift
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
        sec
        sbc ball_lift
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
        stx _render_color
        lda #5
        sta _render_w
        sta _render_style
        lda #6
        sta _render_h
        lda #4
        jsr _fast_draw
@shots:
        ; Laser bolts (1x4: white head, yellow body). With the L bonus an
        ; idle bolt slot shows its red 1x3 cannon on the paddle end the bolt
        ; leaves from.
        lda _shot_live
        beq @cannon0
        lda _shot_x
        sta _render_x
        lda _shot_y
        jsr bolt
        bra @draw0
@cannon0:
        lda _effect
        cmp #5
        bne @shot1
        lda _pad_x
        inc
        sta _render_x
        jsr cannon
@draw0: lda #5
        jsr _fast_draw
@shot1: lda _shot_live+1
        beq @cannon1
        lda _shot_x+1
        sta _render_x
        lda _shot_y+1
        jsr bolt
        bra @draw1
@cannon1:
        lda _effect
        cmp #5
        bne @shards
        lda _pad_x
        clc
        adc _pad_width
        sec
        sbc #2
        sta _render_x
        jsr cannon
@draw1: lda #6
        jsr _fast_draw
@shards:
        ; 1x2 shards in their tile colour (bolts left style 1).
        lda #1
        sta _render_w
        stz _render_style
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
        ; Enemies, sprites 11 and 12: a 4x6 spool (style 6), a TIE (style 10).
        lda #4
        sta _render_w
        lda #6
        sta _render_h
.repeat 2,I
        lda _enemy_live+I
        beq :+
        lda #6+8*I
        sta _render_style
        lda _enemy_x+I
        sta _render_x
        lda _enemy_y+I
        sta _render_y
        lda _enemy_color+I
        sta _render_color
        lda #11+I
        jsr _fast_draw
:
.endrepeat
        rts

; Bolt (A = y) and cannon (on the paddle top) sprite parameters.
bolt:   sta _render_y
        lda #4
        sta _render_h
        lda #1
        sta _render_w
        sta _render_style
        lda #13
        sta _render_color
        rts
cannon: lda #1
        sta _render_w
        stz _render_style
        lda _pad_y
        sec
        sbc #3
        sta _render_y
        lda #3
        sta _render_h
        lda #1
        sta _render_color
        rts

; A HUD character uses fixed columns and white ink; avoid C multiply/setup.
.export _hud_glyph
.import _page_id, _hud_stale
.bss
hud_glyph_text: .res 2
.rodata
hud_column_x:
.repeat CB_HUD_COLS,I
.byte CB_HUD_LEFT+I*2
.endrepeat
.code
_hud_glyph:
        ldx _page_id
        lda _hud_stale,x
        beq @done
        txa
        jsr _hud_next
        cmp #255
        beq @clean
        tay
        lda hud_column_x,y
        sta _fine_x
        lda #CB_HUD_Y
        sta _fine_y
        lda _hud_wanted,y
        jmp _fine_char
@clean: ldx _page_id
        stz _hud_stale,x
@done: rts
