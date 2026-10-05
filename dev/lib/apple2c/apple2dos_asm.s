; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2dos_asm.s — DOS 3.3 commands for cc65 (see apple2dos.h).
;
; Thin wrappers over ../apple2/dos.asm. DOS's page zero is the snapshot
; crt0_apple2.s takes at start (exported there as apple2_zp_buf). A separate
; object: it brings 256 + 41 bytes of BSS that only programs using DOS
; need. Assemble with -I dev/lib/apple2.
; ----------------------------------------------------------------------------
        .export _a2_dos_new, _a2_dos_add, _a2_dos_hex, _a2_dos_run
        .export _a2_dos_cmd, _a2_disk_protected
        .import apple2_zp_buf

.include "apple2.inc"
.include "dos.asm"

        .segment "CODE"

_a2_dos_new:
        jmp     dos_cmd_new

; void a2_dos_add(const char *s): s in A (lo) / X (hi).
_a2_dos_add:
        pha
        txa
        tay
        pla
        jmp     dos_cmd_add

_a2_dos_hex:
        jmp     dos_cmd_hex

_a2_dos_run:
        jmp     dos_cmd_run

; void a2_dos_cmd(const char *cmd): new + add + run.
_a2_dos_cmd:
        pha
        txa
        pha
        jsr     dos_cmd_new     ; clobbers A only
        pla
        tay
        pla
        jsr     dos_cmd_add
        jmp     dos_cmd_run

; unsigned char a2_disk_protected(void): 1 if the slot 6 disk is protected.
_a2_disk_protected:
        jsr     disk_protected
        lda     #0
        rol     a
        ldx     #0
        rts
