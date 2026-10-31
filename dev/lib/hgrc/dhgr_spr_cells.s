; VERHILLE Arnaud — GPL-3.0. DHGR compositor backgrounds made of cells
; (dhgr.h dhgr_spr_cells, dhgr_spr_tiles): for each cell crossing the piece,
; a C callback paint(col, row) or a tile map's shape. Installed into
; dhgr_spr_update's background jump by the setters, so a program that keeps
; a solid background does not link this member. The C callback may use any
; cc65 scratch; the loop keeps its state in BSS. Non-reentrant, no IRQ.
.export _dhgr_spr_cells, _dhgr_spr_tiles, _dhgr_cv_rect
.import _dhgr_cellbyte, pusha, popa, popax, incsp4
.import cv_rx, cv_ry, cv_nib, cv_nibble, dhgr_cv_fill
.importzp cv_rw, cv_rh
.importzp sp
.import _dhgr_spr_bg, _dhgr_spr_bg_jmp, _dhgr_spr_pal, pg, pn, py
.import _dhgr_cv_y1, _dhgr_cv_shape, _dhgr_cv_sx, _dhgr_cv_sy, _dhgr_cv_flags
.import _dhgr_cv_pal, _dhgr_cv_paint

.bss
_dhgr_spr_cell:  .res 2         ; paint(col, row)
_dhgr_spr_map:   .res 2         ; tiles: map rows of map_w bytes, shape set
_dhgr_spr_map_w: .res 1
_dhgr_spr_tset:  .res 2
_dhgr_spr_cell_g: .res 1        ; first cell: group, row; cell height
_dhgr_spr_cell_y: .res 1
_dhgr_spr_cell_h: .res 1
mode:   .res 1                  ; 1 callback, 2 tiles
cg:     .res 1                  ; cell loop: group, cell top row, row index
ctop:   .res 1
crow:   .res 1
cg0:    .res 1
clast:  .res 1

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; void dhgr_spr_tiles(ox, oy, cell_h, map, map_w, set): set in A/X.
_dhgr_spr_tiles:
        sta _dhgr_spr_tset
        stx _dhgr_spr_tset+1
        jsr popa
        sta _dhgr_spr_map_w
        jsr popax
        sta _dhgr_spr_map
        stx _dhgr_spr_map+1
        lda #2
        bne setup
; void dhgr_spr_cells(ox, oy, cell_h, paint): paint in A/X.
_dhgr_spr_cells:
        sta _dhgr_spr_cell
        stx _dhgr_spr_cell+1
        lda #1
setup:  sta mode
        sta _dhgr_spr_bg
        jsr popa
        sta _dhgr_spr_cell_h
        jsr popa
        sta _dhgr_spr_cell_y
        jsr popa
        tax
        lda _dhgr_cellbyte,x
        lsr a
        lsr a
        sta _dhgr_spr_cell_g
        lda #$4C                ; JMP cells
        sta _dhgr_spr_bg_jmp
        lda #<cells
        sta _dhgr_spr_bg_jmp+1
        lda #>cells
        sta _dhgr_spr_bg_jmp+2
        rts

cells:  lda #0                  ; (tiles: unmirrored, slot 0's colours)
        sta _dhgr_cv_flags
        lda #<_dhgr_spr_pal
        sta _dhgr_cv_pal
        lda #>_dhgr_spr_pal
        sta _dhgr_cv_pal+1
        lda _dhgr_spr_cell
        sta call_cell+1
        lda _dhgr_spr_cell+1
        sta call_cell+2
        lda _dhgr_spr_tset       ; (tiles: the shape pointer table)
        sta set_lo+1
        sta set_hi+1
        lda _dhgr_spr_tset+1
        sta set_lo+2
        sta set_hi+2
        inc set_hi+1
        bne :+
        inc set_hi+2
:       lda py
        sec
        sbc _dhgr_spr_cell_y
        bcs :+
        lda #0                  ; (above the cells)
:       ldx #0                  ; row index: repeated subtraction
        stx crow
@div:   cmp _dhgr_spr_cell_h
        bcc @top
        sbc _dhgr_spr_cell_h
        inc crow
        bne @div
@top:   lda _dhgr_cv_y1
        sbc #0                  ; last row = y1 - 1 (C = 0)
        sta clast
        lda pg
        cmp _dhgr_spr_cell_g
        bcs :+
        lda _dhgr_spr_cell_g
:       sta cg0
        ; first cell top = cell_y + crow * cell_h, map row = map + crow * map_w
        lda _dhgr_spr_map
        sta map_row+1
        lda _dhgr_spr_map+1
        sta map_row+2
        lda _dhgr_spr_cell_y
        ldx crow
        beq @rowtop
@mul:   clc
        adc _dhgr_spr_cell_h
        jsr next_map
        dex
        bne @mul
@rowtop:
        sta ctop
@row:   lda cg0
        sta cg
@col:   lda cg
        sec
        sbc _dhgr_spr_cell_g
        ldx mode
        dex
        bne @tile
        jsr pusha
        lda crow
        jsr call_cell
        jmp @after
@tile:  jsr tile_cell
@after: inc cg
        lda pg
        clc
        adc pn
        cmp cg
        beq :+
        bcs @col
:       inc crow
        jsr next_map
        lda ctop
        clc
        adc _dhgr_spr_cell_h
        bcs @end
        sta ctop
        cmp clast
        bcc @row
        beq @row
@end:   rts

; The map row pointer += map_w. A and X kept.
next_map:
        pha
        lda map_row+1
        clc
        adc _dhgr_spr_map_w
        sta map_row+1
        bcc :+
        inc map_row+2
:       pla
        rts

; Tiles: cell column A of row crow: set[map[row][col]] at 7 * cg, ctop.
tile_cell:
        tay
map_row:
        lda $FFFF,y
        asl a
        tay
set_lo: lda $FFFF,y
        sta _dhgr_cv_shape
set_hi: lda $FFFF,y
        sta _dhgr_cv_shape+1
        ora _dhgr_cv_shape
        beq @none
        lda cg
        asl a
        asl a
        asl a
        sec
        sbc cg
        sta _dhgr_cv_sx
        lda ctop
        sta _dhgr_cv_sy
        jmp _dhgr_cv_paint
@none:  rts
call_cell:
        jmp $FFFF               ; (patched: no JMP (ind) page-crossing bug)

; void dhgr_cv_rect(x, y, w, h, colour): C stack h=0, w=1, y=2, x=3.
_dhgr_cv_rect:
        jsr cv_nibble
        sta cv_nib
        ldy #3
        lda (sp),y
        sta cv_rx
        dey
        lda (sp),y
        sta cv_ry
        dey
        lda (sp),y
        sta cv_rw
        dey
        lda (sp),y
        sta cv_rh
        jsr dhgr_cv_fill
        jmp incsp4
