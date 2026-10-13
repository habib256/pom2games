; Tree actions and hung backpack from native $5156 and T12/S08.
.segment "LOWCODE"
module_tree_look:
        lda     noun
        cmp     #152            ; L
        beq     @left
        cmp     #151            ; R
        beq     @right
        cmp     #157            ; B
        beq     @back
        cmp     #155            ; AZ
        beq     @az
        cmp     #156            ; F
        beq     @front
        cmp     #145            ; N E S W
        bcc     @what
        cmp     #149
        bcs     @what
@card:  sec                     ; N E S W -> heading 0, 140, 280, 420
        sbc     #145
        tax
        lda     card_lo,x
        sta     heading
        lda     card_hi,x
        sta     heading+1
@aim:   jsr     magnetic_heading
@front: jmp     show_view
@left:  ldx     #2
        jmp     turn_view
@right: ldx     #3
        jmp     turn_view
@back:  clc                     ; 180 degrees
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
@az:    jmp     do_look_az
@what:  jmp     look_invalid

.export tree_look_aim := @aim

; Placement 5 stores the pack and its contents at the pack's ground anchor.
.segment "TREE"
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
tree_saved_places: .res 76
tree_up_msg: .byte "IN A TREE. CLIMB DOWN TO MOVE.|ANIMALS CAN STILL REACH YOU.",0
tree_down_msg: .byte "BACK ON THE GROUND.",0
tree_poor_msg: .byte "YOUR PHYSICAL CONDITION IS TOO POOR.",0
tree_trapped_msg: .byte "YOU ARE IN A TREE. CLIMB DOWN FIRST.",0
tree_missing_msg: .byte "YOU ARE NOT NEAR A TREE.",0
tree_hang_msg: .byte "HANGING YOUR BACKPACK AND ITS FOOD.",0
tree_lower_msg: .byte "BACKPACK AND CONTENTS RECOVERED.",0
tree_already_msg: .byte "YOUR BACKPACK IS ALREADY HANGING.",0
tree_needpack_msg: .byte "YOU NEED A PACK TO HANG YOUR FOOD IN.",0
tree_full_msg: .byte "TRANSFER REFUSED: LOAD CAPACITY.",0
