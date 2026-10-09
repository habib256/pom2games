; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; One transparent sprite, stride 6, max 6x32 bytes, through hgr_lo/hi.
; ds_col/y/w/h are clipped destination geometry; ds_data points to stride-6
; rows of foreground bits (bit 7 clear). ds_color=0 preserves palette, 1
; applies ds_palette to bytes containing foreground. Call ds_init once.
; ds_present composes old/new overlap directly: no separate erase pass.
; ds_hide restores the saved background. Buffers live outside HGR pages.
; Geometry must fit the page (col+w<=40, y+h<=192); h=0 hides.
; External draws must update saved background, or hide before drawing.
; Main RAM, D=0, non-reentrant, A/X/Y and private scratch destroyed.
.ifndef _HGR_SPRITE_UPDATE_LOADED_
_HGR_SPRITE_UPDATE_LOADED_ = 1
.zeropage
ds_data: .res 2
ds_oldptr: .res 2
ds_newptr: .res 2
ds_frame: .res 2
.bss
ds_col: .res 1
ds_y: .res 1
ds_w: .res 1
ds_h: .res 1
ds_color: .res 1
ds_palette: .res 1
ds_active: .res 1
ds_oldcol: .res 1
ds_oldy: .res 1
ds_oldw: .res 1
ds_oldh: .res 1
ds_row: .res 1
ds_cursor: .res 1
ds_end: .res 1
ds_i: .res 1
ds_j: .res 1
ds_base: .res 1
ds_overlap: .res 1
ds_bg: .res 1
ds_bits: .res 1
ds_seed_valid: .res 1
ds_seed_index: .res 1
ds_seed_bg: .res 1
ds_under0: .res 192
ds_under1: .res 192
.code
ds_init:
        lda #0
        sta ds_active
        lda #<ds_under0
        sta ds_oldptr
        lda #>ds_under0
        sta ds_oldptr+1
        lda #<ds_under1
        sta ds_newptr
        lda #>ds_under1
        sta ds_newptr+1
        rts
ds_hide:
        lda #0
        sta ds_h
        jmp ds_present
ds_row_address:
        ldy ds_row
        lda hgr_lo,y
        sta ds_frame
        lda hgr_hi,y
        sta ds_frame+1
        rts
; A=background, Y=new source index. Store the background before composition.
ds_compose:
        sta (ds_newptr),y
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
; An unchanged byte rectangle (flap, colour change, sub-byte movement) can
; compose directly without the general intersection/restoration walk.
ds_present:
        lda #0
        sta ds_seed_valid
        lda ds_active
        beq ds_general
        lda ds_h
        beq ds_general
        jsr ds_seed
        lda ds_active
        beq ds_general
        lda ds_col
        cmp ds_oldcol
        bne ds_general
        lda ds_y
        cmp ds_oldy
        bne ds_general
        lda ds_w
        cmp ds_oldw
        bne ds_general
        lda ds_h
        cmp ds_oldh
        bne ds_general
        jmp ds_replace
ds_general:
        lda ds_h
        bne @new
        jmp ds_restore_old
@new:   lda #0
        sta ds_j
        lda ds_y
        sta ds_row
ds_new_row:
        jsr ds_row_address
        lda #0
        sta ds_overlap
        lda ds_active
        beq @no_overlap
        lda ds_row
        sec
        sbc ds_oldy
        bcc @no_overlap
        cmp ds_oldh
        bcs @no_overlap
        asl
        sta ds_base
        asl
        clc
        adc ds_base
        sta ds_base
        inc ds_overlap
@no_overlap:
        lda ds_col
        sta ds_cursor
        clc
        adc ds_w
        sta ds_end
ds_new_byte:
        lda ds_overlap
        beq @screen
        lda ds_cursor
        sec
        sbc ds_oldcol
        bcc @screen
        cmp ds_oldw
        bcs @screen
        clc
        adc ds_base
        tay
        lda (ds_oldptr),y
        jmp @compose
@screen:
        lda ds_seed_valid
        beq @read_frame
        lda ds_j
        cmp ds_seed_index
        bne @read_frame
        lda ds_seed_bg
        jmp @compose
@read_frame:
        ldy ds_cursor
        lda (ds_frame),y
@compose:
        ldy ds_j
        jsr ds_compose
        ldy ds_cursor
        sta (ds_frame),y
        inc ds_j
        inc ds_cursor
        lda ds_cursor
        cmp ds_end
        bcc ds_new_byte
        lda ds_j
        clc
        adc #6
        sec
        sbc ds_w
        sta ds_j
        inc ds_row
        lda ds_row
        sec
        sbc ds_y
        cmp ds_h
        bcs @rows_done
        jmp ds_new_row
@rows_done:
; New image is already visible before restoring old-exclusive bytes.
ds_restore_old:
        lda ds_active
        bne @old
        jmp ds_commit
@old:   lda #0
        sta ds_i
        lda ds_oldy
        sta ds_row
ds_old_row:
        jsr ds_row_address
        lda #0
        sta ds_overlap
        lda ds_row
        sec
        sbc ds_y
        bcc @no_overlap
        cmp ds_h
        bcs @no_overlap
        inc ds_overlap
@no_overlap:
        lda ds_oldcol
        sta ds_cursor
        clc
        adc ds_oldw
        sta ds_end
ds_old_byte:
        lda ds_overlap
        beq @restore
        lda ds_cursor
        sec
        sbc ds_col
        bcc @restore
        cmp ds_w
        bcc @next
@restore:
        ldy ds_i
        lda (ds_oldptr),y
        ldy ds_cursor
        sta (ds_frame),y
@next:  inc ds_i
        inc ds_cursor
        lda ds_cursor
        cmp ds_end
        bcc ds_old_byte
        lda ds_i
        clc
        adc #6
        sec
        sbc ds_oldw
        sta ds_i
        inc ds_row
        lda ds_row
        sec
        sbc ds_oldy
        cmp ds_oldh
        bcc ds_old_row
ds_commit:
        lda ds_h
        bne @visible
        sta ds_active
        rts
@visible:
        lda ds_col
        sta ds_oldcol
        lda ds_y
        sta ds_oldy
        lda ds_w
        sta ds_oldw
        lda ds_h
        sta ds_oldh
        lda #1
        sta ds_active
        ; Swap under-buffers; no copy and no changes to the framebuffer.
        ldx ds_oldptr
        lda ds_newptr
        sta ds_oldptr
        stx ds_newptr
        ldx ds_oldptr+1
        lda ds_newptr+1
        sta ds_oldptr+1
        stx ds_newptr+1
        rts
; Keep at least one new foreground byte visible before any old bits are
; removed, even when two frames have no lit rows in common. Preserve its
; original screen byte for the non-overlap path's background capture.
ds_seed:
        lda #0
        sta ds_j
        lda ds_y
        sta ds_row
@row:   jsr ds_row_address
        lda ds_col
        sta ds_cursor
        clc
        adc ds_w
        sta ds_end
@byte:  ldy ds_j
        lda (ds_data),y
        bne @found
        inc ds_j
        inc ds_cursor
        lda ds_cursor
        cmp ds_end
        bcc @byte
        lda ds_j
        clc
        adc #6
        sec
        sbc ds_w
        sta ds_j
        inc ds_row
        lda ds_row
        sec
        sbc ds_y
        cmp ds_h
        bcc @row
        rts                       ; intentionally empty frame
@found:
        sta ds_bits
        lda ds_j
        sta ds_seed_index
        inc ds_seed_valid
        ldy ds_cursor
        lda (ds_frame),y
        sta ds_seed_bg
        ora ds_bits
        ldx ds_color
        beq @write
        and #$7f
        ora ds_palette
@write: sta (ds_frame),y
ds_seed_visible:
        rts
ds_replace:
        lda ds_col
        clc
        adc ds_w
        sta ds_end
        lda ds_y
        sta ds_row
        ldx #0
@row:   jsr ds_row_address
        lda ds_col
        sta ds_cursor
@byte:  txa
        tay
        lda (ds_oldptr),y
        sta (ds_newptr),y
        sta ds_bg
        lda (ds_data),y
        beq @background
        ora ds_bg
        ldy ds_color
        beq @write
        and #$7f
        ora ds_palette
        jmp @write
@background:
        lda ds_bg
@write: ldy ds_cursor
        sta (ds_frame),y
        inx
        inc ds_cursor
        lda ds_cursor
        cmp ds_end
        bcc @byte
        txa
        clc
        adc #6
        sec
        sbc ds_w
        tax
        inc ds_row
        lda ds_row
        sec
        sbc ds_y
        cmp ds_h
        bcc @row
        jmp ds_commit
.endif
