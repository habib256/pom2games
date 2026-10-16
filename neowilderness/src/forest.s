; Woodland coverage and Sierra tree profiles. Uses the retired HELLO RAM,
; never DOS vectors. Every result depends on world/ray coordinates, not col.
.segment "WOODS"
forest_bits: .res 294             ; 56 x 42, one bit / four world units
.segment "GDATA"
forest_enabled: .byte 1
.segment "ZEROPAGE"
forest_x: .res 1               ; forest_x + 2 = forest_y (axis index 0 / 2)
forest_tmp: .res 1
forest_y: .res 1
forest_distance: .res 1
forest_start: .res 1
forest_end: .res 1
forest_base: .res 2
forest_lo: .res 1
forest_hi: .res 1
forest_sign: .res 1
forest_proj: .res 2
forest_masked: .res 1
forest_pair: .res 1
; forest_crown_end: game.s GZP (its address stays $ED, before tilt).

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
        ldx     tilt            ; looking up: no tree (the original's rule)
        dex
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
        jsr     forest_candidate
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
        ldx     #0              ; along x, transverse y
        beq     @fraction
@x:     lda     rx
        ldx     #2              ; along y, transverse x
@fraction:
        ; Each cell contains a narrow, centred crown, not a two-cell wall.
        ; 32 native columns span 1/4 cell: the surrounding gaps stay clear.
        sec
        sbc     #96
        bcc     @empty
        lsr
        cmp     #31
        bcs     @empty
        sta     forest_lo       ; unfolded column, for forest_crown
        jmp     forest_centre
@empty: sec
        rts

.segment "FORESTCODE"
; Keep a black lower rim above the native canopy bottom at height 31.
forest_crown_floor = forest_projection+6 ; scenario data: foliage/trunk boundary
.export forest_crown_floor
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
        lda     forest_proj     ; dz + 128 of the crown's cell (forest_candidate)
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
        ; base = thoriz -+ proj: 95 at level, -1 looking down (dhgr.s
        ; tilt_frame); a foot above the view is outside.
        lda     thoriz+1
        sta     forest_base+1
        lda     thoriz
        ldx     forest_sign
        bmi     @below
        sec
        sbc     forest_proj
        sta     forest_base
        bcs     @check
        dec     forest_base+1
        bcc     @check
@below: clc
        adc     forest_proj
        sta     forest_base
        bcc     @check
        inc     forest_base+1
@check: lda     forest_base+1
        bmi     @outside
        clc
        rts
@outside:
        sec
        rts

.segment "CODE"
; C clear when the sample of the ray (Y = x cell, rowsl the row) meets a crown:
; forest_x, forest_y = the crown's own cell (forest_centre), forest_proj = its
; dz + 128, forest_lo / forest_hi = the heights of the column. The cell must
; be dry, wooded and under the timberline.
forest_candidate:
        sty     forest_x
        lda     rowsl
        ldy     dy+1
        bmi     :+
        eor     #255
        clc
        adc     #GH
:       sta     forest_y
        jsr     forest_profile
        bcs     @no
        ldy     forest_x
        ldx     forest_y
        jsr     cell_at
        bmi     @no             ; water
        tay
        clc
        adc     eyeb
        sta     forest_proj
        tya
        clc
        adc     M_BASE
        ldx     MAP+27
        bne     :+
        ldx     #110
:       stx     forest_tmp
        cmp     forest_tmp
        bcs     @no
        ldx     forest_x
        ldy     forest_y
        jsr     forest_contains
        bcs     forest_crown
@no:    sec
        rts
; Heights of crown column forest_lo of the cell forest_x, forest_y.
forest_crown:
        lda     forest_lo
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


.segment "FORESTCODE"
forest_limit: .byte GW, 0, GH

; A = cell, Y = fraction, X = axis: A = |(A * 256 + Y - px,x + 8) >> 4|
; (an arithmetic shift; |difference| < 4096).
forest_dist:
        sta     forest_base+1
        tya
        sec
        sbc     px,x
        tay
        lda     forest_base+1
        sbc     px+1,x
        sta     forest_base+1
        tya
        clc
        adc     #8
        bcc     :+
        inc     forest_base+1
:       ldy     #4
@div:   lsr     forest_base+1
        ror     a
        dey
        bne     @div
        ldy     forest_base+1   ; 0 if positive, 15 if negative
        beq     :+
        eor     #$FF
        clc
        adc     #1
:       rts

.segment "CODE"
; A * A: A = high byte, forest_tmp = low byte (Y = 0, forest_hi clobbered).
forest_square:
        sta     forest_tmp
        sta     forest_hi
        lda     #0
        ldy     #8
        lsr     forest_tmp
@bit:   bcc     :+
        clc
        adc     forest_hi
:       ror     a
        ror     forest_tmp
        dey
        bne     @bit
        rts

.segment "TEXT"
; One crown, one cell (tools/forest_ref.centre_cell). The samples of all the
; columns at step n lie on the circle of radius n cells around the player; a
; crown stands on the transverse centre line of its cell, so its centre column
; meets it where that circle crosses the line. An edge column may sample the
; crown across a cell boundary B along the ray: it must still take the
; crown's own cell (base, profile kind, stipple phase), or the sides of the
; triangle drop to the base of the next cell. Only samples within 64 units of
; B can differ (a centre is within 38 units of its samples); they compare, in
; rounded 1/16 cells, lat^2 + d^2 with (16 n)^2: d = |B - player| along, lat =
; |centre line - player| across. Column-independent, so a pan redraws the
; same crowns. X = 2 * along axis (0 x, 2 y); C set: outside the map.
forest_centre:
        lda     rx,x
        cmp     #64
        bcc     @edge           ; C clear: B = cell * 256
        cmp     #192
        bcc     @own            ; most samples: their own cell
@edge:  lda     forest_x,x      ; C set: B = (cell + 1) * 256
        adc     #0
        sta     forest_end
        ldy     #0
        jsr     forest_dist
        jsr     forest_square
        sta     forest_start    ; d^2
        lda     forest_tmp
        sta     forest_sign
        lda     forest_distance
        jsr     forest_square
        lda     forest_tmp
        sta     forest_pair     ; n^2
        txa
        eor     #2
        tax
        lda     forest_x,x
        ldy     #127
        jsr     forest_dist
        jsr     forest_square   ; lat^2
        tay
        lda     forest_tmp
        clc
        adc     forest_sign
        tya
        adc     forest_start
        cmp     forest_pair     ; C clear: B before the centre (beyond)
        txa
        eor     #2
        tax
        ldy     dx+1,x          ; cell = B - (C xor ray towards -axis):
        bmi     :+              ; towards +axis, invert C, then
        rol     a               ; B - 1 + C
        eor     #1
        ror     a
:       lda     forest_end
        sbc     #0
        sta     forest_x,x
        cmp     forest_limit,x  ; -1 wraps to 255
        rts
@own:   clc
        rts
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
; Rows forest_start..forest_end-1 (never the HUD rows 0..15): contour on the
; first row, crown down to forest_crown_end (checkerboard on row ^ cell x,
; like the Sierra stipple), then trunk; colours of the mood.
forest_paint:
        lda     forest_distance
        beq     @done
        ldx     #0              ; a nearer sprite keeps its rows
        lda     scene_opaque
        beq     :+
        lda     scene_depth
        cmp     forest_distance
        bcs     :+
        inx
:       stx     forest_masked
        ldy     forest_start
        cpy     #HUD_ROWS
        bcc     @crown
        iny
        sty     sp_end
        dey
        lda     cur_pal+PAL_OUTLINE
        jsr     forest_span
@crown: ldy     forest_start
        iny
        cpy     #HUD_ROWS
        bcs     :+
        ldy     #HUD_ROWS
:       sty     forest_tmp
        lda     forest_crown_end
        cmp     forest_end
        bcc     :+
        lda     forest_end
:       sta     sp_end
        lda     ang             ; a: rows where row + azimuth is even
        eor     forest_x
        lsr     a
        lda     cur_pal+PAL_CROWN+1
        ldx     cur_pal+PAL_CROWN
        bcc     :+
        lda     cur_pal+PAL_CROWN
        ldx     cur_pal+PAL_CROWN+1
:       and     #$F0
        sta     forest_pair
        txa
        and     #$0F
        ora     forest_pair
        jsr     forest_span
        ldy     forest_tmp
        cpy     forest_crown_end
        bcs     :+
        ldy     forest_crown_end
:       lda     forest_end
        sta     sp_end
        lda     cur_pal+PAL_TRUNK
        jmp     forest_span
@done:  rts
; forest_span -- entry A on rows Y..sp_end-1, under the sprite mask if any.
forest_span:
        ldx     forest_masked
        bne     :+
        jmp     dspan
:       sta     scene_colour
        jmp     scene_masked
; The render scratch ($50..) ends below $A4, Applesoft's rounding byte, which
; FMULT reads before writing it (docs/MEMORY.md).
.assert forest_pair < $A4, error, "render zero page reaches $A4"
