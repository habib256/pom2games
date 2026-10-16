; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; geoaux.s -- resident fine geography (lot 5), auxiliary language card
; ============================================================================
; Native maps carry the 224 x 168 fine geography as an atlas of 154 tiles of
; 16 x 16 cells (tools/geo_atlas.py, codec 'coarse'), loaded by NEOWILD.SYSTEM
; with this code into the auxiliary language card, bank 1 view:
;
;   $D000-$D3FF  decoded cells of 4 cached tiles, one page per slot:
;                offset (row mod 16) * 16 + (column mod 16), cell byte as in
;                the map (level, bit 7 water, bit 6 lake)
;   $D400-$D47F  their woodland bits, 32 bytes per slot (bit = cell mod 8)
;   $D480-...    this segment (tags, decoder, query), then geo_atlas:
;                154 stream addresses (lo, hi), 20 bytes of raw-tile flags,
;                then the tile streams, up to $F0FF (geo_atlas.ATLAS_END;
;                the module store follows, docs/MEMORY.md section 12)
;
; Everything here runs with ALTZP on (auxiliary zero page, stack and language
; card) and RAMRD/RAMWRT off: the code reads the resident 112 x 84 grid in
; main RAM (the predictor of every tile) and writes geo_wooded,
; geo_water_kind and the counters in main RAM. Entry only through
; cell_native (src/geography.s), which masks interrupts, selects bank 1 with
; write enable and restores ALTZP off and the ROM afterwards.
;
; Tile stream (MSB-first bits; tools/geo_atlas.py delta_encode, 'vlc' code,
; 'coarse' predictor, lake bit on):
;   1 bit any water; if set, alternating dry/wet run lengths from a dry run,
;     each wet run followed by its lake bit;
;   1 bit any woods; if set, alternating bare/wooded run lengths;
;   1 bit unit sign (1 = the frequent step is -1);
;   one residual per cell against the rounded bilinear interpolation of the
;   resident grid: 0 -> 0, 10 -> unit, 110 -> -unit, 111 + nibble k: k - 8,
;   or k = 8 then a 7-bit level. Even/even cells of a dry coarse cell equal
;   it and are not coded.
; Run length: 4 bits, 15 = 15 + following bytes (255 continues).
; A raw tile (flag set) stores the decoded cells then the woodland bytes.
; ============================================================================

GEO_CELLS = $D000
GEO_WOODS = $D400
GEO_TILES = 154
GA_LO     = 0                   ; atlas offsets of the index tables
GA_HI     = GEO_TILES
GA_RAW    = 2 * GEO_TILES
GA_DATA   = 2 * GEO_TILES + (GEO_TILES + 7) / 8

; Auxiliary zero page (ALTZP on only; never used by anything else).
gq_row    = $10
gq_col    = $11
gq_tile   = $12
gq_cell   = $13
gd_bits   = $14                 ; bit buffer, sentinel bit below the data
gd_out    = $16                 ; output cells (low byte 0)
gd_wood   = $18                 ; output woodland bytes
gd_gp     = $1A                 ; resident grid row
gd_pred   = $1C
gd_unit   = $1D
gd_savex  = $1E
gd_runl   = $1F
gd_runh   = $20
gd_leftl  = $21
gd_lefth  = $22
gd_wet    = $23                 ; water plane: bit 7 = wet run due
gd_on     = $24                 ; woodland plane: 0 bare, 1 wooded
gd_acc    = $25
gd_wbit   = $26
gd_ncell  = $27                 ; cells in the tile (0 = 256)
gd_nwood  = $28                 ; woodland bytes in the tile
gd_rows   = $29
gd_x0     = $2A                 ; first coarse column / row of the tile
gd_y0     = $2B
gd_i      = $2C
gd_j      = $2D
gd_c      = $2E
gd_fy     = $2F
gd_t      = $30
gd_cb     = $40                 ; 9 x 9 coarse levels around the tile
gd_cr     = $A0                 ; the same coarse bytes, water bit kept

.macro GETBIT                   ; C = next bit; A, X, Y preserved
        asl     gd_bits         ; (an anonymous label keeps the @ scopes)
        bne     :+
        jsr     geo_refill
:
.endmacro

.segment "GEOAUX"
; Most recently used first; slot = page of GEO_CELLS. $FF: no tile.
geo_tags:  .byte $FF, $FF, $FF, $FF
geo_slots: .byte 0, 1, 2, 3
geo_row14: .repeat 11, I
           .byte I * 14
           .endrep
geo_slot32: .byte 0, 32, 64, 96
geo_bit:   .byte 1, 2, 4, 8, 16, 32, 64, 128
geo_mul9:  .repeat 9, I
           .byte I * 9
           .endrep

; geo_query -- X = fine row 0..167, Y = fine column 0..223.
; Returns A = cell byte (bit 6 removed from water, which sets geo_water_kind
; to 64 for a lake or 0 for a river), geo_wooded nonzero in woodland.
geo_query:
        stx     gq_row
        sty     gq_col
        inc     geo_queries
        bne     :+
        inc     geo_queries+1
        bne     :+
        inc     geo_queries+2
:       txa
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        tax
        tya
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        clc
        adc     geo_row14,x
        cmp     geo_tags
        bne     @search
        ldx     geo_slots
        jmp     geo_read
@search:
        sta     gq_tile
        ldx     #1
@tag:   cmp     geo_tags,x
        beq     @found
        inx
        cpx     #4
        bne     @tag
        dex                     ; miss: reuse the least recently used slot
        sta     geo_tags,x
        jsr     geo_decode
        ldx     #3
@found: ldy     geo_slots,x     ; move entry X to the front
@shift: lda     geo_tags-1,x
        sta     geo_tags,x
        lda     geo_slots-1,x
        sta     geo_slots,x
        dex
        bne     @shift
        lda     gq_tile
        sta     geo_tags
        sty     geo_slots
        tya
        tax
geo_read:                       ; X = slot
        txa
        clc
        adc     #>GEO_CELLS
        sta     gd_out+1
        lda     #0
        sta     gd_out
        lda     gq_row
        asl     a
        asl     a
        asl     a
        asl     a
        sta     gq_cell
        lda     gq_col
        and     #15
        ora     gq_cell
        tay
        lda     (gd_out),y
        sta     gq_cell
        tya                     ; woodland byte: cell / 8 in the slot
        lsr     a
        lsr     a
        lsr     a
        ora     geo_slot32,x
        tay
        lda     gq_col
        and     #7
        tax
        lda     GEO_WOODS,y
        and     geo_bit,x
        sta     geo_wooded
        lda     gq_cell
        bpl     @dry
        and     #64
        sta     geo_water_kind
        lda     gq_cell
        and     #$BF
@dry:   rts

; ----------------------------------------------------------------------------
; geo_decode -- tile gq_tile into the slot of entry X (the LRU entry, 3).
geo_decode:
        inc     geo_decodes
        bne     :+
        inc     geo_decodes+1
:       lda     geo_slots,x
        tax
        clc
        adc     #>GEO_CELLS
        sta     gd_out+1
        lda     geo_slot32,x
        sta     gd_wood
        lda     #>GEO_WOODS
        sta     gd_wood+1
        lda     #0
        sta     gd_out
        lda     gq_tile         ; X = tile row, A = tile column
        ldx     #0
@div:   cmp     #14
        bcc     @geom
        sbc     #14
        inx
        bne     @div
@geom:  asl     a
        asl     a
        asl     a
        sta     gd_x0
        txa
        asl     a
        asl     a
        asl     a
        sta     gd_y0
        lda     #16             ; the last tile row has 8 rows (168 = 10*16+8)
        cpx     #10
        bne     :+
        lda     #8
:       sta     gd_rows
        asl     a
        sta     gd_nwood
        asl     a
        asl     a
        asl     a
        sta     gd_ncell        ; 128, or 0 for 256
        ldx     gq_tile
        lda     geo_atlas+GA_LO,x
        sta     geo_src+1
        lda     geo_atlas+GA_HI,x
        sta     geo_src+2
        txa
        lsr     a
        lsr     a
        lsr     a
        tay
        txa
        and     #7
        tax
        lda     geo_atlas+GA_RAW,y
        and     geo_bit,x
        beq     geo_coded
        ldy     #0              ; raw tile: cells, then woodland bytes
@rc:    jsr     geo_byte
        sta     (gd_out),y
        iny
        cpy     gd_ncell
        bne     @rc
        ldy     #0
@rw:    jsr     geo_byte
        sta     (gd_wood),y
        iny
        cpy     gd_nwood
        bne     @rw
        rts

geo_coded:
        lda     #$80
        sta     gd_bits
        ; Water plane: the kind of every cell (0, $80 river, $C0 lake).
        GETBIT
        ldy     #0
        bcs     @water
        tya
@dry:   sta     (gd_out),y
        iny
        cpy     gd_ncell
        bne     @dry
        beq     @woods
@water: jsr     geo_left
        sty     gd_wet
@wrun:  jsr     geo_run
        lda     #0
        bit     gd_wet
        bpl     @fill
        GETBIT                  ; lake bit
        lda     #$80
        bcc     @fill
        lda     #$C0
@fill:  ldx     gd_runl
        bne     @put
        ldx     gd_runh
        beq     @filled
        ldx     #0              ; 256
@put:   sta     (gd_out),y
        iny
        dex
        bne     @put
@filled:
        lda     gd_wet
        eor     #$80
        sta     gd_wet
        jsr     geo_consume
        bne     @wrun
        ; Woodland plane, least significant bit first.
@woods: GETBIT
        ldy     #0
        bcs     @wooded
        tya
@bare:  sta     (gd_wood),y
        iny
        cpy     gd_nwood
        bne     @bare
        beq     geo_levels
@wooded:
        jsr     geo_left
        sty     gd_on
        lda     #8
        sta     gd_wbit
@orun:  jsr     geo_run
        ldx     gd_runl
        bne     @bit
        lda     gd_runh
        beq     @next
        ldx     #0
@bit:   lda     gd_on
        lsr     a
        ror     gd_acc
        dec     gd_wbit
        bne     :+
        lda     gd_acc
        sta     (gd_wood),y
        iny
        lda     #8
        sta     gd_wbit
:       dex
        bne     @bit
@next:  lda     gd_on
        eor     #1
        sta     gd_on
        jsr     geo_consume
        bne     @orun

; Levels: residuals against the resident grid, 9 x 9 coarse cells cached.
geo_levels:
        GETBIT
        lda     #1
        bcc     :+
        lda     #$FF
:       sta     gd_unit
        ldx     #0
        lda     gd_y0
        sta     gd_j
@cbrow: ldy     gd_j
        cpy     #GH
        bcc     :+
        ldy     #GH-1
:       stx     @resume+1
        tya
        tax
        jsr     grid_row
        sta     gd_gp
        sty     gd_gp+1
@resume:ldx     #0
        lda     gd_x0
        sta     gd_i
        lda     #9
        sta     gd_c
@cbcol: ldy     gd_i
        cpy     #GW
        bcc     :+
        ldy     #GW-1
:       lda     (gd_gp),y
        sta     gd_cr,x
        and     #$7F
        sta     gd_cb,x
        inx
        inc     gd_i
        dec     gd_c
        bne     @cbcol
        inc     gd_j
        cpx     #81
        bne     @cbrow
        ldy     #0
        sty     gd_fy
@row:   lda     gd_fy
        lsr     a
        tax
        lda     geo_mul9,x
        tax
        lda     #8
        sta     gd_c
        bcs     @odd
@even:  lda     gd_cr,x         ; even column: the coarse cell itself
        bpl     :+              ; dry coarse cell: exact, not coded
        and     #$7F
        jsr     geo_resid
:       ora     (gd_out),y
        sta     (gd_out),y
        iny
        lda     gd_cb,x         ; odd column: mean of two, rounded
        sec
        adc     gd_cb+1,x
        lsr     a
        jsr     geo_resid
        ora     (gd_out),y
        sta     (gd_out),y
        iny
        inx
        dec     gd_c
        bne     @even
        beq     @nextrow
@odd:   lda     gd_cb,x         ; odd row, even column: vertical mean
        sec
        adc     gd_cb+9,x
        lsr     a
        jsr     geo_resid
        ora     (gd_out),y
        sta     (gd_out),y
        iny
        lda     gd_cb,x         ; odd row, odd column: (sum of 4 + 2) / 4
        clc
        adc     gd_cb+1,x
        sta     gd_t
        lda     gd_cb+9,x
        clc
        adc     gd_cb+10,x
        clc
        adc     gd_t
        ror     a
        clc
        adc     #1
        lsr     a
        jsr     geo_resid
        ora     (gd_out),y
        sta     (gd_out),y
        iny
        inx
        dec     gd_c
        bne     @odd
@nextrow:
        inc     gd_fy
        lda     gd_fy
        cmp     gd_rows
        bne     @row
        rts

; geo_resid -- A = prediction -> A = level. X and Y preserved.
geo_resid:
        sta     gd_pred
        GETBIT
        bcs     @1
        lda     gd_pred
        rts
@1:     GETBIT
        bcs     @2
        lda     gd_pred
        clc
        adc     gd_unit
        rts
@2:     GETBIT
        bcs     @3
        lda     gd_pred
        sec
        sbc     gd_unit
        rts
@3:     stx     gd_savex
        ldx     #4
        jsr     geo_bits
        cmp     #8
        beq     @abs
        clc
        adc     gd_pred
        sec
        sbc     #8
        ldx     gd_savex
        rts
@abs:   ldx     #7
        jsr     geo_bits
        ldx     gd_savex
        rts

; geo_left -- remaining cells = tile cells; Y = 0 kept, A = 0.
geo_left:
        lda     gd_ncell
        sta     gd_leftl
        cmp     #1              ; carry clear only for 0 (256 cells)
        lda     #0
        bcs     :+
        lda     #1
:       sta     gd_lefth
        lda     #0
        rts

; geo_consume -- remaining -= run; Z set when the plane is complete.
geo_consume:
        sec
        lda     gd_leftl
        sbc     gd_runl
        sta     gd_leftl
        lda     gd_lefth
        sbc     gd_runh
        sta     gd_lefth
        ora     gd_leftl
        rts

; geo_run -- run length -> gd_runl/gd_runh. Y preserved.
geo_run:
        ldx     #4
        jsr     geo_bits
        ldx     #0
        stx     gd_runh
        sta     gd_runl
        cmp     #15
        bcc     @done
@ext:   ldx     #8
        jsr     geo_bits
        pha
        clc
        adc     gd_runl
        sta     gd_runl
        bcc     :+
        inc     gd_runh
:       pla
        cmp     #255
        beq     @ext
@done:  rts

; geo_bits -- X bits (MSB first) -> A. Y preserved.
geo_bits:
        lda     #0
@bit:   GETBIT
        rol     a
        dex
        bne     @bit
        rts

; geo_refill -- the sentinel left the buffer: load the next byte, return its
; top bit in C. A, X, Y preserved.
geo_refill:
        pha
        jsr     geo_byte
        sec
        rol     a
        sta     gd_bits
        pla
        rts

; geo_byte -- next stream byte (the operand is the stream pointer).
geo_byte:
geo_src:
        lda     $FFFF
        inc     geo_src+1
        bne     :+
        inc     geo_src+2
:       rts

; The atlas follows (tools/build_disk.py appends it to this image).
geo_atlas:
.export geo_query, geo_atlas
