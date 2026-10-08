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
mouse_clear_buffers: jmp clear_buffers
mouse_file_manager: jmp file_manager

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
    jsr save_workspace
    jsr _mouse_init
    sei
    jsr restore_workspace
    plp
    lda $FBC0
    bne init_done
    lda _mouse_slot
    beq init_done
    sta native_mouse
    cli
init_done:
    rts

poll:
    lda _mouse_slot
    beq done
    php
    sei
    jsr save_workspace
    jsr _mouse_poll
    jsr restore_workspace
    plp
    rts
done:
    rts

buttons:
    jsr poll
    lda _mouse_buttons
    ora $C061
    ora $C062
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

save_workspace:
    ldx #0
save_zp:
    lda $00,x
    sta saved_zp,x
    inx
    bne save_zp
    lda native_mouse
    bne workspace_saved
    ; AppleMouse scratch and per-slot mailboxes occupy the screen holes.
    ; PCS runtime tables have moved to $6800-$6B7F. Restore firmware
    ; mailboxes after the DOS dialog has cleared its temporary buffers.
    jsr install_holes
workspace_saved:
    rts

install_holes:
    ldx #7
save_holes:
.repeat 8, row
    lda firmware_holes + row*8,x
    sta $0478 + row*$80,x
.endrepeat
    dex
    bpl save_holes
    rts

restore_workspace:
    jsr capture_holes
    ldx #0
restore_zp:
    lda saved_zp,x
    sta $00,x
    inx
    bne restore_zp
    rts

capture_holes:
    ldx #7
restore_holes:
.repeat 8, row
    lda $0478 + row*$80,x
    sta firmware_holes + row*8,x
.endrepeat
    dex
    bpl restore_holes
    rts
; DOS dialogs clear their buffers in the same RAM as native mouse state.
; On //c the ROM IRQ handler owns live coordinates: retain them atomically.
clear_buffers:
    php
    sei
    lda native_mouse
    beq clear_start
    jsr capture_holes
clear_start:
    lda #0
    ldx #47
clear_dos_holes:
    sta dos_holes,x
    dex
    bpl clear_dos_holes
    ldy #0
    tya
clear_loop:
    sta $0400,y
    sta $0500,y
    sta $0600,y
    iny
    bne clear_loop
    lda native_mouse
    beq clear_done
    jsr install_holes
clear_done:
    plp
    rts

file_manager:
    lda native_mouse
    bne native_file_manager
    jmp $AAFD
native_file_manager:
    php
    sei
    pha
    txa
    pha
    tya
    pha
    jsr capture_holes
    ldx #7
install_dos_holes:
.repeat 6, row
    lda dos_holes + row*8,x
    sta $0478 + row*$80,x
.endrepeat
    dex
    bpl install_dos_holes
    pla
    tay
    pla
    tax
    pla
    jsr $AAFD
    sta result_a
    stx result_x
    sty result_y
    php
    pla
    sta result_p
    ldx #7
save_dos_holes:
.repeat 6, row
    lda $0478 + row*$80,x
    sta dos_holes + row*8,x
.endrepeat
    dex
    bpl save_dos_holes
    jsr install_holes
    ; Retain the file manager's flags (especially carry = error), while
    ; restoring the caller's IRQ mask for the native mouse ROM handler.
    pla
    and #4
    sta result_i
    lda result_p
    and #$FB
    ora result_i
    pha
    ldx result_x
    ldy result_y
    lda result_a
    plp
    rts
.segment "BSS"
result_a: .res 1
result_x: .res 1
result_y: .res 1
result_p: .res 1
result_i: .res 1
native_mouse: .res 1
saved_zp: .res 256
firmware_holes: .res 64
dos_holes: .res 48
