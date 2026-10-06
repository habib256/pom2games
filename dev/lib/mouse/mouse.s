; VERHILLE Arnaud — GPL-3.0. AppleMouse II Tech Notes 1 and 5.
; Firmware X=$Cn,Y=$n0. IIe polling mode 1; IIc native IRQs count motion.
; The pointer is kept in 0..139 by MOUSE_Y_LOW..MOUSE_Y_HIGH (0..191 unless
; the program defines them) and starts at 70, MOUSE_Y_START.
.ifndef MOUSE_Y_LOW
MOUSE_Y_LOW = 0
.endif
.ifndef MOUSE_Y_HIGH
MOUSE_Y_HIGH = 191
.endif
.ifndef MOUSE_Y_START
MOUSE_Y_START = 96
.endif
.export _mouse_init, _mouse_poll, _mouse_close
.export _mouse_slot, _mouse_x, _mouse_y, _mouse_buttons
.importzp ptr1
.macpack longbranch
.bss
_mouse_slot: .res 1
_mouse_x: .res 1
_mouse_y: .res 1
_mouse_buttons: .res 1
.rodata
offsets: .byte $05,$07,$0B,$0C,$FB
values:  .byte $38,$18,$01,$20,$D6
.code
firmware:
lookup: ldy $C400,x
        sty jump+1
xparam: ldx #$C4
yparam: ldy #$40
jump:   jmp $C400
_mouse_init:
        lda #0
        sta _mouse_slot
        sta _mouse_buttons
        sta ptr1
        lda #$C1
        sta ptr1+1
next:   ldx #4
check:  ldy offsets,x
        lda (ptr1),y
        cmp values,x
        jne again
        dex
        bpl check
        php
        sei
        lda ptr1+1
        sta lookup+2
        sta xparam+1
        sta jump+2
        and #$0F
        sta _mouse_slot
        asl
        asl
        asl
        asl
        sta yparam+1
        bit $C082
        ldx #$19
        jsr firmware
        lda #1
        ldx #$12
        jsr firmware
        lda #0
        sta $0478
        sta $0578
        sta $05F8
        lda #139
        sta $04F8
        lda #0
        ldx #$17
        jsr firmware
.if MOUSE_Y_LOW
        lda #MOUSE_Y_LOW
        sta $0478
        lda #0
.else
        lda #0
        sta $0478
.endif
        sta $0578
        sta $05F8
        lda #MOUSE_Y_HIGH
        sta $04F8
        lda #1
        ldx #$17
        jsr firmware
        ldx _mouse_slot
        lda #70
        sta $0478,x
        lda #MOUSE_Y_START
        sta $04F8,x
        lda #0
        sta $0578,x
        sta $05F8,x
        ldx #$16
        jsr firmware
        plp
        jsr _mouse_poll
        ; Native //c IOU motion is counted by its ROM interrupt handler,
        ; even when SETMOUSE's application API is in polling mode 1.
        lda $FBC0
        bne :+
        cli
:       lda _mouse_slot
        ldx #0
        rts
again:  inc ptr1+1
        lda ptr1+1
        cmp #$C8
        beq :+
        jmp next
:        lda #0
        tax
        rts
_mouse_poll:
        lda _mouse_slot
        beq done
        php
        sei
        ldx #$14
        jsr firmware
        ; Read result while interrupts remain disabled (Tech Note 1).
        ldx _mouse_slot
        lda $0478,x
        sta _mouse_x
        lda $04F8,x
        sta _mouse_y
        lda $0778,x
        sta _mouse_buttons
        plp
done:   rts
_mouse_close:
        lda _mouse_slot
        beq done
        php
        sei
        lda #0
        ldx #$12
        jsr firmware
        plp
        lda #0
        sta _mouse_slot
        sta _mouse_buttons
        rts

; Optional timing client: mouse VBL mode and firmware acknowledge.
; A=mode (1 polling, 9 polling + VBL). Caller masks IRQ while changing mode.
.export _mouse_timing_mode, _mouse_serve_irq
_mouse_timing_mode:
        ldx #$12
        jmp firmware
_mouse_serve_irq:
        ldx #$13
        jsr firmware
        bcs :+
        ldx _mouse_slot
        lda $0778,x
        and #8
        beq :+
        clc
        rts
:       sec
        rts
