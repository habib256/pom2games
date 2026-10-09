; ============================================================================
; hgr_logom2.asm -- LOGO adapter for shared dev/lib/hgr native kernels.
;
; Originally vendored from POM1's dev/lib/gen2/gen2_logom2.asm (the GEN2 HGR backend of
; the Apple-1 LOGO). The GEN2 card is the Apple II video on the Apple-1 bus,
; the interpreter seam is kept, while plotting/lines now come from dev/lib/hgr.
; init_vdp_g2 sets the HGR
; latch, page 1 and AN3, and leaves TEXT / MIXED to screen.asm (TS/SS/FS).
; ----------------------------------------------------------------------------
; Upstream header:
;
; Drop-in replacement for dev/lib/tms9918/tms9918m2.asm: it exposes the SAME
; public seam (symbols + ZP slots) so LOGO's hardware-independent core links
; unchanged, but every pixel lands in the Uncle Bernie GEN2 HGR framebuffer
; ($2000-$3FFF, 280x192 NTSC artifact colour) instead of TMS9918 Mode-2 VRAM.
;
; Public symbols (identical to the TMS backend):
;   init_vdp_g2     -- put the GEN2 card in GRAPHICS+HIRES+PAGE1, seed pen=white
;   clear_bitmap    -- zero the 8 KB HGR framebuffer
;   disable_sprites -- no-op (HGR has no hardware sprites; turtle = software blit)
;   vdp_set_write   -- no-op (HGR is RAM-mapped, no VRAM address latch)
;   vdp_set_read    -- no-op
;   calc_pix_addr   -- (pix_x,pix_y) -> pix_addr_lo:hi = HGR scanline byte base
;   plot_set        -- plot at (pix_x,pix_y), OR (+pen colour) or XOR per plot_mode
;   line_xy         -- Bresenham (ln_x0,y0)->(ln_x1,y1), 16-bit signed err
;
; Coordinate space: the 8-bit entry points (plot_set, line_xy) cover columns
; 0..255 like the old TMS 256-wide screen; plot_set_x16 / line_xy16 take a
; 9-bit X (pix_xh, ln_x0h/ln_x1h) for the full 280 columns, and the turtle
; clamps to 0..279.
;
; HGR colour: the card has only ~6 artifact colours (vs TMS's 15), set by the
; byte's palette high bit (green/violet family vs blue/orange) and the pixel
; column parity. pen_color (0..15, LOGO/TMS index) maps through pen_hi_tbl to
; the palette high bit; the column parity is whatever the line happens to hit.
; This is an inherent HGR limitation -- thin colour lines alias, exactly as on
; real Apple II / GEN2 hardware.
;
; Owns ZP slots: pix_x, pix_y, pix_addr_lo, pix_addr_hi, pix_mask, pix_byte,
;                ln_x0, ln_y0, ln_x1, ln_y1, ln_dx, ln_dy, ln_sx, ln_sy,
;                ln_err, ln_err_hi, pen_color.
;
; Imports (caller must define): tmp, tmp2 (ZP scratch), plot_mode (BSS byte).
; ============================================================================

.include "apple2.inc"

; --- exported ZP slots (same names the TMS backend exported) ----------------
.exportzp pix_x, pix_y, pix_addr_lo, pix_addr_hi, pix_mask, pix_byte
.exportzp pix_xh          ; high byte of a 9-bit X (0 or 1) for plot_set_x16
.exportzp ln_x0, ln_y0, ln_x1, ln_y1, ln_dx, ln_dy, ln_sx, ln_sy
.exportzp ln_x0h, ln_x1h   ; 9-bit-X line endpoints (set by callers of line_xy16)
.exportzp ln_err, ln_err_hi
.exportzp pen_color

; --- imports ----------------------------------------------------------------
.importzp tmp, tmp2
.import   plot_mode

; --- exported routines (same seam) ------------------------------------------
.export init_vdp_g2, clear_bitmap, disable_sprites
.export vdp_set_write, vdp_set_read, calc_pix_addr, plot_set, plot_set_x16
.export line_xy, line_xy16
.export hgr_col, hgr_mask, pen_hi_tbl
.ifdef LOGO_SPRITE_CACHE
.import emote_plot_background, emote_init
HP_OR_PLOT = emote_plot_background
.endif
.export hgr_lo, hgr_hi      ; scanline base LUTs (hgr_bubble clears its band)
; The LOGO interpreter unconditionally .imports these TMS silicon-strict
; timing helpers (their call sites are scattered outside the gated turtle
; region). On HGR there is no VDP write-window to pad for, so resolve them to
; bare RTS stubs here -- the TMS build links the real ones from
; POM1's dev/lib/tms9918/tms9918_pad.asm and never links this file.
.export tms9918_pad18, vdp_display_off

; ----------------------------------------------------------------------------
.segment "ZEROPAGE"
pix_x:        .res 1
pix_xh:       .res 1     ; 9-bit X high byte (0 = cols 0..255, 1 = cols 256..279)
pix_y:        .res 1
pix_addr_lo:  .res 1
pix_addr_hi:  .res 1
pix_mask:     .res 1
pix_byte:     .res 1
ln_x0:        .res 1
ln_x0h:       .res 1     ; line endpoint 0, X high byte (9-bit X)
ln_y0:        .res 1
ln_x1:        .res 1
ln_x1h:       .res 1     ; line endpoint 1, X high byte
ln_y1:        .res 1
ln_dx:        .res 1
ln_dxh:       .res 1     ; |dx| high byte (16-bit, for >255-px-wide lines)
ln_dy:        .res 1
ln_sx:        .res 1
ln_sy:        .res 1
ln_err:       .res 1
ln_err_hi:    .res 1
pen_color:    .res 1     ; 0..15 LOGO/TMS palette index (SETPC). $0F = white.

; ============================================================================
.segment "CODE"
; ============================================================================

; init_vdp_g2: bring the GEN2 card up in GRAPHICS + HIRES + PAGE1 + full screen
;   and seed the pen to white. Mirrors the TMS init_vdp_g2 contract (seed
;   pen_color so projects that never call SETPC keep the white-on-black look).
init_vdp_g2:
        lda HIRES               ; HGR latch (shown by TS/SS/FS in screen.asm)
        lda LOWSCR              ; page 1 -- never PAGE2 (80STORE bank switch)
        lda $C05F               ; AN3 on: plain HGR even with 80 columns on
        lda #$0F                ; default pen = white (15)
        sta pen_color
        rts

; clear_bitmap: zero the 8 KB HGR page-1 framebuffer ($2000-$3FFF) --
; dev/lib/hgr clear_hgr (no zero page).
.ifdef LOGO_SPRITE_CACHE
clear_bitmap:
        jsr emote_init             ; discard old saved background on any clear
        jmp clear_hgr
.else
clear_bitmap = clear_hgr
.endif
.include "hgr_clear.asm"

; disable_sprites / vdp_set_write / vdp_set_read: no-ops on HGR (kept so the
;   interpreter's explicit calls resolve and cost only a JSR/RTS).
; tms9918_pad18 / vdp_display_off: TMS silicon-strict timing helpers the
;   interpreter imports unconditionally -- no-ops on HGR.
disable_sprites:
vdp_set_write:
vdp_set_read:
tms9918_pad18:
vdp_display_off:
        rts

; calc_pix_addr: (pix_x,pix_y) -> pix_addr_lo:hi = base byte of scanline pix_y
;   in HGR page 1 (column 0). The byte column for pix_x is hgr_col[pix_x];
;   callers that need it index (pix_addr_lo),Y with Y = hgr_col[pix_x].
calc_pix_addr:
        ldx pix_y
        lda hgr_lo,x
        sta pix_addr_lo
        lda hgr_hi,x
        sta pix_addr_hi
        rts

; plot_set: plot (pix_x,pix_y). plot_mode 0 = OR (draw, applies pen colour),
;   1 = XOR (turtle/erase, leaves the trail colour byte's palette bit alone).
; plot_set: 8-bit X entry (pix_x = 0..255). Forces pix_xh = 0 then delegates to
;   the 9-bit core, so every existing 8-bit caller (line_xy, emote, text) is
;   unchanged.
plot_set:
        lda #0
        sta pix_xh
        jmp hgr_plot16
plot_set_x16 = hgr_plot16
hp_x = pix_x
hp_y = pix_y
hp_ptr = pix_addr_lo
hp_mask = pix_mask
hp_mode = plot_mode
hp_color = pen_color
HP_COLOR_TABLE = pen_hi_tbl
.include "hgr_plot.asm"

; pen_color (0..15) -> HGR palette high bit. $00 = green/violet family,
;   $80 = blue/orange family. White (15) stays $00.
pen_hi_tbl:
        ;      0    1    2    3    4    5    6    7
        .byte $00, $00, $00, $00, $80, $80, $80, $80
        ;      8    9   10   11   12   13   14   15
        .byte $80, $80, $00, $00, $00, $00, $00, $00

; Legacy entry points delegate to the shared dev/lib/hgr walker.
; Reuse existing scratch, so the interpreter's zero-page footprint is unchanged.
line_xy:
        lda #0
        sta ln_x0h
        sta ln_x1h
        jmp hgr_line16
line_xy16 = hgr_line16
h16_x0 = ln_x0
h16_y0 = ln_y0
h16_x1 = ln_x1
h16_y1 = ln_y1
h16_dx = ln_dx
h16_dy = ln_dy
h16_sx = ln_sx
h16_sy = ln_sy
h16_err = ln_err
h16_e2 = tmp
h16_pix_x = pix_x
h16_pix_y = pix_y
HGR_LINE16_PLOT = plot_set_x16
.include "hgr_line16.asm"

; --- HGR lookup tables ------------------------------------------------------
        .include "hgr_scanline.inc"     ; hgr_lo[192] / hgr_hi[192]
        HGR_FULL_WIDTH_TABLES = 1
        .include "hgr_plot_tables.inc"  ; hgr_col[280] / hgr_mask[280]
