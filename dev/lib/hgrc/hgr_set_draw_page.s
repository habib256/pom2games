; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; void __fastcall__ hgr_set_draw_page(unsigned char page)
; Select page 2 only for argument 2; every other byte selects page 1.
; Always prepare HGR rows, then shift their high bytes synchronously on change.
; LORES rows stay lazy; existing ones toggle between high bytes 4..7 and 8..11.
; No display soft switch, C stack, new ZP or mutable DATA. Clobbers A/X/Y/tmp1/tmp2.
.export _hgr_set_draw_page
.import _hgr_build_rows, _hgr_flip_rows, _hgr_base, _hgr_draw_page2
.import _hgr_lo_base, _hgr_lo_ready, _hgr_lo_rowhi
.importzp tmp2
.code
_hgr_set_draw_page:
        ldx #0
        cmp #2
        bne normalized
        inx
normalized:
        stx tmp2                ; hgr_build_rows preserves tmp2
        jsr _hgr_build_rows
        lda tmp2
        sta _hgr_draw_page2
        beq page1
        ldy #8
        lda #$40
        bne selected
page1:
        ldy #4
        lda #$20
selected:
        cmp _hgr_base
        beq hires_ready
        sta tmp2
        jsr _hgr_flip_rows      ; preserves Y and tmp2
        lda tmp2
        sta _hgr_base
hires_ready:
        lda _hgr_lo_ready
        beq store_base
        tya
        cmp _hgr_lo_base
        beq done
        ldx #23
lores_row:
        lda _hgr_lo_rowhi,x
        eor #$0c                ; $04..$07 <-> $08..$0b; row offset unchanged
        sta _hgr_lo_rowhi,x
        dex
        bpl lores_row
store_base:
        sty _hgr_lo_base
done:
        rts
