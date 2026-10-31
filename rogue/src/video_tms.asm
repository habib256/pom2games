; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; video_tms.asm -- ROGUE's TMS9918A back-end: the E-Z Color card, any slot
; ============================================================================
; Implements docs/VIDEO_API.md on the real chip:
;   vid_init        POM1's start-up sequence: init_vdp_g1 (8 registers,
;                   16 KB wiped, SAT terminator), display off, pattern /
;                   colour / sprite pattern uploads, name table cleared,
;                   R1 = $C2 (display on, 16x16 sprites)
;   vid_clear       clear_name_table          vid_sprites_off  disable_sprites
;   vid_addr        A/X = VRAM address (the write bit is forced)
;   vid_put         STA data, then 6 idle cycles
;   vid_wait_frame  POM1's hang-proof frame-flag wait
;   vid_idle        nothing (the chip shows what it has)
;   vid_off         R1 = $80: the card's picture blanked
; Timing: >= 18 cycles between two VDP accesses during active display
; (22 cycles STA to STA), kept here whatever the core does between calls:
; every routine leaves >= 6 cycles after its last access before its RTS
; (RTS 6 + the caller's JSR 6 + those 6 = 18).
; Ports: VSTA_* / VLDA_* / VBIT_* (ezvdp.inc), patched to the card's slot
; by boot (vdp_patch). Data: gfx/tileset_rogue.inc, gfx/sprite_pats.inc,
; gfx/sprites_boss.asm (POM1's, unchanged).
; ============================================================================

.segment "ZEROPAGE"
tms_src:        .res 2          ; upload pointer (vid_init only)

.segment "CODE"

vid_clear       = clear_name_table
vid_sprites_off = disable_sprites
vid_off         = vdp_display_off

vid_init:
        JSR     init_vdp_g1     ; exits with R1 = $C0 (display on)
        JSR     vdp_display_off ; uploads with the display off (widest window)
        JSR     upload_tileset
        JSR     upload_colour_table
        JSR     upload_sprite_pats
        JSR     clear_name_table
        JMP     override_r1_16x16

; vid_addr -- A = low, X = high (bit 6 forced: write). Keeps X, Y.
vid_addr:
        JSR     tms9918_pad18   ; whatever came before
        VSTA_CTRL
        TXA
        ORA     #$40
        JSR     tms9918_pad18
        VSTA_CTRL
        NOP
        NOP
        NOP
        RTS

; vid_put -- A at the cursor. Keeps A, X, Y, P.
vid_put:
        VSTA_DATA
        NOP
        NOP
        NOP
        RTS

; vid_wait_frame -- the next frame flag, ~0.4 s at most. Keeps A, X, Y.
vid_wait_frame:
        TMS_WAIT_VBLANK
        RTS

vid_idle:
        RTS

; tms_set_write -- VRAM write address A = low, X = high (+$40 here).
tms_set_write:
        JSR     tms9918_pad18
        VSTA_CTRL
        TXA
        JSR     tms9918_pad18
        VSTA_CTRL
        JMP     tms9918_pad18

; ----------------------------------------------------------------------------
; From POM1 TMS_Rogue.asm (moved here: hardware set-up)
; ----------------------------------------------------------------------------
override_r1_16x16:              ; R1 = $C2: display on, 16x16 sprites
        LDA     #$C2
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$81            ; $01 | $80 -> register 1
        VSTA_CTRL
        JMP     tms9918_pad18

upload_tileset:                 ; 2048 B -> $0000
        LDA     #$00
        LDX     #$40
        JSR     tms_set_write
        LDA     #<tileset_rogue
        STA     tms_src
        LDA     #>tileset_rogue
        STA     tms_src+1
        LDX     #8
@page:  LDY     #0
@byte:  LDA     (tms_src),Y
        VSTA_DATA
        JSR     tms9918_pad18
        INY
        BNE     @byte
        INC     tms_src+1
        DEX
        BNE     @page
        RTS

upload_colour_table:            ; 32 B -> $2000
        LDA     #$00
        LDX     #$60
        JSR     tms_set_write
        LDX     #0
@lp:    LDA     tileset_color_table,X
        VSTA_DATA
        JSR     tms9918_pad18
        INX
        CPX     #32
        BNE     @lp
        RTS

upload_sprite_pats:             ; 448 + 128 B -> $3800
        LDA     #$00
        LDX     #$78
        JSR     tms_set_write
        LDX     #0
@lp1:   LDA     sprite_pats,X
        VSTA_DATA
        JSR     tms9918_pad18
        INX
        BNE     @lp1
        LDX     #0
@lp2:   LDA     sprite_pats+256,X
        VSTA_DATA
        JSR     tms9918_pad18
        INX
        CPX     #192
        BNE     @lp2
        LDX     #0
@lp3:   LDA     boss_sprite_pats,X
        VSTA_DATA
        JSR     tms9918_pad18
        INX
        CPX     #128
        BNE     @lp3
        RTS

; ----------------------------------------------------------------------------
; POM1's dev/lib/tms9918 Mode 1 driver (tms9918m1.asm + tms9918_pad.asm),
; instruction for instruction, ports through ezvdp.inc
; ----------------------------------------------------------------------------

; tms9918_pad18 -- JSR 6 + 3 NOP 6 + RTS 6 = 18 cycles at the call site
tms9918_pad18:
        NOP
        NOP
        NOP
        RTS

vdp_display_off:
        LDA     #$80
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$81            ; cmd = $80 | reg 1
        VSTA_CTRL
        JSR     tms9918_pad18
        RTS

init_vdp_g1:
        JSR     tms9918_pad18   ; cross-caller cushion (18c)
        LDX     #0
@rg:    LDA     vdp1_regs,X
        CPX     #1
        BNE     @rg_store
        AND     #$BF            ; force display OFF for the loop pass
@rg_store:
        VSTA_CTRL
        TXA
        ORA     #$80
        JSR     tms9918_pad18
        VSTA_CTRL
        INX
        CPX     #8
        JSR     tms9918_pad18
        BNE     @rg
        JSR     wipe_all_vram   ; zero all 16 KB while display is still OFF
        JSR     disable_sprites ; SAT terminator with display still OFF
        JSR     tms9918_pad18
        LDA     vdp1_regs+1
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$81            ; cmd = $80 | reg-1
        VSTA_CTRL
        RTS

; Display off: the VDP's CPU window is wide open, no pad in the inner loop
; (9 cycles between two stores, as on the Apple-1).
wipe_all_vram:
        JSR     tms9918_pad18
        LDA     #$00
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$40            ; $00 | $40 = auto-increment write from $0000
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$00
        LDX     #64             ; 64 * 256 = 16384 bytes
@wp:    LDY     #0
@wb:    VSTA_DATA
        INY
        BNE     @wb
        DEX
        BNE     @wp
        RTS

disable_sprites:
        JSR     tms9918_pad18
        LDA     #$00
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$5B            ; $1B | $40 = write at $1B00
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$D0            ; SAT[0].Y = chain terminator
        VSTA_DATA
        JSR     tms9918_pad18
        LDX     #127            ; SAT[1..127] = off-screen Y via auto-inc
        LDA     #$D1
@sat:   VSTA_DATA
        JSR     tms9918_pad18
        DEX
        BNE     @sat
        RTS

clear_name_table:
        JSR     tms9918_pad18
        LDA     #$00
        VSTA_CTRL
        JSR     tms9918_pad18
        LDA     #$58            ; $18 | $40 = write at $1800
        VSTA_CTRL
        JSR     tms9918_pad18
        LDX     #$03            ; 3 * 256 = 768 bytes
        LDA     #$00
@np:    LDY     #$00
@nb:    VSTA_DATA
        JSR     tms9918_pad18
        INY
        BNE     @nb
        DEX
        BNE     @np
        RTS

vdp1_regs:
        .byte   $00, $C0, $06, $80, $00, $36, $07, $01

.include "gfx/tileset_rogue.inc"
.include "gfx/sprite_pats.inc"
.include "gfx/sprites_boss.asm"
.segment "CODE"
