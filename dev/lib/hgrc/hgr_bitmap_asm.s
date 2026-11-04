; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_bitmap_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_blit_run
.exportzp _hgr_b_mask
.import _hgr_rowhi, _hgr_rowlo
.importzp _hgr_b_col, _hgr_b_h, _hgr_b_mode, _hgr_b_src, _hgr_b_stride, _hgr_b_w, _hgr_b_y
.importzp ptr1, ptr2, tmp1, tmp2, tmp3
curcol = tmp1
curmask = tmp2
curbits = tmp3

.segment "ZEROPAGE"
_hgr_b_mask:  .res 1        ; start bit mask (1 << (x % 7))

.segment "CODE"
; Pixels of one destination byte are gathered in `acc` and the mode is applied
; once per byte: each pixel is set, cleared or toggled at most once, so the
; result is the per-pixel one with a fraction of the work.
acc = ptr2
b_srcidx = ptr2+1              ; acc needs only the low scratch byte
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
        sty b_srcidx            ; srcidx = 0
        lda (_hgr_b_src),y
        sec
        rol a                   ; C = first pixel, bit 0 = end sentinel
        sta curbits             ; seven remaining source bits plus sentinel
        ldx _hgr_b_w           ; pixels this row
@px:
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
        dex                     ; stop before any source refill on the last pixel
        beq @rowdone
        asl curbits             ; C = next pixel; zero only after the sentinel
        bne @px
        inc b_srcidx            ; byte exhausted -> next source byte
        ldy b_srcidx
        lda (_hgr_b_src),y
        sec
        rol a
        sta curbits
        jmp @px
@rowdone:
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
        ldy _hgr_b_mode          ; keep acc in A through mode selection
        beq @bset
        cpy #2
        beq @bxor
        eor #$FF                ; CLEAR: dest &= ~mask (keeps the palette bit)
        ldy curcol
        and (ptr1),y
        jmp @store
@bset:
        ldy curcol              ; SET: dest |= mask
        ora (ptr1),y
        bne @store              ; acc was nonzero, so OR cannot produce zero
@bxor:
        ldy curcol              ; XOR: dest ^= mask
        eor (ptr1),y
@store:
        sta (ptr1),y
        lda #0
        sta acc
@done:  rts
