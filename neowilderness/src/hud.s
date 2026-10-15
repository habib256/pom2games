; Magnetic compass ribbon (lot 4: native DHGR colour). Byte groups 7..12
; (colour pixels 49..90) of rows 0..15: a dark blue ribbon whose 140-column
; strip (tools/genhud.py, 4 azimuth units per pixel) scrolls under a fixed
; yellow pointer at pixel 70, white bearings and ticks (a coloured 1-pixel
; stroke on blue fringes on a composite display and in POM2). No disk/ROM
; calls per pan. tools/dhgr_ref.hud_banks is the model.
HUD_G0     = 7                  ; first byte group of the ribbon
HUD_PIX    = 42                 ; ribbon pixels (6 groups)
HUD_CENTRE = 21                 ; pixel 70 = HUD_G0 * 7 + HUD_CENTRE
HUD_BG     = 2                  ; dark blue
HUD_INK    = 15                 ; white
HUD_TICK   = 15                 ; white (a thin light blue tick fringes)
HUD_PTR    = 13                 ; yellow
line_pix   = overlay_text + 96  ; colours of one row (free outside the ray loop)
rib_bits   = overlay_text + 48  ; strip bytes under the 42 ribbon pixels

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

.segment "LOWCODE"
; hud_draw -- the ribbon at the current heading (all 16 rows of its groups).
        B2_ENTRY hud_draw, b2_hud_draw
        sec                     ; strip column under the pointer = magnetic
        lda     heading         ; heading / 4
        sbc     hud_offset
        sta     ang
        lda     heading+1
        sbc     hud_offset+1
        sta     ang+1
        jsr     wrap_ang
        lsr     ang+1
        ror     ang
        lsr     ang+1
        ror     ang
        lda     ang
        sec
        sbc     #HUD_CENTRE
        bcs     :+
        adc     #140
:       tay                     ; Y = strip column of ribbon pixel 0
        ldx     #0
@gather:
        lda     hud_strip,y
        sta     rib_bits,x
        iny
        cpy     #140
        bcc     :+
        ldy     #0
:       inx
        cpx     #HUD_PIX
        bcc     @gather
        ldx     #0
@row:   stx     row0
        jsr     hgr_row2
        lda     hud_mask,x
        beq     @fill
        sta     shift           ; strip bit tested on this row
        lda     hud_on,x
        sta     num             ; its ink
        lda     hud_off,x
        sta     num+1           ; the ribbon background
        ldy     #HUD_PIX-1
@pix:   lda     rib_bits,y
        and     shift
        beq     :+
        lda     num
        bne     @put
:       lda     num+1
@put:   sta     line_pix,y
        dey
        bpl     @pix
        bmi     @pack0
@fill:  lda     hud_off,x       ; plain row
        ldy     #HUD_PIX-1
:       sta     line_pix,y
        dey
        bpl     :-
        ldy     hud_ptr,x       ; pointer: centre +- (half-width)
        beq     @pack0
        dey
        sty     shift
        lda     #HUD_CENTRE
        sec
        sbc     shift
        tay
        lda     shift
        asl     a
        tax                     ; 2 * half-width + 1 pixels
        lda     #HUD_PTR
:       sta     line_pix,y
        iny
        dex
        bpl     :-
@pack0:
        ldy     #0              ; pack the six groups of the row
        ldx     #HUD_G0*2
@pack:  jsr     b2_dhgr_pack    ; (bank 2: not through the stub)
        inx
        inx
        tya
        clc
        adc     #7
        tay
        cpy     #HUD_PIX
        bcc     @pack
        ldx     row0
        inx
        cpx     #HUD_ROWS
        bcc     @row
        rts
; Rows 0..15: tested strip bit, colour when set, colour when clear, pointer
; half-width + 1.
hud_mask: .byte 0, 1, 2, 4, 8, 16, 32, 64, 0, $80, $80, 0, 0, 0, 0, 0
hud_on:   .byte 0, HUD_INK, HUD_INK, HUD_INK, HUD_INK, HUD_INK, HUD_INK, HUD_INK
          .byte 0, HUD_TICK, HUD_TICK, 0, 0, 0, 0, 0
hud_off:  .byte HUD_BG, HUD_BG, HUD_BG, HUD_BG, HUD_BG, HUD_BG, HUD_BG, HUD_BG
          .byte HUD_BG, HUD_BG, HUD_BG, 0, 0, 0, 0, 0
hud_ptr:  .byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 0, 0   ; rows with mask 0 only
        B2_END

        .include "hud.inc"
