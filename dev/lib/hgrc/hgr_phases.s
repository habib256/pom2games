; VERHILLE Arnaud — GPL-3.0. Optional HGR table, main RAM/ZP.
; x -> phase (x % 7), x = 0..279, built once by hgr_x7_fill.
; No inputs. Clobbers A/X/Y, ptr1, tmp1..tmp4; not reentrant.
.export _hgr_build_phases, _hgr_phase7
.import hgr_x7_fill
.importzp ptr1
.bss
_hgr_phase7: .res 280
ready: .res 1
.code
_hgr_build_phases:
        lda ready
        bne @done
        inc ready
        lda #<_hgr_phase7
        sta ptr1
        lda #>_hgr_phase7
        sta ptr1+1
        ldx #2
        jmp hgr_x7_fill
@done:  rts
