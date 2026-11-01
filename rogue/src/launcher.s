; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; launcher.s -- ROGUE: picks the version of the game this Apple II can run
; ============================================================================
; HELLO runs BRUN ROGUE. Then:
;   1. an E-Z Color card (TMS9918A) in a slot (not on a //c: no slots;
;      lib/apple2/ezcolor.asm, boot drive and slot 3 skipped)
;        -> "E-Z COLOR CARD IN SLOT N", BRUN ROGUE.TMS (any Apple II);
;   2. else an Apple //e with 128 KB or a //c ($FBB3 = $06, auxiliary RAM
;      found by writing it: lib/apple2/auxdetect.asm)
;        -> "NO E-Z COLOR CARD: DHGR VERSION", BRUN ROGUE.DHGR;
;   3. else (II, II+, 64 KB //e, no card): a text page says what ROGUE
;      needs; a key returns to DOS.
; DOS's RESET vector is put back before the chained BRUN (the next program
; takes its own snapshot of it).
; ============================================================================

.include "apple2.inc"
.include "ezcolor.inc"

EZ_DETECT_BOOT_SLOT = DOS_IOB_SLOT ; DOS 3.3 IOB: slot * 16 of the boot drive

.segment "STARTUP"
entry:
        APPLE2_PREAMBLE
        JSR     apple2_zp_save
        JSR     HOME
        LDA     $FBB3
        CMP     #$06
        BNE     @probe          ; II / II+: slots, no 128 KB
        LDA     $FBC0
        BEQ     @nocard         ; //c: no slots, no card to look for
@probe: JSR     ez_detect       ; A = slot, Z = 0 if found
        BEQ     @nocard
        LDA     #<page_tms
        LDY     #>page_tms
        JSR     txt_page
        LDA     #<cmd_tms
        LDY     #>cmd_tms
        JMP     chain
@nocard:
        JSR     aux_detect      ; C = 1: //e 128 KB or //c
        BCC     @none
        LDA     #<page_dhgr
        LDY     #>page_dhgr
        JSR     txt_page
        LDA     #<cmd_dhgr
        LDY     #>cmd_dhgr
        JMP     chain
@none:  LDA     #<page_none
        LDY     #>page_none
        JSR     txt_page
        BIT     KBDSTRB
@key:   LDA     KBD
        BPL     @key
        BIT     KBDSTRB
        LDA     #22
        STA     CV
        LDA     #0
        STA     CH
        JSR     VTAB
        JMP     apple2_exit

; chain -- A/Y = a DOS command: the message stays ~0.4 s, DOS's RESET
; vector goes back, the cursor goes below the message, DOS runs it.
chain:
        PHA
        TYA
        PHA
        LDA     #0
        JSR     WAIT            ; ~0.17 s
        LDA     #0
        JSR     WAIT
        LDX     #2
@rv:    LDA     apple2_rst_buf,X
        STA     SOFTEV,X
        DEX
        BPL     @rv
        LDA     #6
        STA     CV
        LDA     #0
        STA     CH
        JSR     VTAB
        PLA
        TAY
        PLA
        JMP     dos_cmd_line    ; BRUN: never returns

; aux_detect (lib/apple2/auxdetect.asm) -- C = 1 on an Apple //e or //c
; with auxiliary RAM beyond the text page (an extended 80-column card): a
; write test through 80STORE + HIRES + PAGE2 that a 1 KB card fails. Included
; here, after its caller, so the launcher keeps its layout (STARTUP).
.include "auxdetect.asm"

.include "txtpage.inc"

.segment "RODATA"
cmd_tms:        .byte "BRUN ROGUE.TMS", 0
cmd_dhgr:       .byte "BRUN ROGUE.DHGR", 0

; 40 columns:   "----------------------------------------"
page_tms:
        .byte INV+0, 0, "      ROGUE - E-Z COLOR CARD FOUND      ", 0
        .byte 2, 0, "E-Z COLOR CARD IN SLOT #: LOADING THE", 0
        .byte 3, 0, "TMS9918 VERSION (ON THE CARD'S MONITOR).", 0
        .byte $FF
page_dhgr:
        .byte INV+0, 0, "   ROGUE - NO E-Z COLOR CARD: DHGR      ", 0
        .byte 2, 0, "NO E-Z COLOR CARD: LOADING THE DOUBLE", 0
        .byte 3, 0, "HI-RES VERSION FOR THIS 128K APPLE.", 0
        .byte $FF
page_none:
        .byte INV+0, 0, "    ROGUE CANNOT RUN ON THIS APPLE      ", 0
        .byte 2, 0,  "ROGUE NEEDS ONE OF THESE:", 0
        .byte 4, 0,  "- THE E-Z COLOR GRAPHICS INTERFACE", 0
        .byte 5, 0,  "  (TMS9918A VIDEO CARD, BYTE 1982) IN", 0
        .byte 6, 0,  "  ANY FREE SLOT EXCEPT 3, WITH ITS OWN", 0
        .byte 7, 0,  "  MONITOR: ANY APPLE II;", 0
        .byte 9, 0,  "- OR AN APPLE //E WITH 128K (EXTENDED", 0
        .byte 10, 0, "  80-COLUMN CARD) OR AN APPLE //C:", 0
        .byte 11, 0, "  DOUBLE HI-RES VERSION.", 0
        .byte 13, 0, "NO CARD ANSWERED (SLOT % = DISK DRIVE,", 0
        .byte 14, 0, "NOT TESTED) AND THIS APPLE HAS NO 128K.", 0
        .byte 16, 0, "PLUG THE CARD IN WITH THE APPLE OFF,", 0
        .byte 17, 0, "THEN BOOT THIS DISK AGAIN.", 0
        .byte 18, 0, "IN POM2: SLOT CONFIG, CARD EZCOLOR,", 0
        .byte 19, 0, "OR START POM2 WITH  --SLOT 4=EZCOLOR", 0
        .byte INV+21, 0, "PRESS A KEY TO RETURN TO DOS.", 0
        .byte $FF

.segment "CODE"
.include "dos.asm"
.include "ezcolor.asm"
.include "exit.asm"
