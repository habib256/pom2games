.setcpu "65C02"
.import _gfx_u16_digits
.export _fast_number := _gfx_u16_digits
; The score also runs in BCD, kept by every award: the HUD then reads its
; five digits as nibbles instead of a 16-bit binary-to-decimal conversion.
.export _hud_number, _score_add_bcd, _score_set_bcd, _score_bcd
.import _hud_wanted
.bss
_score_bcd: .res 3              ; little endian: 00..99, 00..99, 0..5
.code
; A/X = points in BCD (X high byte). Decimal mode is local (65C02 clears D
; on interrupts).
_score_add_bcd:
        sed
        clc
        adc _score_bcd
        sta _score_bcd
        txa
        adc _score_bcd+1
        sta _score_bcd+1
        lda #0
        adc _score_bcd+2
        sta _score_bcd+2
        cld
        rts
; A/X = low two BCD bytes, high digit 0 or the 59990 cap.
_score_set_bcd:
        sta _score_bcd
        stx _score_bcd+1
        stz _score_bcd+2
        cpx #$99
        bne :+
        lda #5
        sta _score_bcd+2
:       rts
; Five ASCII digits into the HUD buffer, most significant first.
_hud_number:
        lda _score_bcd+2
        and #15
        ora #'0'
        sta _hud_wanted
        lda _score_bcd+1
        lsr
        lsr
        lsr
        lsr
        ora #'0'
        sta _hud_wanted+1
        lda _score_bcd+1
        and #15
        ora #'0'
        sta _hud_wanted+2
        lda _score_bcd
        lsr
        lsr
        lsr
        lsr
        ora #'0'
        sta _hud_wanted+3
        lda _score_bcd
        and #15
        ora #'0'
        sta _hud_wanted+4
        rts
