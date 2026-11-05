; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; dhgr_hline(x0,x1,y,set): A=set; stack=y,x1lo,x1hi,x0lo,x0hi.
; Sort full words, clip the right end, then forward a one-row rectangle.
.export _dhgr_hline
.import _dhgr_fill_bits
.importzp sp, ptr1, ptr2, tmp3, tmp4
.code
_dhgr_hline:
        sta tmp4
        ldy #0
        lda (sp),y
        sta tmp3               ; y survives the expanded frame
        iny
        lda (sp),y
        sta ptr2
        iny
        lda (sp),y
        sta ptr2+1
        iny
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        lda ptr2+1
        cmp ptr1+1
        bcc swap
        bne ordered
        lda ptr2
        cmp ptr1
        bcs ordered
swap:
        ldx ptr1
        lda ptr2
        sta ptr1
        stx ptr2
        ldx ptr1+1
        lda ptr2+1
        sta ptr1+1
        stx ptr2+1
ordered:
        lda ptr2+1
        cmp #2
        bcc within
        bne clip
        lda ptr2
        cmp #48
        bcc within
clip:
        lda #48                ; exclusive right end = 560
        sta ptr2
        lda #2
        sta ptr2+1
        bne endpoint
within:
        inc ptr2               ; inclusive endpoint -> exclusive
        bne endpoint
        inc ptr2+1
endpoint:
        lda sp
        bne room
        dec sp+1
room:
        dec sp                 ; six-byte fill_bits frame, one extra byte
        ldy #1
        sec
        lda ptr2
        sbc ptr1
        sta (sp),y
        iny
        lda ptr2+1
        sbc ptr1+1
        sta (sp),y             ; preserve C's modular width for rejected x
        iny
        lda tmp3
        sta (sp),y
        iny
        lda ptr1
        sta (sp),y
        iny
        lda ptr1+1
        sta (sp),y
        ldy #0
        lda #1
        sta (sp),y
        lda tmp4
        jmp _dhgr_fill_bits
