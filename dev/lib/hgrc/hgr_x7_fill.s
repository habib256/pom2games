; VERHILLE Arnaud — GPL-3.0. Shared filler of the optional x/7 tables, main RAM/ZP.
; In: ptr1 = 280-byte table, X = 0 column (x / 7), 1 mask (1 << x % 7),
; 2 phase (x % 7). One walker, one table per call: each table stays its own
; member (hgr_columns.s, hgr_masks.s, hgr_phases.s), so a program reserves
; only the tables it references.
; Clobbers A/Y, ptr1+1, tmp1..tmp4; X preserved. Not reentrant.
.export hgr_x7_fill
.importzp ptr1, tmp1, tmp2, tmp3, tmp4
.code
hgr_x7_fill:
        lda #0
        sta tmp1                ; column
        sta tmp3                ; phase
        sta tmp4                ; first pass ends when y wraps (256 bytes)
        tay
        lda #1
        sta tmp2                ; mask
@loop:  txa
        beq @col
        lsr                     ; kind 1 -> C=1, kind 2 -> C=0
        lda tmp2
        bcs @store
        lda tmp3
        bcc @store
@col:   lda tmp1
@store: sta (ptr1),y
        asl tmp2
        inc tmp3
        lda tmp3
        cmp #7
        bne @next
        lda #0
        sta tmp3
        inc tmp1
        lda #1
        sta tmp2
@next:  iny
        cpy tmp4
        bne @loop
        lda tmp4
        bne @done
        inc ptr1+1              ; x = 256..279
        lda #280-256
        sta tmp4
        bne @loop
@done:  rts
