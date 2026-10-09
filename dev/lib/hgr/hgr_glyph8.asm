; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Eight HGR-order glyph rows at hg_src, through hgr_lo/hi. Main RAM, D=0.
; hgr_glyph8_store: byte column hg_col (0..39), top row hg_y. STORE one
; raw byte/row; no cursor advance. Source, coordinates preserved; A/X/Y lost.
; hgr_glyph8_or / hgr_glyph8_cell: X=hg_x (16 bits, 0..279), Y=hg_y.
; OR sets glyph pixels only. CELL replaces an eight-pixel cell, clearing its
; palette bit like the legacy compact UI emitter; pixels outside stay intact.
; Both include all eight source bits, clip right/bottom, and do not wrap.
; Optional HG_COLOR_TABLE[hg_color] replaces OR palette bits only where lit.
; HG_OR_HOOK receives/returns A=screen byte, Y=byte column; preserves Y and
; hg_* scratch. Optional HG_HOOK_Y/MASK receive the current row/foreground.
; Define HG_STORE_ONLY to omit unaligned entries and their scratch. hg_*
; HG_STORE_UNCLIPPED removes STORE checks: caller guarantees col<40,y<=184.
; aliases may reuse caller memory. Non-reentrant. No video switches touched.
.ifndef _HGR_GLYPH8_LOADED_
_HGR_GLYPH8_LOADED_ = 1
.zeropage
.ifndef hg_src
hg_src: .res 2
.endif
.ifndef hg_ptr
hg_ptr: .res 2
.endif
.ifndef HG_STORE_ONLY
.ifndef hg_x
hg_x: .res 2
.endif
.endif
.bss
.ifndef hg_col
hg_col: .res 1
.endif
.ifndef hg_y
hg_y: .res 1
.endif
.ifndef hg_row
hg_row: .res 1
.endif
.ifndef HG_STORE_ONLY
hg_shift: .res 1
hg_keep_lo: .res 1
hg_keep_hi: .res 1
hg_mode: .res 1
.ifndef hg_lo
hg_lo: .res 1
.endif
.ifndef hg_hi
hg_hi: .res 1
.endif
hg_bits: .res 1
hg_end: .res 1
.ifdef HG_COLOR_TABLE
.ifndef hg_color
hg_color: .res 1
.endif
.endif
.endif
.code
hgr_glyph8_store:
.ifndef HG_STORE_UNCLIPPED
        lda hg_col
        cmp #40
        bcs @done
.endif
        ldx #0
@row:   txa
        clc
        adc hg_y
.ifndef HG_STORE_UNCLIPPED
        bcs @done
        cmp #192
        bcs @done
.endif
        tay
        lda hgr_lo,y
        sta hg_ptr
        lda hgr_hi,y
        sta hg_ptr+1
        txa
        tay
        lda (hg_src),y
        ldy hg_col
        sta (hg_ptr),y
        inx
        cpx #8
        bcc @row
@done:  rts
.ifndef HG_STORE_ONLY
hgr_glyph8_or:
        lda #0
        beq hg_start
hgr_glyph8_cell:
        lda #1
hg_start:
        sta hg_mode
        lda hg_y
        cmp #192
        bcs @invalid
        cmp #185
        bcc @eight
        lda #192
        sec
        sbc hg_y
        bne @end
@eight: lda #8
@end:   sta hg_end
        lda hg_x+1
        beq @low
        cmp #1
        bne @invalid
        lda hg_x
        cmp #24
        bcs @invalid
        clc
        adc #4                    ; 256 = 36*7 + 4
        ldx #36
        bne @divide
@low:   lda hg_x
        ldx #0
@divide:
        cmp #7
        bcc @column
        sbc #7
        inx
        bne @divide
@column:
        sta hg_shift
        stx hg_col
        tax
        lda hg_cell_keep_lo,x
        sta hg_keep_lo
        lda hg_cell_keep_hi,x
        sta hg_keep_hi
        lda #0
        sta hg_row
        ldx hg_mode
        bne hg_cell_loop
        jmp hg_row_loop
@invalid: rts
hg_cell_loop:
        ldy hg_row
        lda (hg_src),y
        ldx #0
        stx hg_hi
        ldx hg_shift
        beq @shifted
@shift: asl a
        rol hg_hi
        dex
        bne @shift
@shifted:
        sta hg_lo
        lda hg_row
        clc
        adc hg_y
        tax
        lda hgr_lo,x
        sta hg_ptr
        lda hgr_hi,x
        sta hg_ptr+1
        ldy hg_col
        lda (hg_ptr),y
        and hg_keep_lo
        ora hg_lo
        and #$7f
        sta (hg_ptr),y
        iny
        cpy #40
        bcs @next
        asl hg_lo
        lda hg_hi
        rol a
        sta hg_hi
        lda (hg_ptr),y
        and hg_keep_hi
        ora hg_hi
        sta (hg_ptr),y
@next: inc hg_row
        lda hg_row
        cmp hg_end
        bcc hg_cell_loop
        rts
hg_row_loop:
        lda hg_row
        clc
        adc hg_y
.ifdef HG_HOOK_Y
        sta HG_HOOK_Y
.endif
        tay
        lda hgr_lo,y
        sta hg_ptr
        lda hgr_hi,y
        sta hg_ptr+1
        ldy hg_row
        lda (hg_src),y
        beq @next                 ; an empty OR row leaves the screen intact
        ldx #0
        stx hg_hi
        ldx hg_shift
        beq @shifted
@shift: asl a
        rol hg_hi
        dex
        bne @shift
@shifted:
        sta hg_lo
        and #$7f
        ldy hg_col
        jsr hg_or_byte
        asl hg_lo                 ; carry = span bit 7
        lda hg_hi
        rol a
        and #$7f
        iny
        cpy #40
        bcs @next
        jsr hg_or_byte
@next:  inc hg_row
        lda hg_row
        cmp hg_end
        bcs @off
        jmp hg_row_loop
@off:   rts
hg_or_byte:
        ; Blank spans must leave the framebuffer and its palette unchanged.
        cmp #0
        beq @done
        sta hg_bits
.ifdef HG_HOOK_MASK
        sta HG_HOOK_MASK
.endif
        ora (hg_ptr),y
.ifdef HG_COLOR_TABLE
        and #$7f
        ldx hg_color
        ora HG_COLOR_TABLE,x
.endif
.ifdef HG_OR_HOOK
        jsr HG_OR_HOOK
.endif
        sta (hg_ptr),y
@done:  rts
; Keep bits outside the 8-pixel cell. Bit 7 is cleared by CELL, while OR
; preserves the byte palette unless HG_COLOR_TABLE explicitly replaces it.
hg_cell_keep_lo: .byte $00,$01,$03,$07,$0f,$1f,$3f
hg_cell_keep_hi: .byte $7e,$7c,$78,$70,$60,$40,$00
.endif
.endif
