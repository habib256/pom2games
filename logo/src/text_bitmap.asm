; ============================================================================
; text_bitmap.asm -- HGR 8x8 glyph blitter for the GEN2 LOGO "full" build.
; ----------------------------------------------------------------------------
; Drop-in replacement for POM1's dev/lib/tms9918/text_bitmap.asm: same public symbol
; (text_blit_glyph) and the same (A, pix_x, pix_y, pen_color) contract, but it
; paints into the GEN2 HGR framebuffer via hgr_glyph8_or + Beautiful Boot 8x8
; font (bbfont) instead of the TMS9918 pattern/colour tables. Used by LOGO's
; on-bitmap text (HELP / LABEL / SAY / LIST / the buffer editor).
;
; Gated by CODETANK_BUILD, exactly like the TMS module, so the same "full"
; feature flag enables it. Link THIS instead of text_bitmap.asm in a GEN2 build.
;
; API (identical to the TMS version):
;   text_blit_glyph   A = ASCII char (bit 7 ignored). pix_x/pix_y = pixel
;                     top-left of the glyph. Draws an 8x8 glyph in OR mode at
;                     the current pen colour, updating sprite backgrounds.
;                     Clips right/bottom without coordinate wrap. Clobbers A,X,Y,
;                     mptr_lo/hi, tmp, tmp2 and the plotter ZP. pix_x / pix_y
;                     are PRESERVED (put back to the glyph origin): the
;                     shared buffer editor advances pix_x by 8 per glyph and
;                     never reloads pix_y -- upstream left them on the glyph's
;                     last plotted pixel, which drew EDIT's text diagonally.
;
; bbfont encoding: 8 bytes/glyph, row 0 = top, bit 0 = leftmost pixel;
; the shared core packs each row into at most two native screen bytes.
; ============================================================================

.ifdef CODETANK_BUILD

.export text_blit_glyph

.import plot_mode, hgr_lo, hgr_hi, pen_hi_tbl, emote_plot_background
.importzp pix_x, pix_xh, pix_y, pix_mask, pix_addr_lo, pen_color
.importzp tmp, tmp2, mptr_lo, mptr_hi
.globalzp hg_x

.code
text_blit_glyph:
        AND #$7F
        STA tmp
        LDA #0
        STA tmp2
        ASL tmp
        ROL tmp2
        ASL tmp
        ROL tmp2
        ASL tmp
        ROL tmp2
        LDA tmp
        CLC
        ADC #<bbfont
        STA mptr_lo
        LDA tmp2
        ADC #>bbfont
        STA mptr_hi
        LDA pix_x
        STA hg_x
        LDA pix_y
        STA hg_y
        LDA #0
        STA hg_x+1
        STA pix_xh
        STA plot_mode
        JSR hgr_glyph8_or
        LDA hg_y
        STA pix_y                 ; the sprite hook uses the current scanline
        RTS

hg_src = mptr_lo
hg_ptr = pix_addr_lo
hg_lo = tmp
hg_hi = tmp2
hg_color = pen_color
HG_COLOR_TABLE = pen_hi_tbl
HG_OR_HOOK = emote_plot_background
HG_HOOK_Y = pix_y
HG_HOOK_MASK = pix_mask
.include "hgr_glyph8.asm"

BBFONT_FIRST = $00
BBFONT_LAST = $FF
.include "bbfont.inc"
.endif
