; VERHILLE Arnaud — GPL-3.0. Full-width HGR Bresenham, same ties as gfx_line.
; Inputs hgr_l_x0/x1=0..279, hgr_l_y0/y1=0..191; tables built by C wrapper.
; OR drawing, bit 7 and holes preserved. Current draw-page row tables.
; Main RAM/ZP, non-reentrant. A/X/Y, flags, ptr1,tmp1/tmp2/tmp3 destroyed.
; No self modification, no bank/IRQ changes. Endpoints/scratch overwritten.
.export _hgr_line_asm, _hgr_l_x0, _hgr_l_x1, _hgr_l_y0, _hgr_l_y1
.import _hgr_col7, _hgr_mask7, _hgr_rowlo, _hgr_rowhi
.importzp ptr1, tmp1, tmp2, tmp3
.bss
_hgr_l_x0: .res 2
_hgr_l_x1: .res 2
_hgr_l_y0: .res 1
_hgr_l_y1: .res 1
dx: .res 2
dy: .res 2
negdy: .res 2
err: .res 2
e2: .res 2
sx: .res 1
sy: .res 1
.code
_hgr_line_asm:
        lda #1
        sta sx
        sta sy
        sec
        lda _hgr_l_x1
        sbc _hgr_l_x0
        sta dx
        lda _hgr_l_x1+1
        sbc _hgr_l_x0+1
        sta dx+1
        bcs @dx_done
        lda #$ff
        sta sx
        lda #0
        sec
        sbc dx
        sta dx
        lda #0
        sbc dx+1
        sta dx+1
@dx_done:
        lda #0
        sta dy+1
        sec
        lda _hgr_l_y1
        sbc _hgr_l_y0
        bcs @dy_done
        ldx #$ff
        stx sy
        eor #$ff
        clc
        adc #1
@dy_done:
        sta dy
        sec
        lda #0
        sbc dy
        sta negdy
        lda #0
        sbc dy+1
        sta negdy+1
        sec
        lda dx
        sbc dy
        sta err
        lda dx+1
        sbc dy+1
        sta err+1
@pixel:
        ldx _hgr_l_x0
        lda _hgr_l_x0+1
        bne @high
        lda _hgr_col7,x
        sta tmp1
        lda _hgr_mask7,x
        jmp @row
@high:
        lda _hgr_col7+256,x
        sta tmp1
        lda _hgr_mask7+256,x
@row:
        sta tmp2
        ldx _hgr_l_y0
        lda _hgr_rowlo,x
        sta ptr1
        lda _hgr_rowhi,x
        sta ptr1+1
        ldy tmp1
        lda tmp2
        ora (ptr1),y
        sta (ptr1),y
        lda _hgr_l_x0
        cmp _hgr_l_x1
        bne @advance
        lda _hgr_l_x0+1
        cmp _hgr_l_x1+1
        bne @advance
        lda _hgr_l_y0
        cmp _hgr_l_y1
        bne @advance
        rts
@advance:
        lda err
        asl
        sta e2
        lda err+1
        rol
        sta e2+1
        ; Signed e2 > -dy, strict: compare biased high bytes, then lows.
        lda negdy+1
        eor #$80
        sta tmp3
        lda e2+1
        eor #$80
        cmp tmp3
        bcc @test_y
        bne @step_x
        lda e2
        cmp negdy
        bcc @test_y
        beq @test_y
@step_x:
        sec
        lda err
        sbc dy
        sta err
        lda err+1
        sbc dy+1
        sta err+1
        lda sx
        bmi @left
        inc _hgr_l_x0
        bne @test_y
        inc _hgr_l_x0+1
        jmp @test_y
@left:
        lda _hgr_l_x0
        bne @dec_low
        dec _hgr_l_x0+1
@dec_low:
        dec _hgr_l_x0
@test_y:
        ; Signed e2 < dx, using the original e2 even after stepping X.
        lda dx+1
        eor #$80
        sta tmp3
        lda e2+1
        eor #$80
        cmp tmp3
        bcc @step_y
        bne @next
        lda e2
        cmp dx
        bcs @next
@step_y:
        clc
        lda err
        adc dx
        sta err
        lda err+1
        adc dx+1
        sta err+1
        lda sy
        bmi @up
        inc _hgr_l_y0
        jmp @next
@up:
        dec _hgr_l_y0
@next:
        jmp @pixel
