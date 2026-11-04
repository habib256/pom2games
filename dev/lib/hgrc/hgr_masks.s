; VERHILLE Arnaud — GPL-3.0. Optional HGR table, main RAM/ZP.
; Empty with HGRC_X7_FOLDED: hgr_columns.s then builds this table too.
; Boolean switches: zero and undefined select the default implementation.
.ifndef HGRC_X7_FOLDED
HGRC_X7_FOLDED = 0
.endif
.if !HGRC_X7_FOLDED
; No inputs. Clobbers A/X/Y and ptr1 only; not reentrant.
.export _hgr_build_masks, _hgr_mask7
.importzp ptr1
.bss
_hgr_mask7: .res 280
ready: .res 1
.code
_hgr_build_masks:
        lda ready
        beq @build
        rts
@build:
        lda #<_hgr_mask7
        sta ptr1
        lda #>_hgr_mask7
        sta ptr1+1
        ldx #40
@group:
        lda #$40                ; bit six down to bit zero
        ldy #6
@pixel:
        sta (ptr1),y
        lsr a
        dey
        bpl @pixel
        ; Advance by one seven-pixel column. Indirect indexing and the
        ; carry below also work when the table starts inside a page.
        clc
        lda ptr1
        adc #7
        sta ptr1
        bcc @next
        inc ptr1+1
@next:
        dex
        bne @group
        inc ready
        rts
.endif
