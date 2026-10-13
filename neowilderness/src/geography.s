; Optional full-resolution geography banks. Seven rows per overlay leave
; space for the lookup at $5F00. Height/water and woodland remain separate.
; The original Sierra data is used only on local comparison disks.
.segment "GEOGRAPHY"
        .res $700
module_geography_cell:
        lda     geo_rows_lo,x
        sta     gp2
        lda     geo_rows_hi,x
        sta     gp2+1
        lda     (gp2),y
        bpl     :+
        pha
        and     #64
        sta     geo_water_kind
        pla
        and     #$BF
:
        pha
        tya
        lsr
        lsr
        lsr
        clc
        adc     geo_woods_rows,x
        tax
        tya
        and     #7
        tay
        lda     forest_masks,y
        and     $5E20,x
        sta     geo_wooded
        pla
        rts
geo_rows_lo:
        .repeat 7,I
        .byte <($5800+224*I)
        .endrepeat
geo_rows_hi:
        .repeat 7,I
        .byte >($5800+224*I)
        .endrepeat
geo_woods_rows: .byte 0,28,56,84,112,140,168
.segment "GDATA"
geo_wooded: .byte 0
geo_water_kind: .byte 0         ; 0 = river, 64 = lake (only defined in water)
.segment "GCODE"
; X = original row, Y = original column. Only resident/SIM callers may use
; this entry: it replaces the $5800 overlay. Legacy maps retain their grid.
cell_native:
        lda     MAP+37
        bne     @native
        tya
        lsr
        tay
        txa
        lsr
        tax
        jmp     cell_at
@native:
        tya
        pha
        txa
        ldy     #GEO_FIRST
@bank:  cmp     #7
        bcc     @load
        sec
        sbc     #7
        iny
        bne     @bank
@load:  pha
        tya
        jsr     overlay_load
        pla
        tax
        pla
        tay
        jmp     module_geography_cell
.segment "ENVIRON"
native_here:
        lda     px
        asl
        lda     px+1
        rol
        tay
        lda     py
        asl
        lda     py+1
        rol
        tax
        jmp     cell_native

.segment "GCODE"
native_next:
        lda     nx
        asl
        lda     nx+1
        rol
        tay
        lda     ny
        asl
        lda     ny+1
        rol
        tax
        jmp     cell_native
