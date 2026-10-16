; VERHILLE Arnaud — GPL-3.0.
; Common navigation events. Only waiting loops poll the axes. Buttons are
; edge-triggered: holding VALIDATE never validates the next dialog too.
.segment "CODE"
.export ui_poll
keyboard_wait:
        jsr     ui_poll
        beq     keyboard_wait
        rts
ui_poll:
        txa
        pha
        tya
        pha
        lda     KBD
        bpl     @joy
        bit     KBDSTRB
        and     #$7F
        cmp     #'a'
        bcc     @return
        cmp     #'z'+1
        bcs     @return
        and     #$DF
        bne     @return
@joy:   dec     ui_scan
        bne     @none
        jsr     ui_joystick
        cmp     ui_last
        bne     @new
        cmp     #KC_RET
        beq     @none
        cmp     #KC_ESC
        beq     @none
        dec     ui_repeat
        bne     @none
        ldx     #15
        bne     @take
@new:   sta     ui_last
        ldx     #50
@take:  stx     ui_repeat
        bne     @return
@none:  lda     #0
@return:
        sta     ui_result+1
        pla
        tay
        pla
        tax
ui_result:
        lda     #0
        rts

; Parallel paddle timing, at most ~3 ms; calibrated in loop counts rather
; than ROM PDL units. Both timers still high at the end means no joystick.
ui_joystick:
        lda     $C062
        bmi     @cancel
        lda     $C061
        bmi     @accept
        lda     #0
        sta     ui_x
        sta     ui_y
        ldx     #0
        sta     $C070
@time:  lda     $C064
        bpl     :+
        stx     ui_x
:       lda     $C065
        bpl     :+
        stx     ui_y
:       inx
        bpl     @time
        lda     ui_x
        and     ui_y
        cmp     #127
        beq     @none
        lda     ui_x
        cmp     #26
        bcc     @left
        cmp     #86
        bcs     @right
        lda     ui_y
        cmp     #26
        bcc     @up
        cmp     #86
        bcs     @down
@none:  lda     #0
        rts
@cancel:lda     #KC_ESC
        rts
@accept:lda     #KC_RET
        rts
@left:  lda     #KC_LEFT
        rts
@right: lda     #KC_RIGHT
        rts
@up:    lda     #KC_UP
        rts
@down:  lda     #KC_DOWN
        rts
ui_x:   .byte 0
ui_y:   .byte 0
.segment "RESBSS"
ui_scan:   .res 1
ui_last:   .res 1
ui_repeat: .res 1
.segment "CODE"
; Historical entry used by the command reader and module callers.
kbd_upcase:
        cmp     #'a'
        bcc     :+
        cmp     #'z'+1
        bcs     :+
        and     #$DF
:       cmp     #0
        rts

; Typing a command suspends the stick; dialog readers still use ui_poll.
ui_prompt_poll:
        lda     mn_mode
        jne     ui_poll
        lda     linelen
        jeq     ui_poll
        lda     KBD
        bpl     @none
        bit     KBDSTRB
        and     #$7F
        jmp     kbd_upcase
@none:  lda     #0
        rts
