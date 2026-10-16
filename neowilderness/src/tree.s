; Tree actions and hung backpack from native $5156 and T12/S08.
.segment "LOWCODE"
module_tree_look:
        jsr     orient_look     ; lot 7: SUN, STARS, objects, aid rule (orient.s)
        lda     noun
        cmp     #149            ; U, UP
        beq     look_up
        cmp     #150            ; D, DOWN
        beq     look_down
        cmp     #152            ; L
        beq     @left
        cmp     #151            ; R
        beq     @right
        cmp     #157            ; B
        beq     @back
        cmp     #156            ; F, AHEAD, FORWARD
        beq     look_front
        jmp     look_invalid    ; N E S W, AZ: orient_look (src/orient.s)
@aim:   jsr     magnetic_heading
        jmp     show_view
@left:  ldx     #2
        jmp     turn_view
@right: ldx     #3
        jmp     turn_view
@back:  lda     #0              ; LOOK B levels the view (SURV3D $1028)
        sta     tilt
        clc                     ; 180 degrees
        lda     heading
        adc     #<280
        sta     ang
        lda     heading+1
        adc     #>280
        sta     ang+1
        jsr     wrap_ang
        lda     ang
        sta     heading
        lda     ang+1
        sta     heading+1
        jmp     show_view


.export tree_look_aim := @aim

; LOOK UP / DOWN / AHEAD, PAN UP / DOWN (SURV3D $0FA9, docs/LOOK_UPDOWN.md):
; three tilts. LOOK sets one, PAN steps toward it and stops at the end;
; PAN AHEAD does nothing. An unchanged tilt redraws nothing (LOOK AHEAD at
; level still shows the view, as before). Inside the cabin the tilt does
; not change. Looking down is refused ("NOT NOW.", the original's short
; message 64) while a standing animal is at contact. No game time.
look_up:
        ldx     #1
        lda     verb
        cmp     #V_PAN
        bne     look_tilt
        ldx     tilt
        inx
        cpx     #2
        bne     look_tilt
        rts
look_down:
        ldx     #$FF
        lda     verb
        cmp     #V_PAN
        bne     look_tilt
        ldx     tilt
        dex
        cpx     #$FE
        bne     look_tilt
        rts
look_front:
        lda     verb
        cmp     #V_PAN
        beq     look_rts
        ldx     #0
        cpx     tilt
        beq     look_view
look_tilt:
        cpx     tilt
        beq     look_rts
        lda     shelter_inside
        bne     look_view
        txa
        bpl     look_set
        jsr     look_standing
        ldx     #$FF            ; the only negative tilt
        bcc     look_set
        lda     #<m_notnow
        ldx     #>m_notnow
        jmp     message
look_set:
        stx     tilt
        lda     #0              ; the sprite ceiling depends on the tilt
        sta     scene_cache_valid
look_view:
        jmp     show_view
look_rts:
        rts

; look_standing -- carry set when an animal at contact stands (the
; original's sprite flag bit 7, Journey T0D/SE $5F7D: by region and slot,
; the bear in the Sierra Nevada; the snakes and the cougar lie low).
look_standing:
        lda     animal_kind
        beq     @no
        lda     px+1
        cmp     animal_x
        bne     @no
        lda     py+1
        cmp     animal_y
        bne     @no
        ldy     region_number
        cpy     #7
        bcs     @no
        lda     animal_kind     ; 6, 7, 8: slots 1-3; 9 never stands
        sec
        sbc     #5
        tax
        lda     look_stand_bits,y
@bit:   lsr     a
        dex
        bne     @bit
        rts                     ; carry = bit of the slot
@no:    clc
        rts
; Slots 1-3 that stand, by region (0: a legacy map, the Sierra Nevada):
; T0D/SE $5F86: slot 1 unless region 3, slot 2 in region 3, slot 3 in
; region 1, none from region 5.
look_stand_bits: .byte %001, %101, %001, %010, %001, 0, 0

; Placement 5 stores the pack and its contents at the pack's ground anchor.
.segment "ORIENT"
module_tree_command:
        lda     verb
        cmp     #V_CLIMB
        beq     tree_climb
        cmp     #V_HANG
        jeq     tree_hang
        cmp     #V_LOWER
        jeq     tree_lower
        cmp     #V_GET
        jeq     tree_lower
        cmp     #V_CARRY
        jeq     tree_lower
        cmp     #V_PACK
        jeq     tree_lower
        jmp     tree_trapped

tree_climb:
        lda     noun
        cmp     #173            ; TREE
        beq     @toggle
        cmp     #150            ; DOWN
        bne     @direction
        lda     tree_in
        bne     @down
@direction:
        lda     tree_in
        bne     tree_trapped
        lda     noun
        beq     @walk
        cmp     #149            ; UP
        beq     @walk
        cmp     #150
        bne     tree_bad
@walk:  jmp     do_walk
@toggle:
        lda     tree_in
        bne     @down
        jsr     tree_here
        bcc     tree_missing
        fld     s_health
        fop     FCOMP, tree_health_min
        cmp     #1              ; native strictly greater than 2.5
        bne     @poor
        lda     #1
        sta     tree_in
        jsr     load_totals
        lda     #<tree_up_msg
        ldx     #>tree_up_msg
        jmp     message
@down: lda     #0
        sta     tree_in
        jsr     load_totals
        lda     #<tree_down_msg
        ldx     #>tree_down_msg
        jmp     message
@poor: lda     #<tree_poor_msg
        ldx     #>tree_poor_msg
        jmp     message

tree_trapped:
        lda     #<tree_trapped_msg
        ldx     #>tree_trapped_msg
        jmp     message
tree_missing:
        lda     #<tree_missing_msg
        ldx     #>tree_missing_msg
        jmp     message
tree_bad:
        lda     #<m_oops
        ldx     #>m_oops
        jmp     message

tree_here:
        lda     shelter_inside
        bne     @no
        jsr     woods_here
        bcc     @no
        jsr     level_here
        clc
        adc     M_BASE
        sta     tree_height
        lda     MAP+27
        bne     :+
        lda     #110
:       cmp     tree_height
        beq     @no
        bcc     @no
        sec
        rts
@no:    clc
        rts

tree_hang:
        jsr     tree_here
        jcc     tree_missing
        lda     noun
        cmp     #135            ; FOOD
        beq     @pack
        cmp     #21             ; BACKPACK (alias)
        jne     tree_bad
@pack: lda     it_place+21
        cmp     #5
        beq     @already
        cmp     #255
        beq     @needpack
        ldx     #21
        jsr     have
        bcc     @needpack
        lda     it_place+21
        sta     tree_pack_place
        lda     px+1
        sta     it_x+21
        lda     py+1
        sta     it_y+21
        lda     it_place+64
        cmp     #2
        bne     @items
        lda     #5
        sta     it_place+22      ; packed canteen's water follows it
@items: ldx     #75
@item: lda     it_place,x
        cmp     #2
        bne     @next
        cpx     #22             ; hand-held canteen remains available
        beq     @next
        lda     #5
        sta     it_place,x
@next: dex
        bne     @item
        ; Split food retains its independent ground pile and coordinates.
        ldx     #23
@food: lda     it_pack_lo,x
        ora     it_pack_hi,x
        beq     :+
        lda     #5
        sta     it_place,x
:       inx
        cpx     #38
        bcc     @food
        lda     #5
        sta     it_place+21
        jsr     load_totals
        lda     #<tree_hang_msg
        ldx     #>tree_hang_msg
        jsr     message
        jmp     tree_spend      ; spend may replace this overlay: never return
@already:
        lda     #<tree_already_msg
        ldx     #>tree_already_msg
        jmp     message
@needpack:
        lda     #<tree_needpack_msg
        ldx     #>tree_needpack_msg
        jmp     message

tree_lower:
        lda     noun
        cmp     #135
        beq     @pack
        cmp     #21
        jne     tree_bad
@pack: lda     it_place+21
        cmp     #5
        bne     @unreachable
        ldx     #21
        jsr     at_ground
        bcc     @unreachable
        ldx     #75
@restore:
        lda     it_place,x
        sta     tree_saved_places,x
        cmp     #5
        bne     @next
        lda     #2
        cpx     #22
        bcc     @set
        cpx     #38
        bcs     @set
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @packed
        lda     #4
        bne     @set
@packed:
        lda     #2
@set:  sta     it_place,x
@next: dex
        bne     @restore
        lda     tree_pack_place
        bne     :+
        lda     #3              ; originally on ground: retrieve in hand
:       sta     it_place+21
        jsr     load_totals
        lda     load_bad
        bne     @rollback
        ldy     #6
@capacity:
        lda     load_limits,y
        cmp     load_used,y
        lda     load_limits+1,y
        sbc     load_used+1,y
        bcc     @rollback
        dey
        dey
        bpl     @capacity
        lda     #<tree_lower_msg
        ldx     #>tree_lower_msg
        jmp     message
@rollback:
        ldx     #75
@copy: lda     tree_saved_places,x
        sta     it_place,x
        dex
        bne     @copy
        jsr     load_totals
        lda     #<tree_full_msg
        ldx     #>tree_full_msg
        jmp     message
@unreachable:
        lda     #<m_noitem
        ldx     #>m_noitem
        jmp     message

tree_height: .byte 0
tree_health_min: .byte $82,$20,0,0,0
tree_saved_places = tb_buf       ; rollback only; no text fetch before restore
.assert TB_MAX >= 76, error, "tree rollback scratch"

        .include "orient.s"     ; lot 7: orientation

        .include "object_menu.s"

        .include "equipment.s"
