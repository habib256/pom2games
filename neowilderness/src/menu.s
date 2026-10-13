; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; menu.s -- the four 80-column rows as a command surface (lot 8, step 2;
; docs/MENUS.md section 4).
;
;   rows 20-22, columns 0-37   the grid of verbs (6 cells of 6), then the
;                              list of the open verb (durations, directions,
;                              items in 3 cells of 12, ounces); three rows
;                              visible, scrolled by row; the selected cell
;                              in inverse
;   column 38                  separator
;   rows 20-22, columns 40-78  the last result, wrapped by words (message),
;                              then, when the result leaves it free, the
;                              stock row: food and water carried and here
;   row 23                     "> " + the command as the parser will read
;                              it (typed or composed), then the key hints
;
; Two homes (docs/MEMORY.md section 11):
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
;
; get_line keeps its contract: inbuf / linelen hold a command when it
; returns; the menu composes the same text the keyboard would give. An item
; chosen in a list is also passed in menu_noun, since display names such
; as COTTN SOCKS are not vocabulary words (resolve_noun).
; Modes: 0 typed line (arrows turn, RETURN or UP opens the grid, DOWN shows
; STATUS); 1 grid (arrows move, RETURN selects, ESC backs up); 2 numeric
; prompt of the INPUT module (prompt). A command issued from the grid
; leaves the grid open for the next one.
; ============================================================================
.segment "MENUCODE"

MN_SEP   = 38                   ; separator column
MN_RIGHT = 40                   ; first column of the result column
MN_LAST  = 79                   ; reserved column (never written)
K_NONE   = 0                    ; verb kinds: the list the verb opens
K_DUR    = 1
K_LOOK   = 2
K_CLIMB  = 3
K_QTY    = 4
K_ITEMS  = 5                    ; + filter: 0 GET, 1 TAKE, 2 WEAR, 3 DROP, 4 EAT, 5 USE
C_SHELTER = 1                   ; context: shown only at the cabin cell, outside
C_INSIDE = 2                    ; inside the cabin
C_ANIMAL = 3                    ; an animal on the player's cell
C_SUFFIX = 4                    ; a second string completes the command
C_QTY_ITEM = 8                  ; ounces asked after the item (EAT)
C_QTY    = 16                   ; ounces asked after the verb (DRINK WATER)
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
get_line:
        jsr     menu_gather
        lda     mn_mode
        cmp     #1
        beq     :+
        lda     #0
        sta     mn_mode
:       jsr     level1
        jsr     stock_row
        jsr     redraw
idle:   lda     KBD             ; tests wait for this loop
        bpl     idle
        bit     KBDSTRB
        and     #$7F
        jsr     kbd_upcase
        ldx     mn_mode
        cpx     #1
        jeq     menu_key
prompt_key:
        cmp     #KC_RET
        beq     @ret
        cmp     #KC_UP
        beq     @open
        cmp     #KC_DOWN
        beq     @status
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
@turn:  jsr     turn_view
        jmp     idle
@clear: lda     #0
        sta     linelen
        sta     inbuf
        beq     @line
done_typed:
        lda     #0
        sta     mn_mode         ; the next prompt starts on the typed line
done:   ldx     linelen
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
        beq     select
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
        jcc     idle
        sta     mn_cur
        jmp     @moved
@down:  lda     mn_cur
        clc
        adc     mn_cols
        cmp     mn_count
        jcs     idle
        sta     mn_cur
@moved: jsr     scroll_to_cur
        jsr     draw_grid
        jmp     idle
@back:  lda     mn_level
        cmp     #1
        beq     @close
        jsr     level1          ; a list: back to the verbs
        jmp     @show
@close: jsr     to_prompt
@show:  jsr     redraw
        jmp     idle

; select -- RETURN on the selected cell: the verb opens its list or runs,
; the list entry completes the command (and may ask the ounces).
select: lda     mn_level
        cmp     #1
        beq     @verb
        jsr     append_space
        lda     mn_cur
        jsr     text_of
        jsr     append_str
        lda     mn_level
        cmp     #3
        jeq     done_menu
        lda     mn_items
        jeq     done_menu
        ldy     mn_cur
        lda     overlay_text,y
        sta     menu_noun
        lda     mn_ctx
        and     #C_QTY_ITEM
        jeq     done_menu
        lda     menu_noun
        cmp     #38             ; provisions only: a dose is one item
        jcs     done_menu
@ounces:
        lda     #K_QTY
        jsr     open_list
        lda     #3
        sta     mn_level
        jmp     @show
@verb:  lda     mn_cur
        sta     mn_verb
        jsr     text_of         ; gp2 = label; its kind and context before it
        sec
        lda     gp2
        sbc     #2
        sta     gp2
        bcs     :+
        dec     gp2+1
:       ldy     #0
        lda     (gp2),y
        sta     mn_kind
        iny
        lda     (gp2),y
        sta     mn_ctx
        iny
        tya
        clc
        adc     gp2
        sta     gp2
        bcc     :+
        inc     gp2+1
:       jsr     append_str      ; gp2 then points to the suffix, if any
        lda     mn_ctx
        and     #C_SUFFIX
        beq     :+
        jsr     append_str
:       lda     mn_ctx
        and     #C_QTY
        bne     @ounces
        lda     mn_kind
        jeq     done_menu
        jsr     open_list
        lda     #2
        sta     mn_level
@show:  jsr     redraw
        jmp     idle

; prompt -- the numeric prompt of the INPUT module: "> " on row 23, the
; cursor after it (the module echoes the digits), its own hint.
prompt: lda     #0
        sta     linelen
        sta     inbuf
        lda     #2
        sta     mn_mode
        jsr     draw_line
        lda     #23
        sta     CV
        jsr     t_vtab
        lda     #2
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
; level1 -- the grid of verbs that apply here; the selection is kept.
level1: lda     #1
        sta     mn_level
        lda     #0
        sta     linelen
        sta     inbuf
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
        lda     mn_verb         ; back on the last verb chosen
        cmp     mn_count
        bcc     :+
        lda     #0
:       sta     mn_cur
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
        sbc     #2
        bcc     :+
        cmp     mn_top
        bcc     :+
        sta     mn_top
:       rts

; open_list -- A = kind: the list of the open verb, from its first cell.
open_list:
        sta     mn_t
        lda     #0
        sta     mn_cur
        sta     mn_top
        sta     mn_hdr
        sta     mn_items
        lda     #6
        sta     mn_cols
        sta     mn_wid
        lda     mn_t
        cmp     #K_ITEMS
        bcs     build_items
        tax
        lda     list_lo-1,x
        sta     mn_list
        sta     gp2
        lda     list_hi-1,x
        sta     mn_list+1
        sta     gp2+1
        lda     #0
        sta     mn_count
@count: ldy     #0
        lda     (gp2),y
        beq     @done
        jsr     skip_str
        inc     mn_count
        bne     @count
@done:  rts

; build_items -- the items the verb may name (mn_t = filter): present in a
; group the verb does not already target, in overlay_text.
build_items:
        sec
        sbc     #K_ITEMS
        sta     mn_t
        inc     mn_items
        lda     #3
        sta     mn_cols
        lda     #12
        sta     mn_wid
        lda     #0
        sta     mn_count
        ldy     mn_t
        ldx     filt_lo,y
@item:  ldy     mn_t
        txa
        cmp     filt_hi,y
        bcs     @done
        cpy     #4              ; EAT: provisions and medicine, not the gear
        bne     @test           ; between them nor the sunglasses
        cpx     #43
        beq     @next
        cpx     #38
        bcc     @test
        cpx     #41
        bcc     @next
@test:  jsr     member
        ldy     mn_t
        sta     mn_n
        lda     filt_ex,y
        eor     #$FF
        and     mn_n
        beq     @next
        ldy     mn_count
        txa
        sta     overlay_text,y
        inc     mn_count
@next:  inx
        bne     @item
@done:  rts

; member -- A = the groups item X belongs to (G_*), 0 when absent.
; Provisions: their pack stock (hung with the pack) and their ground stock,
; wherever it lies (the handler names the cell). Gear: its placement.
; Preserves X.
member: lda     it_place,x
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
        lda     #G_HUNG
:       sta     mn_n
@ground:
        lda     it_gnd_lo,x
        ora     it_gnd_hi,x
        beq     @prov
        lda     mn_n
        ora     #G_GROUND
        sta     mn_n
@prov:  lda     mn_n
        rts
@gear:  tay
        cpy     #6
        bcs     @none
        lda     place_mask,y
        rts
@none:  lda     #0
        rts
place_mask: .byte G_GROUND, G_WORN, G_PACK, G_HAND, G_PACK, G_HUNG

; build_verbs -- mn_idx = the entries of verb_table whose context applies.
build_verbs:
        lda     #0
        sta     mn_count
        sta     mn_n
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
        bcc     @skip
        ldy     mn_count
        lda     mn_n
        sta     mn_idx,y
        inc     mn_count
@skip:  jsr     skip_entry
        inc     mn_n
        jmp     @loop
@done:  rts

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
        lda     it_name_lo,x
        sta     gp2
        lda     it_name_hi,x
        sta     gp2+1
        rts
@walk:  lda     mn_level
        cmp     #1
        bne     :+
        lda     mn_idx,y        ; the grid: entry number
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
append_space:
        lda     #' '
        ldx     linelen
        cpx     #MAXLINE
        bcs     :+
        sta     inbuf,x
        inc     linelen
:       rts

; ----------------------------------------------------------------------------
; drawing (t_update: one store per changed cell, both pages)
; ----------------------------------------------------------------------------
redraw: jsr     draw_grid
        jmp     draw_line

; draw_grid -- rows 20-22, columns 0-37: the visible cells, the separator.
draw_grid:
        lda     #0
        sta     mn_row
@row:   lda     #20
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
        lda     #0
        sta     mn_col
        lda     mn_cols
        sta     mn_c
@cell:  lda     #0
        sta     mn_inv
        lda     mn_i
        cmp     mn_count
        bcs     @blank
        jsr     text_of
        lda     mn_mode
        cmp     #1
        bne     @put
        lda     mn_i
        cmp     mn_cur
        bne     @put
        dec     mn_inv
        bne     @put
@blank: jsr     empty_text
@put:   lda     mn_wid
        sta     mn_w
        jsr     cell_put
        inc     mn_i
        dec     mn_c
        bne     @cell
        lda     #MN_SEP
        sec
        sbc     mn_col
        beq     @sep
        bcc     @sep
        sta     mn_w
        jsr     empty_text
        jsr     cell_put
@sep:   lda     #'|'|$80        ; the separator shows the rows out of view
        ldx     mn_row
        bne     :+
        ldy     mn_top
        beq     @mark
        lda     #'^'|$80
        bne     @mark
:       cpx     #2
        bne     @mark
        ldy     mn_i            ; first index of the next row
        cpy     mn_count
        bcs     @mark
        lda     #'V'|$80
@mark:  ldy     #MN_SEP
        jsr     t_update
        lda     #' '|$80
        ldy     #MN_SEP+1
        jsr     t_update
        inc     mn_row
        lda     mn_row
        cmp     #3
        jne     @row
        rts
empty_text:
        lda     #<str_empty
        sta     gp2
        lda     #>str_empty
        sta     gp2+1
        rts

.segment "MENUCODE"
; draw_line -- row 23: "> ", the command (no cursor: the text is the cursor), the hint.
draw_line:
        lda     #23
        jsr     t_bascalc
        lda     #'>'|$80
        ldy     #0
        jsr     t_update
        lda     #' '|$80
        ldy     #1
        jsr     t_update
        lda     #2
        sta     mn_col
        lda     #MAXLINE
        sta     mn_w
        lda     #0
        sta     mn_inv
        lda     #<inbuf
        sta     gp2
        lda     #>inbuf
        sta     gp2+1
        jsr     cell_put
        ldx     mn_mode
        lda     hint_lo,x
        sta     gp2
        lda     hint_hi,x
        sta     gp2+1
        lda     #MN_RIGHT
        sta     mn_col
        lda     #MN_LAST-MN_RIGHT
        sta     mn_w
        jmp     cell_put

; cell_put -- the string at gp2 from column mn_col, padded with spaces to
; mn_w cells (one space at least after a longer label: cells are
; proportional, a row of six fits in 38 columns for every run of six
; verbs), in inverse when mn_inv is set. mn_col ends after the cell.
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
        jsr     cell_char
        dex
        bne     @spaces
        rts
cell_char:
        ora     #$80
        bit     mn_inv
        bpl     :+
        and     #$3F
:       ldy     mn_col
        jsr     t_update
        inc     mn_col
        rts

; ----------------------------------------------------------------------------
; the result column (message, game.s): resident with the game, since a
; command prints while the swap image is away
; ----------------------------------------------------------------------------
.segment "GCODE"
; msg_begin -- clear the result column, cursor at its first cell.
msg_begin:
        ldx     #20
@row:   txa
        jsr     t_bascalc
        ldy     #MN_RIGHT
        jsr     t_clreol_y
        inx
        cpx     #23
        bcc     @row
        lda     #20
        sta     CV
        jsr     t_vtab
        lda     #MN_RIGHT
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
        cpy     #MN_LAST-MN_RIGHT
        bcs     @done
        sta     msg_word,y
        inc     msg_wlen
        bne     @done
@space: jsr     msg_flush
        lda     CH
        cmp     #MN_RIGHT       ; no space at the start of a row
        beq     @done
        cmp     #MN_LAST
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
        cmp     #MN_LAST+1
        bcc     @print
        lda     CV
        cmp     #22
        bcs     @print
        jsr     msg_row
@print: ldy     #0
@ch:    lda     CH
        cmp     #MN_LAST
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
        lda     #MN_RIGHT
        sta     CH
        rts
; msg_newline -- "|" of a message: a new row while one is left, else a space.
msg_newline:
        jsr     msg_flush
        lda     CV
        cmp     #22
        bcc     msg_row
        lda     #' '|$80
        jmp     msg_char

; stock_row -- row 22 of the result column, when the result left it blank:
; the food and water carried (pack, canteen), then those on this cell.
.segment "MENUSWAP"
stock_row:
        lda     #22
        jsr     t_bascalc
        ldy     #MN_RIGHT/2
        sta     PAGE2_AUX       ; column 40: even, auxiliary page
        lda     (BASL),y
        sta     PAGE2_MAIN
        cmp     #' '|$80
        beq     :+
        rts
:       lda     #22
        sta     CV
        jsr     t_vtab
        lda     #MN_RIGHT
        sta     CH
        jsr     puts
        .byte   "FOOD ",0
        ldx     #23
        jsr     sum_pack
        jsr     puts
        .byte   " OZ  WATER ",0
        ldx     #N_WATER
        jsr     sum_pack
        jsr     puts
        .byte   " OZ  HERE ",0
        ldx     #23
        jsr     sum_ground
        jsr     puts
        .byte   "/",0
        ldx     #N_WATER
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
@print: jmp     print_u16

; ----------------------------------------------------------------------------
; tables
; ----------------------------------------------------------------------------
.segment "MENUSWAP"
; verb_table -- kind, context, label, 0 [, suffix, 0]; $FF ends. Contextual
; verbs come first, as in the survival band.
verb_table:
        .byte   K_NONE, C_INSIDE|C_SUFFIX, "EXIT", 0, " SHELTER", 0
        .byte   K_NONE, C_SHELTER|C_SUFFIX, "ENTER", 0, " SHELTER", 0
        .byte   K_NONE, C_ANIMAL, "IGNORE", 0
        .byte   K_NONE, C_ANIMAL, "SCARE", 0
        .byte   K_NONE, C_ANIMAL, "ATTACK", 0
        .byte   K_DUR, 0, "WALK", 0
        .byte   K_DUR, 0, "SWIM", 0
        .byte   K_LOOK, 0, "LOOK", 0
        .byte   K_DUR, 0, "REST", 0
        .byte   K_DUR, 0, "WAIT", 0
        .byte   K_ITEMS+4, C_QTY_ITEM, "EAT", 0
        .byte   K_NONE, C_SUFFIX|C_QTY, "DRINK", 0, " WATER", 0
        .byte   K_ITEMS+0, 0, "GET", 0
        .byte   K_ITEMS+1, 0, "TAKE", 0
        .byte   K_ITEMS+2, 0, "WEAR", 0
        .byte   K_ITEMS+3, 0, "DROP", 0
        .byte   K_ITEMS+5, 0, "USE", 0
        .byte   K_CLIMB, 0, "CLIMB", 0
        .byte   K_NONE, C_SUFFIX, "HANG", 0, " FOOD", 0
        .byte   K_NONE, C_SUFFIX, "LOWER", 0, " FOOD", 0
        .byte   K_NONE, 0, "STATUS", 0
        .byte   K_NONE, C_SUFFIX, "INVENT", 0, "ORY", 0
        .byte   K_NONE, 0, "TOPO", 0
        .byte   K_NONE, 0, "MAP", 0
        .byte   K_NONE, 0, "HELP", 0
        .byte   K_NONE, 0, "QUIT", 0
        .byte   $FF
list_lo: .byte  <list_dur, <list_look, <list_climb, <list_qty
list_hi: .byte  >list_dur, >list_look, >list_climb, >list_qty
list_dur:   .byte "10 MIN",0,"20 MIN",0,"30 MIN",0,"1 H",0,"2 H",0,"4 H",0,"8 H",0,0
list_look:  .byte "LEFT",0,"RIGHT",0,"BACK",0,"AHEAD",0,"NORTH",0,"EAST",0,"SOUTH",0,"WEST",0,0
list_climb: .byte "TREE",0,"DOWN",0,0
list_qty:   .byte "2 OZ",0,"4 OZ",0,"8 OZ",0,"12 OZ",0,"16 OZ",0,"24 OZ",0,"32 OZ",0,"48 OZ",0,0
; Item filters: first item, last + 1, the groups the verb already targets.
filt_lo: .byte  1, 1, 1, 1, 23, 41
filt_hi: .byte  76, 76, 21, 76, 52, 52
filt_ex: .byte  G_PACK, G_HAND, G_WORN, G_GROUND|G_HUNG, G_HUNG, 0
str_empty:   .byte 0
.segment "RESCODE"
hint_lo: .byte  <hint_typed, <hint_grid, <hint_number
hint_hi: .byte  >hint_typed, >hint_grid, >hint_number
hint_typed:  .byte "RET: MENU  <>: TURN  OR TYPE A COMMAND",0
hint_grid:   .byte "ARROWS: MOVE  RET: SELECT  ESC: BACK",0
hint_number: .byte "NUMBER THEN RET   ESC: CANCEL",0
str_status:  .byte "STATUS", 0
.segment "MENUCODE"

; State: part of the image (zero at the start) rather than BSS, since the
; area held the loader's I/O buffer. Resident: the lists and messages of a
; command may run while the swap image is away.
mn_mode:  .byte 0               ; 0 typed line, 1 grid, 2 numeric prompt
mn_level: .byte 0               ; 1 verbs, 2 the list of the verb, 3 ounces
mn_cur:   .byte 0               ; selected cell
mn_verb:  .byte 0               ; the verb last chosen (the grid returns to it)
mn_top:   .byte 0               ; first visible row
mn_count: .byte 0
mn_cols:  .byte 0               ; cells per row
mn_wid:   .byte 0               ; cell width
mn_hdr:   .byte 0               ; bytes before a label (2: verb_table)
mn_items: .byte 0               ; the list names items (overlay_text)
mn_list:  .word 0
mn_kind:  .byte 0
mn_ctx:   .byte 0
menu_noun: .byte 0              ; item chosen in a list (resolve_noun)
msg_wlen: .byte 0
msg_x:    .byte 0
msg_y:    .byte 0
mn_idx:   .res 32               ; the grid: applicable entries of verb_table
msg_word: .res MN_LAST-MN_RIGHT
