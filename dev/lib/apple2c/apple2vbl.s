; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2vbl.s — video clock for ProDOS games: //e VBL polling, //c VBL IRQ.
;
; //e (enhanced): the VBL edge of $C019 (bit 7 clear in the blank), counted
; by a2_vbl_scan, which the game calls often while it draws.
; //c: the VBL interrupt of the built-in mouse firmware (mode 9), served by a
; ProDOS ALLOC_INTERRUPT handler. The handler counts the refresh, then calls
; the game's hook (a2_vbl_hook: the page flip, say).
; Anything else: no clock (mode 0), the game paces itself with delays.
; a2_vbl_count counts refreshes in both modes, modulo 256.
;
; Needs ProDOS, dev/lib/mouse (mouse_init first for the //c mode) and
; apple2frame.s. Neither the handler nor the scan uses the zero page or
; cc65's stack. Option (ca65 -D): A2_VBL_SCAN_SEI=1 reads an edge again
; under SEI before counting it, for games whose own interrupt handlers also
; call a2_vbl_scan (otherwise one between the read and the store would count
; it twice); 9 cycles more, only when the beam changes.
.setcpu "65C02"
.import _a2_frame_init
.import _mouse_timing_mode, _mouse_serve_irq, _mouse_slot
.export _a2_vbl_init, _a2_vbl_irq_init, _a2_vbl_close, _a2_vbl_scan
.export _a2_vbl_mode, _a2_vbl_count, _a2_vbl_beam, _a2_vbl_hook
.ifndef A2_VBL_SCAN_SEI
A2_VBL_SCAN_SEI = 0
.endif

.bss
_a2_vbl_mode:  .res 1           ; 0 none, 1 //e VBL polling, 2 //c VBL IRQ
_a2_vbl_count: .res 1           ; refreshes seen
_a2_vbl_beam:  .res 1           ; last $C019 bit 7 (//e)
_a2_vbl_hook:  .res 2           ; called by the handler after the count; 0 none
.data                           ; (6 bytes: a game moving its own lists here
allocate: .byte 2,0
        .word vbl_irq            ; keeps its DATA size)
release: .byte 1,0

.code
; A = 1 (and mode 1) on a //e with a VBL signal, else 0 (mode 0). Calls
; a2_frame_init (its delay is reset). X = 0.
_a2_vbl_init:
        jsr _a2_vbl_close       ; release an existing IRQ before polling
        jsr _a2_frame_init      ; A = 1 or 0, X = 0
        cmp #1
        bne none                ; mode 0 already (closed above)
        sta _a2_vbl_mode
        lda $C019
        and #$80
        sta _a2_vbl_beam
        lda #1                  ; (X = 0 since a2_frame_init)
        rts

; A = 2 (and mode 2) once the mouse firmware's VBL interrupt is installed,
; else 0 (no mouse, or MLI/firmware refused), preserving the previous mode.
; Repeated initialization reuses the handler. Success enables IRQs (CLI).
_a2_vbl_irq_init:
        lda _a2_vbl_mode
        lsr                     ; mode 2 alone has bit 1 set:
        bne irq_ready           ; never allocate a second handler
        lda _mouse_slot
        beq none
        php
        sei
        jsr $BF00
        .byte $40                ; ALLOC_INTERRUPT
        .word allocate
        bcs failed
        lda allocate+1
        sta release+1
        lda #9                   ; mouse firmware: VBL interrupts
        jsr _mouse_timing_mode
        bcs mouse_failed
        plp
irq_ready:
        lda #2
        sta _a2_vbl_mode
        cli
        ldx #0
        rts
mouse_failed:
        jsr $BF00               ; firmware refused: undo this allocation
        .byte $41
        .word release
failed: plp
none:   lda #0
        tax
        rts

; Back to mode 0; in mode 2, the mouse to mode 1 and the handler removed.
_a2_vbl_close:
        lda _a2_vbl_mode
        lsr                     ; mode 2 alone has bit 1 set: A = 1,
        beq closed              ; the firmware's passive mode below
        php
        sei
        jsr _mouse_timing_mode  ; A = 1
        jsr $BF00
        .byte $41                ; DEALLOC_INTERRUPT
        .word release
        plp
closed: stz _a2_vbl_mode
        rts

; Count //e VBL edges (picture -> blank). Call at most ~4 000 cycles apart
; while drawing (the blank lasts ~4 550): no edge is then missed. 33 cycles
; with the JSR when nothing changed (21 outside mode 1); A clobbered.
_a2_vbl_scan:
        lda _a2_vbl_mode
        lsr                     ; C = 1 for mode 1 alone
        bcc scanned
        lda $C019
        and #$80
        cmp _a2_vbl_beam
        beq scanned              ; (the common case: nothing written)
.if A2_VBL_SCAN_SEI
        php
        sei
        lda $C019
        and #$80
        cmp _a2_vbl_beam
        beq :+                   ; an interrupt took it
        sta _a2_vbl_beam
        asl a                    ; C = bit 7: blank -> picture, nothing
        bcs :+
        inc _a2_vbl_count
:       plp
.else
        sta _a2_vbl_beam
        asl a                    ; C = bit 7: blank -> picture, nothing
        bcs scanned
        inc _a2_vbl_count
.endif
scanned:
        rts

; ProDOS interrupt handler: C = 0 if it was the mouse firmware's VBL.
vbl_irq:
        cld
        jsr _mouse_serve_irq
        bcs served               ; not ours: C = 1 back to ProDOS
        inc _a2_vbl_count
        lda _a2_vbl_hook+1
        beq served               ; C = 0 since the bcs
        jsr hook
        clc                      ; (the hook ignores C: clear it again)
served: rts
hook:   jmp (_a2_vbl_hook)
