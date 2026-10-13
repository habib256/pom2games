; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Full redraws and SIM use a clean text curtain. Preserve the live command
; and result rows and the cursor; restore the four-row command window. Never expose
; an earlier STATUS/HELP page or executable bytes in HGR.
.segment "CODE"
view_hide:
view_loading:
        lda     #1              ; keep HELLO visible until the first full view
        bne     view_hide_done
        lda     CH
        pha
        lda     CV
        pha
        lda     #0
        jsr     vtab
        lda     #20
        sta     $23
        jsr     CLREOP
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
.segment "CODE"
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
topo_output:
        pha
        sty     topo_output_y+1
        cmp     #$8D
        beq     topo_output_newline
        and     $32
        ldy     CH
        cmp     ($28),y
        beq     topo_output_advance
topo_store:
        sta     ($28),y
topo_output_advance:
        inc     CH
        lda     CH
        cmp     #40
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

topo_pad:
        ldy     CH
        lda     #' '|$80
topo_pad_byte:
topo_pad_limit:
        cpy     #40
        bcs     topo_pad_done
        cmp     ($28),y
        beq     topo_pad_next
topo_clear_store:
        sta     ($28),y
topo_pad_next:
        iny
        bne     topo_pad_byte
topo_pad_done:
        ldy     topo_pad_limit+1
        sty     CH
        rts

.segment "CODE"
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
