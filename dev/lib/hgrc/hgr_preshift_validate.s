; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Internal validation shared by the two public preshifted-sprite entries.
; Inputs: ptr2 = hgr_xs_spr, X = C-stack offset of y then x; rows already built.
; Outputs: hgr_xs_x/y when valid; C=0 valid, C=1 rejected.
; Clobbers A/Y and flags; preserves tmp4 (general entry's mode).
; Does not initialize columns/phases or call a worker on rejected input.
.export _hgr_xs_validate
.importzp sp, ptr2, _hgr_xs_x, _hgr_xs_y
.code
_hgr_xs_validate:
        ldy #2
        lda (ptr2),y            ; stride (descriptor ABI: bits pointer, stride, h)
        beq outside
        iny
        lda (ptr2),y
        beq outside
        txa                     ; reject empty descriptors before copying x/y
        tay
        lda (sp),y
        cmp #192
        bcs outside
        sta _hgr_xs_y
        iny
        lda (sp),y
        sta _hgr_xs_x
        iny
        lda (sp),y
        sta _hgr_xs_x+1
        beq inside
        cmp #1
        bne outside
        lda _hgr_xs_x
        cmp #24                 ; valid iff x < 280
        rts
inside:
        clc
        rts
outside:
        sec
        rts
