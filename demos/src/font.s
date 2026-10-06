; =============================================
; FONT — the 256 CP437 glyphs of the Beautiful Boot 8x8 font on the HGR screen
; VERHILLE Arnaud - 2026. Apple II port of POM1's sketchs/gen2/
; demo_hgr_bbfont_show (HGR_BBFontShow.asm, GEN2 card). The captions went to
; the Apple-1 terminal: here they sit on the 4 text lines of the mixed screen,
; the grid moves up to stay above them, any key returns to the DEMO menu
; (BLOAD FONT + CALL 24576). Font: Michael Pohoreski. GPL-3.0.
; =============================================
; Displays all 256 code points from fonts/font_codepage_437_8x8.png
; (linear CP437 order, index = IBM code point).
;
; Assemble with cc65:
;   Build: make
;
; Grid: 16 columns x 16 rows. Each cell 14x16 px (7-bit glyph + pad byte).
; Row pitch 10 scanlines, rows 0..150: every glyph above the mixed-mode text.
; Loop exit: gidx wraps 255→0 (8-bit), so use BNE after INC, not CMP #256.
; =============================================

.include "apple2.inc"

; --- Zero page ---
.zeropage
            .res 2
cur_x:      .res 1
cur_y:      .res 1
ptr_lo:     .res 1
ptr_hi:     .res 1
gidx:       .res 1
cellcol:    .res 1
fpl:        .res 1
fph:        .res 1
cline:      .res 1
row_tmp:    .res 1

.code

main:
        APPLE2_PREAMBLE_CALL            ; started by CALL from the DEMO menu
        JSR apple2_zp_save
        JSR hgr_init_clear              ; HGR page 1, cleared before it shows
        LDA MIXSET                      ; 4 text lines under the grid
        JSR HOME
        LDA #20                         ; first visible text row
        STA CV
        JSR VTAB
        LDA #<str_title
        LDX #>str_title
        JSR print_str_ax

        LDA #$00
        STA gidx

@show:  LDA gidx
        AND #$0F
        STA cellcol             ; column 0..15
        LDA gidx
        LSR A
        LSR A
        LSR A
        LSR A
        TAX                     ; row 0..15
        LDA row_y_base,X
        STA cur_y

        LDA gidx
        LDX cellcol
        JSR draw_glyph_cell

        INC gidx
        BNE @show               ; 256 glyphs: stop when gidx wraps 255→0

        LDA #<str_footer
        LDX #>str_footer
        JSR print_str_ax

        JSR wait_key
        JMP apple2_return               ; ZP + text screen back, RTS to the menu

; --- print_str_ax: dev/lib/apple2/print.asm (COUT). ---
.include "print.asm"

; --- Draw one glyph: A = CP437 index 0..255, X = column 0..15, cur_y = top ---
draw_glyph_cell:
        STA gidx
        STX cellcol

        LDA #$00
        STA fph
        LDA gidx
        ASL A
        ROL fph
        ASL A
        ROL fph
        ASL A
        ROL fph
        CLC
        ADC #<bbfont
        STA fpl
        LDA fph
        ADC #>bbfont
        STA fph

        LDX #$00
@sc:    STX cline
        TXA
        CLC
        ADC cur_y
        TAY
        LDA hgr_lo,Y
        STA ptr_lo
        LDA hgr_hi,Y
        STA ptr_hi

        LDY cline
        CPY #$08
        BCS @blank
        LDA (fpl),Y
        JMP @writ
@blank: LDA #$00
@writ:  PHA
        LDA cellcol
        ASL A
        TAY
        PLA
        STA (ptr_lo),Y
        INY
        LDA #$00
        STA (ptr_lo),Y

        LDX cline
        INX
        CPX #$10
        BCC @sc
        RTS

; --- Top scanline for each of 16 rows (pitch 10, from line 0: the last glyph
;     row ends at 157, above the mixed-mode text that starts at 160) ---
row_y_base:
        .byte   0,  10,  20,  30,  40,  50,  60,  70
        .byte  80,  90, 100, 110, 120, 130, 140, 150

str_title:
        .byte "FONT: BEAUTIFUL BOOT 8X8, CP437", $0D
        .byte "256 GLYPHS, IBM PC ORDER $00-$FF", $0D, 0

str_footer:
        .byte "ANY KEY: BACK TO THE MENU", 0

; all 256 glyphs: the demo shows the whole code page
BBFONT_FIRST = $00
BBFONT_LAST  = $FF
.include "bbfont.inc"
.include "hgr_scanline.inc"      ; hgr_lo / hgr_hi
.include "hgr.asm"               ; dev/lib/apple2: hgr_init_clear
.include "kbd.asm"               ; wait_key
.include "exit.asm"              ; apple2_zp_save / apple2_return
