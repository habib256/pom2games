; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ported from POM1 dev/lib/tms9918 @ e399808 (text_bitmap.asm)
; ============================================================================
; text_bitmap.asm  --  8x8 monochrome glyph blitter for TMS9918 Mode-2
; ----------------------------------------------------------------------------
; Renders a Beautiful Boot glyph (bbfont_tms.inc, ASCII $20-$7F) into the bitmap pattern table at the
; cell aligned to (pix_x, pix_y), and tints the matching colour cell with
; pen_color. Lifted from TMS_Logo_16k.asm so any Mode-2 project that wants
; on-bitmap text overlays (scores, "GAME OVER", tutorial captions, narrator
; bubbles) can .import the routine instead of re-implementing it.
;
; Port: POM1 read the Apple-1 charmap.rom (1 KB, bit-reversed on the fly,
; gated by CODETANK_BUILD); this port blits tms_bbfont from bbfont_tms.inc
; (768 bytes, already MSB-left), included here when the routine is used.
; Codes below $20 draw as $20..$3F (A AND $7F, minus $20, AND $7F).
;
; ----------------------------------------------------------------------------
; API:
;   text_blit_glyph        A = ASCII char (bit 7 ignored). Reads pix_x/pix_y as
;                     the cell-aligned pixel coordinate of the glyph's
;                     top-left corner; the routine masks low 3 bits to
;                     guarantee cell alignment, so callers can pass
;                     unaligned values. Tints the cell with pen_color.
;                     Clobbers A, X, Y, mptr_lo/hi, tmp, tmp2,
;                     pix_addr_lo/hi.
;
; Caller-provided ZP (must be .exportzp'd by the caller):
;   tmp, tmp2         scratch (1 byte each)
;   mptr_lo, mptr_hi  16-bit cursor into tms_bbfont (1 byte each)
;
; Lib-provided ZP (already exported by tms9918m2.asm):
;   pix_x, pix_y                 input position (cell-aligned on entry/exit)
;   pix_addr_lo/hi               clobbered, holds VRAM cursor
;   pen_color                    foreground colour for the colour cell
; ============================================================================

.ifndef _TEXT_BITMAP_ASM_LOADED_
_TEXT_BITMAP_ASM_LOADED_ = 1

.include "tms9918.inc"



.segment "CODE"


.ifref text_blit_glyph
; ----------------------------------------------------------------------------
; text_blit_glyph: paint one 8x8 glyph + its colour cell. See module header for
;   the full register / ZP contract.
; ----------------------------------------------------------------------------
text_blit_glyph:
        AND #$7F                  ; clamp to printable range
        SEC
        SBC #$20                  ; tms_bbfont starts at ' '
        AND #$7F
        STA tmp                   ; tmp:tmp2 = A * 8 (16-bit shift)
        LDA #0
        STA tmp2
        ASL tmp
        ROL tmp2
        ASL tmp
        ROL tmp2
        ASL tmp
        ROL tmp2
        CLC
        LDA tmp
        ADC #<tms_bbfont
        STA mptr_lo
        LDA tmp2
        ADC #>tms_bbfont
        STA mptr_hi
        ; force cell-aligned write addr (low 3 bits of pix_y = 0)
        LDA pix_x
        AND #$F8
        STA pix_x
        LDA pix_y
        AND #$F8
        STA pix_y
        JSR calc_pix_addr
        JSR vdp_set_write
        LDY #0
@row:   LDA (mptr_lo),Y           ; already MSB = leftmost pixel
        JSR     ez_data_w
        INY
        CPY #8
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        BNE @row
        ; --- paint the cell's 8 colour-table bytes with pen_color so callers
        ;     also tint LABEL/SAY text. The colour table mirrors the
        ;     pattern table layout at base $2000, so we can re-prime the
        ;     VDP cursor with the same pix_addr but the $2000 base bit set.
        LDA pix_addr_lo
        JSR     ez_ctrl_w
        LDA pix_addr_hi
        ORA #$60                  ; $20 (colour base) | $40 (write enable)
        JSR     ez_ctrl_w
        LDA pen_color
        ASL
        ASL
        ASL
        ASL                       ; pen_color in high nibble
        ORA #$01                  ; transparent background ($x1)
        LDX #8
@col:   JSR     ez_data_w
        DEX
        BNE @col
        RTS

.include "bbfont_tms.inc"         ; tms_bbfont (guarded: shared with the game)
.endif

.endif  ; _TEXT_BITMAP_ASM_LOADED_
