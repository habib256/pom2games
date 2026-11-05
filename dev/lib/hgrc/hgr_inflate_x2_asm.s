; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; See hgr_x2_target.s for the private ABI. Bytewise 7-dot to 14-dot conversion,
; with duplicate output rows and palette bits only on nonzero output bytes.
; All cc65 scratch may be destroyed. No new RAM, ZP or hardware-stack locals.
.export _hgr_inflate_x2_asm
.importzp sp, ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4
.rodata
spread: .byte 0,1,4,5,16,17,20,21,64,65,68,69,80,81,84,85
.code
_hgr_inflate_x2_asm:
        lda tmp3
        cmp #6
        bcc valid_color
        lda #0                  ; every unknown color is black, like the C
valid_color:
        cmp #4
        bcc color_ready
        clc
        adc #126                ; blue/orange -> left/right with palette bit 7
color_ready:
        sta tmp3
row:
        ldy #3
        clc
        lda (sp),y
        adc ptr2
        sta ptr3
        iny
        lda (sp),y
        adc ptr2+1
        sta ptr3+1
        lda tmp1
        sta tmp4
pixel:
        ldy #0
        lda (ptr1),y
        and #15
        tax
        lda spread,x
        sta ptr4
        lda (ptr1),y
        lsr
        lsr
        lsr
        lsr
        and #7                  ; source bit 7 never contributes pixels
        tax
        lda spread,x
        sta ptr4+1
        lda tmp3
        and #3
        cmp #2
        beq decode
        cmp #3
        beq right
        cmp #1
        beq white
        lda #0
        sta ptr4
        sta ptr4+1
        jmp decode
white:
        lda ptr4
        asl
        ora ptr4
        sta ptr4
        lda ptr4+1
        rol
        ora ptr4+1
        sta ptr4+1
        jmp decode
right:
        asl ptr4
        rol ptr4+1
decode:
        lda ptr4
        and #127
        tax
        asl ptr4
        lda ptr4+1
        rol
        sta ptr4+1
        txa
        beq low_ready
        bit tmp3
        bpl low_ready
        ora #128
low_ready:
        sta (ptr2),y
        sta (ptr3),y
        iny
        lda ptr4+1
        beq high_ready
        bit tmp3
        bpl high_ready
        ora #128
high_ready:
        sta (ptr2),y
        sta (ptr3),y
        inc ptr1
        bne :+
        inc ptr1+1
:       clc
        lda ptr2
        adc #2
        sta ptr2
        bcc :+
        inc ptr2+1
:       clc
        lda ptr3
        adc #2
        sta ptr3
        bcc :+
        inc ptr3+1
:       dec tmp4
        beq row_done
        jmp pixel
row_done:
        lda ptr3
        sta ptr2
        lda ptr3+1
        sta ptr2+1
        dec tmp2
        beq done
        jmp row
done:
        rts
