; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ported from POM1 dev/lib/tms9918 @ e399808 (tms9918.inc)
; ============================================================================
; tms9918.inc -- POM1's TMS9918 macros on the Apple II E-Z Color card
; ============================================================================
; Include after apple2.inc (it includes ../apple2/ezcolor.inc: put both
; dev/lib/apple2 and dev/lib/tms9918 on the ca65 include path). The card sits
; in a slot found at run time (ez_detect), so VDP_DATA / VDP_CTRL do NOT
; exist here: a leftover `STA VDP_DATA` fails to assemble or link instead of
; writing to a wrong address. Rewrite them:
;
;   POM1 (P-LAB, Apple-1)               here (after JSR ez_detect)
;   STA VDP_DATA / JSR tms9918_pad18    JSR ez_data_w          (22 c, A/X/Y/P kept)
;   STA VDP_CTRL / JSR tms9918_pad18    JSR ez_ctrl_w          (22 c, A/X/Y/P kept)
;   LDA VDP_DATA                        JSR ez_data_r          (N/Z as LDA, padded)
;   LDA VDP_CTRL / BIT VDP_CTRL         JSR ez_status / JSR ez_status_bit
;   unpadded blanked fills              ez_fill_blank / ez_copy_blank
;
; The 18-cycle contract is unchanged (see ../apple2/ezcolor.inc). Never use
; an indexed store on the ports (STA EZ_DATA,X): the NMOS dummy read breaks
; the VDP's protocol.
;
; Include order: game code, then dev/lib/tms9918/*.asm, then
; ../apple2/ezcolor.asm LAST (all .ifref-guarded).
; ============================================================================

.ifndef _TMS9918_INC_LOADED_
_TMS9918_INC_LOADED_ = 1

.include "ezcolor.inc"

; Zero page of the drivers, reserved here (top of the source) so code above
; the driver include addresses it as zero page. Each name can be aliased by
; defining it before this include. Options (define before the include):
;   TMS9918_M1_ZP = 1 (default)  vdp_lo vdp_hi vdp_src_lo vdp_src_hi vdp_row
;                                vdp_col (tms9918m1.asm / tms9918_text.asm)
;   TMS9918_M2_ZP = 1            pix_* ln_* pen_color (tms9918m2.asm, 17 B)
;   TMS9918_CONSOLE_ZP = 1       cur_row cur_col con_tmp (tms9918_console.asm)
; Without the option, the driver reserves its own (later in the source:
; earlier references then assemble as absolute, with a ca65 warning).
.ifndef TMS9918_M1_ZP
TMS9918_M1_ZP = 1
.endif
.ifndef TMS9918_M2_ZP
TMS9918_M2_ZP = 0
.endif
.ifndef TMS9918_CONSOLE_ZP
TMS9918_CONSOLE_ZP = 0
.endif
.macro TMS9918_ZP_RES name
.ifndef name
name: .res 1
.endif
.endmacro
.pushseg
.zeropage
.if TMS9918_M1_ZP
        TMS9918_ZP_RES vdp_lo
        TMS9918_ZP_RES vdp_hi
        TMS9918_ZP_RES vdp_src_lo
        TMS9918_ZP_RES vdp_src_hi
        TMS9918_ZP_RES vdp_row
        TMS9918_ZP_RES vdp_col
.endif
.if TMS9918_M2_ZP
        TMS9918_ZP_RES pix_x
        TMS9918_ZP_RES pix_y
        TMS9918_ZP_RES pix_addr_lo
        TMS9918_ZP_RES pix_addr_hi
        TMS9918_ZP_RES pix_mask
        TMS9918_ZP_RES pix_byte
        TMS9918_ZP_RES ln_x0
        TMS9918_ZP_RES ln_y0
        TMS9918_ZP_RES ln_x1
        TMS9918_ZP_RES ln_y1
        TMS9918_ZP_RES ln_dx
        TMS9918_ZP_RES ln_dy
        TMS9918_ZP_RES ln_sx
        TMS9918_ZP_RES ln_sy
        TMS9918_ZP_RES ln_err
        TMS9918_ZP_RES ln_err_hi
        TMS9918_ZP_RES pen_color
.endif
.if TMS9918_CONSOLE_ZP
        TMS9918_ZP_RES cur_row
        TMS9918_ZP_RES cur_col
        TMS9918_ZP_RES con_tmp
.endif
.popseg

; POM1 names, same contract (pad18: 22-cycle store-to-store).
.macro WRT_DATA_REG
        EZ_WRT_DATA_REG
.endmacro

.macro WRT_DATA_VAL val
        EZ_WRT_DATA_VAL val
.endmacro

; Frame flag polling through BIT (A kept; the status read clears F, 5S, C).
.macro WAIT_VBLANK
        EZ_WAIT_VBLANK
.endmacro

.macro WAIT_VBLANK_SAFE
        EZ_WAIT_VBLANK_SAFE
.endmacro

.macro WAIT_5S
        EZ_WAIT_5S
.endmacro

.endif  ; _TMS9918_INC_LOADED_
