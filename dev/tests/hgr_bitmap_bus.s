; Standalone bitmap kernel fixture: parameters supplied by the host bus probe.
.import _hgr_blit_run
.export _hgr_rowlo, _hgr_rowhi
.exportzp _hgr_b_col, _hgr_b_h, _hgr_b_mode, _hgr_b_src
.exportzp _hgr_b_stride, _hgr_b_w, _hgr_b_y, ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
.zeropage
_hgr_b_col: .res 1
_hgr_b_h: .res 1
_hgr_b_mode: .res 1
_hgr_b_src: .res 2
_hgr_b_stride: .res 1
_hgr_b_w: .res 1
_hgr_b_y: .res 1
ptr1: .res 2
ptr2: .res 2
tmp1: .res 1
tmp2: .res 1
tmp3: .res 1
tmp4: .res 1
.importzp _hgr_b_mask
.code
entry:
    lda $1000
    sta _hgr_b_w
    lda $1001
    sta _hgr_b_h
    lda $1002
    sta _hgr_b_stride
    lda #0
    sta _hgr_b_y
    sta _hgr_b_mode
    sta _hgr_b_col
    sta _hgr_b_src
    lda #$90
    sta _hgr_b_src+1
    lda #1
    sta _hgr_b_mask
    jsr _hgr_blit_run
    lda #1
    sta $1003
@done: jmp @done
_hgr_rowlo:
.repeat 192, I
.byte <($2000+(I .mod 8)*$400+((I/8) .mod 8)*$80+(I/64)*$28)
.endrepeat
_hgr_rowhi:
.repeat 192, I
.byte >($2000+(I .mod 8)*$400+((I/8) .mod 8)*$80+(I/64)*$28)
.endrepeat
