; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Mutable scanline addresses for the current HGR draw page.
; BSS defaults survive DOS CALL re-entry correctly. No C software stack.
; Clobbers A/X/Y/tmp1 only; hgr_row relies on tmp2 being preserved.
; HGRC_ROWLO_FIXED = 1: the low bytes do not depend on the page, so
; _hgr_rowlo is hgr_fixed_rows.s's constant table (for a program that links
; it anyway: -192 B of BSS, -5 B, 1,344 cycles less to build; a program
; without it would load 192 B more).
.ifndef HGRC_ROWLO_FIXED
HGRC_ROWLO_FIXED = 0
.endif
.export _hgr_build_rows, _hgr_rowlo, _hgr_rowhi
.import _hgr_base
.importzp tmp1

.bss
.if HGRC_ROWLO_FIXED
.import hgr_fixed_rowlo
_hgr_rowlo = hgr_fixed_rowlo
.else
_hgr_rowlo: .res 192
.endif
_hgr_rowhi: .res 192
ready:     .res 1

.code
_hgr_build_rows:
        lda ready
        bne done
        lda _hgr_base
        bne base_set
        lda #$20
        sta _hgr_base
base_set:
        tay
        ldx #0
        stx tmp1
row:
        tya
        sta _hgr_rowhi,x
.if !HGRC_ROWLO_FIXED
        lda tmp1
        sta _hgr_rowlo,x
.endif
        iny
        iny
        iny
        iny
        inx
        txa
        and #7
        bne row
        ; Next eight-line group: undo the high-byte line offset,
        ; toggle low bit 7, and carry into the high byte on even groups.
        tya
        sec
        sbc #32
        tay
        lda tmp1
        eor #$80
        sta tmp1
        bmi group_set
        iny
group_set:
        cpx #192
        beq finish
        txa
        and #63
        bne row
        ; Next screen third starts at low byte 40 or 80.
        lda tmp1
        clc
        adc #40
        sta tmp1
        ldy _hgr_base
        bne row                 ; base is always nonzero
finish:
        lda #1
        sta ready
done:
        rts
