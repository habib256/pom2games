; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_blit7_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
; Both entries require clipped parameters: 1 <= hgr_b_w <= 40,
; hgr_b_col+hgr_b_w <= 40 and 1 <= hgr_b_h <= 192-hgr_b_y.
.export _hgr_blit7_run, _hgr_preshift_xor_run
.import _hgr_rowhi, _hgr_rowlo
.importzp _hgr_b_col, _hgr_b_h, _hgr_b_mode, _hgr_b_src, _hgr_b_stride, _hgr_b_w, _hgr_b_y
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "CODE"
.macro  BLIT7_LOOP m
        .local  row, col, nyc
row:    ldy     _hgr_b_y               ; ptr1 = rowbase(y) + col
        lda     _hgr_rowlo,y
        clc
        adc     _hgr_b_col
        sta     ptr1
        lda     _hgr_rowhi,y
        ; A visible row starts at low offset <= $D0; col <= 39, so
        ; adding the clipped column never carries into the high byte.
        sta     ptr1+1
        ldy     _hgr_b_w                 ; clipped width <=40: Y is offset and counter
        dey
col:    lda     (_hgr_b_src),y
.if m = 1
        eor     #$FF                    ; CLEAR: dest &= ~src
        and     (ptr1),y
.elseif m = 2
        eor     (ptr1),y                ; XOR: dest ^= src
.else
        ora     (ptr1),y                ; SET: dest |= src
.endif
        sta     (ptr1),y
        dey
        bpl     col
        clc                             ; src += stride ; y += 1 ; rows--
        lda     _hgr_b_src
        adc     _hgr_b_stride
        sta     _hgr_b_src
        bcc     nyc
        inc     _hgr_b_src+1
nyc:    inc     _hgr_b_y
        dec     _hgr_b_h
        bne     row
        rts
.endmacro

_hgr_blit7_run:
        lda     _hgr_b_mode
        beq     blit7_set               ; 0 = SET
        cmp     #2
        beq     blit7_xor               ; 2 = XOR
        BLIT7_LOOP 1                     ; 1 = CLEAR (fall-through)
blit7_set:
        BLIT7_LOOP 0
; _hgr_preshift_xor_run: the XOR loop entered directly, for the pre-shift engine
; (hgr_sprite's HGR_XOR hot path and hgr_xs_run): no mode test per call; the
; inner loop is lda (src),y / eor (dst),y / sta (dst),y, ~21 cycles a byte.
_hgr_preshift_xor_run:
blit7_xor:
        BLIT7_LOOP 2
