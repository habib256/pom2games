; VERHILLE Arnaud — GPL-3.0. Optional HGR table, main RAM/ZP.
; No inputs. Clobbers A/X/Y, ptr1, tmp1/tmp2/tmp3; not reentrant.
.export _hgr_build_columns, _hgr_col7
.importzp ptr1, tmp1, tmp2, tmp3
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
        lda #0
        sta tmp1
        sta tmp3
        ldx #0
        ldy #0
@loop:
        lda tmp1
        sta (ptr1),y
        inx
        cpx #7
        bne @next
        ldx #0
        inc tmp1
@next:
        iny
        cpy tmp3
        bne @loop
        lda tmp3
        bne @done
        inc ptr1+1
        lda #24
        sta tmp3
        jmp @loop
@done:
        inc ready
        rts
