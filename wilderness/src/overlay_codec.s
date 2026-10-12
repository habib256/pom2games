; Resident reverse LZ decoder. Input occupies its final module window.
; A protected 128-byte prefix is kept in the retired DOS text buffer after
; the visible text has been restored. All live ZP, including FAC, is restored.
.segment "LOWCODE"
unpack_source = ang
unpack_dest = dx
unpack_match = dy
unpack_remain = rx
unpack_flags = ry
unpack_bits = ry+1
unpack_offset = thr
unpack_length = thr+1

overlay_unpack:
        lda     overlay_wanted
        cmp     #3
        beq     @sim
        lda     #$58
        bne     @base
@sim:   lda     #$20
@base:  sta     unpack_header+2
        sta     unpack_base+1
        ldy     #0
        jsr     unpack_header
        bne     @raw
        iny
        jsr     unpack_header
        cmp     #'W'
        beq     @packed
@raw:   rts
@packed:
        ldy     #2
        jsr     unpack_header
        sta     unpack_dest
        sec
        sbc     #128
        sta     unpack_remain
        iny
        jsr     unpack_header
        pha
        sbc     #0
        sta     unpack_remain+1
        pla
        clc
        adc     unpack_base+1
        sta     unpack_dest+1
        iny
        jsr     unpack_header
        clc
        adc     #6
        sta     unpack_source
        iny
        jsr     unpack_header
        adc     unpack_base+1
        sta     unpack_source+1
        ldy     #127
@prefix:
        lda     (unpack_source),y
        sta     overlay_text,y
        dey
        bpl     @prefix
        lda     #0
        sta     unpack_bits
@token: lda     unpack_bits
        bne     :+
        jsr     unpack_get
        sta     unpack_flags
        lda     #8
        sta     unpack_bits
:       dec     unpack_bits
        lsr     unpack_flags
        bcs     @match
        jsr     unpack_get
        ldx     unpack_dest
        bne     :+
        dec     unpack_dest+1
:       dec     unpack_dest
        sta     (unpack_dest),y
        lda     unpack_remain
        bne     :+
        dec     unpack_remain+1
:       dec     unpack_remain
        jmp     @check
@match: jsr     unpack_get
        sta     unpack_offset
        clc
        lda     unpack_dest
        adc     unpack_offset
        sta     unpack_match
        php
        jsr     unpack_get
        sta     unpack_length
        lsr
        lsr
        lsr
        lsr
        sta     unpack_offset
        plp
        lda     unpack_dest+1
        adc     unpack_offset
        sta     unpack_match+1
        lda     unpack_length
        and     #15
        clc
        adc     #3
        cmp     #18
        bne     :+
        jsr     unpack_get
        clc
        adc     #18
:       tax
        stx     unpack_length
        sec
        lda     unpack_dest
        sbc     unpack_length
        sta     unpack_dest
        bcs     :+
        dec     unpack_dest+1
:       sec
        lda     unpack_match
        sbc     unpack_length
        sta     unpack_match
        bcs     :+
        dec     unpack_match+1
:       txa
        tay
        dey
@copy:  lda     (unpack_match),y
        sta     (unpack_dest),y
        dey
        dex
        bne     @copy
        sec
        lda     unpack_remain
        sbc     unpack_length
        sta     unpack_remain
        bcs     :+
        dec     unpack_remain+1
:
@check: lda     unpack_remain
        ora     unpack_remain+1
        jne     @token
        lda     #0
        sta     unpack_dest
unpack_base:
        lda     #$58
        sta     unpack_dest+1
        ldy     #127
@restore_prefix:
        lda     overlay_text,y
        sta     (unpack_dest),y
        dey
        bpl     @restore_prefix
        ldx     #0
@zp:    lda     dos_zp_prog,x
        sta     $00,x
        inx
        bne     @zp
        rts
unpack_header:
        lda     $5800,y
        rts
unpack_get:
        lda     unpack_source
        bne     :+
        dec     unpack_source+1
:       dec     unpack_source
        ldy     #0
        lda     (unpack_source),y
        rts
