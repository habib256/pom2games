; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2t80_ptr.s — a pointer on apple2t80.s's 80-column text (apple2t80.h,
; APPLE2C_T80_PTR_SRCS): the cell (t80_ptr_x, t80_ptr_y) shown inverse (an
; inverse cell normal, MouseText '+'). Assemble apple2t80.s with -D T80_PTR=1
; (APPLE2C_T80_PTR_AFLAGS) so that its text routines draw under it.
; Borrows cc65's ptr1. PAGE1 on exit.
.setcpu "65C02"
.importzp ptr1
.import t80_rowlo, t80_rowhi
.export _t80_ptr_x, _t80_ptr_y, _t80_ptr_on, t80_ptr_save
.export _t80_ptr_show, _t80_ptr_hide, t80_flip

.bss
_t80_ptr_x:  .res 1             ; the pointer's cell
_t80_ptr_y:  .res 1
_t80_ptr_on: .res 1             ; 1: shown
t80_ptr_save: .res 1            ; the screen code under it

.code
; ptr1 = the pointer's row, Y = its column / 2, C = 1: odd (main), else aux
; (PAGE2 on: the caller goes back to PAGE1).
ptr_at: ldy _t80_ptr_y
        lda t80_rowlo,y
        sta ptr1
        lda t80_rowhi,y
        sta ptr1+1
        lda _t80_ptr_x
        lsr a
        tay
        bcs :+
        bit $C055
:       rts

_t80_ptr_show:
        lda _t80_ptr_on
        bne :+
        jsr ptr_at
        lda (ptr1),y
        sta t80_ptr_save
        jsr t80_flip
        sta (ptr1),y
        bit $C054
        inc _t80_ptr_on
:       rts

_t80_ptr_hide:
        lda _t80_ptr_on
        beq :+
        jsr ptr_at
        lda t80_ptr_save
        sta (ptr1),y
        bit $C054
        stz _t80_ptr_on
:       rts

; A = a screen code -> its inverse (normal: inverse; inverse: normal;
; MouseText: '+'). X, Y kept.
t80_flip:
        cmp #$80
        bcc @ton
        cmp #$E0
        bcs @lo                  ; $E0-$FF lower case
        cmp #$C0                 ; retain the original carry result
        and #$3F                 ; $80-$DF: inverse uppercase/punctuation
        rts
@lo:    and #$7F
        rts
@ton:   cmp #$20
        bcs :+
        ora #$C0                 ; $00-$1F
        rts
:       cmp #$40
        bcc @o80                 ; $20-$3F
        cmp #$60
        bcs @o80                 ; $60-$7F
        lda #$AB                 ; MouseText
        rts
@o80:   ora #$80
        rts
