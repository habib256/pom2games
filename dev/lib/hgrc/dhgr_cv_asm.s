; VERHILLE Arnaud — GPL-3.0. DHGR compositor canvas painters (dhgr.h,
; "Flicker-free sprite compositor"). The canvas holds the current piece:
; one byte per colour pixel, the colour's DHGR nibble ((c>>1)|(c<<3))&15,
; rows of dhgr_cv_w bytes, dhgr_cv_h rows, from colour pixel dhgr_cv_x0,
; row dhgr_cv_y0. A piece holds at most 255 bytes: an offset is one index
; register, cv_rowoff[r] = r * w (cv_begin, per piece). Rectangles are
; filled by an unrolled `sta canvas+k,y` sequence (5 cycles a byte), in
; strips of 8 columns; its operands hold the canvas address, patched by
; dhgr_cv_patch (dhgr_spr_asm.s). A RECTS shape lying wholly inside the
; piece is painted without clipping (its rectangles must lie inside its
; w x h). Main RAM only: no bank switch, no IRQ masking. A/X/Y, ptr1-ptr4,
; tmp1 destroyed; non-reentrant, never from an IRQ.
; DHGR_SPR_CODE_SEGMENT=1: code and tables in segment DHGRSPRCODE.
.export _dhgr_cv_paint, _dhgr_cv_solid, dhgr_cv_fill, cv_seq, cv_nibble, cv_begin
.export _dhgr_cv_buf, _dhgr_cv_x0, _dhgr_cv_y0, _dhgr_cv_w, _dhgr_cv_h
.export _dhgr_cv_x1, _dhgr_cv_y1, _dhgr_cv_shape, _dhgr_cv_sx, _dhgr_cv_sy
.export _dhgr_cv_flags, _dhgr_cv_pal
.export cv_rx, cv_ry, cv_rw, cv_rh, cv_nib, cv_rowoff
.export cv_sw, cv_sh, cv_count
.if .defined(DHGR_SPR_RECTS_ONLY)
.if !DHGR_SPR_RECTS_ONLY
.import dhgr_cv_bitmap
.endif
.else
.import dhgr_cv_bitmap
.endif
.importzp ptr1, ptr2, ptr3, ptr4, tmp1

ROWS = 36                       ; 255 / 7
fw = ptr3                       ; f_run: columns left, first byte, rows
col = ptr3+1
rows = ptr4

.bss
_dhgr_cv_buf:   .res 2          ; the canvas
_dhgr_cv_x0:    .res 1          ; piece left colour pixel (7 * group)
_dhgr_cv_y0:    .res 1          ; piece top row
_dhgr_cv_w:     .res 1          ; piece width in pixels = canvas stride
_dhgr_cv_h:     .res 1          ; rows
_dhgr_cv_x1:    .res 1          ; x0 + w (exclusive, <= 140)
_dhgr_cv_y1:    .res 1          ; y0 + h (exclusive, <= 192)
_dhgr_cv_shape: .res 2          ; painter input: dhgr_shape_t *
_dhgr_cv_sx:    .res 1
_dhgr_cv_sy:    .res 1
_dhgr_cv_flags: .res 1          ; DHGR_SPR_MIRROR in bit 0
_dhgr_cv_pal:   .res 2          ; four colours for 16..19
cv_rowoff: .res ROWS            ; r * w
cv_rx:  .res 1                  ; dhgr_cv_fill input rectangle
cv_ry:  .res 1
cv_rw:  .res 1
cv_rh:  .res 1
cv_nib: .res 1                  ; nibble 0..15
mirror: .res 1                  ; bit 7: mirrored
xin:    .res 1                  ; bit 7: the shape is inside horizontally
cbase:  .res 1                  ; unclipped shape: its column, row in the piece
rbase:  .res 1
cv_sw:
sw:     .res 1                  ; shape width (mirror)
cv_sh:
sh:     .res 1
cv_count:
count:  .res 1

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; The piece is set (dhgr_cv_x0..y1): row offsets, the fill's row advance.
cv_begin:
        lda _dhgr_cv_w
        sta f_adv+1
        lda #0
        tay
:       sta cv_rowoff,y
        clc
        adc _dhgr_cv_w
        iny
        cpy _dhgr_cv_h
        bne :-
        rts

; void __fastcall__ dhgr_cv_solid(colour): the whole piece.
_dhgr_cv_solid:
        jsr cv_nibble
        sta f_nib+1
        lda _dhgr_cv_w
        sta fw
        lda _dhgr_cv_h
        sta rows
        lda #0
        sta col
        beq f_run

fill_none:
        rts
; cv_rx/ry/rw/rh in colour pixels, cv_nib: fill, clipped to the piece.
dhgr_cv_fill:
        lda cv_nib
        sta f_nib+1
        lda cv_rx
fill_a: tax                     ; X = left, A = right (exclusive)
        clc
        adc cv_rw
        bcs @xcap
        cmp _dhgr_cv_x1
        bcc @xe
@xcap:  lda _dhgr_cv_x1
@xe:    cpx _dhgr_cv_x0
        bcs @xs
        ldx _dhgr_cv_x0
@xs:    stx tmp1
        sec
        sbc tmp1
        beq fill_none
        bcc fill_none
        sta fw
        txa
        sbc _dhgr_cv_x0         ; (C = 1) the column in the piece
        sta col
fill_y: ldx cv_ry               ; rows, the same way (fw, col set)
        txa
        clc
        adc cv_rh
        bcs @ycap
        cmp _dhgr_cv_y1
        bcc @ye
@ycap:  lda _dhgr_cv_y1
@ye:    cpx _dhgr_cv_y0
        bcs @ys
        ldx _dhgr_cv_y0
@ys:    stx tmp1
        sec
        sbc tmp1
        beq fill_none
        bcc fill_none
        sta rows
        txa
        sbc _dhgr_cv_y0         ; (C = 1)
        tax
        lda col
        clc
        adc cv_rowoff,x
        sta col
        ; fall through

; Fill rows x fw bytes from canvas offset col with the nibble in f_nib+1.
f_run:  lda fw                  ; this strip: min(fw, 8) columns
        cmp #9
        bcc :+
        lda #8
:       tax
        lda jlo-1,x
        sta f_go+1
        lda jhi-1,x
        sta f_go+2
        ldy col
        ldx rows
f_nib:  lda #0
f_go:   jmp cv_seq
cv_seq:
.repeat 8, J
        sta $FF00 + 7 - J,y     ; (patched: canvas + 7 - J)
.endrepeat
        tya
        clc
f_adv:  adc #0
        tay
        dex
        bne f_nib
        lda fw
        sec
        sbc #8
        beq f_end
        bcc f_end
        sta fw
        lda col
        adc #7                  ; (C = 1: + 8)
        sta col
        bne f_run
f_end:  rts

; Colour (A, low nibble) -> DHGR nibble: rotate right by one bit.
cv_nibble:
        and #15
        lsr a
        bcc :+
        ora #8
:       rts

; void dhgr_cv_paint(void): dhgr_cv_shape at dhgr_cv_sx, dhgr_cv_sy,
; mirrored if dhgr_cv_flags bit 0, colours 16..19 from dhgr_cv_pal.
_dhgr_cv_paint:
        lda _dhgr_cv_shape
        sta ptr2
        lda _dhgr_cv_shape+1
        sta ptr2+1
        ldy #5
        lda (ptr2),y            ; data
        tax
        dey
        lda (ptr2),y
        pha
        dey
        lda (ptr2),y            ; n
        sta count
        dey
        lda (ptr2),y            ; h
        sta sh
        dey
        lda (ptr2),y            ; w
        sta sw
        dey
        lda (ptr2),y            ; kind
        stx ptr2+1
        tax
        pla
        sta ptr2
        txa
        beq rects
.if .defined(DHGR_SPR_RECTS_ONLY)
.if DHGR_SPR_RECTS_ONLY
        rts
.else
        jmp dhgr_cv_bitmap
.endif
.else
        jmp dhgr_cv_bitmap
.endif
; RECTS: count x {x, y, w, h, colour}.
rects:  lda count
        beq r_done
        lda _dhgr_cv_flags
        ror a
        ror a
        sta mirror              ; bit 7 = DHGR_SPR_MIRROR
        lda _dhgr_cv_pal
        sta ptr1
        lda _dhgr_cv_pal+1
        sta ptr1+1
        lda #0
        sta xin
        lda _dhgr_cv_sx         ; the shape inside the piece: no clipping
        sec
        sbc _dhgr_cv_x0
        bcc r_slow
        sta cbase
        clc
        adc sw
        bcs r_slow
        cmp _dhgr_cv_w
        beq :+
        bcs r_slow
:       lda #$80                ; inside horizontally
        sta xin
        lda _dhgr_cv_sy
        sec
        sbc _dhgr_cv_y0
        bcc r_slow
        sta rbase
        clc
        adc sh
        bcs r_slow
        cmp _dhgr_cv_h
        beq r_fast
        bcc r_fast
r_slow: jmp slow
r_done: rts

r_fast: ldy #4
        lda (ptr2),y            ; colour
        cmp #16
        bcc :+
        and #3
        tay
        lda (ptr1),y
:       and #15
        lsr a
        bcc :+
        ora #8
:       sta f_nib+1
        ldy #3
        lda (ptr2),y            ; h
        beq @next
        sta rows
        dey
        lda (ptr2),y            ; w
        beq @next
        sta fw
        dey
        lda (ptr2),y            ; y
        clc
        adc rbase
        tax
        dey
        lda (ptr2),y            ; x
        bit mirror
        bpl :+
        eor #$FF                ; mirrored: sw - x - w
        sec
        adc sw
        sec
        sbc fw
:       clc
        adc cbase
        adc cv_rowoff,x
        sta col
        jsr f_run
@next:  lda ptr2
        clc
        adc #5
        sta ptr2
        bcc :+
        inc ptr2+1
:       dec count
        bne r_fast
        rts

slow:   ldy #4
        lda (ptr2),y            ; colour
        cmp #16
        bcc :+
        and #3
        tay
        lda (ptr1),y
:       jsr cv_nibble
        sta f_nib+1
        ldy #3
        lda (ptr2),y
        sta cv_rh
        dey
        lda (ptr2),y
        sta cv_rw
        dey
        lda (ptr2),y            ; y
        clc
        adc _dhgr_cv_sy
        bcs @skip               ; past row 255
        sta cv_ry
        dey
        lda (ptr2),y            ; x
        bit mirror
        bpl @x
        eor #$FF                ; mirrored: sw - x - w
        sec
        adc sw
        sec
        sbc cv_rw
@x:     bit xin
        bpl @clipx
        clc                     ; inside horizontally: rows clipped only
        adc cbase
        sta col
        lda cv_rw
        beq @skip
        sta fw
        jsr fill_y
        jmp @skip
@clipx: clc
        adc _dhgr_cv_sx
        bcs @skip               ; past column 255
        jsr fill_a
@skip:  lda ptr2
        clc
        adc #5
        sta ptr2
        bcc :+
        inc ptr2+1
:       dec count
        bne slow
        rts

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if !DHGR_SPR_CODE_SEGMENT
.rodata
.endif
.else
.rodata
.endif
jlo:                            ; f_run's entry for 1..8 columns
.repeat 8, W
        .byte <(cv_seq + 3 * (7 - W))
.endrepeat
jhi:
.repeat 8, W
        .byte >(cv_seq + 3 * (7 - W))
.endrepeat
