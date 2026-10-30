; ProDOS SYS entry $2000: move the C program to $6000, then its HI part
; to $4000, each from the end (sources and destinations overlap, always
; with the destination above), then its L8 part down to $0C40 (no
; overlap), then start it.
.setcpu "65C02"
.segment "CODE"
        cld
        sta $C002               ; main RAM read/write, 80STORE off
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
        jsr copy
        lda #<(hi+hi_size-1)
        sta $06
        lda #>(hi+hi_size-1)
        sta $07
        lda #<($4000+hi_size-1)
        sta $08
        lda #>($4000+hi_size-1)
        sta $09
        lda #<hi_size
        sta $0A
        lda #>hi_size
        sta $0B
        jsr copy
        lda #<(low+low_size-1)
        sta $06
        lda #>(low+low_size-1)
        sta $07
        lda #<($0C40+low_size-1)
        sta $08
        lda #>($0C40+low_size-1)
        sta $09
        lda #<low_size
        sta $0A
        lda #>low_size
        sta $0B
        jsr copy
        jmp $6000
; Copy $0A/$0B bytes, last byte from ($06) to ($08), going down.
copy:   ldy #0
@loop:  lda ($06),y
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
        bne @loop
        rts
; L8 and HI first: game.bin's copy to $6000, then HI's to $4000, leave
; them in place; L8 goes below, to $0C40 (free since RSS.SYSTEM ran).
low:    .incbin "game.bin.low"
low_size = *-low
hi:     .incbin "game.bin.hi"
hi_size = *-hi
payload: .incbin "game.bin"
size = *-payload
.assert hi_size <= $2000, error, "HI fills $4000-$5FFF"
.assert low_size <= $03C0, error, "L8 fills $0C40-$0FFF"
.assert size <= $5E80, error, "the program reaches the C stack ($BE80)"
