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
LC_ROM_WRAM = $C081             ; language card, read twice: ROM read, RAM write
LC_RAM_RAM  = $C083             ;  RAM (bank 2) read and write
LC_ROM      = $C082             ;  ROM read, RAM write-protected
DOS_IOB_SLOT = $B7E9            ; DOS 3.3: slot * 16 of the last drive used
DOSWARM_    = $03D0

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
        LDA     DOS_IOB_SLOT    ; the boot drive's slot, for the way out
        LSR
        LSR
        LSR
        LSR
        AND     #7
        BNE     :+
        LDA     #6
:       ORA     #$C0
        STA     rg_boot+2
        LDA     #<rg_reset      ; Ctrl-RESET: the same way out
        STA     SOFTEV
        LDA     #>rg_reset
        STA     SOFTEV+1
        EOR     #$A5
        STA     SOFTEV+2
        ; the language card: the Monitor ROM into its RAM, then RAM
        BIT     LC_ROM_WRAM
        BIT     LC_ROM_WRAM
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
        BIT     LC_RAM_RAM
        BIT     LC_RAM_RAM
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
        JMP     DOSWARM_        ; nothing was touched: DOS is still there

msg_need:
        .byte   "ROGUE.DHGR NEEDS AN APPLE //E 128K OR //C", $0D
        .byte   "PRESS A KEY", $0D, 0

.assert __LCCODE_LOAD__ + __LCCODE_SIZE__ = __LCDATA_LOAD__, error, "LCDATA follows LCCODE"

.segment "CODE"

; plat_quit -- (core hook) ESC: leave (no DOS any more: reboot, see above).
plat_quit:
        JSR     vid_off
        ; fall through
; rg_reset -- also the Ctrl-RESET vector: the mark for HELLO, the Apple's
; own screen, then the boot drive's ROM.
rg_reset:
        SEI
        LDA     #'Q'
        STA     QUIT_MARK
        LDA     #'U'
        STA     QUIT_MARK+1
        BIT     LC_ROM
        STA     RAMRDOFF
        STA     RAMWRTOFF
        STA     COL80OFF
        BIT     DHIRES_OFF
        BIT     LOWSCR
        BIT     TXTSET
rg_boot:
        JMP     $C600           ; slot patched at start

; plat_sound_status -- (core hook) nothing to show outside the game screen.
plat_sound_status:
        RTS

.include "core/rogue_core.inc"  ; the game
.include "video_dhgr.asm"       ; its DHGR back-end
