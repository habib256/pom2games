; hgr_clear_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_clear
.import _hgr_base
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "CODE"
_hgr_clear:
        ldx _hgr_base   ; draw-page high byte ($20 page1 / $40 page2)
        bne @baseok          ; 0 = unset (BSS) -> default to page 1
        ldx #$20
        stx _hgr_base
@baseok:
        stx ptr1+1
        ldy #$00
        sty ptr1             ; ptr1 = base<<8, Y = 0
        ldx #$20             ; 32 pages = 8 KB (page-base independent)
@page:
        sta (ptr1),y         ; store the fill byte (A preserved throughout)
        iny
        bne @page            ; 256 bytes of this page (Y wraps back to 0)
        inc ptr1+1           ; next page
        dex
        bne @page            ; 32 pages -> done (8 KB framebuffer)
        rts
