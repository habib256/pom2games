; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; rogue_dhgr.s -- ROGUE.DHGR: the game on the //e / //c double hi-res screen
; ============================================================================
; Apple //e 128 KB (extended 80-column card) or //c. Started by the ROGUE
; launcher when no E-Z Color card is found (or BRUN ROGUE.DHGR):
;   core/rogue_core.inc   the game (POM1's TMS_Rogue), no hardware access
;   video_dhgr.asm        vid_* on DHGR pages 1 and 2 (docs/VIDEO_API.md: the
;                         virtual TMS9918 screen; the game view the X2 way,
;                         video_x2.asm)
;
; DOS 3.3 loads the file at $4000 and is then given up: the game needs both
; DHGR pages ($2000-$5FFF), so the part of the file below $6000 (the
; back-end, segments LCCODE / LCDATA) moves to the language card's RAM
; ($D000-, the Monitor ROM copied to $F800-$FFFF first: tune.asm calls WAIT),
; and $9600-$BFFF (DOS's place) holds the BSS. Nothing is loaded afterwards.
; Leaving (ESC + Y, ESC at the title, Ctrl-RESET): the mark "QU" at
; QUIT_MARK, then the disk boots again: its HELLO sees the mark, clears it
; and ends at the BASIC prompt with DOS 3.3 back (DIRTBIKE's way).
; Memory: src/rogue_dhgr.cfg, docs/PORT.md §6.
; ============================================================================

.include "apple2.inc"

QUIT_MARK = $0FFE               ; = src/hello.bas PEEK (4094), (4095): "QU"
                                ; (above HELLO and its variables; DOS's boot
                                ; leaves it alone; the game: DGPAGE's spare)

.import __LCCODE_LOAD__, __LCCODE_RUN__, __LCCODE_SIZE__
.import __LCDATA_LOAD__, __LCDATA_SIZE__

.segment "ZEROPAGE"
rg_ptr:  .res 2

.segment "STARTUP"

entry:
        APPLE2_PREAMBLE
        LDA     $FBB3           ; //e and //c: $06
        CMP     #$06
        BNE     @nodhgr
        SEI
        APPLE2_REBOOT_INIT      ; the boot drive's slot, for the way out
        APPLE2_SOFTEV apple2_reboot     ; Ctrl-RESET: the same way out
        ; the language card: the Monitor ROM into its RAM, then RAM
        BIT     ROMIN
        BIT     ROMIN
        LDA     #0
        STA     rg_ptr
        TAY
        LDX     #$F8
@rom:   STX     rg_ptr+1
:       LDA     (rg_ptr),Y
        STA     (rg_ptr),Y
        INY
        BNE     :-
        INX
        BNE     @rom
        BIT     LCBANK2
        BIT     LCBANK2
        ; the back-end to its place in the language card
        LDA     #<__LCCODE_LOAD__
        STA     @src+1
        LDA     #>__LCCODE_LOAD__
        STA     @src+2
        LDA     #<__LCCODE_RUN__
        STA     @dst+1
        LDA     #>__LCCODE_RUN__
        STA     @dst+2
        LDX     #>(__LCCODE_SIZE__ + __LCDATA_SIZE__ + 255)
        LDY     #0
@src:   LDA     $FFFF,Y
@dst:   STA     $FFFF,Y
        INY
        BNE     @src
        INC     @src+2
        INC     @dst+2
        DEX
        BNE     @src
        LDA     #0
        STA     QUIT_MARK
        STA     z:dg_cpg        ; the back-end's page operands: page 0's
        STA     sfx_req
        LDA     #1
        STA     snd_on          ; sounds on
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
        JMP     DOSWARM        ; nothing was touched: DOS is still there

msg_need:
        .byte   "ROGUE.DHGR NEEDS AN APPLE //E 128K OR //C", $0D
        .byte   "PRESS A KEY", $0D, 0

.assert __LCCODE_LOAD__ + __LCCODE_SIZE__ = __LCDATA_LOAD__, error, "LCDATA follows LCCODE"

.segment "CODE"

; plat_quit -- (core hook) ESC: leave (no DOS any more: reboot, see above).
; apple2_reboot (dev/lib/apple2/exit.asm, also the Ctrl-RESET vector): the
; Apple's own screen, the mark for HELLO, then the boot drive's ROM.
; Included here, not at the end: plat_quit falls into it, and the core's
; code after it keeps its addresses (sound.asm's tone loop: one page).
plat_quit:
        JSR     vid_off
EXIT_REBOOT_ONLY = 1            ; exit.asm: apple2_reboot alone, in CODE here
EXIT_REBOOT_IIE  = 1            ; //e/c only: LC ROM, main banks, 40 columns
EXIT_REBOOT_MARK = QUIT_MARK
.include "exit.asm"             ; apple2_reboot

; plat_sound_status -- (core hook) nothing to show outside the game screen.
plat_sound_status:
        RTS

.include "core/rogue_core.inc"  ; the game
.include "video_dhgr.asm"       ; its DHGR back-end
