; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; mt_pages.s -- the MouseText top pages of NeoWildernessXL (docs/MENUS.md 9)
; ============================================================================
; The tail of the STATUS module on the XL edition only (segment STATX,
; $AF00-$B5FF, build/wildstx.bin: tools/build_disk.py appends it to the XL
; copy of wildsta.bin and writes the XL_* bytes of src/status.s,
; src/pages.s, src/inventory.s and src/game.s). The 140 KB edition keeps the
; plain pages: none of this is on its disk. The tail runs over the menu's
; $B000-$B5FF while a page is shown, as the simulation does between two
; prompts: get_line gathers the menu again (src/menu.s menu_gather).
; The shared helpers (mt_rep, mt_str, mt_puts) serve the pages, page_foot_x
; and the tail of MEDVIEW, which runs while STATUS is loaded. CRAFT, read
; over STATUS ($9600-$A7FF), keeps this tail: its page is drawn by the same
; frame engine (mt_cout, mt_pad), with its post-its in pf_craft.
; ============================================================================
.segment "STATX"
stx_base:
; ----------------------------------------------------------------------------
; Post-its (docs/MENUS.md 9.3, 15 October 2026). The shared pages lay out
; their blocks for both editions (a block's heading in inverse on its first
; row, its rows from column 0 or 41); on XL each block is a post-it, framed
; by the output itself. A page's table (pf_pages) gives six bytes a post-it:
; its first and last rows, its first and last columns, its title (0: the
; page's heading). The pages' COUT (mt_cout) writes each character, pad_to
; (tab, vtab, CR, topo_pad: the resident xl_padhook jumps to mt_pad while
; mt_cout is the COUT) the spaces; a cell of a frame gets its glyph: the
; first row the title (a static one: in inverse, a space each side), then
; the line '_' (MT_BOTTOM) to the last column; the last row the line $4C
; (MT_TOP); the rows between a bar on the left of the first column ($5F,
; MT_LBAR) and on the right of the last ($5A, MT_RBAR). Text that falls on
; a bar is written after it (a row starts at column 0 or 41, its text
; lands inside the box); text on a line wins over it, but normal spaces:
; they wait (pf_pend) and become the line when a pad follows them, spaces
; when more text does. Every cell is still written once with its final
; value (differential, one store per changed cell): the frames cost no
; store when the page is drawn again.
PF_BUF = page_top+3             ; dedicated 80-byte row frame, above CRAFT's blocks

; page_top_x -- (page_top's head jumps here) A = the page: an 80-column text
; page and its folder tabs: row 0, each page a tab between two MouseText
; bars ($5A on the left, $5F on the right), the page shown in inverse, the
; letters after them (never the screen's edge); row 1, the line under the
; tabs ($4C, at the top of its cells), open under the page shown. The
; cursor on row 2. Every cell is written once (differential, as page_top).
; The page's post-its: its table.
page_top_x:
        sta     pg_cur
        tax
        lda     pf_pages_lo,x
        sta     pf_tab
        lda     pf_pages_hi,x
        sta     pf_tab+1
        lda     #$FF
        sta     pf_row
        sta     pf_b1           ; (no signature: built again)
        jsr     text_screen
        jsr     text_mode80
        lda     #<mt_cout       ; the COUT of the pages: the post-its (text_finish
        sta     $36             ; puts back the COUT text_begin found)
        lda     #>mt_cout
        sta     $37
        ldx     #0
@tab:   stx     pg_i
        lda     #MT_RBAR        ; the tab's left edge
        jsr     COUT
        cpx     pg_cur
        bne     :+
        lda     CH              ; the page shown: in inverse, open below
        sta     pg_gap
        lda     #$3F
        sta     INVFLG
:       lda     #' '|$80
        jsr     COUT
        lda     pg_name_offsets,x
        jsr     pg_tab_text
        lda     #' '|$80
        jsr     COUT
        lda     #$FF
        sta     INVFLG
        ldy     CH
        ldx     pg_i
        cpx     pg_cur
        bne     :+
        sty     pg_gap_end
:       lda     #MT_LBAR        ; its right edge
        jsr     COUT
        inx
        cpx     #PG_COUNT
        bcc     @tab
        jsr     puts
        .byte   "|", 0
        ldy     #0              ; row 1: the line, open under the tab
@line:  lda     #MT_TOP
        cpy     pg_gap
        bcc     :+
        cpy     pg_gap_end
        bcs     :+
        lda     #' '|$80
:       jsr     COUT
        iny
        cpy     #80
        bcc     @line
        rts
pg_gap:     .byte 0             ; row 1: the columns under the page shown
pg_gap_end: .byte 0

; page_foot_x -- (the pages' JSR page_foot, XL) A/Y = the page's keys (an
; mt_str string). The footer of every page: row 22 a line across, row 23
; the arrows that turn the pages, the page's keys, and at column 70
; "ESC/<down> VIEW", or "ESC VIEW" on a page with a level. vtab pads the
; rows on the way (the post-its' last rows).
page_foot_x:
        pha
        tya
        pha
        lda     #22
        jsr     vtab
        lda     #MT_LINE
        ldy     #80             ; (the 80th wraps to row 23)
        jsr     mt_rep
pf_keys:
        jsr     mt_puts
        .byte   " ", MS_LEFT, MS_RIGHT, " PAGE  ", 0
        pla
        tay
        pla
        jsr     mt_str
        lda     #70
        jsr     tab
        jsr     puts
        .byte   "ESC", 0
        ldx     pg_cur
        lda     pg_levels,x
        bne     :+
        jsr     mt_puts
        .byte   "/", MS_DOWN, 0
:       jsr     puts
        .byte   " VIEW", 0
        rts

; page_foot23_x -- (OBJECTS' JSR page_foot, XL) the footer without the line
; of row 22: rows 20-22 hold the answer of the last transfer (columns 0-38).
page_foot23_x:
        pha
        tya
        pha
        lda     #23
        jsr     vtab
        jmp     pf_keys

; mt_rep -- Y times the character A: a MouseText glyph ($40-$5F) or a
; character with bit 7 set. A and X kept.
mt_rep: jsr     COUT
        dey
        bne     mt_rep
        rts
; mt_str -- the string at A/Y; mt_puts -- the string after the JSR. A byte
; below $20 is a MouseText glyph (MS_*: MT_* ^ $50), the others characters
; (ORA #$80). X kept.
mt_str: sta     gp2
        sty     gp2+1
mt_gp:  ldy     #0
@ch:    lda     (gp2),y
        beq     @end
        cmp     #$20
        bcs     :+
        eor     #$50            ; (a glyph: never 0)
        bne     @out
:       ora     #$80
@out:   jsr     COUT
        iny
        bne     @ch
@end:   rts
mt_puts:
        pla
        clc
        adc     #1
        sta     gp2
        pla
        adc     #0
        sta     gp2+1
        jsr     mt_gp           ; Y: the string's 0
        tya
        clc
        adc     gp2
        tay
        lda     gp2+1
        adc     #0
        pha
        tya
        pha
        rts
; pg_desc_x -- (OPTIONS' JSR vtab, XL) A = the row: there, the sentence of
; the option holding the focus (none on the tab row).
.pushseg
.segment "STATUS"
pg_desc_x:
        jsr     vtab
        ldx     pg_focus
        beq     :+
        lda     pg_desc_offsets-1,x
        pha
        lda     pg_desc_ids-1,x
        jmp     st_bank_suffix
:       rts
pg_desc_ids: .byte pg_desc_texts,pg_desc_texts,pg_desc_texts,pg_d4
pg_desc_offsets: .byte 0,46,80,0
.popseg
; bar_x -- (bar's head, XL) a gauge of ten cells, A of them full: solid
; blocks ($4E), checkerboards ($56) for the rest, then two spaces.
bar_x:  sta     pf_n
        ldx     #0
@cell:  lda     #MT_BLOCK
        cpx     pf_n
        bcc     :+
        lda     #MT_HALF1
:       jsr     COUT
        inx
        cpx     #10
        bcc     @cell
        jsr     puts
        .byte   "  ", 0
        rts

; ----------------------------------------------------------------------------
; The frame engine. mt_cout -- the COUT of the pages (page_top_x). A, X, Y
; kept. A CR: topo_output's (its padding comes back through mt_pad).
mt_cout:
        cmp     #$8D
        bne     :+
        jmp     topo_output
:       pha
        stx     pf_sx
        sty     pf_sy
        and     INVFLG          ; (topo_output's AND $32)
        sta     pf_ch
        lda     CV              ; spaces waiting on another row: forgotten
        cmp     pf_prow
        beq     @cell
        sta     pf_prow
        lda     #0
        sta     pf_pend
@cell:  lda     CV              ; (pf_sync: a new row only)
        cmp     pf_row
        beq     :+
        jsr     pf_sync
:
        ldy     CH
        lda     PF_BUF,y
        beq     @text
        cmp     #MT_LBAR
        beq     @bar
        cmp     #MT_RBAR
        beq     @bar
        ldx     pf_ch           ; a line or a title: a normal space waits
        cpx     #' '|$80
        bne     @text
        ldx     pf_pend
        bne     :+
        sty     pf_ps
:       inc     pf_pend
        inc     CH
        bne     @out
@text:  ldx     pf_pend         ; the spaces waiting: spaces, text follows
        beq     :+
        lda     #' '|$80
        ldy     pf_ps
        jsr     t_update
        inc     pf_ps
        dec     pf_pend
        jmp     @text
:       lda     pf_ch
        jsr     pf_put
@out:   ldx     pf_sx
        ldy     pf_sy
        pla
        rts
@bar:   jsr     pf_put          ; the bar, then the text after it
        jmp     @cell
; pf_put -- A in the cell CH of row CV, the cursor on (past the row's
; width: the next row, column 0, as topo_output).
pf_put: ldy     CH
        jsr     t_update
        inc     CH
        lda     CH
        cmp     WNDWDTH
        bcc     :+
        lda     #0
        sta     CH
        inc     CV
        jsr     t_vtab
:       rts

; mt_pad -- (xl_padhook: pad_to while mt_cout is the COUT, pad_limit set)
; the cells from CH (or the first space waiting) to pad_limit - 1: the
; frame's glyphs, spaces elsewhere (clear_to, run by run); CH ends at
; pad_limit. X kept, as pad_to.
mt_pad: stx     pf_sx
        lda     pf_pend         ; the spaces waiting on this row: the line
        beq     :+
        lda     #0
        sta     pf_pend
        lda     CV
        cmp     pf_prow
        bne     :+
        lda     pf_ps
        sta     CH
:       lda     CV              ; (pf_sync: a new row only)
        cmp     pf_row
        beq     @cell
        jsr     pf_sync
@cell:  ldy     CH
        cpy     pad_limit
        bcs     @end
        lda     PF_BUF,y
        bne     @glyph
@run:   iny                     ; a run of plain cells
        cpy     pad_limit
        bcs     :+
        lda     PF_BUF,y
        beq     @run
:       lda     pad_limit
        pha
        sty     pad_limit
        ldy     CH
        jsr     clear_to
        lda     pad_limit
        sta     CH
        pla
        sta     pad_limit
        bne     @cell           ; (pad_limit > CH > 0)
@glyph: jsr     t_update
        inc     CH
        bne     @cell
@end:   lda     pad_limit
        sta     CH
        ldx     pf_sx
        rts

; pf_sync -- PF_BUF holds the frame of row CV. A row's signature (the state
; of each post-it there: none, first, between, last; 2 bits each) tells
; whether the buffer of the last row built serves it as is (most rows: the
; bars of the same post-its); else it is built again. X, Y changed.
pf_sync:
        lda     CV
        cmp     pf_row
        bne     :+
        rts
:       sta     pf_row
        lda     #0
        sta     pf_s0
        sta     pf_s1
        ldx     CV              ; rows 0-1, the tabs: no post-it (the table
        cpx     #2              ; of CRAFT is not read yet)
        bcc     @same
        tax                     ; (0: the table's start)
@sig:   jsr     pf_get
        cmp     #PF_END
        beq     @same
        sta     pf_top
        jsr     pf_get
        sta     pf_bot
        inx                     ; (the columns, the title)
        inx
        inx
        inx
        ldy     #0              ; 0: above or below
        lda     CV
        cmp     pf_top
        bcc     @st
        beq     @first
        cmp     pf_bot
        bcc     @between
        bne     @st
        iny                     ; 3: the last row
@between:
        iny                     ; 2: a row between
@first: iny                     ; 1: the first row
@st:    tya
        asl     pf_s0
        rol     pf_s1
        asl     pf_s0
        rol     pf_s1
        ora     pf_s0
        sta     pf_s0
        jmp     @sig
@same:  lda     pf_s0           ; the buffer's own signature: kept
        cmp     pf_b0
        bne     :+
        lda     pf_s1
        cmp     pf_b1
        bne     :+
        rts
:       lda     pf_s0
        sta     pf_b0
        lda     pf_s1
        sta     pf_b1
        ldx     #79
        lda     #0
:       sta     PF_BUF,x
        dex
        bpl     :-
        lda     CV
        cmp     #2
        bcs     :+
        rts
:       inx                     ; (0: the table's start)
@box:   jsr     pf_get          ; the first row ($FF: the table's end)
        cmp     #PF_END
        bne     :+
        rts
:       sta     pf_top
        jsr     pf_get
        sta     pf_bot
        jsr     pf_get
        sta     pf_l
        jsr     pf_get
        sta     pf_r
        jsr     pf_get
        sta     @ts+1
        jsr     pf_get
        sta     @ts+2
        stx     pf_x
        lda     pf_row
        cmp     pf_top
        bcc     @next           ; above the box
        beq     @top
        cmp     pf_bot
        bcc     @mid
        bne     @next           ; below it
        lda     #MT_TOP         ; the last row: the line at the top
        jsr     pf_line
        bcs     @next
@mid:   ldy     pf_l            ; a row between: the bars
        lda     #MT_LBAR
        sta     PF_BUF,y
        ldy     pf_r
        lda     #MT_RBAR
        sta     PF_BUF,y
        bne     @next
@top:   lda     #MT_BOTTOM      ; the first row: the line at the bottom,
        jsr     pf_line         ; the title over it
        lda     @ts+2
        beq     @next           ; (0: the page writes its heading)
        ldy     pf_l
        ldx     #0
        lda     #$20            ; an inverse space
@title: sta     PF_BUF,y
        iny
@ts:    lda     $FFFF,x
        beq     :+
        and     #$3F            ; in inverse
        inx
        bne     @title
:       lda     #$20
        sta     PF_BUF,y
@next:  ldx     pf_x
        jmp     @box
pf_get:
pf_tab = * + 1
        lda     $FFFF,x
        inx
        rts
; pf_line -- A in PF_BUF from pf_l to pf_r. C set.
pf_line:
        ldy     pf_l
:       sta     PF_BUF,y
        cpy     pf_r
        iny
        bcc     :-
        rts
pf_row:  .byte $FF              ; the row of PF_BUF
pf_s0:   .byte 0                ; the signature of row CV
pf_s1:   .byte 0
pf_b0:   .byte 0                ; the signature of PF_BUF's row
pf_b1:   .byte $FF
pf_sx:   .byte 0
pf_sy:   .byte 0
pf_ch:   .byte 0
pf_pend: .byte 0                ; normal spaces waiting on a line: how many,
pf_ps:   .byte 0                ; from which column,
pf_prow: .byte 0                ; on which row
pf_top:  .byte 0
pf_bot:  .byte 0
pf_l:    .byte 0
pf_r:    .byte 0
pf_x:    .byte 0
pf_n:    .byte 0

; The post-its of each page (PF, src/mousetext.inc): first row, last row,
; first column, last column, title (0: the page's heading). docs/MENUS.md 9.
pf_pages_lo: .byte <pf_status, <pf_objects, <pf_craft, <pf_help, <pf_options, <pf_menu, <eq_frames
pf_pages_hi: .byte >pf_status, >pf_objects, >pf_craft, >pf_help, >pf_options, >pf_menu, >eq_frames
pf_status:
        PF      2, 14, 0, 39, 0                 ; CONDITION
        PF      2, 10, 41, 79, 0                ; LOCAL
        PF      11, 14, 41, 79, 0               ; CONDITIONS
        PF      15, 21, 0, 79, 0                ; MEDICAL
        .byte   PF_END
ob_frames_x:
        lda     #2
        sta     pf_obj_hands
        jsr     ob_build
        ldx     #1
        jsr     ob_top
        sta     ob_e
        ldx     ob_at+1
@find:  lda     overlay_text,x
        cmp     #$82
        beq     @found
        inx
        bne     @find
@found: txa
        sec
        sbc     ob_at+1
        sbc     ob_e
        bcc     @past
        beq     @past
        clc
        adc     #3
        cmp     #15
        bcs     @below
        sta     pf_obj_pack
        tax
        dex
        stx     pf_obj_hands+1
        rts
@past:  lda     #$8A             ; skip a PACK heading repeated below its frame title
        sta     overlay_text,x
        lda     #$FE
        sta     pf_obj_hands
        lda     #2
        sta     pf_obj_pack
        rts
@below: lda     #$FE
        sta     pf_obj_pack
        lda     #15
        sta     pf_obj_hands+1
        rts
pf_objects:
        PF      2, 15, 0, 39, 0                 ; LOCAL
pf_obj_hands:
        PF      2, 3, 41, 79, 0                 ; HANDS, bottom computed
pf_obj_pack:
        PF      4, 15, 41, 79, 0                ; PACK, top computed
        PF      16, 20, 0, 39, 0                ; CARRYING
        PF      16, 20, 41, 79, 0               ; LOAD
        .byte   PF_END
pf_help:
        PF      2, 9, 0, 39, 0                  ; (the blocks' headings)
        PF      2, 9, 41, 79, 0
        PF      11, 19, 0, 39, 0
        PF      11, 19, 41, 79, 0
        .byte   PF_END
pf_options:
        PF      2, 9, 0, 79, 0                  ; OPTIONS
        .byte   PF_END
pf_menu:
        PF      2, 5, 0, 39, 0                  ; RANGERS
        PF      6, 9, 0, 39, 0                  ; SAVE / RESTORE
        PF      10, 12, 0, 39, mn_quit          ; QUIT
        .byte   PF_END

; The keys of the cursor pages and of OBJECTS (page_foot's pg_k_menu,
; inventory_keys).
pg_k_menu_x: .byte MS_UP, MS_DOWN, " CHOOSE  ", MS_RET, " SELECT", 0
.pushseg
.segment "MEDVX"
inventory_keys_x: .byte MS_RET, " LIST/ACT ", MS_LEFT, MS_RIGHT, MS_UP, MS_DOWN, " MOVE  H HANDS", 0
mvx_end:
.popseg
ob_mul: lda     #0
        sta     num
        sta     num+1
@add:   dey
        bmi     @rts
        clc
        lda     num
        adc     ob_m
        sta     num
        lda     num+1
        adc     ob_m+1
        sta     num+1
        jmp     @add
@rts:   rts
stx_end:
.assert PF_BUF + 80 <= page_keys, error, "PF_BUF: page_top's body too short"
.assert PF_BUF >= CRAFT_RUN + (crx_end - CRAFT_RUN + 511) / 512 * 512, error, "PF_BUF under CRAFT's blocks"

; ----------------------------------------------------------------------------
; The grid (docs/MENUS.md 9, XL): a bar on the right of each labelled cell's
; last column, the cells side by side as boxes. Resident: tools/build_disk.py
; copies xl_pad over page_foot (src/pages.s), which XL never calls (its
; pages use page_foot_x); cell_put's pad loop calls it there (XL_ABS). It
; must stay position independent: branches only, and absolute addresses
; outside itself.
.segment "XLRES"
; xl_pad -- (cell_put, the pad of a cell) A = ' ', X = the pads left: the
; last pad of a labelled cell of the grid is the bar; else cell_char.
xl_pad: cpx     #1
        bne     @space
        ldy     mn_k            ; (an empty cell: spaces)
        beq     @space
        ldy     mn_col
        cpy     #MN_GRID        ; (the result column's command line: spaces)
        bcc     @space
        cpy     #MN_GRID+6*6-1 ; right edge stays open (after DRINK)
        bcs     @space
        lda     #MT_RBAR
        jsr     t_update
@skip:  inc     mn_col
        rts
@space: jmp     cell_char
; xl_curtain -- (view_hide's CLREOP) the curtain of a simulation or a full
; redraw, the long actions, with an hourglass in its middle (row 9, column
; 39: an odd column, the main page).
xl_curtain:
        jsr     CLREOP
        lda     #MT_HOURGL
        sta     $0400+128+40+39/2
        rts
; xl_padhook -- (pad_to's first instruction, XL: tab, vtab, a CR, topo_pad)
; while the pages' COUT is mt_cout (a top page is being drawn), mt_pad pads
; with the post-its' frames; else pad_to's own spaces. A = the limit.
xl_padhook:
        sta     pad_limit
        ldy     $37
        cpy     #>mt_cout
        beq     @x
        jmp     pad_to+3
@x:     jmp     mt_pad
xl_pad_end:
.segment "STATX"
; pad_to (LOWPAGE) jumps to xl_padhook (resident, over page_foot: XL_COPIES).
        XL_BYTE XI_LOWPG, pad_to, $4C
        XL_BYTE XI_LOWPG, pad_to+1, <(page_foot+xl_padhook-xl_pad)
        XL_BYTE XI_LOWPG, pad_to+2, >(page_foot+xl_padhook-xl_pad)
