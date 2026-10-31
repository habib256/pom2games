; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ported from POM1 dev/lib/tms9918 @ e399808 (tms9918_pad.asm)
; ============================================================================
; tms9918_pad.asm -- silicon-strict padding helpers + display gate (R1)
; ============================================================================
; The POM1 names, for code ported from the Apple-1 P-LAB card. New code calls
; ez_pad18 / ez_data_w (../apple2/ezcolor.asm), which carry the same contract.
;
;   tms9918_pad18  JSR = 18 cycles (JSR 6 + 3 NOP + RTS 6), A/X/Y and every
;                  flag preserved: callers put it between a compare and its
;                  branch. tms9918_pad12 is the legacy alias (= pad18).
;   tms9918_pad24  30 cycles (optional cushion).
;   tms9918_pad40  48 cycles (LEGACY: TMS_Rogue's upload loops).
;   vdp_display_off  R1 = $80 (blanked, 16K, no IRQ, 8x8 sprites)
;   vdp_display_on   R1 = $C0 (display on, 16K, 8x8 sprites)
;
; Blank the display around a VRAM burst after init: the VDP then serves the
; CPU every ~2 us and unpadded loops are safe (ez_fill_blank). Programs with
; another R1 (e.g. $C2, 16x16 sprites) write their own value back.
; SILICON WARNING (openMSX): a register write also loads the VRAM address
; counter's high bits; set the VRAM address again after these helpers.
; Each entry is .ifref-guarded.
; ============================================================================

.ifndef _TMS9918_PAD_ASM_LOADED_
_TMS9918_PAD_ASM_LOADED_ = 1

.include "tms9918.inc"

.segment "CODE"

.ifref vdp_display_on
_TMS9918_PAD_DISPLAY_ .set 1
.endif
.ifref vdp_display_off
_TMS9918_PAD_DISPLAY_ .set 1
.endif
.ifdef _TMS9918_PAD_DISPLAY_
vdp_display_on:
        LDA     #$C0
        .byte   $2C             ; BIT abs: swallows the LDA #$80 below
vdp_display_off:
        LDA     #$80
        JSR     ez_ctrl_w       ; value (pad included)
        LDA     #$81            ; command: register 1
        JMP     ez_ctrl_w
.endif

.ifref tms9918_pad24
tms9918_pad24:
        JSR     tms9918_pad18   ; 6 + 18
        RTS                     ; + 6 = 30 cycles
.endif

.ifref tms9918_pad40
tms9918_pad40:
        JSR     tms9918_pad18
        JSR     tms9918_pad18
        RTS                     ; 6 + 18 + 18 + 6 = 48 cycles
.endif

.ifref tms9918_pad12
tms9918_pad12 = tms9918_pad18   ; legacy name, same 18 cycles
.endif

.ifref tms9918_pad18
tms9918_pad18:
        NOP
        NOP
        NOP
        RTS
.endif

.endif  ; _TMS9918_PAD_ASM_LOADED_
