; Magnetic compass ribbon in DHGR colour (lot 4): colour columns 56..83
; (groups 8..11, bytes 16..23 of each bank), rows 0..15, 7 azimuth units per
; pixel. Letters N E S W and ticks scroll under the fixed yellow pointer
; (column 70); no disk/ROM calls per pan. hud_col, the per-column colour
; primitive, also draws the survival panels (src/summary.s).
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

HUD_X0   = 56                   ; first colour column of the ribbon (group 8)
HUD_LAST = 27                   ; its last pixel: frame column 83
TOP_LETTER = 2                  ; letters: rows 2..6
TOP_TICK   = 8                  ; ticks: row 9, long ones rows 8..9
hud_pen_g = dca                 ; pen: colour group 0..19
hud_pen_k = dcb                 ;      phase 0..6
hud_top   = dv0                 ; hud_col: row of mask bit 0
hud_ink   = dv1                 ;          colour
hud_part  = dpa_off             ; hud_col: parts A, B of the pixel, 4 bytes
                                ; each: byte offset ($FF: none), kept bits,
                                ; colour bits, bank switch ($54/$55)
hud_g2    = dp                  ;          2 * group
hud_px    = dp+1                ;          part index
hud_left  = be                  ; hud_draw: strip pixel of ribbon pixel 0
hud_x     = row0                ;           ribbon pixel
.assert dj+1 = hud_part+7, error, "hud_part needs 8 bytes of pass scratch"
.assert ph_offb = ph_offa+28 .and ph_banka = ph_offa+7 .and ph_pata = ph_offa+14 .and ph_bitsa = ph_offa+21, error, "phase tables: A then B, 7 bytes each"

.segment "LOWCODE"
        .include "hud.inc"      ; build/, from tools/genhud.py
.assert HUD_BORDER = 15, error, "hud_draw stores a white frame as whole bytes"

; hud_draw -- the ribbon over the cached landscape (rows 160..175 keep the
; terrain hidden by the HUD). Clobbers ang, the pass scratch and hp.
hud_draw:
        ; Whole bytes, both banks: frame rows 0 and 15 white, black interior
        ; with the frame columns 56 (aux 16 bits 0..3) and 83 (main 23 bits 3..6).
        php
        sei
        ldx     #15
@row:   txa
        jsr     hud_row
        lda     #$7F
        cpx     #0
        beq     @fill
        cpx     #15
        beq     @fill
        lda     #0
@fill:  ldy     #23
@byte:  sta     PAGE2_AUX
        sta     (hp),y
        sta     PAGE2_MAIN
        sta     (hp),y
        dey
        cpy     #16
        bcs     @byte
        pha
        ora     #$78
        ldy     #23
        sta     (hp),y
        pla
        ora     #$0F
        ldy     #16
        sta     PAGE2_AUX
        sta     (hp),y
        sta     PAGE2_MAIN
        dex
        bpl     @row
        plp
        ; Ribbon pixel 0 = (magnetic heading - 98) / 7 = heading / 7 - 14
        ; on the 80-pixel strip.
        sec
        lda     heading
        sbc     hud_offset
        sta     ang
        lda     heading+1
        sbc     hud_offset+1
        sta     ang+1
        jsr     wrap_ang
        lda     #80-14
        sta     hud_left
@q:     lda     ang             ; 140 units = 20 pixels
        cmp     #140
        lda     ang+1
        sbc     #0
        bcc     @rem
        sta     ang+1
        lda     ang
        sbc     #140
        sta     ang
        lda     hud_left
        clc
        adc     #20
        sta     hud_left
        bcc     @q
@rem:   lda     ang
        jsr     div7
        txa
        adc     hud_left        ; carry clear (div7)
        cmp     #80             ; at most 66 + 60 + 19
        bcc     :+
        sbc     #80
:       sta     hud_left
        ; Interior pixels 1..26: letter column, ticks, and the fixed yellow
        ; index (pixels 12..16 = columns 68..72, rows 11..13).
        lda     #HUD_X0+1
        jsr     hud_pen
        lda     #1
@col:   sta     hud_x
        adc     hud_left        ; carry clear
        cmp     #80
        bcc     :+
        sbc     #80
:       tax
        lda     hud_strip,x
        pha
        ldx     #HUD_INK
        asl     a
        bcc     :+
        ldx     #HUD_NORTH
:       stx     hud_ink
        ldx     #TOP_LETTER
        stx     hud_top
        and     #$1F*2
        lsr     a
        jsr     hud_col
        lda     #HUD_TICK
        sta     hud_ink
        lda     #TOP_TICK
        sta     hud_top
        pla
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        and     #3
        jsr     hud_col
        lda     hud_x
        sec
        sbc     #70-2-HUD_X0
        cmp     #5
        bcs     :+
        tax
        lda     #HUD_POINTER
        sta     hud_ink
        lda     #11
        sta     hud_top
        lda     hud_ptr_mask,x
        jsr     hud_col
:       jsr     hud_next
        lda     hud_x
        clc
        adc     #1
        cmp     #HUD_LAST
        bcc     @col
        rts

; hud_col -- A = row mask (bit k: row hud_top + k, rows 0..15 only): paint
; colour hud_ink in the colour column of the pen, read-modify-write in the
; bank(s) of its phase (docs/DHGR.md 1). Keeps the pen, hud_top, hud_ink;
; clobbers A, X, Y, dm and the pass scratch dpa_off..dp. Returns with main
; selected.
hud_col:
        tax
        bne     :+
        rts                     ; empty mask
:       stx     dm
        php
        sei
        lda     hud_pen_g
        asl     a
        sta     hud_g2
        ldy     hud_pen_k       ; part A tables, then part B (+28)
        ldx     #0
@part:  lda     ph_offa,y
        bmi     @single         ; $FF: no part B
        clc
        adc     hud_g2
        sta     hud_part,x
        lda     ph_banka,y
        sta     hud_part+3,x
        lda     ph_bitsa,y
        eor     #$7F
        sta     hud_part+1,x
        stx     hud_px
        lda     ph_pata,y       ; dc_pat + 16 j + colour
        clc
        adc     hud_ink
        tax
        lda     dc_pat-<dc_pat,x
        ldx     hud_px
        and     ph_bitsa,y
        sta     hud_part+2,x
        tya
        adc     #28             ; carry clear
        tay
        inx
        inx
        inx
        inx
        cpx     #8
        bcc     @part
        bcs     @rows
@single:
        sta     hud_part,x
@rows:  lda     hud_top
        jsr     hud_row
@pixel: lsr     dm
        bcc     @down
        ldx     #0
@byte:  lda     hud_part,x
        bmi     @main
        ldy     hud_part+3,x
        sta     $C000,y         ; PAGE2: bank of this part
        tay
        lda     (hp),y
        and     hud_part+1,x
        ora     hud_part+2,x
        sta     (hp),y
        inx
        inx
        inx
        inx
        cpx     #8
        bcc     @byte
@main:  sta     PAGE2_MAIN
@down:  lda     hp+1            ; next row: +$400, row 8 at $2080
        clc
        adc     #4
        cmp     #$40
        bcc     :+
        lda     #$80
        sta     hp
        lda     #$20
:       sta     hp+1
        lda     dm
        bne     @pixel
        plp
        rts

; hud_row -- A = row 0..15: hp = its address ($2000 + (A & 7) * $400 +
; (A & 8) * $10). Preserves X and Y.
hud_row:
        pha
        and     #7
        asl     a
        asl     a
        ora     #$20
        sta     hp+1
        pla
        and     #8
        asl     a
        asl     a
        asl     a
        asl     a
        sta     hp
        rts

; hud_pen -- A = colour column: pen at its group and phase.
hud_pen:
        jsr     div7
        stx     hud_pen_g
        sta     hud_pen_k
        rts

; hud_next -- the pen moves one colour column right.
hud_next:
        inc     hud_pen_k
        lda     hud_pen_k
        cmp     #7
        bcc     :+
        lda     #0
        sta     hud_pen_k
        inc     hud_pen_g
:       rts
