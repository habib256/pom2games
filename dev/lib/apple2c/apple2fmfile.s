; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ----------------------------------------------------------------------------
; apple2fmfile.s — whole DOS 3.3 binary files for cc65 (see apple2fm.h):
; a2_fm_load() / a2_fm_save(), the error-returning BLOAD / BSAVE.
;
; Self-contained over ../apple2/fm.asm (its own copy of the file manager
; calls): for a program that only loads and saves whole files, without the
; open / read / write API of apple2fm.s (APPLE2C_FM_FILE_SRCS instead of
; APPLE2C_FM_SRCS; linking both works but duplicates ~400 bytes).
; Assemble with $(APPLE2C_AFLAGS); -D FM_SEI=1 if interrupts are enabled.
; ----------------------------------------------------------------------------
        .export _a2_fm_load, _a2_fm_save
        .import popax

        .segment "BSS"
ld_buf: .res 2
ld_len: .res 2

        .segment "CODE"

; unsigned char __fastcall__ a2_fm_save(const char *name, const void *buf,
;                                       unsigned len)
; BSAVE name,A buf,L len: the file is created if missing.
_a2_fm_save:
        sta     fm_hdr+2
        stx     fm_hdr+3
        jsr     popax           ; buf: also the header's load address
        sta     fm_hdr
        stx     fm_hdr+1
        jsr     popax           ; name
        jsr     ax_ay
        jsr     fm_bsave
        ldx     #0
        rts

; unsigned char __fastcall__ a2_fm_load(const char *name, void *buf,
;                                       unsigned len)
; The first len data bytes of a binary file into buf (its 4-byte header is
; skipped: the file's own load address is not used). The file must exist.
_a2_fm_load:
        sta     ld_len
        stx     ld_len+1
        jsr     popax
        sta     ld_buf
        stx     ld_buf+1
        jsr     popax           ; name
        jsr     ax_ay
        ldx     #FM_MUST_EXIST
        jsr     fm_open
        bcs     ret
        jsr     fm_hdr4         ; the header, into fm_hdr
        jsr     fm_read
        bcs     end
        lda     ld_len
        sta     fm_len
        lda     ld_len+1
        sta     fm_len+1
        lda     ld_buf
        ldy     ld_buf+1
        jsr     fm_read
end:    jsr     fm_bend         ; close; the first error wins
ret:    ldx     #0
        rts

; A/X (cc65) -> A/Y (fm.asm).
ax_ay:  pha
        txa
        tay
        pla
        rts

; fm.asm emits its routines only when referenced before inclusion.
.include "fm.asm"
