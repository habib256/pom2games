; Magnetic compass ribbon: 98 pixels centred above the view. Eight bearings
; and sixteen ticks move under the fixed pointer; no disk/ROM calls per pan.
.segment "GDATA"
hud_offset: .word 0
.segment "ENVIRON"
hud_init:
        lda     heading
        pha
        lda     heading+1
        pha
        lda     #0
        sta     heading
        sta     heading+1
        jsr     magnetic_heading
        lda     heading
        sta     hud_offset
        lda     heading+1
        sta     hud_offset+1
        pla
        sta     heading+1
        pla
        sta     heading
        rts

.segment "GCODE"
.segment "TEXT"
; Border byte for row X, column Y. Interior remains clear.
hud_border_byte:
        lda     #127
        cpx     #0
        beq     @done
        cpx     #15
        beq     @done
        lda     #1
        cpy     #13
        beq     @done
        lda     #64
        cpy     #26
        beq     @done
        lda     #0
@done:  rts

.segment "LOWCODE"
hud_draw:
        ; Composite the ribbon over the cached landscape. HGR rows 160..175
        ; are hidden in mixed mode; they preserve pixels masked by the HUD.
        ldx     #0
@clear: jsr     hgr_row2
        ldy     #26
@byte:  jsr     hud_border_byte
        jsr     dbl_put
        dey
        cpy     #13
        bcs     @byte
        inx
        cpx     #2              ; ribbon rows 2..9 are copied whole below
        bne     :+
        ldx     #10
:       cpx     #HUD_ROWS
        bcc     @clear
        ; Left edge = magnetic heading - 49 ribbon pixels (98 azimuth units).
        sec
        lda     heading
        sbc     hud_offset
        sta     ang
        lda     heading+1
        sbc     hud_offset+1
        sta     ang+1
        jsr     wrap_ang
        sec
        lda     ang
        sbc     #98
        sta     ang
        lda     ang+1
        sbc     #0
        sta     ang+1
        jsr     wrap_ang
        lsr     ang+1
        lda     ang
        ror     a
        sta     num
        lda     ang+1
        sta     num+1
        ldx     #0
@divide:
        lda     num+1
        bne     @sub
        lda     num
        cmp     #7
        bcc     @divided
@sub:   sec
        lda     num
        sbc     #7
        sta     num
        lda     num+1
        sbc     #0
        sta     num+1
        inx
        bne     @divide
@divided:
        stx     be              ; first source byte, 0..39
        lda     num
        clc
        adc     #1              ; shift packed 7-bit pairs by remainder+1
        sta     shift
        lda     #0
        sta     row0
@row:   ldx     row0
        lda     hud_strip_lo,x
        sta     gp
        lda     hud_strip_hi,x
        sta     gp+1
        txa
        clc
        adc     #2              ; two-pixel top padding
        tax
        jsr     hgr_row2
        lda     be
        sta     tmp
        lda     #13
        sta     num
@copy:  ldy     tmp
        lda     (gp),y
        asl     a
        sta     qlo
        iny
        cpy     #40
        bcc     :+
        ldy     #0
:       sty     tmp
        lda     (gp),y
        ldx     shift
@bits:  lsr     a
        ror     qlo
        dex
        bne     @bits
        lda     qlo
        and     #$7F
        ldy     num
        cpy     #13
        bne     :+
        ora     #1
:       cpy     #26
        bne     :+
        ora     #64
:       jsr     dbl_put
        inc     num
        lda     num
        cmp     #27
        bcc     @copy
        inc     row0
        lda     row0
        cmp     #8
        bcc     @row
        ; Fixed downward yellow index, centred on colour pixel 70
        ; (HGR pixels 140..141), rows 11..13: whole bytes 19 and 20.
        ldx     #8
@index: txa
        lsr     a
        lsr     a
        adc     #11
        stx     tmp
        tax
        jsr     hgr_row2
        ldx     tmp
        ldy     #19
        lda     hud_ptr,x
        sta     (hp2),y
        iny
        lda     hud_ptr+1,x
        sta     (hp2),y
        php
        sei
        sta     PAGE2_AUX
        lda     hud_ptr+3,x
        sta     (hp2),y
        dey
        lda     hud_ptr+2,x
        sta     (hp2),y
        sta     PAGE2_MAIN
        plp
        dex
        dex
        dex
        dex
        bpl     @index
        rts

        .include "hud.inc"
