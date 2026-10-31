; VERHILLE Arnaud — GPL-3.0. DHGR compositor: pack the chunky canvas of the
; current piece (dhgr_cv_asm.s) and write its screen bytes once each.
; Seven nibbles n0..n6 (one colour group) give four bytes (aux, main, aux,
; main at bank offsets 2g, 2g, 2g+1, 2g+1):
;   b0 = n0 | (n1&7)<<4        b1 = n1>>3 | n2<<1 | (n3&3)<<5
;   b2 = n3>>2 | n4<<2 | (n5&1)<<6        b3 = n5>>1 | n6<<3
; with one 16-byte table t4[n] = n << 4 (~77 cycles a group):
;   b0 = (t4[n1] | n0) & $7F       b1 = rol(t4[n3] | n2, C = n1 >= 8) & $7F
;   b2 = ror(t4[n4] | n3, C = n5 & 1) >> 1       b3 = (t4[n6] | n5) >> 1
; The piece's groups are consecutive in the canvas (X += 7). Self-modifying:
; the canvas operands are patched by dhgr_cv_patch at each update when they
; do not hold the canvas address (a reloaded overlay window), the screen
; operands per row. IRQs are masked only around each group's two auxiliary
; stores (~30 cycles); RAMWRT is main again before each plp. Bit 7 of every
; byte is 0. A/X/Y, tmp1-tmp4, ptr1 destroyed; non-reentrant, never from an
; IRQ. DHGR_SPR_PACK_TABLES is accepted and has no effect (one table now).
.include "apple2.inc"
RAMWRTON = $C005
.export _dhgr_spr_blit, _dhgr_spr_goff, _dhgr_spr_gend, dhgr_cv_patch
.export spr_row, spr_ovhook
.import _dhgr_cv_buf, _dhgr_cv_y0, _dhgr_cv_h, cv_seq
.import _dhgr_spr_ov_on, _dhgr_spr_ovr_jmp, _dhgr_spr_ovg_jmp
.import _dhgr_base, dhgr_rowlo, dhgr_rowhi
.importzp tmp1, tmp2, tmp3, tmp4, ptr1

.bss
spr_row: .res 1
left:   .res 1                  ; rows still to write
_dhgr_spr_goff: .res 1          ; 2 * first group: the row's first bank offset
_dhgr_spr_gend: .res 1          ; 2 * (last group + 1)

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if DHGR_SPR_CODE_SEGMENT
.segment "DHGRSPRCODE"
.else
.code
.endif
.else
.code
.endif

; void dhgr_spr_blit(void): the piece's rows y0..y0+h-1, groups goff/2 on.
_dhgr_spr_blit:
        lda _dhgr_cv_y0
        sta spr_row
        lda _dhgr_cv_h
        sta left
        lda #$2C                ; (BIT abs: no overlay in the groups)
        sta spr_ovhook
        ldx #0                  ; canvas offset of the group's n0
b_row:   ldy spr_row
        lda dhgr_rowlo,y        ; (even: + 1 by ora)
        sta s_m0+1
        sta s_a0+1
        ora #1
        sta s_m1+1
        sta s_a1+1
        lda dhgr_rowhi,y
        ora _dhgr_base
        sta s_m0+2
        sta s_a0+2
        sta s_m1+2
        sta s_a1+2
        bit _dhgr_spr_ov_on
        bpl :+
        jsr _dhgr_spr_ovr_jmp   ; (dhgr_spr_overlay.s: spr_ovhook; X kept)
:       ldy _dhgr_spr_goff
        sty tmp4
b_group:
c1:     ldy $FFFF,x             ; n1
        lda t4,y
c0:     ora $FFFF,x
        and #$7F
        sta tmp1                ; b0
        cpy #8                  ; C = n1 bit 3
c3:     ldy $FFFF,x
        lda t4,y
c2:     ora $FFFF,x
        rol a
        and #$7F
        sta tmp2                ; b1
c5:     lda $FFFF,x
        lsr a                   ; C = n5 bit 0
c4:     ldy $FFFF,x
        lda t4,y
c3b:    ora $FFFF,x
        ror a
        lsr a
        sta tmp3                ; b2
c6:     ldy $FFFF,x
        lda t4,y
c5b:    ora $FFFF,x
        lsr a                   ; b3
spr_ovhook:
        jsr _dhgr_spr_ovg_jmp   ; (BIT abs unless the row crosses the overlay; X kept)
        ldy tmp4
s_m1:   sta $FFFF,y             ; main odd
        lda tmp2
s_m0:   sta $FFFF,y             ; main even
        php
        sei
        sta RAMWRTON
        lda tmp1
s_a0:   sta $FFFF,y             ; aux even
        lda tmp3
s_a1:   sta $FFFF,y             ; aux odd
        sta RAMWRTOFF
        plp
        txa
        clc
        adc #7
        tax
        iny
        iny
        sty tmp4
        cpy _dhgr_spr_gend
        bne b_group
b_rowend:
        inc spr_row
        dec left
        beq :+
        jmp b_row
:       rts

; Patch every canvas operand (pack above, fill sequence in dhgr_cv_asm.s)
; unless c0 already holds the canvas address. ptr1, A/X/Y destroyed.
dhgr_cv_patch:
        lda _dhgr_cv_buf
        cmp c0+1
        bne @do
        lda _dhgr_cv_buf+1
        cmp c0+2
        beq @done
@do:    ldx #PATCHES * 3 - 3
@op:    lda patches,x
        sta ptr1
        lda patches+1,x
        sta ptr1+1
        lda patches+2,x
        clc
        adc _dhgr_cv_buf
        ldy #0
        sta (ptr1),y
        lda _dhgr_cv_buf+1
        adc #0
        iny
        sta (ptr1),y
        dex
        dex
        dex
        bpl @op                 ; (c0, entry 0, last)
@done:  rts

.if .defined(DHGR_SPR_CODE_SEGMENT)
.if !DHGR_SPR_CODE_SEGMENT
.rodata
.endif
.else
.rodata
.endif
patches:                        ; operand address, canvas offset
        .addr c0+1
        .byte 0
        .addr c1+1
        .byte 1
        .addr c2+1
        .byte 2
        .addr c3+1
        .byte 3
        .addr c3b+1
        .byte 3
        .addr c4+1
        .byte 4
        .addr c5+1
        .byte 5
        .addr c5b+1
        .byte 5
        .addr c6+1
        .byte 6
.repeat 8, J
        .addr cv_seq + 1 + 3 * J
        .byte 7 - J
.endrepeat
PATCHES = (* - patches) / 3
t4:
.repeat 16, N
        .byte N << 4
.endrepeat
