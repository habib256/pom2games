; VERHILLE Arnaud — GPL-3.0. PCS adapter for DEVBENCH's AppleMouse driver.
; Fixed jump table, shared by every overlay; preserve PCS zero page.
; Runtime tables are relocated above the driver, leaving mouse mailboxes
; visible in text RAM. Private firmware state survives DOS buffer clears.
.setcpu "6502"
.import _mouse_init, _mouse_poll, _mouse_slot, _mouse_x, _mouse_y, _mouse_buttons
.export mouse_init, mouse_buttons, mouse_cursor_x, mouse_cursor_y
.exportzp ptr1
.segment "ZEROPAGE"
ptr1: .res 2
.segment "CODE"
mouse_init:     jmp init
mouse_buttons:  jmp buttons
mouse_cursor_x: jmp cursor_x
mouse_cursor_y: jmp cursor_y
mouse_clear_buffers: jmp mouse_context_clear_buffers
mouse_file_manager: jmp mouse_context_file_manager
mouse_drag_delta: jmp drag_delta
mouse_drag_anchor: jmp drag_anchor

CURSORY = $82
CURSORXDIV7 = $83
CURSORXMOD7 = $84
CRSRRTSTOP = $8C
DIV7 = $1400
MOD7 = $1500
; Original entry prologues (LDA #50 / JSR $FCA8) occupy five bytes.
PADDLE_X_BODY = $19FE + 5
PADDLE_Y_BODY = $1A59 + 5

init:
    php
    sei
    jsr mouse_context_save_workspace
    jsr _mouse_init
    sei
    jsr mouse_context_restore_workspace
    plp
    lda $FBC0
    bne init_done
    lda _mouse_slot
    beq init_done
    sta mouse_context_native_mouse
    cli
init_done:
    rts

poll:
    lda _mouse_slot
    beq done
    php
    sei
    jsr mouse_context_save_workspace
    jsr _mouse_poll
    jsr mouse_context_restore_workspace
    plp
    rts
done:
    rts

buttons:
    ; Original GETBUTNS preserves X/Y. In particular WORLD's slider loop
    ; retains its WSET index in Y while the button remains held.
    txa
    pha
    tya
    pha
    jsr poll
    pla
    tay
    pla
    tax
    lda _mouse_buttons
    ora $C061
    ora $C062
    rts

; A is the clamped horizontal displacement, X the new drag position.
; Absolute mouse input can move more than 15 pixels between editor polls.
; Keep the historical small-step guard only for the paddle cursor.
drag_delta:
    pha
    lda _mouse_slot
    beq paddle_delta
    pla
accept_delta:
    sec
    rts
paddle_delta:
    pla
    cmp #$10
    bcc accept_delta
    cmp #$F0
    bcs accept_delta
    clc
    rts

; The paddle UI warps the hand to the piece's right edge. Absolute mouse
; input must keep the click position, so a pickup has zero displacement.
drag_anchor:
    lda _mouse_slot
    bne anchor_done
    ldx $03 ; PARAM+3 = right bound
    lda DIV7,x
    sta CURSORXDIV7
    lda MOD7,x
    sta CURSORXMOD7
anchor_done:
    rts

cursor_x:
    lda _mouse_slot
    beq paddle_x
    jsr poll
    ; The shared driver reports 0..139 color pixels: two HGR pixels each.
    lda _mouse_x
    asl
    bcs wide_x
    tay
    ldx DIV7,y
    lda MOD7,y
    jmp clamp_x
wide_x:
    ; For x >= 256, (256 + low) / 7 = 36 + (4 + low) / 7.
    clc
    adc #4
    ldx #36
divide_x:
    cmp #7
    bcc clamp_x
    sbc #7
    inx
    bne divide_x
clamp_x:
    cpx CRSRRTSTOP
    bcc done_x
    ldx CRSRRTSTOP
    lda #0
done_x:
    rts
paddle_x:
    lda #50
    jsr $FCA8
    jmp PADDLE_X_BODY

cursor_y:
    lda _mouse_slot
    beq paddle_y
    ; UPDATECRSR calls cursor_x first, which already polls both axes.
    lda _mouse_y
    rts
paddle_y:
    lda #50
    jsr $FCA8
    jmp PADDLE_Y_BODY

MOUSE_CONTEXT_DOS_ENTRY = $AAFD
MOUSE_CONTEXT_DOS_ROWS = 6
MOUSE_CONTEXT_CLEAR_BASE = $0400
MOUSE_CONTEXT_CLEAR_PAGES = 3
.include "mouse_context.asm"
