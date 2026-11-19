; VERHILLE Arnaud — GPL-3.0. Optional HGR table, main RAM/ZP.
; Empty with HGRC_X7_FOLDED: hgr_columns.s then builds this table too.
.include "hgr_x7_table.inc"
.if !HGRC_X7_FOLDED
; No inputs. Clobbers A/X/Y and ptr1 only; not reentrant.
        hgr_x7_begin _hgr_build_phases, _hgr_phase7
        ldx #40
@group:
        ldy #6
@pixel:
        tya                     ; phase equals the position within this group
        sta (ptr1),y
        dey
        bpl @pixel
        hgr_x7_next_column
        dex
        bne @group
        inc ready
        rts
.endif
