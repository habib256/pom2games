; VERHILLE Arnaud — GPL-3.0. Optional HGR tables, main RAM/ZP.
; x -> byte column (x / 7), bit mask (1 << x % 7) and phase (x % 7), x = 0..279,
; built together by one loop: every client of one table also used another
; (pixels, text, sprites), so one member and one pass cost less than three.
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
