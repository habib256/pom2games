; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_sprite_xor(unsigned x, byte y, sprite*), cc65 fastcall.
; Separate archive member: XOR-only clients omit the general mode entry.
.export _hgr_sprite_xor
.import _hgr_build_rows, _hgr_xs_validate, _hgr_xs_setup, _hgr_preshift_xor_run, incsp3
.importzp ptr2, _hgr_xs_spr
.code
_hgr_sprite_xor:
        sta _hgr_xs_spr
        sta ptr2
        stx _hgr_xs_spr+1
        stx ptr2+1
        jsr _hgr_build_rows     ; preserves ptr2 for validation
        ldx #0                  ; stack offset of y, followed by x
        jsr _hgr_xs_validate
        bcs done
        jsr _hgr_xs_setup
        jsr _hgr_preshift_xor_run
done:
        jmp incsp3
