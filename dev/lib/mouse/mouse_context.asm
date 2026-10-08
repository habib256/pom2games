; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Optional AppleMouse workspace protection for legacy ASM programs.
; Include in resident writable memory, after caller code; no extra zero page.
; save_workspace: saves all 256 ZP bytes; restores slot-card mailboxes from
; the shadow unless native_mouse!=0 (native //c IRQs own live mailboxes).
; restore_workspace: captures 8x8 text-screen holes then restores all ZP.
; capture_holes/install_holes: copy all 64 mailbox bytes at $0478+n*$80.
; These routines clobber A,X. Caller must mask IRQ across each transaction;
; Initialise mouse_context_native_mouse to zero before mouse_init; set it
; nonzero after detecting native //c firmware.
; No driver init/poll or IRQ enabling is performed by this module.
;
; Optional DOS client: define MOUSE_CONTEXT_DOS_ENTRY (absolute entry address),
; MOUSE_CONTEXT_DOS_ROWS (1..8), MOUSE_CONTEXT_CLEAR_BASE (page aligned),
; MOUSE_CONTEXT_CLEAR_PAGES. clear_buffers masks IRQ, clears the requested
; pages/DOS shadow and retains live native mailboxes. file_manager swaps DOS
; mailboxes around the entry call on native //c only; slot cards call directly.
; X,Y are forwarded; A contains native_mouse at entry (legacy PCS ABI).
; Output A,X,Y and result flags are retained; the caller's I flag is restored. Other firmware state must remain resident; not reentrant.
.ifndef _MOUSE_CONTEXT_LOADED_
_MOUSE_CONTEXT_LOADED_ = 1
.ifdef MOUSE_CONTEXT_DOS_ENTRY
.assert MOUSE_CONTEXT_DOS_ROWS >= 1 .and MOUSE_CONTEXT_DOS_ROWS <= 8, error, "DOS mailbox row count"
.assert (MOUSE_CONTEXT_CLEAR_BASE .mod $100) = 0, error, "clear base must be page aligned"
.assert MOUSE_CONTEXT_CLEAR_PAGES >= 1, error, "clear page count"
.endif
.segment "CODE"
mouse_context_save_workspace:
    ldx #0
mouse_context_save_zp:
    lda $00,x
    sta mouse_context_saved_zp,x
    inx
    bne mouse_context_save_zp
    lda mouse_context_native_mouse
    bne mouse_context_workspace_saved
    ; AppleMouse scratch and per-slot mailboxes occupy the screen holes.
    ; Caller data must not overlap these mailboxes. Restore them after
    ; client operations that cleared text-screen buffers.
    jsr mouse_context_install_holes
mouse_context_workspace_saved:
    rts

mouse_context_install_holes:
    ldx #7
mouse_context_save_holes:
.repeat 8, row
    lda mouse_context_firmware_holes + row*8,x
    sta $0478 + row*$80,x
.endrepeat
    dex
    bpl mouse_context_save_holes
    rts

mouse_context_restore_workspace:
    jsr mouse_context_capture_holes
    ldx #0
mouse_context_restore_zp:
    lda mouse_context_saved_zp,x
    sta $00,x
    inx
    bne mouse_context_restore_zp
    rts

mouse_context_capture_holes:
    ldx #7
mouse_context_restore_holes:
.repeat 8, row
    lda $0478 + row*$80,x
    sta mouse_context_firmware_holes + row*8,x
.endrepeat
    dex
    bpl mouse_context_restore_holes
    rts
.ifdef MOUSE_CONTEXT_DOS_ENTRY
; DOS dialogs clear their buffers in the same RAM as native mouse state.
; On //c the ROM IRQ handler owns live coordinates: retain them atomically.
mouse_context_clear_buffers:
    php
    sei
    lda mouse_context_native_mouse
    beq mouse_context_clear_start
    jsr mouse_context_capture_holes
mouse_context_clear_start:
    lda #0
    ldx #(MOUSE_CONTEXT_DOS_ROWS*8-1)
mouse_context_clear_dos_holes:
    sta mouse_context_dos_holes,x
    dex
    bpl mouse_context_clear_dos_holes
    ldy #0
    tya
mouse_context_clear_loop:
.repeat MOUSE_CONTEXT_CLEAR_PAGES, page
    sta MOUSE_CONTEXT_CLEAR_BASE + page*$100,y
.endrepeat
    iny
    bne mouse_context_clear_loop
    lda mouse_context_native_mouse
    beq mouse_context_clear_done
    jsr mouse_context_install_holes
mouse_context_clear_done:
    plp
    rts

mouse_context_file_manager:
    lda mouse_context_native_mouse
    bne mouse_context_native_file_manager
    jmp MOUSE_CONTEXT_DOS_ENTRY
mouse_context_native_file_manager:
    php
    sei
    pha
    txa
    pha
    tya
    pha
    jsr mouse_context_capture_holes
    ldx #7
mouse_context_install_dos_holes:
.repeat MOUSE_CONTEXT_DOS_ROWS, row
    lda mouse_context_dos_holes + row*8,x
    sta $0478 + row*$80,x
.endrepeat
    dex
    bpl mouse_context_install_dos_holes
    pla
    tay
    pla
    tax
    pla
    jsr MOUSE_CONTEXT_DOS_ENTRY
    sta mouse_context_result_a
    stx mouse_context_result_x
    sty mouse_context_result_y
    php
    pla
    sta mouse_context_result_p
    ldx #7
mouse_context_save_dos_holes:
.repeat MOUSE_CONTEXT_DOS_ROWS, row
    lda $0478 + row*$80,x
    sta mouse_context_dos_holes + row*8,x
.endrepeat
    dex
    bpl mouse_context_save_dos_holes
    jsr mouse_context_install_holes
    ; Retain the file manager's flags (especially carry = error), while
    ; restoring the caller's IRQ mask for the native mouse ROM handler.
    pla
    and #4
    sta mouse_context_result_i
    lda mouse_context_result_p
    and #$FB
    ora mouse_context_result_i
    pha
    ldx mouse_context_result_x
    ldy mouse_context_result_y
    lda mouse_context_result_a
    plp
    rts
.endif
.segment "BSS"
.ifdef MOUSE_CONTEXT_DOS_ENTRY
mouse_context_result_a: .res 1
mouse_context_result_x: .res 1
mouse_context_result_y: .res 1
mouse_context_result_p: .res 1
mouse_context_result_i: .res 1
.endif
mouse_context_native_mouse: .res 1
mouse_context_saved_zp: .res 256
mouse_context_firmware_holes: .res 64
.ifdef MOUSE_CONTEXT_DOS_ENTRY
mouse_context_dos_holes: .res MOUSE_CONTEXT_DOS_ROWS*8
.endif

.endif
