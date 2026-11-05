; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_blit_x2(x,y,mono,w,h,color,mode): A=mode, C stack=color,h,w,monoLo,
; monoHi,y,xLo,xHi. Reject before reserving anything; source area <= 64 bytes.
; The doubled 256-byte buffer remains private to this optional archive member.
.export _hgr_blit_x2
.import _hgr_inflate_x2, _hgr_blit7, pusha, pushax
.importzp sp, tmp1, tmp2, tmp3
BUFFER_BYTES = 256
MAX_SOURCE = BUFFER_BYTES / 4
.assert MAX_SOURCE = 64, error, "bounded product requires the 256-byte x2 buffer"
.bss
buffer: .res BUFFER_BYTES
.code
_hgr_blit_x2:
        sta tmp3                ; mode, only needed once validation succeeds
        ldy #1
        lda (sp),y
        beq rejected
        cmp #MAX_SOURCE+1
        bcs rejected
        sta tmp2                ; shifting height
        iny
        lda (sp),y
        beq rejected
        cmp #MAX_SOURCE+1
        bcs rejected
        sta tmp1                ; shifting width
        ldy #5
        lda (sp),y
        cmp #192
        bcs rejected
        ldy #7
        lda (sp),y
        cmp #2
        bcs rejected
        tax
        dey
        lda (sp),y
        cpx #0
        beq coordinates_ready
        cmp #24
        bcs rejected
coordinates_ready:
        lda #0
product:
        lsr tmp2
        bcc shift
        clc
        adc tmp1
        cmp #MAX_SOURCE+1
        bcs rejected
shift:
        ldx tmp2
        beq accepted
        asl tmp1
        bpl product             ; a future contribution >=128 cannot fit 64
rejected:
        clc
        lda sp
        adc #8
        sta sp
        bcc :+
        inc sp+1
:       rts
accepted:
        lda tmp3
        jsr pusha               ; save mode: nine original argument bytes
        ldy #5
        lda (sp),y
        tax
        dey
        lda (sp),y
        jsr pushax              ; source
        ldy #5
        lda (sp),y
        jsr pusha               ; width
        ldy #5
        lda (sp),y
        jsr pusha               ; height
        ldy #5
        lda (sp),y
        jsr pusha               ; color
        lda #<buffer
        ldx #>buffer
        jsr _hgr_inflate_x2
        ; Reuse the original frame as [bufferLo,bufferHi,2*h,2*w,y,xLo,xHi].
        ldy #2
        lda (sp),y
        asl
        iny
        iny
        sta (sp),y
        dey
        lda (sp),y
        asl
        iny
        iny
        sta (sp),y
        ldy #2
        lda #<buffer
        sta (sp),y
        iny
        lda #>buffer
        sta (sp),y
        ldy #0
        lda (sp),y
        tax
        clc
        lda sp
        adc #2
        sta sp
        bcc :+
        inc sp+1
:       txa
        jmp _hgr_blit7
