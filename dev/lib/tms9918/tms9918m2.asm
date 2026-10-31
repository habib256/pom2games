; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ported from POM1 dev/lib/tms9918 @ e399808 (tms9918m2.asm)
; ============================================================================
; tms9918.asm -- TMS9918 Mode-2 (bitmap, 256x192) driver for Apple-1 + P-LAB
;                Graphic Card. Reusable across LOGO / Maze3D / future games.
;
; Public symbols:
;   init_vdp_g2     -- 8 registers + linear name table + colour table
;                      (caller MUST follow with clear_bitmap + disable_sprites;
;                       both already in the canonical boot sequence)
;   clear_bitmap    -- zero the 6144 B pattern table at $0000
;   disable_sprites -- write Y=$D0 to sprite #0 attribute (chip stops scan)
;   vdp_set_write   -- prep VRAM auto-increment write at pix_addr_lo:hi
;   vdp_set_read    -- prep VRAM read at pix_addr_lo:hi
;   calc_pix_addr   -- (pix_x, pix_y) -> pix_addr_lo:hi  (no mask)
;   plot_set        -- plot at (pix_x, pix_y), OR or XOR per plot_mode
;   line_xy         -- Bresenham (ln_x0,y0)->(ln_x1,y1), 16-bit signed err
;
; Owns ZP slots: pix_x, pix_y, pix_addr_lo, pix_addr_hi, pix_mask, pix_byte,
;                ln_x0, ln_y0, ln_x1, ln_y1, ln_dx, ln_dy, ln_sx, ln_sy,
;                ln_err, ln_err_hi.   (16 bytes total)
;
; Imports (caller must define):
;   tmp                 -- 1 ZP scratch byte (used inside calc_pix_addr,
;                          line_xy 2*err computation).
;   tmp2                -- 1 ZP scratch byte (line_xy 2*err high byte).
;   plot_mode           -- 1 BSS byte: 0 = OR, 1 = XOR.
; ============================================================================

.ifndef _TMS9918M2_ASM_LOADED_
_TMS9918M2_ASM_LOADED_ = 1
.ifdef _TMS9918M1_ASM_LOADED_
.error "tms9918m2.asm: tms9918m2.asm is exclusive with tms9918m1.asm / tms9918_text.asm (same names, other tables)"
.endif
.ifdef _TMS9918_TEXT_ASM_LOADED_
.error "tms9918m2.asm: tms9918m2.asm is exclusive with tms9918m1.asm / tms9918_text.asm (same names, other tables)"
.endif

.include "tms9918.inc"

; --- ZP layout for VDP / line ops ------------------------------------------
.segment "ZEROPAGE"
.ifndef pix_x
pix_x:        .res 1
.endif
.ifndef pix_y
pix_y:        .res 1
.endif
.ifndef pix_addr_lo
pix_addr_lo:  .res 1
.endif
.ifndef pix_addr_hi
pix_addr_hi:  .res 1
.endif
.ifndef pix_mask
pix_mask:     .res 1
.endif
.ifndef pix_byte
pix_byte:     .res 1
.endif
.ifndef ln_x0
ln_x0:        .res 1
.endif
.ifndef ln_y0
ln_y0:        .res 1
.endif
.ifndef ln_x1
ln_x1:        .res 1
.endif
.ifndef ln_y1
ln_y1:        .res 1
.endif
.ifndef ln_dx
ln_dx:        .res 1
.endif
.ifndef ln_dy
ln_dy:        .res 1
.endif
.ifndef ln_sx
ln_sx:        .res 1
.endif
.ifndef ln_sy
ln_sy:        .res 1
.endif
.ifndef ln_err
ln_err:       .res 1
.endif
.ifndef ln_err_hi
ln_err_hi:    .res 1
.endif
.ifndef pen_color
pen_color:    .res 1     ; 0..15 -- foreground colour written to colour
.endif
                         ;   table by plot_set in OR mode. Default $0F
                         ;   (white) is written by init_vdp_g2.

; ============================================================================
.segment "CODE"
; ============================================================================


.ifref init_vdp_g2
; init_vdp_g2: 8 registers + full 16 KB VRAM wipe + linear name table + colour
;   table = $F1 + SAT park. Fully self-sufficient -- nothing relies on power-on
;   VRAM. The @rg loop masks R1's display bit OFF on iter 1 (X=1), so the wipe,
;   name-table and colour bursts all run with the display blanked. While blanked
;   the chip serves the dense ScreenOff access slots (drain ~2c), so those
;   bursts carry NO per-byte pad -- only their address-setup control writes keep
;   the silicon-strict cushion. ~3x faster than the old padded loops.
;   See doc/TMS9918_TRANSFER_WINDOWS.md for the transfer-window rationale.
;
;   The explicit clear_bitmap + disable_sprites calls in existing consumers
;   (Mandel, Logo 8K/16K, basicrt rt_hgr) are now harmless redundant re-clears.
init_vdp_g2:
        ; Caller-gap cushion: covers the case where init_vdp_g2 is
        ; called immediately after another VDP write in the caller.
        JSR     ez_pad18   ; cross-caller cushion (18c)
        LDX #0
@rg:    LDA vdp2_regs,X
        CPX #1
        BNE @rg_store
        AND #$BF                ; R1 display OFF during loop
@rg_store:
        JSR     ez_ctrl_w
        TXA
        ORA #$80
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        JSR     ez_ctrl_w
        INX
        CPX #8
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        BNE @rg
        ; --- wipe ALL 16 KB of VRAM ($0000-$3FFF) while display is OFF ---
        ; Self-sufficient init: nothing relies on power-on VRAM (CLAUDE.md
        ; gotcha). Display is blanked (R1 bit6 cleared in @rg) -> dense ScreenOff
        ; slots (drain ~2c), so the inner STA/INY/BNE burst (>=9c) needs NO pad.
        ; The mode-2 name + colour tables below overwrite their regions; the SAT
        ; is parked by disable_sprites before the display is re-enabled.
        LDA #$00
        JSR     ez_ctrl_w
        LDA #$40                ; $00 | $40 = auto-inc write from $0000
        JSR     ez_ctrl_w
        LDA #<$4000             ; 16384 bytes
        STA ez_count
        LDA #>$4000
        STA ez_count+1
        LDA #$00
        JSR ez_fill_blank       ; no pad: ScreenOff drain ~2c << 9c inner gap
        ; --- write linear name table at $3800 (display still OFF) ---
        ; Display is blanked here (R1 bit6 cleared in @rg), so the chip serves
        ; the dense ScreenOff access slots (drain ~2c). The inner burst gap
        ; (TYA/STA/INY/BNE >= 11c) covers that with margin, so NO per-byte pad
        ; is needed -- only the address-setup control writes keep the cushion.
        ; ~3x faster than the old padded loop (see doc/TMS9918_TRANSFER_WINDOWS.md).
        LDA #$00
        JSR     ez_ctrl_w
        LDA #$78
        JSR     ez_ctrl_w
        LDX #3
@th:    LDY #0
@nm:    TYA
        JSR     ez_data_w        ; no pad: display OFF -> ScreenOff slots
        INY
        BNE @nm
        DEX
        BNE @th
        ; --- color table: $F1 everywhere ($2000-$37FF, 6144 bytes, no pad) ---
        LDA #$00
        JSR     ez_ctrl_w
        LDA #$60
        JSR     ez_ctrl_w
        LDA #<6144
        STA ez_count
        LDA #>6144
        STA ez_count+1
        LDA #$F1
        JSR ez_fill_blank       ; no pad: display OFF -> ScreenOff slots
        ; default pen colour = white (15). plot_set picks this up in OR
        ; mode to recolour the cell it just touched. SETPC overrides.
        LDA #$0F
        STA pen_color
        ; Park the SAT (gold-standard $D0 + 127x $D1 fill) while the display is
        ; still OFF, so the just-wiped SAT ($00 = on-screen Y!) cannot show
        ; ghost sprites. init_vdp_g2 is now fully self-sufficient; the explicit
        ; disable_sprites / clear_bitmap calls in existing consumers (Mandel,
        ; Logo, basicrt) are harmless redundant re-clears.
        JSR disable_sprites
        ; --- Final: re-arm R1 with table value (display ON). Display stays
        ;     OFF until the cmd byte commits, so threshold remains 2c.
        LDA vdp2_regs+1
        JSR     ez_ctrl_w
        LDA #$81
        JSR     ez_ctrl_w
        RTS
.endif

.ifref vdp2_regs
vdp2_regs:
        .byte $02, $C0, $0E, $FF, $03, $76, $03, $F1
.endif

.ifref clear_bitmap
; clear_bitmap: zero the 6144-byte pattern table at $0000.
;   Note: runs with display ON when called immediately after init_vdp_g2;
;   strict-mode Gfx2 slot density may drop bytes from the tight burst, but
;   any subsequent bitmap paint (text_bitmap, line_xy, plot_set) rewrites
;   the affected cells, so visible drops are masked. Callers that need a
;   guaranteed-clean clear should blank display explicitly before the
;   call (Mandel does this via its own clear_pattern_table inline).
clear_bitmap:
        JSR     ez_pad18   ; MANUAL caller-gap cushion (18c)
        LDA #$00
        JSR     ez_ctrl_w
        LDA #$40
        JSR     ez_ctrl_w
        LDX #24
        LDY #0
@lp:    LDA #$00
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        JSR     ez_data_w
        INY
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (back-to-back VDP store)
        BNE @lp
        DEX
        BNE @lp
        RTS
.endif

.ifref disable_sprites
; disable_sprites: defensive SAT.Y init — fill every Y attribute with
;   $D1 (= displayed row 210, off-screen, NOT a chain terminator), then
;   patch SAT[0].Y to $D0 so the chain stops at slot 0. After that even
;   when the caller later writes a real sprite into SAT[0] (e.g. Logo's
;   SETSHAPE turtle), SAT[1].Y = $D1 aborts visible rendering of slot 1+.
;   Mode II SAT base = $3B00 (R5 = $76 in vdp2_regs).
;   Pattern is the Rogue gold-standard from
;   sketchs/doc/TMS9918-SPRITE_INIT.md §4.2 — single $D0 at SAT[0] was observed
;   insufficient in May 2026 silicon-strict POM1 testing (LOGO demo2 +
;   Life CodeTank showed ghost sprites from noise SAT entries past slot 0).
disable_sprites:
        JSR     ez_pad18   ; MANUAL caller-gap cushion
        LDA     #$00
        JSR     ez_ctrl_w
        LDA     #$3B | $40      ; $7B = write at $3B00 (Mode II SAT base)
        JSR     ez_ctrl_w
        LDA     #$D0            ; SAT[0].Y = chain terminator
        JSR     ez_data_w
        LDX     #127            ; SAT[1..127] = off-screen Y via auto-inc
        LDA     #$D1
@sat:   JSR     ez_data_w
        DEX
        BNE     @sat
        RTS
.endif

.ifref line_xy
; line_xy: Bresenham, 16-bit signed err. Inputs ln_x0/y0/x1/y1 (8-bit pixels).
;          dx, dy are 8-bit unsigned magnitudes (always 0..255 on screen).
;          err = dx - dy held in ln_err:ln_err_hi (16-bit signed two's complement).
;          Each iteration tests 2*err vs -dy and dx, both as 16-bit signed.
line_xy:
        ; --- compute dx, sx ---
        SEC
        LDA ln_x1
        SBC ln_x0
        BCS @sxp
        EOR #$FF
        CLC
        ADC #1
        STA ln_dx
        LDA #$FF
        STA ln_sx
        JMP @dy
@sxp:   STA ln_dx
        LDA #$01
        STA ln_sx
@dy:    ; --- compute dy, sy ---
        SEC
        LDA ln_y1
        SBC ln_y0
        BCS @syp
        EOR #$FF
        CLC
        ADC #1
        STA ln_dy
        LDA #$FF
        STA ln_sy
        JMP @init
@syp:   STA ln_dy
        LDA #$01
        STA ln_sy
@init:  ; --- err = dx - dy (16-bit signed; dx,dy are unsigned 0..255) ---
        SEC
        LDA ln_dx
        SBC ln_dy
        STA ln_err
        LDA #0
        SBC #0                ; sign-extend the borrow into err_hi
        STA ln_err_hi
        ; --- copy current point to pix_x/y ---
        LDA ln_x0
        STA pix_x
        LDA ln_y0
        STA pix_y

@step:  JSR plot_set
        LDA ln_x0
        CMP ln_x1
        BNE @do
        LDA ln_y0
        CMP ln_y1
        BEQ @end
@do:    ; --- compute 2*err in tmp:tmp2 (preserve ln_err for the per-axis updates) ---
        LDA ln_err
        STA tmp
        LDA ln_err_hi
        STA tmp2
        ASL tmp
        ROL tmp2
        ; --- test 1: step x if 2*err >= -dy  i.e. (2*err + dy) >= 0 ---
        ;   tmp:tmp2 + (dy zero-extended)  -> sign byte in A
        CLC
        LDA tmp
        ADC ln_dy
        LDA tmp2
        ADC #0
        BMI @no_x             ; sum < 0 -> skip x
        ; err -= dy   (16-bit signed: dy is unsigned, so subtract dy_lo with carry)
        SEC
        LDA ln_err
        SBC ln_dy
        STA ln_err
        LDA ln_err_hi
        SBC #0
        STA ln_err_hi
        ; x0 += sx
        LDA ln_sx
        BPL @sxp2
        DEC ln_x0
        JMP @after_x
@sxp2:  INC ln_x0
@after_x:
        LDA ln_x0
        STA pix_x

@no_x:  ; --- test 2: step y if 2*err < dx  i.e. (2*err - dx) < 0 ---
        SEC
        LDA tmp
        SBC ln_dx
        LDA tmp2
        SBC #0
        BPL @no_y             ; diff >= 0 -> skip y
        ; err += dx
        CLC
        LDA ln_err
        ADC ln_dx
        STA ln_err
        LDA ln_err_hi
        ADC #0
        STA ln_err_hi
        ; y0 += sy
        LDA ln_sy
        BPL @syp2
        DEC ln_y0
        JMP @after_y
@syp2:  INC ln_y0
@after_y:
        LDA ln_y0
        STA pix_y
@no_y:  JMP @step
@end:   RTS
.endif

.ifref plot_set
plot_set:
        LDA pix_y
        CMP #192
        BCS @done
        JSR calc_pix_addr
        LDA pix_x
        AND #$07
        TAX
        LDA bitmask,X
        STA pix_mask
        JSR vdp_set_read
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA zp/abs bridge)
        JSR     ez_data_r
        LDX plot_mode
        BNE @xor
        ORA pix_mask
        JMP @write
@xor:   EOR pix_mask
@write: STA pix_byte
        JSR vdp_set_write
        JSR     ez_pad18   ; +18c silicon-strict pad18-v4 (before LDA zp/abs bridge)
        LDA pix_byte
        JSR     ez_data_w
        ; --- colour cell (only on OR draws). XOR is the turtle-erase
        ;     path which must leave the trail's colour alone.
        LDA plot_mode
        BNE @done
        ; address = $2000 + pix_addr (same offset as pattern cell). The
        ; auto-increment from the data-port write above advanced VRAM
        ; address by 1, so re-prime the control port now.
        LDA pix_addr_lo
        JSR     ez_ctrl_w
        LDA pix_addr_hi
        ORA #$60                ; $60 = $20 (table base) | $40 (write enable)
        JSR     ez_ctrl_w
        LDA pen_color
        ASL
        ASL
        ASL
        ASL                     ; pen_color in high nibble
        ORA #$01                ; transparent background (Mode-2 colour 1)
        JSR     ez_data_w
@done:  RTS
.endif

.ifref vdp_set_write
vdp_set_write:
        JSR     ez_pad18   ; MANUAL caller-gap cushion (18c)
        LDA pix_addr_lo
        JSR     ez_ctrl_w
        LDA pix_addr_hi
        ORA #$40
        JSR     ez_ctrl_w
        RTS                     ; ≥30c after cmd (18c+6c+6c=30c gap)
.endif

.ifref vdp_set_read
vdp_set_read:
        JSR     ez_pad18   ; MANUAL caller-gap cushion (18c)
        LDA pix_addr_lo
        JSR     ez_ctrl_w
        LDA pix_addr_hi
        JSR     ez_ctrl_w
        RTS                     ; ≥30c after cmd
.endif

.ifref calc_pix_addr
calc_pix_addr:
        LDA pix_x
        AND #$F8
        STA tmp
        LDA pix_y
        AND #$07
        ORA tmp
        STA pix_addr_lo
        LDA pix_y
        LSR
        LSR
        LSR
        STA pix_addr_hi
        RTS
.endif

.ifref bitmask
bitmask:
        .byte $80, $40, $20, $10, $08, $04, $02, $01
.endif

.endif  ; _TMS9918M2_ASM_LOADED_
