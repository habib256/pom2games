; VERHILLE Arnaud — GPL-3.0. DHGR compositor overlay (dhgr.h
; dhgr_spr_overlay): a byte-domain OR layer above the sprites (a pointer).
; dhgr_spr_overlay records the wanted box and installs JMPs into
; dhgr_spr_update (dhgr_spr_update.s): the overlay's old and new boxes into
; the damage, then per row / per group of a piece the OR of its bits; the
; part outside the area goes to dhgr_spr_cursor.s's one-pass save-under,
; unless DHGR_SPR_OVERLAY_INSIDE=1: then only the part inside the area is
; ever drawn, `under` is not used and dhgr_spr_cursor.s is not linked.
; A/X/Y, ptr1, tmp1-tmp4 destroyed; non-reentrant, never from an IRQ.
; DHGR_SPR_CODE_SEGMENT=1: code and tables in segment DHGRSPRCODE.
.export _dhgr_spr_overlay, cur_args, cur_take
.import cur_nbx, cur_ny, cur_nw, cur_nh, cur_bits, cur_under
.import _dhgr_spr_v_dirty, _dhgr_spr_cur_jmp, _dhgr_spr_ov_on, _dhgr_spr_add
.import _dhgr_spr_w_g0, w_g1, w_y0, w_y1, spr_row, spr_ovhook
.import _dhgr_spr_rg0, _dhgr_spr_rg1, _dhgr_spr_ry0, _dhgr_spr_ry1
.import _dhgr_spr_goff, _dhgr_spr_gend, popa, popax
INSIDE .set 0
.if .defined(DHGR_SPR_OVERLAY_INSIDE)
.if DHGR_SPR_OVERLAY_INSIDE
INSIDE .set 1
.endif
.endif
.if !INSIDE
.import dhgr_spr_pass
.endif
.importzp ptr1, tmp1, tmp2, tmp3, tmp4

.bss
t_bx:   .res 1                  ; arguments (cur_args), as cur_n*
t_y:    .res 1
t_w:    .res 1
t_h:    .res 1
t_bits: .res 2
t_under: .res 2
ob:     .res 4                  ; ov_group: b0..b3
xsave:  .res 1
NONE = $FF

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; Pop (bx, y, w, h, bits, under) into t_*; w = 0 unless the box is on the
; screen with w * h <= 127. For dhgr_cursor and dhgr_spr_overlay.
cur_args:
        sta t_under
        stx t_under+1
        jsr popax
        sta t_bits
        stx t_bits+1
        jsr popa
        sta t_h
        jsr popa
        sta t_w
        jsr popa
        sta t_y
        jsr popa
        sta t_bx
        lda t_w
        beq @ok
        lda t_bx
        cmp #80
        bcs @hide
        adc t_w                 ; (C = 0)
        cmp #81
        bcs @hide
        lda t_y
        cmp #192
        bcs @hide
        adc t_h
        bcs @hide
        cmp #193
        bcs @hide
        ldx t_h
        beq @hide
        lda #0
:       clc
        adc t_w
        bcs @hide
        dex
        bne :-
        cmp #128
        bcc @ok
@hide:  lda #0
        sta t_w
@ok:    rts

; t_* -> cur_n* (the wanted cursor).
cur_take:
        ldx #7
:       lda t_bx,x
        sta cur_nbx,x
        dex
        bpl :-
        rts

; void dhgr_spr_overlay(bx, y, w, h, bits, under): the wanted overlay,
; applied by dhgr_spr_update (in the area: recomposed; outside: pass below).
_dhgr_spr_overlay:
        jsr cur_args
        lda t_w                 ; both hidden, or the same: nothing to do
        ora cur_nw
        beq @same
        ldx #5
:       lda t_bx,x
        cmp cur_nbx,x
        bne @new
        dex
        bpl :-
@same:  rts
@new:   jsr cur_take
        lda #1
        sta _dhgr_spr_v_dirty
        ldx #11                 ; dhgr_spr_update's overlay entries
:       lda vectors,x
        sta _dhgr_spr_cur_jmp,x
        dex
        bpl :-
        rts

; dhgr_spr_update: the overlay's old and new boxes into the damage.
ovdamage:
        lda #0
        sta _dhgr_spr_v_dirty
        sta _dhgr_spr_ov_on
        ldx _dhgr_spr_w_g0
        cpx #NONE
        beq @new
        stx _dhgr_spr_rg0       ; the old box
        lda w_g1
        sta _dhgr_spr_rg1
        lda w_y0
        sta _dhgr_spr_ry0
        lda w_y1
        sta _dhgr_spr_ry1
        jsr _dhgr_spr_add
@new:   lda #NONE
        sta _dhgr_spr_w_g0
        lda cur_nw
        beq @done
        clc
        adc cur_nbx
        sbc #0                  ; bx + w - 1 (C = 0)
        lsr a
        lsr a
        sta w_g1
        sta _dhgr_spr_rg1
        lda cur_nbx
        lsr a
        lsr a
        sta _dhgr_spr_w_g0
        sta _dhgr_spr_rg0
        lda cur_ny
        sta w_y0
        sta _dhgr_spr_ry0
        clc
        adc cur_nh
        sbc #0
        sta w_y1
        sta _dhgr_spr_ry1
        jsr _dhgr_spr_add
        lda #$80
        sta _dhgr_spr_ov_on
@done:  rts

; dhgr_spr_blit, each row: its group code calls ov_group (JSR at
; spr_ovhook) if the row and the piece's groups cross the overlay, then
; ptr1 = bits + r * w; else it skips it (BIT abs). X kept.
ov_row: lda #$2C
        sta spr_ovhook
        lda spr_row
        sec
        sbc cur_ny
        bcc @none
        cmp cur_nh
        bcs @none
        tay                     ; r
        lda _dhgr_spr_w_g0
        asl a
        cmp _dhgr_spr_gend
        bcs @none
        lda w_g1
        asl a
        cmp _dhgr_spr_goff
        bcc @none
        lda cur_bits
        sta ptr1
        lda cur_bits+1
        sta ptr1+1
        tya
        beq @set
@mul:   lda ptr1
        clc
        adc cur_nw
        sta ptr1
        bcc :+
        inc ptr1+1
:       dey
        bne @mul
@set:   lda #$20                ; JSR
        sta spr_ovhook
@none:  rts

; dhgr_spr_blit, each group of such a row: b0..b2 in tmp1..tmp3, b3 in A,
; tmp4 = 2g. OR in the overlay bytes 4g..4g+3 it covers (Y = 4g + j - bx
; < w). Returns b3 in A; X kept.
ov_group:
        sta ob+3
        lda tmp1
        sta ob
        lda tmp2
        sta ob+1
        lda tmp3
        sta ob+2
        stx xsave
        lda tmp4
        asl a                   ; 4g
        sec
        sbc cur_nbx             ; negative: >= 176 > w
        tay
        ldx #0
@byte:  cpy cur_nw
        bcs @skip
        lda (ptr1),y
        and #$7F
        ora ob,x
        sta ob,x
@skip:  iny
        inx
        cpx #4
        bne @byte
        lda ob
        sta tmp1
        lda ob+1
        sta tmp2
        lda ob+2
        sta tmp3
        ldx xsave
        lda ob+3
        rts


.if .defined(DHGR_SPR_CODE_SEGMENT)
.if !DHGR_SPR_CODE_SEGMENT
.rodata
.endif
.else
.rodata
.endif
vectors:                        ; _dhgr_spr_cur_jmp, ovd, ovr, ovg
.if INSIDE
        rts                     ; (no save-under pass)
        nop
        nop
.else
        jmp dhgr_spr_pass
.endif
        jmp ovdamage
        jmp ov_row
        jmp ov_group
