; VERHILLE Arnaud — GPL-3.0. DHGR compositor bitmap painters (dhgr.h):
; CHUNKY (w x h colours, DHGR_CLEAR transparent, mirrored on request) and
; TILE (w x h DHGR_NIB nibbles, opaque, copied straight). Called by
; dhgr_cv_paint with the shape's data in ptr2; not linked when the library
; is built with DHGR_SPR_RECTS_ONLY=1. A/X/Y, ptr1, ptr2, tmp1 destroyed.
.export dhgr_cv_bitmap
.import _dhgr_cv_x0, _dhgr_cv_y0, _dhgr_cv_x1, _dhgr_cv_y1, _dhgr_cv_sx, _dhgr_cv_sy, _dhgr_cv_w
.import _dhgr_cv_flags, _dhgr_cv_buf, cv_rowoff
.import cv_sw, cv_sh, cv_count
.importzp ptr1, ptr2, tmp1
sw = cv_sw
sh = cv_sh
count = cv_count

.bss
cs:     .res 1                  ; clip: first column, count, row index
cnt:    .res 1
ridx:   .res 1
kind:   .res 1

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; CHUNKY (1): sw x sh colours, DHGR_CLEAR ($80) transparent, mirror.
; TILE (2): sw x sh DHGR nibbles, opaque, no mirror: a straight copy.
bm_none:
        rts
dhgr_cv_bitmap:
        sta kind
        lda _dhgr_cv_sx         ; columns cs .. cs + cnt - 1
        clc
        adc sw
        bcs @xcap
        cmp _dhgr_cv_x1
        bcc @xend
@xcap:  lda _dhgr_cv_x1
@xend:  sta cnt
        lda _dhgr_cv_sx
        cmp _dhgr_cv_x0
        bcs :+
        lda _dhgr_cv_x0
:       sta cs
        lda cnt
        sec
        sbc cs
        beq bm_none
        bcc bm_none
        sta cnt
        lda _dhgr_cv_sy         ; rows: first ridx = top - y0, count
        clc
        adc sh
        bcs @ycap
        cmp _dhgr_cv_y1
        bcc @yend
@ycap:  lda _dhgr_cv_y1
@yend:  sta count
        ldx _dhgr_cv_sy
        cpx _dhgr_cv_y0
        bcs :+
        ldx _dhgr_cv_y0
:       stx tmp1
        sec
        sbc tmp1
        beq bm_none
        bcc bm_none
        sta count
        txa
        sec
        sbc _dhgr_cv_y0
        sta ridx
        txa                     ; skip top - sy source rows
        sec
        sbc _dhgr_cv_sy
        tax
        beq @col
@skip:  lda ptr2
        clc
        adc sw
        sta ptr2
        bcc :+
        inc ptr2+1
:       dex
        bne @skip
@col:   lda cs                  ; first source column
        sec
        sbc _dhgr_cv_sx
        sta tmp1
        lda kind
        cmp #1
        beq @chunky
        lda tmp1                ; TILE: source and canvas both from column cs
        clc
        adc ptr2
        sta ptr2
        bcc :+
        inc ptr2+1
:       lda cnt                 ; enter the 8-copy sequence at (cnt - 1) % 8 + 1
        sta @tw+1
        sec
        sbc #1
        and #7
        eor #7
        sta tmp1
        asl a
        asl a
        adc tmp1                ; 5 bytes each (C = 0)
        adc #<@t8
        sta @tgo+1
        lda #>@t8
        adc #0
        sta @tgo+2
        jsr dest
@tw:    ldy #0
@tgo:   jmp @t8
@t8:
.repeat 8
        dey
        lda (ptr2),y
        sta (ptr1),y
.endrepeat
        tya
        bne @t8
        dec count
        beq @none
        lda ptr2                ; next rows: source + sw, canvas + w
        clc
        adc sw
        sta ptr2
        bcc :+
        inc ptr2+1
        clc
:       lda ptr1
        adc _dhgr_cv_w
        sta ptr1
        bcc @tw
        inc ptr1+1
        bcs @tw                 ; (C = 1)
@none:  rts
@chunky:
        lda _dhgr_cv_flags      ; mirror: from sw - 1 - column, backwards
        lsr a
        lda #$C8                ; iny
        bcc :+
        clc
        lda sw
        sbc tmp1                ; sw - 1 - column
        sta tmp1
        lda #$88                ; dey
:       sta @step
        lda cnt
        sta @cnt+1
        jsr dest
        lda ptr1
        sta @dst+1
        lda ptr1+1
        sta @dst+2
@crow:  ldy tmp1
        ldx #0
@px:    lda (ptr2),y
        bmi @clear
        lsr a                   ; colour -> nibble
        bcc :+
        ora #8
:
@dst:   sta $FFFF,x
@clear:
@step:  iny
        inx
@cnt:   cpx #0
        bne @px
        dec count
        beq @end
        lda ptr2                ; next rows: source + sw, canvas + w
        clc
        adc sw
        sta ptr2
        bcc :+
        inc ptr2+1
        clc
:       lda @dst+1
        adc _dhgr_cv_w
        sta @dst+1
        bcc @crow
        inc @dst+2
        bcs @crow               ; (C = 1)
@end:   rts

; ptr1 = the canvas at row ridx, column cs.
dest:   ldy ridx
        lda cs
        sec
        sbc _dhgr_cv_x0
        clc
        adc cv_rowoff,y         ; (a piece is at most 255 bytes)
        clc
        adc _dhgr_cv_buf
        sta ptr1
        lda _dhgr_cv_buf+1
        adc #0
        sta ptr1+1
        rts

