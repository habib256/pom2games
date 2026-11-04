; VERHILLE Arnaud — GPL-3.0. Optional HGR table, main RAM/ZP.
; Option HGRC_X7_FOLDED (ca65 -D HGRC_X7_FOLDED=1, via HGRC_DEFINES): one
; member builds hgr_col7, hgr_mask7 and hgr_phase7 in one loop (77 B of
; code instead of 130 B for three, but always 841 B of BSS and ~15k cycles on
; first use). Default: one member per table (hgr_masks.s, hgr_phases.s), a
; program reserves only the tables it references.
; Boolean switches: zero and undefined select the default implementation.
.ifndef HGRC_X7_FOLDED
HGRC_X7_FOLDED = 0
.endif
.if HGRC_X7_FOLDED
; x -> byte column (x / 7), bit mask (1 << x % 7) and phase (x % 7), x = 0..279,
; built together by one loop. This option saves code when multiple tables
; are needed, but the default grouped builders now initialize faster.
; hgr_build_masks / hgr_build_phases are the same entry.
; No inputs. Clobbers A/X/Y, tmp1/tmp2; not reentrant.
.export _hgr_build_columns, _hgr_build_masks, _hgr_build_phases
.export _hgr_col7, _hgr_mask7, _hgr_phase7
.importzp tmp1, tmp2
.bss
_hgr_col7:   .res 280
_hgr_mask7:  .res 280
_hgr_phase7: .res 280
ready: .res 1
.code
_hgr_build_masks  := _hgr_build_columns
_hgr_build_phases := _hgr_build_columns
_hgr_build_columns:
        lda ready
        bne @done
        inc ready
        lda #0
        sta tmp1                ; column
        tay                     ; phase
        tax                     ; x (low byte)
        lda #1
        sta tmp2                ; mask
@lo:    lda tmp1                ; x = 0..255
        sta _hgr_col7,x
        lda tmp2
        sta _hgr_mask7,x
        tya
        sta _hgr_phase7,x
        jsr step
        inx
        bne @lo
@hi:    lda tmp1                ; x = 256..279
        sta _hgr_col7+256,x
        lda tmp2
        sta _hgr_mask7+256,x
        tya
        sta _hgr_phase7+256,x
        jsr step
        inx
        cpx #280-256
        bne @hi
@done:  rts
; next x: phase + 1, mask << 1; after phase 6, the next column.
step:   asl tmp2
        iny
        cpy #7
        bne @same
        ldy #0
        inc tmp1
        lda #1
        sta tmp2
@same:  rts
.else
; No inputs. Clobbers A/X/Y and ptr1 only; not reentrant.
.export _hgr_build_columns, _hgr_col7
.importzp ptr1
.bss
_hgr_col7: .res 280
ready: .res 1
.code
_hgr_build_columns:
        lda ready
        beq @build
        rts
@build:
        lda #<_hgr_col7
        sta ptr1
        lda #>_hgr_col7
        sta ptr1+1
        ldx #0
@group:
        txa                     ; one column value for its seven pixels
        ldy #6
@pixel:
        sta (ptr1),y
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
        inx
        cpx #40
        bne @group
        inc ready
        rts
.endif
