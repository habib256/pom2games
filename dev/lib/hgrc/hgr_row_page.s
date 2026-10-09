; VERHILLE Arnaud — GPL-3.0. Explicit-page, immutable HGR addresses.
; fastcall (page on C stack, y in A); pointer in A/X, NULL for invalid input.
; No video/state changes, no BSS/ZP allocation. Main RAM/ZP, D=0.
; Destroys A/X/Y and tmp1/tmp2, non-reentrant. popa balances the C argument.
.export _hgr_row_on_page, hgr_rowptr_on_page
.import hgr_fixed_rowlo, hgr_fixed_rowhi
.import popa
.importzp tmp1, tmp2
.code
_hgr_row_on_page:
        sta tmp1
        jsr popa
        ldy tmp1
; Native ABI: A=page, Y=row, pointer A/X (NULL if invalid).
hgr_rowptr_on_page:
        cmp #1
        beq page1
        cmp #2
        bne invalid
        lda #$40
        bne select
page1:  lda #$20
select: sta tmp2
        cpy #192
        bcs invalid
        lda hgr_fixed_rowhi,y
        ora tmp2
        tax
        lda hgr_fixed_rowlo,y
        rts
invalid:
        lda #0
        tax
        rts
