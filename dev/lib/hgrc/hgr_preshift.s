; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_sprite(unsigned x, byte y, sprite*, byte mode), cc65 fastcall.
; The seven precomputed phases give pixel-precise placement with byte copies.
; The worker selects x/7, x%7 and the phase offset, then clips the dimensions.
; Data ABI: hgr.h. Only existing worker parameters and cc65 scratch are used.
.export _hgr_sprite
.import _hgr_build_rows, _hgr_xs_validate, _hgr_xs_setup, _hgr_preshift_xor_run, _hgr_blit7_run, incsp5
.importzp sp, ptr2, tmp4, _hgr_xs_spr, _hgr_b_mode
.code
_hgr_sprite:
        sta tmp4                ; builders, validate and setup preserve mode
        jsr _hgr_build_rows     ; rejected calls still initialize rows only
        ldy #0
        lda (sp),y
        sta _hgr_xs_spr
        sta ptr2
        iny
        lda (sp),y
        sta _hgr_xs_spr+1
        sta ptr2+1
        ldx #2                  ; stack offset of y, followed by x
        jsr _hgr_xs_validate
        bcs done
        jsr _hgr_xs_setup
        lda tmp4
        cmp #2
        beq xor
        sta _hgr_b_mode
        jsr _hgr_blit7_run
        jmp incsp5
xor:
        jsr _hgr_preshift_xor_run
done:
        jmp incsp5
