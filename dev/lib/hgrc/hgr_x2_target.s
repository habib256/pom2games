; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_inflate_x2(mono,w,h,color,out): A/X=out; stack=color,h,w,monoLo,monoHi.
; The output extent must fit a 16-bit pointer: w*h <= 16383. Only the product's
; high byte is needed, built in eight add/rotate steps without a runtime multiply.
; Kernel ABI: ptr1=source, ptr2=out, tmp1=w, tmp2=h, tmp3=color; the original
; source slots at sp+3/+4 become the 16-bit doubled row stride. No new RAM/ZP.
.export _hgr_inflate_x2
.import _hgr_inflate_x2_asm
.importzp sp, ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
.code
_hgr_inflate_x2:
        sta ptr2
        stx ptr2+1
        ldy #0
        lda (sp),y
        sta tmp3
        iny
        lda (sp),y
        beq done
        sta tmp2
        sta tmp4
        iny
        lda (sp),y
        beq done
        sta tmp1
        lda #0
        ldx #8
product:
        lsr tmp4
        bcc rotate
        clc
        adc tmp1
rotate:
        ror
        dex
        bne product
        cmp #64
        bcs done
        ldy #3
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        lda tmp1
        asl
        ldy #3
        sta (sp),y
        iny
        lda #0
        rol
        sta (sp),y
        jsr _hgr_inflate_x2_asm
done:
        clc
        lda sp
        adc #5
        sta sp
        bcc :+
        inc sp+1
:       rts
