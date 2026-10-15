; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Scene geometry only. Returns before the resident wrapper loads the raw
; asset; no overlay calls into another overlay. Nearby sites (the wreck, the
; shelter: the log or the rock, the ranger outpost; on XL the built tent,
; hut, igloo and trench of lot 3) are billboards, one per view, nearest
; visible first; local sites/animals keep original art. The site sprites
; are read from NEOWILD.BLK (module_site_load, lot 6).
.segment "PROJECT"
SITE_LOG     = SITE_ASSET       ; scene_asset of the site sprites (dhgr.s):
SITE_ROCK    = SITE_ASSET + 1   ; the shelter (MAP+16 = 1 or 2),
SITE_OUTPOST = SITE_ASSET + 2   ; the ranger outpost at the goal; + 3..6:
SITE_COUNT   = 7                ; the tent, hut, igloo, trench (lot 3, XL)
SITE_HEAD    = 4                ; bytes of each image module_site_load checks
SITE_TENT    = 9                ; the tent's item (N_TENT, src/craft.s)
SITE_WINDOW  = $9600            ; where they are read (the SIM window)
SITE_ENTRY   = module_dir + 29 * 7      ; TB_FETCH (memory.s)
SITE_BANK_OF = module_dir + 28 * 7      ; TB_DIR, the text bank
module_project:
        lda     #0
        sta     scene_asset
        sta     scene_drawn
        lda     #9
        sta     proj_best
        ; Local view: the first site of local_order on the player's cell (the
        ; original's order: the wreck, the outpost, then SURV3D T0D/SE $5F4C:
        ; the igloo, the hut, the tent, the natural shelter, the trench).
        ldy     #SITE_COUNT-1
@local: ldx     local_order,y
        jsr     project_site    ; (keeps X and Y)
        bcs     @next
        lda     proj_x+1
        cmp     px+1
        bne     @next
        lda     proj_y+1
        cmp     py+1
        bne     @next
        lda     proj_asset
        jmp     project_local
@next:  dey
        bpl     @local
        ; The animal of the cell is not a candidate: module_animal draws it
        ; after the view, in front of the site (the original's two slots,
        ; $0D84 the site and $0D80 the animal).
        ; With only one nearby candidate its geometry is independent of
        ; heading. Keep it even offscreen so every turn can scroll it back
        ; into view without loading this module. Two or three coarse
        ; candidates keep the original nearest-visible selection and
        ; full-turn fallback. Ties go to the first: wreck, cabin, outpost,
        ; tent, hut, igloo, trench.
        lda     #0
        sta     proj_candidates
        ldx     #0
@count: jsr     project_site
        bcs     :+
        jsr     project_near
        bcc     :+
        inc     proj_candidates
:       inx
        cpx     #SITE_COUNT
        bne     @count
        lda     proj_candidates
        cmp     #2
        bcc     @select
        lda     #2
        sta     scene_drawn      ; bit 1: selection depends on heading
@select:
        ldx     #0
@pick:  jsr     project_site
        bcs     :+
        txa
        pha
        jsr     project_candidate
        pla
        tax
:       inx
        cpx     #SITE_COUNT
        bne     @pick
        lda     scene_asset
        beq     @done
        jmp     scene_height_bound
@done:  rts

; project_site -- X = 0 wreck, 1 the shelter (the log or the rock), 2 the
; ranger outpost, 3 the tent, 4 the hut, 5 the igloo, 6 the trench (lot 3):
; proj_x, proj_y, proj_asset and the bearing of its local view; C set when
; X has no site (no shelter on this map, a sprite not on this disk: the
; 140 KB edition has no built shelter, site_blocks 0). Preserves X and Y.
project_site:
        cpx     #2
        beq     project_outpost
        bcc     :+
        lda     site_blocks,x   ; 0: not on this disk (the 140 KB edition,
        beq     project_none    ; whose PROJECT ends at project_tail)
        jmp     project_shelter ; C set (X > 2)
:       cpx     #1
        beq     project_cabin
project_wreck:
        lda     M_HEAD
        sta     proj_bearing
        lda     M_HEAD+1
        sta     proj_bearing+1
        lda     M_STARTX
        sta     proj_x
        lda     M_STARTX+1
        sta     proj_x+1
        lda     M_STARTY
        sta     proj_y
        lda     M_STARTY+1
        sta     proj_y+1
        lda     #5
        sta     proj_asset
        clc
        rts
; cabin_asset -- the asset of the shelter of MAP+16..20, MAP+16 = 1 the
; log, 2 the rock: on a native map the natural shelter found there (travel.s,
; SURV3D $1CAA), on a generated map its fixed cabin, drawn as that shelter
; would be (tools/mkmap.py writes 2 when its cell is rocky, level >= 96).
project_cabin:
        lda     MAP+16
        bne     cabin_asset
project_none:
        sec
        rts
cabin_asset:
        adc     #SITE_ASSET-2   ; C set (cpx #1 equal): SITE_ASSET - 1 + MAP+16
        jsr     project_ahead
        lda     MAP+19          ; the bearing of its discovery
        sta     proj_bearing
        lda     MAP+20
        sta     proj_bearing+1
        lda     MAP+17
        sta     proj_x+1
        lda     MAP+18
        sta     proj_y+1
        clc
        rts
; The outpost stands where the journey ends: the corner of the goal cell on
; a native map (module_at_goal), the centre of the goal cell otherwise (won
; within one cell).
project_outpost:
        lda     #SITE_OUTPOST
        jsr     project_ahead
        lda     MAP+37
        beq     :+
        lda     #0
        sta     proj_x
        sta     proj_y
:       lda     M_GOALX
        sta     proj_x+1
        lda     M_GOALY
        sta     proj_y+1
        clc
        rts
; project_ahead -- proj_asset = A, its local view in front of the player
; (the heading), at the centre of a cell (proj_x, proj_y low bytes 128).
project_ahead:
        sta     proj_asset
        lda     heading
        sta     proj_bearing
        lda     heading+1
        sta     proj_bearing+1
        lda     #128
        sta     proj_x
        sta     proj_y
        rts

; module_site_load -- (site_load, overlay_load of A = SITE_ASSET..) the site
; sprite into SITE_WINDOW, unless it is already there: whole blocks of
; NEOWILD.BLK through the scratch entry TB_FETCH of the directory (whose bank
; and page count text_fetch never rewrites: both are put back after), with
; ProDOS's bitmap freed around the read (sim_fetch). The window no longer
; holds the simulation (sim_loaded = 0). Runs from a view's preparation or
; turn, never with the simulation's code on the stack (as the stars).
module_site_load:
        sec
        sbc     #SITE_ASSET
        pha
        asl     a               ; Y = SITE_HEAD * site
        asl     a
        tay
        ldx     #0
@same:  lda     SITE_WINDOW,x
        cmp     site_heads,y
        bne     @read
        iny
        inx
        cpx     #SITE_HEAD
        bne     @same
        pla
        rts
@read:  pla
        tax
        lda     #BANK_DISK
        sta     SITE_ENTRY
        lda     site_blocks,x
        sta     SITE_ENTRY+1
        lda     site_len_lo,x
        sta     SITE_ENTRY+3
        lda     site_len_hi,x
        sta     SITE_ENTRY+4
        lda     #<SITE_WINDOW   ; 0
        sta     SITE_ENTRY+5
        sta     SITE_ENTRY+2    ; NEOWILD.BLK under block 256 (build_disk)
        sta     sim_loaded
        lda     #>SITE_WINDOW
        sta     SITE_ENTRY+6
        ldx     #TB_FETCH
        jsr     sim_fetch
        lda     SITE_BANK_OF    ; the text bank's own bank
        sta     SITE_ENTRY
        lda     #0              ; texts are under a page
        sta     SITE_ENTRY+4
        rts

project_local:
        sta     proj_asset
        lda     #0
        sta     proj_shift
        sta     proj_depth
        jsr     project_center
        jsr     project_commit
        jmp     scene_height_bound

; module_animal -- (animal_view, after the view) the animal of the cell,
; always in view while it is there (decision of 15 October 2026, docs/
; LOOK_UPDOWN.md 5): facing the player whatever the heading (LOOK L/R/B,
; turns), centred, in front of the site of the cell and of everything else
; (drawn last), clear of a campfire burning on the cell (animal_fire).
; Without light (no shade: night without a full Moon; the silhouette of
; sunset and civil twilight; the dim nautical and moonlit night) a night
; silhouette: code 0 dark blue, the other codes grey. None looking up
; (SURV3D $1C52), nor in a shelter (no view). The column loop runs from
; ANIMAL_RUN in the SIM window (free during a view: the campfire's
; buffers) while the sprite takes the $5800 window. Before drawing, the
; background under the animal goes to the auxiliary language card (OUTDOOR
; module_animal_bg, docs/MEMORY.md 28): an arrow turn puts it back and
; scrolls the view instead of redrawing it (game.s turn_view, animal_unpan).
ANIMAL_RUN = $A000
module_animal:
        lda     animal_x
        cmp     px+1
        bne     @none
        lda     animal_y
        cmp     py+1
        bne     @none
        lda     tilt
        cmp     #1
        bne     @here
@none:  rts
@here:  lda     animal_kind
        cmp     #9              ; fourth species: sprite module 23
        bne     :+
        lda     #23
:       jsr     project_ahead   ; bearing = heading: centred
        lda     #0
        sta     proj_shift
        sta     proj_depth
        jsr     project_center  ; proj_width, proj_left = 70 - width / 2
        jsr     animal_fire
        ; The bytes of its columns, both banks (OUTDOOR ab_copy): AB_J0 =
        ; the byte of its first column, AB_N + 1 bytes from there (at most
        ; 22: animals up to 72 columns, the crocodile; scene_ref checks it).
        lda     proj_left       ; first column max(0, AL)
        ldx     proj_left+1
        bpl     :+
        lda     #0
:       sta     animal_code + an_first + 1 - ANIMAL_RUN
        jsr     div7            ; column 7g + k: byte 2g, + 1 when k >= 4
        cmp     #4
        txa
        rol     a
        sta     AB_J0
        lda     proj_left       ; last column min(140, AL + W) - 1
        clc
        adc     proj_width
        cmp     #140
        bcc     :+
        lda     #140
:       sta     animal_code + an_last + 1 - ANIMAL_RUN
        sec                     ; (the column loop runs over its columns only)
        sbc     #1
        jsr     div7            ; its last bit 4c + 3: byte 2g, + 1 when k >= 3
        cmp     #3
        txa
        rol     a
        sec
        sbc     AB_J0
        sta     AB_N
        jsr     project_commit  ; scene_asset, sprite_* ($5800 window)
        lda     cur_pal+PAL_SHADE ; 0 day, 1 warm, 4 moonlight: the mood's
        cmp     #2              ; shade; 2, 3, $FF: the night silhouette
        bcc     @lit
        cmp     #4
        beq     @lit
        lda     #$55            ; grey 1
        ldy     #3
:       sta     spr_map,y
        dey
        bne     :-
        lda     #$22            ; dark blue
        sta     spr_map
        bne     @run
@lit:   jsr     dhgr_sprite_map
@run:   lda     #3              ; a turn redraws the whole view (game.s
        sta     scene_drawn     ; turn_view), unless module_animal_bg keeps
                                ; the background ($83: it scrolls)
        lda     #0              ; sprite_* hold the animal: the next view
        sta     scene_cache_valid ; recomputes its scene
        ldx     #animal_end - ANIMAL_RUN
:       lda     animal_code-1,x
        sta     ANIMAL_RUN-1,x
        dex
        bne     :-
        jmp     ANIMAL_RUN
; animal_fire -- a campfire burning on the cell (src/fire.s: 28 columns
; from FL = 56 + fire_bear - heading) and the animal (AL = 70 - W / 2, W
; columns) overlap: the animal goes to the right of the fire when the fire
; is left of the centre of the view (FL <= 56, the fire lit facing the
; heading included), clipped at the right edge, else to its left.
animal_fire:
        lda     fire_on
        beq     @no
        lda     fire_cx
        cmp     px+1
        bne     @no
        lda     fire_cy
        cmp     py+1
        bne     @no
        lda     proj_left       ; AL (30..70: animal widths up to 80)
        sta     qlo
        lda     proj_width      ; W
        sta     qhi
        lda     fire_bear
        sta     proj_bearing
        lda     fire_bear+1
        sta     proj_bearing+1
        lda     #28
        sta     proj_width
        jsr     project_offset  ; proj_left = FL
        lda     qhi             ; the animal's width again (module_animal's
        sta     proj_width      ; columns: the loop, the background)
        ldx     #0
        lda     proj_left+1     ; FL < 0 or > 255: no overlap
        bne     @keep
        lda     proj_left
        cmp     #57
        bcs     @leftof
        adc     #28             ; right of the fire: max(AL, FL + 28)
        cmp     qlo
        bcs     @set
@keep:  lda     qlo             ; AL
        bpl     @set
@leftof:
        sbc     qhi             ; left of the fire: min(AL, FL - W)
        bcs     :+
        dex                     ; FL - W < 0
        bcc     @set
:       cmp     qlo
        bcs     @keep
@set:   sta     proj_left
        stx     proj_left+1
@no:    rts
; Copied to ANIMAL_RUN: the sprite into the $5800 window, then every
; column of the view (sprite_column paints the opaque rows of a local
; sprite, scene_emit), interrupts masked as in render.
animal_code:
        .org    ANIMAL_RUN
        lda     #22             ; OUTDOOR: the background, kept
        jsr     overlay_load
        jsr     module_animal_bg
        lda     scene_asset
        jsr     overlay_load
        php
        sei
an_last = *
        ldx     #140            ; patched: min(140, AL + W), from the right
:       dex
        stx     col
        jsr     column_setup
        jsr     sprite_column
        ldx     col
an_first = *
        cpx     #0              ; patched: max(0, AL), its first column
        bne     :-
        plp
        rts
animal_end:
        .reloc

project_near:
        ; Integer coarse rejection before ROM math. Eight cells in either
        ; axis need the fractional coordinate checked at the radial limit.
        sec
        lda     proj_x+1
        sbc     px+1
        cmp     #9
        bcc     :+
        cmp     #248
        bcs     :+
        clc
        rts
:       sec
        lda     proj_y+1
        sbc     py+1
        cmp     #9
        bcc     :+
        cmp     #248
        bcs     :+
        clc
        rts
:       sec
        rts

project_candidate:
        jsr     project_near
        bcs     :+
        rts
:       sec
        lda     proj_x
        sbc     px
        tay
        lda     proj_x+1
        sbc     px+1
        jsr     GIVAYF
        fop     FMULT, proj_1_256
        fst     t1               ; east, in cells
        fop     FMULT, t1
        fst     t3
        sec
        lda     proj_y
        sbc     py
        tay
        lda     proj_y+1
        sbc     py+1
        jsr     GIVAYF
        fop     FMULT, proj_1_256
        fst     t2               ; north = site Y - player Y, as on TOPO
        fop     FMULT, t2
        fop     FADD, t3
        jsr     FSQR
        jsr     AYINT
        lda     $A0
        beq     :+
        rts
:
        lda     $A1
        cmp     #8
        bcc     :+
        rts
:
        clc
        adc     #1
        sta     proj_depth       ; billboard inserted at floor(distance)+1
        lda     scene_drawn
        ora     #1
        sta     scene_drawn
        lda     proj_depth
        cmp     proj_best
        bcc     :+
        rts
:
        ; Bearing = atan2(east,north), converted to 560 units per turn.
        fld     t2
        lda     FAC
        beq     @east_west
        fld     t2
        fop     FDIV, t1         ; east / north (memory / FAC)
        jmp     @angle
@east_west:
        lda     #140
        sta     proj_bearing
        lda     #0
        sta     proj_bearing+1
        lda     t1+1
        bpl     @bearing_done
        lda     #<420
        sta     proj_bearing
        lda     #>420
        sta     proj_bearing+1
        jmp     @bearing_done
@angle:
        jsr     FATN
        fop     FMULT, proj_angle
        fop     FADD, f_half
        jsr     AYINT
        lda     $A1
        sta     ang
        lda     $A0
        sta     ang+1
        lda     t2+1
        bpl     @north
        clc
        lda     ang
        adc     #<280
        sta     ang
        lda     ang+1
        adc     #>280
        sta     ang+1
@north:
        jsr     wrap_ang
        lda     ang
        sta     proj_bearing
        lda     ang+1
        sta     proj_bearing+1
@bearing_done:
        lda     proj_depth
        ldx     #0
@scale: cmp     #2
        bcc     @scaled
        lsr     a
        inx
        bne     @scale
@scaled:
        stx     proj_shift
        jsr     project_center
        lda     scene_drawn
        cmp     #2
        bcc     @visible         ; sole candidate may remain offscreen
        ; Width overlaps columns 0..139? Keep signed left coordinate.
        lda     proj_left+1
        bmi     @left_edge
        beq     :+
        rts
:
        lda     proj_left
        cmp     #140
        bcc     :+
        rts
:
        jmp     @visible
@left_edge:
        clc
        lda     proj_left
        adc     proj_width
        sta     proj_half
        lda     proj_left+1
        adc     #0
        bpl     :+
        rts
:
        ora     proj_half
        bne     :+
        rts
:
@visible:
        jsr     project_ground
        bcc     :+
        rts
:
        lda     proj_depth
        sta     proj_best
        jmp     project_commit
project_reject:
        rts

project_center:
        jsr     proj_index
        lda     proj_widths-5,x
        sta     proj_width
        ldx     proj_shift
        beq     project_offset
@half:  inc     proj_width
        lsr     proj_width
        dex
        bne     @half
; project_offset -- proj_left = 70 - proj_width / 2 + the angle from the
; heading to proj_bearing in (-280, 280], 16-bit signed.
project_offset:
        sec
        lda     proj_bearing
        sbc     heading
        sta     ang
        lda     proj_bearing+1
        sbc     heading+1
        sta     ang+1
        jsr     wrap_ang        ; 0..559 (only adds 560 here)
        lda     ang
        cmp     #<280
        lda     ang+1
        sbc     #>280
        bcc     @center
        sec
        lda     ang
        sbc     #<560
        sta     ang
        lda     ang+1
        sbc     #>560
        sta     ang+1
@center:
        lda     proj_width
        lsr     a
        sta     proj_half
        lda     #70
        sec
        sbc     proj_half
        clc
        adc     ang
        sta     proj_left
        lda     ang+1
        adc     #0
        sta     proj_left+1
        rts

project_ground:
        jsr     level_here      ; ROM floating point owns the ray's zero page
        clc
        adc     #EYE
        sta     eye
        ldx     proj_y+1
        ldy     proj_x+1
        jsr     cell_at
        and     #127
        sec
        sbc     eye
        sta     proj_dz
        bpl     :+
        eor     #$FF
        clc
        adc     #1
:       pha
        lda     proj_depth
        sta     divisor
        pla
        cmp     divisor
        bcs     @big
        jsr     smalldiv
        sta     qlo
        lda     #0
        sta     qhi
        beq     @row
@big:   jsr     bigdiv
@row:   lda     qlo
        sta     proj_q
        lda     qhi
        sta     proj_q+1
        asl     qlo
        rol     qhi
        clc
        lda     qlo
        adc     proj_q
        sta     qlo
        lda     qhi
        adc     proj_q+1
        sta     qhi
        bcs     @steep          ; 3*q overflow would bring a hidden site onscreen
        lda     proj_dz
        bpl     @shift
        clc
        lda     qlo
        adc     #15
        sta     qlo
        bcc     @shift
        inc     qhi
@shift: ldx     #4
@divide:
        lsr     qhi
        ror     qlo
        dex
        bne     @divide
        lda     qhi
        bne     @steep
        lda     proj_dz
        bmi     @below
        lda     #95
        sec
        sbc     qlo
        bcs     @save
@top:   lda     #0              ; above the view: anchored at row 0, its
        beq     @save           ; bottom row clipped there (tests/scene_ref)
@below: lda     #95
        clc
        adc     qlo
        bcs     @reject
        cmp     #252
        bcs     @reject
@save:  sta     proj_anchor
        clc
        rts
@steep: lda     proj_dz         ; 3*q/16 >= 256: a site far above the eye
        bpl     @top            ; still stands at row 0, one far below hides
@reject:
        sec
        rts

project_commit:
        lda     proj_asset
        sta     scene_asset
        jsr     proj_index
        lda     proj_bases-5,x
        sta     sprite_base
        lda     #10
        cpx     #5              ; the wreck and the outpost stand on the
        beq     :+              ; ground (the original's bit-7 sites), the
        cpx     #SITE_OUTPOST-16 ; other local sprites are lifted 10 rows
        bne     :++
:       lda     #0
:       sta     sprite_origin
        ; The page of the sprite in sprite_column: the $5800 window, or the
        ; SIM window for a site sprite (module_site_load), with its colours.
        ldy     #>$5800
        cpx     #SITE_ASSET-16
        bcc     @page
        lda     proj_asset
        sbc     #SITE_ASSET     ; C set
        asl     a
        asl     a
        tay
        ldx     #0
:       lda     site_colours,y
        sta     dhgr_site,x
        iny
        inx
        cpx     #4
        bne     :-
        ldy     #>SITE_WINDOW
@page:  sty     sprite_page0+2
        sty     sprite_page1+1
        sty     sprite_page2+1
        sty     sprite_page3+1
        lda     proj_left
        sta     sprite_left
        lda     proj_left+1
        sta     sprite_left+1
        lda     proj_shift
        sta     sprite_shift
        tax
        lda     proj_masks,x
        sta     sprite_mask
        lda     proj_depth
        sta     scene_depth
        clc
        adc     #127
        sta     scene_trigger
        lda     proj_anchor
        sta     sprite_anchor
        lda     scene_drawn
        ora     #1
        sta     scene_drawn
        rts

; X = table index of proj_asset: overlays 5..9, then 10 for module 23
; (fourth species), 17..22 for the site sprites SITE_ASSET..SITE_ASSET+5,
; 29 for the trench (SITE_ASSET+6: its width and base follow the rows of
; the first six, which overlap by one byte at proj_widths + 18).
proj_index:
        ldx     proj_asset
        cpx     #23
        bne     :+
        ldx     #10
:       cpx     #SITE_ASSET
        bcc     :+
        txa
        sbc     #16             ; C set
        tax
        cpx     #SITE_ASSET+6-16
        bne     :+
        ldx     #29
:       rts

; proj_sprites: width and bottom opaque row of the wreck, species 1-3, the
; cabin and species 4; the region pack rewrites the 12 bytes for its
; sprites (tools/build_disk.py). The trunk holds the Sierra Nevada.
; The site sprites follow, the same in every region (site k = scene_asset
; - SITE_ASSET: the log, the rock, the outpost, then lot 3's tent, hut,
; igloo and trench): widths at proj_widths + 12 + k and bottom opaque rows
; at proj_bases + 12 + k for k = 0..5; the trench's at proj_widths + 24 and
; proj_bases + 24 (proj_index 29).
proj_sprites:
proj_widths: .byte 119,39,52,33,61,0
proj_bases: .byte 158,168,151,150,152,0
.export proj_sprites
        .byte 88,59,75,58,61,57 ; widths of the site sprites (proj_widths + 12)
        .byte 145,159,159,152,152,153 ; bottom opaque rows (proj_bases + 12)
        .byte 56                ; the trench: width (proj_widths + 24)
proj_1_256: .byte $79,$00,$00,$00,$00
        .byte 159               ; the trench: bottom opaque row (proj_bases + 24)
.assert proj_1_256 + 5 = proj_bases + 24, error, "site sprite tables out of step"
; site_blocks: first block of each site sprite in NEOWILD.BLK (0: not on
; this disk, lot 3's shelters on the 140 KB edition), written by
; tools/build_disk.py
site_blocks: .res SITE_COUNT
; Raw lengths (the directory entry: whole blocks read into SITE_WINDOW).
site_len_lo: .byte <1216,<1158,<2289,<969,<1133,<859,<403
site_len_hi: .byte >1216,>1158,>2289,>969,>1133,>859,>403
; Day colours of codes 0..3 (tools/dhgr_palette.py SPRITES, checked by
; tools/build_disk.py), copied to dhgr_site.
site_colours:
        .byte 0, 9, 8, 13       ; log: black, orange ends, brown bark, yellow
        .byte 0, 5, 4, 10       ; rock: black, grey, dark green moss, light grey
        .byte 0, 8, 4, 15       ; outpost: black, brown roof, green door, white
        .byte 0, 9, 4, 15       ; tent: black, orange canvas, green floor, white
        .byte 0, 8, 4, 13       ; hut: black, brown posts, green thatch, yellow
        .byte 0, 7, 10, 15      ; igloo: black, light blue joints, light grey, white
        .byte 0, 8, 4, 5        ; trench: black, brown earth, green boughs, grey
; Local order (module_project), read from the end: the wreck, the outpost,
; the igloo, the hut, the tent, the natural shelter, the trench.
local_order: .byte 6, 1, 3, 4, 5, 2, 0
.export site_blocks, site_colours, site_len_lo
proj_masks: .byte 0,1,3,7
proj_angle: .byte $87,$32,$40,$E7,$C1 ; 560 / (2*pi)
proj_asset: .byte 0
proj_x: .word 0
proj_y: .word 0
proj_bearing: .word 0
proj_left: .word 0
proj_width: .byte 0
proj_half: .byte 0
proj_best: .byte 9
proj_shift: .byte 0
proj_depth: .byte 0
proj_anchor: .byte 0
proj_dz: .byte 0
proj_q: .word 0
proj_candidates: .byte 0

; A conservative highest possible ridge at each future ray distance. This
; is built once per frame, using the SAME division/row tables as the terrain.
; Legacy maps without a maximum use the format limit (125).
.segment "PROJECT"
scene_height_bound:
        lda     scene_drawn
        beq     @done
        jsr     level_here
        clc
        adc     #EYE
        sta     eye
        lda     MAP+21
        bne     :+
        lda     #126
:       sec
        sbc     #1
        sec
        sbc     eye
        bcs     :+
        lda     #0
:       sta     sprite_width     ; width half is no longer needed after prepare
        lda     #1
        sta     scene_distance
@distance:
        lda     scene_distance
        sta     divisor
        lda     sprite_width
        cmp     divisor
        bcs     @big
        jsr     smalldiv
        tax
        lda     row_p0,x
        jmp     @store
@big:   jsr     bigdiv
        tax
        lda     qhi
        cmp     #2
        bcs     @zero
        lda     row_p0,x
        sec
        sbc     #48
        jmp     @store
@zero:  lda     #0
@store: bit     tilt            ; looking down every ridge is 96 rows higher
        bpl     :+              ; (a lower bound stays conservative back at
        sec                     ; level; tilting down drops the scene cache)
        sbc     #96
        bcs     :+
        lda     #0
:       ldy     scene_distance
        dey
        sta     scene_ceiling,y
        inc     scene_distance
        lda     scene_distance
        cmp     #129
        bcc     @distance
@done:  rts


; fauna_cause -- m_fauna_stop names what set fauna_alert (resident stub;
; the window then holds PROJECT, the callers are resident and show_view or
; report reload what they need). No random draw, no game state written.
.segment "LOWPAGE"
fauna_cause:
        lda     #11
        jsr     overlay_load
        jmp     module_fauna_cause

.segment "PROJECT"
; An animal accepted during this step (fauna_accept: on the player's cell,
; age 0) comes first, with the region's species name: "BEAR IN YOUR AREA!"
; (the original's event 32 is "A <ANIMAL> HAS ENTERED YOUR AREA!").
; Otherwise the first resource of this scan (MAP+36 bits 0-7: types 5-12 of
; T0A/S00), else the natural shelter (type 13, MAP+16): "YOU FIND FISH."
module_fauna_cause:
        ldx     #0
        lda     animal_kind
        beq     @resource
        ldy     animal_age
        bne     @resource
        ldy     animal_x
        cpy     px+1
        bne     @resource
        ldy     animal_y
        cpy     py+1
        bne     @resource
        asl     a               ; 12 * kind + region_species - 72
        asl     a
        sta     gp2
        asl     a
        adc     gp2
        adc     #<(region_species - 72)
        ldy     #>region_species
        jsr     cause_append
        lda     #<cause_area
        ldy     #>cause_area
        bne     cause_append
@resource:
        lda     #<cause_find
        ldy     #>cause_find
        jsr     cause_append
        lda     MAP+36
        ldy     #0
@bit:   lsr     a
        bcs     @found
        iny
        cpy     #8
        bne     @bit            ; no bit: Y = 8, the shelter
@found: lda     cause_offsets,y
        clc
        adc     #<cause_names
        ldy     #>cause_names
        bcc     cause_append
        iny
; A/Y = zero-terminated text, appended at X in m_fauna_stop (X ends on the 0).
cause_append:
        sta     gp2
        sty     gp2+1
        ldy     #0
@copy:  lda     (gp2),y
        sta     m_fauna_stop,x
        beq     @done
        inx
        iny
        bne     @copy
@done:  rts
cause_area: .byte " IN YOUR AREA",'!'|$80,0 ; message: a bare "!" is the stop reason
cause_find: .byte "YOU FIND ",0
cause_names:
        .byte "GAME ANIMALS.",0,"FISH.",0,"INSECTS.",0,"FRUIT.",0,"CACTI.",0
        .byte "MUSHROOMS.",0,"PLANTS.",0,"NUTS.",0,"SHELTER.",0
cause_offsets: .byte 0,14,20,29,36,43,54,62,68
.assert SITE_ENTRY = module_dir + TB_FETCH * DIR_SIZE && SITE_BANK_OF = module_dir + TB_DIR * DIR_SIZE, error, "site sprite entry"
.assert SITE_TENT = N_TENT, error, "the tent item"

; ---------------------------------------------------------------------------
; The tail of PROJECT: what only the built shelters use (lot 3 step 3, XL).
; The 140 KB edition has none of their sprites (site_blocks 0: project_site
; never comes here, module_site_load never asks for them), and
; tools/build_disk.py cuts PROJECT at project_tail on that disk.
;
; The first SITE_HEAD bytes of each image (its width and first offsets),
; written by tools/build_disk.py: module_site_load reads the disk only when
; the SIM window does not start with them (anything else put there since,
; the SIM, a screen, the stars, the campfire, starts at SITE_WINDOW).
site_heads: .res 3 * SITE_HEAD  ; the log, the rock, the outpost
project_tail:
        .res 4 * SITE_HEAD      ; the tent, the hut, the igloo, the trench
; The built shelters (lot 3, src/craft.s): the tent where it lies (USE TENT
; sets it down), never at the wreck (msg 49: the tent of the crash site is
; not pitched); the hut, the igloo and the trench on their cell (cr_sx,
; cr_sy: $FF when never made).
project_shelter:
        txa
        adc     #SITE_ASSET-1   ; C set (X > 2)
        jsr     project_ahead
        cpx     #3
        bne     @built
        lda     it_place+SITE_TENT
        bne     @none
        lda     it_x+SITE_TENT
        sta     proj_x+1
        lda     it_y+SITE_TENT
        sta     proj_y+1
        cmp     M_STARTY+1
        bne     @found
        lda     proj_x+1
        cmp     M_STARTX+1
        bne     @found
@none:  sec
        rts
@built:
        lda     cr_sx-4,x       ; $FF: never made
        cmp     #$FF
        beq     @none
        sta     proj_x+1
        lda     cr_sy-4,x
        sta     proj_y+1
        ; Evaluated after the wreck, the shelter and the outpost: one no
        ; nearer than the best billboard so far (floor(max(|dx|, |dy|)) >=
        ; proj_best, so its depth would be too) costs no ROM arithmetic.
        ; proj_best is 9 for the local view and the count: no change there.
@found: sec
        lda     proj_x
        sbc     px
        lda     proj_x+1
        sbc     px+1
        bpl     :+
        eor     #$FF            ; floor(|dx|), or one less: still a bound
:       cmp     proj_best
        bcs     @none
        sec
        lda     proj_y
        sbc     py
        lda     proj_y+1
        sbc     py+1
        bpl     :+
        eor     #$FF
:       cmp     proj_best
        bcs     @none
        clc
        rts
project_end:
.export site_heads, project_tail, project_end
