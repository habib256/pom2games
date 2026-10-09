; Incremental native white text through dev/lib/hgr/hgr_text8.asm.
; Eighty cells per page, outside the board pack, music and collision tables.
hud_chars = $1E00
.bss
hud_active: .res 1
hud_static: .res 2
.code
hud_filter:
        lda hud_active
        beq @draw
        ldy ht_col
        lda ht_sl
        cmp #4
        beq @page
        cmp #184
        bne @draw
        tya
        clc
        adc #40
        tay
@page:  lda ht_page
        beq @compare
        tya
        clc
        adc #80
        tay
@compare:
        lda ht_a
        cmp hud_chars,y
        beq @skip
        sta hud_chars,y
@draw:  clc
        rts
@skip:  sec
        rts
