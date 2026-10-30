; Robot Space Station — board_swap() and board_swap_run() (sim.h): exchange
; the loaded board with the other drone's, kept here. The arrays are
; declared in this order in sim.c and contiguous (checked at link time):
; parts, wires (the layout), then fl_count, fl_kind, fl_a, fl_b, fl_sinks,
; values (what a turn needs: board_swap_run() exchanges only those).
.setcpu "65C02"
.importzp ptr1, ptr2, tmp1
.import _parts, _fl_count, _values
.export _board_swap, _board_swap_run

LAYOUT_BYTES = 48 + 72
RUN_BYTES = 1 + 3 * 64 + 8 + 72
BOARD_BYTES = LAYOUT_BYTES + RUN_BYTES
.assert _fl_count - _parts = LAYOUT_BYTES, lderror, "sim.c layout arrays not contiguous"
.assert _values + 72 - _parts = BOARD_BYTES, lderror, "sim.c board arrays not contiguous"

.segment "LOW8BSS"                      ; ($0800-$0FFF: not zeroed, filled
other:  .res BOARD_BYTES                ; by use_board() before any turn)
.segment "BSS"
count:  .res 1

.segment "CODE"
_board_swap:
        lda #<_parts
        sta ptr1
        lda #>_parts
        sta ptr1+1
        lda #<other
        sta ptr2
        lda #>other
        sta ptr2+1
        ldx #<BOARD_BYTES
        lda #>BOARD_BYTES
        bra swap
; A turn reads fl_count gates and values[0 .. 8 + fl_count): swap only
; max(fl_count, the other's) entries of each array, the sinks and those
; values (a few dozen bytes for small boards).
_board_swap_run:
        lda _fl_count                   ; exchange the counts, keep the larger
        ldx other + LAYOUT_BYTES
        sta other + LAYOUT_BYTES
        stx _fl_count
        sta count
        cpx count
        bcc :+
        stx count
:       ldx count
        beq @sinks
@gates: lda _fl_count + 0,x             ; fl_kind[x - 1]
        ldy other + LAYOUT_BYTES + 0,x
        sta other + LAYOUT_BYTES + 0,x
        tya
        sta _fl_count + 0,x
        lda _fl_count + 64,x            ; fl_a[x - 1]
        ldy other + LAYOUT_BYTES + 64,x
        sta other + LAYOUT_BYTES + 64,x
        tya
        sta _fl_count + 64,x
        lda _fl_count + 128,x           ; fl_b[x - 1]
        ldy other + LAYOUT_BYTES + 128,x
        sta other + LAYOUT_BYTES + 128,x
        tya
        sta _fl_count + 128,x
        dex
        bne @gates
@sinks: ldx #8                          ; fl_sinks
@sink:  lda _fl_count + 192,x
        ldy other + LAYOUT_BYTES + 192,x
        sta other + LAYOUT_BYTES + 192,x
        tya
        sta _fl_count + 192,x
        dex
        bne @sink
        lda count                       ; values[0 .. 8 + n)
        clc
        adc #8
        tax
@value: lda _values - 1,x
        ldy other + BOARD_BYTES - 72 - 1,x
        sta other + BOARD_BYTES - 72 - 1,x
        tya
        sta _values - 1,x
        dex
        bne @value
        rts

; Swap A * 256 + X bytes at ptr1 and ptr2.
swap:   sta tmp1                        ; whole pages
        ldy #0
        lda tmp1
        beq @rest
@page:  lda (ptr1),y
        pha
        lda (ptr2),y
        sta (ptr1),y
        pla
        sta (ptr2),y
        iny
        bne @page
        inc ptr1+1
        inc ptr2+1
        dec tmp1
        bne @page
@rest:  cpx #0
        beq @done
@byte:  lda (ptr1),y
        pha
        lda (ptr2),y
        sta (ptr1),y
        pla
        sta (ptr2),y
        iny
        dex
        bne @byte
@done:  rts
