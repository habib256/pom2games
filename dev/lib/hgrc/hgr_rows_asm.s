; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_rows_asm.s — HGR scanline-table page flip for hgr_init.c (its own
; archive member: only HGR programs, which own hgr_rowhi, link it).
.export _hgr_flip_rows
.import _hgr_rowhi

.segment "CODE"
; void hgr_flip_rows(void): move the 192 scanline high bytes to the other
; HGR page. $20..$3F EOR $60 = $40..$5F and back. ~3 400 cycles (the compiled
; byte-add loop it replaces took ~16 000, about one frame per flip).
_hgr_flip_rows:
        ldx     #191
@lp:    lda     _hgr_rowhi,x
        eor     #$60
        sta     _hgr_rowhi,x
        dex
        cpx     #$FF            ; 191 > 127: BPL would stop at once
        bne     @lp
        rts
