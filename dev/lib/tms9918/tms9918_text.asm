; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ported from POM1 dev/lib/tms9918 @ e399808 (tms9918_text.asm)
; ============================================================================
; tms9918_text.asm -- TMS9918 Text Mode F1 (40x24 monochrome) driver
;                     for Apple-1 + P-LAB Graphic Card.
;
; Forks tms9918m1.asm. The TMS9918's Text Mode F1 has the *exact same*
; geometry as the Apple-1 PIA display (40 columns x 24 rows), so it's the
; natural drop-in replacement for the slow $D012-driven character output
; once the charmap is uploaded to the VDP pattern table.
;
; Public symbols:
;   init_vdp_text   -- 8 registers + tail-call disable_sprites_text
;   upload_charmap  -- copy 1 KB Apple-1 charmap (bit-reversed) to pattern
;                      table at $0000. Display is blanked during the burst.
;   clear_screen_text -- fill 960 bytes at $0800 with $20 (space)
;   vdp_set_write   -- prep VRAM auto-increment write at vdp_lo:hi
;   vdp_set_read    -- prep VRAM read at vdp_lo:hi
;   name_at_rc_text -- load vdp_lo:hi with name-table addr for
;                      (vdp_row, vdp_col) -- 40-col arithmetic
;   print_at_rc_text-- write char A at (vdp_row, vdp_col) -- full sequence
;
; Owns ZP slots: vdp_lo, vdp_hi, vdp_src_lo, vdp_src_hi, vdp_row, vdp_col.
;                Same layout as tms9918m1.asm so a project never links both.
;
; Imports (caller must define):
;   tmp                 -- 1 ZP scratch byte (used inside name_at_rc_text
;                          and the bit-reverse loop of upload_charmap).
;
; Memory map (Text Mode F1, fixed by the register table below):
;   $0000-$03FF  Pattern table (1 KB = 128 chars * 8 bytes)
;   $0800-$0BBF  Name table   (40 cols * 24 rows = 960 bytes)
;   (no sprites, no colour table -- text mode uses R7 for fg/bg)
;
; Silicon-strict timing: every JSR ez_data_w in this module is followed by
; a paired STA/INX/CPX/BNE that already eats >= 8 cycles, OR by an explicit
; pad. Text-mode active display serves dense CPU access slots in POM1's
; openMSX tables (worst active gap ~8c), so this passes silicon-strict;
; the real-silicon drop floor measured in active Mode I/II is ~16c
; (doc/TMS9918_TRANSFER_WINDOWS.md). The display is blanked (R1 = $80)
; during upload_charmap so the densest burst runs in a free zone anyway.
; ============================================================================

.ifndef _TMS9918_TEXT_ASM_LOADED_
_TMS9918_TEXT_ASM_LOADED_ = 1
.ifdef _TMS9918M2_ASM_LOADED_
.error "tms9918_text.asm: tms9918m2.asm is exclusive with tms9918m1.asm / tms9918_text.asm (same names, other tables)"
.endif

.include "tms9918.inc"

; --- ZP layout -------------------------------------------------------------
.segment "ZEROPAGE"
.ifndef vdp_lo
vdp_lo:         .res 1
.endif
.ifndef vdp_hi
vdp_hi:         .res 1
.endif
.ifndef vdp_src_lo
vdp_src_lo:     .res 1
.endif
.ifndef vdp_src_hi
vdp_src_hi:     .res 1
.endif
.ifndef vdp_row
vdp_row:        .res 1
.endif
.ifndef vdp_col
vdp_col:        .res 1
.endif

; ============================================================================
.segment "CODE"
; ============================================================================


.ifref init_vdp_text
; ----------------------------------------------------------------------------
; init_vdp_text: write 8 Text-Mode-F1 registers.
;   Display is kept OFF during the register pass (R1 committed as $90 —
;   the $D0 table value with bit 6 masked): the pattern and name tables
;   are still power-on garbage at this point, and real DRAM flashes that
;   garbage on screen if the display is enabled first (blank-first
;   discipline, mirrors init_vdp_g1/g2 and basicrt's lr_text_mode).
;   Call enable_text_display (or let upload_charmap's tail do it) once
;   the tables are filled.
; ----------------------------------------------------------------------------
init_vdp_text:
        LDX     #0
@rg:    LDA     vdpt_regs,X
        CPX     #1
        BNE     @nomask
        AND     #$BF            ; R1: keep display OFF over uninit VRAM
@nomask:
        JSR     ez_ctrl_w
        TXA
        ORA     #$80
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        JSR     ez_ctrl_w
        INX
        CPX     #8
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        BNE     @rg
        RTS
.endif

.ifref upload_charmap
; ----------------------------------------------------------------------------
; upload_charmap: chars 0-31 blank, chars $20-$7F from tms_c64font
;   (c64font_tms.inc), pattern table $0000-$03FF. Port: POM1 uploaded the
;   Apple-1 charmap.rom bit-reversed; the C64-style font is already MSB-left
;   and shifted into the 6 pixels Text mode shows (bits 7..2), with a gap.
;   Display is blanked during the burst (unpadded ez_fill_blank /
;   ez_copy_blank), then R1 = $D0.
;
;   Clobbers: A, X, Y, ez_ptr, ez_count.
; ----------------------------------------------------------------------------
upload_charmap:
        ; 1) Blank display (R1 = $80: 16K=1, blank=0/screen off, M1=0 — the
        ;    chip idles in blanked Graphics I during the burst; the mode
        ;    bits come back with the $D0 re-arm at the end).
        LDA     #$80
        JSR     ez_ctrl_w
        LDA     #$81            ; reg 1
        JSR     ez_ctrl_w

        ; 2) Set VRAM write pointer to $0000 (pattern table base).
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA #imm bridge)
        LDA     #$00
        JSR     ez_ctrl_w
        NOP
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA #imm bridge)
        LDA     #$40            ; $00 | $40 = write at $0000
        JSR     ez_ctrl_w

        ; 3) 256 zero bytes (chars 0-31), then the 96 font glyphs.
        LDA     #0
        STA     ez_count
        LDA     #1
        STA     ez_count+1
        LDA     #0
        JSR     ez_fill_blank
        LDA     #<tms_c64font
        STA     ez_ptr
        LDA     #>tms_c64font
        STA     ez_ptr+1
        LDA     #<(96 * 8)
        STA     ez_count
        LDA     #>(96 * 8)
        STA     ez_count+1
        JSR     ez_copy_blank

        ; 4) Re-enable display (R1 = $D0).
        LDA     #$D0
        JSR     ez_ctrl_w
        NOP
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA #imm bridge)
        LDA     #$81
        JSR     ez_ctrl_w
        RTS
.endif

.ifref clear_screen_text
; ----------------------------------------------------------------------------
; clear_screen_text: fill the 960-byte name table at $0800 with $20 (space).
;   Clobbers: A, X, Y.
; ----------------------------------------------------------------------------
clear_screen_text:
        LDA     #$00
        JSR     ez_ctrl_w
        NOP
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA #imm bridge)
        LDA     #$48            ; $08 | $40 = write at $0800
        JSR     ez_ctrl_w
        ; 960 bytes = 3 pages of 256 + 192. Loop X = 3 full pages, then
        ; tail of 192. Each STA VDP_DATA + INY/BNE = >= 8c.
        LDA     #$20            ; space
        LDX     #3
@p:     LDY     #0
@b:     JSR     ez_data_w
        INY
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        BNE     @b
        DEX
        BNE     @p
        ; Tail: 192 bytes
        LDY     #192
@t:     JSR     ez_data_w
        DEY
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        BNE     @t
        RTS
.endif

.ifref vdp_set_read
.ifndef vdp_set_read                      ; shared by tms9918m1.asm and tms9918_text.asm
; ----------------------------------------------------------------------------
; vdp_set_read: prep VDP for reads at vdp_lo:hi.
; ----------------------------------------------------------------------------
vdp_set_read:
        LDA     vdp_lo
        JSR     ez_ctrl_w
        NOP
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA zp/abs bridge)
        LDA     vdp_hi          ; bit 6 = 0 -> read
        JSR     ez_ctrl_w
        RTS
.endif
.endif

.ifref print_at_rc_text
; ----------------------------------------------------------------------------
; print_at_rc_text: write char A at (vdp_row, vdp_col) -- full sequence.
;   Caller is responsible for col<40 / row<24 bounds. The console runtime
;   on top of this driver handles wrap and scroll.
; ----------------------------------------------------------------------------
print_at_rc_text:
        PHA                     ; save char
        JSR     name_at_rc_text
        JSR     vdp_set_write
        PLA
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        JSR     ez_data_w
        RTS
.endif

.ifref vdp_set_write
.ifndef vdp_set_write                      ; shared by tms9918m1.asm and tms9918_text.asm
; ----------------------------------------------------------------------------
; vdp_set_write: prep VDP for auto-incrementing writes at vdp_lo:hi.
; ----------------------------------------------------------------------------
vdp_set_write:
        LDA     vdp_lo
        JSR     ez_ctrl_w
        NOP                     ; +2c gap
        LDA     vdp_hi
        ORA     #$40            ; bit 6 = write
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        JSR     ez_ctrl_w
        RTS
.endif
.endif

.ifref name_at_rc_text
; ----------------------------------------------------------------------------
; name_at_rc_text: compute name-table VRAM address for (vdp_row, vdp_col),
;   store in vdp_lo:hi (vdp_set_write/read OR in the bit 6 write flag later).
;     addr = $0800 + 40 * row + col
;   Inputs:   vdp_row (0..23), vdp_col (0..39)
;   Output:   vdp_lo:hi loaded.
;   Clobbers: A, X.
;
;   Now LUT-driven (was: 32*row + 8*row shift-and-add, ~46 cycles). 24-entry
;   tables pre-bake `$0800 + 40*row`; the call cost drops to ~21 cycles. Over
;   a full console_scroll (23 row reads + 23 row writes + 1 blank = 47 calls)
;   that is ~1175 cycles saved per scroll. Net ROM: +24 bytes (48-byte LUT
;   minus ~24 bytes of dropped arithmetic + the freed `tmp` clobber).
; ----------------------------------------------------------------------------
name_at_rc_text:
        LDX     vdp_row
        LDA     name_row_lo,X
        CLC
        ADC     vdp_col
        STA     vdp_lo
        LDA     name_row_hi,X
        ADC     #0              ; just propagate the col-carry
        STA     vdp_hi
        RTS
.endif

.ifref name_row_lo
; 24-entry tables: name_row_lo[i] / name_row_hi[i] = lo/hi of ($0800 + 40*i).
name_row_lo:
        .byte $00, $28, $50, $78, $A0, $C8, $F0, $18
        .byte $40, $68, $90, $B8, $E0, $08, $30, $58
        .byte $80, $A8, $D0, $F8, $20, $48, $70, $98
.endif

.ifref name_row_hi
name_row_hi:
        .byte $08, $08, $08, $08, $08, $08, $08, $09
        .byte $09, $09, $09, $09, $09, $0A, $0A, $0A
        .byte $0A, $0A, $0A, $0A, $0B, $0B, $0B, $0B
.endif

.ifref vdpt_regs
; ============================================================================
; Text Mode F1 register table.
;
;   Reg 0: $00  External video off, M3=0.
;   Reg 1: $D0  M1=1 (text mode), screen on, IRQ off, 16K, no sprites.
;   Reg 2: $02  Name table at $0800 ($02 << 10).
;   Reg 3: $00  (colour table unused in F1)
;   Reg 4: $00  Pattern table at $0000.
;   Reg 5: $00  (sprite attribute table unused in F1)
;   Reg 6: $00  (sprite pattern table unused in F1)
;   Reg 7: $F0  fg = white (15), bg = black (0).
; ============================================================================
vdpt_regs:
        .byte   $00, $D0, $02, $00, $00, $00, $00, $F0

.endif

.ifref tms_c64font
.include "c64font_tms.inc"        ; tms_c64font (guarded: shared with the game)
.endif

.endif  ; _TMS9918_TEXT_ASM_LOADED_
