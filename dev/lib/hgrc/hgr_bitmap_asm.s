; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_bitmap_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_blit_run
.exportzp _hgr_b_mask
.import _hgr_rowhi, _hgr_rowlo
.importzp _hgr_b_col, _hgr_b_h, _hgr_b_mode, _hgr_b_src, _hgr_b_stride, _hgr_b_w, _hgr_b_y
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_b_mask:  .res 1        ; start bit mask (1 << (x % 7))
b_srcidx:      .res 1        ; source byte index within the current row

.segment "CODE"
; Pixels of one destination byte are gathered in `acc` and the mode is applied
; once per byte: each pixel is set, cleared or toggled at most once, so the
; result is the per-pixel one with a fraction of the work.
acc = ptr2
_hgr_blit_run:
@row:
        ldy _hgr_b_y           ; ptr1 = scanline base
        lda _hgr_rowlo,y
        sta ptr1
        lda _hgr_rowhi,y
        sta ptr1+1
        lda _hgr_b_col         ; reset pen to the sprite's left edge
        sta curcol
        lda _hgr_b_mask
        sta curmask
        ldy #0                  ; load first source byte of this row
        sty acc
        lda (_hgr_b_src),y
        sta tmp3                ; srcbits (MSB-first shift register)
        lda #8
        sta tmp4                ; bits left in srcbits
        sty b_srcidx            ; srcidx = 0
        ldx _hgr_b_w           ; pixels this row
@px:
        asl tmp3                ; C = next pixel (bit 7 first)
        bcc @advance
        lda acc
        ora curmask
        sta acc
@advance:
        asl curmask             ; bit 6 passed: byte complete, next column
        bpl @consumed
        jsr apply
        lda #$01
        sta curmask
        inc curcol
@consumed:
        dec tmp4                ; consumed a source bit
        bne @next
        cpx #1                  ; final pixel: no next byte is needed
        beq @next               ; keep reads within the source row
        inc b_srcidx            ; byte exhausted -> next source byte
        ldy b_srcidx
        lda (_hgr_b_src),y
        sta tmp3
        lda #8
        sta tmp4
@next:
        dex
        bne @px
        jsr apply               ; partial last byte
        clc                     ; next source row + next scanline
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

; Apply `acc` at column curcol on scanline ptr1 (SET/CLEAR/XOR), clear it.
apply:
        lda acc
        beq @done
        ldy curcol
        lda _hgr_b_mode
        beq @bset
        cmp #2
        beq @bxor
        lda acc                 ; CLEAR: dest &= ~mask (keeps the palette bit)
        eor #$FF
        and (ptr1),y
        sta (ptr1),y
        jmp @clear
@bset:
        lda acc                 ; SET: dest |= mask
        ora (ptr1),y
        sta (ptr1),y
        jmp @clear
@bxor:
        lda acc                 ; XOR: dest ^= mask
        eor (ptr1),y
        sta (ptr1),y
@clear: lda #0
        sta acc
@done:  rts
