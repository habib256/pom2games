; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; dhgr_vline(x,y0,y1,set): A=set; stack=y1,y0,xlo,xhi.
.export _dhgr_vline
.import _dhgr_fill_bits
.importzp sp, tmp1, tmp2, tmp4
.code
_dhgr_vline:
        sta tmp4
        ldy #0
        lda (sp),y
        sta tmp1               ; end
        iny
        lda (sp),y
        sta tmp2               ; start
        cmp tmp1
        bcc ordered
        beq ordered
        ldx tmp1
        sta tmp1
        stx tmp2
ordered:
        lda tmp1
        cmp #192
        bcc within
        lda #191
within:
        clc
        adc #1
        sec
        sbc tmp2
        sta tmp1               ; modular byte height, as in C even offscreen
        lda sp
        sec
        sbc #2
        sta sp
        bcs room
        dec sp+1
room:
        ldy #0
        lda tmp1
        sta (sp),y
        iny
        lda #1
        sta (sp),y
        iny
        lda #0
        sta (sp),y
        iny
        lda tmp2
        sta (sp),y             ; x is already in slots 4/5
        lda tmp4
        jmp _dhgr_fill_bits
