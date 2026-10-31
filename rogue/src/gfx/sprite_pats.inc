; From POM1 TMS_Rogue.asm (sprite_pats), unchanged. Format: TMS9918 16x16
; sprites, 32 B each (left column top/bottom 8 rows, right column top/bottom).

.segment "RODATA"
; ============================================================================
; sprite_pats -- 13 sprite patterns (16x16, 32 B each = 416 B), uploaded
; as a single contiguous block to VRAM $3800 by upload_sprite_pats.
; Inlined here rather than .imported from the lib .asm files because
; pulling in the full 33-sprite character lib + 8-sprite undead lib +
; 27-sprite outfit lib + 4-sprite trollkind lib would blow the 3 456 B
; low-bank CODE budget on the DRAM build.
;
;   Slot 0 / $3800 : char_guard_pat (player, lt-blue)
;     Source: dev/lib/tms9918/sprites_characters.asm, post-shift bytes
;     (tools/shift_characters_up.py rebalanced the 2-row blank top + 0
;     blank bottom to 1+1).
;
;   Slot 4 / $3820 : undead_zombie_pat   (was Quale's "skull")
;   Slot 8 / $3840 : undead_ghost_pat
;   Slot 12 / $3860: undead_reaper_pat    (was Quale's "mummy")
;     Source: dev/lib/tms9918/sprites_unliving.asm — Quale's
;     SCROLL-O-SPRITES "The Unliving" row, CC-BY-3.0. Labels were
;     re-mapped (skull → UNDEAD as "first-tier undead", mummy → DEATH
;     as "strongest undead"); the lib's .export was updated to match.
;
;   Slot 16 / $3880: food_drumstick_pat (drumstick — dropped by dead monsters)
;     Source: dev/lib/tms9918/sprites_food_drink.asm — Quale's
;     SCROLL-O-SPRITES "Food & Drink" row, CC-BY-3.0.
;
;   Slot 20 / $38A0: undead_skeleton_pat (was Quale's "crossbones")
;     Source: dev/lib/tms9918/sprites_unliving.asm — second-tier
;     warrior undead. Sits AFTER the food slot in the sprite-pattern
;     table (food landed at slot 16 first chronologically); the
;     skip-by-name SAT addressing is unaffected by slot order.
; ============================================================================
sprite_pats:
char_guard_pat:                              ; slot 0 — player
        .byte $01, $07, $0F, $0F, $09, $08, $0E, $02
        .byte $7A, $68, $6B, $6B, $69, $6A, $34, $00
        .byte $82, $E7, $F0, $F2, $92, $12, $72, $72
        .byte $66, $16, $D8, $E2, $82, $62, $22, $00
undead_zombie_pat:                              ; slot 4 — undead
        .byte $00, $00, $17, $0F, $09, $09, $0F, $2E
        .byte $0C, $04, $38, $57, $47, $07, $06, $02
        .byte $00, $02, $E0, $F0, $F0, $D0, $F0, $B0
        .byte $30, $22, $18, $D4, $E4, $E0, $60, $50
undead_ghost_pat:                               ; slot 8 — ghost
        .byte $00, $07, $0F, $1D, $1B, $5F, $7D, $7C
        .byte $3C, $1E, $1F, $1F, $0F, $03, $00, $00
        .byte $00, $E0, $F0, $F8, $B8, $DA, $7E, $3E
        .byte $3C, $B8, $F8, $F8, $FA, $FC, $00, $00
undead_reaper_pat:                               ; slot 12 — death
        .byte $00, $63, $77, $4F, $48, $51, $51, $56
        .byte $53, $53, $78, $3F, $5F, $47, $47, $4C
        .byte $00, $F0, $E0, $F0, $10, $88, $88, $68
        .byte $C8, $48, $10, $F8, $FC, $E4, $F0, $D8
                                                ; slot 16 — food (meat)
        .byte $00, $00, $00, $00, $00, $00, $03, $0F
        .byte $3B, $5E, $7E, $6C, $78, $31, $1E, $00
        .byte $00, $18, $1E, $1E, $30, $60, $C0, $60
        .byte $00, $40, $40, $80, $80, $00, $00, $00
undead_skeleton_pat:                            ; slot 20 — skeleton
        ; Bytes shifted up by one row vs. the lib's
        ; undead_skeleton_pat (the Quale extraction left a 2-row blank
        ; top and 0-row blank bottom, so the unshifted sprite floats
        ; one cell low). Same fix as char_guard_pat (see the
        ; tools/shift_characters_up.py docstring): each 16-row
        ; half-column is rotated by one — left[0..14] = old left[1..15],
        ; left[15] = 0; mirror for the right half. Only the inline copy
        ; here is shifted; the lib bytes stay raw for other consumers.
        .byte $00, $07, $0F, $0F, $09, $09, $0E, $03
        .byte $03, $18, $27, $31, $33, $04, $04, $00
        .byte $00, $E0, $F0, $F0, $90, $90, $70, $C0
        .byte $40, $18, $E4, $8C, $CC, $20, $20, $00

; --- MVP4 item sprites (slots 24..44) ----------------------------------
; All 16x16 sprites laid out as 4 quadrants of 8 rows each:
;   bytes  0..7  = left top half   (TL)
;   bytes  8..15 = left bottom half (BL)
;   bytes 16..23 = right top half  (TR)
;   bytes 24..31 = right bottom half (BR)
; Each row byte = 8 horizontal pixels, MSB = leftmost column.
;
; The patterns are intentionally simple — readable at the 256x192
; resolution from a few feet, and cheap on VRAM (32 B each). Colour
; comes from the SAT entry, so the same dagger pattern can flash hurt
; (COL_HURT) when it lands a hit.
item_dagger_pat:                                ; slot 24 — dagger / throw
        ; Quale's outfit_dagger_pat (sprites_outfit.asm slot 01/27 of
        ; "Outfit"), inlined to keep the cartridge link self-contained.
        .byte $00, $00, $00, $00, $03, $03, $00, $03
        .byte $07, $0E, $1D, $1A, $1C, $00, $00, $00
        .byte $00, $00, $00, $18, $18, $A0, $C0, $60
        .byte $B0, $B0, $00, $00, $00, $00, $00, $00
item_potion_pat:                                ; slot 28 — potion
        ; Quale's food_vial_pat (sprites_food_drink.asm slot 20/22 of
        ; "Food & Drink") — slim corked bottle. Game still calls the
        ; category POTION (INV_T_POTION); only the visual changed.
        .byte $00, $00, $00, $00, $03, $06, $07, $03
        .byte $04, $0E, $0E, $0E, $0E, $04, $03, $00
        .byte $00, $00, $00, $00, $C0, $60, $E0, $C0
        .byte $20, $10, $10, $10, $10, $20, $C0, $00
item_scroll_pat:                                ; slot 32 — scroll
        ; Quale's magic_letter_pat (sprites_magick.asm slot 07/15 of
        ; "Magick") — rolled scroll with text lines.
        .byte $00, $07, $09, $0B, $08, $0F, $08, $0F
        .byte $0C, $0F, $08, $0F, $6C, $4F, $3F, $00
        .byte $00, $FC, $FE, $FE, $00, $F8, $08, $F8
        .byte $18, $F8, $08, $F8, $18, $F8, $F0, $00
item_weapon_pat:                                ; slot 36 — weapon (sword)
        ; Quale's outfit_sword_pat (sprites_outfit.asm slot 02/27 of
        ; "Outfit") — a hilt-and-blade sword silhouette.
        .byte $00, $00, $00, $00, $00, $01, $03, $07
        .byte $37, $36, $1B, $0C, $17, $63, $60, $00
        .byte $00, $1E, $3E, $7A, $F2, $E4, $C8, $90
        .byte $20, $40, $80, $00, $00, $00, $00, $00
item_armor_pat:                                 ; slot 40 — armor (chest)
        ; Quale's outfit_chainmail_pat (sprites_outfit.asm slot 21/27 of
        ; "Outfit") — a tunic / gambeson silhouette.
        .byte $00, $00, $00, $3C, $3D, $3C, $1C, $0E
        .byte $11, $1F, $1F, $00, $0F, $00, $00, $00
        .byte $00, $00, $00, $3C, $BC, $3C, $38, $70
        .byte $88, $F8, $F8, $00, $F0, $00, $00, $00
item_ring_pat:                                  ; slot 44 — ring
        ; Quale's outfit_ring_pat (sprites_outfit.asm slot 24/27 of
        ; "Outfit") — pendant on a chain. Game still calls the category
        ; RING (INV_T_RING / SUB_RING_*); only the on-screen pictogram
        ; is the amulet.
        .byte $00, $00, $00, $0E, $1E, $1E, $1D, $03
        .byte $1E, $1C, $1C, $0C, $06, $03, $00, $00
        .byte $00, $00, $00, $E0, $F0, $F8, $8C, $04
        .byte $04, $04, $04, $08, $10, $E0, $00, $00
troll_goblin_pat:                                ; slot 48 — troll grunt
        ; Quale's troll_goblin_pat (sprites_trollkind.asm slot 01/4 of
        ; "Trollkind"). Med-green silhouette via MON_COL_TROLL — flees
        ; the player on its turn (ai_troll).
        .byte $00, $00, $00, $00, $00, $77, $3D, $0F
        .byte $07, $08, $1F, $37, $27, $36, $32, $02
        .byte $00, $00, $00, $00, $00, $EE, $BC, $F0
        .byte $E0, $10, $F8, $EC, $E4, $6C, $4C, $40
expl_torch_pat:                                 ; slot 52 — torch
        ; Quale's expl_torch_pat (sprites_exploration.asm slot 01/21
        ; of "Exploration"). Inlined to keep the cartridge link
        ; self-contained. Painted in COL_TORCH (light yellow flame).
        .byte $00, $00, $00, $04, $00, $01, $13, $07
        .byte $04, $02, $07, $0C, $18, $30, $60, $00
        .byte $00, $40, $68, $F0, $F0, $F8, $98, $38
        .byte $78, $F0, $E0, $00, $00, $00, $00, $00

.segment "CODE"
