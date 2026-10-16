; A two-way question keeps its letter shortcuts, and also accepts arrows
; followed by VALIDATE. ESC always cancels. FIRST is the safe default.
.macro UI_TWO name, first, second
.local draw, key, toggle, chosen, done, value
name:
        lda     #first
        sta     value+1
draw:   jsr     prompt
value:  lda     #first
        ora     #$80
        jsr     COUT
key:    jsr     wait_key
        cmp     #KC_ESC
        beq     done
        cmp     #first
        beq     done
        cmp     #second
        beq     done
        cmp     #KC_RET
        beq     chosen
        cmp     #KC_LEFT
        beq     toggle
        cmp     #KC_RIGHT
        beq     toggle
        cmp     #KC_UP
        beq     toggle
        cmp     #KC_DOWN
        bne     key
toggle: lda     value+1
        eor     #(first ^ second)
        sta     value+1
        jmp     draw
chosen: lda     value+1
done:   rts
.endmacro
