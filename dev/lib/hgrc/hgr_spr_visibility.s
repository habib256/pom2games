; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Shared visibility/change tests for rendering and optional damage closure.
; Kept separate so a DAMAGE initializer does not extract the masked renderer.
; NMOS6502, main RAM/ZP, D=0; X preserved by visibility, tmp1 scratch in changed.
.export spr_visible,spr_changed,spr_bits,spr_pgbase
.import _spr_active,_spr_shape,_spr_x,_spr_y,_spr_drawn,_spr_py,_spr_px
.importzp tmp1
.bss
spr_pgbase:.res 1
.rodata
spr_bits:.byte 1,2,4,8,16,32,64,128
.code
; X=id, A=visibility, preserves X, destroys Y/flags.
spr_visible:
        lda _spr_active,x
        beq no
        txa
        asl
        tay
        lda _spr_shape,y
        ora _spr_shape+1,y
        beq no
        lda _spr_x+1,y
        cmp #1
        bcc within
        bne no
        lda _spr_x,y
        cmp #24
        bcs no
within:
        lda _spr_y,x
        cmp #192
        bcs no
        lda #1
        rts
no:
        lda #0
        rts
; X=id, A=changed vs this page. Destroys X/Y/tmp1/flags.
spr_changed:
        jsr spr_visible
        sta tmp1                ; visibility is only live within this leaf
        txa
        clc
        adc spr_pgbase
        tay
        lda _spr_drawn,y
        cmp tmp1
        bne yes
        lda tmp1
        beq no
        lda _spr_py,y
        cmp _spr_y,x
        bne yes
        tya
        asl
        tay
        txa
        asl
        tax
        lda _spr_px,y
        cmp _spr_x,x
        bne yes
        lda _spr_px+1,y
        cmp _spr_x+1,x
        bne yes
        jmp no
yes:
        lda #1
        rts
