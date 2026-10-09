; GPL-3.0. Two square oscillators XOR-mixed on the one-bit Apple II speaker.
; One call = 256 samples, 68 cycles/sample (last branch one cycle shorter).
; No IRQ handler installed. PHP/SEI/PLP protect pitch timing and caller flags.
; Phase persists between blocks. Muted voices reset their phase at entry.
        .export _audio_block, _audio_inc, _audio_reset
        .segment "BSS"
_audio_inc: .res 4
        .segment "ZEROPAGE"
phase0: .res 2
phase1: .res 2
inc0:   .res 2
inc1:   .res 2
state:  .res 1
        .segment "CODE"
_audio_reset:
        lda #0
        sta phase0
        sta phase0+1
        sta phase1
        sta phase1+1
        sta state
        rts
_audio_block:
        php
        sei
        ldx #3
@copy: lda _audio_inc,x
        sta inc0,x
        dex
        bpl @copy
        lda inc0
        ora inc0+1
        bne @voice1
        sta phase0
        sta phase0+1
@voice1:
        lda inc1
        ora inc1+1
        bne @start
        sta phase1
        sta phase1+1
@start: ldy #0
        jmp sample
; Keep every timing branch in one page, including the DEX/BNE loop paths.
        .align 256
sample:
        clc
        lda phase0
        adc inc0
        sta phase0
        lda phase0+1
        adc inc0+1
        sta phase0+1
        clc
        lda phase1
        adc inc1
        sta phase1
        lda phase1+1
        adc inc1+1
        sta phase1+1
        lda phase0+1
        eor phase1+1
        and #$80
        cmp state
        beq unchanged
        sta state
        bit $C030
        jmp next
unchanged:
        bit state
        nop
        nop
        nop
next:  dey
        bne sample
        plp
        rts
