; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full redraws use a clean text curtain; SIM keeps the last complete view.
; Preserve the live command
; and result rows and the cursor; restore the four-row command window. Never expose
; an earlier STATUS/HELP page or executable bytes in HGR.
; The curtain is 80-column text, like the four mixed rows of the view: the
; results stay readable while the view is rebuilt. Coming from a 40-column
; menu, rows 20..23 hold menu text, not results: the whole page is cleared.
.segment "CODE"
view_hide:
view_loading:
        lda     #1              ; keep HELLO visible until the first full view
        bne     view_hide_done
        lda     CH
        pha
        lda     CV
        pha
        lda     #20
        bit     text80
        bmi     :+
        lda     #24
:       sta     $23
        jsr     text_mode80
        lda     #0
        jsr     vtab
        XL_ABS  XI_MAIN, page_foot+xl_curtain-xl_pad, @x54  ; (XL: an hourglass
        jsr     CLREOP                  ; on the curtain, src/mt_pages.s)
        lda     #24
        sta     $23
        lda     #20
        sta     WNDTOP
        pla
        jsr     vtab
        pla
        sta     CH
        jsr     show_text
view_hide_done:
        rts

; MAP and all text menus share differential COUT. Page preparation stays
; behind the current display; wait_key reveals only a completed text page.
text_finish:
        lda     text_vector_hi
        beq     text_finish_done
        lda     $23
        jsr     vtab            ; pad every unfinished/skipped row differentially
text_release:
text_release_lo:
        lda     #0
        sta     $36
text_release_hi:
        lda     #0
        sta     $37
        lda     #0
        sta     text_vector_hi
        jsr     show_text
text_finish_done: rts

; COUT preserves A/X/Y. Self-modified Y saves avoid using scratch shared
; with decimal/float printing. The hook never calls COUT recursively.
; Stores go through t_update: one store per changed cell, in the layout of
; the page (40 columns for menus, 80 for MAP).
topo_output:
        pha
        sty     topo_output_y+1
        cmp     #$8D
        beq     topo_output_newline
        and     $32
        ldy     CH
        bit     text80
        bmi     topo_output_80
        cmp     ($28),y         ; 40-column menus: differential store
        beq     topo_output_next
t_store_menu:
        sta     ($28),y
        bne     topo_output_next
topo_output_80:
        jsr     t_update
topo_output_next:
        inc     CH
        lda     CH
        cmp     WNDWDTH
        bcc     topo_output_done
topo_output_newline:
        jsr     topo_pad
        inc     CV
        lda     #0
        sta     CH
        jsr     t_vtab
topo_output_done:
topo_output_y:
        ldy     #0
        pla
        rts

wait_key:
        txa
        pha
        tya
        pha
        jsr     text_finish
        pla
        tay
        pla
        tax
        jmp     keyboard_wait

text_vector_lo = text_release_lo+1
text_vector_hi = text_release_hi+1
