; Optional departure checklist. UI state only: never part of SAVE.
.pushseg
.segment "TEXT"
dep_mask: .res 2
dep_cursor: .byte 0
dep_running: .byte 0
.popseg

.segment "NAVIGATION"
DEP_COUNT = 14
module_departure:
        lda     #0
        sta     dep_mask
        sta     dep_mask+1
        sta     dep_cursor
        sta     dep_running
        jmp     dep_draw

module_departure_resume:
        lda     #0
        sta     mq_n
        lda     journey_encounters
        cmp     mq_enc
        bne     dep_refused
        ldx     mq_noun
        cpx     #N_WATER
        bne     @gear
        lda     it_pack_lo+N_WATER
        cmp     dep_cursor
        beq     dep_refused
        bcc     dep_refused
        bcs     @success
@gear:  cpx     #23
        bne     @place
        lda     it_gnd_lo+23
        ora     it_gnd_hi+23
        bne     dep_refused
        beq     @success
@place: lda     it_place,x
        cmp     #2
        beq     @success
        cmp     #3
        bne     dep_refused
@success:
        ldx     #0
@find:  lda     dep_ids,x
        cmp     mq_noun
        beq     @clear
        inx
        bne     @find
@clear: jsr     dep_toggle
        jmp     dep_next
dep_refused:
        lda     #2
        sta     dep_running
        lda     #0
        sta     dep_cursor
        jmp     dep_draw

dep_draw:
        jsr     text_mode80
        jsr     text_begin
        lda     #0
        sta     WNDTOP
        jsr     nav_at
        jsr     puts
        .byte "PREPARE DEPARTURE - OPTIONAL EQUIPMENT",0
        jsr     topo_pad
        lda     #1
        jsr     nav_at
        jsr     puts
        .byte "SELECT LOCAL STOCK. NO TRANSFER UNTIL CONFIRMATION.",0
        jsr     topo_pad
        lda     #2
        jsr     nav_at
        jsr     puts
        .byte "REQUEST: GET WATER 64 OZ; PACK ALL LOCAL NUTS; EQUIPMENT ONE EACH.",0
        jsr     topo_pad
        lda     #0
        sta     dep_row
@row:   lda     dep_row
        clc
        adc     #3
        jsr     nav_at
        lda     #$FF
        ldx     dep_row
        cpx     dep_cursor
        bne     :+
        lda     #$3F
:       sta     INVFLG
        jsr     dep_selected
        lda     #' '
        bcc     :+
        lda     #'X'
:       ora     #$80
        jsr     COUT
        jsr     puts
        .byte "  ",0
        ldx     dep_row
        lda     dep_ids,x
        tax
        lda     it_name_lo,x
        sta     gp2
        lda     it_name_hi,x
        sta     gp2+1
        ldy     #0
@name:  lda     (gp2),y
        beq     @named
        ora     #$80
        jsr     COUT
        iny
        bne     @name
@named:
        lda     #27
        jsr     tab
        ldx     dep_row
        jsr     dep_available
        bcc     @unavailable
        jsr     puts
        .byte "LOCAL",0
        jmp     @pad
@unavailable:
        ldx     dep_row
        lda     dep_ids,x
        tax
        lda     it_place,x
        beq     @missing
        cmp     #5
        bcs     @missing
        jsr     puts
        .byte "ALREADY CARRIED",0
        jmp     @pad
@missing:
        jsr     puts
        .byte "NOT AVAILABLE HERE",0
@pad:   jsr     topo_pad
        inc     dep_row
        lda     dep_row
        cmp     #DEP_COUNT
        jcc     @row
        lda     #18
        jsr     nav_at
        lda     #$FF
        ldx     dep_cursor
        cpx     #DEP_COUNT
        bne     :+
        lda     #$3F
:       sta     INVFLG
        jsr     puts
        .byte "REVIEW AND APPLY SELECTED TRANSFERS",0
        jsr     topo_pad
        lda     #$FF
        sta     INVFLG
        lda     #19
        jsr     nav_at
        jsr     puts
        .byte "CURRENT LOAD ",0
        ldy     #0
        jsr     dep_used
        jsr     puts
        .byte " OZ. FREE: PACK ",0
        ldy     #4
        jsr     dep_free
        jsr     puts
        .byte "  HANDS ",0
        ldy     #6
        jsr     dep_free
        jsr     puts
        .byte " IN3",0
        jsr     topo_pad
        lda     dep_running
        cmp     #2
        jeq     @footer         ; keep the native refusal intact in rows 20-22
        lda     #20
        jsr     nav_at
        jsr     dep_forecast
        jsr     puts
        .byte "IF ALL FIT: ",0
        ldy     #0
        jsr     dep_forecast_print
        jsr     puts
        .byte " OZ; PACK ",0
        ldy     #4
        jsr     dep_forecast_print
        jsr     puts
        .byte " / ",0
        ldy     #4
        jsr     dep_limit_print
        jsr     puts
        .byte "; HANDS ",0
        ldy     #6
        jsr     dep_forecast_print
        jsr     puts
        .byte " / ",0
        ldy     #6
        jsr     dep_limit_print
        jsr     puts
        .byte " IN3",0
        jsr     topo_pad
        lda     #21
        jsr     nav_at
        lda     dep_running
        cmp     #2
        beq     @failed
        cmp     #3
        jeq     @complete
        jsr     puts
        .byte "BACKPACK AND CANTEEN FIRST; STOP AT THE FIRST REFUSAL.",0
        jmp     @status
@failed:
        jsr     puts
        .byte "STOPPED: LAST TRANSFER REFUSED OR INTERRUPTED. CHECK OBJECTS.",0
        jmp     @status
@complete:
        jsr     puts
        .byte "SELECTED TRANSFERS COMPLETED. MANUAL PREPARATION REMAINS AVAILABLE.",0
@status:jsr     topo_pad
        lda     #22
        jsr     nav_at
        jsr     topo_pad
@footer:
        lda     #23
        jsr     nav_at
        lda     dep_running
        cmp     #2
        beq     @refusal_keys
        cmp     #4
        beq     @confirm
        jsr     puts
        .byte "UP/DOWN CHOOSE  RETURN TOGGLE / REVIEW  ESC VIEW",0
        jmp     @ready
@refusal_keys:
        jsr     puts
        .byte "STOPPED - NATIVE REASON ABOVE. ARROWS REVIEW  ESC VIEW",0
        jmp     @ready
@confirm:
        jsr     puts
        .byte "RETURN CONFIRM GROUP  ESC BACK TO CHECKLIST",0
@ready: jsr     topo_pad
        jsr     text_release
        jsr     show_text
dep_key:
        jsr     wait_key
        cmp     #KC_ESC
        beq     @escape
        ldx     dep_running
        cpx     #4
        beq     @confirmation
        cmp     #KC_UP
        beq     @up
        cmp     #KC_DOWN
        beq     @down
        cmp     #KC_RET
        bne     dep_key
        ldx     dep_cursor
        cpx     #DEP_COUNT
        beq     @review
        jsr     dep_available
        bcc     dep_key
        ldx     dep_cursor
        jsr     dep_toggle
        jmp     dep_draw
@up:    dec     dep_cursor
        bpl     @draw
        lda     #DEP_COUNT
        sta     dep_cursor
        bne     @draw
@down:  inc     dep_cursor
        lda     dep_cursor
        cmp     #DEP_COUNT+1
        bcc     @draw
        lda     #0
        sta     dep_cursor
@draw:  jmp     dep_draw
@review:lda     #4
        sta     dep_running
        bne     @draw
@confirmation:
        cmp     #KC_RET
        bne     dep_key
        jmp     dep_next
@escape:
        lda     dep_running
        cmp     #4
        bne     @leave
        lda     #0
        sta     dep_running
        jmp     dep_draw
@leave: lda     #0              ; discard checklist selection before UI reuse
        sta     dep_mask
        sta     dep_mask+1
        jmp     show_view

; A selected local item becomes exactly one native command plus callback.
; Loading SITES and GRID is a tail transfer: both may replace this code.
dep_next:
        ldx     #0
@scan:  jsr     dep_selected
        bcs     @take
        inx
        cpx     #DEP_COUNT
        bcc     @scan
        lda     #3
        sta     dep_running
        lda     #0
        sta     dep_cursor
        jmp     dep_draw
@take:  lda     dep_ids,x
        sta     mq_noun
        jsr     dep_command
        lda     it_pack_lo+N_WATER
        sta     dep_cursor
        lda     #1
        sta     dep_running
        lda     #10
        jsr     overlay_load
        jmp     departure_execute

; Compose the same explicit native line as the manual transfer. No stock writes.
dep_command:
        lda     #0
        sta     linelen
        lda     #<dep_pack
        ldx     #>dep_pack
        ldy     mq_noun
        cpy     #21
        beq     @carry
        cpy     #64
        bne     @water
@carry: lda     #<dep_carry
        ldx     #>dep_carry
@water: cpy     #N_WATER
        bne     @verb
        lda     #<dep_water
        ldx     #>dep_water
@verb:  sta     gp2
        stx     gp2+1
        jsr     dep_append
        ldx     mq_noun
        cpx     #N_WATER
        beq     @done
        cpx     #66
        bne     @canteen_name
        lda     #<dep_flashlight
        sta     gp2
        lda     #>dep_flashlight
        sta     gp2+1
        jmp     @append_name
@canteen_name:
        cpx     #64
        bne     @ordinary_name
        lda     #<dep_canteen
        sta     gp2
        lda     #>dep_canteen
        sta     gp2+1
        jmp     @append_name
@ordinary_name:
        lda     it_name_lo,x
        sta     gp2
        lda     it_name_hi,x
        sta     gp2+1
@append_name:
        jsr     dep_append
@done:  ldx     linelen
        lda     #0
        sta     inbuf,x
        rts
dep_append:
        ldy     #0
        ldx     linelen
@char:  lda     (gp2),y
        beq     @done
        and     #$7F
        sta     inbuf,x
        inx
        iny
        bne     @char
@done:  stx     linelen
        rts
dep_pack: .byte "PACK ",0
dep_carry: .byte "CARRY ",0
dep_water: .byte "GET WATER 64 OZ",0
dep_canteen: .byte "CANTEEN",0
dep_flashlight: .byte "FLASHLIGHT",0

; No simulation or inventory mutation while selecting/reviewing.
dep_selected:
        txa
        and     #7
        tay
        lda     forest_masks,y
        cpx     #8
        bcc     :+
        and     dep_mask+1
        jmp     @test
:       and     dep_mask
@test:  cmp     #1
        rts
dep_toggle:
        txa
        and     #7
        tay
        lda     forest_masks,y
        cpx     #8
        bcc     :+
        eor     dep_mask+1
        sta     dep_mask+1
        rts
:       eor     dep_mask
        sta     dep_mask
        rts
dep_available:
        lda     dep_ids,x
        tax
        lda     it_x,x
        cmp     px+1
        bne     @no
        lda     it_y,x
        cmp     py+1
        bne     @no
        cpx     #N_WATER
        beq     @quantity
        cpx     #23
        beq     @quantity
        lda     it_place,x
        cmp     #0
        beq     @yes
@no:    clc
        rts
@quantity:
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @no
@yes:   sec
        rts
dep_free:
        sec
        lda     load_limits,y
        sbc     load_used,y
        sta     num
        lda     load_limits+1,y
        sbc     load_used+1,y
        sta     num+1
        bcs     dep_print
        lda     #0
        sta     num
        sta     num+1
        beq     dep_print
dep_used:
        lda     load_used,y
        sta     num
        lda     load_used+1,y
        sta     num+1
dep_print:
        jmp     print_u16

; Compute requested totals in scratch, without moving or temporarily changing
; any item. Water's explicit 64 OZ adds 128 IN3 to the canteen's destination.
; The native commands still check source quantities and every capacity.
dep_forecast:
        ldx     #7
@copy:  lda     load_used,x
        sta     dep_after,x
        dex
        bpl     @copy
        lda     #0
        sta     dep_row
@item:  ldx     dep_row
        jsr     dep_selected
        jcc     @next
        ldx     dep_row
        lda     dep_ids,x
        tax
        cpx     #N_WATER
        beq     @water
        cpx     #23
        beq     @nuts
        lda     it_oz_lo,x
        sta     dep_amount
        lda     it_oz_hi,x
        sta     dep_amount+1
        ldy     #0
        jsr     dep_add
        cpx     #21
        jeq     @next
        lda     it_vol_lo,x
        sta     dep_amount
        lda     it_vol_hi,x
        sta     dep_amount+1
        ldy     #4
        cpx     #64
        bne     @volume
        ldy     #6
        bne     @volume
@nuts:  lda     it_gnd_lo+23
        sta     dep_amount
        lda     it_gnd_hi+23
        sta     dep_amount+1
        ldy     #0
        jsr     dep_add
        lda     it_vol_lo+23
        sta     dep_multiple
@nutvol:
        ldy     #4
        jsr     dep_add
        dec     dep_multiple
        bne     @nutvol
        beq     @next
@water: lda     #64
        sta     dep_amount
        lda     #0
        sta     dep_amount+1
        tay
        jsr     dep_add
        lda     #128
        sta     dep_amount
        ldy     #6
        lda     it_place+64
        cmp     #2
        bne     @volume
        ldy     #4
@volume:jsr     dep_add
@next:  inc     dep_row
        lda     dep_row
        cmp     #DEP_COUNT
        jcc     @item
        rts
dep_add:
        clc
        lda     dep_after,y
        adc     dep_amount
        sta     dep_after,y
        lda     dep_after+1,y
        adc     dep_amount+1
        sta     dep_after+1,y
        bcc     :+
        lda     #$FF
        sta     dep_after,y
        sta     dep_after+1,y
:       rts
dep_forecast_print:
        lda     dep_after,y
        sta     num
        lda     dep_after+1,y
        sta     num+1
        jmp     print_u16
dep_limit_print:
        lda     load_limits,y
        sta     num
        lda     load_limits+1,y
        sta     num+1
        jmp     print_u16
dep_row: .byte 0
dep_amount: .res 2
dep_multiple: .byte 0
dep_after: .res 8
dep_ids: .byte 21,64,22,23,53,38,40,41,59,66,67,73,11,12
