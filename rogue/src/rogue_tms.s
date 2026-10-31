; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; rogue_tms.s -- ROGUE.TMS: the game on the E-Z Color card (TMS9918A)
; ============================================================================
; Apple II+ 48 KB / DOS 3.3 and later, the card in any slot. Started by the
; ROGUE launcher (or BRUN ROGUE.TMS): boot.inc finds the card again, points
; the VDP accesses at its slot, writes the Apple text page, then `start`.
;   core/rogue_core.inc   the game (POM1's TMS_Rogue), no hardware access
;   video_tms.asm         vid_* on the TMS9918A (docs/VIDEO_API.md)
;   boot.inc              entry, ez_detect, vdp_patch, Apple text page,
;                         plat_quit, plat_sound_status
; Memory: src/rogue_tms.cfg.
; ============================================================================

.include "apple2.inc"
.include "ezcolor.inc"          ; dev/lib/apple2: ez_slot, ez_slotx, ez_ptr...
.include "ezvdp.inc"            ; VSTA_* port macros (video_tms, boot)

.include "txtpage.inc"          ; txt_page
.include "boot.inc"             ; STARTUP: entry = first byte of the file
.include "core/rogue_core.inc"  ; the game
.include "video_tms.asm"        ; its TMS9918A back-end

EZ_DETECT_BOOT_SLOT = $B7E9     ; DOS 3.3 IOB: slot * 16 of the last access
.include "ezcolor.asm"          ; dev/lib/apple2: ez_detect (slot 3 skipped)

.segment "LOWBSS"
apple2_zp_buf:  .res 256        ; DOS's zero page while ROGUE runs
.include "exit.asm"             ; apple2_zp_save / apple2_exit
