; ============================================================================
; mainmenu.inc -- the main menu (ESC in a race): an overlay in the TITLE file
; ============================================================================
;   esc_menu     resident: reads TITLE (tune, text pages, this code at
;                MENU_AT, picture) and runs main_menu; a disk error: the
;                track menu
;   main_menu    TITLE PAGE / HELP / INPUT (keyboard, joystick, mouse: the
;                ones found) / HALL OF FAME / QUIT TO BASIC (the disk boots
;                again, HELLO sees QUIT_MARK and ends: DOS 3.3 is back). Arrows (I / K)
;                and RETURN or SPACE, or the digits 1-5; ESC: the title.
;                The stick moves the marker, the mouse's height points at an
;                item; their button chooses (and leaves the help / scores).
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
MM_N     = 5                    ; items
MM_ROW   = 6                    ; first item's text row (8 scanlines)
MM_REPEAT = 20                  ; stick: turns (~10 ms) between moves
MM_MSTEP = 39                   ; mouse: rows per item (0..191 / 5)
MM_PICK  = 1                    ; mm_pad: the mouse chose another item
.assert LOADBUF + 4 + TUNE_LEN + PAGES_LEN <= MENU_AT, error, "TITLE: tune + pages reach MENU_AT"

.segment "SYSBSS"
mm_sel:  .res 1                 ; the item marked
mm_mi:   .res 1                 ; the item the mouse last pointed at

.segment "CODE"
esc_menu:
        JSR     title_read
        BCC     @ok
        JMP     to_menu
@ok:    LDA     #0
        STA     mm_sel
        STA     mrep                    ; (the stick's repeat delay)
        LDA     #$FF
        STA     mm_mi
        JMP     main_menu

.segment "MENUOVL"
main_menu:
        JSR     page1_text
        LDA     #<mm_text
        STA     sptr
        LDA     #>mm_text
        STA     sptr+1
        JSR     page_lines
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
        LDX     #(MM_ROW + 4) * 8
        JSR     puts_at
mm_key: LDA     KBD                     ; a key, or the stick / mouse
        BMI     @kbd
        JSR     mm_pad
        BEQ     mm_key
        BNE     @act                    ; (always)
@kbd:   BIT     KBDSTRB
        AND     #$7F
        JSR     kbd_upcase
@act:   CMP     #MM_PICK
        BNE     @esc
        JMP     mm_show
@esc:   CMP     #KC_ESC
        BEQ     mm_title
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
        SEC                             ; 1-5: that item
        SBC     #'1'
        CMP     #MM_N
        BCS     mm_key
        STA     mm_sel
        BCC     mm_go                   ; (always)
@up:    LDA     mm_sel
        BEQ     mm_key
        DEC     mm_sel
        JMP     mm_show
@down:  LDA     mm_sel
        CMP     #MM_N - 1
        BCS     mm_key
        INC     mm_sel
        JMP     mm_show

mm_go:  LDA     mm_sel
        BEQ     mm_title
        CMP     #2
        BCC     mm_help
        BEQ     mm_input
        CMP     #3
        BEQ     mm_hof
        ; QUIT: the mouse off (the //c's IRQs), the mark "QU" for HELLO
        ; (src/hello.bas: it ends instead of BRUN), the disk booted again:
        ; BASIC with DOS 3.3 back
        LDA     _mouse_slot
        BEQ     @nomouse
        JSR     _mouse_close
@nomouse:
        LDA     #'Q'
        STA     QUIT_MARK
        LDA     #'U'
        STA     QUIT_MARK+1
        LDA     TXTSET
        LDA     LOWSCR
        JMP     BOOT_SLOT6

mm_title:
        JMP     attract

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

mm_input:                               ; the next device found
        LDX     inp_dev
@next:  INX
        CPX     #3
        BCC     @ok
        LDX     #INP_KEYS
@ok:    CPX     #INP_STICK
        BNE     @m
        LDA     joy_found
        BEQ     @next
@m:     CPX     #INP_MOUSE
        BNE     @set
        LDA     _mouse_slot
        BEQ     @next
@set:   TXA
        JSR     inp_set
        JMP     mm_show

mm_wait:                                ; a key, the button or the mouse's
        LDY     #1
        JSR     tick_wait
        BCS     @rts
        JSR     mm_click
        BCC     mm_wait
@rts:   RTS

; mm_click -- C = 1: the mouse (the input device) clicked, now released
mm_click:
        LDA     inp_dev
        CMP     #INP_MOUSE
        BNE     @no
        JSR     _mouse_poll
        LDA     _mouse_buttons
        BPL     @no
@rel:   JSR     _mouse_poll
        LDA     _mouse_buttons
        BMI     @rel
        SEC
        RTS
@no:    CLC
        RTS

; mm_pad -- one turn (~10 ms) of the stick or the mouse: A = KC_UP, KC_DOWN,
; KC_RET (the button, on release), MM_PICK (the mouse points at another
; item: mm_sel set); 0 (Z = 1): nothing
mm_pad: LDA     #40
        JSR     WAIT
        JSR     mm_click
        BCS     @go
        LDA     inp_dev
        CMP     #INP_MOUSE
        BEQ     @mouse
        LDA     joy_ok
        BEQ     @none
        LDA     BUTN0
        BPL     @nob
@rel:   LDA     BUTN0
        BMI     @rel
@go:    LDA     #KC_RET
        RTS
@nob:   LDA     mrep                    ; the repeat delay
        BEQ     @read
        DEC     mrep
@none:  LDA     #0
        RTS
@read:  JSR     read_stick_fast
        SEC
        LDA     joy_y
        SBC     joy_my
        BCS     @dn
        CMP     #<(-STICK_ON)
        BCS     @none
        LDA     #KC_UP
        BNE     @rep                    ; (always)
@dn:    CMP     #STICK_ON
        BCC     @none
        LDA     #KC_DOWN
@rep:   LDX     #MM_REPEAT
        STX     mrep
        RTS
@mouse: LDA     _mouse_y                ; (mm_click polled it) its item
        LDX     #0
@div:   CMP     #MM_MSTEP
        BCC     @item
        SBC     #MM_MSTEP
        INX
        CPX     #MM_N - 1
        BCC     @div
@item:  CPX     mm_mi                   ; only when it points elsewhere: the
        BEQ     @none                   ; keys keep their choice meanwhile
        LDA     mm_mi
        STX     mm_mi
        CMP     #$FF                    ; (the first look only notes it)
        BEQ     @none
        STX     mm_sel
        LDA     #MM_PICK
        RTS

mm_text:
        .byte 2 * 8, 15, "MAIN MENU", 0
        .byte (MM_ROW + 0) * 8, 12, "1  TITLE PAGE", 0
        .byte (MM_ROW + 2) * 8, 12, "2  HELP", 0
        .byte (MM_ROW + 4) * 8, 12, "3  INPUT:", 0
        .byte (MM_ROW + 6) * 8, 12, "4  HALL OF FAME", 0
        .byte (MM_ROW + 8) * 8, 12, "5  QUIT TO BASIC", 0
        .byte 19 * 8, 6, "ARROWS + RETURN, OR 1 TO 5", 0
        .byte 21 * 8, 9, "ESC: THE TITLE PAGE", 0
        .byte $FF
mm_dev_lo: .byte <mm_keys, <mm_stick, <mm_mouse
mm_dev_hi: .byte >mm_keys, >mm_stick, >mm_mouse
mm_keys:   .byte "KEYBOARD", 0
mm_stick:  .byte "JOYSTICK", 0
mm_mouse:  .byte "MOUSE   ", 0

.segment "CODE"
