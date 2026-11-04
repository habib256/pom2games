; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; Opaque white/black 8x8 DHGR text: each glyph bit is one color pixel, four
; equal dots. Two glyph bits (eight dots) at bit phase 0..6 always fit in two
; 7-bit bytes, so a glyph row is four table lookups ORed into 5-6 bytes.
.include "apple2.inc"
.export _dhgr_puts
.import _hgr_font, _dhgr_base, dhgr_rowlo, dhgr_rowhi, _dhgr_cellbyte, _dhgr_cellphase
.import incsp3
.importzp sp, ptr1, ptr2, ptr3, tmp1, tmp2, tmp3, aux_read
row = tmp2                     ; cc65 scratch; aux_read only clobbers A
gap = tmp3                     ; the one low byte not overlapping a prior high byte
.bss
xpos: .res 1
ypos: .res 1
first: .res 1                   ; interleaved byte of the glyph's first dot
count: .res 1                   ; bytes per glyph row, 5 or 6
pair_index: .res 4              ; dot phase*4 for glyph bit pairs 0..3
pair_byte: .res 4               ; their first output byte
keep: .res 6                    ; screen bits kept in each output byte
buf: .res 6                    ; pair_byte <= 4, so its high byte ends at 5
.rodata
; Glyph bit pair v (two pixels, eight dots) shifted by dot phase P:
; pair_low[P*4+v] in the first byte, pair_high[P*4+v] in the next.
pair_low:
.repeat 7,P
.repeat 4,V
.byte ((((V&1)*$0F)|((V>>1)*$F0))<<P)&$7F
.endrepeat
.endrepeat
pair_high:
.repeat 7,P
.repeat 4,V
.byte ((((V&1)*$0F)|((V>>1)*$F0))<<P)>>7
.endrepeat
.endrepeat
; Per dot phase of the glyph's first dot: kept bits left of it and right of
; dot 32 (phase+32 mod 7), and the row's byte count.
keep_first:
.repeat 7,P
.byte (1<<P)-1
.endrepeat
keep_last:
.repeat 7,P
.if (P+4) .mod 7
.byte $7F-((1<<((P+4) .mod 7))-1)
.else
.byte 0
.endif
.endrepeat
row_bytes: .byte 5,5,5,5,6,6,6
; At phase 4..6 one pair starts two bytes after its predecessor. Other
; phases overlap throughout; slot 5 is then outside the five visible bytes.
gap_byte: .byte 5,5,5,5,4,3,2
.code
; void dhgr_puts(const char *s, unsigned char x, unsigned char y)
; Glyphs 32..127, others print '?'. Stops at the first glyph that would cross
; x=140 or y=192. IRQs are masked one glyph row at a time.
_dhgr_puts:
        sta ypos
        ldy #0
        lda (sp),y
        sta xpos
        iny
        lda (sp),y
        sta ptr3
        iny
        lda (sp),y
        sta ptr3+1
@char:  ldy #0
        lda (ptr3),y
        bne @glyph
@done:  jmp incsp3
@glyph: inc ptr3
        bne @range
        inc ptr3+1
@range: cmp #32
        bcc @unknown
        cmp #128
        bcc @known
@unknown:
        lda #'?'
@known: ldx xpos
        cpx #133
        bcs @done
        ldx ypos
        cpx #185
        bcs @done
        ; ptr2 = hgr_font + (ch-32)*8
        sec
        sbc #32
        ldx #0
        stx ptr2+1
        asl
        rol ptr2+1
        asl
        rol ptr2+1
        asl
        rol ptr2+1
        adc #<_hgr_font
        sta ptr2
        lda ptr2+1
        adc #>_hgr_font
        sta ptr2+1
        ldx xpos
        lda _dhgr_cellbyte,x
        sta first
        ldy _dhgr_cellphase,x
        lda row_bytes,y
        sta count
        lda gap_byte,y
        sta gap
        lda #0
        ldx #5
@clear_keep:
        sta keep,x
        dex
        bpl @clear_keep
        lda keep_first,y
        sta keep
        ldx count
        lda keep_last,y
        sta keep-1,x
        ; Pair i: dot phase P+i, one byte further when that reaches 7.
        tya
        ldx #0
@pair:  pha
        stx tmp1
        cmp #7
        bcc @same
        sbc #7
        inc tmp1
@same:  asl
        asl
        sta pair_index,x
        lda tmp1
        sta pair_byte,x
        pla
        clc
        adc #1
        inx
        cpx #4
        bne @pair
        lda #0
        sta row
@row:   lda #0
        ldy gap
        sta buf,y
        ldy row
        lda (ptr2),y
        sta tmp1
.repeat 4,I
        lda tmp1
        and #3
        ora pair_index+I
        tax
.if I=0
        ; The first pair starts the buffer. Every subsequent high byte is
        ; also a fresh slot; only its low byte can overlap its predecessor.
        lda pair_low,x
        sta buf
        lda pair_high,x
        sta buf+1
.else
        ldy pair_byte+I
        lda pair_low,x
        ora buf,y
        sta buf,y
        lda pair_high,x
        sta buf+1,y
.endif
.if I<3
        lsr tmp1
        lsr tmp1
.endif
.endrepeat
        lda row
        clc
        adc ypos
        tay
        lda dhgr_rowlo,y
        sta ptr1
        lda dhgr_rowhi,y
        ora _dhgr_base
        sta ptr1+1
        ldx #0
        php
        sei
        lda first
        lsr                     ; C = main
        tay                     ; Y = page column, advanced after main writes
        bcs @main
@aux:   lda keep,x
        beq @aux_store
        jsr aux_read
        and keep,x
@aux_store:
        ora buf,x
        sta RAMWRTON
        sta (ptr1),y
        sta RAMWRTOFF
        inx
        cpx count
        beq @row_done
@main:  lda keep,x
        beq @main_store
        lda (ptr1),y
        and keep,x
@main_store:
        ora buf,x
        sta (ptr1),y
        inx
        iny                     ; next aux byte is in the next page column
        cpx count
        bne @aux
@row_done:
        plp
        inc row
        lda row
        cmp #8
        beq @advance
        jmp @row
@advance:
        lda xpos
        clc
        adc #8
        sta xpos
        jmp @char
