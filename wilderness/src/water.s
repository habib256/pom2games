; Water collection owns its window; simulation and quantities use resident bridges.
.segment "GCODE"
water_quantity:
        jsr     get_quantity
        php
        lda     #4
        jsr     overlay_load
        plp
        rts
.segment "ENVIRON"
water_native_here:
        jsr     native_here
        pha
        lda     #4
        jsr     overlay_load
        pla
        rts
.segment "WATER"
module_collect:
        lda     #0
        sta     outdoor_minutes
        sta     outdoor_act
        sta     outdoor_result
        lda     noun
        cmp     #N_WATER
        beq     @water
        cmp     #64
        bne     @ordinary
        lda     inbuf
        cmp     #'R'            ; REFILL CANTEEN
        beq     @fill
        cmp     #'F'
        bne     @ordinary
        lda     inbuf+2
        cmp     #'L'            ; FILL, not FIND
        beq     @fill
@ordinary:
        clc
        rts
@water: ldx     #N_WATER
        lda     MAP+37
        bne     @fill
        jsr     at_ground
        bcc     @fill
        lda     it_gnd_lo+N_WATER
        ora     it_gnd_hi+N_WATER
        bne     @ordinary       ; salvage supplies through the existing item rules
@fill:  lda     #1
        sta     outdoor_result
        lda     MAP+37
        bne     @context
        lda     input_argument
        jne     @done
@context:
        lda     tree_in
        ora     shelter_inside
        jne     @done
        jsr     load_totals
        jsr     outdoor_water_here
        jcc     @done
        lda     #2
        sta     outdoor_result
        lda     it_place+64
        jeq     @done
        cmp     #5
        jeq     @done
        cmp     #255
        jeq     @done
        lda     #3
        sta     outdoor_result
        lda     it_pack_hi+N_WATER
        jne     @done
        lda     it_pack_lo+N_WATER
        cmp     #64
        jcs     @done
        lda     MAP+37
        beq     @snapshot
        lda     #<m_ounces
        ldx     #>m_ounces
        jsr     water_quantity
        jcs     @done
@snapshot:
        lda     it_pack_lo+N_WATER
        sta     out_old_water
        lda     it_place+N_WATER
        sta     out_old_place
        lda     it_oz_lo+N_WATER
        sta     out_old_total
        lda     it_oz_hi+N_WATER
        sta     out_old_total+1
        sec
        lda     #64
        sbc     it_pack_lo+N_WATER
        sta     out_added
        lda     MAP+37
        beq     @apply
        lda     msgnum+1
        bne     @apply
        lda     msgnum
        cmp     out_added
        bcs     @apply
        sta     out_added
@apply:
        clc
        lda     out_old_water
        adc     out_added
        sta     it_pack_lo+N_WATER
        clc
        lda     it_oz_lo+N_WATER
        adc     out_added
        sta     it_oz_lo+N_WATER
        lda     it_oz_hi+N_WATER
        adc     #0
        sta     it_oz_hi+N_WATER
        bcs     @rollback       ; keep the 16-bit total atomic too
        lda     #2
        sta     it_place+N_WATER
        lda     it_gnd_lo+N_WATER
        ora     it_gnd_hi+N_WATER
        beq     :+
        lda     #4
        sta     it_place+N_WATER
:       jsr     load_totals     ; SIM lives at $2000, so this module survives
        lda     load_bad
        bne     @rollback
        ldx     #6
@capacity:
        lda     load_limits+1,x
        cmp     load_used+1,x
        bcc     @rollback
        bne     @next
        lda     load_limits,x
        cmp     load_used,x
        bcc     @rollback
@next:  dex
        dex
        bpl     @capacity
        lda     #1
        sta     water_untreated
        lda     MAP+37
        bne     @native_source
        lda     #10
        sta     outdoor_minutes
        bne     @success
@native_source:
        ; T0F/S00 replenishes the accessible river source to 160 ounces,
        ; then transfers the requested amount without advancing time.
        sec
        lda     #160
        sbc     out_added
        sta     it_gnd_lo+N_WATER
        clc
        lda     #160
        adc     out_old_water
        sta     it_oz_lo+N_WATER
        lda     #0
        sta     it_gnd_hi+N_WATER
        sta     it_oz_hi+N_WATER
        lda     #4
        sta     it_place+N_WATER
        lda     px+1
        sta     it_x+N_WATER
        lda     py+1
        sta     it_y+N_WATER
        lda     #1
        sta     water_ground_untreated
@success:
        lda     #4
        sta     outdoor_result
        jne     @done
@rollback:
        lda     out_old_water
        sta     it_pack_lo+N_WATER
        lda     out_old_place
        sta     it_place+N_WATER
        lda     out_old_total
        sta     it_oz_lo+N_WATER
        lda     out_old_total+1
        sta     it_oz_hi+N_WATER
        jsr     load_totals
        lda     #5
        sta     outdoor_result
@done:  sec
        rts

; Current cell or any adjacent bank cell; never reads beyond the map.
outdoor_water_here:
        lda     MAP+37
        beq     @legacy
        jsr     water_native_here
        asl     a
        rts
@legacy:
        lda     py+1
        sec
        sbc     #1
        sta     out_y
        lda     #3
        sta     out_rows
@row:   lda     px+1
        sec
        sbc     #1
        sta     out_x
        lda     #3
        sta     out_cols
@cell:  ldx     out_y
        cpx     #GH
        bcs     @next
        ldy     out_x
        cpy     #GW
        bcs     @next
        jsr     cell_at
        bmi     @yes
@next:  inc     out_x
        dec     out_cols
        bne     @cell
        inc     out_y
        dec     out_rows
        bne     @row
        clc
        rts
@yes:   sec
        rts

out_old_water: .byte 0
out_old_place: .byte 0
out_old_total: .word 0
out_added: .byte 0
out_x: .byte 0
out_y: .byte 0
out_rows: .byte 0
out_cols: .byte 0
