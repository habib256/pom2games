; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Scene geometry only. Returns before the resident wrapper loads the raw
; asset; no overlay calls into another overlay. Nearby sites are billboards,
; one per view, nearest visible first; local sites/animals keep original art.
.segment "PROJECT"
module_project:
        lda     #0
        sta     scene_asset
        sta     scene_drawn
        lda     #9
        sta     proj_best
        lda     px+1
        cmp     M_STARTX+1
        bne     @cabin
        lda     py+1
        cmp     M_STARTY+1
        bne     @cabin
        lda     M_HEAD
        sta     proj_bearing
        lda     M_HEAD+1
        sta     proj_bearing+1
        lda     #5
        jmp     project_local
@cabin: lda     MAP+16
        beq     @animal
        lda     px+1
        cmp     MAP+17
        bne     @animal
        lda     py+1
        cmp     MAP+18
        bne     @animal
        lda     MAP+19
        sta     proj_bearing
        lda     MAP+20
        sta     proj_bearing+1
        lda     #9
        jmp     project_local
@animal:
        lda     animal_kind
        beq     @remote
        lda     px+1
        cmp     animal_x
        bne     @remote
        lda     py+1
        cmp     animal_y
        bne     @remote
        lda     animal_bearing
        sta     proj_bearing
        lda     animal_bearing+1
        sta     proj_bearing+1
        lda     animal_kind
        jmp     project_local
@remote:
        ; With only one nearby candidate its geometry is independent of
        ; heading. Keep it even offscreen so every turn can scroll it back
        ; into view without loading this module. Two coarse candidates keep
        ; the original nearest-visible selection and full-turn fallback.
        jsr     project_wreck
        jsr     project_near
        lda     #0
        rol     a
        sta     proj_candidates
        lda     MAP+16
        beq     @select
        jsr     project_cabin
        jsr     project_near
        bcc     @select
        inc     proj_candidates
        lda     proj_candidates
        cmp     #2
        bcc     @select
        sta     scene_drawn      ; bit 1: selection depends on heading
@select:
        jsr     project_wreck
        jsr     project_candidate
        lda     MAP+16
        beq     @finish
        jsr     project_cabin
        jsr     project_candidate
@finish:
        lda     scene_asset
        beq     @done
        jmp     scene_height_bound
@done:  rts

project_wreck:
        lda     M_STARTX
        sta     proj_x
        lda     M_STARTX+1
        sta     proj_x+1
        lda     M_STARTY
        sta     proj_y
        lda     M_STARTY+1
        sta     proj_y+1
        lda     #5
        sta     proj_asset
        rts
project_cabin:
        lda     #128
        sta     proj_x
        sta     proj_y
        lda     MAP+17
        sta     proj_x+1
        lda     MAP+18
        sta     proj_y+1
        lda     #9
        sta     proj_asset
        rts

project_local:
        sta     proj_asset
        lda     #0
        sta     proj_shift
        sta     proj_depth
        jsr     project_center
        jsr     project_commit
        jmp     scene_height_bound

project_near:
        ; Integer coarse rejection before ROM math. Eight cells in either
        ; axis need the fractional coordinate checked at the radial limit.
        sec
        lda     proj_x+1
        sbc     px+1
        cmp     #9
        bcc     :+
        cmp     #248
        bcs     :+
        clc
        rts
:       sec
        lda     proj_y+1
        sbc     py+1
        cmp     #9
        bcc     :+
        cmp     #248
        bcs     :+
        clc
        rts
:       sec
        rts

project_candidate:
        jsr     project_near
        bcs     :+
        rts
:       sec
        lda     proj_x
        sbc     px
        tay
        lda     proj_x+1
        sbc     px+1
        jsr     GIVAYF
        fop     FMULT, proj_1_256
        fst     t1               ; east, in cells
        fop     FMULT, t1
        fst     t3
        sec
        lda     py
        sbc     proj_y
        tay
        lda     py+1
        sbc     proj_y+1
        jsr     GIVAYF
        fop     FMULT, proj_1_256
        fst     t2               ; north, in cells
        fop     FMULT, t2
        fop     FADD, t3
        jsr     FSQR
        jsr     AYINT
        lda     $A0
        beq     :+
        rts
:
        lda     $A1
        cmp     #8
        bcc     :+
        rts
:
        clc
        adc     #1
        sta     proj_depth       ; billboard inserted at floor(distance)+1
        lda     scene_drawn
        ora     #1
        sta     scene_drawn
        lda     proj_depth
        cmp     proj_best
        bcc     :+
        rts
:
        ; Bearing = atan2(east,north), converted to 560 units per turn.
        fld     t2
        lda     FAC
        beq     @east_west
        fld     t2
        fop     FDIV, t1         ; east / north (memory / FAC)
        jmp     @angle
@east_west:
        lda     #140
        sta     proj_bearing
        lda     #0
        sta     proj_bearing+1
        lda     t1+1
        bpl     @bearing_done
        lda     #<420
        sta     proj_bearing
        lda     #>420
        sta     proj_bearing+1
        jmp     @bearing_done
@angle:
        jsr     FATN
        fop     FMULT, proj_angle
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     proj_bearing
        lda     $A0
        sta     proj_bearing+1
        lda     t2+1
        bpl     @north
        clc
        lda     proj_bearing
        adc     #<280
        sta     proj_bearing
        lda     proj_bearing+1
        adc     #>280
        sta     proj_bearing+1
@north:
        lda     proj_bearing
        sta     ang
        lda     proj_bearing+1
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     proj_bearing
        lda     ang+1
        sta     proj_bearing+1
@bearing_done:
        lda     proj_depth
        ldx     #0
@scale: cmp     #2
        bcc     @scaled
        lsr     a
        inx
        bne     @scale
@scaled:
        stx     proj_shift
        jsr     project_center
        lda     scene_drawn
        cmp     #2
        bcc     @visible         ; sole candidate may remain offscreen
        ; Width overlaps columns 0..139? Keep signed left coordinate.
        lda     proj_left+1
        bmi     @left_edge
        beq     :+
        rts
:
        lda     proj_left
        cmp     #140
        bcc     :+
        rts
:
        jmp     @visible
@left_edge:
        clc
        lda     proj_left
        adc     proj_width
        sta     proj_half
        lda     proj_left+1
        adc     #0
        bpl     :+
        rts
:
        ora     proj_half
        bne     :+
        rts
:
@visible:
        jsr     project_ground
        bcc     :+
        rts
:
        lda     proj_depth
        sta     proj_best
        jmp     project_commit
project_reject:
        rts

project_center:
        ldx     proj_asset
        lda     proj_widths-5,x
        sta     proj_width
        ldx     proj_shift
        beq     @width
@half:  inc     proj_width
        lsr     proj_width
        dex
        bne     @half
@width: lda     proj_bearing
        sta     ang
        lda     proj_bearing+1
        sta     ang+1
        sec
        lda     ang
        sbc     heading
        sta     ang
        lda     ang+1
        sbc     heading+1
        sta     ang+1
        bpl     @positive
        clc
        lda     ang
        adc     #<560
        sta     ang
        lda     ang+1
        adc     #>560
        sta     ang+1
@positive:
        lda     ang
        cmp     #<280
        lda     ang+1
        sbc     #>280
        bcc     @center
        sec
        lda     ang
        sbc     #<560
        sta     ang
        lda     ang+1
        sbc     #>560
        sta     ang+1
@center:
        lda     proj_width
        lsr     a
        sta     proj_half
        lda     #70
        sec
        sbc     proj_half
        clc
        adc     ang
        sta     proj_left
        lda     ang+1
        adc     #0
        sta     proj_left+1
        rts

project_ground:
        jsr     level_here      ; ROM floating point owns the ray's zero page
        clc
        adc     #EYE
        sta     eye
        ldx     proj_y+1
        ldy     proj_x+1
        jsr     cell_at
        and     #127
        sec
        sbc     eye
        sta     proj_dz
        bpl     :+
        eor     #$FF
        clc
        adc     #1
:       pha
        lda     proj_depth
        sta     divisor
        pla
        cmp     divisor
        bcs     @big
        jsr     smalldiv
        sta     qlo
        lda     #0
        sta     qhi
        beq     @row
@big:   jsr     bigdiv
@row:   lda     qlo
        sta     proj_q
        lda     qhi
        sta     proj_q+1
        asl     qlo
        rol     qhi
        clc
        lda     qlo
        adc     proj_q
        sta     qlo
        lda     qhi
        adc     proj_q+1
        sta     qhi
        bcs     @reject         ; 3*q overflow would bring a hidden site onscreen
        lda     proj_dz
        bpl     @shift
        clc
        lda     qlo
        adc     #15
        sta     qlo
        bcc     @shift
        inc     qhi
@shift: ldx     #4
@divide:
        lsr     qhi
        ror     qlo
        dex
        bne     @divide
        lda     qhi
        bne     @reject
        lda     proj_dz
        bmi     @below
        lda     #95
        sec
        sbc     qlo
        bcs     @save
        lda     #0
        beq     @save
@below: lda     #95
        clc
        adc     qlo
        bcs     @reject
        cmp     #252
        bcs     @reject
@save:  sta     proj_anchor
        clc
        rts
@reject:
        sec
        rts

project_commit:
        lda     proj_asset
        sta     scene_asset
        tax
        lda     proj_bases-5,x
        sta     sprite_base
        lda     #10
        cpx     #5
        bne     :+
        lda     #0
:       sta     sprite_origin
        lda     proj_left
        sta     sprite_left
        lda     proj_left+1
        sta     sprite_left+1
        lda     proj_shift
        sta     sprite_shift
        tax
        lda     proj_masks,x
        sta     sprite_mask
        lda     proj_depth
        sta     scene_depth
        clc
        adc     #127
        sta     scene_trigger
        lda     proj_anchor
        sta     sprite_anchor
        lda     scene_drawn
        ora     #1
        sta     scene_drawn
        rts

proj_widths: .byte 119,39,52,33,61
proj_bases: .byte 158,168,151,150,152
proj_masks: .byte 0,1,3,7
proj_1_256: .byte $79,$00,$00,$00,$00
proj_angle: .byte $87,$32,$40,$E7,$C1 ; 560 / (2*pi)
proj_asset: .byte 0
proj_x: .word 0
proj_y: .word 0
proj_bearing: .word 0
proj_left: .word 0
proj_width: .byte 0
proj_half: .byte 0
proj_best: .byte 9
proj_shift: .byte 0
proj_depth: .byte 0
proj_anchor: .byte 0
proj_dz: .byte 0
proj_q: .word 0
proj_candidates: .byte 0

; A conservative highest possible ridge at each future ray distance. This
; is built once per frame, using the SAME division/row tables as the terrain.
; Legacy maps without a maximum use the format limit (125).
.segment "PROJECT"
scene_height_bound:
        lda     scene_drawn
        beq     @done
        jsr     level_here
        clc
        adc     #EYE
        sta     eye
        lda     MAP+21
        bne     :+
        lda     #126
:       sec
        sbc     #1
        sec
        sbc     eye
        bcs     :+
        lda     #0
:       sta     sprite_width     ; width half is no longer needed after prepare
        lda     #1
        sta     scene_distance
@distance:
        lda     scene_distance
        sta     divisor
        lda     sprite_width
        cmp     divisor
        bcs     @big
        jsr     smalldiv
        tax
        lda     row_p0,x
        jmp     @store
@big:   jsr     bigdiv
        tax
        lda     qhi
        cmp     #2
        bcs     @zero
        lda     row_p0,x
        sec
        sbc     #48
        jmp     @store
@zero:  lda     #0
@store: ldy     scene_distance
        dey
        sta     scene_ceiling,y
        inc     scene_distance
        lda     scene_distance
        cmp     #129
        bcc     @distance
@done:  rts
