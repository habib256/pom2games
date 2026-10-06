; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; bbfont.inc -- the Beautiful Boot 8x8 font, sliced to the glyphs you need
; ============================================================================
; Pick the range BEFORE the include (defaults: ASCII $20-$5F, 64 glyphs,
; 512 bytes -- what hgr_text8.asm expects):
;
;     BBFONT_FIRST = $20          ; first CP437 code kept
;     BBFONT_LAST  = $7F          ; last code kept (lowercase too: 96 glyphs)
;     .include "bbfont.inc"
;
; Emits, in the CURRENT segment (include it where your tables live):
;     bbfont                  the table, 8 bytes per glyph, row 0 on top,
;                             bit 0 = leftmost pixel, bit 7 clear
;     BBFONT_FIRST / BBFONT_LAST / BBFONT_COUNT / BBFONT_BYTES_PER_GLYPH
;
; Glyph of character C is at  bbfont + (C - BBFONT_FIRST) * 8. Fonts of the
; whole code page ($00-$FF) cost 2 KB; keep the range tight on a 48 KB game.
;
; Which font when (see README.md in this folder):
;   asm, byte-aligned text   hgr_text8.asm (ht_font_lo/hi -> bbfont) or a
;                            private 8-row STA loop, as chess does
;   C, HGR                   hgr_puts8 / hgr_puts (dev/lib/hgrc, hgr_font[])
;   C, DHGR                  dhgr_puts (same glyphs) or dhgr_small (4x5)
;   build tools              dev/tools/fonts.py (glyph(), double7(), ...)
; ============================================================================

.ifndef _BBFONT_INC_LOADED_
_BBFONT_INC_LOADED_ = 1

.ifndef BBFONT_FIRST
BBFONT_FIRST = $20
.endif
.ifndef BBFONT_LAST
BBFONT_LAST = $5F
.endif
BBFONT_COUNT           = BBFONT_LAST - BBFONT_FIRST + 1
BBFONT_BYTES_PER_GLYPH = 8

.macro bbglyph code, r0, r1, r2, r3, r4, r5, r6, r7
  .if (code >= BBFONT_FIRST) .and (code <= BBFONT_LAST)
        .byte r0, r1, r2, r3, r4, r5, r6, r7
  .endif
.endmacro

bbfont:
.include "bbfont_glyphs.inc"
.assert (* - bbfont) = BBFONT_COUNT * BBFONT_BYTES_PER_GLYPH, error, "bbfont: range mismatch"

.delmacro bbglyph

.endif  ; _BBFONT_INC_LOADED_
