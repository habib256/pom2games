; VERHILLE Arnaud — GPL-3.0. Numeric bank derived at assembly from font master.
; Eleven glyphs (space, 0..9), seven phases, eight pairs of packed HGR bytes.
.export hgr_hud8_digitlo, hgr_hud8_digithi
.rodata
.macro bbglyph code, r0,r1,r2,r3,r4,r5,r6,r7
 .if code = $20 .or (code >= $30 .and code <= $39)
 .repeat 7, phase
  .byte ((r0 << phase)&$7f), ((r0 << phase)>>7)
  .byte ((r1 << phase)&$7f), ((r1 << phase)>>7)
  .byte ((r2 << phase)&$7f), ((r2 << phase)>>7)
  .byte ((r3 << phase)&$7f), ((r3 << phase)>>7)
  .byte ((r4 << phase)&$7f), ((r4 << phase)>>7)
  .byte ((r5 << phase)&$7f), ((r5 << phase)>>7)
  .byte ((r6 << phase)&$7f), ((r6 << phase)>>7)
  .byte ((r7 << phase)&$7f), ((r7 << phase)>>7)
 .endrepeat
 .endif
.endmacro
digits:
.include "../font/bbfont_glyphs.inc"
.delmacro bbglyph
.assert (*-digits)=1232, error, "Numeric phase bank size"
hgr_hud8_digitlo:
.repeat 77, glyph
 .byte <(digits + (glyph .mod 11)*112 + (glyph/11)*16)
.endrepeat
hgr_hud8_digithi:
.repeat 77, glyph
 .byte >(digits + (glyph .mod 11)*112 + (glyph/11)*16)
.endrepeat
