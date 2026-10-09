; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; TMS pattern -> clipped HGR byte masks, then saved-background composition.
.importzp tx_lo, tx_hi, ty_lo, spr_size, spr_xoff, spr_yoff
.importzp shape_pat_lo, pen_color, em_color, pix_y, pix_mask
.import hgr_lo, hgr_hi, hgr_col, hgr_mask, pen_hi_tbl
.export hgr_draw_emote, emote_init, emote_hide, emote_plot_background
.include "hgr_sprite_update.asm"
.zeropage
e_x: .res 2
.bss
e_masks: .res 192
e_mask: .res 32
e_col: .res 32
e_dim: .res 1
e_width: .res 1
e_y0: .res 1
e_top: .res 1
e_row: .res 1
e_bit: .res 1
e_src: .res 1
e_index: .res 1
e_off: .res 1
e_value: .res 1
e_saved_y: .res 1
e_last_x: .res 2
e_last_y: .res 1
e_last_shape: .res 2
e_last_size: .res 1
e_last_color: .res 1
e_last_pen: .res 1
.code
emote_init = ds_init
emote_hide = ds_hide
hgr_draw_emote:
        lda ds_active
        beq emote_build
        lda tx_lo
        cmp e_last_x
        bne emote_build
        lda tx_hi
        cmp e_last_x+1
        bne emote_build
        lda ty_lo
        cmp e_last_y
        bne emote_build
        lda shape_pat_lo
        cmp e_last_shape
        bne emote_build
        lda shape_pat_lo+1
        cmp e_last_shape+1
        bne emote_build
        lda spr_size
        cmp e_last_size
        bne emote_build
        lda em_color
        cmp e_last_color
        bne emote_build
        lda pen_color
        cmp e_last_pen
        bne emote_build
emote_unchanged:
        rts                       ; repeated identical frame: no HGR writes
emote_build:
        lda #0
        ldx #0
@clear: sta e_masks,x
        inx
        cpx #192
        bne @clear
        ; X is signed during clipping; expose only valid table indexes.
        lda spr_xoff
        asl
        sta e_value
        lda tx_lo
        sec
        sbc e_value
        sta e_x
        lda tx_hi
        sbc #0
        sta e_x+1
        lda em_color
        sta ds_color
        beq @origin
        ldx pen_color
        lda em_par_tbl,x
        clc
        adc e_x
        sta e_x
        bcc @origin
        inc e_x+1
@origin:
        ldx pen_color
        lda pen_hi_tbl,x
        sta ds_palette
        lda #8
        ldx spr_size
        cpx #32
        bne @size
        lda #16
@size:  sta e_dim
        asl
        sta e_width
        lda #39
        sta ds_col
        lda #0
        sta ds_w
        ldx #0
@map:   lda #0
        sta e_mask,x
        lda e_x+1
        beq @low
        cmp #1
        bne @next
        ldy e_x
        cpy #24
        bcs @next
        lda hgr_mask+256,y
        sta e_mask,x
        lda hgr_col+256,y
        jmp @column
@low:   ldy e_x
        lda hgr_mask,y
        sta e_mask,x
        lda hgr_col,y
@column:
        sta e_col,x
        cmp ds_col
        bcs @max
        sta ds_col
@max:   cmp ds_w
        bcc @next
        sta ds_w
@next:  inc e_x
        bne @advance
        inc e_x+1
@advance:
        inx
        cpx e_width
        bcc @map
        lda ds_w
        sec
        sbc ds_col
        clc
        adc #1
        sta ds_w
        ldx #0
@relative:
        lda e_col,x
        sec
        sbc ds_col
        sta e_col,x
        inx
        cpx e_width
        bcc @relative
        lda #0
        sta e_row
        sta e_off
@row:   ldy e_row
        lda (shape_pat_lo),y
        sta e_src
        lda #0
        sta e_bit
@bit:   asl e_src
        bcc @unlit
        lda e_bit
        asl
        tax
        jsr emote_mask
        lda em_color
        bne @unlit
        inx
        jsr emote_mask
@unlit:
        inc e_bit
        lda e_bit
        cmp #8
        bne @second
        lda e_dim
        cmp #8
        beq @row_done
        lda e_row
        clc
        adc #16
        tay
        lda (shape_pat_lo),y
        sta e_src
@second:
        lda e_bit
        cmp e_dim
        bcc @bit
@row_done:
        ; Duplicate all six bytes in one pass (2x vertical scaling).
        ldx e_off
        ldy #6
@copy:  lda e_masks,x
        sta e_masks+6,x
        inx
        dey
        bne @copy
        lda e_off
        clc
        adc #12
        sta e_off
        inc e_row
        lda e_row
        cmp e_dim
        bcc @row
        lda #<e_masks
        sta ds_data
        lda #>e_masks
        sta ds_data+1
        lda spr_yoff
        asl
        sta e_value
        lda #0
        sta e_top
        lda ty_lo
        sec
        sbc e_value
        bcs @positive
        inc e_top
@positive:
        sta e_y0
        sta ds_y
        lda e_width
        sta ds_h
        lda e_top
        beq @bottom
        lda e_y0
        ; Top crop: advance the source pointer by six bytes per hidden row.
        eor #$ff
        clc
        adc #1
        sta e_value
        lda ds_h
        sec
        sbc e_value
        sta ds_h
        lda #0
        sta ds_y
@crop:  lda ds_data
        clc
        adc #6
        sta ds_data
        bcc @cropped
        inc ds_data+1
@cropped:
        dec e_value
        bne @crop
@bottom:
        lda #192
        sec
        sbc ds_y
        cmp ds_h
        bcs @present
        sta ds_h
@present:
        lda tx_lo
        sta e_last_x
        lda tx_hi
        sta e_last_x+1
        lda ty_lo
        sta e_last_y
        lda shape_pat_lo
        sta e_last_shape
        lda shape_pat_lo+1
        sta e_last_shape+1
        lda spr_size
        sta e_last_size
        lda em_color
        sta e_last_color
        lda pen_color
        sta e_last_pen
        jmp ds_present
; X = scaled source column. Skip clipped pixels before indexing row storage.
emote_mask:
        lda e_mask,x
        beq @done
        sta e_value
        lda e_col,x
        clc
        adc e_off
        tay
        lda e_masks,y
        ora e_value
        sta e_masks,y
@done:  rts
em_par_tbl:
        .byte 0,0,1,1,0,0,1,1,0,1,0,1,0,1,0,0

; Optional OR-plot hook: update the saved background under a visible sprite
; and keep its foreground on screen. Input/output A = composed screen byte,
; Y = screen column; Y is preserved. XOR drawing never calls this hook.
emote_plot_background:
        ldx ds_active
        bne @active
        rts
@active:
        sta e_value
        sty e_saved_y
        lda pix_y
        sec
        sbc ds_oldy
        bcc @outside
        cmp ds_oldh
        bcs @outside
        asl
        sta e_index
        asl
        clc
        adc e_index
        sta e_index
        tya
        sec
        sbc ds_oldcol
        bcc @outside
        cmp ds_oldw
        bcs @outside
        clc
        adc e_index
        tay
        lda (ds_oldptr),y
        ora pix_mask
        and #$7f
        ldx pen_color
        ora pen_hi_tbl,x
        sta (ds_oldptr),y
        jsr emote_foreground
        sta e_value
@outside:
        ldy e_saved_y
        lda e_value
        rts
emote_foreground:
        ; ds_data addresses the current clipped mask until the next present.
        sta ds_bg
        lda (ds_data),y
        sta ds_bits
        ora ds_bg
        ldx ds_bits
        beq @done
        ldx ds_color
        beq @done
        and #$7f
        ora ds_palette
@done:  rts
