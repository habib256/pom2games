; VERHILLE Arnaud — GPL-3.0. LORES color number -> DHGR byte pattern
; (aux even, main even, aux odd, main odd): Apple IIe Technical Note #3.
.export _dhgr_prepare_pattern, dhgr_color_patterns
.import _dhgr_pattern
.rodata
; Four bytes per color; the color's nibble is rotated so that bit 0 of
; aux byte 0 is the first displayed dot. Index = color*4 + (byte & 3).
dhgr_color_patterns:
.repeat 16,C
.repeat 4,I
.byte (((((C>>1)|(C<<3))&15)*$1111) >> ((I*7)&3)) & $7F
.endrepeat
.endrepeat
.code
; void dhgr_prepare_pattern(unsigned char color), color masked to 0..15.
_dhgr_prepare_pattern:
        and #15
        asl
        asl
        tax
        lda dhgr_color_patterns,x
        sta _dhgr_pattern
        lda dhgr_color_patterns+1,x
        sta _dhgr_pattern+1
        lda dhgr_color_patterns+2,x
        sta _dhgr_pattern+2
        lda dhgr_color_patterns+3,x
        sta _dhgr_pattern+3
        rts
