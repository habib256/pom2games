; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; hgr_text8.asm -- byte-aligned 8x8 text for the Apple II HGR framebuffer
; ----------------------------------------------------------------------------
; Cursor-based shared glyph emitter for HGR games. Before this module existed,
; HGR_Chess (putc_hgr), HGR_Rogue (hgr_emit_a) and HGR_Maze3D
; (write_char) each carried a private copy of the same idea: STORE one
; 8x8 glyph byte per scanline at a byte column, with a text cursor.
; CHESS now keeps its cursor adapter over the raw hgr_glyph8.asm core.
;
; The glyph is drawn in STORE mode (a space genuinely blanks its cell),
; 8 scanlines from ht_sl, at byte column ht_col; the cursor advances one
; column per char and wraps VDP-style: when ht_col reaches ht_wrap it
; snaps back to ht_left and ht_sl advances 8 -- so a stream of chars
; walks the screen exactly like the TMS9918 auto-increment write
; pointer, which is what lets TMS-ported print loops run unchanged.
; Set ht_wrap = 40 if you never want the wrap.
;
; UI RULE: native-size (x1) text MUST stay white; only doubled (x2) text
; may be colored. For this emitter, use ht_cm_ev/od=$7F and ht_cbit=$00.
; Tint masks remove thin strokes and make small glyphs harder to read.
;
; Fonts: ht_font_lo/hi -> 8-bytes-per-glyph table for chars $20.. ;
; ht_rev picks the bit order:
;   ht_rev = 0   HGR order (bit 0 = leftmost) -- dev/lib/font/bbfont.inc
;   ht_rev = 1   TMS order (bit 7 = leftmost) -- rows pass through
;                rev7_tab (the glyph's rightmost pixel column is dropped;
;                fine for fonts, which keep a blank right column).
; A program whose font is in HGR order can define HGR_TEXT8_HGR_ORDER before
; the include: ht_rev, the rev7 path and the 256-byte rev7_tab disappear.
; Chars < $20 render as space, $60..$7F fold to uppercase, past the
; 64-glyph window renders as space. ht_sl >= 192 skips the draw (the
; cursor still advances). Partial glyphs at y=185..191 clip at the bottom;
; an off-screen cursor stays off-screen when wrapping.
;
; API:
;   hgr_putc8   A = char (bit 7 tolerated). PRESERVES A, X and Y --
;               ported print loops keep counters in all three, and the
;               TMS write-data macros they emulate preserved everything.
;               Glyph bytes pass through the artifact-colour attributes
;               ht_cm_ev / ht_cm_od (pixel-parity masks, alternating by
;               byte-column parity) + ht_cbit (palette bit): WHITE =
;               $7F/$7F/$00 is the pass-through -- INIT THEM AT BOOT.
;               Glyph bit 7 is always stripped: the palette bit comes
;               from ht_cbit, never from the font data.
;   hgr_puts8   NUL-terminated string at ht_src_lo/hi, may span pages.
;               Preserves X and the source pointer; clobbers A, Y.
;
; Caller provides hgr_lo / hgr_hi (include hgr_scanline.inc). The module
; allocates its own ZP (~12 B) and pulls rev7.inc (shared, guarded).
;
; Consumers in this repo: arkabreakout (bbfont, HGR order, HGR_TEXT8_HGR_ORDER)
; and maze3d (its own font, TMS order) -- one module, both bit orders
; exercised. First written for POM1's game_rogue and game_maze3d; chess keeps
; its private putc_hgr (chess/src/chess.s).
; ============================================================================

.ifndef _HGR_TEXT8_LOADED_
_HGR_TEXT8_LOADED_ = 1

.zeropage
ht_col:     .res 1      ; cursor: dest byte column 0..39 (public)
ht_sl:      .res 1      ; cursor: glyph top scanline (public)
ht_left:    .res 1      ; wrap: column the cursor snaps back to (public)
ht_wrap:    .res 1      ; wrap: first column PAST the text window (public)
ht_font_lo: .res 1      ; -> font, 8 B/glyph, first char $20 (public)
ht_font_hi: .res 1
.ifndef HGR_TEXT8_HGR_ORDER
ht_rev:     .res 1      ; 0 = HGR bit order, 1 = TMS order via rev7_tab
.endif
ht_src_lo:  .res 1      ; hgr_puts8 string pointer (public)
ht_src_hi:  .res 1
ht_a:       .res 1      ; char cache (A preserved across hgr_putc8)
ht_t:       .res 1      ; glyph-pointer math, then this char's pixel mask
ht_g_lo:    .res 1      ; glyph pointer
ht_g_hi:    .res 1
ht_lin_lo:  .res 1      ; scanline pointer
ht_lin_hi:  .res 1
ht_cm_ev:   .res 1      ; colour: pixel mask for EVEN byte columns (public)
ht_cm_od:   .res 1      ; colour: pixel mask for ODD byte columns (public)
ht_cbit:    .res 1      ; colour: palette bit $00/$80 (public)
ht_page:    .res 1      ; HGR page selector, EORed into the scanline
                        ; high byte ($00 = page 1, $60 = page 2). INIT
                        ; AT BOOT; double-buffered games flip it

.code

; ----------------------------------------------------------------------------
; hgr_putc8: draw char A at the cursor, advance + wrap. Preserves A/X/Y.
; ----------------------------------------------------------------------------
hgr_putc8:
        STA ht_a
        TXA
        PHA
        TYA
        PHA
        ; VDP-style wrap at ENTRY: a stream that just filled the window
        ; draws its next char at the head of the next text row.
        LDA ht_col
        CMP ht_wrap
        BCC @nowrap
        LDA ht_left
        STA ht_col
        LDA ht_sl
        CMP #192
        BCS @nowrap             ; off-screen rows stay off-screen
        CLC
        ADC #8
        STA ht_sl
@nowrap:
        LDA ht_sl
        CMP #192
        BCS @out                ; off-screen: skip draw, still advance
        ; glyph index: fold lowercase, map out-of-window to space
        LDA ht_a
        AND #$7F
        CMP #$60
        BCC @nofold
        SBC #$20                ; $60..$7F -> uppercase (C set by the CMP)
@nofold:
        SEC
        SBC #$20
        BCS @sub_ok
        LDA #0                  ; control chars -> space
@sub_ok:
        CMP #64
        BCC @idx_ok
        LDA #0                  ; past the 64-glyph window -> space
@idx_ok:
        ; glyph ptr = font + idx * 8: idx < 64, so the product is 9 bits and
        ; three shifts in A leave its bit 8 in the carry.
        ASL A
        ASL A
        ASL A
        STA ht_t
        LDA #0
        ROL A
        STA ht_g_hi
        LDA ht_t
        CLC
        ADC ht_font_lo
        STA ht_g_lo
        LDA ht_g_hi
        ADC ht_font_hi
        STA ht_g_hi
        ; artifact colour: the pixel mask follows the byte-column parity and
        ; is constant for the 8 rows. WHITE ($7F/$7F/$00) is a pass-through --
        ; the caller's boot MUST init the three attributes (garbage masks =
        ; invisible text on a real cold boot).
        LDA ht_col
        LSR A                   ; C = column parity
        LDA ht_cm_ev
        BCC @c_m
        LDA ht_cm_od
@c_m:   STA ht_t
        LDX #0                  ; glyph row 0..7
@row:   TXA
        CLC
        ADC ht_sl
        TAY
        CPY #192
        BCS @out                ; clip partial glyphs at the bottom edge
        LDA hgr_lo,Y
        STA ht_lin_lo
        LDA hgr_hi,Y
        EOR ht_page
        STA ht_lin_hi
        TXA
        TAY
        LDA (ht_g_lo),Y         ; glyph row byte
.ifndef HGR_TEXT8_HGR_ORDER
        LDY ht_rev
        BEQ @put
        TAY
        LDA rev7_tab,Y          ; TMS bit order -> HGR
@put:
.endif
        AND ht_t                ; glyph bit 7 is always stripped: the palette
        ORA ht_cbit             ; bit comes from ht_cbit, never from the font
        LDY ht_col
        STA (ht_lin_lo),Y       ; STORE: text overwrites its cell
        INX
        CPX #8
        BNE @row
@out:
        INC ht_col
        PLA
        TAY
        PLA
        TAX
        LDA ht_a
        RTS

; ----------------------------------------------------------------------------
; hgr_puts8: print the NUL-terminated string at ht_src_lo/hi. Clobbers A,Y.
; ----------------------------------------------------------------------------
.ifndef HGR_TEXT8_NO_PUTS
hgr_puts8:
        LDA ht_src_hi
        PHA                     ; retain the caller's source pointer
        LDY #0
@lp:    LDA (ht_src_lo),Y
        BEQ @done
        JSR hgr_putc8           ; preserves Y
        INY
        BNE @lp
        INC ht_src_hi           ; Y wrapped: continue with the next 256 bytes
        JMP @lp
@done:  PLA
        STA ht_src_hi
        LDA #0                  ; keep the historical NUL return value
        RTS
.endif

.ifndef HGR_TEXT8_HGR_ORDER
.include "rev7.inc"
.endif

.endif  ; _HGR_TEXT8_LOADED_
