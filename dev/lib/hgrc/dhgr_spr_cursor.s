; VERHILLE Arnaud — GPL-3.0. DHGR one-pass save-under cursor (dhgr.h
; dhgr_cursor; the outside-the-area part of dhgr_spr_overlay, called by
; dhgr_spr_update through the JMP dhgr_spr_overlay.s installs). A cursor is
; w x h interleaved bytes (bx 0..79, aux even) ORed with bits; the bytes it
; covers are saved in `under` (2 x the largest w * h used), the next
; position's right after them (or at `under` again once those are free).
; One pass over old U new: each byte is read once (the saved copy when the old cursor covered it, else the screen),
; saved if the new cursor covers it, then written once: restored or ORed.
; Bytes in the excluded box (the compositor's area: groups eg0..eg1, rows
; ey0..ey1) are skipped. IRQs masked only around each banked access.
; A/X/Y, ptr1-ptr4, tmp1-tmp4 destroyed; non-reentrant, never from an IRQ.
.include "apple2.inc"
RAMWRTON = $C005
.export _dhgr_cursor, dhgr_spr_pass
.import cur_nbx, cur_ny, cur_nw, cur_nh, cur_bits, cur_under, cur_obx, cur_args, cur_take
.import _dhgr_spr_ag0, _dhgr_spr_ag1, _dhgr_spr_ay0, _dhgr_spr_ay1
.import _dhgr_base, dhgr_rowlo, dhgr_rowhi
.importzp ptr1, ptr2, ptr3, ptr4, tmp1, tmp2, tmp3, tmp4, aux_read

.bss
cur_eg0:  .res 1                ; excluded box (eg0 > eg1: none)
cur_eg1:  .res 1
cur_ey0:  .res 1
cur_ey1:  .res 1
obx = cur_obx                   ; on screen: bx, y, w, h (dhgr_spr_update.s,
oy = cur_obx + 1                ; cleared by dhgr_spr_init; ow = 0: nothing)
ow = cur_obx + 2
oh = cur_obx + 3
osave:  .res 2                  ; the half holding its saved bytes
nsave:  .res 2
ub0:    .res 1                  ; union: bytes ub0..ub1-1, rows row..uy1-1
ub1:    .res 1
row:    .res 1
uy1:    .res 1
flags:  .res 1                  ; bit 7: row in old, bit 6: row in new
xrow:   .res 1                  ; bit 7: row excluded

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; dhgr_spr_update's pass: the compositor's area excluded. Nothing to do
; when the old box (if any) and the new one (if any) lie inside the area.
dhgr_spr_pass:
        ldx #3
:       lda _dhgr_spr_ag0,x
        sta cur_eg0,x
        dex
        bpl :-
        lda ow
        beq @old
        ldx #3
:       lda obx,x               ; (obx, oy, ow, oh)
        sta tmp1,x
        dex
        bpl :-
        jsr inside
        bcc @pass
@old:   lda cur_nw
        beq @none
        lda cur_nbx
        sta tmp1
        lda cur_ny
        sta tmp2
        lda cur_nw
        sta tmp3
        lda cur_nh
        sta tmp4
        jsr inside
        bcc @pass
@none:  lda #0                  ; nothing saved outside the area
        sta ow
        rts
@pass:  jmp dhgr_cursor_core

; Box tmp1..tmp4 (bx, y, w, h) inside the excluded box: C = 1.
inside: lda tmp2
        cmp cur_ey0
        bcc @no
        clc
        adc tmp4
        sbc #0                  ; last row (C = 0: - 1)
        cmp cur_ey1
        beq :+
        bcs @no
:       lda tmp1
        lsr a
        lsr a
        cmp cur_eg0
        bcc @no
        lda tmp1
        clc
        adc tmp3
        sbc #0
        lsr a
        lsr a
        cmp cur_eg1
        beq :+
        bcs @no
:       sec
        rts
@no:    clc
        rts

; void dhgr_cursor(bx, y, w, h, bits, under): move/show (w > 0) or hide.
; Nothing excluded. under: 2 * w * h bytes; change w * h only while hidden.
_dhgr_cursor:
        jsr cur_args
        jsr cur_take
        lda #$FF
        sta cur_eg0
        lda #0
        sta cur_eg1
        ; fall through

; cur_* in, the excluded box set: one pass, then the new state.
dhgr_cursor_core:
@valid: ; where the new saved bytes go: under, or right after the old
        ; ones if they are there (under: 2 x the largest w x h used)
        lda cur_under
        ldx cur_under+1
        ldy ow
        beq @half
        cmp osave
        bne @half
        cpx osave+1
        bne @half
        ldy oh                  ; under + the old w * h
        lda #0
        clc
:       adc ow
        dey
        bne :-
        clc
        adc cur_under
        bcc @half
        inx
@half:  sta nsave
        stx nsave+1
        ; union of the old and new boxes
        lda #$FF
        sta ub0
        sta row
        lda #0
        sta ub1
        sta uy1
        lda ow
        beq @new
        lda obx
        sta ub0
        clc
        adc ow
        sta ub1
        lda oy
        sta row
        clc
        adc oh
        sta uy1
@new:   lda cur_nw
        beq @union
        lda cur_nbx
        cmp ub0
        bcs :+
        sta ub0
:       clc
        adc cur_nw
        cmp ub1
        bcc :+
        sta ub1
:       lda cur_ny
        cmp row
        bcs :+
        sta row
:       clc
        adc cur_nh
        cmp uy1
        bcc @union
        sta uy1
@union: lda row
        cmp uy1
        bcc rows
        jmp done

; One row: flags, the excluded part, the screen row, three row pointers
; biased by -bx so that Y = b indexes them.
rows:   lda #0
        sta flags
        ldx ow
        beq @newrow
        lda row
        sec
        sbc oy
        cmp oh
        bcs @newrow
        tax                     ; ptr2 = osave + r * ow - obx
        lda osave
        ldy osave+1
        jsr times_ow
        sta ptr2
        sty ptr2+1
        lda #$80
        sta flags
@newrow:
        ldx cur_nw
        beq @rowok
        lda row
        sec
        sbc cur_ny
        cmp cur_nh
        bcs @rowok
        sta tmp4
        tax                     ; ptr3 = nsave + r * w - bx
        lda nsave
        ldy nsave+1
        jsr times_nw
        sta ptr3
        sty ptr3+1
        ldx tmp4                ; ptr4 = bits + r * w - bx
        lda cur_bits
        ldy cur_bits+1
        jsr times_nw
        sta ptr4
        sty ptr4+1
        lda flags
        ora #$40
        sta flags
@rowok: lda flags
        bne :+
        jmp next_row
:       lda #0
        sta xrow
        lda row
        cmp cur_ey0
        bcc :+
        lda cur_ey1
        cmp row
        bcc :+
        lda #$80
        sta xrow
:       ldx row
        lda dhgr_rowlo,x
        sta ptr1
        lda dhgr_rowhi,x
        ora _dhgr_base
        sta ptr1+1
        ldx ub0                 ; X = b, the byte
bytes:  lda #0                  ; tmp1 bit 7: old covers b, bit 6: new does
        sta tmp1
        bit flags
        bpl @notold
        txa
        sec
        sbc obx
        cmp ow
        bcs @notold
        lda #$80
        sta tmp1
@notold:
        bit flags
        bvc @notnew
        txa
        sec
        sbc cur_nbx
        cmp cur_nw
        bcs @notnew
        lda tmp1
        ora #$40
        sta tmp1
@notnew:
        lda tmp1
        beq next_byte
        bit xrow                ; in the excluded box: the compositor's
        bpl @in
        txa
        lsr a
        lsr a
        cmp cur_eg0
        bcc @in
        cmp cur_eg1
        beq next_byte
        bcc next_byte
@in:    txa
        tay
        bit tmp1                ; the byte under the cursor(s)
        bpl @screen
        lda (ptr2),y            ; saved by the old one
        jmp @base
@screen:
        lsr a
        tay
        bcs @main
        php
        sei
        jsr aux_read
        plp
        jmp @read
@main:  lda (ptr1),y
@read:  and #$7F
@base:  bit tmp1
        bvc @write
        sta tmp2
        txa
        tay
        lda tmp2
        sta (ptr3),y            ; saved for the new one
        lda (ptr4),y
        and #$7F
        ora tmp2
@write: sta tmp2
        txa
        lsr a
        tay
        lda tmp2
        bcs @wmain
        php
        sei
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        plp
        jmp next_byte
@wmain: sta (ptr1),y
next_byte:
        inx
        cpx ub1
        bcs next_row
        jmp bytes
next_row:
        inc row                 ; (rows between two boxes: jump to the next)
        lda #$FF
        sta tmp1
        ldx ow
        beq @new
        lda row
        sec
        sbc oy
        cmp oh
        bcc @go                 ; in the old box
        lda oy
        cmp row
        bcc @new
        sta tmp1
@new:   ldx cur_nw
        beq @next
        lda row
        sec
        sbc cur_ny
        cmp cur_nh
        bcc @go
        lda cur_ny
        cmp row
        bcc @next
        cmp tmp1
        bcs @next
        sta tmp1
@next:  lda tmp1
        sta row
@go:    lda row
        cmp uy1
        bcs done
        jmp rows
done:   lda cur_nw              ; the new state
        sta ow
        lda cur_nbx
        sta obx
        lda cur_ny
        sta oy
        lda cur_nh
        sta oh
        lda nsave
        sta osave
        lda nsave+1
        sta osave+1
        rts

; A/Y = base, X = r: A/Y = base + r * w - bx (old: ow, obx; new: nw, nbx).
times_ow:
        sta tmp2
        lda ow
        sta tmp3
        lda obx
        jmp times
times_nw:
        sta tmp2
        lda cur_nw
        sta tmp3
        lda cur_nbx
times:  eor #$FF                ; base - bx
        sec
        adc tmp2
        bcs :+
        dey
:       cpx #0
        beq @done
@add:   clc
        adc tmp3
        bcc :+
        iny
:       dex
        bne @add
@done:  rts

