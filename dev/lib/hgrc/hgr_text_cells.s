; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Internal fastcall: room in A/X, 0..264 -> floor(room/18)+1 in A, X=0.
; Standalone helper; the native text entry inlines its bounded count. D=0. No memory or IRQ changes.
.export _hgr_text16_cells
.code
_hgr_text16_cells:
        cpx #1
        bcs @maximum            ; 256..264 all fit fifteen cells
        ; X is already zero: count each successful subtraction plus one.
        sec
@count: inx
        sbc #18
        bcs @count
        txa
        ldx #0
        rts
@maximum:
        lda #15
        ldx #0
        rts
