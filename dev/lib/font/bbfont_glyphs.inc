; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; =============================================================================
; bbfont_glyphs.inc -- MASTER of the Beautiful Boot 8x8 font (CP437, 256 glyphs)
; =============================================================================
; One `bbglyph code, r0..r7` line per glyph: 8 rows top->bottom, bit 0 =
; leftmost pixel, bit 7 always clear (a glyph is 7 px wide, HGR byte order).
;   $20-$7F  Beautiful Boot (Michael Pohoreski, apple2_hgr_font_tutorial),
;            AND #$7F + 8 rows reversed into HGR order
;   $00-$1F, $80-$FF  CP437 box drawing and symbols (from POM1's
;            font_codepage_437_8x8.png)
;
; Never include this file directly: bbfont.inc defines the `bbglyph` macro
; that keeps only the requested range, and dev/tools/fonts.py reads it for
; every C table and build tool. Edit a glyph HERE, then run
;   python3 dev/tools/fonts.py
; =============================================================================

        bbglyph $00, $00,$00,$00,$00,$00,$00,$00,$00  ; PNG
        bbglyph $01, $7E,$01,$25,$01,$3D,$19,$01,$7E  ; PNG
        bbglyph $02, $7E,$7F,$5B,$7F,$43,$67,$7F,$7E  ; PNG
        bbglyph $03, $36,$7F,$7F,$7F,$3E,$1C,$08,$00  ; PNG
        bbglyph $04, $08,$1C,$3E,$7F,$3E,$1C,$08,$10  ; PNG
        bbglyph $05, $1C,$3E,$1C,$7F,$7F,$3E,$1C,$3E  ; PNG
        bbglyph $06, $08,$08,$1C,$3E,$7F,$3E,$1C,$3E  ; PNG
        bbglyph $07, $00,$00,$18,$3C,$3C,$18,$00,$00  ; PNG
        bbglyph $08, $7F,$7F,$67,$43,$43,$67,$7F,$7F  ; PNG
        bbglyph $09, $00,$3C,$66,$42,$42,$66,$3C,$00  ; PNG
        bbglyph $0A, $7F,$43,$19,$3D,$3D,$19,$43,$7F  ; PNG
        bbglyph $0B, $70,$60,$70,$3E,$33,$33,$33,$1E  ; PNG
        bbglyph $0C, $3C,$66,$66,$66,$3C,$18,$7E,$18  ; PNG
        bbglyph $0D, $7C,$4C,$7C,$0C,$0C,$0E,$0F,$07  ; PNG
        bbglyph $0E, $7E,$46,$7E,$46,$46,$66,$67,$03  ; PNG
        bbglyph $0F, $19,$5A,$3C,$67,$67,$3C,$5A,$19  ; PNG
        bbglyph $10, $01,$07,$1F,$7F,$1F,$07,$01,$00  ; PNG
        bbglyph $11, $40,$70,$7C,$7F,$7C,$70,$40,$00  ; PNG
        bbglyph $12, $18,$3C,$7E,$18,$18,$7E,$3C,$18  ; PNG
        bbglyph $13, $66,$66,$66,$66,$66,$00,$66,$00  ; PNG
        bbglyph $14, $7E,$5B,$5B,$5E,$58,$58,$58,$00  ; PNG
        bbglyph $15, $7C,$46,$1C,$36,$36,$1C,$33,$1E  ; PNG
        bbglyph $16, $00,$00,$00,$00,$7E,$7E,$7E,$00  ; PNG
        bbglyph $17, $18,$3C,$7E,$18,$7E,$3C,$18,$7F  ; PNG
        bbglyph $18, $18,$3C,$7E,$18,$18,$18,$18,$00  ; PNG
        bbglyph $19, $18,$18,$18,$18,$7E,$3C,$18,$00  ; PNG
        bbglyph $1A, $00,$18,$30,$7F,$30,$18,$00,$00  ; PNG
        bbglyph $1B, $00,$0C,$06,$7F,$06,$0C,$00,$00  ; PNG
        bbglyph $1C, $00,$00,$03,$03,$03,$7F,$00,$00  ; PNG
        bbglyph $1D, $00,$24,$66,$7F,$66,$24,$00,$00  ; PNG
        bbglyph $1E, $00,$18,$3C,$7E,$7F,$7F,$00,$00  ; PNG
        bbglyph $1F, $00,$7F,$7F,$7E,$3C,$18,$00,$00  ; PNG
        bbglyph $20, $00,$00,$00,$00,$00,$00,$00,$00  ; BB ' '
        bbglyph $21, $07,$07,$07,$07,$00,$07,$07,$00  ; BB '!'
        bbglyph $22, $36,$36,$24,$36,$00,$00,$00,$00  ; BB '"'
        bbglyph $23, $1E,$1E,$3F,$1E,$3F,$1E,$1E,$00  ; BB '#'
        bbglyph $24, $0C,$3E,$03,$1E,$30,$1F,$0C,$00  ; BB '$'
        bbglyph $25, $37,$37,$18,$0C,$06,$3B,$3B,$00  ; BB '%'
        bbglyph $26, $06,$0F,$06,$0F,$3B,$1B,$2E,$00  ; BB '&'
        bbglyph $27, $0C,$0C,$08,$0C,$00,$00,$00,$00  ; BB '\''
        bbglyph $28, $38,$1C,$0E,$0E,$0E,$1C,$38,$00  ; BB '('
        bbglyph $29, $07,$0E,$1C,$1C,$1C,$0E,$07,$00  ; BB ')'
        bbglyph $2A, $08,$2A,$1C,$3E,$1C,$2A,$08,$00  ; BB '*'
        bbglyph $2B, $0C,$0C,$3F,$3F,$0C,$0C,$00,$00  ; BB '+'
        bbglyph $2C, $00,$00,$00,$00,$00,$07,$06,$03  ; BB ','
        bbglyph $2D, $00,$00,$3E,$3E,$00,$00,$00,$00  ; BB '-'
        bbglyph $2E, $00,$00,$00,$00,$00,$07,$07,$00  ; BB '.'
        bbglyph $2F, $60,$70,$38,$1C,$0E,$07,$03,$00  ; BB '/'
        bbglyph $30, $1E,$33,$33,$33,$33,$33,$1E,$00  ; BB '0'
        bbglyph $31, $0C,$0E,$0F,$0C,$0C,$0C,$3F,$00  ; BB '1'
        bbglyph $32, $1E,$3F,$33,$38,$0E,$3F,$3F,$00  ; BB '2'
        bbglyph $33, $1E,$3F,$30,$3E,$30,$3F,$1E,$00  ; BB '3'
        bbglyph $34, $38,$3C,$36,$33,$3F,$30,$30,$00  ; BB '4'
        bbglyph $35, $3F,$3F,$03,$1F,$30,$3F,$1E,$00  ; BB '5'
        bbglyph $36, $1E,$3F,$03,$1F,$33,$3F,$1E,$00  ; BB '6'
        bbglyph $37, $3F,$3F,$30,$18,$0C,$0C,$0C,$00  ; BB '7'
        bbglyph $38, $1E,$3F,$33,$1E,$33,$3F,$1E,$00  ; BB '8'
        bbglyph $39, $1E,$3F,$33,$3E,$30,$3F,$1E,$00  ; BB '9'
        bbglyph $3A, $00,$1C,$1C,$00,$00,$1C,$1C,$00  ; BB ':'
        bbglyph $3B, $00,$07,$07,$00,$00,$07,$06,$03  ; BB ';'
        bbglyph $3C, $70,$38,$1C,$0E,$1C,$38,$70,$00  ; BB '<'
        bbglyph $3D, $00,$00,$3E,$00,$3E,$00,$00,$00  ; BB '='
        bbglyph $3E, $07,$0E,$1C,$38,$1C,$0E,$07,$00  ; BB '>'
        bbglyph $3F, $1E,$3F,$33,$18,$0C,$00,$0C,$00  ; BB '?'
        bbglyph $40, $1E,$33,$33,$3B,$3B,$03,$3E,$00  ; BB '@'
        bbglyph $41, $1E,$3F,$33,$3F,$3F,$33,$33,$00  ; BB 'A'
        bbglyph $42, $1F,$3F,$33,$1F,$33,$3F,$1F,$00  ; BB 'B'
        bbglyph $43, $1E,$3F,$33,$03,$33,$3F,$1E,$00  ; BB 'C'
        bbglyph $44, $1F,$3F,$33,$33,$33,$3F,$1F,$00  ; BB 'D'
        bbglyph $45, $3F,$3F,$03,$1F,$03,$3F,$3F,$00  ; BB 'E'
        bbglyph $46, $3F,$3F,$03,$1F,$1F,$03,$03,$00  ; BB 'F'
        bbglyph $47, $1E,$3F,$03,$3B,$33,$3F,$1E,$00  ; BB 'G'
        bbglyph $48, $33,$33,$33,$3F,$3F,$33,$33,$00  ; BB 'H'
        bbglyph $49, $3F,$3F,$0C,$0C,$0C,$3F,$3F,$00  ; BB 'I'
        bbglyph $4A, $30,$30,$30,$30,$33,$3F,$1E,$00  ; BB 'J'
        bbglyph $4B, $33,$3B,$1F,$0F,$1F,$3B,$33,$00  ; BB 'K'
        bbglyph $4C, $03,$03,$03,$03,$03,$3F,$3F,$00  ; BB 'L'
        bbglyph $4D, $33,$3F,$33,$33,$33,$33,$33,$00  ; BB 'M'
        bbglyph $4E, $33,$33,$37,$3F,$3B,$33,$33,$00  ; BB 'N'
        bbglyph $4F, $1E,$3F,$33,$33,$33,$3F,$1E,$00  ; BB 'O'
        bbglyph $50, $1F,$3F,$33,$3F,$1F,$03,$03,$00  ; BB 'P'
        bbglyph $51, $1E,$33,$33,$33,$3B,$1E,$38,$00  ; PNG 'Q' CP437 PNG
        bbglyph $52, $1F,$3F,$33,$3F,$1F,$3B,$33,$00  ; BB 'R'
        bbglyph $53, $1E,$33,$03,$1E,$30,$33,$1E,$00  ; BB 'S'
        bbglyph $54, $3F,$3F,$0C,$0C,$0C,$0C,$0C,$00  ; BB 'T'
        bbglyph $55, $33,$33,$33,$33,$33,$3F,$1E,$00  ; BB 'U'
        bbglyph $56, $33,$33,$33,$33,$33,$1E,$0C,$00  ; BB 'V'
        bbglyph $57, $33,$33,$33,$33,$33,$3F,$33,$00  ; BB 'W'
        bbglyph $58, $33,$33,$1E,$0C,$1E,$33,$33,$00  ; BB 'X'
        bbglyph $59, $33,$33,$33,$1E,$0C,$0C,$0C,$00  ; BB 'Y'
        bbglyph $5A, $3F,$3F,$18,$0C,$06,$3F,$3F,$00  ; BB 'Z'
        bbglyph $5B, $3C,$3C,$0C,$0C,$0C,$3C,$3C,$00  ; BB '['
        bbglyph $5C, $03,$07,$0E,$1C,$38,$70,$60,$00  ; BB '\\'
        bbglyph $5D, $0F,$0F,$0C,$0C,$0C,$0F,$0F,$00  ; BB ']'
        bbglyph $5E, $0C,$1E,$3F,$00,$00,$00,$00,$00  ; BB '^'
        bbglyph $5F, $00,$00,$00,$00,$00,$7F,$7F,$00  ; BB '_'
        bbglyph $60, $06,$0C,$18,$00,$00,$00,$00,$00  ; BB '`'
        bbglyph $61, $00,$00,$1E,$30,$3E,$33,$3E,$00  ; BB 'a'
        bbglyph $62, $03,$03,$1F,$33,$33,$33,$1F,$00  ; BB 'b'
        bbglyph $63, $00,$00,$1E,$33,$03,$33,$1E,$00  ; BB 'c'
        bbglyph $64, $30,$30,$3E,$33,$33,$33,$3E,$00  ; BB 'd'
        bbglyph $65, $00,$00,$1E,$33,$1F,$03,$1E,$00  ; BB 'e'
        bbglyph $66, $1C,$36,$06,$1F,$06,$06,$06,$00  ; BB 'f'
        bbglyph $67, $00,$00,$1E,$33,$33,$3E,$30,$1E  ; BB 'g'
        bbglyph $68, $03,$03,$1F,$33,$33,$33,$33,$00  ; BB 'h'
        bbglyph $69, $00,$0C,$00,$0C,$0C,$0C,$0C,$00  ; BB 'i'
        bbglyph $6A, $30,$00,$30,$30,$30,$33,$33,$1E  ; BB 'j'
        bbglyph $6B, $03,$03,$33,$1B,$0F,$1B,$33,$00  ; BB 'k'
        bbglyph $6C, $0E,$0C,$0C,$0C,$0C,$0C,$1E,$00  ; BB 'l'
        bbglyph $6D, $00,$00,$33,$3F,$33,$33,$33,$00  ; BB 'm'
        bbglyph $6E, $00,$00,$1F,$33,$33,$33,$33,$00  ; BB 'n'
        bbglyph $6F, $00,$00,$1E,$33,$33,$33,$1E,$00  ; BB 'o'
        bbglyph $70, $00,$00,$1F,$33,$33,$1F,$03,$03  ; BB 'p'
        bbglyph $71, $00,$00,$3E,$33,$33,$3E,$30,$30  ; BB 'q'
        bbglyph $72, $00,$00,$1F,$33,$03,$03,$03,$00  ; BB 'r'
        bbglyph $73, $00,$00,$1E,$03,$1E,$30,$1E,$00  ; BB 's'
        bbglyph $74, $06,$06,$1F,$06,$06,$36,$1C,$00  ; BB 't'
        bbglyph $75, $00,$00,$33,$33,$33,$33,$3E,$00  ; BB 'u'
        bbglyph $76, $00,$00,$33,$33,$33,$1E,$0C,$00  ; BB 'v'
        bbglyph $77, $00,$00,$33,$33,$33,$3F,$33,$00  ; BB 'w'
        bbglyph $78, $00,$00,$33,$1E,$0C,$1E,$33,$00  ; BB 'x'
        bbglyph $79, $00,$00,$33,$33,$33,$3E,$30,$1E  ; BB 'y'
        bbglyph $7A, $00,$00,$3F,$18,$0C,$06,$3F,$00  ; BB 'z'
        bbglyph $7B, $1C,$1E,$06,$07,$06,$1E,$1C,$00  ; BB '{'
        bbglyph $7C, $0C,$0C,$0C,$0C,$0C,$0C,$0C,$0C  ; BB '|'
        bbglyph $7D, $0E,$1E,$18,$38,$18,$1E,$0E,$00  ; BB '}'
        bbglyph $7E, $06,$3F,$18,$00,$00,$00,$00,$00  ; BB '~'
        bbglyph $7F, $00,$00,$00,$00,$00,$00,$00,$00  ; BB
        bbglyph $80, $1E,$33,$03,$33,$1E,$18,$30,$1E  ; PNG
        bbglyph $81, $00,$33,$00,$33,$33,$33,$7E,$00  ; PNG
        bbglyph $82, $38,$00,$1E,$33,$3F,$03,$1E,$00  ; PNG
        bbglyph $83, $7E,$43,$3C,$60,$7C,$66,$7C,$00  ; PNG
        bbglyph $84, $33,$00,$1E,$30,$3E,$33,$7E,$00  ; PNG
        bbglyph $85, $07,$00,$1E,$30,$3E,$33,$7E,$00  ; PNG
        bbglyph $86, $0C,$0C,$1E,$30,$3E,$33,$7E,$00  ; PNG
        bbglyph $87, $00,$00,$1E,$03,$03,$1E,$30,$1C  ; PNG
        bbglyph $88, $7E,$43,$3C,$66,$7E,$06,$3C,$00  ; PNG
        bbglyph $89, $33,$00,$1E,$33,$3F,$03,$1E,$00  ; PNG
        bbglyph $8A, $07,$00,$1E,$33,$3F,$03,$1E,$00  ; PNG
        bbglyph $8B, $33,$00,$0E,$0C,$0C,$0C,$1E,$00  ; PNG
        bbglyph $8C, $3E,$63,$1C,$18,$18,$18,$3C,$00  ; PNG
        bbglyph $8D, $07,$00,$0E,$0C,$0C,$0C,$1E,$00  ; PNG
        bbglyph $8E, $63,$1C,$36,$63,$7F,$63,$63,$00  ; PNG
        bbglyph $8F, $0C,$0C,$00,$1E,$33,$3F,$33,$00  ; PNG
        bbglyph $90, $38,$00,$3F,$06,$1E,$06,$3F,$00  ; PNG
        bbglyph $91, $00,$00,$7E,$30,$7E,$33,$7E,$00  ; PNG
        bbglyph $92, $7C,$36,$33,$7F,$33,$33,$73,$00  ; PNG
        bbglyph $93, $1E,$33,$00,$1E,$33,$33,$1E,$00  ; PNG
        bbglyph $94, $00,$33,$00,$1E,$33,$33,$1E,$00  ; PNG
        bbglyph $95, $00,$07,$00,$1E,$33,$33,$1E,$00  ; PNG
        bbglyph $96, $1E,$33,$00,$33,$33,$33,$7E,$00  ; PNG
        bbglyph $97, $00,$07,$00,$33,$33,$33,$7E,$00  ; PNG
        bbglyph $98, $00,$33,$00,$33,$33,$3E,$30,$1F  ; PNG
        bbglyph $99, $43,$18,$3C,$66,$66,$3C,$18,$00  ; PNG
        bbglyph $9A, $33,$00,$33,$33,$33,$33,$1E,$00  ; PNG
        bbglyph $9B, $18,$18,$7E,$03,$03,$7E,$18,$18  ; PNG
        bbglyph $9C, $1C,$36,$26,$0F,$06,$67,$3F,$00  ; PNG
        bbglyph $9D, $33,$33,$1E,$3F,$0C,$3F,$0C,$0C  ; PNG
        bbglyph $9E, $1F,$33,$33,$5F,$63,$73,$63,$63  ; PNG
        bbglyph $9F, $70,$58,$18,$3C,$18,$18,$1B,$0E  ; PNG
        bbglyph $A0, $38,$00,$1E,$30,$3E,$33,$7E,$00  ; PNG
        bbglyph $A1, $1C,$00,$0E,$0C,$0C,$0C,$1E,$00  ; PNG
        bbglyph $A2, $00,$38,$00,$1E,$33,$33,$1E,$00  ; PNG
        bbglyph $A3, $00,$38,$00,$33,$33,$33,$7E,$00  ; PNG
        bbglyph $A4, $00,$1F,$00,$1F,$33,$33,$33,$00  ; PNG
        bbglyph $A5, $3F,$00,$33,$37,$3F,$3B,$33,$00  ; PNG
        bbglyph $A6, $3C,$36,$36,$7C,$00,$7E,$00,$00  ; PNG
        bbglyph $A7, $1C,$36,$36,$1C,$00,$3E,$00,$00  ; PNG
        bbglyph $A8, $0C,$00,$0C,$06,$03,$33,$1E,$00  ; PNG
        bbglyph $A9, $00,$00,$00,$3F,$03,$03,$00,$00  ; PNG
        bbglyph $AA, $00,$00,$00,$3F,$30,$30,$00,$00  ; PNG
        bbglyph $AB, $43,$63,$33,$7B,$4C,$66,$33,$70  ; PNG
        bbglyph $AC, $43,$63,$33,$5B,$6C,$76,$73,$40  ; PNG
        bbglyph $AD, $18,$18,$00,$18,$18,$18,$18,$00  ; PNG
        bbglyph $AE, $00,$4C,$66,$33,$66,$4C,$00,$00  ; PNG
        bbglyph $AF, $00,$33,$66,$4C,$66,$33,$00,$00  ; PNG
        bbglyph $B0, $44,$11,$44,$11,$44,$11,$44,$11  ; PNG
        bbglyph $B1, $2A,$55,$2A,$55,$2A,$55,$2A,$55  ; PNG
        bbglyph $B2, $5B,$6E,$5B,$77,$5B,$6E,$5B,$77  ; PNG
        bbglyph $B3, $18,$18,$18,$18,$18,$18,$18,$18  ; PNG
        bbglyph $B4, $18,$18,$18,$18,$1F,$18,$18,$18  ; PNG
        bbglyph $B5, $18,$18,$1F,$18,$1F,$18,$18,$18  ; PNG
        bbglyph $B6, $6C,$6C,$6C,$6C,$6F,$6C,$6C,$6C  ; PNG
        bbglyph $B7, $00,$00,$00,$00,$7F,$6C,$6C,$6C  ; PNG
        bbglyph $B8, $00,$00,$1F,$18,$1F,$18,$18,$18  ; PNG
        bbglyph $B9, $6C,$6C,$6F,$60,$6F,$6C,$6C,$6C  ; PNG
        bbglyph $BA, $6C,$6C,$6C,$6C,$6C,$6C,$6C,$6C  ; PNG
        bbglyph $BB, $00,$00,$7F,$60,$6F,$6C,$6C,$6C  ; PNG
        bbglyph $BC, $6C,$6C,$6F,$60,$7F,$00,$00,$00  ; PNG
        bbglyph $BD, $6C,$6C,$6C,$6C,$7F,$00,$00,$00  ; PNG
        bbglyph $BE, $18,$18,$1F,$18,$1F,$00,$00,$00  ; PNG
        bbglyph $BF, $00,$00,$00,$00,$1F,$18,$18,$18  ; PNG
        bbglyph $C0, $18,$18,$18,$18,$78,$00,$00,$00  ; PNG
        bbglyph $C1, $18,$18,$18,$18,$7F,$00,$00,$00  ; PNG
        bbglyph $C2, $00,$00,$00,$00,$7F,$18,$18,$18  ; PNG
        bbglyph $C3, $18,$18,$18,$18,$78,$18,$18,$18  ; PNG
        bbglyph $C4, $00,$00,$00,$00,$7F,$00,$00,$00  ; PNG
        bbglyph $C5, $18,$18,$18,$18,$7F,$18,$18,$18  ; PNG
        bbglyph $C6, $18,$18,$78,$18,$78,$18,$18,$18  ; PNG
        bbglyph $C7, $6C,$6C,$6C,$6C,$6C,$6C,$6C,$6C  ; PNG
        bbglyph $C8, $6C,$6C,$6C,$0C,$7C,$00,$00,$00  ; PNG
        bbglyph $C9, $00,$00,$7C,$0C,$6C,$6C,$6C,$6C  ; PNG
        bbglyph $CA, $6C,$6C,$6F,$00,$7F,$00,$00,$00  ; PNG
        bbglyph $CB, $00,$00,$7F,$00,$6F,$6C,$6C,$6C  ; PNG
        bbglyph $CC, $6C,$6C,$6C,$0C,$6C,$6C,$6C,$6C  ; PNG
        bbglyph $CD, $00,$00,$7F,$00,$7F,$00,$00,$00  ; PNG
        bbglyph $CE, $6C,$6C,$6F,$00,$6F,$6C,$6C,$6C  ; PNG
        bbglyph $CF, $18,$18,$7F,$00,$7F,$00,$00,$00  ; PNG
        bbglyph $D0, $6C,$6C,$6C,$6C,$7F,$00,$00,$00  ; PNG
        bbglyph $D1, $00,$00,$7F,$00,$7F,$18,$18,$18  ; PNG
        bbglyph $D2, $00,$00,$00,$00,$7F,$6C,$6C,$6C  ; PNG
        bbglyph $D3, $6C,$6C,$6C,$6C,$7C,$00,$00,$00  ; PNG
        bbglyph $D4, $18,$18,$78,$18,$78,$00,$00,$00  ; PNG
        bbglyph $D5, $00,$00,$78,$18,$78,$18,$18,$18  ; PNG
        bbglyph $D6, $00,$00,$00,$00,$7C,$6C,$6C,$6C  ; PNG
        bbglyph $D7, $6C,$6C,$6C,$6C,$7F,$6C,$6C,$6C  ; PNG
        bbglyph $D8, $18,$18,$7F,$18,$7F,$18,$18,$18  ; PNG
        bbglyph $D9, $18,$18,$18,$18,$1F,$00,$00,$00  ; PNG
        bbglyph $DA, $00,$00,$00,$00,$78,$18,$18,$18  ; PNG
        bbglyph $DB, $7F,$7F,$7F,$7F,$7F,$7F,$7F,$7F  ; PNG
        bbglyph $DC, $00,$00,$00,$00,$7F,$7F,$7F,$7F  ; PNG
        bbglyph $DD, $0F,$0F,$0F,$0F,$0F,$0F,$0F,$0F  ; PNG
        bbglyph $DE, $70,$70,$70,$70,$70,$70,$70,$70  ; PNG
        bbglyph $DF, $7F,$7F,$7F,$7F,$00,$00,$00,$00  ; PNG
        bbglyph $E0, $00,$00,$6E,$3B,$13,$3B,$6E,$00  ; PNG
        bbglyph $E1, $00,$1E,$33,$1F,$33,$1F,$03,$03  ; PNG
        bbglyph $E2, $00,$3F,$33,$03,$03,$03,$03,$00  ; PNG
        bbglyph $E3, $00,$7F,$36,$36,$36,$36,$36,$00  ; PNG
        bbglyph $E4, $3F,$33,$06,$0C,$06,$33,$3F,$00  ; PNG
        bbglyph $E5, $00,$00,$7E,$1B,$1B,$1B,$0E,$00  ; PNG
        bbglyph $E6, $00,$66,$66,$66,$66,$3E,$06,$03  ; PNG
        bbglyph $E7, $00,$6E,$3B,$18,$18,$18,$18,$00  ; PNG
        bbglyph $E8, $3F,$0C,$1E,$33,$33,$1E,$0C,$3F  ; PNG
        bbglyph $E9, $1C,$36,$63,$7F,$63,$36,$1C,$00  ; PNG
        bbglyph $EA, $1C,$36,$63,$63,$36,$36,$77,$00  ; PNG
        bbglyph $EB, $38,$0C,$18,$3E,$33,$33,$1E,$00  ; PNG
        bbglyph $EC, $00,$00,$7E,$5B,$5B,$7E,$00,$00  ; PNG
        bbglyph $ED, $60,$30,$7E,$5B,$5B,$7E,$06,$03  ; PNG
        bbglyph $EE, $1C,$06,$03,$1F,$03,$06,$1C,$00  ; PNG
        bbglyph $EF, $1E,$33,$33,$33,$33,$33,$33,$00  ; PNG
        bbglyph $F0, $00,$3F,$00,$3F,$00,$3F,$00,$00  ; PNG
        bbglyph $F1, $0C,$0C,$3F,$0C,$0C,$00,$3F,$00  ; PNG
        bbglyph $F2, $06,$0C,$18,$0C,$06,$00,$3F,$00  ; PNG
        bbglyph $F3, $18,$0C,$06,$0C,$18,$00,$3F,$00  ; PNG
        bbglyph $F4, $70,$58,$58,$18,$18,$18,$18,$18  ; PNG
        bbglyph $F5, $18,$18,$18,$18,$18,$1B,$1B,$0E  ; PNG
        bbglyph $F6, $0C,$0C,$00,$3F,$00,$0C,$0C,$00  ; PNG
        bbglyph $F7, $00,$6E,$3B,$00,$6E,$3B,$00,$00  ; PNG
        bbglyph $F8, $1C,$36,$36,$1C,$00,$00,$00,$00  ; PNG
        bbglyph $F9, $00,$00,$00,$18,$18,$00,$00,$00  ; PNG
        bbglyph $FA, $00,$00,$00,$00,$18,$00,$00,$00  ; PNG
        bbglyph $FB, $70,$30,$30,$30,$37,$36,$3C,$38  ; PNG
        bbglyph $FC, $1E,$36,$36,$36,$36,$00,$00,$00  ; PNG
        bbglyph $FD, $0E,$18,$0C,$06,$1E,$00,$00,$00  ; PNG
        bbglyph $FE, $00,$00,$3C,$3C,$3C,$3C,$00,$00  ; PNG
        bbglyph $FF, $00,$00,$00,$00,$00,$00,$00,$00  ; PNG
