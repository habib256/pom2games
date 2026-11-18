; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2fm.s — DOS 3.3 file manager for cc65 (see apple2fm.h).
;
; Thin wrappers over ../apple2/fm.asm: each returns fm.asm's code in A
; (X = 0); a2_fm_open turns "created" (C = 0, A = 6) into A2_FM_CREATED (1).
; A separate object (APPLE2C_FM_SRCS): only the programs that use files
; pay for it. Assemble with $(APPLE2C_AFLAGS) (-I dev/lib/apple2);
; -D FM_SEI=1 for a program that enables interrupts.
; ----------------------------------------------------------------------------
        .export _a2_fm_open, _a2_fm_read, _a2_fm_write, _a2_fm_seek
        .export _a2_fm_close, _a2_fm_delete, _a2_fm_lock, _a2_fm_unlock
        .export _a2_fm_verify
        .export _a2_fm_file, _a2_fm_type, _a2_fm_slot, _a2_fm_drive
        .import popax

        .segment "CODE"

; unsigned char __fastcall__ a2_fm_open(const char *name, unsigned char type)
_a2_fm_open:
        sta     fm_type         ; type (fm_open stores X there too)
        jsr     popax           ; name
        jsr     ax_ay
        ldx     fm_type
        jsr     fm_open
        bcs     ret
        cmp     #FM_ERR_NOT_FOUND
        bne     ret             ; A = 0: the file was there
        lda     #1              ; A2_FM_CREATED
ret:    ldx     #0
        rts

; unsigned char __fastcall__ a2_fm_read(void *buf, unsigned len)
_a2_fm_read:
        jsr     len_buf
        jsr     fm_read
        ldx     #0
        rts

; unsigned char __fastcall__ a2_fm_write(const void *buf, unsigned len)
_a2_fm_write:
        jsr     len_buf
        jsr     fm_write
        ldx     #0
        rts

; unsigned char __fastcall__ a2_fm_seek(unsigned pos)
_a2_fm_seek:
        jsr     ax_ay
        jsr     fm_seek
        ldx     #0
        rts

; unsigned char a2_fm_close(void)
_a2_fm_close:
        jsr     fm_close
        ldx     #0
        rts

; unsigned char __fastcall__ a2_fm_delete / lock / unlock / verify(name)
_a2_fm_delete:
        jsr     ax_ay
        jsr     fm_delete
        ldx     #0
        rts
_a2_fm_lock:
        jsr     ax_ay
        jsr     fm_lock
        ldx     #0
        rts
_a2_fm_unlock:
        jsr     ax_ay
        jsr     fm_unlock
        ldx     #0
        rts
_a2_fm_verify:
        jsr     ax_ay
        jsr     fm_verify
        ldx     #0
        rts

; fm_len = A/X, then A/Y = the pointer popped from the C stack.
len_buf:
        sta     fm_len
        stx     fm_len+1
        jsr     popax
        ; falls into ax_ay
; A/X (cc65) -> A/Y (fm.asm).
ax_ay:  pha
        txa
        tay
        pla
        rts

; fm.asm emits its routines only when referenced before inclusion.
.include "fm.asm"

_a2_fm_file  = fm_file
_a2_fm_type  = fm_type
_a2_fm_slot  = fm_slot
_a2_fm_drive = fm_drive
