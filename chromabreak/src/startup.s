; ProDOS SYS entry $2000. Relocate backwards: source/destination may overlap.
.setcpu "65C02"
.segment "CODE"
        cld
        sta $C002
        sta $C004
        sta $C000
        ldx #$FF
        txs
        ; Keep the 2 KiB compact font tables below graphics, freeing game memory.
        ; Copy it before relocating the overlapping SYS payload.
        lda #<font_payload
        sta $06
        lda #>font_payload
        sta $07
        stz $08
        lda #$08
        sta $09
        ldx #8
        ldy #0
font_copy:
        lda ($06),y
        sta ($08),y
        iny
        bne font_copy
        inc $07
        inc $09
        dex
        bne font_copy
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
font_payload: .incbin "font.bin"
.assert *-font_payload=2048, error, "DHGR font payload must be 2 KiB"
