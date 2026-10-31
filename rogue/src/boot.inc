; VERHILLE Arnaud — GPL-3.0 (see LICENSE at repository root).
; ============================================================================
; boot.inc -- ROGUE's Apple II start: find the E-Z Color card, or say why not
; ============================================================================
; BRUN ROGUE lands on `entry` (first byte of the file, $4000):
;   1. zero page snapshot + Ctrl-RESET -> DOS (exit.asm);
;   2. ez_detect: the card is looked for in every slot but the DOS boot
;      drive's (lib/apple2/ezcolor.asm; its order and rules are there);
;   3. no card: a full text page explains what is missing and how to fix
;      it, a key returns to DOS;
;   4. a card: vdp_patch points every VDP access of the game at its slot
;      (ezvdp.inc), the Apple text page tells the player to look at the
;      card's monitor (it stays up during the game: the game never writes
;      to the Apple screen except the SOUND line), then `start`, the
;      Apple-1 game's own entry.
; ============================================================================

.segment "STARTUP"

entry:
        APPLE2_PREAMBLE
        JSR     apple2_zp_save  ; FIRST: DOS's zero page, RESET -> DOS
        LDA     #1
        STA     snd_on          ; sounds on
        LDA     #0
        STA     sfx_req
        JSR     HOME
        JSR     ez_detect       ; A = slot 1..7, 0 = no card
        BNE     @found
        ; --- no card: explain, wait, back to DOS ---
        LDA     #<page_nocard
        LDY     #>page_nocard
        JSR     txt_page
        BIT     KBDSTRB
@key:   LDA     KBD
        BPL     @key
        BIT     KBDSTRB
        LDA     #21             ; the DOS prompt below the message
        JMP     exit_at_row
@found:
        JSR     vdp_patch       ; the game's VDP accesses -> this slot
        LDA     #<page_found
        LDY     #>page_found
        JSR     txt_page
        LDA     snd_on
        JSR     plat_sound_status
        JMP     start           ; the Apple-1 game from here

; ----------------------------------------------------------------------------
; vdp_patch -- every VDP access of the game (ezvdp.inc's VDPFIX table) gets
; the card's port: operand low byte = $80 | port | ez_slotx. Idempotent.
; ----------------------------------------------------------------------------
.import __VDPFIX_LOAD__, __VDPFIX_SIZE__
vdp_patch:
        LDA     #<__VDPFIX_LOAD__
        STA     txt_ptr
        LDA     #>__VDPFIX_LOAD__
        STA     txt_ptr+1
@site:  LDA     txt_ptr
        CMP     #<(__VDPFIX_LOAD__ + __VDPFIX_SIZE__)
        BNE     @go
        LDA     txt_ptr+1
        CMP     #>(__VDPFIX_LOAD__ + __VDPFIX_SIZE__)
        BEQ     @done
@go:    LDY     #0
        LDA     (txt_ptr),Y     ; operand address, low
        STA     txt_dst
        INY
        LDA     (txt_ptr),Y
        STA     txt_dst+1
        DEY
        LDA     (txt_dst),Y  ; $80 / $81 (or an earlier slot's port)
        AND     #$01            ; keep the port: 0 data, 1 control
        ORA     #$80
        ORA     ez_slotx
        STA     (txt_dst),Y
        CLC
        LDA     txt_ptr
        ADC     #2
        STA     txt_ptr
        BCC     @site
        INC     txt_ptr+1
        BNE     @site
@done:  RTS

; ----------------------------------------------------------------------------
; plat_quit -- (core hook) ESC (title, or Y to the in-game question): blank the card's
; picture, put the DOS prompt under the Apple page's text, leave.
; exit_at_row -- A = text row of the prompt; restores DOS and its page zero.
; ----------------------------------------------------------------------------
plat_quit:
        JSR     vid_off
        LDA     #20
exit_at_row:
        STA     CV
        LDA     #0
        STA     CH
        JSR     VTAB            ; BASL/BASH for that row (kept by apple2_exit)
        JMP     apple2_exit

; plat_sound_status -- (core hook) A = snd_on: the bottom line of the
; Apple page says SOUND ON / OFF. Keeps nothing but the core's state.
plat_sound_status:
        TAX
        LDA     #<page_snd_on
        LDY     #>page_snd_on
        CPX     #0
        BNE     @on
        LDA     #<page_snd_off
        LDY     #>page_snd_off
@on:    JMP     txt_page

.segment "RODATA"


; 40 columns:   "----------------------------------------"
page_found:
        .byte INV+0, 0, "  ROGUE PLAYS ON THE E-Z COLOR MONITOR  ", 0
        .byte INV+1, 0, "        E-Z COLOR CARD IN SLOT #        ", 0
        .byte 3, 0,  "LOOK AT THE CARD'S OWN SCREEN: THIS", 0
        .byte 4, 0,  "APPLE SCREEN ONLY KEEPS THE KEYS.", 0
        .byte 6, 0,  "I J K L OR ARROWS  MOVE, BUMP TO FIGHT", 0
        .byte 7, 0,  "B        BAG (A LETTER USES AN ITEM)", 0
        .byte 8, 0,  "T        THROW A DAGGER, THEN I J K L", 0
        .byte 9, 0,  ".        REST ONE TURN", 0
        .byte 10, 0, "H OR ?   HELP ON THE CARD'S SCREEN", 0
        .byte 11, 0, "S        SOUND ON / OFF", 0
        .byte 12, 0, "ESC      QUIT TO DOS (Y CONFIRMS)", 0
        .byte 14, 0, "WALK ONTO ITEMS TO PICK THEM UP. FIND", 0
        .byte 15, 0, "THE STAIRS, GO DOWN 12 FLOORS AND BEAT", 0
        .byte 16, 0, "THE DEMON OF DEPTH 13. ONE LIFE ONLY.", 0
        .byte 18, 0, "CTRL-RESET ALSO RETURNS TO DOS.", 0
        .byte $FF

page_snd_on:
        .byte 22, 0, "SOUND: ON ", 0
        .byte $FF
page_snd_off:
        .byte 22, 0, "SOUND: OFF", 0
        .byte $FF

page_nocard:
        .byte INV+0, 0, "     E-Z COLOR CARD NOT FOUND           ", 0
        .byte 2, 0,  "ROGUE NEEDS THE E-Z COLOR GRAPHICS", 0
        .byte 3, 0,  "INTERFACE: THE TMS9918A COLOR VIDEO", 0
        .byte 4, 0,  "CARD (BYTE, AUGUST 1982) AND ITS OWN", 0
        .byte 5, 0,  "MONITOR. THE GAME IS SHOWN ON THAT", 0
        .byte 6, 0,  "MONITOR, NOT ON THIS SCREEN.", 0
        .byte 8, 0,  "NO CARD ANSWERED IN SLOTS 1, 2, 4 TO 7", 0
        .byte 9, 0,  "(SLOT % IS THE DISK DRIVE: NOT TESTED).", 0
        .byte 11, 0, "TURN THE APPLE OFF, PLUG THE CARD IN", 0
        .byte 12, 0, "ANY FREE SLOT BUT 3, CONNECT ITS", 0
        .byte 13, 0, "MONITOR, THEN BOOT THIS DISK AGAIN.", 0
        .byte 15, 0, "IN POM2: SLOT CONFIG, CARD EZCOLOR,", 0
        .byte 16, 0, "OR START IT WITH  --SLOT 4=EZCOLOR", 0
        .byte INV+18, 0, "PRESS A KEY TO RETURN TO DOS.", 0
        .byte $FF

.segment "CODE"
