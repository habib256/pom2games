; VERHILLE Arnaud — GPL-3.0. DHGR compositor: dhgr_spr_palette (dhgr.h),
; a member of its own: linked by the programs that call it. A/X/Y, ptr1,
; tmp1 destroyed; non-reentrant.
.export _dhgr_spr_palette
.import _dhgr_spr_dirty, _dhgr_spr_pal, dhgr_spr_slots
.import popa
.importzp ptr1, tmp1

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; void dhgr_spr_palette(id, four): four in A/X, id on the C stack.
_dhgr_spr_palette:
        sta ptr1
        stx ptr1+1
        jsr popa
        cmp #<dhgr_spr_slots    ; (DHGR_SPR_MAX of dhgr_spr_update.s)
        bcs @done
        tax
        asl a
        asl a
        tay
        sta tmp1                ; ptr1 -= 4 * id: Y = 4 * id + k for both
        lda ptr1
        sec
        sbc tmp1
        sta ptr1
        bcs :+
        dec ptr1+1
:       lda #3
        sta tmp1
@c:     lda (ptr1),y
        cmp _dhgr_spr_pal,y
        beq :+
        sta _dhgr_spr_pal,y
        lda #1
        sta _dhgr_spr_dirty,x
:       iny
        dec tmp1
        bpl @c
@done:  rts
