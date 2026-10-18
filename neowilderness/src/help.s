; Cold HELP renderer; STATUS remains live in the other window.
.segment "HELPUI"
module_help_body:
        lda     #30
        sta     WNDWDTH
        lda     #$3F
        sta     INVFLG
        jsr     puts
        .byte   " HELP ", 0
        jsr     pg_first
        ldx     #0
@topic: stx     help_page
        lda     help_names_lo,x
        ldy     help_names_hi,x
        jsr     print_str_ay
        ldx     help_page
        inx
        cpx     #4
        beq     @body
        jsr     pg_line
        ldx     help_page
        inx
        jmp     @topic
@body:  lda     #22
        jsr     vtab
        lda     #80
        sta     WNDWDTH
        lda     #2
        ldx     #30
        jsr     st_at_x
        ldx     pg_focus
        beq     :+
        dex
:       stx     help_page
        lda     #0
        sta     help_part
        jsr     help_load
        lda     #$3F
        sta     help_inv
@line:  ldx     #0
        jsr     help_line
        jsr     topo_pad
        inc     CV
        jsr     t_vtab
        lda     #30
        sta     CH
        lda     #$FF
        sta     help_inv
        lda     CV
        cmp     #22
        bcs     @footer
        lda     #' '|$80
        jsr     COUT
        jmp     @line
@footer:
        lda     #<pg_k_menu_x
        ldy     #>pg_k_menu_x
        jsr     page_foot_x
help_key:
        jsr     wait_key
        jsr     page_keys
        jmp     help_key
; Print the selected topic one line at a time, leaving all other topics folded.
help_line:
        stx     help_x
        lda     help_ptr,x
        sta     gp2
        lda     help_ptr+1,x
        sta     gp2+1
        lda     help_inv
        sta     INVFLG
@ch:    ldy     #0
        lda     (gp2),y
        bne     @char
        lda     help_part
        bne     @end
        inc     help_part
        jsr     help_load
        jmp     help_line
@char:  inc     gp2
        bne     :+
        inc     gp2+1
:       cmp     #13
        beq     @end
        ora     #$80
        jsr     COUT
        jmp     @ch
@end:   lda     #$FF
        sta     INVFLG
        ldx     help_x
        lda     gp2
        sta     help_ptr,x
        lda     gp2+1
        sta     help_ptr+1,x
        rts
help_page: .byte 0
help_x:    .byte 0
help_inv:  .byte 0
help_ptr:  .word 0
help_names_lo: .byte <hp_move,<hp_items,<hp_live,<hp_save
help_names_hi: .byte >hp_move,>hp_items,>hp_live,>hp_save
help_ids: .byte om_need,om_qty_label,om_eat_word,om_lower_word
help_part: .byte 0
help_load:
        ldx     help_page
        lda     help_part
        bne     @more
        lda     help_ids,x
        jsr     text_fetch
        lda     #<(tb_buf+8)
        ldx     #>(tb_buf+8)
        bne     @store
@more:  lda     help_more_lo,x
        pha
        lda     help_more_hi,x
        tax
        pla
@store: sta     help_ptr
        stx     help_ptr+1
        ldx     #0
        rts
help_more_lo: .byte <hp_m0,<hp_m1,<hp_m2,<hp_m3
help_more_hi: .byte >hp_m0,>hp_m1,>hp_m2,>hp_m3
hp_m0: .byte "CANCEL: STOP. UP: PAGES.",13,"MAP: RETURN TO PLAN A ROUTE.",0
hp_m1: .byte "PORTION -> REVIEW -> CONFIRM",13,"CANCEL: BACK. USE: ACTIVATE.",0
hp_m2: .byte "REST: ENERGY. STATUS: CARE.",13,"CATCH: BAIT + TRAP/GEAR.",0
hp_m3: .byte "CANCEL: BACK. QUIT ASKS FIRST.",0
hp_move: .byte " MOVE",0
hp_items: .byte " OBJECTS & GEAR",0
hp_live: .byte " SURVIVE",0
hp_save: .byte " SAVE & LEAVE",0
