; Woodland coverage and Sierra tree profiles. Uses the retired HELLO RAM,
; never DOS vectors. Every result depends on world/ray coordinates, not col.
.segment "WOODS"
forest_bits: .res 294             ; 56 x 42, one bit / four world units
.segment "GDATA"
forest_enabled: .byte 1
.segment "ZEROPAGE"
forest_tmp: .res 1
forest_x: .res 1
forest_y: .res 1
forest_distance: .res 1
forest_start: .res 1
forest_end: .res 1
forest_base: .res 2
forest_lo: .res 1
forest_hi: .res 1
forest_sign: .res 1
forest_proj: .res 2
.segment "GZP": zeropage
; $A4 is Applesoft's rounding byte: foliage must not leave it nonzero.
forest_crown_end: .res 1

.segment "FORESTCODE"
; X/Y = terrain cell east/north. Preserve registers, carry = wooded.
forest_contains:
        stx     forest_x
        sty     forest_y
        lda     MAP+26
        beq     @no
        tya
        lsr
        sta     forest_tmp
        lda     #0
        sta     gp1+1
        lda     forest_tmp
        asl
        rol     gp1+1
        asl
        rol     gp1+1
        asl
        rol     gp1+1
        sec
        sbc     forest_tmp
        sta     gp1
        lda     gp1+1
        sbc     #0
        clc
        adc     #>forest_bits
        sta     gp1+1
        txa
        lsr
        pha
        lsr
        lsr
        lsr
        tay
        pla
        and     #7
        tax
        lda     forest_masks,x
        and     (gp1),y
        beq     @no
        sec
        bcs     @return
@no:    clc
@return:
        ldx     forest_x
        ldy     forest_y
        rts
.segment "GCODE"
woods_here:
        ldx     py+1
        ldy     px+1
        jsr     cell_at
        bpl     :+
        clc
        rts
:       ldx     px+1
        ldy     py+1
        jmp     forest_contains
.segment "LOWTEXT"
forest_masks: .byte 1,2,4,8,16,32,64,128

.segment "LOWCODE"
; Called for every column, even a terrain-free night/shelter scene.
forest_reset:
        lda     #0
        sta     forest_distance
        lda     #$2C            ; BIT abs: skip probe, preserving carry and Y
        ldx     forest_enabled
        beq     :+
        lda     #$20            ; JSR: at most the first eight candidate cells
:       sta     render_forest_call
        rts

.segment "GCODE"
; Query before rejecting hidden ground: a canopy can rise above a ridge.
; Ray state and carry are preserved; bigdiv only uses qlo/qhi/divisor.
forest_probe:
        php
        tya
        pha
        lda     forest_enabled
        jeq     @done
        lda     forest_distance
        jne     @done
        lda     n
        sec
        sbc     #127
        cmp     #9
        bcs     @stop
        sta     forest_distance
        sta     divisor
        lda     (gp),y
        bmi     @reject
        clc
        adc     M_BASE
        ldx     MAP+27
        bne     :+
        ldx     #110
:       stx     forest_tmp
        cmp     forest_tmp
        bcs     @reject
        tya
        tax
        lda     rowsl
        ldy     dy+1
        bmi     :+
        eor     #255
        clc
        adc     #GH
:       tay
        jsr     forest_contains
        bcc     @reject
        jsr     forest_profile
        bcs     @reject
        jsr     forest_projection
        bcs     @reject
        ; Native bottom-up crown coordinates; a central stem reaches the ground.
        lda     forest_hi
        jsr     forest_divide
        jsr     forest_screen_y
        lda     forest_sign
        bmi     @top_zero
        bne     @reject
        lda     forest_tmp
        cmp     #VIEW_ROWS
        bcs     @reject
        bcc     @top_store
@top_zero:
        lda     #0
@top_store:
        sta     forest_start
        lda     forest_lo
        jsr     forest_divide
        jsr     forest_screen_y
        lda     forest_sign
        bmi     @reject
        bne     @bottom_clip
        lda     forest_tmp
        cmp     top
        bcc     :+
@bottom_clip:
        lda     top
:       sta     forest_end
        cmp     forest_start
        bcc     @reject
        beq     @reject
        bne     @stop           ; nearest visible crown is final for this ray
@reject:
        lda     #0
        sta     forest_distance
        beq     @done
@stop:  lda     #$2C            ; no stack/register save on later ray steps
        sta     render_forest_call
@done:  pla
        tay
        plp
        rts

.segment "FORESTCODE"
; Sierra crown heights, with level lower foliage, folded around column 15.
forest_profile:
        ; The dominant ray axis selects the transverse world coordinate.
        lda     dy
        bne     :+
        ldx     dy+1
        bne     @x
        beq     @use_y
:       lda     dx
        bne     :+
        ldx     dx+1
        bne     @use_y
        beq     @x
:       ldx     dx+1
        bpl     :+
        eor     #255
        clc
        adc     #1
:       sta     forest_tmp
        lda     dy
        ldx     dy+1
        bpl     :+
        eor     #255
        clc
        adc     #1
:       cmp     forest_tmp
        bcs     @x
@use_y: lda     ry
        ldx     forest_y
        jmp     @fraction
@x:     lda     rx
        ldx     forest_x
@fraction:
        ; Each cell contains a narrow, centred crown, not a two-cell wall.
        ; 32 native columns span 1/4 cell: the surrounding gaps stay clear.
        sec
        sbc     #96
        bcc     @empty
        lsr
        cmp     #31
        bcs     @empty
        cmp     #16
        bcc     :+
        eor     #255
        clc
        adc     #31              ; 30 - profile column
:       asl
        sta     forest_tmp
        lda     forest_x
        eor     forest_y
        and     #2
        beq     :+
        lda     #32
:       ora     forest_tmp
        tax
        lda     forest_tmp
        cmp     #28             ; three central source columns carry the trunk
        bcc     :+
        lda     #0
        beq     @lo
:       lda     forest_profiles,x
@lo:    sta     forest_lo
        lda     forest_profiles+1,x
        sta     forest_hi
        clc
        rts
@empty: sec
        rts

; Keep a black lower rim above the native canopy bottom at height 31.
forest_projection:
        jsr     forest_project_base
        bcs     @done
        lda     #32
        jsr     forest_divide
        jsr     forest_screen_y
        lda     forest_tmp
        ldx     forest_sign
        beq     @edge
        txa
        asl                     ; negative boundary -> 0, overflow -> 255
        lda     #0
        sbc     #0
@edge:
        sta     forest_crown_end
        clc
@done:  rts

.segment "GCODE"
; 95 - trunc(48 * dz / distance). Keep a 16-bit base below the viewport.
forest_project_base:
        lda     dzb
        eor     #128
        sta     forest_sign
        bpl     :+
        eor     #255
        clc
        adc     #1
:       jsr     bigdiv
        lda     qlo
        asl
        sta     forest_proj
        lda     qhi
        rol
        sta     forest_proj+1
        ; abs(dz) <= 127 and distance >= 1: doubling cannot carry out.
        lda     forest_proj
        adc     qlo
        sta     forest_proj
        lda     forest_proj+1
        adc     qhi
        bcs     @outside        ; reject 3*q overflow before it wraps near zero
        sta     forest_proj+1
        ldx     #4
@shift: lsr     forest_proj+1
        ror     forest_proj
        dex
        bne     @shift
        lda     forest_proj+1
        bne     @outside
        lda     #0
        sta     forest_base+1
        lda     #HORIZON
        ldx     forest_sign
        bmi     @below
        sec
        sbc     forest_proj
        bcc     @outside
        sta     forest_base
        clc
        rts
@below: clc
        adc     forest_proj
        sta     forest_base
        lda     #0
        adc     #0
        sta     forest_base+1
        ; A is 0 or 1, so ADC already cleared carry.
        rts
@outside:
        sec
        rts

.segment "TEXT"
; A / candidate distance, returned in A (profile height in pixels).
forest_divide:
        ldx     #0
@div:   cmp     forest_distance
        bcc     @done
        sec
        sbc     forest_distance
        inx
        bne     @div
@done:  txa
        rts
; Subtract A from the base without modifying the base itself. Result hi is
; returned in forest_sign; the base stays available for the next call.
forest_screen_y:
        sta     forest_tmp
        sec
        lda     forest_base
        sbc     forest_tmp
        sta     forest_tmp
        lda     forest_base+1
        sbc     #0
        sta     forest_sign
        rts

.segment "GCODE"
; Restore opaque, stippled Sierra foliage after sky/sun. Foreground sprites win.
forest_paint:
        lda     forest_distance
        beq     @done
        ldx     forest_start
@row:   cpx     #HUD_ROWS
        bcc     @next
        lda     scene_opaque
        beq     @pixel
        lda     scene_depth
        cmp     forest_distance
        bcs     @pixel
        lda     sprite_rows,x
        bpl     @next
@pixel: lda     hgr_lo,x
        sta     hp
        lda     hgr_hi,x
        sta     hp+1
        ldy     be
        lda     (hp),y
        and     me
        sta     (hp),y
        ldy     bo
        lda     (hp),y
        and     mo
        sta     (hp),y
        lda     view_dark
        bne     @next
        cpx     forest_start
        beq     @next           ; continuous black contour against sky/ground
        cpx     forest_crown_end
        bcs     @next           ; trunk is solid black, crown keeps its stipple
        txa
        eor     forest_x
        lsr
        bcc     @next
        lda     (hp),y
        ora     ob              ; opaque Sierra green/black stipple
        sta     (hp),y
@next:  inx
        cpx     forest_end
        bcc     @row
@done:  rts
