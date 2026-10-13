; Original Journey graphics: raw column streams loaded into the shared $5800
; window. Bitmap bytes remain in ignored build/, never embedded in source.
.segment "GDATA"
scenes_enabled: .byte 1
scene_drawn: .byte 0            ; bit 0: geometry; bit 1: multiple nearby candidates
scene_minutes: .byte 0
animal_kind: .byte 0            ; overlay 6 bear, 7 cougar, 8 rattlesnake
animal_x: .byte 0
animal_y: .byte 0
animal_bearing: .word 0
animal_age: .byte 0
nature_frequency: .byte 1       ; integer multiplier 0..100, original default 1
fauna_rng: .byte $B7            ; independent of the weather RNG
fauna_alert: .byte 0            ; accepted encounter interrupts travel/rest
scene_cache_valid: .byte 0
scene_cache_pos: .res 6
scene_cache_animal: .res 5
scene_cache_drawn: .byte 0
scene_cache_asset: .byte 0
.segment "SCRATCH"
sprite_left: .res 2
sprite_x: .res 1
sprite_width: .res 1
sprite_y: .res 1
sprite_bits: .res 1
sprite_codes: .res 1
sprite_colour: .res 1
sprite_origin: .res 1
scene_asset: .res 1
scene_depth: .res 1              ; 0 local; distant billboard inserted at ray step
sprite_shift: .res 1
sprite_mask: .res 1
sprite_base: .res 1
sprite_anchor: .res 1
scene_trigger: .res 1
scene_pending: .res 1
scene_ray_x: .res 1
sprite_scaled: .res 1
.segment "GCODE"
scene_update:
        ; Clock clears the prior alert before each actual activity. A redraw
        ; must retain a new encounter/attack until the result is displayed.
        lda     scenes_enabled
        beq     @clear
        lda     shelter_inside
        bne     @clear
        lda     nature_frequency
        bne     @time
        lda     animal_kind
        beq     @clear          ; no encounters or presence: no disk/RNG work
@time:
        lda     scene_minutes
        beq     @done
        lda     #3
        jsr     overlay_load
        jsr     module_fauna
@done:  rts
@clear: lda     #0
        sta     scene_minutes
        rts

; Parsing LOOK uses the shared sprite/VOCAB window. Restore the asset
; before reusing the geometry; arrow turns normally need no disk read.
.segment "TEXT"
scene_pan_load:
        lda     #0
        sta     scene_cache_valid ; cached heading no longer matches moved geometry
        lda     scene_asset
        beq     @done
        txa
        pha
        lda     scene_asset
        jsr     overlay_load
        pla
        tax
@done:  rts

.segment "GCODE"
scene_prepare:
        lda     #0
        sta     scene_drawn
        sta     scene_asset
        lda     scenes_enabled
        beq     @done
        lda     scene_cache_valid
        beq     @compute
        ldx     #5
@position:
        lda     px,x
        cmp     scene_cache_pos,x
        bne     @compute
        dex
        bpl     @position
        ldx     #4
@animal:
        lda     animal_kind,x
        cmp     scene_cache_animal,x
        bne     @compute
        dex
        bpl     @animal
        lda     scene_cache_drawn
        sta     scene_drawn
        lda     scene_cache_asset
        sta     scene_asset
        jmp     @load
@compute:
        lda     #11
        jsr     overlay_load
        jsr     module_project
        ldx     #5
@save_pos:
        lda     px,x
        sta     scene_cache_pos,x
        dex
        bpl     @save_pos
        ldx     #4
@save_animal:
        lda     animal_kind,x
        sta     scene_cache_animal,x
        dex
        bpl     @save_animal
        lda     scene_drawn
        sta     scene_cache_drawn
        lda     scene_asset
        sta     scene_cache_asset
        lda     #1
        sta     scene_cache_valid
@load:  lda     scene_asset
        beq     @done
        jmp     overlay_load
@done:  rts

; DOS's saved text is dead after scene_prepare has finished its last BLOAD.
; Reuse those 160 bytes as the current column's colours/transparent mask.
; There must be no disk load inside the ray loop.
sprite_rows = overlay_text
.export sprite_rows
.segment "SCRATCH"
scene_opaque: .res 1
scene_distance: .res 1
scene_colour: .res 1
scene_pos: .res 1
scene_end: .res 1
.segment "CODE"
; Decode and paint ONLY the current column, before direction uses dx/dy/rx.
sprite_column:
        lda     #0
        sta     scene_opaque
        sta     scene_pending
        lda     scene_asset
        bne     :+
        rts
:       sec
        lda     col
        sbc     sprite_left
        sta     sprite_x
        lda     #0
        sbc     sprite_left+1
        beq     :+
        jmp     @done
:
        lda     sprite_x
        ldx     sprite_shift
        beq     @scaled_x
@scale_x:
        asl     a
        bcc     :+
        jmp     @done
:
        dex
        bne     @scale_x
@scaled_x:
        sta     sprite_x
        cmp     $5800
        bcc     :+
        jmp     @done
:
        lda     #1
        sta     scene_opaque
        ldx     #VIEW_ROWS-1
        lda     #$FF
@clear: sta     sprite_rows,x
        dex
        cpx     #$FF
        bne     @clear
        lda     sprite_x
        asl     a
        adc     #1
        sta     dx
        lda     #$58
        sta     dx+1
        ldy     #0
        lda     (dx),y
        sta     rx
        iny
        lda     (dx),y
        clc
        adc     #$58
        sta     rx+1
        iny
        lda     (dx),y
        sta     dy
        iny
        lda     (dx),y
        clc
        adc     #$58
        sta     dy+1
        ldy     #0
        lda     #191
        sec
        sbc     (rx),y
        sta     sprite_y
        jsr     sprite_advance
        lda     #0
        sta     sprite_codes
@pixel: jsr     sprite_code
        bcc     :+
        jmp     @done
:
        sta     sprite_colour
        bne     @paint
        jsr     sprite_code
        bcc     :+
        jmp     @done
:
        beq     @transparent
@paint: lda     scene_depth
        beq     @local
        lda     sprite_base
        sec
        sbc     sprite_y
        sta     sprite_scaled
        and     sprite_mask
        bne     @transparent
        lda     sprite_scaled
        ldx     sprite_shift
        beq     @scaled_y
@scale_y:
        lsr     a
        dex
        bne     @scale_y
@scaled_y:
        sta     sprite_scaled
        lda     sprite_anchor
        sec
        sbc     sprite_scaled
        tay
        jmp     @clip
@local: lda     sprite_y
        sec
        sbc     sprite_origin    ; lift: 0 wreck, 10 other local sprites
        tay
@clip:
        cpy     #VIEW_ROWS
        bcs     @transparent
        lda     sprite_colour
        sta     sprite_rows,y     ; 0..3 opaque, $FF transparent
@transparent:
        dec     sprite_y
        jmp     @pixel
@done:  lda     scene_opaque
        beq     @return
        lda     scene_depth
        beq     @emit
        lda     #1
        sta     scene_pending
        lda     #0
        sta     scene_opaque
@return:
        rts
@emit:  jmp     scene_emit

.segment "GCODE"
; Delay a distant sprite until all terrain nearer than its plane is known.
scene_activate:
        ; The hot ray loop checks scene_pending before calling us.
        lda     n
        cmp     scene_trigger
        bcc     scene_activation_done
scene_force:
        lda     scene_pending
        beq     scene_activation_done
        sty     scene_ray_x
        lda     #0
        sta     scene_pending
        lda     #1
        sta     scene_opaque
        ldy     top
        lda     #$FF
@foreground:
        cpy     #VIEW_ROWS
        bcs     @paint
        sta     sprite_rows,y    ; nearer ground/ridges own these rows
        iny
        bne     @foreground
@paint: jsr     scene_emit
        jsr     scene_trim
        ldy     scene_ray_x
scene_activation_done: rts

.segment "GCODE"
; Paint contiguous same-code runs, rather than invoking dspan for each row.
scene_emit:
        lda     scene_opaque
        beq     @done
        ldy     #0
@scan:  cpy     #VIEW_ROWS
        bcs     @done
        lda     sprite_rows,y
        bmi     @skip
        sta     scene_colour
        sty     scene_pos
@run:   iny
        cpy     #VIEW_ROWS
        bcs     @paint
        cmp     sprite_rows,y
        beq     @run
@paint: sty     scene_end
        sty     sp_end
        ldy     scene_pos
        ldx     scene_colour    ; original code 0..3 -> shaded mood colour
        lda     spr_map,x
        jsr     dspan
        ldy     scene_end
        jmp     @scan
@skip:  iny
        bne     @scan
@done:  rts

.segment "CODE"
; Terrain spans paint only transparent runs. Sprite bits never get overwritten.
scene_span:
        sta     scene_colour
        lda     scene_opaque
        bne     scene_masked
        lda     scene_colour
        jmp     dspan
; scene_masked -- scene_colour on the transparent rows of Y..sp_end-1 only.
scene_masked:
        sty     scene_pos
        lda     sp_end
        sta     scene_end
@scan:  ldy     scene_pos
        cpy     scene_end
        bcs     @done
        lda     sprite_rows,y
        bmi     @run
        inc     scene_pos
        bne     @scan
@run:   iny
        cpy     scene_end
        bcs     @fill
        lda     sprite_rows,y
        bmi     @run
@fill:  sty     sp_end
        ldy     scene_pos
        lda     sp_end
        sta     scene_pos
        lda     scene_colour
        jsr     dspan
        lda     scene_end
        sta     sp_end
        jmp     @scan
@done:  rts

; Already opaque rows do not contribute to the remaining terrain frontier.
.segment "GCODE"
scene_trim:
        lda     scene_opaque
        beq     @done
        ldx     top
@trim:  cpx     #0
        beq     @store
        dex
        lda     sprite_rows,x
        bpl     @trim
        inx
@store: stx     top
@done:  rts

.segment "TEXT"
scene_ceiling: .res 128
.segment "CODE"

; Carry = end of stream. Token extraction preserves every escape sequence.
sprite_code:
        lda     sprite_codes
        bne     @bits
        lda     rx
        cmp     dy
        lda     rx+1
        sbc     dy+1
        bcs     @done
        ldy     #0
        lda     (rx),y
        sta     sprite_bits
        jsr     sprite_advance
        lda     #4
        sta     sprite_codes
@bits:  lda     sprite_bits
        and     #3
        pha
        lsr     sprite_bits
        lsr     sprite_bits
        dec     sprite_codes
        pla
        clc
@done:  rts
.segment "GCODE"
sprite_advance:
        inc     rx
        bne     :+
        inc     rx+1
:       rts

.include "fauna.s"
.segment "TEXT"
; The first message names the region and its wildlife from the texts of the
; loaded pack (REGIONTEXT), in the words of the original introduction (GO3).
m_crash: .byte "CRASH IN @",<region_intro,". REACH THE RANGERS.",13
        .byte "WILDLIFE: @",<region_fauna,13
        .byte "TRY INVENTORY, STATUS, TOPO, HELP.",0

; message placeholder '@' + selector: a text of the loaded region. The
; selector is the low byte of a REGIONTEXT field ($5780-$57FF, one page):
; <region_species names the species of fauna_named (animal_kind 6..9, set
; by OUTDOOR), any other value prints the field it points to. Fields are
; zero padded, so every name ends in the page. Y is the '@' index;
; message_next skips the selector.
.assert >region_name = >(region_intro + 21), error, "REGIONTEXT must fit in one page"
message_region:
        iny
        tya
        pha
        lda     (gp1),y
        cmp     #<region_species
        bne     @field
        lda     fauna_named     ; 12 * (kind - 6) + region_species
        asl     a
        asl     a
        sta     gp2
        asl     a
        adc     gp2             ; C clear: 8 * kind < 128
        adc     #<(region_species - 72)
@field: sta     gp2
        lda     #>region_name
        sta     gp2+1
        jsr     message_string
        pla
        tay
        jmp     message_next
fauna_named: .byte 6            ; species of the last animal reaction

; wait_any -- a key (messages read)
wait_any:
        jsr     wait_key
        lda     #0
        sta     shown
        rts
