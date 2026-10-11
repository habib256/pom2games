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
 ; X = logical terrain row. hp = terrain/cache; hp2 = visible screen.
; Cache rows 0..15 at HGR 160..175, outside the mixed-mode picture.
view_row:
        lda     hgr_lo,x
        sta     hp2
        sta     hp
        lda     hgr_hi,x
        sta     hp2+1
        sta     hp+1
        cpx     #HUD_ROWS
        bcs     @done
        lda     hp
        clc
        adc     #$50
        sta     hp
        inc     hp+1
        inc     hp+1
@done:  rts

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
@clear: jsr     view_row
        ldy     #26
@byte:  jsr     hud_border_byte
        sta     (hp2),y
        dey
        cpy     #13
        bcs     @byte
        inx
        cpx     #HUD_ROWS
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
        lda     hgr_lo,x
        sta     hp2
        lda     hgr_hi,x
        sta     hp2+1
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
:       sta     (hp2),y
        inc     num
        lda     num
        cmp     #27
        bcc     @copy
        inc     row0
        lda     row0
        cmp     #8
        bcc     @row
        ; Fixed downward pointer, precisely at screen pixel 140.
        lda     #$40
        sta     $3080+19         ; row 12, pixel 139
        lda     #3
        sta     $3080+20         ; row 12, pixels 140..141
        lda     #1
        sta     $3480+20         ; row 13, pixel 140
        rts

        .include "hud.inc"
