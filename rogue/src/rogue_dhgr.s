; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; rogue_dhgr.s -- ROGUE.DHGR: the game on the //e / //c double hi-res screen
; ============================================================================
; Apple //e 128 KB (extended 80-column card) or //c, DOS 3.3. Started by the
; ROGUE launcher when no E-Z Color card is found (or BRUN ROGUE.DHGR):
;   core/rogue_core.inc   the game (POM1's TMS_Rogue), no hardware access
;   video_dhgr.asm        vid_* on DHGR page 1 (docs/VIDEO_API.md: the
;                         virtual TMS9918 screen, halved horizontally)
; Memory: src/rogue_dhgr.cfg. Sound status (S): the core's own message only.
; ============================================================================

.include "apple2.inc"

.segment "STARTUP"

entry:
        APPLE2_PREAMBLE
        JSR     apple2_zp_save  ; FIRST: DOS's zero page, RESET -> DOS
        LDA     $FBB3           ; //e and //c: $06
        CMP     #$06
        BNE     @nodhgr
        LDA     #1
        STA     snd_on          ; sounds on
        LDA     #0
        STA     sfx_req
        JMP     start           ; vid_init: DHGR on
@nodhgr:
        JSR     HOME
        LDX     #0
@msg:   LDA     msg_need,X
        BEQ     @key
        ORA     #$80
        JSR     COUT
        INX
        BNE     @msg
@key:   LDA     KBD
        BPL     @key
        BIT     KBDSTRB
        JMP     apple2_exit

msg_need:
        .byte   "ROGUE.DHGR NEEDS AN APPLE //E 128K OR //C", $0D
        .byte   "PRESS A KEY", $0D, 0

; plat_quit -- (core hook) ESC: DHGR off, text page cleared, back to DOS.
plat_quit:
        JSR     vid_off
        JMP     apple2_exit

; plat_sound_status -- (core hook) nothing to show outside the game screen.
plat_sound_status:
        RTS

; exit.asm's hook after the text display is back: an empty page for the
; DOS prompt (also after Ctrl-RESET).
dhgr_exit_home:
        JMP     HOME
APPLE2_EXIT_HOOK = dhgr_exit_home

.include "core/rogue_core.inc"  ; the game
.include "video_dhgr.asm"       ; its DHGR back-end

.segment "LOWBSS"
apple2_zp_buf:  .res 256        ; DOS's zero page while ROGUE runs
.include "exit.asm"             ; apple2_zp_save / apple2_exit
