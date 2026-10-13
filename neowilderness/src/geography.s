; Native fine geography (lot 5). Native maps (header byte 37) carry the
; 224 x 168 grid as a compressed atlas in the auxiliary language card, decoded
; on demand into a cache of four 16 x 16 tiles (src/geoaux.s). A query never
; reads the disk and never touches the $5800 window. Legacy maps keep the
; resident 112 x 84 grid.
.segment "GDATA"
geo_wooded: .byte 0
geo_water_kind: .byte 0         ; 0 = river, 64 = lake (only defined in water)
.segment "GCODE"
; X = original row, Y = original column -> A = cell byte, N = water.
; Any caller may use it. Native maps: geo_wooded (nonzero in woodland) and,
; for water, geo_water_kind (64 lake, 0 river). Legacy maps retain their grid.
; Interrupts are masked while the auxiliary zero page, stack and language
; card (bank 1, write enabled) are selected; ALTZP off and the ROM are
; restored. RAMRD and RAMWRT must be off (they always are between transfers).
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
        php
        sei
        sta     ALTZPON
        lda     LCBANK1         ; twice: read RAM bank 1, write enabled
        lda     LCBANK1
        jsr     geo_query
        bit     LCROM
        sta     ALTZPOFF
        plp
        ora     #0              ; N, Z from the cell
        rts
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
