; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; hgr_utoa_asm.s — Apple II HGR kernel; linked independently from hgrc.lib.
.export _hgr_utoa
.exportzp _hgr_u_lo, _hgr_u_hi, _hgr_u_ptr
.importzp ptr1, ptr2, tmp1, tmp2, tmp3, tmp4
curcol = tmp1
curmask = tmp2
curbits = tmp3
rowcnt = tmp4

.segment "ZEROPAGE"
_hgr_u_lo:    .res 1        ; value low byte  (consumed by the subtraction)
_hgr_u_hi:    .res 1        ; value high byte
_hgr_u_ptr:   .res 2        ; output buffer pointer

.segment "CODE"
_hgr_utoa:
        ldx #0                  ; power index 0..4
        lda #0
        sta tmp3                ; tmp3 != 0 once a digit has been emitted
        ldy #0                  ; output index
@pw:
        lda #0
        sta tmp4                ; digit for this power
@sub:
        lda _hgr_u_lo          ; value -= power (16-bit), while it fits
        sec
        sbc utoa_pw_lo,x
        sta tmp1
        lda _hgr_u_hi
        sbc utoa_pw_hi,x
        bcc @pwdone             ; borrow -> value < power -> next power
        sta _hgr_u_hi
        lda tmp1
        sta _hgr_u_lo
        inc tmp4
        jmp @sub
@pwdone:
        lda tmp4                ; emit if nonzero, already-emitting, or units
        bne @emit
        lda tmp3
        bne @emit
        cpx #4
        bne @skip
@emit:
        lda tmp4
        ora #$30
        sta (_hgr_u_ptr),y
        iny
        lda #1
        sta tmp3
@skip:
        inx
        cpx #5
        bne @pw
        lda #0
        sta (_hgr_u_ptr),y     ; NUL terminator
        rts

utoa_pw_lo: .byte $10, $E8, $64, $0A, $01   ; 10000, 1000, 100, 10, 1  (low byte)
utoa_pw_hi: .byte $27, $03, $00, $00, $00   ; 10000, 1000, 100, 10, 1  (high byte)
