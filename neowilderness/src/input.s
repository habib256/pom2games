; Neowilderness input: no simulation changes until syntax and units pass.
.segment "INPUT"
module_input_command:
        ; The vocabulary ignores leading spaces. Numeric commands and QUIT
        ; must do the same before checking their first word.
        ldx     #0
        jsr     input_spaces
        txa
        beq     :+
        tay
        ldx     #0
@shift: lda     inbuf,y
        sta     inbuf,x
        beq     @shifted
        iny
        inx
        bne     @shift
@shifted:
        stx     linelen
:
        ldx     #0
@quit:  lda     inbuf,x
        cmp     input_quit_word,x
        bne     @number
        inx
        cpx     #4
        bcc     @quit
@tail:  lda     inbuf,x
        beq     input_quit
        cmp     #' '
        bne     @number
        inx
        bne     @tail
@number:
        ldx     #0
@scan:  lda     inbuf,x
        beq     @ordinary
        cmp     #'0'
        bcc     @next
        cmp     #'9'+1
        bcc     @found
@next:  inx
        bne     @scan
@found: cpx     #0
        beq     input_bad_command
        lda     inbuf-1,x
        cmp     #' '
        bne     input_bad_command
        stx     input_start
        jsr     input_allowed
        bcs     input_bad_command
        ldx     input_start
        jsr     input_parse
        bcs     input_bad_command
        ldx     input_start
@trim:  dex
        lda     inbuf,x
        cmp     #' '
        beq     @trim
        inx
        stx     linelen
        lda     #0
        sta     inbuf,x
        inc     input_argument
@ordinary:
        jmp     input_rest_command
input_ordinary:
        clc
        rts
input_bad_command:
        jsr     input_bad
        sec
        rts

input_quit:
        lda     #0
        sta     shown
        lda     #<input_quit_message
        ldx     #>input_quit_message
        jsr     message
        jsr     input_confirm
        cmp     #'Y'
        jne     input_cancel
        jmp     quit

; Exact, unqualified rest verbs can dispatch while INPUT is already present.
; Drop module_input_command's return address before entering resident code:
; SLEEP loads SIM/MEDICAL, which replace this overlay before it returns.
input_rest_command:
        ldx     #0
@entry: stx     input_pos
        lda     input_rest_words,x
        beq     input_ordinary
        sta     g2
        ldy     #0
@word:  inx
        lda     input_rest_words,x
        cmp     inbuf,y
        bne     @next
        iny
        cpy     g2
        bcc     @word
        lda     inbuf,y
        bne     @next
        lda     input_rest_words+1,x
        sta     verb
        lda     #0
        sta     qual
        sta     noun
        sta     nounbuf
        sta     parser_badverb
        lda     #1
        sta     found
        pla
        pla
        jmp     do_rest
@next:  lda     input_pos
        clc
        adc     g2
        adc     #2
        tax
        bne     @entry

input_rest_words:
        .byte 4,"REST",V_REST,5,"SLEEP",V_REST,4,"CAMP",V_CAMP
        .byte 8,"EXERCISE",V_EXER,4,"WAIT",V_WAIT,5,"PAUSE",V_WAIT,0

; Only supported numeric verbs may take an inline argument.
input_allowed:
        lda     #<input_verbs
        sta     gp2
        lda     #>input_verbs
        sta     gp2+1
@entry: ldy     #0
        lda     (gp2),y
        beq     @bad
        sta     g2
        ldx     #0
@word:  iny
        lda     (gp2),y
        cmp     inbuf,x
        bne     @next
        inx
        cpx     g2
        bcc     @word
        lda     inbuf,x
        cmp     #' '
        beq     @good
@next:  lda     gp2
        sec
        adc     g2
        sta     gp2
        bcc     @entry
        inc     gp2+1
        bne     @entry
@bad:  sec
        rts
@good: clc
        rts

module_number:
        lda     #0
        sta     shown
        lda     input_mode
        cmp     #2
        bne     :+
        jsr     input_stock
:       lda     input_argument
        bne     input_validate
input_read:
        jsr     prompt
        lda     #0
        sta     linelen
input_number_idle:
        jsr     wait_key
        jsr     kbd_upcase
        cmp     #KC_ESC
        jeq     input_cancel
        cmp     #KC_UP
        jeq     input_spin_up
        cmp     #KC_DOWN
        jeq     input_spin_down
        cmp     #KC_RET
        beq     @done
        cmp     #KC_LEFT
        beq     @erase
        cmp     #' '
        bcc     input_number_idle
        cmp     #'Z'+1
        bcs     input_number_idle
        ldx     linelen
        cpx     #MAXLINE
        bcs     input_number_idle
        sta     inbuf,x
        inc     linelen
        ora     #$80
        jsr     COUT
        jmp     input_number_idle
@erase: lda     linelen
        beq     input_number_idle
        dec     linelen
        dec     CH
        lda     #' '|$80
        jsr     COUT
        dec     CH
        jmp     input_number_idle
@done:  ldx     linelen
        lda     #0
        sta     inbuf,x
        ldx     #0
        jsr     input_spaces
        lda     inbuf,x
        beq     input_cancel
        jsr     input_parse
        bcc     input_validate
        jsr     input_bad
        jmp     input_read

input_validate:
        lda     input_value
        ora     input_value+1
        bne     @unit
        lda     input_mode
        cmp     #3              ; lot 7: azimuth 0 is north, not a cancel
        beq     @unit
        cmp     #0
        bne     input_cancel
@unit:  lda     input_mode
        cmp     #1
        beq     @duration
        lda     input_unit
        beq     @byte
        cmp     #3
        bne     input_invalid
        lda     input_mode
        cmp     #2              ; OZ: quantities, and FORAGE's (mode 3)
        bcc     input_invalid
@byte:  lda     input_mode
        cmp     #3             ; azimuth caller validates the complete 0..359 range
        beq     @accept
        lda     input_value+1
        bne     input_invalid
        beq     @accept
@duration:
        lda     input_unit
        cmp     #3
        beq     input_invalid
        cmp     #2
        beq     @minutes
        lda     #1
        sta     input_unit
        bne     @byte
@minutes:
        lda     input_value
        cmp     #<(15300+1)
        lda     input_value+1
        sbc     #>(15300+1)
        bcs     input_invalid
@accept:
        lda     input_value
        sta     msgnum
        lda     input_value+1
        sta     msgnum+1
        lda     #0
        sta     shown
        clc
        rts
input_invalid:
        jsr     input_bad
        lda     input_argument
        jeq     input_read
        sec
        rts
input_cancel:
        lda     #0
        sta     shown
        sta     msgnum
        sta     msgnum+1
        lda     #<input_cancelled
        ldx     #>input_cancelled
        jsr     message
        sec
        rts
input_bad:
        lda     #0
        sta     shown
        lda     #<input_invalid_message
        ldx     #>input_invalid_message
        jmp     message

input_spaces:
        lda     inbuf,x
        cmp     #' '
        bne     @done
        inx
        bne     input_spaces
@done:  rts

; Accessible ounces only: carried stock and the ground pile on this cell;
; BOIL WATER boils the canteen's, else the pile's (camp.s camp_boil: w_avail).
input_stock:
        lda     verb
        cmp     #9
        bne     :+
        lda     w_avail
        sta     stock_available
        lda     w_avail+1
        sta     stock_available+1
        jmp     @show
:       ldx     noun
        lda     it_place,x
        cmp     #5
        bne     @packed
        lda     #0
        sta     stock_available
        sta     stock_available+1
        beq     @ground
@packed:
        lda     it_pack_lo,x
        sta     stock_available
        lda     it_pack_hi,x
        sta     stock_available+1
@ground:
        jsr     at_ground
        bcc     @show
        clc
        lda     stock_available
        adc     it_gnd_lo,x
        sta     stock_available
        lda     stock_available+1
        adc     it_gnd_hi,x
        sta     stock_available+1
        bcc     @show
        lda     #$FF
        sta     stock_available
        sta     stock_available+1
@show:  lda     #<input_stock_prompt
        ldx     #>input_stock_prompt
        jmp     message

; Unsigned 16-bit number followed by H, MIN or OZ, with complete consumption.
input_parse:
        lda     #0
        sta     input_value
        sta     input_value+1
        sta     input_unit
        stx     input_pos
        jsr     input_spaces
        stx     input_digits
@digit: lda     inbuf,x
        cmp     #'0'
        bcc     @unit
        cmp     #'9'+1
        bcs     @unit
        and     #15
        sta     input_digit
        lda     input_value
        cmp     #<6553
        lda     input_value+1
        sbc     #>6553
        bcc     @multiply
        jne     @bad
        lda     input_value
        cmp     #<6553
        jne     @bad
        lda     input_digit
        cmp     #6
        jcs     @bad
@multiply:
        asl     input_value
        rol     input_value+1
        lda     input_value
        sta     g1
        lda     input_value+1
        sta     g2
        asl     input_value
        rol     input_value+1
        asl     input_value
        rol     input_value+1
        clc
        lda     input_value
        adc     g1
        sta     input_value
        lda     input_value+1
        adc     g2
        sta     input_value+1
        clc
        lda     input_value
        adc     input_digit
        sta     input_value
        bcc     :+
        inc     input_value+1
:       inx
        bne     @digit
@unit:  cpx     input_digits
        beq     @bad
        jsr     input_spaces
        lda     inbuf,x
        beq     @good
        cmp     #'H'
        bne     @min
        lda     #1
        sta     input_unit
        inx
        bne     @tail
@min:   cmp     #'M'
        bne     @oz
        inx
        lda     inbuf,x
        cmp     #'I'
        bne     @bad
        inx
        lda     inbuf,x
        cmp     #'N'
        bne     @bad
        lda     #2
        bne     @set
@oz:    cmp     #'O'
        bne     @bad
        inx
        lda     inbuf,x
        cmp     #'Z'
        bne     @bad
        lda     #3
@set:   sta     input_unit
        inx
@tail:  jsr     input_spaces
        lda     inbuf,x
        bne     @bad
@good:  clc
        rts
@bad:   sec
        rts

input_quit_word: .byte "QUIT"
input_start: .byte 0
input_pos: .byte 0
input_digits: .byte 0
input_digit: .byte 0
input_verbs:
        .byte 4,"WALK",2,"GO",3,"RUN",4,"MOVE",5,"CRAWL",4,"SWIM"
        .byte 4,"REST",5,"SLEEP",4,"CAMP",8,"EXERCISE",4,"WAIT",5,"PAUSE"
        .byte 3,"EAT",5,"DRINK",6,"NATURE",3,"WET",4,"BOIL"   ; BOIL WATER 8 OZ: the grid's (docs/MENUS.md 4)
        .byte 3,"GET",4,"PACK",4,"DROP",5,"CARRY"
        .byte 4,"SAVE",7,"RESTORE",5,"CATCH",0  ; CATCH GAME 1 H: the grid's duration

        .include "hof_load.inc" ; module_end, module_restart (lot 7)
.segment "CODE"

.segment "INPUT"

.segment "INPUT"
        UI_TWO input_confirm, 'N', 'Y'

.segment "INPUT"
; Numeric questions accept UP/DOWN as a spinner as well as typed digits.
; Only the text buffer changes; validation still uses input_validate.
input_spin_up:
        lda     #1
        bne     input_spin
input_spin_down:
        lda     #$FF
input_spin:
        sta     input_spin_delta+1
        ldx     linelen
        lda     #0
        sta     inbuf,x
        sta     input_value
        sta     input_value+1
        txa
        beq     input_spin_change
        ldx     #0
        jsr     input_parse
        jcs     input_number_idle
input_spin_change:
input_spin_delta:
        lda     #1
        bmi     input_spin_subtract
        inc     input_value
        bne     input_spin_draw
        inc     input_value+1
        bne     input_spin_draw
        dec     input_value+1
        dec     input_value
        bne     input_spin_draw
input_spin_subtract:
        lda     input_value
        ora     input_value+1
        beq     input_spin_draw
        lda     input_value
        bne     :+
        dec     input_value+1
:       dec     input_value
input_spin_draw:  jsr     prompt
        lda     input_value
        sta     num
        lda     input_value+1
        sta     num+1
        ldx     #8
input_spin_place: ldy     #0
input_spin_digit: sec
        lda     num
        sbc     pow10,x
        sta     input_spin_lo+1
        lda     num+1
        sbc     pow10+1,x
        bcc     input_spin_emit
        sta     num+1
input_spin_lo:
        lda     #0
        sta     num
        iny
        bne     input_spin_digit
input_spin_emit:  tya
        bne     input_spin_put
        cpx     #0
        beq     input_spin_put
        lda     linelen
        beq     input_spin_next
        tya
input_spin_put:   ora     #'0'
        ldy     linelen
        sta     inbuf,y
        inc     linelen
        ora     #$80
        jsr     COUT
input_spin_next:  dex
        dex
        bpl     input_spin_place
        jmp     input_number_idle
