; ============================================================================
; mainmenu.inc -- the main menu (ESC in a race): an overlay in the TITLE file
; ============================================================================
;   esc_menu     resident: reads TITLE (tune, text pages, this code at
;                MENU_AT, picture) and runs main_menu; a disk error: the
;                track menu
;   main_menu    BACK TO THE RACE (a race not finished: race_resume) /
;                TITLE PAGE / HELP / INPUT (joystick or paddles, if found, or
;                keyboard alone; the keys always drive; kept in DIRTHOF
;                when the menu ends) / HALL OF FAME / QUIT TO BASIC (the disk
;                boots again, HELLO sees QUIT_MARK and ends: DOS 3.3 is
;                back). Arrows (I / K) and RETURN or SPACE, or the digits
;                0-5; ESC: back to the race, else the title.
;                The stick moves the marker (one item per push), a button
;                chooses (and leaves the help / scores).
;
; The code and its text cost no RAM: they come with TITLE into LOADBUF,
; over the loaded track (load_track runs before every race anyway).
; dirtbike.cfg links segment MENUOVL to run at MENU_AT and writes it to
; build/menu.bin; tools/titlefile.py puts it at its place in TITLE.
; ============================================================================

QUIT_MARK = $8000               ; = src/hello.bas PEEK (32768), (32769): "QU"
                                ; (the game's own code: DOS's boot leaves it,
                                ; BRUN DIRTBIKE would write over it)
BOOT_SLOT6 = $C600              ; the disk drive's boot ROM (slot 6, the //c's too)
MENU_AT  = $9C00                ; = dirtbike.cfg MENUOVL, tools/titlefile.py
MM_N     = 6                    ; items (0: back to the race)
MM_ROW   = 5                    ; first item's text row (8 scanlines)
MM_REPEAT = 20                  ; stick: turns (~10 ms) between moves
.assert LOADBUF + 4 + TUNE_LEN + PAGES_LEN <= MENU_AT, error, "TITLE: tune + pages reach MENU_AT"

.segment "SYSBSS"
mm_sel:  .res 1                 ; the item marked
mm_lo:   .res 1                 ; the first item: 0 in a race, else 1

.segment "CODE"
esc_menu:
        JSR     title_read
        BCS     :+
        JMP     mm_enter
:       JMP     to_menu

.segment "MENUOVL"
mm_enter:
        JSR     stick_calib             ; paddles: from where they are
        LDA     state                   ; a race on (not finished): it can
        CMP     #ST_FINISH              ; go on, item 0
        LDA     #0
        STA     mrep                    ; (the stick's repeat delay)
        ROL     A
        STA     mm_lo
        STA     mm_sel
main_menu:
        JSR     page1_text
        LDA     #<mm_text
        STA     sptr
        LDA     #>mm_text
        STA     sptr+1
        JSR     page_lines
        LDX     mm_lo                   ; ESC's line, and item 0 in a race
        LDA     mm_esc_lo,X
        LDY     mm_esc_hi,X
        LDX     #9
        STX     ht_col
        LDX     #21 * 8
        JSR     puts_at
        LDA     mm_lo
        BNE     mm_show
        JSR     hgr_puts8_at
        .byte   12, MM_ROW * 8
        .addr   mm_back
mm_show:
        LDX     #MM_N - 1               ; the marker on the chosen item
@mk:    TXA
        ASL     A
        ADC     #MM_ROW
        ASL     A
        ASL     A
        ASL     A
        STA     ht_sl
        LDA     #10
        STA     ht_col
        LDA     #' '
        CPX     mm_sel
        BNE     @put
        LDA     #'>'
@put:   JSR     hgr_putc8
        DEX
        BPL     @mk
        LDX     inp_dev                 ; the input device's name
        LDA     mm_dev_lo,X
        LDY     mm_dev_hi,X
        LDX     #23
        STX     ht_col
        LDX     #(MM_ROW + 6) * 8
        JSR     puts_at
mm_key: LDA     KBD                     ; a key, or the stick
        BMI     @kbd
        JSR     mm_pad
        BEQ     mm_key
        BNE     @act                    ; (always)
@kbd:   BIT     KBDSTRB
        AND     #$7F
        JSR     kbd_upcase
@act:   CMP     #KC_ESC                 ; ESC: the race, else the title
        BNE     @ar
        LDA     mm_lo
        STA     mm_sel
        JMP     mm_go
@ar:
        CMP     #KC_UP
        BEQ     @up
        CMP     #'I'
        BEQ     @up
        CMP     #KC_DOWN
        BEQ     @down
        CMP     #'K'
        BEQ     @down
        CMP     #KC_RET
        BEQ     mm_go
        CMP     #' '
        BEQ     mm_go
        SEC                             ; 0-5: that item
        SBC     #'0'
        CMP     #MM_N
        BCS     mm_key
        CMP     mm_lo
        BCC     mm_key
        STA     mm_sel
        BCS     mm_go                   ; (always)
@up:    LDA     mm_sel
        CMP     mm_lo
        BEQ     mm_key
        DEC     mm_sel
        JMP     mm_show
@down:  LDA     mm_sel
        CMP     #MM_N - 1
        BCS     mm_key
        INC     mm_sel
        JMP     mm_show

mm_go:  LDA     mm_sel
        CMP     #2
        BEQ     mm_help
        CMP     #3
        BEQ     mm_input
        CMP     #4
        BEQ     mm_hof
        JSR     mm_keep                 ; the menu ends: the device kept
        LDA     mm_sel
        BEQ     mm_back_go
        CMP     #1
        BEQ     mm_title
        ; QUIT: the mark "QU" for HELLO (src/hello.bas: it ends instead of
        ; BRUN), the disk booted again: BASIC with DOS 3.3 back
        LDA     #'Q'
        STA     QUIT_MARK
        LDA     #'U'
        STA     QUIT_MARK+1
        LDA     TXTSET
        LDA     LOWSCR
        JMP     BOOT_SLOT6

mm_title:
        JMP     attract
mm_back_go:
        JMP     race_resume

mm_help:
        JSR     page1_text              ; (the help page came with TITLE)
        LDA     page_lo
        STA     sptr
        LDA     page_hi
        STA     sptr+1
        JSR     page_lines
        JSR     mm_wait
        JMP     main_menu

mm_hof: LDA     #0                      ; tracks 1-15, then 16-30
        JSR     hof_page
        JSR     mm_wait
        LDA     #15
        JSR     hof_page
        JSR     mm_wait
        JMP     main_menu

mm_input:                               ; the next device (stick, paddles,
        LDX     inp_dev                 ; keyboard); the game port's two
        LDA     mm_next,X               ; only when something answered
        CMP     #INP_KEYS
        BEQ     @set
        LDX     joy_found
        BNE     @set
        LDA     #INP_KEYS
@set:   inp_set
        JMP     mm_show
mm_next: .byte INP_PADDLES, INP_STICK, INP_KEYS ; after STICK, KEYS, PADDLES

; mm_keep -- the device chosen into DIRTHOF, when it changed (write
; protected: kept for this game only)
mm_keep:
        LDA     inp_dev
        CMP     inp_pref
        BEQ     @rts
        STA     inp_pref
        JMP     hof_save
@rts:   RTS

mm_wait:                                ; a key or a button
        LDY     #1
        JSR     tick_wait
        BCC     mm_wait
        RTS

; mm_pad -- one turn (~10 ms) of the stick: A = KC_UP, KC_DOWN (KC_LEFT /
; KC_RIGHT: ignored), KC_RET (a button, on release); 0 (Z = 1): nothing
mm_pad: LDA     #40
        JSR     WAIT
        LDY     #MM_REPEAT
        JMP     stick_menu

mm_text:
        .byte 2 * 8, 15, "MAIN MENU", 0
        .byte (MM_ROW + 2) * 8, 12, "1  TITLE PAGE", 0
        .byte (MM_ROW + 4) * 8, 12, "2  HELP", 0
        .byte (MM_ROW + 6) * 8, 12, "3  INPUT:", 0
        .byte (MM_ROW + 8) * 8, 12, "4  HALL OF FAME", 0
        .byte (MM_ROW + 10) * 8, 12, "5  QUIT TO BASIC", 0
        .byte 19 * 8, 6, "ARROWS + RETURN, OR A DIGIT", 0
        .byte $FF
mm_back:   .byte "0  BACK TO THE RACE", 0
mm_esc_lo: .byte <mm_escr, <mm_esct
mm_esc_hi: .byte >mm_escr, >mm_esct
mm_escr:   .byte "ESC: BACK TO THE RACE", 0
mm_esct:   .byte "ESC: THE TITLE PAGE", 0
mm_dev_lo: .byte <mm_stick, <mm_keys, <mm_pdl ; INP_STICK, INP_KEYS, INP_PADDLES
mm_dev_hi: .byte >mm_stick, >mm_keys, >mm_pdl
mm_keys:   .byte "KEYBOARD", 0
mm_stick:  .byte "JOYSTICK", 0
mm_pdl:    .byte "PADDLES ", 0          ; (8 wide: covers the others)

.segment "CODE"
