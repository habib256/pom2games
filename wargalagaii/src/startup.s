; WG2.SYS: ProDOS SYS entry $2000. Moves the game image to $6000 (backwards:
; source and destination overlap) and starts it.
.setcpu "65C02"
.segment "CODE"
        cld
        sta $C002
        sta $C004
        sta $C000
        ldx #$FF
        txs
        lda #<(payload+size-1)
        sta $06
        lda #>(payload+size-1)
        sta $07
        lda #<($6000+size-1)
        sta $08
        lda #>($6000+size-1)
        sta $09
        lda #<size
        sta $0A
        lda #>size
        sta $0B
        ldy #0
copy:   lda ($06),y
        sta ($08),y
        lda $06
        bne :+
        dec $07
:       dec $06
        lda $08
        bne :+
        dec $09
:       dec $08
        lda $0A
        bne :+
        dec $0B
:       dec $0A
        lda $0A
        ora $0B
        bne copy
        jmp $6000
payload: .incbin "game.bin"
size=*-payload
.assert size <= $5E00, error, "game image overlaps the C stack"
