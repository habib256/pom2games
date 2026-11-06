; VERHILLE Arnaud — GPL-3.0. Fixed-camera projection, NMOS6502/cc65.
; Fastcall AX=out; C stack y,x lo/hi,camera lo/hi. Consume five bytes.
; Main RAM/ZP, D=0, not reentrant/IRQ-callable. ptr1..ptr4,tmp1..tmp4
; clobbered; no private state, self modification, bank or IRQ changes.
.export _a2_perspective_project
.import incsp5
.importzp sp,ptr1,ptr2,ptr3,ptr4,tmp1,tmp2,tmp3,tmp4
.code
_a2_perspective_project:
        sta ptr4
        stx ptr4+1
        ora ptr4+1
        beq @reject
@camera:
        ldy #3
        lda (sp),y
        sta ptr1
        iny
        lda (sp),y
        sta ptr1+1
        ora ptr1
        beq @reject
        ldy #0
        lda (ptr1),y
        sta ptr2
        iny
        lda (ptr1),y
        sta ptr2+1
        ora ptr2
        beq @reject
        iny
        lda (ptr1),y
        sta ptr3
        iny
        lda (ptr1),y
        sta ptr3+1
        ora ptr3
        beq @reject
        iny
        lda (ptr1),y
        sta tmp1
        iny
        lda (ptr1),y
        sta tmp2
        ora tmp1
        beq @reject
        iny
        lda (ptr1),y
        beq @reject
        cmp #193
        bcs @reject
        sta tmp3
        ldy #0
        lda (sp),y
        cmp tmp3
        bcs @reject
        sta tmp4
        ldy #2
        lda (sp),y
        cmp #1
        bcc @xvalid
        bne @reject
        dey
        lda (sp),y
        cmp #24
        bcs @reject
@xvalid:
        lda tmp1
        sta ptr1
        lda tmp2
        sta ptr1+1
        ldy tmp4
        lda (ptr1),y
        cmp #192
        bcc @screen_ok
; Central return keeps every validation branch within the relative range.
@reject:
        lda #0
        tax
        jmp incsp5
@screen_ok:
        sta tmp3
        lda (ptr2),y
        sta tmp2
        tya
        asl
        tay
        bcc @shift
        inc ptr3+1
@shift:
        lda (ptr3),y
        sta ptr1
        iny
        lda (ptr3),y
        sta ptr1+1
        cmp #2
        bcs @reject
        cmp #0
        beq @input
        lda ptr1
        cmp #24
        bcs @reject
@input:
        ldy #1
        lda (sp),y
        sta tmp1
        lda tmp2
        beq @identity
        lda #0
        ldx #8
@multiply:
        lsr tmp1
        bcc @halve
        clc
        adc tmp2
@halve:
        ror a
        dex
        bne @multiply
        sta tmp1
        ldy #2
        lda (sp),y
        beq @sum
        lda tmp1
        clc
        adc tmp2
        sta tmp1
        bcc @sum
        inx
        bne @sum
@identity:
        ldy #2
        lda (sp),y
        tax
@sum:
        lda tmp1
        clc
        adc ptr1
        sta tmp1
        txa
        adc ptr1+1
        cmp #2
        bcs @reject
        tax
        beq @store
        lda tmp1
        cmp #24
        bcs @reject
@store:
        ldy #0
        lda tmp1
        sta (ptr4),y
        iny
        txa
        sta (ptr4),y
        iny
        lda tmp3
        sta (ptr4),y
        lda #1
        ldx #0
        jmp incsp5
