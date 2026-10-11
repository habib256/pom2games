; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
.segment "TRAVEL"

; Original T08/S07 $5BFB-$5C94 prepares an integer major coordinate and
; a sine-driven minor accumulator; T09/S00 $5B35 rounds the minor each step.
module_swim_prepare:
        lda     heading+1
        ldy     heading
        jsr     GIVAYF
        fst     t1
        fld     f_deg_heading
        fop     FDIV, t1        ; map the 560 azimuths back to original degrees
        fop     FADD, f_half
        jsr     AYINT
        sec
        lda     #90
        sbc     $A1
        sta     num
        lda     #0
        sbc     $A0
        sta     num+1
        bpl     @angle
        clc
        lda     num
        adc     #<360
        sta     num
        lda     num+1
        adc     #>360
        sta     num+1
@angle: lda     #0
        sta     travel_axis
        sta     travel_sign
        lda     num+1
        beq     @low
        lda     num
        cmp     #59            ; angle < 315
        bcc     @yminus
        bcs     @slope
@low:   lda     num
        cmp     #46
        bcc     @slope
        cmp     #135
        bcc     @yplus
        cmp     #226
        bcs     @yminus
        lda     #$FF
        sta     travel_sign
        bne     @slope
@yminus:
        lda     #$FF
        sta     travel_sign
@yplus:
        inc     travel_axis
@slope: lda     num+1
        ldy     num
        jsr     GIVAYF
        fop     FMULT, trv_rad
        lda     travel_axis
        beq     :+
        fop     FSUB, trv_half_pi ; original cos = SIN(pi/2 - angle)
:       jsr     FSIN
        fst     travel_delta
        ; Original coordinates are integers in half-map-cell units.
        lda     px
        asl
        lda     px+1
        rol
        sta     g0
        lda     py
        asl
        lda     py+1
        rol
        sta     g1
        ldx     travel_axis
        lda     g0,x
        sta     travel_major
        txa
        eor     #1
        tax
        ldy     g0,x
        lda     #0
        jsr     GIVAYF
        fst     travel_accum
        rts

module_swim_next:
        lda     travel_sign
        bmi     @minus
        inc     travel_major
        jmp     @minor
@minus: dec     travel_major
@minor: fld     travel_accum
        fop     FADD, travel_delta
        fst     travel_accum
        fld     travel_accum
        fop     FADD, f_half
        jsr     AYINT
        ldx     travel_axis
        lda     travel_major
        sta     g0,x
        txa
        eor     #1
        tax
        lda     $A1
        sta     g0,x
        .repeat 2, I
        lda     g0+I
        lsr
        sta     nx+2*I+1
        lda     #0
        ror
        sta     nx+2*I
        sec
        sbc     px+2*I
        sta     wdx+2*I
        lda     nx+2*I+1
        sbc     px+2*I+1
        sta     wdx+2*I+1
        .endrepeat
        rts

trv_rad:     .byte $7B,$0E,$FA,$35,$37
trv_half_pi: .byte $81,$49,$0F,$DA,$D5

; A land destination is permitted when leaving water, or when the next
; raster half-step enters water. WALK stops a full cell before water, so
; rejecting the first land half-step would make SWIM impossible from shore.
; Probe without committing position, time, or the raster's next-step state.
module_swim_land:
        ldx     py+1
        ldy     px+1
        jsr     cell_at
        bpl     @entry
        lda     #1
        sta     travel_shore
        sec
        rts
@entry: ldx     #3
@save:  lda     nx,x
        pha
        lda     wdx,x
        pha
        dex
        bpl     @save
        lda     travel_major
        pha
        ldx     #4
@float: lda     travel_accum,x
        pha
        dex
        bpl     @float
        jsr     module_swim_next
        lda     nx+1
        cmp     #2
        bcc     @no
        cmp     #GW-2
        bcs     @no
        lda     ny+1
        cmp     #2
        bcc     @no
        cmp     #GH-2
        bcs     @no
        tax
        ldy     nx+1
        jsr     cell_at
        bpl     @no
        sec
        bcs     @restore
@no:    clc
@restore:
        php
        pla
        sta     trv_admitted
        ldx     #0
@unfloat:
        pla
        sta     travel_accum,x
        inx
        cpx     #5
        bne     @unfloat
        pla
        sta     travel_major
        ldx     #0
@unsave:
        pla
        sta     wdx,x
        pla
        sta     nx,x
        inx
        cpx     #4
        bne     @unsave
        lda     trv_admitted
        pha
        plp
        bcs     @done
        lda     #8
        sta     travel_reason
        clc
@done:  rts
trv_admitted: .byte 0

; Normal swimming, T08/S07 $5B51 and T09/S00 $5909-$59CC.
; Default original modifiers: $4BBE=2, $4B49=1, $4B4C=0.
; Terrain/equipment and illness changes to those modifiers remain to port.
module_swim_step:
        jsr     travel_pounds
        fop     FADD, trv_adjust
        fst     t1
        lda     body_weight+1
        ldy     body_weight
        jsr     GIVAYF
        fop     FDIV, t1
        fop     FMULT, trv_180
        fst     t1
        fld     s_health
        jsr     FSQR
        fst     t2
        fld     trv_six
        fop     FMULT, t2
        fst     t2
        fld     trv_five
        fop     FMULT, t1
        fst     t1
        fld     t2
        fop     FDIV, t1
        fst     t1
        lda     wdx
        ora     wdx+1
        beq     @straight
        lda     wdy
        ora     wdy+1
        beq     @straight
        fld     trv_diagonal
        jmp     @duration
@straight:
        fld     trv_straight
@duration:
        fop     FMULT, t1
        fop     FADD, f_half
        jsr     AYINT
        lda     $A0
        bne     @unsupported    ; spend currently accepts only byte durations
        lda     $A1
        beq     @unsupported
        sta     stepmin
        clc
        rts
@unsupported:
        sec
        rts

; Original float encodings, including their final mantissa bits.
trv_adjust:   .byte $82,$00,$00,$00,$00 ; 2 ($4BBE initial modifier)
trv_180:      .byte $88,$34,$00,$00,$00
trv_five:     .byte $83,$20,$00,$00,$00
trv_six:      .byte $83,$40,$00,$00,$00
trv_straight: .byte $7F,$4C,$CC,$CC,$CD ; .4
trv_diagonal: .byte $80,$11,$26,$E9,$79 ; .567

; T08/S07 $5AE7/$5D3A: swimming costs .06 * total pounds + basal rate.
; $50A1 truncates carried ounces / 16 before adding body pounds. Our load
; table counts water separately; remove the canteen's initially full water
; weight (its dry shell is 16 oz) to avoid counting that water twice.
 .segment "ENVIRON"
module_swim_metabolic:
        jsr     travel_pounds
        fop     FMULT, f_swim_k
        fop     FADD, f_rest_rate
        rts

travel_pounds:
        lda     load_used
        sta     num
        lda     load_used+1
        sta     num+1
        lda     it_place+64
        beq     @pounds
        cmp     #$FF
        beq     @pounds
        sec
        lda     num
        sbc     it_oz_lo+64
        sta     num
        lda     num+1
        sbc     it_oz_hi+64
        sta     num+1
        clc
        lda     num
        adc     #16
        sta     num
        bcc     @pounds
        inc     num+1
@pounds:
        ldx     #4
@shift: lsr     num+1
        ror     num
        dex
        bne     @shift
        clc
        lda     num
        adc     body_weight
        tay
        lda     num+1
        adc     body_weight+1
        jsr     GIVAYF
        rts
