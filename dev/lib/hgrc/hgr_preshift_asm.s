; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_preshift_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_preshift_xor_run, _hgr_xs_run
.exportzp _hgr_xs_x, _hgr_xs_y, _hgr_xs_spr
.import _hgr_col7, _hgr_phase7, _hgr_rowhi, _hgr_rowlo
.import _hgr_build_columns, _hgr_build_phases
.importzp _hgr_b_col, _hgr_b_h, _hgr_b_src, _hgr_b_stride, _hgr_b_w, _hgr_b_y
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_xs_x:    .res 2        ; pixel x (0..279)
_hgr_xs_y:    .res 1        ; pixel y (0..191)
_hgr_xs_spr:  .res 2        ; pointer to the hgr_sprite_t {bits, stride, h}

.segment "CODE"
_hgr_xs_run:
        jsr _hgr_build_columns
        jsr _hgr_build_phases
        ; col = hgr_col7[x] -> _hgr_b_col ; phase = hgr_phase7[x] -> tmp1
        lda _hgr_xs_x+1
        bne @xhi
        ldx _hgr_xs_x
        lda _hgr_col7,x
        ldy _hgr_phase7,x
        jmp @xset
@xhi:
        ldx _hgr_xs_x
        lda _hgr_col7+256,x
        ldy _hgr_phase7+256,x
@xset:
        sta _hgr_b_col
        sty tmp1                  ; tmp1 = phase (0..6)
        ; deref spr -> ptr2 ; read bits/stride/h
        lda _hgr_xs_spr
        sta ptr2
        lda _hgr_xs_spr+1
        sta ptr2+1
        ldy #0
        lda (ptr2),y              ; bits low
        sta _hgr_b_src
        iny
        lda (ptr2),y              ; bits high
        sta _hgr_b_src+1
        iny
        lda (ptr2),y              ; stride
        sta _hgr_b_stride
        sta _hgr_b_w             ; default w = stride
        sta tmp2                  ; tmp2 = stride
        iny
        lda (ptr2),y              ; h
        sta _hgr_b_h             ; default h
        sta tmp3                  ; tmp3 = full h (for the phase offset)
        lda _hgr_xs_y
        sta _hgr_b_y
        ; right clip: col + stride > 40 ? w = 40 - col
        lda _hgr_b_col
        clc
        adc tmp2
        bcs @clipw                ; col+stride >= 256 still exceeds the row
        cmp #41
        bcc @wok
@clipw:
        lda #40
        sec
        sbc _hgr_b_col
        sta _hgr_b_w
@wok:
        ; bottom clip: y + h > 192 ? h = 192 - y
        lda _hgr_xs_y
        clc
        adc tmp3
        bcs @clipb                ; y+h >= 256 -> clip
        cmp #193
        bcc @hok
@clipb:
        lda #192
        sec
        sbc _hgr_xs_y
        sta _hgr_b_h
@hok:
        ; src += phase * (h * stride). phaseblock = h*stride via loop-add -> ptr1
        lda #0
        sta ptr1
        sta ptr1+1
        ldx tmp3                  ; full h
@hloop:
        clc
        lda ptr1
        adc tmp2                  ; + stride
        sta ptr1
        bcc @h2
        inc ptr1+1
@h2:
        dex
        bne @hloop
        ldx tmp1                  ; phase
        beq @offdone
@ploop:
        clc
        lda _hgr_b_src
        adc ptr1
        sta _hgr_b_src
        lda _hgr_b_src+1
        adc ptr1+1
        sta _hgr_b_src+1
        dex
        bne @ploop
@offdone:
        ; fall through into the XOR row loop below.

; --- _hgr_preshift_xor_run : dedicated XOR blit for the pre-shift engine -------
; Same as _hgr_blit7_run but mode is hardwired to XOR, so the per-byte mode
; dispatch (ldx _hgr_b_mode / beq / cpx #2 / beq) is gone: the inner loop is the
; Buzzard-Bait minimum -- lda (src),y / eor (dst),y / sta (dst),y (~24 cyc/byte
; vs ~34 for the general path). hgr_sprite() calls this for HGR_XOR (the hot
; animation path) so an erase+redraw pair fits inside V-blank; SET/CLEAR still go
; through _hgr_blit7_run. Same hgr_b_* zero-page block.
_hgr_preshift_xor_run:
@row:
        ldy _hgr_b_y           ; ptr1 = rowbase(y) + col
        lda _hgr_rowlo,y
        clc
        adc _hgr_b_col
        sta ptr1
        lda _hgr_rowhi,y
        adc #0
        sta ptr1+1
        ldy #0                  ; Y indexes src[j] AND dest[col+j] together
@col:
        lda (_hgr_b_src),y     ; pre-shifted source byte
        eor (ptr1),y            ; dest ^= src  (no mode test)
        sta (ptr1),y
        iny
        cpy _hgr_b_w
        bne @col
        clc                     ; src += stride ; y += 1 ; rows--
        lda _hgr_b_src
        adc _hgr_b_stride
        sta _hgr_b_src
        bcc @nyc
        inc _hgr_b_src+1
@nyc:
        inc _hgr_b_y
        dec _hgr_b_h
        bne @row
        rts
