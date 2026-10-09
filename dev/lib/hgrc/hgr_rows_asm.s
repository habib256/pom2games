; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_rows_asm.s — HGR scanline-table page flip for hgr_init.c (its own
; archive member: only HGR programs, which own hgr_rowhi, link it).
.export _hgr_flip_rows
.import _hgr_rowhi

.segment "CODE"
; void hgr_flip_rows(void): move the 192 scanline high bytes to the other
; HGR page. $20..$3F EOR $60 = $40..$5F and back. Eight rows per iteration:
; removes 7/8 of loop overhead without changing table ABI, RAM or ZP.
_hgr_flip_rows:
        ldx     #23
@lp:    lda     _hgr_rowhi,x
        eor     #$60
        sta     _hgr_rowhi,x
        .repeat 7, block
        lda     _hgr_rowhi+24*(block+1),x
        eor     #$60
        sta     _hgr_rowhi+24*(block+1),x
        .endrepeat
        dex
        bpl     @lp
        rts
