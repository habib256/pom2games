; VERHILLE Arnaud — GPL-3.0. DHGR compositor: dhgr_spr_area (dhgr.h), a
; member of its own: linked by the programs that call it (the default area
; is the whole screen). A/X/Y destroyed; non-reentrant.
.export _dhgr_spr_area
.import _dhgr_spr_ag0, _dhgr_spr_ag1, _dhgr_spr_ay0, _dhgr_spr_ay1
.import dhgr_spr_group, incsp3
.importzp sp

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; void dhgr_spr_area(x0, y0, x1, y1): C stack x1 0, y0 1, x0 2; y1 in A.
_dhgr_spr_area:
        cmp #192
        bcc :+
        lda #191
:       sta _dhgr_spr_ay1
        ldy #1
        lda (sp),y
        sta _dhgr_spr_ay0
        iny
        lda (sp),y
        jsr dhgr_spr_group
        sta _dhgr_spr_ag0
        ldy #0
        lda (sp),y
        cmp #140
        bcc :+
        lda #139
:       jsr dhgr_spr_group
        sta _dhgr_spr_ag1
        jmp incsp3
