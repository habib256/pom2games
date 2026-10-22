; VERHILLE Arnaud — GPL-3.0. hgr_hud_invalidate and hgr_hud8_invalidate: one
; routine, the two field structs share their head (x, y, width, valid).
; void (field *, unsigned char page): page 0 clears both histories, 1/2 only
; that page's bit; other pages and a NULL field are ignored. A/X/Y, ptr1.
.export _hgr_hud_invalidate, _hgr_hud8_invalidate
.import popax
.importzp ptr1
VALID = 4                       ; offsetof(hgr_hud_field_t, valid)
.code
_hgr_hud8_invalidate := _hgr_hud_invalidate
_hgr_hud_invalidate:
        pha                     ; page
        jsr popax
        sta ptr1
        stx ptr1+1
        ora ptr1+1
        tax                     ; X = 0: NULL field
        pla
        cpx #0
        beq @done
        ldy #VALID
        tax
        beq @store              ; page 0: valid = 0
        dex
        beq @page1
        dex
        bne @done
        lda #1                  ; page 2: keep page 1's bit
        .byte $2C               ; BIT abs: skip the next LDA
@page1: lda #2                  ; page 1: keep page 2's bit
        and (ptr1),y
@store: sta (ptr1),y
@done:  rts
