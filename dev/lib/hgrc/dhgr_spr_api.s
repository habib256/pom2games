; VERHILLE Arnaud — GPL-3.0. DHGR compositor calls (dhgr.h): slots,
; invalidation, solid background (the palette and the area: their own
; members, dhgr_spr_palette.s).
; They only record; dhgr_spr_update draws (dhgr_spr_init is in
; dhgr_spr_update.s).
; cc65 C calling convention; A/X/Y, ptr1, tmp1-tmp3 destroyed; non-reentrant.
.export _dhgr_spr_set, _dhgr_spr_invalidate, _dhgr_spr_solid, dhgr_spr_group
.import _dhgr_spr_shlo, _dhgr_spr_shhi, _dhgr_spr_x, _dhgr_spr_y
.import _dhgr_spr_x1, _dhgr_spr_y1, _dhgr_spr_flags, _dhgr_spr_dirty
.import _dhgr_spr_rg0, _dhgr_spr_rg1, _dhgr_spr_ry0, _dhgr_spr_ry1, _dhgr_spr_add
.import _dhgr_spr_solid_c, _dhgr_spr_bg, _dhgr_cellbyte
.import incsp3, incsp5
.importzp sp, ptr1, tmp1, tmp2, tmp3

.ifndef DHGR_SPR_MAX
DHGR_SPR_MAX = 8
.endif
MAX = DHGR_SPR_MAX
NONE = $FF
HIDDEN = 2

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; unsigned char dhgr_spr_set(id, shape, x, y, flags): C stack y 0, x 1,
; shape 2-3, id 4; flags in A. 0 for a bad id; unchanged: not dirty.
_dhgr_spr_set:
        sta tmp1
        ldy #4
        lda (sp),y
        cmp #MAX
        bcc :+
        lda #0
        jmp ret
:       tax
        lda #0
        sta tmp2                ; something changed
        lda tmp1
        cmp _dhgr_spr_flags,x
        beq :+
        sta _dhgr_spr_flags,x
        inc tmp2
:       txa                     ; y, x, shape low, high: stack 0..3 and the
        clc                     ; arrays MAX apart from _dhgr_spr_y
        adc #3 * MAX
        tax
        ldy #3
@field: lda (sp),y
        cmp _dhgr_spr_y,x
        beq :+
        sta _dhgr_spr_y,x
        inc tmp2
:       txa
        sec
        sbc #MAX
        tax
        dey
        bpl @field
        ldy #4
        lda (sp),y
        tax
        lda tmp2
        beq @one
        lda #1
        sta _dhgr_spr_dirty,x
        lda #NONE
        sta _dhgr_spr_y1,x
        lda _dhgr_spr_shlo,x    ; visible: a shape, not hidden, on the screen
        sta ptr1
        ora _dhgr_spr_shhi,x
        beq @one
        lda _dhgr_spr_shhi,x
        sta ptr1+1
        lda tmp1
        and #HIDDEN
        bne @one
        ldy #1
        lda (ptr1),y            ; w
        beq @one
        sta tmp3
        lda _dhgr_spr_x,x
        cmp #140
        bcs @one
        ldy #140
        jsr endc
        sta _dhgr_spr_x1,x
        ldy #2
        lda (ptr1),y            ; h
        beq @one
        sta tmp3
        lda _dhgr_spr_y,x
        cmp #192
        bcs @one
        ldy #192
        jsr endc
        sta _dhgr_spr_y1,x
@one:   lda #1
ret:    ldx #0
        jmp incsp5

; A + tmp3 - 1, at most Y - 1 (A < Y, tmp3 > 0). X kept.
endc:   sty @lim+1
        clc
        adc tmp3
        bcs @cap
@lim:   cmp #0
        bcc @ok
@cap:   lda @lim+1
        clc
@ok:    sbc #0                  ; (C = 0: - 1)
        rts

; void dhgr_spr_invalidate(x, y, w, h): C stack w 0, y 1, x 2; h in A.
_dhgr_spr_invalidate:
        sta tmp3                ; h
        tax
        beq @done
        ldy #1
        lda (sp),y
        cmp #192
        bcs @done
        sta _dhgr_spr_ry0
        ldy #192
        jsr endc
        sta _dhgr_spr_ry1
        ldy #0
        lda (sp),y              ; w
        beq @done
        sta tmp3
        ldy #2
        lda (sp),y              ; x
        cmp #140
        bcs @done
        tax
        jsr group
        sta _dhgr_spr_rg0
        txa
        ldy #140
        jsr endc
        jsr group_a
        sta _dhgr_spr_rg1
        jsr _dhgr_spr_add
@done:  jmp incsp3

dhgr_spr_group:                 ; (dhgr_spr_area.s)
group_a:
        tax
group:  lda _dhgr_cellbyte,x    ; colour pixel X -> group (x / 7)
        lsr a
        lsr a
        rts

; void __fastcall__ dhgr_spr_solid(colour)
_dhgr_spr_solid:
        sta _dhgr_spr_solid_c
        lda #0
        sta _dhgr_spr_bg
        rts
