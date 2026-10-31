; ported from POM1 dev/lib/tms9918 @ e399808 (sprites_overworld.asm)
; Port: .export lines dropped; each pattern is .ifref-guarded (only the
; patterns the source above references assemble), RODATA segment.
; ============================================================================
; sprites_overworld.asm  --  13 sprites (16x16, TMS9918 sprite mode)
; derived: dev/lib/gen2/sprites/sprites_overworld_hgr.asm -- after editing this master rerun:
;   python3 tools/build_hgr_sprites.py --only overworld
; ----------------------------------------------------------------------------
; SCROLL-O-SPRITES "Overworld" by Quale, May 2013, CC-BY-3.0.
; Lifted from pic/undefined - Imgur.png by tools/extract_scroll_sprites.py.
;
; Layout: each 16x16 sprite occupies 32 bytes -- the first 16 bytes are
; the left half (column 0..7), the next 16 the right half (column 8..15).
; Native TMS9918 16x16 sprite layout: stream the 32 bytes into a
; sprite-pattern slot starting at the ACTIVE MODE'S sprite-pattern table
; + slot*32 (asm Mode-1 init_vdp_g1: R6=$07 -> $3800; C lib SCREEN1/SCREEN2
; tables: R6=$03 -> $1800 — on those layouts $3800 is the NAME table!).
; ============================================================================
.ifndef _SPRITES_OVERWORLD_ASM_LOADED_
_SPRITES_OVERWORLD_ASM_LOADED_ = 1

.pushseg
.rodata



; slot 01/13 of "Overworld" row -- grass
.ifref world_grass_pat
world_grass_pat:
        .byte $00, $00, $00, $00, $00, $00, $02, $02
        .byte $08, $00, $00, $00, $00, $00, $00, $00
        .byte $00, $00, $00, $00, $00, $00, $00, $A0
        .byte $80, $00, $00, $00, $00, $00, $00, $00
.endif

; slot 02/13 of "Overworld" row -- pebbles
.ifref world_pebbles_pat
world_pebbles_pat:
        .byte $00, $00, $00, $00, $00, $00, $02, $00
        .byte $08, $03, $03, $00, $00, $00, $00, $00
        .byte $00, $00, $00, $00, $00, $C0, $E0, $60
        .byte $00, $20, $00, $00, $00, $00, $00, $00
.endif

; slot 03/13 of "Overworld" row -- flower  (was: bushes)
.ifref world_flower_pat
world_flower_pat:
        .byte $00, $00, $00, $00, $00, $01, $05, $06
        .byte $02, $01, $00, $00, $00, $00, $00, $00
        .byte $00, $00, $00, $00, $00, $80, $A0, $60
        .byte $40, $80, $00, $00, $00, $00, $00, $00
.endif

; slot 04/13 of "Overworld" row -- tree_full  (was: tree)
.ifref world_tree_full_pat
world_tree_full_pat:
        .byte $00, $03, $0F, $1F, $3F, $3F, $7F, $7F
        .byte $7C, $3A, $0D, $01, $01, $01, $03, $00
        .byte $00, $C0, $F0, $F8, $FC, $FC, $FE, $FE
        .byte $3E, $5C, $B0, $80, $80, $80, $C0, $00
.endif

; slot 05/13 of "Overworld" row -- tree_pine  (was: pine)
.ifref world_tree_pine_pat
world_tree_pine_pat:
        .byte $00, $01, $03, $07, $00, $07, $0F, $1F
        .byte $00, $0F, $1F, $3F, $00, $01, $01, $00
        .byte $00, $80, $C0, $E0, $00, $E0, $F0, $F8
        .byte $00, $F0, $F8, $FC, $00, $80, $80, $00
.endif

; slot 06/13 of "Overworld" row -- tree_bare  (was: deadtree)
.ifref world_tree_bare_pat
world_tree_bare_pat:
        .byte $00, $00, $0A, $04, $1C, $04, $02, $7A
        .byte $27, $03, $01, $01, $01, $01, $03, $00
        .byte $00, $00, $50, $20, $38, $20, $40, $5E
        .byte $E4, $C0, $80, $80, $80, $80, $C0, $00
.endif

; slot 07/13 of "Overworld" row -- waves  (was: water)
.ifref world_waves_pat
world_waves_pat:
        .byte $00, $00, $0C, $33, $00, $00, $00, $0C
        .byte $33, $00, $00, $00, $0C, $33, $00, $00
        .byte $00, $00, $CC, $30, $00, $00, $00, $CC
        .byte $30, $00, $00, $00, $CC, $30, $00, $00
.endif

; slot 08/13 of "Overworld" row -- boulders  (was: hill)
.ifref world_boulders_pat
world_boulders_pat:
        .byte $00, $07, $0F, $0F, $1F, $1E, $1D, $1B
        .byte $03, $1B, $3D, $7E, $7E, $7E, $7E, $00
        .byte $00, $E0, $F0, $F8, $F8, $00, $F8, $FC
        .byte $FC, $FE, $FE, $FE, $F2, $EC, $1E, $00
.endif

; slot 09/13 of "Overworld" row -- cave  (was: tent)
.ifref world_cave_pat
world_cave_pat:
        .byte $00, $00, $00, $03, $07, $0F, $0F, $1F
        .byte $1E, $1C, $1C, $1C, $1D, $03, $07, $00
        .byte $00, $00, $00, $C0, $E0, $F0, $F0, $F8
        .byte $78, $38, $38, $38, $B8, $C0, $E0, $00
.endif

; slot 10/13 of "Overworld" row -- house  (was: hut)
.ifref world_house_pat
world_house_pat:
        .byte $00, $00, $00, $01, $02, $05, $0B, $17
        .byte $2F, $1F, $12, $12, $1D, $03, $07, $00
        .byte $00, $00, $00, $90, $50, $B0, $D0, $E8
        .byte $F4, $F8, $48, $48, $B8, $C0, $E0, $00
.endif

; slot 11/13 of "Overworld" row -- castlle  (was: castle)
.ifref world_castlle_pat
world_castlle_pat:
        .byte $00, $00, $00, $2D, $3F, $3F, $00, $1F
        .byte $17, $16, $1C, $1C, $1D, $03, $07, $00
        .byte $00, $00, $00, $B4, $FC, $FC, $00, $F8
        .byte $E8, $68, $38, $38, $B8, $C0, $E0, $00
.endif

; slot 12/13 of "Overworld" row -- cart  (was: dock)
.ifref world_cart_pat
world_cart_pat:
        .byte $00, $00, $00, $7F, $00, $08, $08, $00
        .byte $7F, $0F, $0E, $0F, $01, $01, $00, $00
        .byte $00, $00, $00, $FE, $02, $02, $02, $02
        .byte $FE, $1E, $EE, $1E, $50, $10, $E0, $00
.endif

; slot 13/13 of "Overworld" row -- ship  (was: boat)
.ifref world_ship_pat
world_ship_pat:
        .byte $00, $02, $01, $03, $07, $37, $67, $47
        .byte $46, $44, $61, $7E, $7F, $3F, $00, $00
        .byte $00, $80, $80, $80, $80, $A0, $90, $08
        .byte $06, $0C, $1C, $F8, $F0, $E0, $00, $00
.endif

.popseg
.endif  ; _SPRITES_OVERWORLD_ASM_LOADED_
