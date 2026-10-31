; ported from POM1 dev/lib/tms9918 @ e399808 (sprites_emotes.asm)
; Port: .export lines dropped; each pattern is .ifref-guarded (only the
; patterns the source above references assemble), RODATA segment.
; ============================================================================
; sprites_emotes.asm  --  14 sprites (16x16, TMS9918 sprite mode)
; derived: dev/lib/gen2/sprites/sprites_emotes_hgr.asm -- after editing this master rerun:
;   python3 tools/build_hgr_sprites.py --only emotes
; ----------------------------------------------------------------------------
; SCROLL-O-SPRITES by Quale, May 2013, CC-BY-3.0. Lifted from
; pic/undefined - Imgur.png by tools/extract_scroll_expressions.py and
; previously inlined into TMS_Logo_16k.asm. Pulled out so any project
; that wants a face / narrator sprite (CodeTank menu, narrator scenes,
; tutorials, etc.) can .import the labels without copy-pasting 384 B
; of pattern data.
;
; Layout: each 16x16 sprite occupies 32 bytes -- the first 16 bytes are
; the left half (column 0..7), the next 16 the right half (column 8..15).
; This is the native TMS9918 16x16 sprite layout: stream the 32 bytes
; into a sprite-pattern slot starting at base $3800 + slot*32.
;
; All shapes are static -- no directional or animation handling needed;
; SETSHAPE / equivalent just swaps the sprite-0 pattern.
; ============================================================================
.ifndef _SPRITES_EMOTES_ASM_LOADED_
_SPRITES_EMOTES_ASM_LOADED_ = 1

.pushseg
.rodata



; NORMAL -- neutral / default expression
.ifref serious_pat
serious_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $63, $77
        .byte $77, $7F, $7C, $7F, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $E2, $F6
        .byte $F6, $FE, $0E, $FE, $FC, $F8, $00, $00
.endif

; HAPPY -- happy
.ifref happy_pat
happy_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $63, $77
        .byte $77, $7F, $7D, $7E, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $E2, $F6
        .byte $F6, $FE, $EE, $1E, $FC, $F8, $00, $00
.endif

; SUPER -- super happy, big open mouth
.ifref excited_pat
excited_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $77, $77
        .byte $77, $7F, $7C, $7C, $3E, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $FA, $FA
        .byte $FA, $FE, $0E, $0E, $1C, $F8, $00, $00
.endif

; SAD -- sad / frown
.ifref sad_pat
sad_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $73, $67
        .byte $77, $7F, $7E, $7D, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $E6, $F2
        .byte $F6, $FE, $1E, $EE, $FC, $F8, $00, $00
.endif

; UPSET -- upset / disappointed
.ifref hurt_pat
hurt_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $67, $73
        .byte $67, $7F, $7E, $7C, $3C, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $F2, $E6
        .byte $F2, $FE, $1E, $0E, $0C, $F8, $00, $00
.endif

; ANGRY -- angry, frowning brows
.ifref angry_pat
angry_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $67, $73
        .byte $77, $7F, $7E, $7D, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $F2, $E6
        .byte $F6, $FE, $1E, $EE, $FC, $F8, $00, $00
.endif

; GRUMPY -- grumpy, tongue out
.ifref upset_pat
upset_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $67, $73
        .byte $77, $7F, $7E, $7C, $3C, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $F2, $E6
        .byte $F6, $FE, $0E, $0E, $1C, $F8, $00, $00
.endif

; PERV -- pervy / lewd
.ifref smug_pat
smug_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $7F, $63
        .byte $6F, $7F, $7E, $7F, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $FE, $E2
        .byte $EE, $FE, $FE, $3E, $FC, $F8, $00, $00
.endif

; SICK -- queasy / about to throw up (X eyes)
.ifref sick_pat
sick_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $7F, $7B
        .byte $7F, $7E, $7E, $7E, $3D, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $FE, $EE
        .byte $FE, $DE, $1E, $DE, $EC, $F8, $00, $00
.endif

; SLEEP -- asleep
.ifref sleeping_pat
sleeping_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $7F, $7B
        .byte $67, $7F, $7F, $7F, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $FE, $FA
        .byte $E6, $FE, $3E, $FE, $FC, $F8, $00, $00
.endif

; PIRATE -- pirate (one eye shut)
.ifref yarr_pat
yarr_pat:
        .byte $00, $00, $0F, $33, $7C, $7F, $67, $73
        .byte $77, $7F, $7C, $7F, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $3C, $C2, $C2
        .byte $E2, $FE, $0E, $FE, $FC, $F8, $00, $00
.endif

; SHADES -- wearing shades / sunglasses
.ifref nerd_pat
nerd_pat:
        .byte $00, $00, $1F, $3F, $7F, $7F, $00, $6E
        .byte $6E, $71, $7F, $7F, $3F, $1F, $00, $00
        .byte $00, $00, $F8, $FC, $FE, $FE, $00, $DC
        .byte $DC, $E2, $3E, $FE, $FC, $F8, $00, $00

; ============================================================================
; Extras: 16x16 birds (V silhouette / inverted V) + 8x8 heart. Lifted from
; TMS_Logo_16k.asm so any TMS9918 demo / narrator scene can pull them in.
; The 16x16 layout is the same as the emotes above (TL, BL, TR, BR halves).
; The heart is a single 8 B 8x8 block -- the typical SETSHAPE size flip
; (R1 = $C0 instead of $C2) belongs to the caller.
; ============================================================================

.endif

; BIRD1 -- bird with wings up (V silhouette).
.ifref bird1_pat
bird1_pat:
        ; TL (rows 0-7, cols 0-7)
        .byte $00, $80, $C0, $60, $38, $0F, $02, $03
        ; BL (rows 8-15, cols 0-7)
        .byte $03, $02, $00, $00, $00, $00, $00, $00
        ; TR (rows 0-7, cols 8-15)
        .byte $00, $01, $03, $06, $1C, $F0, $40, $C0
        ; BR (rows 8-15, cols 8-15)
        .byte $C0, $40, $00, $00, $00, $00, $00, $00

.endif

; BIRD2 -- bird with wings down (^ silhouette). BIRD1 mirrored vertically.
.ifref bird2_pat
bird2_pat:
        ; TL
        .byte $00, $00, $00, $00, $00, $02, $03, $03
        ; BL
        .byte $02, $0F, $38, $60, $C0, $80, $00, $00
        ; TR
        .byte $00, $00, $00, $00, $00, $40, $C0, $C0
        ; BR
        .byte $40, $F0, $1C, $06, $03, $01, $00, $00

.endif

; HEART (8x8 single block):
;     .##..##.   $66
;     ########   $FF
;     ########   $FF
;     ########   $FF
;     .######.   $7E
;     ..####..   $3C
;     ...##...   $18
;     ........   $00

.ifref heart_pat
heart_pat:
        .byte $66, $FF, $FF, $FF, $7E, $3C, $18, $00
.endif

.popseg
.endif  ; _SPRITES_EMOTES_ASM_LOADED_
