; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; unsigned char * __fastcall__ hgr_row(unsigned char y)
.export _hgr_row
.import _hgr_build_rows, _hgr_rowlo, _hgr_rowhi
.importzp tmp2
.code
_hgr_row:
        cmp #192
        bcs outside
        sta tmp2
        jsr _hgr_build_rows
        ldy tmp2
        ldx _hgr_rowhi,y
        lda _hgr_rowlo,y
        rts
outside:
        lda #0
        tax
        rts
