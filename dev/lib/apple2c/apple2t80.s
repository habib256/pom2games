; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; apple2t80.s — 80-column text written directly, for cc65 programs
; (apple2t80.h, APPLE2C_T80_SRCS). //e (80-column card) / //c, 65C02.
; 80STORE on: even columns in aux $0400-$07FF (PAGE2 on while written), odd
; ones in main; ALTCHARSET on (inverse lower case, MouseText). Text page 1,
; full screen. Borrows cc65's ptr1/ptr2/tmp1/tmp2 and popa; no interrupt
; handler may write the text page or toggle PAGE2 meanwhile.
;
; Option (ca65 -D, APPLE2C_T80_PTR_AFLAGS): T80_PTR=1 for programs that link
; apple2t80_ptr.s (a pointer cell shown inverse): t80_init takes it off,
; t80_putc / t80_puts / t80_fill draw under it (what they write there is
; kept for t80_ptr_hide, shown flipped), t80_scroll takes it off meanwhile.
; Without it: no pointer code, nothing imported from apple2t80_ptr.s.
.setcpu "65C02"
.importzp ptr1, ptr2, tmp1, tmp2
.import popa
.export _t80_x, _t80_y, _t80_mode, _t80_sw
.export _t80_init, _t80_putc, _t80_puts, _t80_fill, _t80_scroll
.export t80_rowlo, t80_rowhi
.ifndef T80_PTR
T80_PTR = 0
.endif
.if T80_PTR
.import _t80_ptr_x, _t80_ptr_y, _t80_ptr_on, t80_ptr_save
.import _t80_ptr_show, _t80_ptr_hide, t80_flip
.endif

.bss
_t80_x:      .res 1
_t80_y:      .res 1
_t80_mode:   .res 1             ; 0 normal, 1 inverse, 2 raw screen codes
.data
_t80_sw:     .byte 39           ; t80_scroll: columns 0 .. 2 t80_sw + 1
.code

; 80STORE, 80COL, ALTCHARSET, TEXT, full screen, page 1; both halves of the
; text page cleared to spaces (not the screen holes: the slots', the mouse
; firmware's); mode 0 (normal).
_t80_init:
        sta $C001                ; 80STORE
        sta $C00D                ; 80COL
        sta $C00F                ; ALTCHARSET
        bit $C051                ; TEXT
        bit $C052                ; full screen
        bit $C054                ; PAGE1
        stz _t80_mode
.if T80_PTR
        stz _t80_ptr_on
.endif
        jsr @clr                 ; main (odd columns), then aux
        bit $C055
        jsr @clr
        bit $C054
        rts
@clr:   ldx #$77
        lda #$A0
:       sta $0400,x
        sta $0480,x
        sta $0500,x
        sta $0580,x
        sta $0600,x
        sta $0680,x
        sta $0700,x
        sta $0780,x
        dex
        bpl :-
        rts

; ptr1 = the row t80_y.
setrow:
        ldy _t80_y
        lda t80_rowlo,y
        sta ptr1
        lda t80_rowhi,y
        sta ptr1+1
        rts

; A = ASCII -> the screen code for t80_mode, written at (t80_x, t80_y) of
; the row in ptr1 (nothing past column 79); t80_x saturates at 80.
put:    ldx _t80_mode
        beq @norm
        dex
        bne @raw
        cmp #$40                 ; inverse: @..Z[\]^_ -> $00-$1F
        bcc @raw
        cmp #$60
        bcs @raw                 ; lower case: $60-$7F, inverse with ALTCHAR
        and #$1F
        bra @raw
@norm:  ora #$80
@raw:   tax
        lda _t80_x
        cmp #80
        bcs @done
.if T80_PTR
        ldy _t80_ptr_on          ; under the pointer: kept, shown flipped
        beq @wr
        cmp _t80_ptr_x
        bne @wr
        ldy _t80_y
        cpy _t80_ptr_y
        bne @wr
        stx t80_ptr_save
        txa
        jsr t80_flip
        tax
        lda _t80_x
@wr:
.endif
        lsr a
        tay
        txa
        bcs @main
        bit $C055                ; even column: aux
        sta (ptr1),y
        bit $C054
        bra @out
@main:  sta (ptr1),y
@out:   inc _t80_x
@done:  rts

_t80_putc:
        tax                     ; setrow preserves X
        jsr setrow
        txa
        jmp put

; A/X = a NUL-terminated string.
_t80_puts:
        sta ptr2
        stx ptr2+1
        jsr setrow
        ldy #0
@next:  lda _t80_x
        cmp #80
        bcs @end
        lda (ptr2),y
        beq @end
        phy
        jsr put
        ply
        iny
        bne @next
@end:   rts

; t80_fill(char, count).
_t80_fill:
        sta tmp2
        jsr popa
        sta tmp1
        jsr setrow
        lda tmp2
        beq @end
@next:  lda tmp1
        jsr put
        dec tmp2                ; put and optional t80_flip preserve tmp2
        bne @next
@end:   rts

; Columns 0 .. 2 t80_sw + 1 of the rows t80_y .. t80_y + t80_x - 1 (t80_x =
; the row count here) one row up (A = 0: the last row keeps its text, to be
; redrawn) or down (A != 0: the first). t80_y is left moved.
.if T80_PTR
_t80_scroll:
        ldy _t80_ptr_on          ; the pointer off meanwhile
        phy
        pha
        jsr _t80_ptr_hide
        pla
        jsr scroll
        pla
        beq :+
        jmp _t80_ptr_show
:       rts
.else
_t80_scroll = scroll
.endif

scroll: sta tmp1
        lda _t80_x
        beq @end
        dec a
        sta tmp2                 ; rows to copy
        beq @end
        lda tmp1
        bne @down
@up:    jsr @pair                ; dst = t80_y, src = t80_y + 1
        inc _t80_y
        dec tmp2
        bne @up
        rts
@down:  lda _t80_y               ; from the bottom: dst = last, src = last - 1
        clc
        adc tmp2
        sta _t80_y
@dn:    dec _t80_y
        jsr @pair2
        dec tmp2
        bne @dn
@end:   rts
@pair:  ldy _t80_y               ; row y + 1 -> row y
        lda t80_rowlo+1,y
        sta ptr2
        lda t80_rowhi+1,y
        sta ptr2+1
        bra @copy
@pair2: ldy _t80_y               ; row y -> row y + 1
        lda t80_rowlo,y
        sta ptr2
        lda t80_rowhi,y
        sta ptr2+1
        iny
@copy:  lda t80_rowlo,y
        sta ptr1
        lda t80_rowhi,y
        sta ptr1+1
        ldy _t80_sw
:       lda (ptr2),y
        sta (ptr1),y
        dey
        bpl :-
        bit $C055
        ldy _t80_sw
:       lda (ptr2),y
        sta (ptr1),y
        dey
        bpl :-
        bit $C054
        rts

; The text rows' addresses (page 1; in CODE: a program may reuse its RODATA
; at the exit).
t80_rowlo:
.repeat 24, r
        .byte <($0400 + (r .mod 8) * 128 + (r / 8) * 40)
.endrepeat
t80_rowhi:
.repeat 24, r
        .byte >($0400 + (r .mod 8) * 128 + (r / 8) * 40)
.endrepeat
