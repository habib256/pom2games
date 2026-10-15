; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; menu.s -- the four 80-column rows as a command surface (lot 8, step 2;
; docs/MENUS.md section 4).
;
;   rows 20-23, columns 0-38   the last result, wrapped by words (message),
;                              then, when the result leaves row 23 free,
;                              the stock row (food and water carried and
;                              here), or "> " + the command as the parser
;                              will read it while one is typed or composed
;   column 39                  separator
;   rows 20-23, columns 41-78  the grid of verbs (6 cells of 6: eleven
;                              base verbs at fixed cells, greyed in lower
;                              case when they cannot act here, then the
;                              contextual ones that can), then the list of
;                              the open verb (durations, directions, items
;                              in 3 cells of 12, ounces); four rows
;                              visible, scrolled by row; the selected cell
;                              in inverse
;
; Three homes (docs/MEMORY.md sections 11 and 18):
;   MENUCODE  $BA00-$BDFF, resident: what commands and the INPUT module
;             need (message's result column, prompt), the keyboard loop,
;             row 23, the stock row, the state. The area is the ProDOS I/O
;             buffer of the end of a journey only (the loader has its own).
;   MENUSWAP  $B000-$B5FF, the top of the SIM window, free between two
;             simulation steps (the star module's tables end below $B000):
;             the grid, its lists and tables. The image sleeps in the HGR
;             rows 176-191 of both banks, hidden under the mixed text rows
;             and never drawn (32 chunks of 48 bytes, holes included), put
;             there by the loader (boot.s ld_scatter) and copied back by
;             get_line at every prompt (menu_gather, 1,536 bytes).
;   GRID      src/grid.s, a module of the store copied below MENUSWAP at
;             each RETURN in the grid and each step of its queue: the
;             lists, the composition, the queue of prerequisites.
;
; get_line keeps its contract: inbuf / linelen hold a command when it
; returns; the menu composes the same text the keyboard would give. An item
; chosen in a list is also passed in menu_noun, since display names such
; as COTTN SOCKS are not vocabulary words (resolve_noun).
; Modes: 0 typed line (on an empty line LEFT/RIGHT turn the view, RETURN or
; TAB opens the grid; UP shows the top pages, STATUS first, DOWN the bottom
; ones, TOPO first); 1 grid (arrows move, UP on the first row of verbs and TAB
; close it, RETURN selects, ESC backs up). The numeric
; prompt of the INPUT module (prompt) uses the same row. A command issued
; from the grid leaves the grid open for the next one.
; ============================================================================
.segment "MENUCODE"

MN_RES   = 0                    ; first column of the result column
MN_SEP   = 39                   ; separator column
MN_END   = MN_SEP               ; column after the result column
MN_GRID  = 41                   ; first column of the grid
MN_LAST  = 79                   ; reserved column (never written)
MN_ROWS  = 4                    ; rows of the grid and of the result column
MN_BOTTOM = 23                  ; last row
KC_TAB   = $09                  ; TAB (Ctrl-I): the grid on, the grid off
; Verb kinds (the first byte of a verb_table entry; bit 7 = K_BASE: a base
; verb at a fixed cell, shown greyed in lower case when it cannot act here
; rather than hidden; docs/MENUS.md 4).
K_NONE   = 0                    ; the label (and its suffix) is the command
K_DUR    = 1                    ; durations
K_LOOK   = 2                    ; directions
K_CLIMB  = 3                    ; TREE or DOWN, the one that applies
K_MAKE   = 4                    ; lot 2: FIRE, WATER (what can be made here)
K_CARE   = 5                    ; the MEDICAL page, focus on the first condition
K_BOIL   = 6                    ; BOIL WATER (UTENSILS first)
K_ITEMS  = 7                    ; + filter: F_GET .. F_COOK (src/grid.s)
K_BASE   = $80
F_GET    = 0                    ; item filters (filt_*, grid.s gr_ranges)
F_WEAR   = 1
F_DROP   = 2
F_EAT    = 3
F_USE    = 4
F_DRINK  = 5
F_KILL   = 6                    ; lot 4: named targets (forage_menu decides)
F_SKIN   = 7
F_CATCH  = 8
F_COOK   = 9
E_KILL   = 12                   ; verb_table entry of the animal's KILL
C_SHELTER = 1                   ; context: shown only at the cabin cell, outside
C_INSIDE = 2                    ; inside the cabin
C_ANIMAL = 3                    ; an animal on the player's cell
C_SUFFIX = 4                    ; a second string completes the command
; Bits 5-7: a condition of the place (src/game.s verb_extra, 14 October 2026:
; the grid offers only what can be done here).
X_FIRE   = 32                   ; a fire burns (lot 2: DOUSE)
X_SWIM   = 64                   ; in water, or the next half-step enters it
X_CLIMB  = 96                   ; a tree here (TREE), or in a tree (DOWN)
X_HANG   = 128                  ; a tree here and the backpack carried
X_LOWER  = 160                  ; the backpack hung on this cell
X_WALK   = 192                  ; not in water, no water ahead (one cell: WALK or SWIM)
X_FORAGE = 224                  ; lot 4: CATCH, KILL small game or fish here,
                                ; SKIN a carcass, COOK (fire) (src/forage.s
                                ; forage_menu)
G_WORN   = 1                    ; item group masks (inventory groups)
G_HAND   = 2
G_PACK   = 4
G_GROUND = 8
G_HUNG   = 16
SWAP_RUN = $B000                ; MENUSWAP run address (src/wild.cfg SWAP)
SWAP_ROW = $2350                ; HGR row 176: first hidden chunk
SWAP_CHUNKS = 16                ; chunks of 48 bytes per bank
.segment "MZP": zeropage
; Temporaries of the drawing and the lists ($F0-$F8: outside the render
; scratch and the Applesoft floating point area, src/wild.cfg).
mn_i:   .res 1
mn_c:   .res 1
mn_row: .res 1
mn_col: .res 1
mn_w:   .res 1
mn_k:   .res 1
mn_inv: .res 1
mn_n:   .res 1
mn_t:   .res 1
mn_src: .res 2                  ; menu_gather: hidden row, swap destination
mn_dst: .res 2
.segment "MENUCODE"

; ----------------------------------------------------------------------------
; get_line -- the prompt: returns with the command in inbuf / linelen.
; ----------------------------------------------------------------------------
; fire_idle -- (idle) no key waits: the campfire's turn (src/fire.s).
fire_idle:
        jsr     fire_tick
        jmp     idle
get_line:
        jsr     menu_gather
        lda     mq_n            ; a queue of the grid (src/grid.s): its next
        beq     get_line_body   ; step, or the end of the queue
        jsr     grid_fetch
        jmp     module_queue
get_line_body:
        lda     mn_mode
        cmp     #1
        beq     :+
        lda     #0
        sta     mn_mode
:       jsr     level1
        jsr     stock_row
        jsr     redraw
idle:   lda     KBD             ; tests wait for this loop
        bpl     fire_idle
        bit     KBDSTRB
        sta     fire_dly+1      ; a key: the fire waits (src/fire.s)
        and     #$7F
        jsr     kbd_upcase
        ldx     mn_mode
        cpx     #1
        jeq     menu_key
prompt_key:
        cmp     #KC_RET
        beq     @ret
        cmp     #KC_UP
        beq     @status
        cmp     #KC_TAB
        beq     @open
        cmp     #KC_DOWN        ; DOWN opens the grid (its last row: TOPO)
        beq     @open
        cmp     #KC_LEFT
        beq     @left
        cmp     #KC_RIGHT
        beq     @right
        cmp     #KC_ESC
        beq     @clear
        cmp     #' '
        bcc     idle
        cmp     #'Z'+1
        bcs     idle
        ldx     linelen
        cpx     #MAXLINE
        bcs     idle
        sta     inbuf,x
        inc     linelen
        lda     #0
        sta     inbuf+1,x
@line:  jsr     draw_line
        jmp     idle
@ret:   lda     linelen
        bne     done_typed
@open:  lda     #1
        sta     mn_mode
        jsr     redraw
        jmp     idle
@status:
        lda     #<str_status
        sta     gp2
        lda     #>str_status
        sta     gp2+1
        jsr     append_str
        jmp     done_typed
@left:  ldx     linelen
        beq     @turnl
        dec     linelen
        ldx     linelen
        lda     #0
        sta     inbuf,x
        beq     @line
@turnl: ldx     #0
        beq     @turn
@right: ldx     linelen
        jne     idle
        ldx     #1
@turn:  jsr     fire_hide       ; the view scrolls: no fire in it (X kept)
        jsr     turn_view
        jsr     level1          ; SWIM depends on the heading
        jsr     draw_grid
        jmp     idle
@clear: lda     #0
        sta     linelen         ; inbuf itself is left as the reference does
        beq     @line
done_typed:
        lda     #0
        sta     mn_mode         ; the next prompt starts on the typed line
done:   jsr     fire_hide       ; every command and screen sees the bare view
        ldx     linelen
        lda     #0
        sta     inbuf,x
        rts
done_menu:
        lda     #1              ; the next prompt starts in the grid
        sta     mn_mode
        bne     done

; The grid is open: arrows move the selection, RETURN selects, ESC backs up.
menu_key:
        cmp     #KC_ESC
        jeq     @back
        cmp     #KC_TAB
        jeq     @close          ; TAB: back to the view, whatever the level
        cmp     #' '
        bcc     :+
        cmp     #'Z'+1
        bcs     :+
        pha                     ; a letter: back to the typed line
        jsr     to_prompt
        jsr     draw_grid       ; no selection any more
        pla
        jmp     prompt_key
:       ldx     mn_count
        jeq     idle            ; nothing to choose (an empty item list)
        cmp     #KC_LEFT
        beq     @prev
        cmp     #KC_RIGHT
        beq     @next
        cmp     #KC_UP
        beq     @up
        cmp     #KC_DOWN
        beq     @down
        cmp     #KC_RET
        jeq     select
        jne     idle
@prev:  ldx     mn_cur
        bne     :+
        ldx     mn_count
:       dex
        stx     mn_cur
        jmp     @moved
@next:  ldx     mn_cur
        inx
        cpx     mn_count
        bcc     :+
        ldx     #0
:       stx     mn_cur
        jmp     @moved
@up:    lda     mn_cur
        sec
        sbc     mn_cols
        bcs     :+
        lda     mn_level        ; above the first row of verbs: the view
        cmp     #1
        beq     @close
        jmp     idle
:       sta     mn_cur
        jmp     @moved
@down:  lda     mn_cur
        clc
        adc     mn_cols
        cmp     mn_count
        bcc     @below
        jsr     grid_bottom     ; no cell below
        jcs     done_typed      ; "T": the bottom pages
        jmp     @moved
@below: sta     mn_cur
@moved: jsr     scroll_to_cur
        jsr     draw_grid
        jmp     idle
@back:  lda     mn_level
        cmp     #1
        beq     @close
        jsr     level1          ; a list: back to the verbs
        jmp     @show
@close: lda     mn_level        ; the grid reopens on the same verb
        cmp     #1
        bne     :+
        jsr     verb_of_cur
:       jsr     to_prompt
@show:  jsr     redraw
        jmp     idle

; select -- (menu_key) RETURN in the grid: module_select, in GRID (src/grid.s).
select: jsr     grid_fetch
        jmp     module_select

; grid_bottom -- (menu_key, DOWN with no cell below) on the last row of the
; verbs, the grid closes (as UP on its first row does) and the line is "T":
; TOPO, the bottom pages; C set. Above a shorter last row: its last cell (the
; next DOWN goes on); in a list: no move; C clear.
grid_bottom:
        lda     mn_level
        cmp     #1
        bne     @stay
        lda     #0              ; A = the start of the row below
:       clc
        adc     mn_cols
        cmp     mn_cur
        beq     :-
        bcc     :-
        cmp     mn_count
        bcs     @pages
        ldx     mn_count
        dex
        stx     mn_cur
        clc
        rts
@pages: jsr     to_prompt
        lda     #<str_topo
        sta     gp2
        lda     #>str_topo
        sta     gp2+1
        jsr     append_str
        sec
        rts
@stay:  clc
        rts
; prompt -- the numeric prompt of the INPUT module: "> " on the last row of
; the result column, the cursor after it (the module echoes the digits).
prompt: lda     #0
        sta     linelen
        sta     mn_mode
        lda     #MN_BOTTOM
        sta     CV
        jsr     t_vtab
        jsr     res_clear
        jsr     draw_arrow
        lda     #MN_RES+2
        sta     CH
        rts

; menu_gather -- MENUSWAP from the hidden HGR rows to SWAP_RUN: 16 chunks
; of 48 bytes of the main bank, then of the auxiliary one (PAGE2 under
; 80STORE, as the text primitives do). Row 176 + 8g is at SWAP_ROW + $400 g,
; row 184 + 8g $80 further.
menu_gather:
        php
        sei
        lda     #<SWAP_RUN
        sta     mn_dst
        lda     #>SWAP_RUN
        sta     mn_dst+1
        sta     PAGE2_MAIN
        jsr     @bank
        sta     PAGE2_AUX
        jsr     @bank
        sta     PAGE2_MAIN
        plp
        rts
@bank:  lda     #<SWAP_ROW
        sta     mn_src
        lda     #>SWAP_ROW
        sta     mn_src+1
        ldx     #SWAP_CHUNKS
@chunk: ldy     #47
:       lda     (mn_src),y
        sta     (mn_dst),y
        dey
        bpl     :-
        lda     mn_dst
        clc
        adc     #48
        sta     mn_dst
        bcc     :+
        inc     mn_dst+1
:       lda     mn_src              ; $50 -> $D0 (same group), $D0 -> $50 (next)
        eor     #$80
        sta     mn_src
        bmi     :+
        lda     mn_src+1
        clc
        adc     #4
        sta     mn_src+1
:       dex
        bne     @chunk
        rts

; ----------------------------------------------------------------------------
; levels and lists (MENUSWAP)
; ----------------------------------------------------------------------------
.segment "MENUSWAP"
; to_prompt -- the typed line, empty.
to_prompt:
        lda     #0
        sta     mn_mode
; level1 -- the grid of verbs: the base verbs at their fixed cells (greyed
; when they cannot act here), then the contextual ones that can; the cursor
; on the last verb chosen, or on KILL when an animal has just arrived.
level1: lda     #1
        sta     mn_level
        lda     #0
        sta     linelen
        sta     menu_noun
        sta     mn_items
        sta     mn_top
        lda     #2
        sta     mn_hdr
        lda     #6
        sta     mn_cols
        sta     mn_wid
        lda     #<verb_table
        sta     mn_list
        lda     #>verb_table
        sta     mn_list+1
        jsr     build_verbs
        lda     #C_ANIMAL       ; an animal arrived: the cursor on KILL
        jsr     ctx_ok
        lda     #0
        rol     a
        cmp     mn_anim
        sta     mn_anim
        beq     :+
        bcc     :+
        lda     #E_KILL
        sta     mn_verb
:       ldx     mn_count        ; the cell of the last verb chosen
:       dex
        bmi     :+
        lda     mn_idx,x
        and     #$7F
        cmp     mn_verb
        bne     :-
        txa
        .byte   $2C             ; BIT abs: skips the LDA
:       lda     #0
        sta     mn_cur
; scroll_to_cur -- the three visible rows include the selected cell.
scroll_to_cur:
        lda     mn_cur
        ldx     #0
:       cmp     mn_cols
        bcc     :+
        sbc     mn_cols
        inx
        bne     :-
:       cpx     mn_top          ; X = row of the selection
        bcs     :+
        stx     mn_top
        rts
:       txa
        sec
        sbc     #MN_ROWS-1
        bcc     :+
        cmp     mn_top
        bcc     :+
        sta     mn_top
:       rts

; verb_of_cur -- mn_verb = the verb_table entry of the selected cell.
verb_of_cur:
        ldx     mn_cur
        lda     mn_idx,x
        and     #$7F
        sta     mn_verb
        rts

; items_any -- A = filter: C set when one item at least qualifies.
items_any:
        sta     mn_t
        tay
        ldx     filt_lo,y
@item:  ldy     mn_t
        txa
        cmp     filt_hi,y
        bcs     @none
        jsr     item_ok
        bcs     @rts
        inx
        bne     @item
@none:  clc
@rts:   rts

; item_ok -- C set when the verb of filter mn_t (F_GET .. F_DRINK) may name
; item X: accessible (member), in a group the verb does not target. EAT:
; the provisions, the oral remedies (FLAGYL, SALT TAB, QUININE) and the
; piles of food; GET: not the backpack or canteen already in hand. Preserves X.
item_ok:
        ldy     mn_t
        cpy     #F_USE
        bne     :+
        jsr     use_item_ok     ; lot 2: the items USE handles
        bcc     @no
:       cpy     #F_EAT
        bne     @test
        cpx     #38
        bcc     @test
        cpx     #76
        bcs     @test
        cpx     #47
        beq     @test
        cpx     #48
        beq     @test
        cpx     #50
        bne     @no
@test:  jsr     member
        ldy     mn_t
        bne     @mask
        cpx     #21             ; GET: the backpack and the canteen in hand
        beq     :+              ; are carried already
        cpx     #64
        bne     @mask
:       and     #<~G_HAND
@mask:  sta     mn_n
        lda     filt_ex,y
        eor     #$FF
        and     mn_n
        beq     @no
        sec
        rts
@no:    clc
        rts

; member -- A = the groups item X belongs to (G_*) when it is accessible
; here, else 0. Provisions: their pack stock (with the pack hung here), their
; ground stock on this cell. Gear: its placement, the ground and the hung
; pack on this cell only. The piles of lot 4 (76..86, HIDE 94): their pack
; and ground stocks (the ground piles are this cell's: forage_here).
; Preserves X.
member: cpx     #76
        bcs     @pile
        lda     it_place,x
        cmp     #$FF
        beq     @none
        cpx     #N_WATER
        bcc     @gear
        cpx     #38
        bcs     @gear
        lda     #0
        sta     mn_n
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        beq     @ground
        lda     #G_PACK
        ldy     it_place,x
        cpy     #5
        bne     :+
        jsr     hung_here
        bcc     @ground
        lda     #G_HUNG
:       sta     mn_n
@ground:
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @prov
        jsr     at_ground
        bcc     @prov
@both:  lda     mn_n
        ora     #G_GROUND
        sta     mn_n
@prov:  lda     mn_n
        rts
@gear:  tay
        cpy     #6
        bcs     @none
        lda     place_mask,y
        cmp     #G_GROUND
        beq     @here
        cmp     #G_HUNG
        bne     @rts
        jsr     hung_here
        bcs     @rts
@none:  lda     #0
@rts:   rts
@here:  jsr     at_ground
        bcs     @rts
        bcc     @none
@pile:  lda     #FG_HIDE
        cpx     #94
        beq     :+
        cpx     #87
        bcs     @second
        txa                     ; (C clear) X - 76
        sbc     #76-1
:       tay
        lda     #0
        sta     mn_n
        lda     fg_pl,y
        ora     fg_ph,y
        beq     :+
        lda     #G_PACK
        sta     mn_n
:       lda     fg_gl,y
        ora     fg_gh,y
        bne     @both
        beq     @prov
; lot 3: BOW, SPEAR, CLUB, ROCK, SPLINT (89..93, src/craft.s cr_b1), for the
; grid's greyed verbs a superset (the lists are exact: src/grid.s gr_ok):
; their place, the ground of any cell; the ROCK absent, on the land cell
; reached since (cr_rock_land).
@second:
        txa                     ; (C set)
        sbc     #89
        bcc     @none           ; 87, 88
        tay
        lda     cr_b1,y
        bpl     @placed
        cpy     #3
        bne     @none
        jmp     cr_rock_land
@placed:
        tay
        lda     place_mask,y
        rts
; hung_here -- C set when the backpack hangs on this cell.
hung_here:
        lda     px+1
        cmp     it_x+21
        bne     @no
        lda     py+1
        cmp     it_y+21
        bne     @no
        sec
        rts
@no:    clc
        rts
place_mask: .byte G_GROUND, G_WORN, G_PACK, G_HAND, G_PACK, G_HUNG

; build_verbs -- mn_idx = the cells of the grid: the entries of verb_table
; that apply here, and the base ones that do not with bit 7 (greyed); mn_c
; counts the entries.
build_verbs:
        jsr     forage_here     ; the piles of another cell are lost
        jsr     water_bits      ; (cached: no probe below)
        lda     #0
        sta     mn_count
        sta     mn_c
        lda     #<verb_table
        sta     gp2
        lda     #>verb_table
        sta     gp2+1
@loop:  ldy     #0
        lda     (gp2),y
        cmp     #$FF
        beq     @done
        iny
        lda     (gp2),y
        and     #3
        jsr     ctx_ok
        bcc     @no
        ldy     #1              ; the place's condition: a fire here,
        lda     (gp2),y         ; else verb_extra (resident)
        and     #$E0
        cmp     #X_FIRE
        bne     :+
        lda     fire_on
        beq     @no
        bne     @kind
:       jsr     verb_extra
        bcc     @no
@kind:  ldy     #0              ; the kind's condition (items, care...)
        lda     (gp2),y
        and     #$7F
        jsr     kind_ok
        lda     mn_c
        bcs     @add
@no:    ldy     #0              ; a base verb stays, greyed
        lda     (gp2),y
        bpl     @skip
        lda     mn_c
        ora     #$80
@add:   ldy     mn_count
        sta     mn_idx,y
        inc     mn_count
@skip:  jsr     skip_entry
        inc     mn_c
        jmp     @loop
@done:  rts

; kind_ok -- A = kind: C set when the verb can act here. Items: one to name
; (a source of water for DRINK, and for GET with the canteen); CARE: a
; condition active; BOIL: a fire or the stove in use, UTENSILS, water; MAKE:
; a fire or water (mk_fire, mk_water). Keeps gp2.
kind_ok:
        tax
        lda     gp2
        pha
        lda     gp2+1
        pha
        txa
        jsr     @test
        pla
        sta     gp2+1
        pla
        sta     gp2
        rts
@test:  cmp     #K_ITEMS
        bcs     @items
        cmp     #K_CARE
        beq     @care
        cmp     #K_BOIL
        beq     @boil
        cmp     #K_MAKE
        bne     @yes
        jsr     mk_fire
        bcs     @rts
        jmp     mk_water
@items: sbc     #K_ITEMS
        cmp     #F_KILL         ; lot 4's: forage_menu decided
        bcs     @yes
        pha
        jsr     items_any
        pla
        bcs     @rts
        cmp     #F_DRINK
        beq     :+
        cmp     #F_GET
        bne     @no
        ldx     #64             ; GET of a source: into the canteen
        jsr     have
        bcc     @rts
:       jmp     grid_water
@rts:   rts
@care:  ldx     #12
:       lda     injury_active,x
        bne     @yes
        dex
        bpl     :-
@no:    clc
        rts
@boil:  lda     fire_on
        bne     :+
        lda     camp_use
        and     #U_STOVE
        beq     @no
:       ldx     #73             ; UTENSILS (USE UTENSILS goes first)
        jsr     have
        bcc     @rts
        ldx     #N_WATER        ; the canteen, or the pile here
        jmp     have
@yes:   sec
        rts

; ctx_ok -- C set when context A (0..3) applies now (summary_hint's tests).
ctx_ok: beq     @yes
        cmp     #2
        beq     @inside
        bcs     @animal
        lda     shelter_inside  ; 1: the cabin cell, outside
        bne     @no
        lda     MAP+16
        beq     @no
        lda     px+1
        cmp     MAP+17
        bne     @no
        lda     py+1
        cmp     MAP+18
        bne     @no
@yes:   sec
        rts
@inside:
        lda     shelter_inside
        bne     @yes
@no:    clc
        rts
@animal:
        lda     animal_kind
        beq     @no
        lda     animal_x
        cmp     px+1
        bne     @no
        lda     animal_y
        cmp     py+1
        bne     @no
        beq     @yes

; text_of -- A = visible index: gp2 = its label (an item name, or the
; string of the entry after mn_hdr bytes).
text_of:
        tay
        lda     mn_items
        beq     @walk
        ldx     overlay_text,y
        jmp     grid_item_name  ; (src/grid.s: a list is open, GRID is here)
@walk:  lda     mn_level
        cmp     #1
        bne     :+
        lda     mn_idx,y        ; the grid: entry number
        and     #$7F
        tay
:       sty     mn_n
        lda     mn_list
        sta     gp2
        lda     mn_list+1
        sta     gp2+1
@loop:  lda     mn_n
        beq     @hdr
        jsr     skip_entry
        dec     mn_n
        bne     @loop
@hdr:   lda     gp2
        clc
        adc     mn_hdr
        sta     gp2
        bcc     :+
        inc     gp2+1
:       rts

; skip_entry -- gp2 = the next entry: mn_hdr bytes, the label, its suffix.
skip_entry:
        lda     mn_hdr
        beq     skip_str
        ldy     #1
        lda     (gp2),y
        and     #C_SUFFIX
        sta     mn_t
        lda     gp2
        clc
        adc     #2
        sta     gp2
        bcc     :+
        inc     gp2+1
:       jsr     skip_str
        lda     mn_t
        beq     skip_rts
; skip_str -- gp2 = after the 0-terminated string at gp2.
skip_str:
        ldy     #0
:       lda     (gp2),y
        beq     skip_done
        iny
        bne     :-
skip_rts:
        rts

; append_str -- the string at gp2 to inbuf (at most MAXLINE); gp2 after it.
append_str:
        ldy     #0
@loop:  lda     (gp2),y
        beq     @end
        ldx     linelen
        cpx     #MAXLINE
        bcs     :+
        sta     inbuf,x
        inc     linelen
:       iny
        bne     @loop
@end:   ldx     linelen
        lda     #0
        sta     inbuf,x
skip_done:
        iny
        tya
        clc
        adc     gp2
        sta     gp2
        bcc     :+
        inc     gp2+1
:       rts

; mk_fire -- C set when MAKE FIRE can succeed here (camp.s make_fire, the
; grid lighting a match first): no fire yet, not in water nor on snowy
; rocks, MATCHES with a use left; in rain or a wind of 41 mph and more,
; FUEL with an ounce left, or the shelter.
mk_fire:
        lda     fire_on
        bne     mk_no
        jsr     water_bits
        and     #2
        bne     mk_no
        jsr     woods_here      ; rocky (bare, level 96 and more) and snowy
        bcs     :+
        jsr     level_here
        cmp     #96
        bcc     :+
        cmp     M_SNOW
        bcs     mk_no
:       ldx     #38
        jsr     mk_stock
        bcc     mk_rts
        jsr     camp_storm
        bcc     mk_yes
        lda     shelter_inside
        bne     mk_yes
        ldx     #40
        jmp     mk_stock
mk_yes: sec
mk_rts: rts
mk_no:  clc
        rts
; ----------------------------------------------------------------------------
; drawing (t_update: one store per changed cell, both pages)
; ----------------------------------------------------------------------------
redraw: jsr     draw_grid
        jmp     draw_line

; draw_grid -- rows 20-23, columns 41-78: the separator, the visible cells.
draw_grid:
        lda     #0
        sta     mn_row
@row:   lda     #MN_BOTTOM+1-MN_ROWS
        clc
        adc     mn_row
        jsr     t_bascalc
        lda     mn_top
        clc
        adc     mn_row
        tax
        lda     #0
        beq     @times
:       clc
        adc     mn_cols
        dex
@times: cpx     #0
        bne     :-
        sta     mn_i            ; first index of the row
        lda     #MN_GRID
        sta     mn_col
        lda     mn_cols
        sta     mn_c
@cell:  lda     #0
        sta     mn_inv
        ldy     mn_i
        cpy     mn_count
        bcs     @blank
        lda     mn_level        ; a greyed verb: bit 6 (lower case)
        cmp     #1
        bne     :+
        lda     mn_idx,y
        and     #$80
        lsr     a
        sta     mn_inv
:       tya
        jsr     text_of
        lda     mn_mode
        cmp     #1
        bne     @put
        lda     mn_i
        cmp     mn_cur
        bne     @put
        lda     mn_inv          ; the selection: bit 7 (inverse)
        ora     #$80
        sta     mn_inv
        bne     @put
@blank: jsr     empty_text
@put:   lda     mn_wid
        sta     mn_w
        jsr     cell_put
        inc     mn_i
        dec     mn_c
        bne     @cell
        lda     #MN_LAST
        sec
        sbc     mn_col
        beq     @sep
        bcc     @sep
        sta     mn_w
        jsr     empty_text
        jsr     cell_put
@sep:   XL_IMM  XI_SWAP, MT_LBAR, @x50  ; (XL, docs/MENUS.md 9: MouseText, a
        lda     #'|'|$80        ; bar and arrows) the separator shows the
        ldx     mn_row          ; rows out of view
        bne     :+
        ldy     mn_top
        beq     @mark
        XL_IMM  XI_SWAP, MT_UP, @x51
        lda     #'^'|$80
        bne     @mark
:       cpx     #MN_ROWS-1
        bne     @mark
        ldy     mn_i            ; first index of the next row
        cpy     mn_count
        bcs     @mark
        XL_IMM  XI_SWAP, MT_DOWN, @x52
        lda     #'V'|$80
@mark:  ldy     #MN_SEP
        jsr     t_update
        lda     #' '|$80
        ldy     #MN_SEP+1
        jsr     t_update
        inc     mn_row
        lda     mn_row
        cmp     #MN_ROWS
        jne     @row
        rts
empty_text:
        lda     #<str_empty
        sta     gp2
        lda     #>str_empty
        sta     gp2+1
        rts

.segment "MENUCODE"
; draw_line -- the last row of the result column: "> " and the command
; (typed or composed, no cursor: the text is the cursor) while there is
; one, else the stock row.
draw_line:
        lda     #MN_BOTTOM
        jsr     t_bascalc
        lda     linelen
        bne     @command
        jsr     res_clear       ; an empty line: inbuf keeps the last command
        jmp     stock_row
@command:
        jsr     draw_arrow
        lda     #MN_RES+2
        sta     mn_col
        lda     #MN_END-MN_RES-2
        sta     mn_w
        lda     #0
        sta     mn_inv
        lda     #<inbuf
        sta     gp2
        lda     #>inbuf
        sta     gp2+1
        jmp     cell_put

; draw_arrow -- "> " at the start of the last row of the result column
; (BASL set to it).
draw_arrow:
        lda     #'>'|$80
        ldy     #MN_RES
        jsr     t_update
        lda     #' '|$80
        ldy     #MN_RES+1
        jmp     t_update

; res_clear -- the result column of row BASL in spaces (the grid stays).
; Preserves X.
res_clear:
        lda     #MN_END
        sta     pad_limit
        ldy     #MN_RES
        jmp     clear_to

; cell_put -- the string at gp2 from column mn_col, padded with spaces to
; mn_w cells (one space at least after a longer label: cells are
; proportional, a row of six fits in 38 columns for every run of six
; verbs; a list row may run one cell long, clipped before column 79), in
; inverse when mn_inv is set. mn_col ends after the cell.
cell_put:
        ldy     #0
        sty     mn_k
@char:  ldy     mn_k
        lda     (gp2),y
        beq     @pad
        jsr     cell_char
        inc     mn_k
        bne     @char
@pad:   lda     mn_w
        sec
        sbc     mn_k
        bcc     @one
        beq     @one
        tax
        bne     @spaces
@one:   ldx     #1
@spaces:
        lda     #' '
        XL_ABS  XI_MENU, page_foot, @x53        ; (XL: xl_pad, below)
        jsr     cell_char
        dex
        bne     @spaces
        rts
cell_char:
        ora     #$80
        bit     mn_inv
        bvc     @case           ; a greyed verb: its letters in lower case,
        cmp     #'A'|$80        ; never inverse (the primary character set
        bcc     @case           ; has no inverse lower case): selected, its
        ora     #$20            ; spaces alone are
        bne     @put
@case:  bit     mn_inv
        bpl     @put
        and     #$3F
@put:   ldy     mn_col
        cpy     #MN_LAST
        bcs     :+
        jsr     t_update
:       inc     mn_col
        rts

; ----------------------------------------------------------------------------
; the result column (message, game.s): resident with the game, since a
; command prints while the swap image is away
; ----------------------------------------------------------------------------
.segment "GCODE"
; msg_begin -- clear the result column, cursor at its first cell.
msg_begin:
        ldx     #MN_BOTTOM+1-MN_ROWS
@row:   txa
        jsr     t_bascalc
        jsr     res_clear
        inx
        cpx     #MN_BOTTOM+1
        bcc     @row
        lda     #MN_BOTTOM+1-MN_ROWS
        sta     CV
        jsr     t_vtab
        lda     #MN_RES
        sta     CH
        lda     #0
        sta     msg_wlen
        rts

; msg_char -- A = character (bit 7 set) of the result: words are buffered
; and placed whole (msg_flush). Preserves X and Y.
msg_char:
        stx     msg_x
        sty     msg_y
        cmp     #' '|$80
        beq     @space
        ldy     msg_wlen
        cpy     #MN_END-MN_RES
        bcs     @done
        sta     msg_word,y
        inc     msg_wlen
        bne     @done
@space: jsr     msg_flush
        lda     CH
        cmp     #MN_RES         ; no space at the start of a row
        beq     @done
        cmp     #MN_END
        bcs     @done
        lda     #' '|$80
        jsr     COUT
@done:  ldx     msg_x
        ldy     msg_y
        rts

; msg_flush -- the buffered word at the cursor, on the next row when it
; does not fit (the last row keeps what fits). Preserves X and Y.
msg_flush:
        lda     msg_wlen
        bne     :+
        rts
:       sty     msg_y
        clc
        adc     CH
        cmp     #MN_END+1
        bcc     @print
        lda     CV
        cmp     #MN_BOTTOM
        bcs     @print
        jsr     msg_row
@print: ldy     #0
@ch:    lda     CH
        cmp     #MN_END
        bcs     @end
        lda     msg_word,y
        jsr     COUT
        iny
        cpy     msg_wlen
        bcc     @ch
@end:   lda     #0
        sta     msg_wlen
        ldy     msg_y
        rts
msg_row:
        inc     CV
        jsr     t_vtab
        lda     #MN_RES
        sta     CH
        rts
; msg_newline -- "|" of a message: a new row while one is left, else a space.
msg_newline:
        jsr     msg_flush
        lda     CV
        cmp     #MN_BOTTOM
        bcc     msg_row
        lda     #' '|$80
        jmp     msg_char

; stock_row -- the last row of the result column, when the result left it blank:
; the food and water carried (pack, canteen), then those on this cell, in
; ounces: "FOOD 192 WATER 64 HERE 248/0 OZ" (39 columns with four digits
; everywhere).
.segment "MENUSWAP"
stock_row:
        lda     #MN_BOTTOM
        jsr     t_bascalc
        ldy     #MN_RES/2
        sta     PAGE2_AUX       ; column 0: even, auxiliary page
        lda     (BASL),y
        sta     PAGE2_MAIN
        cmp     #' '|$80
        beq     :+
        rts
:       lda     #MN_BOTTOM
        sta     CV
        jsr     t_vtab
        lda     #MN_RES
        sta     CH
        jsr     puts
        .byte   "FOOD ",0
        ldx     #23
        jsr     sum_pack
        jsr     puts
        .byte   " WATER ",0
        ldx     #N_WATER
        jsr     sum_pack
        jsr     puts
        .byte   " HERE ",0
        ldx     #23
        jsr     sum_ground
        jsr     puts
        .byte   "/",0
        ldx     #N_WATER
        jsr     sum_ground
        jsr     puts
        .byte   " OZ",0
        rts
; sum_ground -- X = first item: the ground ounces here of the provisions X..
sum_ground:
        lda     #$80
        bne     sum_items
; sum_pack -- X = first item: the pack ounces of the provisions X.. (water
; alone when X = N_WATER), hung or absent ones excluded.
sum_pack:
        lda     #0
sum_items:
        sta     mn_t
        lda     #0
        sta     num
        sta     num+1
        lda     #38
        sta     mn_n            ; last provision + 1
        cpx     #N_WATER
        bne     @item
        lda     #N_WATER+1
        sta     mn_n
        bne     @item
@next:  inx
        cpx     mn_n
        bcs     @print
@item:  lda     it_place,x
        cmp     #$FF
        beq     @next
        bit     mn_t
        bmi     @ground
        cmp     #5
        beq     @next
        clc
        lda     num
        adc     it_pack_lo,x
        sta     num
        lda     num+1
        adc     it_pack_hi,x
        sta     num+1
        jmp     @next
@ground:
        jsr     at_ground
        bcc     @next
        clc
        lda     num
        adc     it_gnd_lo,x
        sta     num
        lda     num+1
        adc     it_gnd_hi,x
        sta     num+1
        jmp     @next
@print: lda     CH              ; five digits at most: never past column 38
        cmp     #MN_END-5
        bcs     @rts
        jmp     print_u16
@rts:   rts

; ----------------------------------------------------------------------------
; tables
; ----------------------------------------------------------------------------
.segment "MENUSWAP"
; verb_table -- kind, context, label, 0 [, suffix, 0]; $FF ends (docs/MENUS.md
; 4). The base verbs first, at fixed cells (row 20: WALK or SWIM, LOOK,
; REST, WAIT, EAT, DRINK; row 21: GET, WEAR, DROP, USE, MAKE), greyed when
; K_BASE and they cannot act here; then the contextual ones that can, by
; urgency: the animal, the fire, the care, the lot 4 and lot 2 work, the
; tree and the cabin. E_KILL is the animal's KILL (ATTACK).
verb_table:
        .byte   K_DUR, X_SWIM, "SWIM", 0
        .byte   K_DUR, X_WALK, "WALK", 0
        .byte   K_LOOK, 0, "LOOK", 0
        .byte   K_DUR, 0, "REST", 0
        .byte   K_DUR, 0, "WAIT", 0
        .byte   K_BASE|K_ITEMS+F_EAT, 0, "EAT", 0
        .byte   K_BASE|K_ITEMS+F_DRINK, 0, "DRINK", 0
        .byte   K_BASE|K_ITEMS+F_GET, 0, "GET", 0
        .byte   K_BASE|K_ITEMS+F_WEAR, 0, "WEAR", 0
        .byte   K_BASE|K_ITEMS+F_DROP, 0, "DROP", 0
        .byte   K_BASE|K_ITEMS+F_USE, 0, "USE", 0
        .byte   K_BASE|K_MAKE, 0, "MAKE", 0
        .byte   K_NONE, C_ANIMAL, "KILL", 0             ; E_KILL
        .byte   K_NONE, C_ANIMAL, "SCARE", 0
        .byte   K_NONE, C_ANIMAL, "IGNORE", 0
        .byte   K_NONE, X_FIRE|C_SUFFIX, "DOUSE", 0, " FIRE", 0
        .byte   K_CARE, 0, "CARE", 0
vt_cook:  .byte K_ITEMS+F_COOK, X_FORAGE, "COOK", 0
        .byte   K_BOIL, 0, "BOIL", 0
vt_skin:  .byte K_ITEMS+F_SKIN, X_FORAGE, "SKIN", 0
vt_catch: .byte K_ITEMS+F_CATCH, X_FORAGE, "CATCH", 0
vt_kill:  .byte K_ITEMS+F_KILL, X_FORAGE, "KILL", 0
        .byte   K_CLIMB, X_CLIMB, "CLIMB", 0
        .byte   K_NONE, X_HANG|C_SUFFIX, "HANG", 0, " FOOD", 0
        .byte   K_NONE, X_LOWER|C_SUFFIX, "LOWER", 0, " FOOD", 0
        .byte   K_NONE, C_SHELTER|C_SUFFIX, "ENTER", 0, " SHELTER", 0
        .byte   K_NONE, C_INSIDE|C_SUFFIX, "EXIT", 0, " SHELTER", 0
        .byte   $FF
str_empty:   .byte 0
str_status:  .byte "STATUS", 0
str_topo:    .byte "T", 0        ; fast_words: TOPO
.assert >str_topo = >str_status, error, "prompt_key: one high byte for both"
.segment "MENUCODE"
; Item filters F_GET .. F_DRINK (the grid's test, items_any): first item,
; last + 1, the groups the verb does not name (GET: not the pack's nor the
; worn; DRINK: the water alone). The piles of lot 4 (76..86, HIDE 94) are
; members too (member). Resident since the integration of lots 2, 7, 9 and 13.
filt_lo: .byte  1, 2, 1, 23, 38, N_WATER
filt_hi: .byte  95, 21, 95, 87, 94, N_WATER+1   ; USE: 38-73 (lot 2; lot 7's MAP...CHART within), 89-93 (lot 3)
filt_ex: .byte  G_PACK|G_WORN, 0, G_GROUND|G_HUNG, G_HUNG, 0, G_HUNG
; use_item_ok -- C set when USE handles item X: GND COVER, RAINCOAT,
; MATCHES, GLASS, FUEL, the medicine (41-51), FLASHLIGHT, STOVE, UTENSILS.
use_item_ok:
        txa
        lsr     a
        lsr     a
        lsr     a
        tay
        txa
        and     #7
        sty     mn_n
        tay
        lda     use_bit,y
        ldy     mn_n
        and     use_items,y
        ldy     mn_t            ; (item_ok's filter)
        cmp     #1              ; C set when the bit is
        rts
use_bit:    .byte 1,2,4,8,16,32,64,128
use_items:  .byte $00,$18,$00,$00,$C0,$FF,$0F,$00,$84,$02,$00,$3E ; 11,12,38-51,66,71,73, 89-93
; cr_rock_land -- (member) the ROCK absent: G_GROUND on a land cell once
; the player has left the settled cell (cr_still 0; water_bits, cached at
; the prompt: bit 1 water), else 0 (settled: in the water).
cr_rock_land:
        lda     cr_still
        asl     a
        ora     wb_bits
        and     #2
        eor     #2
        asl     a
        asl     a
        rts
; mk_stock -- C set when item X is here with a use (an ounce) left.
mk_stock:
        jsr     have
        bcc     mk_rts2
        lda     it_pack_lo,x
        ora     it_pack_hi,x
        cmp     #1
        rts
; mk_water -- C set when MAKE WATER can: a GND COVER or RAINCOAT here (its
; USE goes first), AM or PM under a clear sky (water_condense_ok without
; the sunset).
mk_water:
        ldx     #11
        jsr     have
        bcs     :+
        ldx     #12
        jsr     have
        bcc     mk_rts2
:       lda     weather_sky
        bne     mk_no2
        lda     period
        cmp     #2
        bcc     mk_rts2
        cmp     #4
        bcs     mk_no2
        sec
mk_rts2: rts
mk_no2: clc
        rts

; State: part of the image (zero at the start) rather than BSS, since the
; area held the loader's I/O buffer. Resident: the lists and messages of a
; command may run while the swap image is away.
mn_mode:  .byte 0               ; 0 typed line, 1 grid
mn_level: .byte 0               ; 1 verbs, 2 the list of the verb, 3 ounces
mn_cur:   .byte 0               ; selected cell
mn_verb:  .byte 0               ; the verb_table entry last chosen (the grid returns to it)
mn_top:   .byte 0               ; first visible row
mn_count: .byte 0
mn_cols:  .byte 0               ; cells per row
mn_wid:   .byte 0               ; cell width
mn_hdr:   .byte 0               ; bytes before a label (2: verb_table)
mn_items: .byte 0               ; the list names items (overlay_text)
mn_list:  .word 0
mn_kind:  .byte 0
mn_anim:  .byte 0               ; 1: an animal was here at the last grid
menu_noun: .byte 0              ; item chosen in a list (resolve_noun)
msg_wlen: .byte 0
msg_x:    .byte 0
msg_y:    .byte 0
mn_idx:   .res 27               ; the grid: entries of verb_table (bit 7: greyed), one at most each
msg_word: .res MN_END-MN_RES

.segment "RESCODE"
; grid_fetch -- the GRID module (src/grid.s) into the SIM window, below
; the grid's image: RETURN in the grid, a step of its queue. Counted as a module
; load, as load_totals_quiet does.
grid_fetch:
        ldx     #GRID_MODULE
        jsr     mem_fetch
        lda     #0
        sta     sim_loaded
        inc     overlay_reads
        bne     :+
        inc     overlay_reads+1
:       rts

; grid_water -- C set with water to drink or collect here: rain or snow
; falling, a river or lake (water_here on a legacy map; on a native one, in
; the water).
grid_water:
        lda     weather_sky
        cmp     #2
        bcs     @rts
        lda     MAP+37
        bne     :+
        jmp     water_here
:       jsr     water_bits
        and     #2
        cmp     #1
@rts:   rts

; The queue of the grid (src/grid.s, docs/MENUS.md 4): the steps a choice
; needs, typed one after the other by get_line. Not saved (a queue never
; outlives the choice that made it).
.segment "LOWPAGE"
mq_n:     .byte 0               ; steps (0: no queue)
mq_i:     .byte 0               ; the next one
mq_noun:  .byte 0               ; the item of a step that names one
mq_enc:   .byte 0               ; journey_encounters when it began
mq_list:  .res 5                ; the steps (grid.s S_*)
pg_open:  .byte 0               ; CARE: STATUS opens on MEDICAL, focused

.segment "MENUCODE"

