; ============================================================================
; menu.inc -- choose one of the 30 tracks (HGR page 1)
; ============================================================================
;   menu      draw the menu, wait for a choice; returns A = sel (0..29)
;             when the player starts a race. Only the tracks already
;             finished (a best time in the hall of fame) can be chosen, and
;             the lowest one not finished yet; a game then runs on through
;             the next ones.
; Two columns of 15 tracks; the marker follows arrows / J K L I or the
; joystick, RETURN / SPACE / button 0 starts. Under the list: the record of
; the session and the reference time (tools/solver.py) of the track.
; ============================================================================

MENU_TOP  = 32                  ; first row of the list
MENU_INFO = 160
MENU_HELP = 176
REPEAT    = 6                   ; menu turns between stick repeats

.segment "ZEROPAGE"
sel:      .res 1                ; selected track
msel:     .res 1                ; scratch

.segment "DATA"
lbl_lock: .byte 0               ; bit 7: put_track_label prints no name

.segment "CODE"

.segment "TXTC5"                 ; runs in the text page (copied at boot)
menu:
        LDA     sel                     ; a locked track: back to track 1
        JSR     is_locked
        BCC     @open
        LDA     #0
        STA     sel
@open:  JSR     page1_text
        LDA     #<msg_title
        LDY     #>msg_title
        LDX     #16
        STX     ht_col
        LDX     #8
        JSR     puts_at
        LDA     #<msg_help
        LDY     #>msg_help
        LDX     #2
        STX     ht_col
        LDX     #MENU_HELP
        JSR     puts_at
        LDA     #0                      ; the list
        STA     msel
@list:  JSR     draw_entry
        INC     msel
        LDA     msel
        CMP     #NTRACKS
        BNE     @list
        JSR     mark_sel
@wait:  JSR     menu_input              ; A = new selection, or $FF/$FE/$FD/$FC
        CMP     #$FC
        BNE     @nh
        LDX     #0                      ; H: the help page, then the menu again
        JSR     show_page
        JMP     menu
@nh:    CMP     #$FD
        BEQ     @esc
        CMP     #$FE
        BEQ     @go
        CMP     #$FF
        BEQ     @wait
        JSR     is_locked               ; not finished yet: the marker stays
        BCS     @wait
        PHA
        LDA     #' '                    ; move the marker
        JSR     put_marker
        PLA
        STA     sel
        JSR     mark_sel
        JMP     @wait
@go:    LDA     sel
        CLC
        RTS
@esc:   SEC                             ; ESC: back to the title
        RTS

.segment "CODE"
; page1_text -- page 1 on screen, black, set up for text
page1_text:
        LDA     #0
        STA     ht_page
        STA     pidx
        JSR     render_begin            ; page 1 tables for the text
        JSR     clear_page1
        LDA     TXTCLR
        LDA     MIXCLR
        LDA     HIRES
        LDA     LOWSCR
        RTS

; mark_sel -- the marker and the info line of `sel`
.segment "TXTC7"                 ; runs in the text page (copied at boot)
mark_sel:
        LDA     #'>'
        JSR     put_marker
        LDA     #<msg_info              ; "RECORD -:--.-  REF M:SS.T"
        STA     ht_src_lo
        LDA     #>msg_info
        STA     ht_src_hi
        LDA     #2
        STA     ht_col
        LDA     #MENU_INFO
        STA     ht_sl
        JSR     hgr_puts8
        LDX     sel
        LDA     rec_min,X
        CMP     #$FF
        BEQ     @nor
        LDA     #9
        STA     ht_col
        LDA     rec_min,X
        LDY     rec_sec,X
        PHA
        LDA     rec_hun,X
        TAX
        PLA
        JSR     put_time
@nor:   LDA     #24                     ; reference time
        STA     ht_col
        LDA     sel                     ; track_par + 6 sel
        ASL     A
        STA     msel
        ASL     A
        CLC
        ADC     msel
        TAX
        LDY     #6
@par:   LDA     track_par,X
        JSR     hgr_putc8
        INX
        DEY
        BNE     @par
        RTS

.segment "CODE"
; put_marker -- char A left of entry `sel`
put_marker:
        PHA
        LDA     sel
        JSR     entry_pos
        DEC     ht_col
        PLA
        JMP     hgr_putc8

; entry_pos -- A = track: ht_col = its number's column, ht_sl = its row
entry_pos:
        LDX     #2
        CMP     #15
        BCC     @c
        SBC     #15
        LDX     #22
@c:     STX     ht_col
        ASL     A
        ASL     A
        ASL     A
        ADC     #MENU_TOP
        STA     ht_sl
        RTS

; is_locked -- C = 1: track A not open. Open: the tracks finished (a best
; time) and the lowest one not finished yet. Keeps A.
is_locked:
        TAX
        LDY     #0                      ; Y = the lowest not finished
@low:   LDA     rec_min,Y
        CMP     #$FF
        BEQ     @first
        INY
        CPY     #NTRACKS
        BNE     @low
@first: LDA     rec_min,X
        CMP     #$FF                    ; C = 0: finished
        BCC     @r
        STY     pen
        TXA
        CMP     pen
        BEQ     @open
        SEC
        RTS
@open:  CLC
@r:     TXA
        RTS

; draw_entry -- "NN NAME" of track msel at its place in the list ("NN ----"
; while locked)
draw_entry:
        LDA     msel
        JSR     entry_pos
        LDA     msel
        JSR     is_locked
        ROR     lbl_lock
        ; fall through

; put_track_label -- "NN NAME" of track A at ht_col / ht_sl
put_track_label:
        PHA
        TAX                             ; number, 2 digits
        INX
        TXA
        LDX     #'0'
@ten:   CMP     #10
        BCC     @one
        SBC     #10
        INX
        BNE     @ten
@one:   PHA
        TXA
        JSR     hgr_putc8
        PLA
        ORA     #'0'
        JSR     hgr_putc8
        INC     ht_col
        ASL     lbl_lock                ; locked: no name
        BCC     @name
        PLA
        LDA     #<msg_locked
        STA     ht_src_lo
        LDA     #>msg_locked
        STA     ht_src_hi
        BNE     @put
@name:  LDA     #<track_names           ; the A-th name
        STA     ht_src_lo
        LDA     #>track_names
        STA     ht_src_hi
        PLA
        TAX
        BEQ     @put
        LDY     #0
@skip:  LDA     (ht_src_lo),Y
        INC     ht_src_lo
        BNE     @s1
        INC     ht_src_hi
@s1:    CMP     #0
        BNE     @skip
        DEX
        BNE     @skip
@put:   JMP     hgr_puts8

; put_time -- "M:SS.T" from A = minutes, Y = seconds (BCD), X = hundredths
put_time:
        ORA     #'0'
        JSR     hgr_putc8
        LDA     #':'
        JSR     hgr_putc8
        TYA
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        ORA     #'0'
        JSR     hgr_putc8
        TYA
        AND     #$0F
        ORA     #'0'
        JSR     hgr_putc8
        LDA     #'.'
        JSR     hgr_putc8
        TXA
        LSR     A
        LSR     A
        LSR     A
        LSR     A
        ORA     #'0'
        JMP     hgr_putc8

; puts_at -- string A/Y at column ht_col, row X
puts_at:
        STA     ht_src_lo
        STY     ht_src_hi
        STX     ht_sl
        JMP     hgr_puts8

; menu_input -- one turn (~10 ms): A = new selection, $FE = start, $FF = none
menu_input:
        LDA     #40
        JSR     WAIT
        LDA     KBD
        BMI     @key
        LDY     #REPEAT
        JSR     stick_menu
        BEQ     @none
        BNE     @act                    ; (always)
@key:   BIT     KBDSTRB
        AND     #$7F
        JSR     kbd_upcase
@act:   CMP     #KC_RET
        BEQ     @start
        CMP     #KC_ESC
        BEQ     @esc
        CMP     #' '
        BEQ     @start
        CMP     #'H'
        BEQ     @help
        CMP     #KC_UP
        BEQ     @up
        CMP     #'I'
        BEQ     @up
        CMP     #KC_DOWN
        BEQ     @down
        CMP     #'K'
        BEQ     @down
        CMP     #KC_LEFT
        BEQ     @left
        CMP     #'J'
        BEQ     @left
        CMP     #KC_RIGHT
        BEQ     @right
        CMP     #'L'
        BEQ     @right
@none:  LDA     #$FF
        RTS
@start: LDA     #$FE
        RTS
@esc:   LDA     #$FD
        RTS
@help:  LDA     #$FC
        RTS
@up:    LDA     sel
        BEQ     @none
        SEC
        SBC     #1
        RTS
@down:  LDA     sel
        CMP     #NTRACKS-1
        BCS     @none
        ADC     #1
        RTS
@left:  LDA     sel
        CMP     #15
        BCC     @none
        SBC     #15
        RTS
@right: LDA     sel
        CMP     #15
        BCS     @none
        ADC     #15
        RTS

; clear_page1 -- HGR page 1 black
clear_page1:
        LDA     #$20
        STA     cp_dst+1
        LDY     #0
        STY     cp_dst
        TYA
@c:     STA     (cp_dst),Y
        INY
        BNE     @c
        INC     cp_dst+1
        LDX     cp_dst+1
        CPX     #$40
        BNE     @c
        RTS

.segment "RODATA"
msg_title: .byte "DIRTBIKE", 0
msg_locked: .byte "----------", 0
msg_help:  .byte "ARROWS: CHOOSE  RETURN: RACE  H: HELP", 0
msg_info:  .byte "BEST   -:--.-     REF ", 0
msg_load:  .byte "LOADING...                   ", 0
msg_derr:  .byte "DISK ERROR: PRESS A KEY      ", 0
.segment "CODE"
