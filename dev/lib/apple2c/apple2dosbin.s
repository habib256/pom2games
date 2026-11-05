; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2dosbin.s — a2_dos_bload() / a2_dos_bsave() for cc65 (apple2dos.h).
;
; "BLOAD NAME,A$hhhh" / "BSAVE NAME,A$hhhh,L$hhhh" built and run with the
; a2_dos_* calls of apple2dos_asm.s (link both). A separate object
; (APPLE2C_DOSBIN_SRCS): only the programs that call it pay for it.
; 6502; borrows cc65 ptr2/ptr3/tmp1 before tail-calling DOS.
; popax and the new/add/hex builders preserve this scratch. It is dead
; before a2_dos_run can invoke DOS/COUT and swap page zero.
; ----------------------------------------------------------------------------
        .export _a2_dos_bload, _a2_dos_bsave
        .import _a2_dos_new, _a2_dos_add, _a2_dos_hex, _a2_dos_run
        .import popax

        .importzp ptr2, ptr3, tmp1
bin_addr = ptr2
bin_len = ptr3
bin_save = tmp1

        .segment "CODE"
; void __fastcall__ a2_dos_bsave(const char *name, void *addr, unsigned len)
_a2_dos_bsave:
        sta     bin_len
        stx     bin_len+1
        jsr     popax           ; addr
        ldy     #1
        bne     bin
; void __fastcall__ a2_dos_bload(const char *name, void *addr)
_a2_dos_bload:
        ldy     #0
bin:    sty     bin_save
        sta     bin_addr
        stx     bin_addr+1
        jsr     _a2_dos_new     ; clobbers A only
        lda     #<s_bload
        ldx     #>s_bload
        ldy     bin_save
        beq     :+
        lda     #<s_bsave
        ldx     #>s_bsave
:       jsr     _a2_dos_add
        jsr     popax           ; name
        jsr     _a2_dos_add
        lda     #<s_addr
        ldx     #>s_addr
        jsr     _a2_dos_add
        lda     bin_addr+1
        jsr     _a2_dos_hex
        lda     bin_addr
        jsr     _a2_dos_hex
        lda     bin_save
        beq     @run
        lda     #<s_len
        ldx     #>s_len
        jsr     _a2_dos_add
        lda     bin_len+1
        jsr     _a2_dos_hex
        lda     bin_len
        jsr     _a2_dos_hex
@run:   jmp     _a2_dos_run

        .segment "RODATA"
s_bload:        .asciiz "BLOAD "
s_bsave:        .asciiz "BSAVE "
s_addr:         .asciiz ",A$"
s_len:          .asciiz ",L$"
