; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; dhgr_fill_rect(x,y,width,height,color): A=color; stack=height,width,y,x.
; Expand the four byte arguments into the helper's five-byte bit rectangle.
.export _dhgr_fill_rect
.import _dhgr_prepare_pattern, _dhgr_bit_rect, addysp
.importzp sp, tmp1
.code
_dhgr_fill_rect:
        tax                    ; preserve color while checking x
        ldy #3
        lda (sp),y
        cmp #140
        bcc valid
        ldy #4
        jmp addysp             ; invalid x leaves the pattern unchanged
valid:
        txa
        jsr _dhgr_prepare_pattern
        ldy #3
        lda #140
        sec
        sbc (sp),y
        ldy #1
        cmp (sp),y
        bcs clipped
        sta (sp),y             ; width=min(width,140-x), before multiplying
clipped:
        ldy #0
        lda (sp),y
        tax                    ; height survives the frame expansion in X
        lda sp
        bne room
        dec sp+1
room:
        dec sp                 ; now: spare,height,width,y,x
        ldy #2
        lda (sp),y
        asl a
        sta tmp1
        lda #0
        rol a
        asl tmp1
        rol a                  ; A/tmp1 = 16-bit width*4
        ldy #1
        sta (sp),y
        dey
        lda tmp1
        sta (sp),y
        ldy #3
        lda (sp),y
        dey
        sta (sp),y             ; move y before replacing its slot with x low
        ldy #4
        lda (sp),y
        asl a
        sta tmp1
        lda #0
        rol a
        asl tmp1
        rol a                  ; A/tmp1 = 16-bit x*4
        ldy #4
        sta (sp),y
        dey
        lda tmp1
        sta (sp),y
        txa
        jmp _dhgr_bit_rect     ; consumes widthlo,widthhi,y,xlo,xhi
